"""
OVERTHRONE :: components/panels/battle_map.py
PUBG-inspired military tactical map — full beast mode.
"""

import streamlit as st
from config import TEAM_COLORS

# ── Terrain cell background variation ────────────────────────
def _terrain_bg(idx: int, owner: str) -> str:
    if owner:
        return {
            "ALPHA":   "#0a2040",
            "CRIMSON": "#2a0a0a",
            "VERDANT": "#0a2a12",
            "AURUM":   "#2a1a00",
        }.get(owner, "#0a0a14")
    # Unclaimed — vary terrain type by position
    row, col = divmod(idx, 10)
    t = (row * 3 + col * 7) % 11
    patterns = [
        "#010d05", "#010e06", "#020f07", "#011005",
        "#020e08", "#01100a", "#010d04", "#010f06",
        "#020d05", "#011108", "#020e07",
    ]
    return patterns[t]


def _cell_glow(owner: str) -> str:
    return {
        "ALPHA":   "#0099FF",
        "CRIMSON": "#FF2244",
        "VERDANT": "#00CC88",
        "AURUM":   "#FFB800",
        "":        "transparent",
    }.get(owner, "transparent")


# Special terrain overlays (loot drops etc.)
TERRAIN_SPECIAL = {15: "🪂", 33: "🏥", 44: "💊", 55: "🔫", 66: "💣", 77: "⚡"}


def render_battle_map(gs, tc):
    grid          = gs["grid"]
    total_claimed = sum(1 for c in grid if c)
    unclaimed     = 100 - total_claimed

    # ── Map header ─────────────────────────────────────────
    st.markdown(f"""
    <div class="map-header">
        <div>
            <div class="map-title">🗺  ERANGEL BATTLE ZONE · SECTOR 9</div>
        </div>
        <div style="display:flex;gap:16px;align-items:center">
            <span class="map-zone-label">🔵 ZONE SHRINKING</span>
            <span class="map-counter">
                ☠️ <span style="color:#FF6644">{total_claimed}</span> CAPTURED
                &nbsp;·&nbsp;
                🟢 <span style="color:#64ff96">{unclaimed}</span> FREE
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Build cells HTML ───────────────────────────────────
    cells_html = ""
    for idx, owner in enumerate(grid):
        bg      = _terrain_bg(idx, owner)
        glow    = _cell_glow(owner)
        owned   = "owned" if owner else ""
        shadow  = f"inset 0 0 7px {glow}cc, 0 0 4px {glow}77" if owner else "none"
        border  = f"border-color:{glow}55;" if owner else "border-color:#0c1e0e;"

        special = TERRAIN_SPECIAL.get(idx, "")
        tooltip = f"Cell {idx} · {owner if owner else 'UNCLAIMED'}"

        if special:
            cells_html += (
                f'<div class="map-cell {owned}" title="⚡ SPECIAL · {tooltip}" '
                f'style="background:{bg};box-shadow:{shadow};{border}'
                f'display:flex;align-items:center;justify-content:center;font-size:0.48rem">'
                f'<span class="map-airdrop">{special}</span></div>'
            )
        else:
            cells_html += (
                f'<div class="map-cell {owned}" title="{tooltip}" '
                f'style="background:{bg};box-shadow:{shadow};{border}"></div>'
            )

    # ── Legend ─────────────────────────────────────────────
    legend_html = ""
    for tname, tinfo in TEAM_COLORS.items():
        c    = tinfo["color"]
        terr = tc.get(tname, 0)
        legend_html += (
            f'<div class="legend-item">'
            f'<div class="legend-dot" style="background:{c};box-shadow:0 0 6px {c}88"></div>'
            f'{tinfo["icon"]} {tname} '
            f'<span style="color:{c};font-weight:bold;margin-left:2px">{terr}</span>'
            f'</div>'
        )
    legend_html += (
        '<div class="legend-item">'
        '<div class="legend-dot" style="background:#010d05;border:1px solid #0e2a10"></div>'
        f'FREE ZONE ({unclaimed})'
        '</div>'
        '<div class="legend-item" style="color:#ff9500">🪂 LOOT</div>'
    )

    # ── Map stats bar ──────────────────────────────────────
    top_team = max(TEAM_COLORS.keys(), key=lambda t: tc.get(t, 0))
    top_c    = TEAM_COLORS[top_team]["color"]
    stats_html = (
        f'<div class="map-stats">'
        f'<div class="map-stat"><span class="map-stat-val">{total_claimed}</span><span class="map-stat-lbl">CLAIMED</span></div>'
        f'<div class="map-stat"><span class="map-stat-val">{unclaimed}</span><span class="map-stat-lbl">FREE</span></div>'
        f'<div class="map-stat"><span class="map-stat-val" style="color:{top_c}">{top_team}</span><span class="map-stat-lbl">LEADING</span></div>'
        f'<div class="map-stat"><span class="map-stat-val" style="color:#64ff96">{tc.get(top_team,0)}</span><span class="map-stat-lbl">CELLS</span></div>'
        f'</div>'
    )

    st.markdown(f"""
<div class="map-wrap" style="position:relative">
    <div class="map-corner tl"></div><div class="map-corner tr"></div>
    <div class="map-corner bl"></div><div class="map-corner br"></div>
    <div class="safe-ring" style="top:50%;left:50%;width:56%;height:56%;"></div>
    <div class="safe-ring-inner" style="top:50%;left:50%;width:28%;height:28%;"></div>
    <div class="map-grid">{cells_html}</div>
    {stats_html}
    <div class="map-legend">{legend_html}</div>
</div>
""", unsafe_allow_html=True)

