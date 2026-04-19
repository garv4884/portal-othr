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

from db import (
    load_gs, load_evs, terr_count, load_teams, load_users,
    push_ev, save_gs, reset_gs, redis_live, run_code_safe, get_user,
    execute_bot, simulate_epoch, acquire_epoch_lock,
    apply_task_rewards, mark_team_task_done, team_task_cd_remaining
)
from config import (
    TASKS, DIFF_COLOR, EVENT_COLORS, STARTING_HP, STARTING_AP,
    EPOCH_DURATION_SECS, ATTACK_COST_AP, CELL_COLORS, CELL_GLOW,
    TERRAIN_SPECIAL, get_amoeba_adjacency, MONARCH_TASK_PORTAL
)
from styles.theme import get_full_css
from components.header import render_header
from components.sidebar import render_sidebar


def _normalize_answer(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _task_attempt_panel(task: dict, team: str, username: str):
    task_id = task["id"]
    portal = MONARCH_TASK_PORTAL.get(task_id, {})
    drive_url = portal.get("drive_url", "")
    expected_answer = portal.get("answer", "")

    st.markdown(f"### {task['title']}")
    st.markdown(task["desc"])

    if drive_url:
        st.markdown(f"[Open Intel Report (Drive Link)]({drive_url})")
    else:
        st.warning("Intel report is not available for this operation.")

    ans = st.text_input("Breach Signature", key=f"ans_{task_id}", placeholder="Enter Flag")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("AUTHENTICATE", use_container_width=True, key=f"submit_{task_id}"):
            current_gs = load_gs()
            if _normalize_answer(ans) == _normalize_answer(expected_answer):
                apply_task_rewards(current_gs, team, task["pts"], task["title"])
                mark_team_task_done(current_gs, team, task_id)
                save_gs(current_gs)
                st.success("ACCESS GRANTED.")
                st.rerun()
            else:
                current_gs.setdefault("team_task_cooldown", {})[team] = time.time() + 180
                save_gs(current_gs)
                push_ev("TASK", f"FAILED BREACH on {task['title']} by {username}.", team)
                st.error("ACCESS DENIED. LOCKDOWN INITIATED.")
                st.rerun()
    with c2:
        if st.button("ABORT", use_container_width=True, key=f"cancel_{task_id}"):
            st.rerun()


@st.cache_data(ttl=60, show_spinner=False)
def get_bot_preview(bcode, tname, gs_json, teams_json):
    _gs = json.loads(gs_json)
    _t = json.loads(teams_json)
    return execute_bot(bcode, tname, _gs, _t)


def show_war_room():
    # ── Inject Theme ─────────────────────────────────────────
    st.markdown(get_full_css(), unsafe_allow_html=True)

    username = st.session_state.username
    users    = load_users()
    user     = users.get(username, {})
    MT       = user.get("team")
    dn       = user.get("display_name", username)

    if not MT:
        st.warning("You must join a kingdom to access the War Room.")
        if st.button("Go to Kingdom Selection"):
            st.session_state.page = "team_select"
            st.rerun()
        return

    # ── SESSION DEFAULTS ─────────────────────────────────────
    if "active_tab" not in st.session_state: st.session_state.active_tab = "Home"
    if "code_outputs" not in st.session_state: st.session_state.code_outputs = {}

    # ── LOAD DATA ────────────────────────────────────────────
    gs    = load_gs()
    evs   = load_evs(40)
    teams = load_teams()
    tc    = terr_count(gs["grid"], list(teams.keys()))

    from db import get_timer_state
    remaining = get_timer_state(gs)
    
    # Check if epoch rolled over
    if remaining <= 0 and not gs.get("game_over"):
        if acquire_epoch_lock(gs["epoch"]):
            gs = simulate_epoch(gs)
        else:
            time.sleep(1.5)
        st.rerun()

    pct_left  = remaining / EPOCH_DURATION_SECS
    mins_left = int(remaining // 60)
    secs_left = int(remaining % 60)

    # ── METRICS ───────────────────────────────────────────────
    my_hp   = int(gs["hp"].get(MT, 10000))
    my_ap   = int(gs["ap"].get(MT, 0))
    my_terr = tc.get(MT, 0)

    # ── SHARED COMPONENTS (Sidebar & Header) ─────────────────
    render_sidebar(gs, tc, dn, MT, my_hp, my_ap, my_terr, mins_left, secs_left, pct_left, redis_live, teams, users)
    render_header(gs, tc, dn, MT, mins_left, secs_left, pct_left, teams, remaining)

    # ── FORCE REFRESH BUTTON ────────────────────────────────
    c_ref1, c_ref2 = st.columns([5, 1])
    with c_ref2:
        if st.button("🔄 REFRESH", use_container_width=True, help="Force a manual state reload from Redis"):
            st.rerun()

    # ── VICTORY CONDITION ───────────────────────────────────
    if gs.get("game_over"):
        st.markdown(f"<h1>WINNER: {gs['game_over']}</h1>", unsafe_allow_html=True)
        return

    # ── TAB NAVIGATION ──────────────────────────────────────
    tab_names = ["Home", "Tasks Human", "Tasks (Bot)", "Attack Decision Bot", "Strategy Deck"]
    tab_cols  = st.columns(len(tab_names), gap="small")
    for i, tname in enumerate(tab_names):
        with tab_cols[i]:
            btn_cls = "nav-tab-btn active" if st.session_state.active_tab == tname else "nav-tab-btn"
            st.markdown(f'<div class="{btn_cls}"></div>', unsafe_allow_html=True)
            if st.button(tname, key=f"tab_{tname}", use_container_width=True):
                st.session_state.active_tab = tname
                st.rerun()

    active = st.session_state.active_tab
    st.markdown(f"<div style='font-family:ShareTechMono,monospace;font-size:0.55rem;color:var(--dim);margin:12px 0'>► {active.upper()}</div>", unsafe_allow_html=True)

    if gs["hp"].get(MT, 0) <= 0 and active != "Home":
        st.error("Your kingdom has fallen. You can no longer take actions.")
    
    # ─────────────────────────────────────────────────────────────
    # TAB: HOME
    # ─────────────────────────────────────────────────────────────
    elif active == "Home":
        left_col, right_col = st.columns([2.3, 1], gap="large")
        with left_col:
            st.markdown('<div class="sec-lbl">🗺️ BATTLE ZONE · LIVE ARCHITECTURE</div>', unsafe_allow_html=True)
            
            grid_json = json.dumps(gs["grid"])
            team_colors_json = json.dumps({k: v.get("bg", "#0a1a0e") for k,v in teams.items()})
            team_strokes_json = json.dumps({k: v.get("color", "#0a1a0e") for k,v in teams.items()})
            team_meta_json = json.dumps({k: {"hp":gs["hp"].get(k,0),"ap":gs["ap"].get(k,0)} for k in teams.keys()})
            
            from components.panels.organic_grid import get_organic_grid_js
            d3_map_html = get_organic_grid_js(grid_json, team_colors_json, team_strokes_json, team_meta_json, MT)
            components.html(d3_map_html, height=520)

        with right_col:
            st.markdown('<div class="sec-lbl">📡 LIVE DECRYPTIONS</div>', unsafe_allow_html=True)
            st.markdown('<div class="ev-feed">', unsafe_allow_html=True)
            for ev in evs:
                clr = EVENT_COLORS.get(ev["kind"], "#fff")
                st.markdown(f'<div class="ev-item" style="border-left-color:{clr}"><span class="ev-ts">{ev["ts"]}</span> {ev["msg"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TAB: TASKS HUMAN
    # ─────────────────────────────────────────────────────────────
    elif active == "Tasks Human":
        cd_rem = team_task_cd_remaining(gs, MT)
        if cd_rem > 0:
            st.markdown(f'<div class="cd-bar">⏳ TEAM LOCKDOWN: {int(cd_rem//60):02d}:{int(cd_rem%60):02d}</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sec-lbl">🧠 HUMAN INTELLIGENCE · MONARCH MISSIONS</div>', unsafe_allow_html=True)
        tc_cols = st.columns(2, gap="small")
        solved_list = gs.get("ctf_solved", {}).get(MT, [])
        
        for i, task in enumerate(TASKS["monarch"]):
            is_solved = task["id"] in solved_list
            dc = DIFF_COLOR.get(task["diff"], "cyan")
            with tc_cols[i % 2]:
                st.markdown(f"""
                <div class="tc" style="border-top:2px solid {dc}44">
                    <div class="tc-diff" style="background:{dc}18;color:{dc};border:1px solid {dc}44">{task['diff']}</div>
                    <div class="tc-title">{task['title']}</div>
                    <div class="tc-desc">{task['desc']}</div>
                    <div class="tc-pts">+{task['pts']} AP</div>
                </div>
                """, unsafe_allow_html=True)
                if is_solved:
                    st.success("SECURED")
                else:
                    if st.button(f"ATTEMPT {task['id']}", key=f"btn_{task['id']}", use_container_width=True, disabled=cd_rem > 0):
                        _task_attempt_panel(task, MT, username)

    # ─────────────────────────────────────────────────────────────
    # TAB: TASKS (BOT)
    # ─────────────────────────────────────────────────────────────
    elif active == "Tasks (Bot)":
        st.markdown('<div class="sec-lbl">💻 SOVEREIGN · AUTOMATED SUBROUTINES</div>', unsafe_allow_html=True)
        sel_id = st.selectbox("Select Mission", options=["custom"] + [t["id"] for t in TASKS["sovereign"]])
        
        default_code = "# Code here"
        task_obj = None
        if sel_id != "custom":
            task_obj = next(t for t in TASKS["sovereign"] if t["id"] == sel_id)
            default_code = task_obj.get("starter", "")

        user_code = st.text_area("Python Editor", value=default_code, height=250)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("RUN CODE", use_container_width=True):
                so, se = run_code_safe(user_code)
                st.session_state.code_outputs[sel_id] = {"so": so, "se": se}
        with c2:
            if st.button("SUBMIT", use_container_width=True, disabled=sel_id == "custom"):
                so, se = run_code_safe(user_code)
                if not se:
                    # Award rewards immediately as per logic
                    fresh_gs = load_gs()
                    if task_obj["id"] not in fresh_gs.get("ctf_solved", {}).get(MT, []):
                        apply_task_rewards(fresh_gs, MT, task_obj["pts"], task_obj["title"])
                        mark_team_task_done(fresh_gs, MT, task_obj["id"])
                        save_gs(fresh_gs)
                        st.success("Mission complete! AP awarded.")
                else:
                    st.error("Execution failed.")

        if sel_id in st.session_state.code_outputs:
            out = st.session_state.code_outputs[sel_id]
            st.code(out["so"] or out["se"])

    # ─────────────────────────────────────────────────────────────
    # TAB: ATTACK DECISION BOT
    # ─────────────────────────────────────────────────────────────
    elif active == "Attack Decision Bot":
        st.markdown('<div class="sec-lbl">⚙️ HEURISTICS · TARGETING ENGINE</div>', unsafe_allow_html=True)
        default_bot = "def evaluate_target(target):\n    return 100 if target['is_empty'] else 0"
        db_code = gs.get("bots", {}).get(MT, default_bot)
        user_code = st.text_area("Bot Code", value=db_code, height=300)
        
        if st.button("SAVE LOGIC", use_container_width=True):
            fresh_gs = load_gs()
            fresh_gs.setdefault("bots", {})[MT] = user_code
            save_gs(fresh_gs)
            st.success("Logic Synchronized.")

        if st.button("🧪 DRY RUN", use_container_width=True):
            sout, serr = execute_bot(user_code, MT, gs, teams)
            if serr: st.error(serr)
            else: st.success("Syntax Validated.")
            st.code(sout or serr)

        # ── MANUAL BYPASS LOGIC ────────────────────────────────
        if gs.get("bypassed", {}).get(MT):
            st.markdown("---")
            target_cell = st.number_input("Manual Attack Target Cell Index", 0, len(gs["grid"])-1)
            if st.button("🗡️ LAUNCH MANUAL ATTACK (500 AP)", use_container_width=True):
                # Verification logic matches simulate_epoch
                fresh_gs = load_gs()
                ap = int(fresh_gs["ap"].get(MT, 0))
                from config import get_amoeba_adjacency
                adj = get_amoeba_adjacency(len(fresh_gs["grid"]))
                my_cells = [i for i, o in enumerate(fresh_gs["grid"]) if o == MT]
                valid_targets = set()
                for c in my_cells:
                    valid_targets.update([n for n in adj.get(c, []) if n < len(fresh_gs["grid"])])
                
                if ap < ATTACK_COST_AP: st.error("Insufficient AP.")
                elif target_cell not in valid_targets: st.error("Target not adjacent.")
                elif fresh_gs["grid"][target_cell] == MT: st.error("Target already owned.")
                else:
                    target_owner = fresh_gs["grid"][target_cell]
                    fresh_gs["grid"][target_cell] = MT
                    fresh_gs["ap"][MT] -= ATTACK_COST_AP
                    if target_owner and target_owner in fresh_gs["hp"]:
                        fresh_gs["hp"][target_owner] = max(0, int(fresh_gs["hp"][target_owner]) - 100)
                    save_gs(fresh_gs)
                    push_ev("ATTACK", f"MANUAL ({MT}) captured cell {target_cell}!", MT)
                    st.success("Target Captured.")
                    st.rerun()

    # ─────────────────────────────────────────────────────────────
    # TAB: STRATEGY DECK
    # ─────────────────────────────────────────────────────────────
    elif active == "Strategy Deck":
        st.markdown('<div class="sec-lbl">🃏 DECK · POLITICAL MANEUVERS</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        all_teams = [t for t in teams.keys() if t != MT]
        alliances = gs.get("alliances", {}).get(MT, [])
        ally_reqs = gs.get("alliance_reqs", {}).get(MT, [])
        
        with c1:
            st.markdown(f'<div style="background:rgba(0,204,136,0.05); border-top:2px solid #00CC88; padding:15px; border-radius:4px; height:100%"><h4 style="color:#00CC88; margin:0; font-family:Orbitron;">HANDSHAKE</h4><p style="font-size:0.75rem; color:#aaa;">Pact of non-aggression.</p></div>', unsafe_allow_html=True)
            non_allies = [t for t in all_teams if t not in alliances]
            t_ally = st.selectbox("Offer Alliance to:", ["--"] + non_allies)
            if st.button("SEND ALLIANCE REQUEST") and t_ally != "--":
                fresh_gs = load_gs()
                fresh_gs.setdefault("alliance_reqs", {}).setdefault(t_ally, []).append(MT)
                save_gs(fresh_gs)
                st.info("Sent.")
            if ally_reqs:
                for req in ally_reqs:
                    if st.button(f"ACCEPT {req}"):
                        fresh_gs = load_gs()
                        fresh_gs.setdefault("alliances", {}).setdefault(MT, []).append(req)
                        fresh_gs["alliances"].setdefault(req, []).append(MT)
                        fresh_gs["alliance_reqs"][MT].remove(req)
                        save_gs(fresh_gs)
                        push_ev("SYS", f"Alliance forged: {MT} & {req}", MT)
                        st.rerun()
                        
        with c2:
            st.markdown(f'<div style="background:rgba(255,10,50,0.05); border-top:2px solid #FF2244; padding:15px; border-radius:4px; height:100%"><h4 style="color:#FF2244; margin:0; font-family:Orbitron;">BACKSTAB</h4><p style="font-size:0.75rem; color:#aaa;">Betray an ally.</p></div>', unsafe_allow_html=True)
            if alliances:
                t_bs = st.selectbox("Target:", ["--"] + alliances)
                if st.button("QUEUE BACKSTAB") and t_bs != "--":
                    fresh_gs = load_gs()
                    fresh_gs.setdefault("queued_actions", {})[MT] = {"action": "BACKSTAB", "target": t_bs}
                    save_gs(fresh_gs)
                    st.success("Traitor.")
            else: st.info("No allies.")
            
        with c3:
            st.markdown(f'<div style="background:rgba(0,229,255,0.08); border-top:2px solid #00E5FF; padding:15px; border-radius:4px; height:100%"><h4 style="color:#00E5FF; margin:0; font-family:Orbitron;">SUSPICION</h4><p style="font-size:0.75rem; color:#aaa;">Accuse an ally.</p></div>', unsafe_allow_html=True)
            if alliances:
                t_susp = st.selectbox("Suspect:", ["--"] + alliances)
                if st.button("QUEUE SUSPICION") and t_susp != "--":
                    fresh_gs = load_gs()
                    fresh_gs.setdefault("queued_actions", {})[MT] = {"action": "SUSPICION", "target": t_susp}
                    save_gs(fresh_gs)
                    st.success("Judiciary.")
            else: st.info("No allies.")

    # ── CHRONOS SYNC ENGINE (v2.0) ───────────────────────────
    sync_seed = random.random()
    chronos_html = f"""
    <script>
        const raw_r = {remaining};
        function syncClocks() {{
            const win = window.parent;
            if(!win) return;
            if(win._otChronos) clearInterval(win._otChronos);
            let r = Math.floor(raw_r);
            function tick() {{
                const timerIDs = ['ot-global-timer', 'ot-sidebar-timer'];
                timerIDs.forEach(id => {{
                    const el = win.document.getElementById(id);
                    if(el) {{
                        const m = Math.floor(r/60).toString().padStart(2,'0');
                        const s = Math.floor(r%60).toString().padStart(2,'0');
                        el.innerText = m + ':' + s;
                    }}
                }});
                if(r === 0) win.location.reload(); 
                r--;
                if(r < -15) r = -15; 
            }}
            tick();
            win._otChronos = setInterval(tick, 1000);
        }}
        setTimeout(syncClocks, 250);
    </script>
    """
    components.html(chronos_html, height=0)
