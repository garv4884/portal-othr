"""
OVERTHRONE :: _pages/war_room.py
Ultimate 'Cooked' Integration: High-Fidelity JS Sync + D3.js Organic Map + Premium Strategy
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
    push_ev, save_gs, reset_gs, redis_live, run_code_safe, get_user,
    simulate_epoch, expand_territory, run_bot_task
)
from config import (
    TASKS, BOT_TASKS, DIFF_COLOR, EVENT_COLORS, STARTING_HP, STARTING_AP,
    EPOCH_DURATION_SECS, ATTACK_COST_AP, CELL_COLORS, CELL_GLOW,
    TERRAIN_SPECIAL, MONARCH_TASK_PORTAL
)
from styles.theme import get_full_css

# -- HELPERS --------------------------------------------------
def _normalize_answer(value: str) -> str:
    return " ".join((value or "").strip().lower().split())

def _visible_ap(gs, team):
    real = int(gs["ap"].get(team, 0))
    shadow = int(gs.get("shadow_task_ap", {}).get(team, 0))
    return real + shadow

# -- UI COMPONENTS --------------------------------------------
def _mount_live_timer_sync(gs):
    # D3.js powered header timer & progress bar sync
    end_iso = gs["epoch_end"]
    components.html(f"""
        <script>
            const END_MS = Date.parse("{end_iso}");
            const DURATION = {EPOCH_DURATION_SECS};
            const parent = window.parent;
            const doc = parent.document;

            function tick() {{
                const timerVal = doc.getElementById('ot-live-timer');
                const barVal = doc.getElementById('ot-live-bar');
                if(!timerVal || !barVal) return;

                const rem = Math.max(0, Math.floor((END_MS - Date.now()) / 1000));
                const m = String(Math.floor(rem/60)).padStart(2,'0');
                const s = String(rem%60).padStart(2,'0');
                timerVal.textContent = m + ":" + s;
                timerVal.style.color = rem <= 60 ? "#FF2244" : "#FFD700";
                
                const pct = (rem / DURATION) * 100;
                barVal.style.width = pct.toFixed(1) + "%";
            }}
            if(parent.__otTimer) clearInterval(parent.__otTimer);
            tick();
            parent.__otTimer = setInterval(tick, 1000);
        </script>
    """, height=0)

def render_d3_map(gs, teams, MT):
    # The "Cooked" Organic Voronoi Grid
    grid_json = json.dumps(gs["grid"])
    team_colors = json.dumps({k: v.get("bg", "#0a1a0e") for k,v in teams.items()})
    team_strokes = json.dumps({k: v.get("color", "#0099FF") for k,v in teams.items()})
    
    meta_dict = {}
    for t_id, t_data in teams.items():
        meta_dict[t_id] = {
            "hp": gs["hp"].get(t_id, 0),
            "ap": _visible_ap(gs, t_id),
            "terr": gs["grid"].count(t_id),
            "members": len(t_data.get("members", []))
        }
    meta_json = json.dumps(meta_dict)

    d3_html = f"""
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin:0; background:transparent; overflow:hidden; }}
        #map-container {{ width:100%; height:500px; position:relative; }}
        .cell {{ stroke-width:1.5px; transition:0.3s; cursor:pointer; }}
        .cell:hover {{ stroke:#fff; stroke-width:3px; opacity:0.8; }}
        #tooltip {{
            position:absolute; background:rgba(2,10,15,0.95); border:1px solid #D4AF37;
            padding:12px; color:#fff; font-family:'Share Tech Mono', monospace; 
            pointer-events:none; opacity:0; border-radius:4px; z-index:100;
        }}
    </script>
    <div id="map-container">
        <div id="tooltip"></div>
        <div id="d3-anchor"></div>
    </div>
    <script>
        const width = 600, height = 500;
        const svg = d3.select("#d3-anchor").append("svg").attr("viewBox", `0 0 600 500`);
        const g = svg.append("g");

        const grid = {grid_json};
        const colors = {team_colors};
        const strokes = {team_strokes};
        const meta = {meta_json};

        // Standard point generation from config
        const n = 30;
        const points = [];
        const phi = (1 + Math.sqrt(5)) / 2;
        for(let i=0; i<n; i++) {{
            let r = 180 * Math.sqrt((i+0.5)/n);
            let theta = 2 * Math.PI * i / phi;
            points.push([300 + r * Math.cos(theta), 250 + r * Math.sin(theta)]);
        }}

        const delaunay = d3.Delaunay.from(points);
        const voronoi = delaunay.voronoi([0,0,600,500]);

        g.selectAll("path")
            .data(points.map((p,i)=>i))
            .join("path")
            .attr("class", "cell")
            .attr("d", i => voronoi.renderCell(i))
            .attr("fill", i => colors[grid[i]] || "#0a1a0e")
            .attr("stroke", i => strokes[grid[i]] || "#1a3a1a")
            .on("mouseover", (e, i) => {{
                const owner = grid[i];
                let html = `<div style="color:#D4AF37;font-weight:bold;margin-bottom:5px">CELL ${{i}}</div>`;
                if(owner) {{
                    html += `<div style="color:#00E5FF">${{owner}}</div>`;
                    html += `HP: ${{meta[owner].hp}}<br>AP: ${{meta[owner].ap}}`;
                }} else html += "WILDERNESS";
                d3.select("#tooltip").html(html).style("opacity", 1);
            }})
            .on("mousemove", e => {{
                d3.select("#tooltip").style("left", (e.pageX+15)+"px").style("top", (e.pageY-20)+"px");
            }})
            .on("mouseout", () => d3.select("#tooltip").style("opacity", 0));

        g.selectAll("text").data(points).join("text")
            .attr("x", d=>d[0]).attr("y", d=>d[1]).attr("dy","0.3em").attr("text-anchor","middle")
            .attr("fill","rgba(255,255,255,0.6)").style("font-size","10px").text((d,i)=>i);

        svg.call(d3.zoom().on("zoom", e => g.attr("transform", e.transform)));
    </script>
    """
    components.html(d3_html, height=520)

# -- MAIN DASHBOARD -------------------------------------------
def show_war_room():
    st.markdown(get_full_css(), unsafe_allow_html=True)
    username = st.session_state.username
    user = get_user(username)
    MT = user.get("team")
    dn = user.get("display_name", username)

    if not MT:
        st.warning("Kingdom identity not found. Please join a team.")
        return

    # DATA LOAD
    gs = load_gs()
    teams = load_teams()
    evs = load_evs(40)
    tc = terr_count(gs["grid"], list(teams.keys()))

    # EPOCH CHECK
    from db import simulate_epoch
    end_dt = datetime.fromisoformat(gs["epoch_end"])
    remaining = (end_dt - datetime.utcnow()).total_seconds()
    
    if remaining <= 0 and not gs.get("game_over"):
        gs = simulate_epoch(gs)
        st.rerun()

    # AUTOREFRESH
    st_autorefresh(interval=30000 if remaining > 10 else 5000, key="epoch_sync")

    # SIDEBAR
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:1rem 0; border-bottom:1px solid rgba(212,175,55,0.2); margin-bottom:1.5rem">
            <div style="font-family:Orbitron; font-size:1.1rem; font-weight:900; letter-spacing:4px; color:var(--gold)">OVERTHRONE</div>
            <div style="font-family:Share Tech Mono; font-size:0.55rem; letter-spacing:3px; color:var(--dim)">HELIX x ISTE · WAR ROOM OS v5.0</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="sb-title">SOVEREIGN IDENTITY</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-row"><span class="sb-lbl">USER</span><span class="sb-val" style="color:var(--red)">{dn}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-row"><span class="sb-lbl">KINGDOM</span><span class="sb-val" style="color:var(--gold)">{MT}</span></div>', unsafe_allow_html=True)

        my_hp, my_ap = int(gs["hp"].get(MT, 0)), _visible_ap(gs, MT)
        my_terr = gs["grid"].count(MT)
        st.markdown('<div class="sb-title" style="margin-top:1.5rem">BIOMETRICS · LIVE</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-row"><span class="sb-lbl">HEALTH</span><span class="sb-val" style="color:var(--red)">{my_hp:,}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-row"><span class="sb-lbl">RESOURCES</span><span class="sb-val" style="color:var(--cyan)">{my_ap:,} AP</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-row"><span class="sb-lbl">AREA</span><span class="sb-val" style="color:var(--gold)">{my_terr} cells</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="sb-title" style="margin-top:1.5rem">CHRONOS SYNC</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-row"><span class="sb-lbl">EPOCH</span><span class="sb-val">{gs["epoch"]}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-row"><span class="sb-lbl">TIME REMAINING</span><span class="sb-val" id="ot-live-timer" style="color:var(--gold)">--:--</span></div>', unsafe_allow_html=True)

        if st.button("LOGOUT", use_container_width=True):
            st.session_state.logged_in = False; st.rerun()

    # WIN CINEMATIC
    if gs.get("game_over"):
        winner = gs["game_over"]
        st.markdown(f"""
        <div style="background:var(--void); padding:100px 20px; text-align:center; border:1px solid var(--gold); border-radius:10px; box-shadow:0 0 100px rgba(212,175,55,0.2)">
            <h1 style="font-family:Orbitron; color:var(--gold); font-size:3.5rem; letter-spacing:12px">SOVEREIGNTY ACHIEVED</h1>
            <p style="font-family:Share Tech Mono; color:var(--text); font-size:1.5rem">Kingdom {winner} stands alone.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # HEADER
    st.markdown(f"""
    <div class="ot-hdr">
        <div><div class="ot-logo">OVERTHRONE</div><div class="ot-subtitle">WAR ROOM OS v5.0</div></div>
        <div style="text-align:right">
            <div class="ot-epoch-num">EPOCH {gs["epoch"]}</div>
            <div class="ot-epoch-phase">MOBILIZATION</div>
        </div>
    </div>
    <div class="ot-tbar"><div class="ot-tbar-fill" id="ot-live-bar" style="width:100%"></div></div>
    """, unsafe_allow_html=True)
    _mount_live_timer_sync(gs)

    # TABS
    tab_names = ["HOME", "TASKS (HUMAN)", "TASKS (BOT)", "STRATEGY DECK", "LEADERBOARD"]
    if "active_tab" not in st.session_state: st.session_state.active_tab = "HOME"
    t_cols = st.columns(len(tab_names))
    for i, tname in enumerate(tab_names):
        with t_cols[i]:
            active = "active" if st.session_state.active_tab == tname else ""
            if st.button(tname, key=f"nav_{tname}", use_container_width=True):
                st.session_state.active_tab = tname; st.rerun()

    active = st.session_state.active_tab

    # ─────────────────────────────────────────────────────────────
    # HOME
    # ─────────────────────────────────────────────────────────────
    if active == "HOME":
        l_col, r_col = st.columns([2.5, 1], gap="large")
        with l_col:
            render_d3_map(gs, teams, MT)
        with r_col:
            st.markdown('<div class="sec-lbl">📡 LIVE DECRYPTIONS</div>', unsafe_allow_html=True)
            feed = '<div class="ev-feed">'
            for ev in evs:
                clr = EVENT_COLORS.get(ev["kind"], "#fff")
                feed += f'<div class="ev-item" style="border-left-color:{clr}"><span class="ev-ts">{ev["ts"]}</span> {ev["msg"]}</div>'
            feed += '</div>'
            st.markdown(feed, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TASKS (HUMAN)
    # ─────────────────────────────────────────────────────────────
    elif active == "TASKS (HUMAN)":
        st.markdown('<div class="sec-lbl">🧠 HUMAN INTELLIGENCE · MONARCH CTF</div>', unsafe_allow_html=True)
        solved = gs.get("task_done_by_user", {}).get(username, {})
        cols = st.columns(2)
        for i, task in enumerate(TASKS["monarch"]):
            is_done = task["id"] in solved
            dc = DIFF_COLOR.get(task["diff"], "cyan")
            with cols[i % 2]:
                link_html = f'<div style="margin-top:10px;"><a href="{task["link"]}" target="_blank" style="color:var(--gold); text-decoration:none; font-size:0.75rem; border:1px solid var(--gold); padding:4px 10px; border-radius:4px;">📥 DOWNLOAD ATTACHMENT</a></div>' if "link" in task else ""
                st.markdown(f'<div class="tc" style="border-top:2px solid {dc}44"><div class="tc-title">{task["title"]}</div><div class="tc-desc">{task["desc"]}</div>{link_html}<div class="tc-pts">+{task["pts"]} AP</div></div>', unsafe_allow_html=True)
                if is_done: st.success("SECURED")
                else:
                    ans = st.text_input(f"Signal for {task['id']}", key=f"ans_{task['id']}")
                    if st.button(f"AUTHENTICATE {task['id']}", key=f"btn_{task['id']}"):
                        if _normalize_answer(ans) == _normalize_answer(MONARCH_TASK_PORTAL[task["id"]]["answer"]):
                            gs = load_gs()
                            gs.setdefault("task_done_by_user", {}).setdefault(username, {})[task["id"]] = datetime.utcnow().isoformat()
                            gs["ap"][MT] = int(gs["ap"].get(MT, 0)) + task["pts"]
                            save_gs(gs); st.success("ACCESS GRANTED"); st.rerun()
                        else: st.error("ACCESS DENIED")

    # ─────────────────────────────────────────────────────────────
    # TASKS (BOT)
    # ─────────────────────────────────────────────────────────────
    elif active == "TASKS (BOT)":
        st.markdown('<div class="sec-lbl">💻 SOVEREIGN · CATEGORICAL CODING</div>', unsafe_allow_html=True)
        cat = st.selectbox("Category", sorted(list(set(t["category"] for t in BOT_TASKS.values()))))
        t_id = st.selectbox("Mission", [t["id"] for t in BOT_TASKS.values() if t["category"] == cat])
        task = BOT_TASKS[t_id]
        
        st.markdown(f"### {task['title']}")
        st.markdown(task["description"])
        code = st.text_area("Implementation", value=task["template"], height=200)
        
        if st.button("SUBMIT FIRMWARE"):
            gs = load_gs()
            ok, msg = run_bot_task(t_id, code, MT, gs)
            if ok:
                gs["ap"][MT] += task["ap_reward"]
                save_gs(gs); st.success(msg); st.rerun()
            else: st.error(msg)

    # ─────────────────────────────────────────────────────────────
    # STRATEGY DECK
    # ─────────────────────────────────────────────────────────────
    elif active == "STRATEGY DECK":
        st.markdown('<div class="sec-lbl">🃏 ACTION CARDS · STRATEGY DECK</div>', unsafe_allow_html=True)
        all_teams = [t for t in teams.keys() if t != MT]
        alliances = gs.get("alliances", {}).get(MT, [])
        
        # Action Cards
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="tc" style="border-top:2px solid #00CC88"><h4>HANDSHAKE</h4><p>Form Alliance</p></div>', unsafe_allow_html=True)
            t_ally = st.selectbox("Partner", ["--"] + [t for t in all_teams if t not in alliances])
            if st.button("OFFER PACT") and t_ally != "--":
                gs = load_gs(); gs.setdefault("alliance_reqs", {}).setdefault(t_ally, []).append(MT); save_gs(gs); st.success("Sent.")
        
        with c2:
            st.markdown('<div class="tc" style="border-top:2px solid #FF2244"><h4>BACKSTAB</h4><p>Secret Betrayal</p></div>', unsafe_allow_html=True)
            t_bs = st.selectbox("Betray", ["--"] + alliances)
            if st.button("QUEUE BETRAYAL") and t_bs != "--":
                gs = load_gs(); gs.setdefault("queued_actions", {})[MT] = {"action": "BACKSTAB", "target": t_bs}; save_gs(gs); st.success("Queued.")

        with c3:
            st.markdown('<div class="tc" style="border-top:2px solid #00E5FF"><h4>SUSPICION</h4><p>Catch Betrayal</p></div>', unsafe_allow_html=True)
            t_susp = st.selectbox("Verify", ["--"] + alliances)
            if st.button("QUEUE AUDIT") and t_susp != "--":
                gs = load_gs(); gs.setdefault("queued_actions", {})[MT] = {"action": "SUSPICION", "target": t_susp}; save_gs(gs); st.success("Queued.")

        # Attack Queue
        st.markdown('<div class="sec-lbl" style="margin-top:2rem">⚔️ BOMBARDMENT QUEUE</div>', unsafe_allow_html=True)
        q_target = st.selectbox("Target", ["--"] + all_teams)
        q_hits = st.number_input("Hits (500 AP each)", 1, 10, 1)
        if st.button("QUEUE ATTACK") and q_target != "--":
            gs = load_gs(); gs.setdefault("queued_attacks", []).append({"actor": MT, "target": q_target, "hits": q_hits}); save_gs(gs); st.success("Added to Queue.")

        # Expansion
        st.markdown('<div class="sec-lbl" style="margin-top:2rem">🌍 EXPANSION</div>', unsafe_allow_html=True)
        if st.button("EXPAND ADJACENT (150 AP)"):
            gs = load_gs()
            ok, msg = expand_territory(gs, MT)
            if ok: save_gs(gs); st.success(msg); st.rerun()
            else: st.error(msg)

    # ─────────────────────────────────────────────────────────────
    # LEADERBOARD
    # ─────────────────────────────────────────────────────────────
    elif active == "LEADERBOARD":
        st.markdown('<div class="sec-lbl">🏆 KINGDOM RANKINGS · LIVE STANDINGS</div>', unsafe_allow_html=True)
        stats = []
        for tname, tdata in teams.items():
            stats.append({
                "name": tname, "hp": gs["hp"].get(tname, 0), "ap": _visible_ap(gs, tname),
                "terr": gs["grid"].count(tname), "color": tdata.get("color"), "members": len(tdata.get("members", []))
            })
        stats.sort(key=lambda x: (x["terr"], x["hp"]), reverse=True)

        st.markdown('<table class="lb-table">', unsafe_allow_html=True)
        for i, s in enumerate(stats):
            hp_w = min(100, (s["hp"]/STARTING_HP)*100)
            st.markdown(f"""
            <tr class="lb-row">
                <td class="lb-cell lb-rank">#{i+1}</td>
                <td class="lb-cell">
                    <div style="color:{s['color']}; font-family:Orbitron; font-weight:bold">{s['name']}</div>
                    <div style="font-size:0.5rem; color:var(--dim)">{s['members']} MEMBERS</div>
                </td>
                <td class="lb-cell" style="width:200px">
                    <div class="hp-bar-bg"><div class="hp-bar-fill" style="width:{hp_w}%; background:{s['color']}"></div></div>
                    <div style="font-size:0.55rem; color:{s['color']}">{s['hp']:,} HP</div>
                </td>
                <td class="lb-cell" style="text-align:right">
                    <div style="color:var(--gold); font-family:Share Tech Mono">{s['terr']} CELLS</div>
                    <div style="color:var(--cyan); font-family:Share Tech Mono">{s['ap']:,} AP</div>
                </td>
            </tr>
            """, unsafe_allow_html=True)
        st.markdown('</table>', unsafe_allow_html=True)
