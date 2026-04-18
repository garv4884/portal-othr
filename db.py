import streamlit as st
import redis
import html
import time
import re
import json
import hashlib
import ast
import sys
import subprocess
from datetime import datetime, timedelta

# Import config constants
try:
    from config import TEAM_PALETTE, EPOCH_DURATION_SECS, STARTING_HP, STARTING_AP
except ImportError:
    pass

class MockRedis:
    def __init__(self):
        self._d = {}
        self._lists = {}
    def get(self, k): return self._d.get(k)
    def set(self, k, v, ex=None): self._d[k] = v; return True
    def setnx(self, k, v):
        if k in self._d: return False
        self._d[k] = v; return True
    def expire(self, k, t): return True
    def lpush(self, k, *vals):
        if k not in self._lists: self._lists[k] = []
        for v in vals: self._lists[k].insert(0, v)
        return len(self._lists[k])
    def ltrim(self, k, start, end):
        if k in self._lists: self._lists[k] = self._lists[k][start:end+1]
        return True
    def lrange(self, k, s, e):
        lst = self._lists.get(k, [])
        return lst[s: None if e == -1 else e + 1]
    def ping(self): return True
    def delete(self, k):
        self._d.pop(k, None)
        self._lists.pop(k, None)
        return True

import streamlit as st
import redis

@st.cache_resource
def get_redis():
    try:
        url = st.secrets["REDIS_URL"]
        r = redis.from_url(url, decode_responses=True)
        r.ping()
        return r, True
    except Exception:
        return MockRedis(), False


R, redis_live = get_redis()

# ── ACCOUNTS ──────────────────────────────────────────────────
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
    raw = R.get("ot:users")
    if raw:
        try: return json.loads(raw)
        except: pass
    return {}

def save_users(users): R.set("ot:users", json.dumps(users))

def get_user(username): return load_users().get(username)

def register_user(username, password, display_name):
    # Backend Safety: Strict length and sanitized
    un = html.escape(username[:20].strip())
    dn = html.escape(display_name[:20].strip())
    if not re.match(r"^[a-zA-Z0-9 -]+$", un) or not re.match(r"^[a-zA-Z0-9 -]+$", dn):
        return False, "Names must be alphanumeric/spaces only."
    
    users = load_users()
    if un in users: return False, "Username exists."
    users[un] = {
        "pw_hash": hash_pw(password),
        "display_name": dn,
        "team": None,
        "created": datetime.utcnow().isoformat()
    }
    save_users(users)
    return True, "Account created"

def login_user(username, password):
    users = load_users()
    if username not in users: return False, "User not found."
    if users[username]["pw_hash"] != hash_pw(password): return False, "Wrong password."
    return True, users[username]

# ── DYNAMIC TEAMS ─────────────────────────────────────────────
def load_teams():
    raw = R.get("ot:teams_meta")
    if raw:
        try: return json.loads(raw)
        except: pass
    return {}

def save_teams(t): R.set("ot:teams_meta", json.dumps(t))

def create_team(tname, username, join_code=""):
    tname = tname.strip()
    teams = load_teams()
    users = load_users()
    if len(teams) >= 30: return False, "Maximum 30 teams allowed on the map."
    if tname in teams: return False, "Already exists."
    
    old_team = users.get(username, {}).get("team")
    if old_team and old_team in teams and username in teams[old_team]["members"]:
        teams[old_team]["members"].remove(username)

    
    # Assign color
    idx = len(teams) % len(TEAM_PALETTE)
    col = TEAM_PALETTE[idx]
    
    # Backend Safety: Strict length and sanitized
    tname = html.escape(tname[:20].strip())
    if not re.match(r"^[a-zA-Z0-9 -]+$", tname):
        return False, "Kingdom name must be alphanumeric/spaces only."
    
    teams[tname] = {
        "creator": username,
        "join_code": join_code[:20],
        "members": [username],
        "created": datetime.utcnow().isoformat(),
        "color": col["color"],
        "bg": col["bg"],
        "icon": col["icon"]
    }
    save_teams(teams)
    
    users[username]["team"] = tname
    save_users(users)
    
    # Init stats cleanly
    gs = load_gs()
    if tname not in gs["hp"]:
        gs["hp"][tname] = STARTING_HP
        gs["ap"][tname] = STARTING_AP
        
        # Expand the world map by exactly 1 region per entering kingdom
        while len(gs["grid"]) < len(teams):
            gs["grid"].append("")
            
        # Assign random available cell
        empty_cells = [i for i, owner in enumerate(gs["grid"]) if not owner]
        if empty_cells:
            import random
            assigned = random.choice(empty_cells)
            gs["grid"][assigned] = tname
            
        save_gs(gs)
        
    return True, f"Created {tname}"

def join_team(tname, username, join_code=""):
    teams = load_teams()
    users = load_users()
    if tname not in teams: return False, "Kingdom not found."
    if str(teams[tname].get("join_code", "")) != str(join_code): return False, "Incorrect Vault Password."
    if username in teams[tname]["members"]: return False, "Already joined."
    
    old_team = users.get(username, {}).get("team")
    if old_team and old_team in teams and username in teams[old_team]["members"]:
        teams[old_team]["members"].remove(username)
        
    teams[tname]["members"].append(username)
    save_teams(teams)
    
    users[username]["team"] = tname
    save_users(users)
    return True, f"Joined {tname}"

# ── GAME STATE (GRID) ───────────────────────────────────────────
def _init_state():
    grid = []
    return {
        "grid": grid,
        "hp":   {},
        "ap":   {},
        "epoch": 1,
        "phase": "MOBILIZATION",
        "epoch_end": (datetime.utcnow() + timedelta(seconds=EPOCH_DURATION_SECS)).isoformat(),
        "bypassed": {}, # Tracks which teams bypassed the bot this epoch
        "bots": {},
        "alliances": {},
        "alliance_reqs": {},
        "queued_actions": {},
        "ctf_solved": {}
    }

def load_gs():
    raw = R.get("ot:state")
    if raw:
        try: return json.loads(raw)
        except: pass
    s = _init_state()
    save_gs(s)
    return s

def save_gs(s): R.set("ot:state", json.dumps(s))
def reset_gs(): R.delete("ot:state")

def get_timer_state(gs):
    """Refined Global Timer: Calculates time until epoch end from server state."""
    try:
        end_time = datetime.fromisoformat(gs["epoch_end"])
        remaining = max(0.0, (end_time - datetime.utcnow()).total_seconds())
        # Snap to 10s intervals for cleaner backend sync reporting
        return remaining
    except Exception:
        # Fallback to default if state is corrupted
        return 900.0

def acquire_epoch_lock(epoch_num):
    key = f"ot:epoch_lock_{epoch_num}"
    if R.setnx(key, "1"):
        R.expire(key, 90)
        return True
    return False

def check_admin_auth(attempt_pw):
    """Redis-backed rate limiting for Admin login"""
    lock_key = "ot:admin_lockout"
    if R.get(lock_key):
        return False, "System is temporarily locked due to multiple failed attempts."
    
    if attempt_pw == "overlord":
        R.delete("ot:admin_fail_count")
        return True, "Authenticated"
    
    fails = int(R.get("ot:admin_fail_count") or 0) + 1
    R.set("ot:admin_fail_count", str(fails), ex=3600)
    if fails >= 5:
        R.set(lock_key, "1", ex=300) # 5 min lockout
        return False, "5/5 Failed attempts. Portal locked for 5 minutes."
    return False, f"Invalid Credentials. ({fails}/5)"

def push_ev(kind, msg, team=None):
    ev = {"ts": datetime.utcnow().strftime("%H:%M:%S"), "kind": kind, "msg": msg, "team": team}
    R.lpush("ot:events", json.dumps(ev))
    R.ltrim("ot:events", 0, 199)

def load_evs(limit=30):
    res = R.lrange("ot:events", 0, limit - 1)
    out = []
    for r in res:
        try: out.append(json.loads(r))
        except: pass
    return out

def terr_count(grid, dict_teams=None):
    c = {}
    if dict_teams: c = {t: 0 for t in dict_teams}
    c[""] = 0
    for cell in grid:
        if cell not in c:
            c[cell] = 0
        c[cell] += 1
    return c

class SafeVisitor(ast.NodeVisitor):
    def visit_Import(self, node): raise Exception("Imports are forbidden.")
    def visit_ImportFrom(self, node): raise Exception("Imports are forbidden.")
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in ['eval', 'exec', 'compile', 'open', '__import__', 'getattr', 'setattr', 'delattr', 'input', 'breakpoint', 'dir', 'vars', 'locals', 'globals', 'help']:
                raise Exception(f"Function '{node.func.id}' is forbidden.")
        self.generic_visit(node)
    def visit_Attribute(self, node):
        if node.attr.startswith('__'): raise Exception("Private attribute access is forbidden.")
        self.generic_visit(node)

def run_code_safe(code: str, timeout: int = 5) -> tuple[str, str]:
    try:
        tree = ast.parse(code)
        SafeVisitor().visit(tree)
    except Exception as e:
        return "", f"[SECURITY] {str(e)}"
    
    try:
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout)
        return res.stdout[:3000], res.stderr[:1000]
    except subprocess.TimeoutExpired:
        return "", "[TIMEOUT] "
    except Exception as e:
        return "", str(e)


# ── GAME LOGIC ────────────────────────────────────────────────
def execute_bot(code_str, MT, target_gs, teams_dict):
    """Sandbox evaluates user heuristic code against valid target metadata."""
    from config import get_amoeba_adjacency
    
    alliances = target_gs.get("alliances", {}).get(MT, [])
    grid = target_gs["grid"]
    adj = get_amoeba_adjacency(len(grid))
    
    my_cells = [i for i, owner in enumerate(grid) if owner == MT]
    valid_targets = set()
    for c in my_cells:
        for n in adj.get(c, []):
            if n < len(grid):
                owner = grid[n]
                if owner != MT and owner not in alliances:
                    valid_targets.add(n)
                
    targets_data = []
    for c in valid_targets:
        owner = grid[c]
        targets_data.append({
            "_id": int(c),
            "is_empty": owner == "",
            "owner": owner,
            "owner_hp": int(target_gs["hp"].get(owner, 0)) if owner else 0,
            "owner_ap": int(target_gs["ap"].get(owner, 0)) if owner else 0,
            "owner_territory": sum(1 for x in grid if x == owner) if owner else 0
        })

    t_str = json.dumps(targets_data)
    
    injected_code = f"""
TARGETS = {t_str}
{code_str}

best_score = -999999
best_id = None
try:
    for t in TARGETS:
        s = evaluate_target(t)
        if s is not None and s > best_score:
            best_score = s
            best_id = t['_id']
except Exception as e:
    pass

if best_id is not None:
    print(f"__SYS_BOT_MOVE__ {{best_id}}")
"""
    stdout, stderr = run_code_safe(injected_code, timeout=0.8)
    return stdout.strip(), stderr.strip()


def simulate_epoch(gs):
    """Transition to a new epoch, resolving all moves and bots."""
    from config import EPOCH_DURATION_SECS, ATTACK_COST_AP
    teams = load_teams()
    
    # Trigger epoch switch
    gs["epoch"] += 1
    gs["epoch_end"] = (datetime.utcnow() + timedelta(seconds=EPOCH_DURATION_SECS)).isoformat()
    gs["phase"] = "MANEUVER" # Standard transition
    
    bypassed_teams = gs.get("bypassed", {})
    gs["bypassed"] = {} # clear for next epoch
    if "bots" not in gs: gs["bots"] = {}
    
    queued = gs.get("queued_actions", {})
    gs["queued_actions"] = {}
    
    # 0. Global Economy: Passive AP Regen
    for t in teams:
        gs["ap"][t] = int(gs["ap"].get(t, 0)) + 100

    # 1. Resolve Suspicions
    for actor, action in list(queued.items()):
        if action["action"] == "SUSPICION":
            target = action["target"]
            target_action = queued.get(target)
            if target_action and target_action["action"] == "BACKSTAB" and target_action["target"] == actor:
                damage = 3000
                gs["hp"][target] = max(0, int(gs["hp"].get(target, 0)) - damage)
                push_ev("SYS", f"JUDICIAL DISCOVERY: {actor} caught {target} preparing a backstab! {target} suffers -{damage} HP.", actor)
            else:
                damage = 3000
                gs["hp"][actor] = max(0, int(gs["hp"].get(actor, 0)) - damage)
                push_ev("SYS", f"JUDICIAL FAILURE: {actor} falsely accused {target}. {actor} suffers -{damage} HP.", actor)
            
    # 2. Resolve Backstabs
    for actor, action in list(queued.items()):
        if action["action"] == "BACKSTAB" and gs["hp"].get(actor, 0) > 0:
            target = action["target"]
            if actor in gs["alliances"] and target in gs["alliances"][actor]: gs["alliances"][actor].remove(target)
            if target in gs["alliances"] and actor in gs["alliances"][target]: gs["alliances"][target].remove(actor)
            damage = 3000
            if target in gs["hp"]:
                gs["hp"][target] = max(0, int(gs["hp"][target]) - damage)
                push_ev("ATTACK", f"BETRAYAL! {actor} backstabbed {target} for {damage} HP damage!", actor)

    # 3. Execute Bot for every active team
    for tname, bcode in gs["bots"].items():
        if tname not in bypassed_teams:
            if gs["hp"].get(tname, 0) <= 0: continue
            stdout, err = execute_bot(bcode, tname, gs, teams)
            if "__SYS_BOT_MOVE__" in stdout:
                try:
                    token_part = stdout.split("__SYS_BOT_MOVE__")[1].strip()
                    cell_idx = int(token_part.split()[0])
                    ap = int(gs["ap"].get(tname, 0))
                    
                    # ── VERIFY ADJACENCY (PREVENT BOT SPOOF TELEPORT) ──
                    from config import get_amoeba_adjacency
                    alliances = gs.get("alliances", {}).get(tname, [])
                    adj = get_amoeba_adjacency(len(gs["grid"]))
                    my_cells = [i for i, owner in enumerate(gs["grid"]) if owner == tname]
                    valid_targets = set()
                    for c in my_cells:
                        valid_targets.update([n for n in adj.get(c, []) if n < len(gs["grid"]) and gs["grid"][n] != tname and gs["grid"][n] not in alliances])

                    if ap >= ATTACK_COST_AP and cell_idx in valid_targets:
                        prev = gs["grid"][cell_idx]
                        gs["grid"][cell_idx] = tname
                        gs["ap"][tname] -= ATTACK_COST_AP
                        if prev and prev in gs["hp"]:
                            gs["hp"][prev] = max(0, int(gs["hp"][prev]) - 100)
                        push_ev("ATTACK", f"BOT ({tname}) captured cell {cell_idx}!", tname)
                    else:
                        push_ev("SYS", f"BOT ({tname}) attempted invalid/teleport targeting.", tname)
                except:
                    push_ev("SYS", f"BOT ({tname}) execution failed to parse attack move", tname)
                    
    # 4. Clean up eliminated map territories
    for t, hp in list(gs["hp"].items()):
        if hp <= 0:
            for i in range(len(gs["grid"])):
                if gs["grid"][i] == t:
                    gs["grid"][i] = ""
                    
    # 5. Victory Assessment
    living = [t for t, hp in gs["hp"].items() if hp > 0]
    if gs["epoch"] > 1 and len(teams) > 1:
        if len(living) == 1:
            gs["game_over"] = living[0]
        elif len(living) == 0:
            gs["game_over"] = "DRAW"

    save_gs(gs)
    return gs
