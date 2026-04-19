"""
OVERTHRONE :: styles/theme.py
Vibrant neon cyberpunk aesthetic with glowing interfaces.
"""

FONTS = """@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');"""

_CSS = """
*, *::before, *::after { box-sizing: border-box; }
:root {
    --void:#03030a; --panel:#080813; --card:#0c0c1a; --gold:#D4AF37; --goldb:#FFD700;
    --cyan:#00E5FF; --red:#FF2244; --green:#00CC88; --purple:#CC44FF; --dim:#8890b8;
    --muted:#555a84; --text:#dde0ee; --bdim:rgba(255,255,255,0.05); --bgold:rgba(212,175,55,0.25);
}

.stApp {
    background-color:var(--void) !important;
    background-image:
        radial-gradient(ellipse 90% 50% at 50% 0%,rgba(0,150,255,0.07) 0%,transparent 55%),
        radial-gradient(ellipse 70% 60% at 95% 100%,rgba(212,175,55,0.05) 0%,transparent 50%),
        repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(255,255,255,0.012) 3px,rgba(255,255,255,0.012) 4px);
    font-family:'Rajdhani',sans-serif; color:var(--text) !important;
}

#MainMenu, footer, .stDeployButton { display: none !important; }
[data-baseweb="tab-list"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; height: 0 !important; min-height: 0 !important; overflow: visible !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[kind="headerNoPadding"],
[aria-label="Collapse sidebar"],
button[title="Collapse sidebar"] {
    display: none !important;
    opacity: 0 !important;
    pointer-events: none !important;
    visibility: hidden !important;
    width: 0 !important;
}

.block-container { padding: 1rem 1rem 3rem !important; max-width:1700px !important; }
::-webkit-scrollbar { width:3px; height:3px; }
::-webkit-scrollbar-track { background:#06060f; }
::-webkit-scrollbar-thumb { background:var(--gold); border-radius:2px; }

[data-testid="stSidebar"] {
    background:linear-gradient(160deg,#05050f 0%,#09091a 100%) !important;
    border-right:1px solid rgba(212,175,55,0.2) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top:0 !important; }

.stButton > button {
    font-family:'Orbitron',monospace !important; font-size:0.58rem !important;
    letter-spacing:2px !important; text-transform:uppercase !important;
    background:transparent !important; border:1px solid rgba(212,175,55,0.3) !important;
    color:var(--gold) !important; border-radius:2px !important; padding:0.45rem 0.9rem !important;
    width:100%; transition:all 0.2s !important;
}
.stButton > button:hover { background:rgba(212,175,55,0.1) !important; box-shadow:0 0 16px rgba(212,175,55,0.18) !important; color:var(--goldb) !important; }
.stButton > button:disabled { opacity:0.35 !important; cursor:not-allowed !important; }

[data-testid="stTextInput"] input { background:var(--card) !important; border:1px solid rgba(212,175,55,0.25) !important; border-radius:2px !important; color:var(--text) !important; font-family:'Share Tech Mono',monospace !important; font-size:0.8rem !important; }

/* ── HEADER ────────────────────────────────────────────────── */
.ot-hdr { 
    display:flex; align-items:center; justify-content:space-between; padding:0.9rem 1.2rem;
    background:linear-gradient(90deg,rgba(212,175,55,0.05) 0%,transparent 70%);
    border-bottom:1px solid rgba(212,175,55,0.2); margin-bottom:1rem; 
}
.ot-logo { font-family:'Orbitron',monospace; font-size:1.9rem; font-weight:900; letter-spacing:6px;
    background:linear-gradient(135deg,#b8892a 0%,#FFD700 45%,#D4AF37 70%,#FFF5CC 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.ot-subtitle { font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:var(--dim); letter-spacing:3px; margin-top:2px; }
.ot-epoch-box { text-align:right; }
.ot-epoch-num { font-family:'Orbitron',monospace; font-size:1.3rem; font-weight:700; color:var(--gold); line-height:1; }
.ot-epoch-phase { font-family:'Share Tech Mono',monospace; font-size:0.55rem; letter-spacing:3px; color:var(--dim); font-weight:700; }
.ot-tbar { height:2px; background:var(--muted); margin-bottom:1rem; overflow:hidden; }
.ot-tbar-fill { height:100%; background:linear-gradient(90deg,var(--gold),var(--goldb)); box-shadow:0 0 8px var(--gold); transition:width 1s linear; }

/* ── SIDEBAR SECTIONS ──────────────────────────────────────── */
.sb-title { font-family:'Orbitron',monospace; font-size:0.55rem; letter-spacing:4px; color:var(--muted); margin-bottom:0.9rem; text-transform:uppercase; font-weight:700; padding:1.2rem 1rem 0.2rem; border-top:1px solid var(--bdim); }
.sb-row { display:flex; justify-content:space-between; align-items:center; padding:0.4rem 1rem; }
.sb-lbl { font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:var(--dim); text-transform:uppercase; }
.sb-val { font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:var(--text); }

/* ── MAP OVERLAY & TABS ────────────────────────────────────── */
.sec-lbl { font-family:'Orbitron',monospace; font-size:0.55rem; letter-spacing:4px; color:var(--dim); margin-bottom:8px; text-transform:uppercase; border-left:2px solid var(--gold); padding-left:10px; }
.tc { background:var(--card); border:1px solid var(--bdim); border-radius:3px; padding:1.2rem; position:relative; overflow:hidden; transition:all 0.3s; margin-bottom:10px; box-shadow:0 4px 15px rgba(0,0,0,0.3); }
.tc:hover { border-color:rgba(0,229,255,0.3); transform:translateY(-2px); box-shadow:0 0 20px rgba(0,229,255,0.1); }
.tc-title { font-family:'Orbitron',monospace; font-size:0.7rem; letter-spacing:1px; color:var(--gold); margin-bottom:0.5rem; }
.tc-desc { font-size:0.8rem; color:var(--dim); line-height:1.5; margin-bottom:0.8rem; }
.tc-pts { font-family:'Share Tech Mono',monospace; font-size:0.9rem; color:var(--cyan); font-weight:700; }

.nav-tab-btn > button {
    border-color: rgba(212,175,55,0.1) !important;
    background: rgba(0,0,0,0.2) !important;
    color: var(--dim) !important;
}
.nav-tab-btn.active > button {
    border-color: var(--gold) !important;
    background: rgba(212,175,55,0.1) !important;
    color: var(--goldb) !important;
    box-shadow: 0 0 10px rgba(212,175,55,0.2) !important;
}

#ot-live-timer { font-family:'Orbitron'; font-size:1.8rem; font-weight:900; color:var(--red); letter-spacing:2px; }

/* ── EVENT FEED ─────────────────────────────────────────── */
.ev-feed { display:flex; flex-direction:column; gap:6px; max-height:450px; overflow-y:auto; padding-right:5px; }
.ev-item { padding:8px 12px; border-radius:3px; background:rgba(255,255,255,0.02); border-left:3px solid; display:flex; gap:10px; align-items:baseline; font-family:'Share Tech Mono',monospace; font-size:0.75rem; border-bottom:1px solid rgba(255,255,255,0.02); }
.ev-ts { color:var(--muted); font-size:0.6rem; flex-shrink:0; }
"""

def get_full_css() -> str:
    return f"<style>\n{FONTS}\n{_CSS}\n</style>"

def get_auth_css() -> str:
    return f"<style>\n{FONTS}\n{_CSS}\n[data-testid='stSidebar'] {{ display:none !important; }}\n.block-container {{ max-width:600px !important; padding-top:4rem !important; }}\n</style>"
