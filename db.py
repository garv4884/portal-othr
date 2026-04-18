import json
import redis
import hashlib
import sys
import subprocess
from datetime import datetime, timedelta
import streamlit as st
import redis

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
    def lpush(self, k, *vals):
        if k not in self._lists: self._lists[k] = []
        for v in vals: self._lists[k].insert(0, v)
        return len(self._lists[k])
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
        from mock_redis import MockRedis  # Ensure you have your mock fallback accessible
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
    users = load_users()
    if username in users: return False, "Username exists."
    users[username] = {
        "pw_hash": hash_pw(password),
        "display_name": display_name,
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
    raw = R.get("ot:teams")
    if raw:
        try: return json.loads(raw)
        except: pass
    return {}

def save_teams(t): R.set("ot:teams", json.dumps(t))

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
    
    teams[tname] = {
        "creator": username,
        "join_code": join_code,
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
    grid = [""] * 30
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
        "queued_actions": {}
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

def push_ev(kind, msg, team=None):
    ev = {"ts": datetime.utcnow().strftime("%H:%M:%S"), "kind": kind, "msg": msg, "team": team}
    R.lpush("ot:events", json.dumps(ev))

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

def run_code_safe(code: str, timeout: int = 5) -> tuple[str, str]:
    blocked = ["import os", "import sys", "import subprocess", "open(", "__import__",
               "exec(", "eval(", "compile(", "os.system", "os.popen", "shutil"]
    for b in blocked:
        if b in code: return "", f"[SECURITY] Blocked: '{b}'"
    try:
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout)
        return res.stdout[:3000], res.stderr[:1000]
    except subprocess.TimeoutExpired:
        return "", "[TIMEOUT] "
    except Exception as e:
        return "", str(e)
