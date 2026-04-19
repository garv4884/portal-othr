"""
OVERTHRONE :: _pages/war_room.py
Advanced UI + Heuristic Bots + Blitz Attacks + Multi-Category Missions
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
    simulate_epoch, acquire_epoch_lock, apply_task_rewards, 
    mark_team_task_done, team_task_cd_remaining
)
from config import (
    TASKS, BOT_TASKS, DIFF_COLOR, EVENT_COLORS, STARTING_HP, STARTING_AP,
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
    expected_answer = portal.get("answer", "")

    st.markdown(f"### {task['title']}")
    st.markdown(task["desc"])
    
    if "link" in task:
        st.markdown(f"[🔗 INTEL SOURCE]({task['link']})")

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
                current_gs.setdefault("team_task_cooldown", {})[team] = time.time()
                save_gs(current_gs)
                push_ev("TASK", f"FAILED BREACH: {team} on {task['title']}. Security lockdown active.", team)
                st.error("ACCESS DENIED. KINGDOM LOCKDOWN INITIATED.")
                st.rerun()
    with c2:
        if st.button("ABORT", use_container_width=True, key=f"cancel_{task_id}"):
            st.rerun()

def show_war_room():
    st.markdown(get_full_css(), unsafe_allow_html=True)

    username = st.session_state.username
    users    = load_users()
    user     = users.get(username, {})
    MT       = user.get("team")
    dn       = user.get("display_name", username)

    if not MT:
        st.warning("You must join a kingdom to access the War Room.")
        return

    # -- SESSION STATE --
    if "active_tab" not in st.session_state: st.session_state.active_tab = "Home"
    if "code_outputs" not in st.session_state: st.session_state.code_outputs = {}

    # -- LOAD DATA --
    gs    = load_gs()
    evs   = load_evs(40)
    teams = load_teams()
    tc    = terr_count(gs["grid"], list(teams.keys()))

    from db import get_timer_state
    remaining = get_timer_state(gs)
    
    # Check Epoch Rollover
    if remaining <= 0 and not gs.get("game_over"):
        if acquire_epoch_lock(gs["epoch"]):
            gs = simulate_epoch(gs)
        else:
            time.sleep(1.5)
        st.rerun()

    pct_left  = remaining / EPOCH_DURATION_SECS
    mins_left = int(remaining // 60)
    secs_left = int(remaining % 60)

    my_hp   = int(gs["hp"].get(MT, 10000))
    my_ap   = int(gs["ap"].get(MT, 0))
    my_terr = tc.get(MT, 0)

    # -- RENDER UI --
    render_sidebar(gs, tc, dn, MT, my_hp, my_ap, my_terr, mins_left, secs_left, pct_left, redis_live, teams, users)
    render_header(gs, tc, dn, MT, mins_left, secs_left, pct_left, teams, remaining)

    # Tabs
    tab_names = ["Home", "Tasks Human", "Tasks Bot", "Heuristic Bot", "Strategy Deck"]
    tab_cols  = st.columns(len(tab_names))
    for i, tname in enumerate(tab_names):
        with tab_cols[i]:
            if st.button(tname, key=f"tab_{tname}", use_container_width=True):
                st.session_state.active_tab = tname
                st.rerun()

    active = st.session_state.active_tab
    st.markdown(f"<div style='font-family:ShareTechMono,monospace;font-size:0.6rem;color:var(--dim);margin:10px 0'>► {active.upper()}</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TAB: HOME
    # ─────────────────────────────────────────────────────────────
    if active == "Home":
        l_col, r_col = st.columns([2.5, 1], gap="large")
        with l_col:
            st.markdown('<div class="sec-lbl">🗺️ BATTLE ZONE · LIVE ARCHITECTURE</div>', unsafe_allow_html=True)
            grid_json = json.dumps(gs["grid"])
            team_colors_json = json.dumps({k: v.get("bg", "#0a1a0e") for k,v in teams.items()})
            team_strokes_json = json.dumps({k: v.get("color", "#0a1a0e") for k,v in teams.items()})
            team_meta_json = json.dumps({k: {"hp":gs["hp"].get(k,0),"ap":gs["ap"].get(k,0)} for k in teams.keys()})
            
            from components.panels.organic_grid import get_organic_grid_js
            d3_map_html = get_organic_grid_js(grid_json, team_colors_json, team_strokes_json, team_meta_json, MT)
            components.html(d3_map_html, height=520)

            # BLITZ ATTACK PANEL
            st.markdown('<div class="sec-lbl">🗡️ BLITZ EXECUTION</div>', unsafe_allow_html=True)
            with st.expander("MANUAL BOMBARDMENT (INSTANT CAPTURE)", expanded=True):
                col_i, col_b = st.columns([2, 1])
                target_cell = col_i.number_input("Target Index", 0, len(gs["grid"])-1, key="blitz_idx")
                if col_b.button("LAUNCH BLITZ", use_container_width=True):
                    # Adjacency Logic
                    adj = get_amoeba_adjacency(len(gs["grid"]))
                    my_cells = [i for i, o in enumerate(gs["grid"]) if o == MT]
                    valid = any(target_cell in adj.get(c, []) for c in my_cells)
                    
                    if not valid: st.error("Target not adjacent.")
                    elif gs["ap"].get(MT, 0) < ATTACK_COST_AP: st.error("Insufficient AP.")
                    elif gs["grid"][target_cell] == MT: st.error("Target already claimed.")
                    else:
                        prev_owner = gs["grid"][target_cell]
                        gs["grid"][target_cell] = MT
                        gs["ap"][MT] -= ATTACK_COST_AP
                        if prev_owner and prev_owner in gs["hp"]:
                            gs["hp"][prev_owner] = max(0, int(gs["hp"][prev_owner]) - 100)
                        save_gs(gs)
                        push_ev("ATTACK", f"BLITZ: {MT} bombarded cell {target_cell} (-{ATTACK_COST_AP} AP)", MT)
                        st.success("Target Captured.")
                        st.rerun()

        with r_col:
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
            st.markdown(f'<div class="cd-bar">⏳ KINGDOM LOCKDOWN: {int(cd_rem//60):02d}:{int(cd_rem%60):02d}</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sec-lbl">🧠 HUMAN INTELLIGENCE · MONARCH CTF</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        solved_list = gs.get("ctf_solved", {}).get(MT, [])
        
        for i, task in enumerate(TASKS["monarch"]):
            is_solved = task["id"] in solved_list
            dc = DIFF_COLOR.get(task["diff"], "cyan")
            with cols[i % 2]:
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
                    if st.button(f"ATTEMPT {task['id']}", use_container_width=True, disabled=cd_rem > 0):
                        _task_attempt_panel(task, MT, username)

    # ─────────────────────────────────────────────────────────────
    # TAB: TASKS BOT
    # ─────────────────────────────────────────────────────────────
    elif active == "Tasks Bot":
        st.markdown('<div class="sec-lbl">💻 SOVEREIGN · CATEGORICAL CODING</div>', unsafe_allow_html=True)
        cats = sorted(list(set(t["category"] for t in BOT_TASKS.values())))
        cat = st.selectbox("Category", cats)
        
        c_tasks = [t for t in BOT_TASKS.values() if t["category"] == cat]
        t_id = st.selectbox("Select Mission", [t["id"] for t in c_tasks])
        task = BOT_TASKS[t_id]
        
        st.markdown(f"### {task['title']}")
        st.markdown(task['description'])
        st.markdown(f"**Reward:** {task['ap_reward']} AP | **Difficulty:** {task['difficulty']}")
        
        code = st.text_area("Python Implementation", value=task["template"], height=300)
        
        col_r, col_s = st.columns(2)
        with col_r:
            if st.button("RUN TEST HARNESS", use_container_width=True):
                full_code = code + "\n" + task["test_harness"] + "\nprint(verify_val)"
                so, se = run_code_safe(full_code)
                st.session_state.code_outputs[t_id] = {"so": so, "se": se}
        with col_s:
            if st.button("SUBMIT FIRMWARE", use_container_width=True):
                full_code = code + "\n" + task["test_harness"] + "\nprint(verify_val)"
                so, se = run_code_safe(full_code)
                try:
                    res = float(so.strip()) if "." in so else int(so.strip())
                    if res == task["expected_output"]:
                        gs = load_gs()
                        if t_id not in gs.get("ctf_solved", {}).get(MT, []):
                            apply_task_rewards(gs, MT, task["ap_reward"], task["title"])
                            mark_team_task_done(gs, MT, t_id)
                            save_gs(gs)
                            st.success("Logic Validated. AP Awarded.")
                            st.rerun()
                    else: st.error(f"Logic failure. Expected {task['expected_output']}, got {res}")
                except: st.error("Execution failed or returned invalid data.")

        if t_id in st.session_state.code_outputs:
            out = st.session_state.code_outputs[t_id]
            st.code(out["so"] or out["se"])

    # ─────────────────────────────────────────────────────────────
    # TAB: HEURISTIC BOT
    # ─────────────────────────────────────────────────────────────
    elif active == "Heuristic Bot":
        st.markdown('<div class="sec-lbl">⚙️ HEURISTICS · TARGETING ENGINE</div>', unsafe_allow_html=True)
        default_bot = 'def evaluate_target(target):\n    """\n    target: {\n      "is_empty": bool,\n      "owner": str,\n      "owner_hp": int,\n      "owner_ap": int,\n      "owner_territory": int\n    }\n    """\n    return 0'
        db_code = gs.get("bots", {}).get(MT, default_bot)
        user_code = st.text_area("Bot Code (eval_target)", value=db_code, height=400)
        
        if st.button("SAVE TARGETING LOGIC", use_container_width=True):
            gs = load_gs()
            gs.setdefault("bots", {})[MT] = user_code
            save_gs(gs)
            st.success("Synchronized with Core Interface.")

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
            st.markdown('<div style="background:rgba(0,204,136,0.05); border-top:2px solid #00CC88; padding:15px; border-radius:4px; height:200px"><h4 style="color:#00CC88; margin:0; font-family:Orbitron;">HANDSHAKE</h4><p style="font-size:0.75rem; color:#aaa;">Pact of non-aggression.</p></div>', unsafe_allow_html=True)
            non_allies = [t for t in all_teams if t not in alliances]
            t_ally = st.selectbox("Offer Alliance to:", ["--"] + non_allies)
            if st.button("SEND ALLIANCE REQUEST") and t_ally != "--":
                gs = load_gs()
                gs.setdefault("alliance_reqs", {}).setdefault(t_ally, []).append(MT)
                save_gs(gs)
                st.info("Sent.")
            if ally_reqs:
                for req in ally_reqs:
                    if st.button(f"ACCEPT {req}"):
                        gs = load_gs()
                        gs.setdefault("alliances", {}).setdefault(MT, []).append(req)
                        gs["alliances"].setdefault(req, []).append(MT)
                        gs["alliance_reqs"][MT].remove(req)
                        save_gs(gs)
                        st.rerun()
                        
        with c2:
            st.markdown('<div style="background:rgba(255,10,50,0.05); border-top:2px solid #FF2244; padding:15px; border-radius:4px; height:200px"><h4 style="color:#FF2244; margin:0; font-family:Orbitron;">BACKSTAB</h4><p style="font-size:0.75rem; color:#aaa;">Betray an ally.</p></div>', unsafe_allow_html=True)
            if alliances:
                t_bs = st.selectbox("Target:", ["--"] + alliances)
                if st.button("QUEUE BACKSTAB") and t_bs != "--":
                    gs = load_gs()
                    gs.setdefault("queued_actions", {})[MT] = {"action": "BACKSTAB", "target": t_bs}
                    save_gs(gs)
                    st.success("Traitor.")
            else: st.info("No allies.")
            
        with c3:
            st.markdown('<div style="background:rgba(0,229,255,0.08); border-top:2px solid #00E5FF; padding:15px; border-radius:4px; height:200px"><h4 style="color:#00E5FF; margin:0; font-family:Orbitron;">SUSPICION</h4><p style="font-size:0.75rem; color:#aaa;">Accuse an ally.</p></div>', unsafe_allow_html=True)
            if alliances:
                t_susp = st.selectbox("Suspect:", ["--"] + alliances)
                if st.button("QUEUE SUSPICION") and t_susp != "--":
                    gs = load_gs()
                    gs.setdefault("queued_actions", {})[MT] = {"action": "SUSPICION", "target": t_susp}
                    save_gs(gs)
                    st.success("Judiciary.")
            else: st.info("No allies.")

    # Chronos Sync
    components.html(f"""
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
                if(r < -20) r = -20;
            }}
            tick();
            win._otChronos = setInterval(tick, 1000);
        }}
        setTimeout(syncClocks, 250);
    </script>
    """, height=0)
