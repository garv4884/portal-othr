"""
OVERTHRONE :: components/sidebar.py
Premium sidebar: identity, biometrics, epoch timer, quick actions.
"""

import streamlit as st
from db import push_ev, reset_gs, save_gs, load_teams, load_users, simulate_epoch
from config import STARTING_HP


def render_sidebar(gs, tc, dn, MT, my_hp, my_ap, my_terr,
                   mins_left, secs_left, pct_left, redis_live, teams_meta, all_users):
    my_meta    = teams_meta.get(MT, {})
    MY_COLOR   = my_meta.get("color", "#00E5FF")
    hp_pct     = max(0.0, my_hp / STARTING_HP)
    ap_pct     = min(my_ap / 3000, 1.0)
    hp_col     = "#FF2244" if my_hp < 1500 else ("#FFB800" if my_hp < 3000 else MY_COLOR)

    with st.sidebar:
        st.markdown("""
        <img src="dummy" style="display:none;" onerror="if(!window._otTgl){{window._otTgl=1;document.addEventListener('click',e=>{{let c=e.target;while(c&&c!==document.body){{if(c.id==='ot-logo-btn'||c.id==='sticky-sidebar-toggle'){{e.preventDefault();e.stopPropagation();let o=document.querySelector('[data-testid=\\'collapsedControl\\']');let x=document.querySelector('[data-testid=\\'stSidebarCollapseButton\\']');if(x&&window.getComputedStyle(x).display!=='none')x.dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true}}));else if(o)o.dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true}}));return;}}c=c.parentElement;}}}},true);}}">
        <div class="sb-head">
            <div id="ot-logo-btn" style="cursor:pointer; display:flex; align-items:center; gap:12px;" title="Toggle Sidebar">
                <div style="font-size:1.2rem; color:#D4AF37; filter:drop-shadow(0 0 5px #D4AF37);">☰</div>
                <div style="font-family:'Orbitron',monospace;font-size:1.05rem;font-weight:900;
                    letter-spacing:5px;background:linear-gradient(135deg,#8a6010,#FFD700,#D4AF37);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                    OVERTHRONE
                </div>
            </div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.5rem;
                color:#444;letter-spacing:3px;margin-top:4px; padding-left: 28px;">
                HELIX × ISTE · WAR ROOM OS v5
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Sovereign Identity ────────────────────────────────
        my_meta      = teams_meta.get(MT, {})
        members      = my_meta.get("members", [st.session_state.username])
        member_names = [all_users.get(m, {}).get("display_name", m) for m in members]
        pills = "".join(f'<span class="member-pill">{n}</span>' for n in member_names)

        st.markdown(f"""
        <div class="sb-section">
            <div class="sb-title">SOVEREIGN IDENTITY</div>
            <div class="sb-row">
                <span class="sb-lbl">HANDLE</span>
                <span class="sb-val" style="color:{MY_COLOR}">{dn}</span>
            </div>
            <div class="sb-row">
                <span class="sb-lbl">KINGDOM</span>
                <span class="sb-val" style="color:{MY_COLOR}">{my_meta.get('icon', '👑')} {MT}</span>
            </div>
        </div>
        <div class="sb-section">
            <div class="sb-title">TEAM ROSTER</div>
            {pills}
        </div>
        """, unsafe_allow_html=True)

        # ── Biometrics ────────────────────────────────────────
        st.markdown(f"""
        <div class="sb-section">
            <div class="sb-title">COMBAT METRICS · LIVE</div>
            <div class="sb-row">
                <span class="sb-lbl">HEALTH</span>
                <span class="sb-val" style="color:{hp_col}">{my_hp:,} HP</span>
            </div>
            <div class="mini-bar" style="margin-bottom:10px">
                <div class="mini-bar-f" style="width:{hp_pct*100:.0f}%;background:{hp_col};box-shadow:0 0 6px {hp_col}88"></div>
            </div>
            <div class="sb-row">
                <span class="sb-lbl">ATTACK PTS</span>
                <span class="sb-val" style="color:#00E5FF">{my_ap:,} AP</span>
            </div>
            <div class="mini-bar" style="margin-bottom:10px">
                <div class="mini-bar-f" style="width:{ap_pct*100:.0f}%;background:#00E5FF;box-shadow:0 0 5px #00E5FF66"></div>
            </div>
            <div class="sb-row">
                <span class="sb-lbl">TERRITORY</span>
                <span class="sb-val" style="color:#D4AF37">{my_terr} / 100</span>
            </div>
            <div class="mini-bar">
                <div class="mini-bar-f" style="width:{my_terr}%;background:linear-gradient(90deg,#D4AF37,#FFD700)"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Epoch ─────────────────────────────────────────────
        timer_color = "#FF2244" if mins_left < 3 else ("#FFB800" if mins_left < 7 else "#FFD700")
        st.markdown(f"""
        <div class="sb-section">
            <div class="sb-title">EPOCH STATUS</div>
            <div class="sb-row">
                <span class="sb-lbl">EPOCH #</span>
                <span class="sb-val" style="color:#D4AF37;font-weight:700">{gs['epoch']}</span>
            </div>
            <div class="sb-row">
                <span class="sb-lbl">PHASE</span>
                <span class="sb-val" style="color:#00E5FF;font-size:0.58rem;letter-spacing:1px">{gs['phase']}</span>
            </div>
            <div class="sb-row" style="margin-top:6px">
                <span class="sb-lbl">REMAINING</span>
                <span style="font-family:'Orbitron',monospace;font-size:1rem;font-weight:700;
                    color:{timer_color};filter:drop-shadow(0 0 6px {timer_color}55)">
                    {mins_left:02d}:{secs_left:02d}
                </span>
            </div>
            <div class="mini-bar" style="margin-top:8px">
                <div class="mini-bar-f" style="width:{pct_left*100:.0f}%;
                    background:linear-gradient(90deg,{timer_color},{timer_color}aa)"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


        # ── System Status ─────────────────────────────────────
        r_col = "#00CC88" if redis_live else "#FF2244"
        r_txt = "● CONNECTED" if redis_live else "● MOCK (LOCAL)"
        st.markdown(f"""
        <div class="sb-section">
            <div class="sb-title">SYSTEM STATUS</div>
            <div class="sb-row">
                <span class="sb-lbl">REDIS</span>
                <span style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:{r_col}">{r_txt}</span>
            </div>
            <div class="sb-row">
                <span class="sb-lbl">WEBSOCKET</span>
                <span style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:#00E5FF">● :8765</span>
            </div>
            <div class="sb-row">
                <span class="sb-lbl">PARTICIPANTS</span>
                <span style="font-family:'Orbitron',monospace;font-size:0.65rem;color:#D4AF37">200</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Logout ────────────────────────────────────────────
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("⬡  LOGOUT", use_container_width=True):
            for k in ["logged_in", "username", "user_data", "active_tab",
                      "cooldown", "ws_log", "seeded", "code_outputs"]:
                st.session_state.pop(k, None)
            st.rerun()
