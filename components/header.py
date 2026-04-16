"""
OVERTHRONE :: components/header.py
Header bar + kingdom status cards.
"""

import streamlit as st
from config import TEAM_COLORS, STARTING_HP


def render_header(gs, tc, dn, MT, mins_left, secs_left, pct_left):
    MY_COLOR    = TEAM_COLORS[MT]["color"]
    timer_color = "#FF2244" if mins_left < 3 else ("#FFB800" if mins_left < 7 else "#FFD700")

    st.markdown(f"""
<div class="ot-hdr">
    <div class="ot-hdr-left">
        <div class="ot-logo" id="ot-logo-btn" style="cursor:pointer;" title="Click to Toggle Sidebar">OVERTHRONE</div>
        <div class="ot-subtitle">HELIX × ISTE · THE ULTIMATE KINGDOM SIMULATION</div>
    </div>
""", unsafe_allow_html=True)
    
    import streamlit.components.v1 as _comp
    _comp.html("""
    <script>
    (function() {
        var d = window.parent.document;
        function toggleSidebar() {
            var sb = d.querySelector('[data-testid="stSidebar"]');
            var open = sb && parseInt(window.parent.getComputedStyle(sb).width) > 50;
            if (open) {
                var b = d.querySelector('[data-testid="stSidebarCollapseButton"] button') || d.querySelector('[data-testid="stSidebarCollapseButton"]');
                if (b) b.click();
            } else {
                var b = d.querySelector('[data-testid="collapsedControl"] button') || d.querySelector('[data-testid="collapsedControl"]');
                if (b) b.click();
            }
        }
        function hook() {
            var logo = d.getElementById("ot-logo-btn");
            if (logo && !logo.hasAttribute('data-bound')) {
                logo.addEventListener('click', toggleSidebar);
                logo.setAttribute('data-bound', 'true');
            }
        }
        setInterval(hook, 500); 
    })();
    </script>
    """, height=0)

    st.markdown(f"""
    <div class="ot-center">
        <span class="ot-live-badge">● LIVE</span>
        <div class="ot-team-badge" style="color:{MY_COLOR};border-color:{MY_COLOR}44;background:{MY_COLOR}08">
            {TEAM_COLORS[MT]['icon']} {dn.upper()} · TEAM {MT}
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
    cols = st.columns(4, gap="small")
    for col, (tname, tinfo) in zip(cols, TEAM_COLORS.items()):
        hp   = int(gs["hp"].get(tname, STARTING_HP))
        ap   = int(gs["ap"].get(tname, 0))
        terr = tc.get(tname, 0)
        c    = tinfo["color"]
        bg   = tinfo["bg"]
        mine = tname == MT
        hp_p = max(0.0, hp / STARTING_HP)
        ap_p = min(ap / 3000, 1.0)

        badge  = f'<span class="you-tag" style="background:{c}22;color:{c};border:1px solid {c}55">YOU</span>' if mine else ""
        border = f"border-color:{c}44;box-shadow:0 0 20px {c}14;" if mine else ""

        with col:
            st.markdown(f"""
            <div class="kcard" style="{border}background:linear-gradient(140deg,{bg} 0%,var(--card) 100%)">
                <div class="kcard-accent" style="background:linear-gradient(180deg,{c},{c}66);box-shadow:0 0 10px {c}88"></div>
                <div class="kcard-name" style="color:{c}">{tinfo['icon']} TEAM {tname}{badge}</div>
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
