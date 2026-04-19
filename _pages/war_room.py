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
    push_ev, save_gs, reset_gs, redis_live, run_code_safe, get_user,
    execute_bot, simulate_epoch, acquire_epoch_lock
)
from config import (
    TASKS, DIFF_COLOR, EVENT_COLORS, STARTING_HP, STARTING_AP,
    EPOCH_DURATION_SECS, ATTACK_COST_AP, CELL_COLORS, CELL_GLOW,
    TERRAIN_SPECIAL, get_amoeba_adjacency
)
from styles.theme import get_full_css
from components.header import render_header
from components.sidebar import render_sidebar



@st.cache_data(ttl=60, show_spinner=False)
def get_bot_preview(bcode, tname, gs_json, teams_json):
    _gs = json.loads(gs_json)
    _t = json.loads(teams_json)
    return execute_bot(bcode, tname, _gs, _t)

def show_war_room():
    # ── Inject Theme ─────────────────────────────────────────
    st.markdown(get_full_css(), unsafe_allow_html=True)

    # ── Auto-Refresh Disabled (Transitioned to Event-Driven Smart Ticker) ──
    # st_autorefresh is removed to allow manual and milestone-only syncing.
    d3_map_html = ""
    chronos_html = ""
    
    username = st.session_state.username
    users    = load_users()
    user     = users.get(username, {})
    MT       = user.get("team")
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

    from db import get_timer_state
    remaining = get_timer_state(gs)

    if "bypassed" not in gs: gs["bypassed"] = {}
    
    # Check if epoch rolled over
    if remaining <= 0 and not gs.get("game_over"):
        if acquire_epoch_lock(gs["epoch"]):
            gs = simulate_epoch(gs)
        else:
            time.sleep(1.5) # Await the prime evaluator to finish simulation
        st.rerun()

    pct_left  = remaining / EPOCH_DURATION_SECS
    mins_left = int(remaining // 60)
    secs_left = int(remaining % 60)
    MY_COLOR  = teams.get(MT, {}).get("color", "#0099FF")
    MY_ICON   = teams.get(MT, {}).get("icon", "🔵")

    # ── METRICS ───────────────────────────────────────────────
    my_hp   = int(gs["hp"].get(MT, 10000))
    my_ap   = int(gs["ap"].get(MT, 0))
    my_terr = tc.get(MT, 0)

    # ── SHARED COMPONENTS ────────────────────────────────────
    render_sidebar(gs, tc, dn, MT, my_hp, my_ap, my_terr, mins_left, secs_left, pct_left, redis_live, teams, users)
    render_header(gs, tc, dn, MT, mins_left, secs_left, pct_left, teams, remaining)

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
        
    # ── 2-MINUTE POPUP BOT WARNING ───────────────────────────
    if remaining <= 120 and MT not in gs.get("bypassed", {}) and gs["hp"].get(MT, 0) > 0:
        db_code = gs.get("bots", {}).get(MT, "# Auto-Generated\\nprint('DEFEND')")
        stdout, err = get_bot_preview(db_code, MT, json.dumps(gs), json.dumps(teams))
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
                # Apply penalty with JIT Lock
                fresh_gs = load_gs()
                fresh_gs["ap"][MT] = max(0, int(fresh_gs["ap"].get(MT, 0)) - 150)
                if "bypassed" not in fresh_gs: fresh_gs["bypassed"] = {}
                fresh_gs["bypassed"][MT] = True
                save_gs(fresh_gs)
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
            unclaimed = len(gs["grid"]) - total_claimed
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
                
                const data = {grid_json};
                // D3 Voronoi requires at least 3 nodes mathematically. We peg it to 7 to maintain the organic amoeba aesthetic at start.
                const n = Math.max(7, data.length);
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
                // Safely map points, preventing null errors if geometry array exceeds actual database array
                const pData = points.map((p, i) => ({{p: p, i: i, owner: i < data.length ? data[i] : ""}}));
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
            # Final Polish: Scrollable expanded feed for high-concurrency event
            feed_html = '<div class="ev-feed" style="max-height:400px; overflow-y:auto; padding-right:5px;">'
            for ev in evs[:50]:
                bc = EVENT_COLORS.get(ev.get("kind","SYS"), "#333355")
                feed_html += f'<div class="ev-item" style="border-left-color:{bc}; margin-bottom:4px; padding:4px 8px;"><span class="ev-ts" style="font-size:0.6rem; opacity:0.6;">{ev.get("ts","--:--:--")}</span><span class="ev-msg" style="font-size:0.75rem;">{ev.get("msg","")}</span></div>'
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
    # TASKS HUMAN -> NOW CYBER COMMAND CTF
    # ─────────────────────────────────────────────────────────────
    elif active == "Tasks Human":
        st.markdown('<div class="sec-lbl">🧠 CYBER COMMAND · CAPTURE THE FLAG</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:rgba(0, 229, 255, 0.05);border-left:2px solid #00E5FF;border-radius:2px;padding:8px 12px;margin-bottom:12px;font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:#dde0ee;line-height:1.5;">
            Resolve the target operations. Input the correct Flag (Case-Sensitive) to secure AP.<br>
            Flags format: <code>HELIX{...}</code>. Points are granted once per kingdom.
        </div>
        """, unsafe_allow_html=True)

        if "ctf_solved" not in gs:
            gs["ctf_solved"] = {}

        tc_cols = st.columns(2, gap="small")
        for i, task in enumerate(TASKS["monarch"]):
            tid = task["id"]
            dc = DIFF_COLOR.get(task.get("diff", "EASY"), "#00E5FF")
            
            solved_list = gs["ctf_solved"].get(tid, [])
            is_solved = MT in solved_list
            
            with tc_cols[i % 2]:
                st.markdown(f"""
                <div class="tc" style="border-top:2px solid {dc}44">
                    <div class="tc-diff" style="background:{dc}18;color:{dc};border:1px solid {dc}44">{task.get('diff', '')}</div>
                    <div class="tc-title">{task.get('title', 'Unknown Operation')}</div>
                    <div class="tc-desc">{task.get('desc', '')}</div>
                    <a href="{task.get('link', '#')}" target="_blank" style="color:#00E5FF; text-decoration:none; font-family:'Share Tech Mono'; font-size:0.8rem; border-bottom:1px dashed #00E5FF; display:inline-block; margin-bottom:10px;">🔗 Launch Operation Tracker</a>
                    <div class="tc-pts">+{task.get('pts', 0)} AP Reward</div>
                </div>
                """, unsafe_allow_html=True)
                
                if is_solved:
                    st.markdown("""
                    <div style="background:rgba(0,204,136,0.1); border:1px solid #00CC88; color:#00CC88; text-align:center; padding:5px; font-family:'Orbitron'; letter-spacing:2px; border-radius:3px;">
                        ✅ OPERATION SECURED
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    flag_val = st.text_input("Flag Input", key=f"flag_in_{tid}", label_visibility="collapsed", placeholder="HELIX{...}")
                    if st.button(f"VERIFY FLAG — {task.get('title')}", key=f"btn_flag_{tid}", use_container_width=True):
                        # Final Polish: Case-insensitive and trimmed flag verification
                        if flag_val and flag_val.strip().upper() == task.get("flag", "").upper():
                            fresh_gs = load_gs()
                            if "ctf_solved" not in fresh_gs: fresh_gs["ctf_solved"] = {}
                            if tid not in fresh_gs["ctf_solved"]: fresh_gs["ctf_solved"][tid] = []
                            
                            if MT not in fresh_gs["ctf_solved"][tid]:
                                fresh_gs["ap"][MT] = int(fresh_gs["ap"].get(MT, 0)) + task.get("pts", 0)
                                fresh_gs["ctf_solved"][tid].append(MT)
                                save_gs(fresh_gs)
                                push_ev("TASK", f"Team {MT} cracked CTF '{task.get('title')}'! (+{task.get('pts')} AP)", MT)
                                st.success("ACCESS GRANTED.")
                            else:
                                st.info("Flag already claimed.")
                            st.rerun()
                        else:
                            st.error("ACCESS DENIED. INVALID SIGNATURE.")

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
                verify_token = task_obj.get("verify", "XYZZZZ999")
                
                if verify_token in so:
                    fresh_gs = load_gs()
                    if "ctf_solved" not in fresh_gs: fresh_gs["ctf_solved"] = {}
                    if sel_id not in fresh_gs["ctf_solved"]: fresh_gs["ctf_solved"][sel_id] = []
                    
                    if MT not in fresh_gs["ctf_solved"][sel_id]:
                        fresh_gs["ap"][MT] = int(fresh_gs["ap"].get(MT, 0)) + task_obj["pts"]
                        fresh_gs["ctf_solved"][sel_id].append(MT)
                        save_gs(fresh_gs)
                        push_ev("TASK", f"Team {MT} completed bot challenge '{task_obj['title']}'", MT)
                        st.success("Accepted! AP awarded.")
                    else:
                        st.info("Challenge already passed. No additional AP awarded.")
                else:
                    st.error("Execution succeeded, but output does not match expected result.")
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
            if len(c_code) > 8192:
                st.warning("Subroutine limit exceeded (Max 8KB). Optimization required.")
            else:
                fresh_gs = load_gs()
                if "bots" not in fresh_gs: fresh_gs["bots"] = {}
                fresh_gs["bots"][MT] = c_code
                save_gs(fresh_gs)
        
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
                # Final Polish: Scale attack input to global grid size
                target_cell = st.number_input(f"Target Cell (0-{len(gs['grid'])-1})", 0, len(gs["grid"])-1, 0)
                if st.button("🗡️ LAUNCH MANUAL ATTACK", use_container_width=True):
                    fresh_gs = load_gs()
                    ap = int(fresh_gs["ap"].get(MT, 0))
                    
                    adj = get_amoeba_adjacency(len(fresh_gs["grid"]))
                    my_cells = [i for i, owner in enumerate(fresh_gs["grid"]) if owner == MT]
                    valid_targets = set()
                    for c in my_cells:
                        valid_targets.update([n for n in adj.get(c, []) if n < len(fresh_gs["grid"])])
                        
                    if ap >= ATTACK_COST_AP and target_cell in valid_targets and fresh_gs["grid"][target_cell] != MT:
                        prev = fresh_gs["grid"][target_cell]
                        alliances = fresh_gs.get("alliances", {}).get(MT, [])
                        if prev and prev in alliances:
                            st.error("Protocol violation: Cannot manually bombard an Ally.")
                        else:
                            fresh_gs["grid"][target_cell] = MT
                            fresh_gs["ap"][MT] -= ATTACK_COST_AP
                            if prev and prev in fresh_gs["hp"]:
                                fresh_gs["hp"][prev] = max(0, int(fresh_gs["hp"][prev]) - 100)
                            save_gs(fresh_gs)
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
                fresh_gs = load_gs()
                if "alliance_reqs" not in fresh_gs: fresh_gs["alliance_reqs"] = {}
                if t_ally not in fresh_gs["alliance_reqs"]: fresh_gs["alliance_reqs"][t_ally] = []
                if MT not in fresh_gs["alliance_reqs"][t_ally]:
                    fresh_gs["alliance_reqs"][t_ally].append(MT)
                    save_gs(fresh_gs)
                    push_ev("SYS", f"Team {MT} offered an alliance to {t_ally}.", MT)
                    st.success("Request Sent!")
            
            if ally_reqs:
                st.markdown("<div style='margin-top:10px;font-size:0.8rem;color:#D4AF37'>PENDING REQUESTS</div>", unsafe_allow_html=True)
                for req_team in ally_reqs:
                    if st.button(f"ACCEPT {req_team}", key=f"acc_{req_team}", use_container_width=True):
                        # Make mutual
                        fresh_gs = load_gs()
                        if "alliances" not in fresh_gs: fresh_gs["alliances"] = {}
                        if MT not in fresh_gs["alliances"]: fresh_gs["alliances"][MT] = []
                        if req_team not in fresh_gs["alliances"]: fresh_gs["alliances"][req_team] = []
                        
                        if req_team not in fresh_gs["alliances"][MT]: fresh_gs["alliances"][MT].append(req_team)
                        if MT not in fresh_gs["alliances"][req_team]: fresh_gs["alliances"][req_team].append(MT)
                        
                        if req_team in fresh_gs.get("alliance_reqs", {}).get(MT, []):
                            fresh_gs["alliance_reqs"][MT].remove(req_team)
                        save_gs(fresh_gs)
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
                    fresh_gs = load_gs()
                    if "queued_actions" not in fresh_gs: fresh_gs["queued_actions"] = {}
                    fresh_gs["queued_actions"][MT] = {"action": "BACKSTAB", "target": t_bs}
                    save_gs(fresh_gs)
                    st.success("Backstab Queued!")

            if my_queued and my_queued["action"] == "BACKSTAB":
                st.warning(f"Queued secretly vs: {my_queued['target']}")
                if st.button("Cancel Queue", key="c_bs"):
                    fresh_gs = load_gs()
                    if MT in fresh_gs.get("queued_actions", {}):
                        fresh_gs["queued_actions"].pop(MT)
                        save_gs(fresh_gs)
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
                    fresh_gs = load_gs()
                    if "queued_actions" not in fresh_gs: fresh_gs["queued_actions"] = {}
                    fresh_gs["queued_actions"][MT] = {"action": "SUSPICION", "target": t_susp}
                    save_gs(fresh_gs)
                    st.success("Suspicion Queued!")

            if my_queued and my_queued["action"] == "SUSPICION":
                st.warning(f"Queued vs: {my_queued['target']}")
                if st.button("Cancel Queue", key="c_susp"):
                    fresh_gs = load_gs()
                    if MT in fresh_gs.get("queued_actions", {}):
                        fresh_gs["queued_actions"].pop(MT)
                        save_gs(fresh_gs)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ── GLOBAL CHRONOS SYNC ENGINE ───────────────────────────
    # Hidden component that synchronizes all clocks across the portal
    import random
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
                
                // Milestone Triggers: Snap-to-Server at critical moments
                if(r === 120 || r === 0 || r === -5) {{
                    console.log("CHRONOS: Milestone Triggered @ " + r + "s. Reloading...");
                    win.location.reload(); 
                }}
                
                r--;
                if(r < -20) r = -20; // Prevent runaway negative ticking
            }}
            
            tick();
            win._otChronos = setInterval(tick, 1000);
            console.log("CHRONOS: System Synchronized @ " + raw_r + "s (seed={sync_seed:.4f})");
        }}
        // Slight delay to ensure DOM hydration
        setTimeout(syncClocks, 250);
    </script>
    """
    components.html(chronos_html, height=0)

