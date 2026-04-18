"""
OVERTHRONE :: components/header.py
Header bar + kingdom status cards.
"""

import streamlit as st
from config import STARTING_HP
from db import load_teams


def render_header(gs, tc, dn, MT, mins_left, secs_left, pct_left, teams_meta):
    my_meta     = teams_meta.get(MT, {})
    MY_COLOR    = my_meta.get("color", "#00E5FF")
    timer_color = "#FF2244" if mins_left < 3 else ("#FFB800" if mins_left < 7 else "#FFD700")

    # ── Sidebar Toggle Logic ──────────────────────────────
    import streamlit.components.v1 as _comp
    _comp.html("""
    <script>
    (function() {
        var d = window.parent.document;
        if (window.parent.__OT_SIDEBAR_HOOKED_V2__) return;
        window.parent.__OT_SIDEBAR_HOOKED_V2__ = true;

        function toggleSidebar() {
            var openParams = d.querySelectorAll('[data-testid="collapsedControl"] svg, [data-testid="collapsedControl"] button, [data-testid="collapsedControl"]');
            var closeParams = d.querySelectorAll('[data-testid="stSidebarCollapseButton"] svg, [data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"]');
            
            var clicked = false;
            // Try close first
            closeParams.forEach(function(el) {
                if (!clicked && el.offsetParent !== null) {
                    el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                    clicked = true;
                }
            });
            if (clicked) return;
            
            // Try open
            openParams.forEach(function(el) {
                if (!clicked && el.offsetParent !== null) {
                   el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                   clicked = true;
                }
            });
        }

        d.addEventListener('click', function(e) {
            var curr = e.target;
            while (curr && curr !== d.body) {
                if (curr.id === 'ot-logo-btn' || curr.id === 'sticky-sidebar-toggle') {
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
    """, height=1)

    st.markdown(f"""
<div id="sticky-sidebar-toggle" style="position:fixed; top:50%; left:0; transform:translateY(-50%); z-index:999999; background:linear-gradient(90deg, rgba(8,8,19,0.95), rgba(212,175,55,0.1)); border:1px solid rgba(212,175,55,0.4); border-left:none; padding:25px 6px; cursor:pointer; color:#D4AF37; box-shadow: 2px 0 15px rgba(212,175,55,0.25); border-radius:0 10px 10px 0; transition:all 0.3s; display:flex; align-items:center; justify-content:center;" onmouseover="this.style.background='rgba(212,175,55,0.25)';this.style.boxShadow='4px 0 25px rgba(212,175,55,0.5)';" onmouseout="this.style.background='linear-gradient(90deg, rgba(8,8,19,0.95), rgba(212,175,55,0.1))';this.style.boxShadow='2px 0 15px rgba(212,175,55,0.25)';">
    <div style="font-family:'Orbitron',monospace; font-weight:900; font-size:11px; writing-mode:vertical-rl; text-orientation:mixed; letter-spacing:4px; text-shadow:0 0 5px rgba(212,175,55,0.8);">〉 PANEL</div>
</div>
<div class="ot-hdr">
    <div style="display:flex; align-items:center; gap:1.2rem;">
        <div id="ot-logo-btn" style="cursor:pointer; display:flex; align-items:center; gap:12px; position:relative; z-index:100;" title="Toggle Sidebar">
            <div style="font-size:1.5rem; color:var(--gold); filter:drop-shadow(0 0 5px var(--gold));">☰</div>
            <div class="ot-logo" style="transition: filter 0.3s;" onmouseover="this.style.filter='drop-shadow(0 0 10px rgba(212,175,55,0.8))'" onmouseout="this.style.filter='none'">OVERTHRONE</div>
        </div>
        <div style="height:25px; width:1px; background:rgba(212,175,55,0.25); margin:0 5px"></div>
        <div class="ot-subtitle">HELIX × ISTE · THE ULTIMATE KINGDOM SIMULATION</div>
    </div>
    <div class="ot-center">
        <span class="ot-live-badge">● LIVE</span>
        <div class="ot-team-badge" style="color:{MY_COLOR};border-color:{MY_COLOR}44;background:{MY_COLOR}08">
            {my_meta.get('icon', '👑')} {dn.upper()} · TEAM {MT}
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


def render_kingdom_cards(gs, tc, MT, teams_meta):
    if not teams_meta:
        st.caption("No kingdoms formed yet.")
        return

    team_list = list(teams_meta.items())
    cols = st.columns(min(len(team_list), 4), gap="small")
    for col, (tname, tinfo) in zip(cols, team_list):
        hp   = int(gs["hp"].get(tname, STARTING_HP))
        ap   = int(gs["ap"].get(tname, 0))
        terr = tc.get(tname, 0)
        c    = tinfo.get("color", "#00E5FF")
        bg   = tinfo.get("bg", "#001133")
        icon = tinfo.get("icon", "👑")
        mine = tname == MT
        hp_p = max(0.0, hp / STARTING_HP)
        ap_p = min(ap / 3000, 1.0)

        badge  = f'<span class="you-tag" style="background:{c}22;color:{c};border:1px solid {c}55">YOU</span>' if mine else ""
        border = f"border-color:{c}44;box-shadow:0 0 20px {c}14;" if mine else ""

        with col:
            st.markdown(f"""
            <div class="kcard" style="{border}background:linear-gradient(140deg,{bg} 0%,var(--card) 100%)">
                <div class="kcard-accent" style="background:linear-gradient(180deg,{c},{c}66);box-shadow:0 0 10px {c}88"></div>
                <div class="kcard-name" style="color:{c}">{icon} TEAM {tname}{badge}</div>
                <div class="kcard-stats">
                    <div>
                        <div class="kcard-sl">HEALTH</div>
                        <div class="kcard-sv" style="color:{c}">{hp:,}</div>
                        <div class="mini-bar">
                            <div class="mini-bar-f" style="width:{hp_p*100:.0f}%;background:{c};box-shadow:0 0 4px {c}"></div>
                        </div>
                    </div>
                    <div>
                        <div class="kcard-sl">ATTACK</div>
                        <div class="kcard-sv" style="color:#00E5FF">{ap:,}</div>
                        <div class="mini-bar">
                            <div class="mini-bar-f" style="width:{ap_p*100:.0f}%;background:#00E5FF;box-shadow:0 0 4px #00E5FF"></div>
                        </div>
                    </div>
                    <div>
                        <div class="kcard-sl">CELLS</div>
                        <div class="kcard-sv" style="color:#D4AF37">{terr}</div>
                        <div class="kcard-sl" style="font-size:0.4rem">/100</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
