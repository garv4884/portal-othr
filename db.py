import hashlib
import json
import logging
import os
import subprocess
import sys
import time
import random
from datetime import datetime, timedelta

import streamlit as st
import redis

# Import config constants
try:
	from config import TEAM_PALETTE, EPOCH_DURATION_SECS, STARTING_HP, STARTING_AP, ATTACK_COST_AP
except ImportError:
	pass

_LOG = logging.getLogger(__name__)

# -- STORAGE BACKENDS -----------------------------------------
class InMemoryStore:
	def __init__(self):
		self._kv = {}

	def get(self, key):
		return self._kv.get(key)

	def set(self, key, value, ex=None):
		self._kv[key] = value
		return True

	def lpush(self, key, *values):
		items = self._kv.get(key, [])
		if not isinstance(items, list):
			items = []
		for value in values:
			items.insert(0, value)
		self._kv[key] = items
		return len(items)

	def lrange(self, key, start, end):
		items = self._kv.get(key, [])
		if not isinstance(items, list):
			return []
		stop = None if end == -1 else end + 1
		return items[start:stop]

	def delete(self, key):
		self._kv.pop(key, None)
		return True

	def flushdb(self):
		self._kv.clear()
		return True

	def ping(self):
		return True

@st.cache_resource
def get_store():
	try:
		# Use Streamlit secrets for Redis config; fall back to local defaults
		host = st.secrets.get("REDIS_HOST", "localhost")
		port = int(st.secrets.get("REDIS_PORT", 6379))
		password = st.secrets.get("REDIS_PASSWORD", None)
		
		r = redis.Redis(
			host=host, 
			port=port, 
			password=password, 
			decode_responses=True,
			socket_timeout=2
		)
		r.ping()
		return r, True
	except Exception as e:
		_LOG.warning(f"Redis connection failed: {e}. Falling back to memory.")
		return InMemoryStore(), False

R, redis_live = get_store()

# -- ACCOUNTS -------------------------------------------------
def hash_pw(pw):
	return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
	raw = R.get("ot:users")
	if raw:
		try: return json.loads(raw)
		except: pass
	return {}

def save_users(users):
	R.set("ot:users", json.dumps(users))

def get_user(username):
	return load_users().get(username)

def register_user(username, password, display_name):
	users = load_users()
	if username in users:
		return False, "Username exists."
	users[username] = {
		"pw_hash": hash_pw(password),
		"display_name": display_name,
		"team": None,
		"created": datetime.utcnow().isoformat(),
	}
	save_users(users)
	return True, "Account created"

def login_user(username, password):
	users = load_users()
	if username not in users:
		return False, "User not found."
	if users[username]["pw_hash"] != hash_pw(password):
		return False, "Wrong password."
	return True, users[username]

# -- TEAMS ---------------------------------------------------
def load_teams():
	raw = R.get("ot:teams_meta")
	if raw:
		try: return json.loads(raw)
		except: pass
	return {}

def save_teams(teams):
	R.set("ot:teams_meta", json.dumps(teams))

def create_team(tname, username, join_code=""):
	tname = tname.strip()
	teams = load_teams()
	users = load_users()
	if len(teams) >= 30: return False, "Map capacity reached."
	if tname in teams: return False, "Kingdom claimed."

	idx = len(teams) % len(TEAM_PALETTE)
	col = TEAM_PALETTE[idx]

	teams[tname] = {
		"creator": username,
		"join_code": join_code,
		"members": [username],
		"created": datetime.utcnow().isoformat(),
		"color": col["color"], "bg": col["bg"], "icon": col["icon"],
	}
	save_teams(teams)

	if username in users:
		users[username]["team"] = tname
		save_users(users)

	gs = load_gs()
	if tname not in gs["hp"]:
		gs["hp"][tname] = STARTING_HP
		gs["ap"][tname] = STARTING_AP
		empty = [i for i, owner in enumerate(gs["grid"]) if not owner]
		if empty:
			gs["grid"][random.choice(empty)] = tname
		save_gs(gs)

	return True, f"Kingdom {tname} established."

def join_team(tname, username, join_code=""):
	teams = load_teams()
	users = load_users()
	if tname not in teams:
		return False, "Kingdom not found."
	if str(teams[tname].get("join_code", "")) != str(join_code):
		return False, "Incorrect Vault Password."
	if username in teams[tname]["members"]:
		return False, "Already joined."

	old_team = users.get(username, {}).get("team")
	if old_team and old_team in teams and username in teams[old_team]["members"]:
		teams[old_team]["members"].remove(username)

	teams[tname]["members"].append(username)
	save_teams(teams)

	users[username]["team"] = tname
	save_users(users)
	return True, f"Joined {tname}"

# -- GAME STATE ----------------------------------------------
def _init_state():
	return {
		"grid": [""] * 30,
		"hp": {}, "ap": {},
		"epoch": 1,
		"phase": "MOBILIZATION",
		"epoch_end": (datetime.utcnow() + timedelta(seconds=EPOCH_DURATION_SECS)).isoformat(),
		"queued_actions": {},
		"queued_attacks": [],
		"task_done_by_user": {},
		"task_done_by_team": {},
		"alliances": {},
		"alliance_reqs": {},
		"shadow_task_ap": {}
	}

def load_gs():
	raw = R.get("ot:state")
	if raw:
		try: return json.loads(raw)
		except: pass
	state = _init_state()
	save_gs(state)
	return state

def save_gs(state):
	R.set("ot:state", json.dumps(state))

def reset_gs():
	R.delete("ot:state")
	R.delete("ot:events")

def push_ev(kind, msg, team=None):
	event = {"ts": datetime.utcnow().strftime("%H:%M:%S"), "kind": kind, "msg": msg, "team": team}
	R.lpush("ot:events", json.dumps(event))

def load_evs(limit=40):
	res = R.lrange("ot:events", 0, limit - 1)
	out = []
	for item in res:
		try: out.append(json.loads(item))
		except: pass
	return out

def terr_count(grid, teams_list):
	counts = {t: 0 for t in teams_list}
	for cell in grid:
		if cell in counts: counts[cell] += 1
	counts[""] = grid.count("")
	return counts

# -- SIMULATION ENGINE ---------------------------------------
def simulate_epoch(gs):
	gs = dict(gs)
	gs["epoch"] += 1
	gs["epoch_end"] = (datetime.utcnow() + timedelta(seconds=EPOCH_DURATION_SECS)).isoformat()
	
	queued = gs.get("queued_actions", {})
	gs["queued_actions"] = {}
	queued_attacks = gs.get("queued_attacks", [])
	gs["queued_attacks"] = []
	blocked_backstabbers = set()
	
	# 1. Resolve Suspicions
	for actor, action in list(queued.items()):
		if action["action"] == "SUSPICION":
			target = action["target"]
			t_action = queued.get(target)
			if t_action and t_action["action"] == "BACKSTAB" and t_action["target"] == actor:
				dmg = 3000
				gs["hp"][target] = max(0, int(gs["hp"].get(target, 0)) - dmg)
				blocked_backstabbers.add(target)
				push_ev("SYS", f"DISCOVERY: {actor} caught {target} plot! {target} suffers -{dmg} HP.", actor)
			else:
				dmg = 2000
				gs["hp"][actor] = max(0, int(gs["hp"].get(actor, 0)) - dmg)
				push_ev("SYS", f"FAILURE: {actor} falsely accused {target}. {actor} suffers -{dmg} HP.", actor)

	# 2. Resolve Backstabs
	for actor, action in list(queued.items()):
		if action["action"] == "BACKSTAB" and actor not in blocked_backstabbers:
			target = action["target"]
			if actor in gs["alliances"] and target in gs["alliances"][actor]: gs["alliances"][actor].remove(target)
			if target in gs["alliances"] and actor in gs["alliances"][target]: gs["alliances"][target].remove(actor)
			dmg = 3000
			gs["hp"][target] = max(0, int(gs["hp"].get(target, 0)) - dmg)
			push_ev("ATTACK", f"BETRAYAL: {actor} backstabbed {target} (-{dmg} HP)!", actor)

	# 3. Resolve Queued Human Attacks
	for attack in queued_attacks:
		actor, target, requested = attack.get("actor"), attack.get("target"), int(attack.get("hits", 1))
		if gs["hp"].get(actor, 0) <= 0 or gs["hp"].get(target, 0) <= 0: continue
		
		max_hits = int(gs["ap"].get(actor, 0)) // ATTACK_COST_AP
		hits = min(requested, max_hits)
		if hits > 0:
			dmg = hits * 100
			gs["ap"][actor] -= hits * ATTACK_COST_AP
			gs["hp"][target] = max(0, int(gs["hp"][target]) - dmg)
			
			if hits >= 3:
				t_cells = [i for i, c in enumerate(gs["grid"]) if c == target]
				if t_cells:
					cell = random.choice(t_cells)
					gs["grid"][cell] = actor
					push_ev("ATTACK", f"CONQUEST: {actor} seized cell {cell} from {target}!", actor)
			push_ev("ATTACK", f"STRIKE: {actor} hit {target} x{hits} (-{dmg} HP).", actor)

	# 4. Eliminations
	for t, hp in list(gs["hp"].items()):
		if hp <= 0:
			for i in range(len(gs["grid"])):
				if gs["grid"][i] == t: gs["grid"][i] = ""

	# 5. Economy: +50 AP per cell
	for t in gs["hp"]:
		if gs["hp"].get(t, 0) > 0:
			terr = gs["grid"].count(t)
			ap_gain = terr * 50
			gs["ap"][t] = int(gs["ap"].get(t, 0)) + ap_gain
			if ap_gain > 0: push_ev("SYS", f"{t} income: +{ap_gain} AP.", t)

	gs["shadow_task_ap"] = {}
	save_gs(gs)
	return gs

def expand_territory(gs, team):
	from config import get_amoeba_adjacency
	adj = get_amoeba_adjacency(len(gs["grid"]))
	my_cells = [i for i, owner in enumerate(gs["grid"]) if owner == team]
	candidates = set()
	for c in my_cells:
		candidates.update([n for n in adj.get(c, []) if gs["grid"][n] == ""])
	if not candidates or int(gs["ap"].get(team, 0)) < 150: return False, "Insufficient resources or space."
	target = random.choice(list(candidates))
	gs["grid"][target] = team
	gs["ap"][team] -= 150
	push_ev("ATTACK", f"EXPANSION: {team} claimed cell {target}.", team)
	return True, f"Claimed cell {target}."

def run_code_safe(code, timeout=5):
	blocked = ["import os", "import sys", "subprocess", "open(", "exec(", "eval("]
	if any(b in code for b in blocked): return "", "[SECURITY] Blocked."
	try:
		res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout)
		return res.stdout[:2000], res.stderr[:1000]
	except Exception as e: return "", str(e)

def run_bot_task(task_id, user_code, team, gs):
	from config import BOT_TASKS
	if task_id not in BOT_TASKS: return False, "Not found."
	task = BOT_TASKS[task_id]
	
	now = time.time()
	last = gs.setdefault("bot_solve_time", {}).get(team, 0)
	if now - last < 30: return False, f"Cooldown: {30-int(now-last)}s"
	
	full_code = user_code + "\n" + task["test_harness"]
	stdout, stderr = run_code_safe(full_code)
	if stderr: return False, f"Logic error: {stderr[:80]}"
	
	try:
		exec_globals = {}
		exec(full_code, exec_globals)
		val = exec_globals.get("verify_val")
		expected = task["expected_output"]
		if (isinstance(expected, float) and abs(val-expected)<0.01) or (val == expected):
			gs["bot_solve_time"][team] = now
			gs.setdefault("task_done_by_team", {}).setdefault(team, {})[task_id] = datetime.utcnow().isoformat()
			return True, f"VALIDATED: {task['verify_token']}"
		return False, f"Wrong answer. Got {val}"
	except Exception as e: return False, str(e)
