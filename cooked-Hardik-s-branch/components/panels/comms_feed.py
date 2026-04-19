"""
OVERTHRONE :: components/panels/comms_feed.py
Live event feed + elimination tracker — using separate st.markdown calls.
"""

import streamlit as st
from config import TEAM_COLORS, EVENT_COLORS


def render_comms_feed(evs, gs):
    # ── Panel header ──────────────────────────────────────────
    st.markdown("""
    <div class="panel-header" style="margin-bottom:6px">
        <span class="panel-title">📡 COMMS FEED · LIVE</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Event feed ────────────────────────────────────────────
    feed_html = '<div class="ev-feed">'
    for ev in evs[:18]:
        bc        = EVENT_COLORS.get(ev.get("kind", "SYS"), "#333355")
        kind_icon = _ev_icon(ev.get("kind", "SYS"))
        feed_html += (
            f'<div class="ev-item" style="border-left-color:{bc}">'
            f'<span class="ev-ts">{ev.get("ts","--:--:--")}</span>'
            f'<span style="margin-right:4px">{kind_icon}</span>'
            f'<span class="ev-msg">{ev.get("msg","")}</span>'
            f'</div>'
        )
    feed_html += '</div>'
    st.markdown(feed_html, unsafe_allow_html=True)

    st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)

    # ── Elimination tracker ───────────────────────────────────
    st.markdown('<div class="sb-title">ELIMINATION TRACKER</div>', unsafe_allow_html=True)
    ranked = sorted(TEAM_COLORS.items(), key=lambda x: int(gs["hp"].get(x[0], 0)), reverse=True)
    for tname, tinfo in ranked:
        hp     = int(gs["hp"].get(tname, 5000))
        status = "ELIMINATED" if hp <= 0 else "ACTIVE"
        sc     = "#FF2244" if hp <= 0 else "#00CC88"
        st.markdown(f"""
        <div class="elim-row">
            <span style="color:{tinfo['color']}">{tinfo['icon']} TEAM {tname}</span>
            <span style="font-family:'Orbitron',monospace;font-size:0.48rem;letter-spacing:2px;color:{sc}">{status}</span>
        </div>
        """, unsafe_allow_html=True)


def _ev_icon(kind: str) -> str:
    return {
        "ATTACK":    "⚔️",
        "BACKSTAB":  "🗡️",
        "ALLIANCE":  "🤝",
        "SUSPICION": "👁️",
        "TASK":      "✅",
        "SYS":       "⚙️",
        "WS_TX":     "📡",
    }.get(kind, "·")
