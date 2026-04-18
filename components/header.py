"""
OVERTHRONE :: components/header.py
Header bar + kingdom status cards.
"""

import streamlit as st
from config import TEAM_COLORS, STARTING_HP
from db import load_teams_meta


def render_header(gs, tc, dn, MT, mins_left, secs_left, pct_left):
    teams_meta = load_teams_meta()
    my_meta    = teams_meta.get(MT, {})
    MY_COLOR   = my_meta.get("color", "#0099FF")
    MY_ICON    = my_meta.get("icon", "🔵")
    
    timer_color = "#FF2244" if mins_left < 3 else ("#FFB800" if mins_left < 7 else "#FFD700")

    # ── Sidebar Toggle Logic ──────────────────────────────
    import streamlit.components.v1 as _comp
    _comp.html("""
    <script>
    (function() {
        var d = window.parent.document;
        if (window.parent.__OT_SIDEBAR_HOOKED__) return;
        window.parent.__OT_SIDEBAR_HOOKED__ = true;

        function toggleSidebar() {
            var sb = d.querySelector('[data-testid="stSidebar"]');
            var isClosed = !sb || sb.getBoundingClientRect().width < 50;
            var btn;
            if (isClosed) {
                btn = d.querySelector('[data-testid="collapsedControl"] button') || d.querySelector('[data-testid="collapsedControl"]');
            } else {
                btn = d.querySelector('[data-testid="stSidebarCollapseButton"] button') || d.querySelector('[data-testid="stSidebarCollapseButton"]');
            }
            if (btn) btn.click();
        }

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

    st.markdown(f"""
<div class="ot-hdr">
    <div style="display:flex; align-items:center; gap:1.2rem;">
        <div id="ot-logo-btn" style="cursor:pointer; display:flex; align-items:center; gap:12px;" title="Toggle Sidebar">
            <div style="font-size:1.5rem; color:var(--gold); filter:drop-shadow(0 0 5px var(--gold));">☰</div>
            <div class="ot-logo" style="transition: filter 0.3s;" onmouseover="this.style.filter='drop-shadow(0 0 10px rgba(212,175,55,0.8))'" onmouseout="this.style.filter='none'">OVERTHRONE</div>
        </div>
        <div style="height:25px; width:1px; background:rgba(212,175,55,0.25); margin:0 5px"></div>
        <div class="ot-subtitle">HELIX × ISTE · THE ULTIMATE KINGDOM SIMULATION</div>
    </div>
    <div class="ot-center">
        <span class="ot-live-badge">● LIVE</span>
        <div class="ot-team-badge" style="color:{MY_COLOR};border-color:{MY_COLOR}44;background:{MY_COLOR}08">
            {MY_ICON} {dn.upper()} · TEAM {MT}
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


def render_kingdom_cards(gs, tc, MT):
    teams_meta = load_teams_meta()
    
    # Sort teams by territory (cells) descending
    sorted_teams = sorted(teams_meta.items(), key=lambda x: tc.get(x[0], 0), reverse=True)
    top_4_teams  = sorted_teams[:4]
    
    cols = st.columns(4, gap="small")
    for col, (tname, tinfo) in zip(cols, top_4_teams):
        hp   = int(gs["hp"].get(tname, STARTING_HP))
        ap   = int(gs["ap"].get(tname, 0))
        terr = tc.get(tname, 0)
        c    = tinfo.get("color", "#0099FF")
        bg   = tinfo.get("bg", "#001933")
        icon = tinfo.get("icon", "🔵")
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
