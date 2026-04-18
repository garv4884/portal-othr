"""
OVERTHRONE :: _pages/war_room.py
Neon UI + Grid Map + Automated Attack Bot Execution
"""

import json
import time
import random
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

from db import (
    load_gs, load_evs, terr_count, load_teams, load_users,
    push_ev, save_gs, reset_gs, redis_live, run_code_safe, get_user
)
from config import (
    TASKS, DIFF_COLOR, EVENT_COLORS, STARTING_HP, STARTING_AP,
    EPOCH_DURATION_SECS, ATTACK_COST_AP, CELL_COLORS, CELL_GLOW,
    TERRAIN_SPECIAL, get_amoeba_adjacency
)
from styles.theme import get_full_css


def execute_bot(code_str, MT, target_gs, teams_dict):
    """Sandbox evaluates user heuristic code against valid target metadata."""
    alliances = target_gs.get("alliances", {}).get(MT, [])
    grid = target_gs["grid"]
    adj = get_amoeba_adjacency(len(grid))
    
    my_cells = [i for i, owner in enumerate(grid) if owner == MT]
    valid_targets = set()
    for c in my_cells:
        for n in adj.get(c, []):
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

    import json
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
    stdout, stderr = run_code_safe(injected_code, timeout=2)
    return stdout.strip(), stderr.strip()


def show_war_room():
    # ── Auto-Refresh Timer (Ticks every 2s) ─────────────────
    st_autorefresh(interval=2000, limit=None, key="ot_refresh")
    
    username = st.session_state.username
    user     = get_user(username)
    MT       = user["team"]
    dn       = user.get("display_name", username)

    # ── SESSION DEFAULTS ─────────────────────────────────────
    if "active_tab" not in st.session_state: st.session_state.active_tab = "Home"
    if "cooldown"   not in st.session_state: st.session_state.cooldown   = {}
    if "ws_log"     not in st.session_state: st.session_state.ws_log     = []
    if "code_outputs" not in st.session_state: st.session_state.code_outputs = {}
    if "bot_code"   not in st.session_state: 
        st.session_state.bot_code = "# Auto-Generated Standard Tactics\\n# Output format: ATTACK, <cell_index>\\nprint('DEFEND')"

    # ── LOAD DATA ────────────────────────────────────────────
    gs    = load_gs()
    evs   = load_evs(40)
    teams = load_teams()
    tc    = terr_count(gs["grid"], list(teams.keys()))

    try:
        epoch_end = datetime.fromisoformat(gs["epoch_end"])
        remaining = max(0.0, (epoch_end - datetime.utcnow()).total_seconds())
    except Exception:
        remaining = EPOCH_DURATION_SECS

    if "bypassed" not in gs: gs["bypassed"] = {}
    
    # Check if epoch rolled over
    if remaining <= 0 and not gs.get("game_over"):
        # Trigger epoch switch
        gs["epoch"] += 1
        gs["epoch_end"] = (datetime.utcnow() + timedelta(seconds=EPOCH_DURATION_SECS)).isoformat()
        bypassed_teams = gs["bypassed"]
        gs["bypassed"] = {} # clear for next epoch
        if "bots" not in gs: gs["bots"] = {}
        
        queued = gs.get("queued_actions", {})
        gs["queued_actions"] = {}
        
        # 1. Resolve Suspicions
        for actor, action in list(queued.items()):
            if action["action"] == "SUSPICION":
                target = action["target"]
                target_action = queued.get(target)
                if target_action and target_action["action"] == "BACKSTAB" and target_action["target"] == actor:
                    # caught! target damaged
                    damage = 3000
                    gs["hp"][target] = max(0, int(gs["hp"].get(target, 0)) - damage)
                    push_ev("SYS", f"JUDICIAL DISCOVERY: {actor} caught {target} preparing a backstab! {target} suffers -{damage} HP.", actor)
                else:
                    # false accusation! actor damaged
                    damage = 3000
                    gs["hp"][actor] = max(0, int(gs["hp"].get(actor, 0)) - damage)
                    push_ev("SYS", f"JUDICIAL FAILURE: {actor} falsely accused {target}. {actor} suffers -{damage} HP.", actor)
                
        # 2. Resolve Backstabs
        for actor, action in list(queued.items()):
            if action["action"] == "BACKSTAB" and gs["hp"].get(actor, 0) > 0:
                target = action["target"]
                # Break alliance
                if actor in gs["alliances"] and target in gs["alliances"][actor]: gs["alliances"][actor].remove(target)
                if target in gs["alliances"] and actor in gs["alliances"][target]: gs["alliances"][target].remove(actor)
                
                # massively damage target
                damage = 3000
                if target in gs["hp"]:
                    gs["hp"][target] = max(0, int(gs["hp"][target]) - damage)
                    push_ev("ATTACK", f"BETRAYAL! {actor} backstabbed {target} for {damage} HP damage!", actor)
        
        # 3. Execute Bot for every active team
        for tname, bcode in gs["bots"].items():
            if tname not in bypassed_teams:
                # skip dead teams
                if gs["hp"].get(tname, 0) <= 0: continue
                stdout, err = execute_bot(bcode, tname, gs, teams)
                if "__SYS_BOT_MOVE__" in stdout:
                    try:
                        # Extract the exact ID immediately following the secure token
                        token_part = stdout.split("__SYS_BOT_MOVE__")[1].strip()
                        cell_idx = int(token_part.split()[0])
                        ap = int(gs["ap"].get(tname, 0))
                        if ap >= ATTACK_COST_AP and gs["grid"][cell_idx] != tname:
                            prev = gs["grid"][cell_idx]
                            gs["grid"][cell_idx] = tname
                            gs["ap"][tname] -= ATTACK_COST_AP
                            if prev and prev in gs["hp"]:
                                gs["hp"][prev] = max(0, int(gs["hp"][prev]) - 100)
                            push_ev("ATTACK", f"BOT ({tname}) captured cell {cell_idx}!", tname)
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
        if gs["epoch"] > 1 and len(gs["hp"]) > 1:
            if len(living) == 1:
                gs["game_over"] = living[0]
            elif len(living) == 0:
                gs["game_over"] = "DRAW"

        save_gs(gs)
        st.rerun()

    pct_left  = remaining / EPOCH_DURATION_SECS
    mins_left = int(remaining // 60)
    secs_left = int(remaining % 60)
    MY_COLOR  = teams.get(MT, {}).get("color", "#0099FF")
    MY_ICON   = teams.get(MT, {}).get("icon", "🔵")

    # ── STYLES ───────────────────────────────────────────────
    st.markdown(get_full_css(), unsafe_allow_html=True)

    # ── SIDEBAR ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div class="sb-head">
            <div class="ot-logo" style="font-size:1.1rem;letter-spacing:4px">OVERTHRONE</div>
            <div class="ot-subtitle" style="margin-top:3px">HELIX x ISTE · WAR ROOM OS v5.0</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="sb-section">
            <div class="sb-title">SOVEREIGN IDENTITY</div>
            <div class="sb-row"><span class="sb-lbl">USER</span><span class="sb-val" style="color:{MY_COLOR}">{dn}</span></div>
            <div class="sb-row"><span class="sb-lbl">TEAM</span><span class="sb-val" style="color:{MY_COLOR}">{MY_ICON} {MT}</span></div>
        </div>
        """, unsafe_allow_html=True)

        my_meta = teams.get(MT, {})
        members = my_meta.get("members", [username])
        all_users = load_users()
        member_names = [all_users.get(m, {}).get("display_name", m) for m in members]
        pills = "".join(f'<span class="member-pill">{n}</span>' for n in member_names)
        st.markdown(f'<div class="sb-section"><div class="sb-title">TEAM ROSTER</div>{pills}</div>', unsafe_allow_html=True)

        my_hp   = int(gs["hp"].get(MT, STARTING_HP))
        my_ap   = int(gs["ap"].get(MT, 0))
        my_terr = tc.get(MT, 0)
        hp_p = max(0, my_hp / STARTING_HP)
        ap_p = min(my_ap / float(STARTING_AP*2), 1.0)

        st.markdown(f"""
        <div class="sb-section">
            <div class="sb-title">BIOMETRICS · LIVE</div>
            <div class="sb-row"><span class="sb-lbl">HEALTH POINTS</span><span class="sb-val" style="color:{MY_COLOR}">{my_hp:,}</span></div>
            <div class="mini-bar" style="margin-bottom:8px">
                <div class="mini-bar-f" style="width:{hp_p*100:.0f}%;background:{MY_COLOR};box-shadow:0 0 5px {MY_COLOR}"></div>
            </div>
            <div class="sb-row"><span class="sb-lbl">ATTACK POINTS</span><span class="sb-val" style="color:#00E5FF">{my_ap:,}</span></div>
            <div class="mini-bar" style="margin-bottom:8px">
                <div class="mini-bar-f" style="width:{ap_p*100:.0f}%;background:#00E5FF;box-shadow:0 0 5px #00E5FF"></div>
            </div>
            <div class="sb-row"><span class="sb-lbl">TERRITORY</span><span class="sb-val" style="color:#D4AF37">{my_terr} / 30 cells</span></div>
            <div class="mini-bar"><div class="mini-bar-f" style="width:{my_terr}%;background:#D4AF37"></div></div>
        </div>
        """, unsafe_allow_html=True)

        timer_color = "#FF2244" if remaining <= 60 else "#FFD700"
        st.markdown(f"""
        <div class="sb-section">
            <div class="sb-title">EPOCH STATUS</div>
            <div class="sb-row"><span class="sb-lbl">EPOCH</span><span class="sb-val" style="color:#D4AF37">{gs['epoch']}</span></div>
            <div class="sb-row"><span class="sb-lbl">REMAINING</span><span class="sb-val" style="color:{timer_color};font-weight:700">{mins_left:02d}:{secs_left:02d}</span></div>
            <div class="mini-bar" style="margin-top:6px">
                <div class="mini-bar-f" style="width:{pct_left*100:.0f}%;background:linear-gradient(90deg,#D4AF37,#FFD700)"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="sb-section"><div class="sb-title">NETWORK</div>', unsafe_allow_html=True)
        if st.button("LOGOUT / RECONNECT", use_container_width=True):
            for k in ["logged_in","username","user_data","active_tab","bot_code"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── SIDEBAR TOGGLE SCRIPT (Robust Version) ───────────────
    components.html("""
    <script>
    (function() {
        var d = window.parent.document;
        
        // Prevent multiple hooks
        if (window.parent.__OT_SIDEBAR_HOOKED__) return;
        window.parent.__OT_SIDEBAR_HOOKED__ = true;

        console.log("OVERTHRONE: Sidebar Controller Initialized");

        function toggleSidebar() {
            var sb = d.querySelector('[data-testid="stSidebar"]');
            var isClosed = !sb || sb.getBoundingClientRect().width < 50;
            
            var btn;
            if (isClosed) {
                // Find the "Expand" button
                btn = d.querySelector('[data-testid="collapsedControl"] button') || 
                      d.querySelector('[data-testid="collapsedControl"]');
            } else {
                // Find the "Collapse" button
                btn = d.querySelector('[data-testid="stSidebarCollapseButton"] button') || 
                      d.querySelector('button[kind="headerNoSpacing"]'); // Fallback for some Streamlit versions
            }

            if (btn) {
                console.log("OVERTHRONE: Toggling Sidebar...");
                btn.click();
            } else {
                console.warn("OVERTHRONE: Sidebar toggle button not found");
            }
        }

        // Global listener on parent document handles clicks even if logo is rerendered
        d.addEventListener('click', function(e) {
            var curr = e.target;
            while (curr && curr !== d.body) {
                if (curr.id === 'ot-logo-btn') {
                    e.preventDefault();
                    e.stopPropagation();
                    toggleSidebar();
                    return;
                }
                curr = curr.parentElement;
            }
        }, true);
    })();
    </script>
    """, height=0)

    # ── HEADER ───────────────────────────────────────────────
    st.markdown(f"""
<div class="ot-hdr">
    <div style="display:flex; align-items:center; gap:1.2rem;">
        <div id="ot-logo-btn" style="cursor:pointer; display:flex; align-items:center; gap:12px;" title="Toggle Sidebar">
            <div style="font-size:1.5rem; color:var(--gold); filter:drop-shadow(0 0 5px var(--gold));">☰</div>
            <div class="ot-logo" style="transition: filter 0.3s;" onmouseover="this.style.filter='drop-shadow(0 0 10px rgba(212,175,55,0.8))'" onmouseout="this.style.filter='none'">OVERTHRONE</div>
        </div>
        <div style="height:25px; width:1px; background:rgba(212,175,55,0.25); margin:0 5px"></div>
        <div class="ot-subtitle">HELIX x ISTE · THE ULTIMATE KINGDOM SIMULATION</div>
    </div>
    <div style="display:flex;align-items:center;gap:1.2rem">
        <span class="ot-live-badge">LIVE</span>
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.58rem;color:{MY_COLOR}">
            {MY_ICON} {dn.upper()} · {MT}
        </div>
    </div>
    <div class="ot-epoch-box">
        <div class="ot-epoch-num">EPOCH {gs['epoch']}</div>
        <div class="ot-epoch-phase">{gs['phase']}</div>
    </div>
    <div class="ot-timer" style="color:{timer_color}">{mins_left:02d}:{secs_left:02d}</div>
</div>
<div class="ot-tbar"><div class="ot-tbar-fill" style="width:{pct_left*100:.1f}%"></div></div>
""", unsafe_allow_html=True)

    # ── VICTORY CONDITION DISPLAY ────────────────────────────
    if gs.get("game_over"):
        winner = gs["game_over"]
        title = "SOVEREIGNTY ACHIEVED" if winner != "DRAW" else "MUTUAL DESTRUCTION"
        desc = f"Kingdom {winner} is the sole survivor." if winner != "DRAW" else "No kingdoms survived the final epoch. The realm falls to ruin."
        st.markdown(f"""
        <div style="background:var(--void); border-top:1px solid var(--gold); border-bottom:1px solid var(--gold); padding:80px 20px; text-align:center; box-shadow:0 0 100px rgba(212,175,55,0.2) inset; animation:pulse 3s infinite;">
            <h1 style="font-family:'Orbitron',monospace; color:var(--goldb); margin:0; font-size:4rem; text-shadow:0 0 30px var(--gold); letter-spacing:10px">{title}</h1>
            <p style="font-family:'Share Tech Mono',monospace; color:var(--text); margin-top:20px; font-size:1.5rem;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
        return  # Halt loading normal dashboard
        
    # ── 1-MINUTE POPUP BOT WARNING ───────────────────────────
    if remaining <= 60 and MT not in gs.get("bypassed", {}) and gs["hp"].get(MT, 0) > 0:
        db_code = gs.get("bots", {}).get(MT, "# Auto-Generated\\nprint('DEFEND')")
        stdout, err = execute_bot(db_code, MT, gs, teams)
        plan_msg = stdout if stdout else "(No Output / Formatting Error)"
        if "__SYS_BOT_MOVE__" in plan_msg:
            try:
                cell_id = plan_msg.split("__SYS_BOT_MOVE__")[1].strip().split()[0]
                plan_msg = f"ATTACK CELL {cell_id}"
            except: pass
        st.markdown(f"""
        <div class="warning-popup" style="background:linear-gradient(180deg, rgba(255,34,68,0.2) 0%, rgba(255,34,68,0.05) 100%); border:2px solid #FF2244; box-shadow:0 0 30px rgba(255,34,68,0.2);">
            <div style="display:flex; align-items:center; justify-content:center; gap:15px; margin-bottom:15px;">
                <div style="width:40px; height:2px; background:#FF2244;"></div>
                <h3 style="font-family:'Orbitron',monospace;color:#FF2244;margin:0;letter-spacing:6px;font-size:1.4rem">⚠️ IMMINENT BOT EXECUTION</h3>
                <div style="width:40px; height:2px; background:#FF2244;"></div>
            </div>
            <div style="font-family:'Share Tech Mono',monospace;color:#dde0ee;font-size:1.1rem;margin-bottom:20px; text-shadow: 0 0 10px rgba(221,224,238,0.3);">
                Epoch terminal state reached in <span style="color:#FF2244; font-weight:700;">{int(remaining)}s</span>.<br>
                Subroutine analysis complete. Planned move detected:<br>
                <strong style="color:#00E5FF;font-size:1.4rem;display:block;margin-top:12px; letter-spacing:2px; border:1px solid rgba(0,229,255,0.3); padding:10px; background:rgba(0,229,255,0.05);">{plan_msg}</strong>
            </div>
            <div style="font-size:0.75rem; color:#888; letter-spacing:1px;">USE MANUAL OVERRIDE (BYPASS CARD) TO FREEZE BOT ACTIONS</div>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("🃏 PLAY ATTACK CARD (Bypass Bot) -150 AP", use_container_width=True):
                # Apply penalty
                gs["ap"][MT] = max(0, int(gs["ap"].get(MT, 0)) - 150)
                gs["bypassed"][MT] = True
                save_gs(gs)
                push_ev("SYS", f"Team {MT} utilized manual override override (-150 AP)", MT)
                st.rerun()

    if gs.get("bypassed", {}).get(MT) and gs["hp"].get(MT, 0) > 0:
        st.info("You have bypassed the automated bot phase. Your bot is frozen for this epoch. You may attack manually.")

    # ── MAIN TABS ────────────────────────────────────────────
    tab_names = ["Home", "Tasks Human", "Tasks (Bot)", "Attack Decision Bot", "Strategy Deck"]
    tab_cols  = st.columns(len(tab_names), gap="small")
    for i, tname in enumerate(tab_names):
        with tab_cols[i]:
            btn_cls = "nav-tab-btn active" if st.session_state.active_tab == tname else "nav-tab-btn"
            st.markdown(f'<div class="{btn_cls}"></div>', unsafe_allow_html=True) # Styling hack
            if st.button(tname, key=f"tab_{tname}", use_container_width=True):
                st.session_state.active_tab = tname
                st.rerun()

    active = st.session_state.active_tab
    st.markdown(f"<div style='font-family:ShareTechMono,monospace;font-size:0.55rem;color:var(--dim);margin:12px 0'>► {active.upper()}</div>", unsafe_allow_html=True)

    is_eliminated = gs["hp"].get(MT, 0) <= 0

    if is_eliminated and active != "Home":
        st.markdown(f"""
        <div style="background:rgba(255,10,50,0.1); border:1px solid #FF2244; padding:60px 20px; text-align:center; border-radius:10px; box-shadow:0 0 80px rgba(255,10,50,0.3) inset;">
            <h1 style="font-family:'Orbitron',monospace; color:#FF2244; margin:0; font-size:3rem; text-shadow:0 0 20px #FF2244; letter-spacing:10px">KINGDOM FALLEN</h1>
            <p style="font-family:'Share Tech Mono',monospace; color:#ccc; margin-top:20px; font-size:1.2rem;">Your HP has reached 0. You are permanently eliminated from the war.</p>
        </div>
        """, unsafe_allow_html=True)
    # ─────────────────────────────────────────────────────────────
    # HOME TAB (Grid Map + Comms Feed)
    # ─────────────────────────────────────────────────────────────
    elif active == "Home":
        left_col, right_col = st.columns([2.3, 1], gap="large")

        with left_col:
            total_claimed = sum(1 for c in gs["grid"] if c)
            unclaimed = 30 - total_claimed
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <div style="font-family:'Orbitron',monospace;font-size:0.5rem;letter-spacing:4px;color:#64ff96;text-shadow:0 0 8px #00ff5566">
                    🗺️ BATTLE ZONE · ORGANIC NEON
                </div>
                <div style="display:flex;gap:14px">
                    <span style="font-family:'Orbitron',monospace;font-size:0.52rem;color:#fff">
                        ☠️ {total_claimed} CLAIMED &nbsp;|&nbsp; 🟢 {unclaimed} FREE
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            team_colors_json = json.dumps({k: v.get("bg", "#0a1a0e") for k,v in teams.items()})
            team_strokes_json = json.dumps({k: v.get("color", "#0a150c") for k,v in teams.items()})
            grid_json = json.dumps(gs["grid"])

            team_meta_dict = {}
            for t_id, t_dict in teams.items():
                mems = len(t_dict.get("members", []))
                team_meta_dict[t_id] = {
                    "hp": gs["hp"].get(t_id, 0),
                    "ap": gs["ap"].get(t_id, 0),
                    "terr": sum(1 for x in gs["grid"] if x == t_id),
                    "members": mems
                }
            metadata_json = json.dumps(team_meta_dict)

            d3_map_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/d3-delaunay@6"></script>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Share+Tech+Mono&display=swap');
                body {{ margin: 0; padding: 0; background-color: transparent; }}
                .voronoi-cell {{ stroke-width: 1.5px; transition: fill 0.3s, opacity 0.3s; cursor: crosshair; }}
                .voronoi-cell:hover {{ opacity: 0.8; stroke: #fff !important; stroke-width: 2.5px !important; z-index: 10; }}
                .amoeba-border {{ stroke: rgba(100,255,100,0.3); stroke-width: 2; fill: none; stroke-dasharray: 5,5; filter: drop-shadow(0 0 8px rgba(0,255,100,0.4)); }}
                .map-wrap {{
                    background:linear-gradient(135deg,#020d08 0%,#030f0a 40%,#020a06 100%);
                    border:1px solid rgba(100,255,100,0.15); border-radius:6px;
                    box-shadow:inset 0 0 80px rgba(0,0,0,0.6);
                    position:relative;overflow:hidden;
                    width: 100%; height: 500px;
                }}
                #d3-tooltip {{
                    position: absolute; background: rgba(5, 10, 15, 0.95); border: 1px solid #D4AF37; border-radius: 4px;
                    padding: 10px; color: #fff; font-family: 'Share Tech Mono', monospace; font-size: 12px;
                    pointer-events: none; opacity: 0; transition: opacity 0.1s; z-index: 100; box-shadow: 0 0 15px rgba(0,0,0,0.8);
                }}
                .tt-title {{ font-family: 'Orbitron', monospace; color: #D4AF37; font-size:14px; margin-bottom:5px; border-bottom:1px solid rgba(212,175,55,0.3); padding-bottom:3px;}}
                .tt-row {{ display:flex; justify-content:space-between; width:140px; margin-bottom:2px;}}
                .tt-lbl {{ color: #888; }}
                .tt-val {{ color: #00E5FF; font-weight:700; }}
            </style>
            </head>
            <body>
            <div class="map-wrap">
            <div id="d3-map" style="width: 100%; height: 100%; display: flex; justify-content: center; align-items: center;"></div>
            <div id="d3-tooltip"></div>
            </div>
            <script>
                const width = 600, height = 500;
                const svg = d3.select("#d3-map").append("svg")
                    .attr("viewBox", `0 0 ${{width}} ${{height}}`)
                    .attr("style", "width:100%; height:100%; display:block; padding: 10px;");
                
                const n = 30;
                const points = [];
                const phi = (1 + Math.sqrt(5)) / 2;
                for(let i=0; i<n; i++) {{
                    let r = 180 * Math.sqrt((i+0.5)/n);
                    let theta = 2 * Math.PI * i / phi;
                    let noiseX = (Math.sin(i*123) * 15);
                    let noiseY = (Math.cos(i*321) * 15);
                    points.push([width/2 + r * Math.cos(theta) + noiseX, height/2 + r * Math.sin(theta) + noiseY]);
                }}
                
                const delaunay = d3.Delaunay.from(points);
                const voronoi = delaunay.voronoi([0, 0, width, height]);
                const pData = points.map((p, i) => ({{p: p, i: i}}));
                
                const data = {grid_json};
                const backgrounds = {team_colors_json};
                const strokes = {team_strokes_json};
                const meta = {metadata_json};
                const tooltip = d3.select("#d3-tooltip");
                
                const g = svg.append("g");
                
                g.append("g")
                   .selectAll("path")
                   .data(pData)
                   .join("path")
                   .attr("class", "voronoi-cell")
                   .attr("d", d => voronoi.renderCell(d.i))
                   .attr("fill", d => {{
                       let owner = data[d.i];
                       if(owner && backgrounds[owner]) return backgrounds[owner];
                       return (d.i%3===0) ? "#0a1f0a" : "#0d1a0d";
                   }})
                   .attr("stroke", d => {{
                       let owner = data[d.i];
                       if(owner && strokes[owner]) return strokes[owner];
                       return "#081a08";
                   }})
                   .attr("style", d => {{
                       let owner = data[d.i];
                       if(owner && meta[owner]) {{
                           let hp = meta[owner].hp;
                           let glow = Math.min(25, Math.max(0, (hp - 1000) / 400));
                           let col = strokes[owner] || "#ffffff";
                           return `filter: drop-shadow(0px 0px ${{glow}}px ${{col}});`;
                       }}
                       return "";
                   }})
                   .on("mouseover", (e, d) => {{
                       let owner = data[d.i];
                       let content = `<div class="tt-title">CELL ${{d.i}} · ${{(owner || "WILDERNESS").toUpperCase()}}</div>`;
                       if(owner && meta[owner]) {{
                           let m = meta[owner];
                           content += `<div class="tt-row"><span class="tt-lbl">HP</span><span class="tt-val" style="color:#FF2244">${{m.hp.toLocaleString()}}</span></div>`;
                           content += `<div class="tt-row"><span class="tt-lbl">AP</span><span class="tt-val">${{m.ap.toLocaleString()}}</span></div>`;
                           content += `<div class="tt-row"><span class="tt-lbl">AREA</span><span class="tt-val" style="color:#D4AF37">${{m.terr}}</span></div>`;
                           content += `<div class="tt-row"><span class="tt-lbl">MEMBERS</span><span class="tt-val" style="color:#00CC88">${{m.members}}</span></div>`;
                       }} else {{
                           content += `<div style="text-align:center;color:#888;margin-top:8px;font-style:italic">UNASSIGNED WILDERNESS</div>`;
                       }}
                       tooltip.html(content).style("opacity", 1);
                   }})
                   .on("mousemove", (e) => {{
                       let rect = document.querySelector('.map-wrap').getBoundingClientRect();
                       let mx = e.clientX - rect.left;
                       let my = e.clientY - rect.top;
                       tooltip.style("left", (mx + 15) + "px").style("top", (my - 20) + "px");
                   }})
                   .on("mouseout", () => {{
                       tooltip.style("opacity", 0);
                   }});
                   
                const expandedHull = d3.polygonHull(points.map(p => [p[0] + (p[0]-width/2)*0.16, p[1] + (p[1]-height/2)*0.16]));
                g.append("path")
                   .attr("class", "amoeba-border")
                   .attr("d", "M" + expandedHull.join("L") + "Z");

                // Render cell ids for visibility 
                g.append("g")
                   .selectAll("text")
                   .data(pData)
                   .join("text")
                   .attr("x", d => d.p[0])
                   .attr("y", d => d.p[1])
                   .attr("dy", "0.3em")
                   .attr("text-anchor", "middle")
                   .attr("fill", "rgba(255,255,255,0.85)")
                   .attr("style", "font-family:'Share Tech Mono'; font-size:11px; font-weight:700; pointer-events:none; filter: drop-shadow(0px 1px 3px rgba(0,0,0,1));")
                   .text(d => d.i);
                   
                // Zoom & Pan functionality
                const zoom = d3.zoom()
                    .scaleExtent([0.5, 4])
                    .on("zoom", (e) => {{
                        g.attr("transform", e.transform);
                    }});
                svg.call(zoom);
            </script>
            </body>
            </html>
            """
            
            components.html(d3_map_html, height=520, scrolling=False)

            legend_html = ""
            for tname, tinfo in teams.items():
                terr_pct = tc.get(tname, 0)
                legend_html += f'<div class="legend-item"><div class="legend-dot" style="background:{tinfo.get("color","#555")};box-shadow:0 0 6px {tinfo.get("color","#555")}"></div>{tinfo.get("icon","·")} {tname} <span style="color:{tinfo.get("color","#555")};margin-left:3px">{terr_pct}</span></div>'
            legend_html += f'<div class="legend-item"><div class="legend-dot" style="background:#0a1a0e;border:1px solid #1a3a1a"></div>FREE ZONE ({unclaimed})</div>'

            st.markdown(f"""
            <div class="map-legend">{legend_html}</div>
            """, unsafe_allow_html=True)

        with right_col:
            st.markdown('<div class="sec-lbl">COMMS FEED · LIVE</div>', unsafe_allow_html=True)
            feed_html = '<div class="ev-feed">'
            for ev in evs[:22]:
                bc = EVENT_COLORS.get(ev.get("kind","SYS"), "#333355")
                feed_html += f'<div class="ev-item" style="border-left-color:{bc}"><span class="ev-ts">{ev.get("ts","--:--:--")}</span><span class="ev-msg">{ev.get("msg","")}</span></div>'
            feed_html += '</div>'
            st.markdown(feed_html, unsafe_allow_html=True)
            
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-lbl">ELIMINATION TRACKER</div>', unsafe_allow_html=True)
            ranked_e = sorted(teams.items(), key=lambda x: int(gs["hp"].get(x[0], 0)), reverse=True)
            for tname, tinfo in ranked_e:
                hp = int(gs["hp"].get(tname, STARTING_HP))
                status = "ELIMINATED" if hp <= 0 else "ACTIVE"
                sc = "#FF2244" if hp <= 0 else "#00CC88"
                st.markdown(f"""
                <div class="elim-row">
                    <span style="color:{tinfo.get('color','#fff')}">{tinfo.get('icon','·')} TEAM {tname}</span>
                    <span style="font-family:'Orbitron',monospace;font-size:0.48rem;letter-spacing:2px;color:{sc}">{status}</span>
                </div>
                """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TASKS HUMAN
    # ─────────────────────────────────────────────────────────────
    elif active == "Tasks Human":
        cd_end = st.session_state.cooldown.get(MT, 0)
        cd_rem = max(0.0, cd_end - time.time())
        if cd_rem > 0:
            st.markdown(f'<div class="cd-bar">⏳ TASK COOLDOWN — {int(cd_rem//60):02d}:{int(cd_rem%60):02d} remaining</div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-lbl">🧠 HUMAN TASKS · MANUAL CLAIM</div>', unsafe_allow_html=True)
        tc_cols = st.columns(2, gap="small")
        for i, task in enumerate(TASKS["monarch"]):
            dc = DIFF_COLOR[task["diff"]]
            with tc_cols[i % 2]:
                st.markdown(f"""
                <div class="tc" style="border-top:2px solid {dc}44">
                    <div class="tc-diff" style="background:{dc}18;color:{dc};border:1px solid {dc}44">{task['diff']}</div>
                    <div class="tc-title">{task['title']}</div>
                    <div class="tc-desc">{task['desc']}</div>
                    <div class="tc-pts">+{task['pts']} AP</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"CLAIM +{task['pts']}AP", key=f"task_{task['id']}", use_container_width=True, disabled=(cd_rem > 0)):
                    if random.random() < 0.15:
                        st.session_state.cooldown[MT] = time.time() + 900
                        push_ev("TASK", f"Task FAILED — Team {MT} entering cooldown", MT)
                        st.error("Failed! 15-min cooldown.")
                    else:
                        gs["ap"][MT] = int(gs["ap"].get(MT, 0)) + task["pts"]
                        save_gs(gs)
                        push_ev("TASK", f"Team {MT} completed '{task['title']}' +{task['pts']} AP", MT)
                        st.success(f"+{task['pts']} AP earned!")
                    st.rerun()

    # ─────────────────────────────────────────────────────────────
    # TASKS BOT (Code editor)
    # ─────────────────────────────────────────────────────────────
    elif active == "Tasks (Bot)":
        st.markdown('<div class="sec-lbl">💻 BOT TASKS · PYTHON CHALLENGES</div>', unsafe_allow_html=True)
        sov_task_names = {t["id"]: t["title"] for t in TASKS["sovereign"]}
        sel_id = st.selectbox(
            "Load task template",
            options=["custom"] + [t["id"] for t in TASKS["sovereign"]],
            format_func=lambda x: "— Scratchpad —" if x == "custom" else sov_task_names[x],
            key="bot_task_sel"
        )
        
        default_code = "# Scratchpad\nprint('Hello World')"
        if sel_id != "custom":
            task_obj = next((t for t in TASKS["sovereign"] if t["id"] == sel_id), None)
            if task_obj: default_code = task_obj.get("starter", default_code)

        code_key = f"b_code_{sel_id}"
        if code_key not in st.session_state: st.session_state[code_key] = default_code

        user_code = st.text_area("Code Editor", value=st.session_state[code_key], height=280, key=f"b_editor_{sel_id}", label_visibility="collapsed")
        st.session_state[code_key] = user_code

        r_col, s_col = st.columns([1, 1], gap="small")
        with r_col: run_c = st.button("▶ RUN", key="b_run", use_container_width=True)
        with s_col: sub_c = st.button("✓ SUBMIT FOR AP", key="b_submit", use_container_width=True, disabled=(sel_id=="custom"))

        out_key = f"b_out_{sel_id}"
        if run_c:
            so, se = run_code_safe(user_code)
            st.session_state.code_outputs[out_key] = {"stdout":so, "stderr":se, "ts": datetime.utcnow().strftime("%H:%M:%S")}
        if sub_c and sel_id != "custom":
            so, se = run_code_safe(user_code)
            st.session_state.code_outputs[out_key] = {"stdout":so, "stderr":se, "ts": datetime.utcnow().strftime("%H:%M:%S")}
            if not se:
                task_obj = next(t for t in TASKS["sovereign"] if t["id"] == sel_id)
                gs["ap"][MT] = int(gs["ap"].get(MT, 0)) + task_obj["pts"]
                save_gs(gs)
                push_ev("TASK", f"Team {MT} completed bot challenge '{task_obj['title']}'", MT)
                st.success("Accepted! AP awarded.")
            else:
                st.error("Errors detected.")

        out = st.session_state.code_outputs.get(out_key)
        if out:
            out_html = f'<div class="code-term"><div style="color:#555">RUN @ {out["ts"]}</div>'
            if out["stdout"]: out_html += f'<div class="stdout">{out["stdout"]}</div>'
            if out["stderr"]: out_html += f'<div class="stderr">{out["stderr"]}</div>'
            if not out["stdout"] and not out["stderr"]: out_html += '<div class="ok">✓ No output</div>'
            out_html += '</div>'
            st.markdown(out_html, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # ATTACK DECISION BOT
    # ─────────────────────────────────────────────────────────────
    elif active == "Attack Decision Bot":
        st.markdown('<div class="sec-lbl">⚙️ AUTOMATION LOGIC · HEURISTICS ENGINE</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:rgba(212,175,55,0.06);border-left:2px solid #D4AF37;border-radius:2px;padding:8px 12px;margin-bottom:12px;font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:#dde0ee;line-height:1.5;">
            Configure the logic your bot executes at the end of every epoch (5 min).<br>
            The backend engine passes an anonymized <code>target</code> dict to your <code>evaluate_target(target)</code> function.<br>
            Your script must return an integer score. The engine attacks the target with the highest score.
        </div>
        """, unsafe_allow_html=True)
        
        if "bots" not in gs: gs["bots"] = {}
        default_bot = '''def evaluate_target(target):
    """
    target dictionary looks like:
    {
      "is_empty": bool,
      "owner": str,
      "owner_hp": int,
      "owner_ap": int,
      "owner_territory": int
    }
    """
    score = 0
    if target["is_empty"]:
        score += 50
    elif target["owner_hp"] < 2000:
        score += 100
        
    return score
'''
        db_code = gs["bots"].get(MT, default_bot)
        
        c_code = st.text_area("Bot Code", value=db_code, height=280, key="decision_bot_editor", label_visibility="collapsed")
        
        if c_code != db_code:
            gs["bots"][MT] = c_code
            save_gs(gs)
        
        col_test, col_man = st.columns(2)
        with col_test:
            if st.button("🧪 DRY RUN LOGIC", use_container_width=True):
                sout, serr = execute_bot(c_code, MT, gs, teams)
                if serr:
                    st.error(f"Logic Error: {serr}")
                else:
                    if "__SYS_BOT_MOVE__" in sout:
                        try:
                            tid = sout.split("__SYS_BOT_MOVE__")[1].strip().split()[0]
                            st.success(f"✔️ Valid Attack Target Evaluated: Cell {tid}")
                        except:
                            st.warning("⚠️ Invalid return target formatting.")
                    else:
                        st.info(f"Bot Output: {sout or 'None'}")
        
        with col_man:
            if gs.get("bypassed", {}).get(MT):
                st.markdown("<div style='text-align:center;padding:5px;font-family:Share Tech Mono;color:#00E5FF'>Bypass Active — Manual Mode Unlocked</div>", unsafe_allow_html=True)
                target_cell = st.number_input("Target Cell (0-29)", 0, 29, 0)
                if st.button("🗡️ LAUNCH MANUAL ATTACK", use_container_width=True):
                    ap = int(gs["ap"].get(MT, 0))
                    
                    adj = get_amoeba_adjacency(len(gs["grid"]))
                    my_cells = [i for i, owner in enumerate(gs["grid"]) if owner == MT]
                    valid_targets = set()
                    for c in my_cells:
                        valid_targets.update(adj.get(c, []))
                        
                    if ap >= ATTACK_COST_AP and target_cell in valid_targets and gs["grid"][target_cell] != MT:
                        prev = gs["grid"][target_cell]
                        gs["grid"][target_cell] = MT
                        gs["ap"][MT] -= ATTACK_COST_AP
                        if prev and prev in gs["hp"]:
                            gs["hp"][prev] = max(0, int(gs["hp"][prev]) - 100)
                        save_gs(gs)
                        push_ev("ATTACK", f"MANUAL ({MT}) captured cell {target_cell}!", MT)
                        st.success(f"Captured {target_cell}!")
                    else:
                        st.error("Invalid Target or Insufficient AP.")

    # ─────────────────────────────────────────────────────────────
    # STRATEGY DECK
    # ─────────────────────────────────────────────────────────────
    elif active == "Strategy Deck":
        st.markdown('<div class="sec-lbl">🃏 ACTION CARDS · STRATEGY DECK</div>', unsafe_allow_html=True)
        
        all_teams = [t for t in teams.keys() if t != MT]
        alliances = gs.get("alliances", {}).get(MT, [])
        ally_reqs = gs.get("alliance_reqs", {}).get(MT, [])
        queued_actions = gs.get("queued_actions", {})
        my_queued = queued_actions.get(MT, None)
        
        c1, c2, c3 = st.columns(3)
        
        # 1. Alliance Card
        with c1:
            st.markdown("""
            <div style="background:rgba(0, 204, 136, 0.05);border-top:2px solid #00CC88;padding:10px;height:100%">
            <h4 style="color:#00CC88;margin:0 0 10px 0;font-family:Orbitron">HANDSHAKE</h4>
            <div style="font-size:0.75rem;margin-bottom:10px;color:#aaa">Form a Non-Aggression Pact. Bots will ignore allied cells.</div>
            <hr style="border-color:#00CC8844">
            """, unsafe_allow_html=True)
            non_allies = [t for t in all_teams if t not in alliances]
            t_ally = st.selectbox("Offer Alliance to:", ["--"] + non_allies, key="ally_sel", label_visibility="collapsed")
            if st.button("SEND ALLIANCE REQUEST", use_container_width=True) and t_ally != "--":
                if "alliance_reqs" not in gs: gs["alliance_reqs"] = {}
                if t_ally not in gs["alliance_reqs"]: gs["alliance_reqs"][t_ally] = []
                if MT not in gs["alliance_reqs"][t_ally]:
                    gs["alliance_reqs"][t_ally].append(MT)
                    save_gs(gs)
                    push_ev("SYS", f"Team {MT} offered an alliance to {t_ally}.", MT)
                    st.success("Request Sent!")
            
            if ally_reqs:
                st.markdown("<div style='margin-top:10px;font-size:0.8rem;color:#D4AF37'>PENDING REQUESTS</div>", unsafe_allow_html=True)
                for req_team in ally_reqs:
                    if st.button(f"ACCEPT {req_team}", key=f"acc_{req_team}", use_container_width=True):
                        # Make mutual
                        if "alliances" not in gs: gs["alliances"] = {}
                        if MT not in gs["alliances"]: gs["alliances"][MT] = []
                        if req_team not in gs["alliances"]: gs["alliances"][req_team] = []
                        
                        gs["alliances"][MT].append(req_team)
                        gs["alliances"][req_team].append(MT)
                        
                        gs["alliance_reqs"][MT].remove(req_team)
                        save_gs(gs)
                        push_ev("SYS", f"Team {MT} and {req_team} forged an Alliance!", MT)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # 2. Backstab Card
        with c2:
            st.markdown("""
            <div style="background:rgba(255, 34, 68, 0.05);border-top:2px solid #FF2244;padding:10px;height:100%">
            <h4 style="color:#FF2244;margin:0 0 10px 0;font-family:Orbitron">BACKSTAB</h4>
            <div style="font-size:0.75rem;margin-bottom:10px;color:#aaa">Secretly override Alliance protection for the upcoming epoch rollover. Deals massive damage.</div>
            <hr style="border-color:#FF224444">
            """, unsafe_allow_html=True)
            if not alliances:
                st.info("You have no alliances.")
            else:
                t_bs = st.selectbox("Target Ally:", ["--"] + alliances, key="bs_sel", label_visibility="collapsed")
                if st.button("QUEUE BACKSTAB", use_container_width=True) and t_bs != "--":
                    if "queued_actions" not in gs: gs["queued_actions"] = {}
                    gs["queued_actions"][MT] = {"action": "BACKSTAB", "target": t_bs}
                    save_gs(gs)
                    st.success("Backstab Queued!")

            if my_queued and my_queued["action"] == "BACKSTAB":
                st.warning(f"Queued secretly vs: {my_queued['target']}")
                if st.button("Cancel Queue", key="c_bs"):
                    gs["queued_actions"].pop(MT)
                    save_gs(gs)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # 3. Suspicion Card
        with c3:
            st.markdown("""
            <div style="background:rgba(0, 229, 255, 0.05);border-top:2px solid #00E5FF;padding:10px;height:100%">
            <h4 style="color:#00E5FF;margin:0 0 10px 0;font-family:Orbitron">SUSPICION</h4>
            <div style="font-size:0.75rem;margin-bottom:10px;color:#aaa">Investigate an ally. Resolves at rollover. Traitors are eliminated. False accusations eliminate YOU.</div>
            <hr style="border-color:#00E5FF44">
            """, unsafe_allow_html=True)
            if not alliances:
                st.info("You have no alliances.")
            else:
                t_susp = st.selectbox("Suspect Ally:", ["--"] + alliances, key="susp_sel", label_visibility="collapsed")
                if st.button("QUEUE SUSPICION", use_container_width=True) and t_susp != "--":
                    if "queued_actions" not in gs: gs["queued_actions"] = {}
                    gs["queued_actions"][MT] = {"action": "SUSPICION", "target": t_susp}
                    save_gs(gs)
                    st.success("Suspicion Queued!")

            if my_queued and my_queued["action"] == "SUSPICION":
                st.warning(f"Queued vs: {my_queued['target']}")
                if st.button("Cancel Queue", key="c_susp"):
                    gs["queued_actions"].pop(MT)
                    save_gs(gs)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

