import sys
import json
import time
import random
import subprocess
from datetime import datetime, timedelta
import streamlit as st
import redis

# -- CONFIG IMPORTS ------------------------------------------
# Note: we import these to ensure simulate_epoch has access to constants
from config import (
    STARTING_HP, STARTING_AP, EPOCH_DURATION_SECS, 
    ATTACK_COST_AP, TEAM_PALETTE
)

# -- REDIS CONNECTION ----------------------------------------
def get_redis_connection():
    # Production: Use internal fly.io / container address or st.secrets
    url = st.secrets.get("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(url, decode_responses=True)

R = get_redis_connection()

def redis_live():
    try:
        return R.ping()
    except:
        return False

# -- USER MANAGEMENT -----------------------------------------
def load_users():
    raw = R.get("ot:users")
    if raw:
        try:
            return json.loads(raw)
        except:
            pass
    return {}

def save_users(users):
    R.set("ot:users", json.dumps(users))

def get_user(username):
    users = load_users()
    return users.get(username)

# -- TEAM MANAGEMENT -----------------------------------------
def load_teams():
    raw = R.get("ot:teams_meta")
    if raw:
        try:
            return json.loads(raw)
        except:
            pass
    return {}

def save_teams(teams):
    R.set("ot:teams_meta", json.dumps(teams))

def _active_backstabber_for_team(gs, target_team):
    """Returns the name of the kingdom currently queuing a backstab against target_team."""
    queued = gs.get("queued_actions", {})
    for actor, action in queued.items():
        if action.get("action") == "BACKSTAB" and action.get("target") == target_team:
            if gs["hp"].get(actor, 0) > 0:
                return actor
    return None

def create_team(tname, username, join_code=""):
    tname = tname.strip()
    teams = load_teams()
    users = load_users()
    
    if tname in teams:
        return False, "Kingdom name already claimed."
    
    idx = len(teams) % len(TEAM_PALETTE)
    config_col = TEAM_PALETTE[idx]
    
    teams[tname] = {
        "creator": username,
        "join_code": join_code,
        "members": [username],
        "created": datetime.utcnow().isoformat(),
        "color": config_col["color"],
        "bg": config_col["bg"],
        "icon": config_col["icon"]
    }
    save_teams(teams)
    
    if username in users:
        users[username]["team"] = tname
        save_users(users)
    
    gs = load_gs()
    if tname not in gs["hp"]:
        gs["hp"][tname] = STARTING_HP
        gs["ap"][tname] = STARTING_AP
        
        # Random initial spawn
        empty = [i for i, owner in enumerate(gs["grid"]) if not owner]
        if empty:
            cell = random.choice(empty)
            gs["grid"][cell] = tname
        save_gs(gs)
        
    return True, f"Kingdom {tname} established."

# -- GAME STATE ----------------------------------------------
def _init_state():
    return {
        "grid": [""] * 30,
        "hp": {},
        "ap": {},
        "epoch": 1,
        "epoch_end": (datetime.utcnow() + timedelta(seconds=EPOCH_DURATION_SECS)).isoformat(),
        "ctf_solved": {},
        "bypassed": {},
        "alliances": {},
        "alliance_reqs": {},
        "queued_actions": {}
    }

def load_gs():
    raw = R.get("ot:state")
    if raw:
        try:
            return json.loads(raw)
        except:
            pass
    state = _init_state()
    save_gs(state)
    return state

def save_gs(state):
    R.set("ot:state", json.dumps(state))

def reset_gs():
    R.delete("ot:state")
    R.delete("ot:events")

def push_ev(kind, msg, team=None):
    event = {
        "ts": datetime.utcnow().strftime("%H:%M:%S"),
        "kind": kind,
        "msg": msg,
        "team": team
    }
    R.lpush("ot:events", json.dumps(event))
    R.ltrim("ot:events", 0, 99)

def load_evs(limit=40):
    raw = R.lrange("ot:events", 0, limit-1)
    evs = []
    for r in raw:
        try: evs.append(json.loads(r))
        except: pass
    return evs

def terr_count(grid, teams_list):
    counts = {t: 0 for t in teams_list}
    for cell in grid:
        if cell in counts:
            counts[cell] += 1
    return counts

# -- ECONOMICS & TASKS ---------------------------------------
def team_task_cd_remaining(gs, team):
    last_fail = gs.get("team_task_cooldown", {}).get(team, 0)
    elapsed = time.time() - last_fail
    return max(0, 180 - elapsed)

def apply_task_rewards(gs, team, pts, title):
    # Betrayal Interception
    traitor = _active_backstabber_for_team(gs, team)
    if traitor:
        gs["ap"][traitor] = int(gs["ap"].get(traitor, 0)) + pts
        gs.setdefault("shadow_ap", {}).setdefault(team, 0)
        gs["shadow_ap"][team] += pts
        push_ev("BACKSTAB", f"INTERCEPTED: {traitor} stole {pts} AP from {team} during '{title}'!", traitor)
        return

    # Normal Reward Execution
    gs["ap"][team] = int(gs["ap"].get(team, 0)) + pts
    
    # Alliance Points Sharing (Hardik's Portal Logic)
    allies = gs.get("alliances", {}).get(team, [])
    for ally in allies:
        if gs["hp"].get(ally, 0) > 0:
            gs["ap"][ally] = int(gs["ap"].get(ally, 0)) + pts
            
    push_ev("TASK", f"Kingdom {team} secured '{title}'. (+{pts} AP distributed)", team)

def mark_team_task_done(gs, team, task_id):
    solved = gs.setdefault("ctf_solved", {})
    if team not in solved: solved[team] = []
    if task_id not in solved[team]:
        solved[team].append(task_id)

# -- SIMULATION ENGINE ---------------------------------------
def get_timer_state(gs):
    try:
        end_dt = datetime.fromisoformat(gs["epoch_end"])
        diff = (end_dt - datetime.utcnow()).total_seconds()
        return max(0, diff)
    except:
        return 0

def acquire_epoch_lock(epoch_num):
    # Atomic lock to prevent multi-simulation
    key = f"ot:lock:epoch:{epoch_num}"
    return R.set(key, "locked", nx=True, ex=30)

def execute_heuristic_bot(code, tname, gs, teams_meta):
    """
    Evaluates every cell on the map using the team's heuristic logic.
    Returns (target_index, score) for the highest-scoring valid move.
    """
    from config import get_amoeba_adjacency
    adj = get_amoeba_adjacency(len(gs["grid"]))
    my_cells = [i for i, owner in enumerate(gs["grid"]) if owner == tname]
    alliances = gs.get("alliances", {}).get(tname, [])
    
    valid_targets = set()
    for c in my_cells:
        valid_targets.update([n for n in adj.get(c, []) if gs["grid"][n] != tname and gs["grid"][n] not in alliances])

    if not valid_targets:
        return None, 0

    best_idx = None
    best_score = -1e9
    
    # Pre-calculate team territories for the target metadata
    tc = terr_count(gs["grid"], list(teams_meta.keys()))

    for idx in valid_targets:
        target_owner = gs["grid"][idx]
        target_meta = {
            "is_empty": (not target_owner),
            "owner": target_owner if target_owner else "NONE",
            "owner_hp": int(gs["hp"].get(target_owner, 0)) if target_owner else 0,
            "owner_ap": int(gs["ap"].get(target_owner, 0)) if target_owner else 0,
            "owner_territory": tc.get(target_owner, 0) if target_owner else 0
        }
        
        # Inject standard evaluate_target wrapper
        injected_code = f"""
import json
target = {json.dumps(target_meta)}
{code}
try:
    print(evaluate_target(target))
except Exception:
    print(0)
"""
        stdout, stderr = run_code_safe(injected_code, timeout=0.5)
        try:
            score = int(stdout.strip()) if stdout.strip() else 0
            if score > best_score:
                best_score = score
                best_idx = idx
        except:
            continue

    return best_idx, best_score

def simulate_epoch(gs):
    # Complex Rollover Logic with Bot Heuristics
    gs = dict(gs)
    gs["epoch"] = int(gs.get("epoch", 0)) + 1
    gs["epoch_end"] = (datetime.utcnow() + timedelta(seconds=EPOCH_DURATION_SECS)).isoformat()
    
    teams_meta = load_teams()
    bypassed_teams = gs.get("bypassed", {})
    
    # 1. Clear Shadow AP & distribute real rewards from previous betrayed tasks
    gs["shadow_ap"] = {}
    
    # 2. Heuristic Bot Attacks
    from config import ATTACK_COST_AP
    bot_logic = gs.get("bots", {})
    for tname, bcode in bot_logic.items():
        if tname in bypassed_teams: continue
        if gs["hp"].get(tname, 0) <= 0: continue
        
        target_idx, score = execute_heuristic_bot(bcode, tname, gs, teams_meta)
        if target_idx is not None and int(gs["ap"].get(tname, 0)) >= ATTACK_COST_AP:
            target_owner = gs["grid"][target_idx]
            gs["grid"][target_idx] = tname
            gs["ap"][tname] -= ATTACK_COST_AP
            if target_owner and target_owner in gs["hp"]:
                gs["hp"][target_owner] = max(0, int(gs["hp"][target_owner]) - 100)
            push_ev("ATTACK", f"BOT ({tname}) captured cell {target_idx} (Score: {score})", tname)

    # 3. Standard Passive Rollover
    gs["bypassed"] = {}
    gs["queued_actions"] = {}
    for t in gs["hp"]:
        if gs["hp"].get(t, 0) > 0:
            gs["ap"][t] = int(gs["ap"].get(t, 0)) + 150 # Passive tick

    # 4. Fallout Cleanup
    for t, hp in list(gs["hp"].items()):
        if hp <= 0:
            for i in range(len(gs["grid"])):
                if gs["grid"][i] == t:
                    gs["grid"][i] = ""

    save_gs(gs)
    return gs

def run_code_safe(code, timeout=5):
    blocked = ["import os", "import sys", "subprocess", "open(", "exec(", "eval("]
    for b in blocked:
        if b in code: return "", f"[SECURITY] Blocked: {b}"
    try:
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout)
        return res.stdout[:2000], res.stderr[:1000]
    except subprocess.TimeoutExpired:
        return "", "[TIMEOUT]"
    except Exception as e:
        return "", str(e)
