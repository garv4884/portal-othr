"""
OVERTHRONE :: components/panels/leaderboard.py
Premium leaderboard panel with rankings, AP standings, and team rosters.
"""

import streamlit as st
from db import load_users, load_teams_meta
from config import TEAM_COLORS

RANK_ICONS  = ["🥇", "🥈", "🥉", "④"]
RANK_COLORS = ["#FFD700", "#C0C0C0", "#CD7F32", "#555577"]


def render_leaderboard(gs, tc, MT):
    ranked = sorted(
        TEAM_COLORS.items(),
        key=lambda x: (tc.get(x[0], 0), int(gs["hp"].get(x[0], 0))),
        reverse=True,
    )
    all_users  = load_users()
    teams_meta = load_teams_meta()

    # ── Header ────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">🏆 KINGDOM RANKINGS</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="lb-header">
        <div></div><div>KINGDOM</div>
        <div style="text-align:right">HP</div>
        <div style="text-align:right">CELLS</div>
        <div>DOMINANCE</div>
    </div>
    """, unsafe_allow_html=True)

    for rank, (tname, tinfo) in enumerate(ranked):
        hp   = int(gs["hp"].get(tname, 0))
        ap   = int(gs["ap"].get(tname, 0))
        terr = tc.get(tname, 0)
        c    = tinfo["color"]
        mine = tname == MT
        mine_style = f"border-color:{c}44;box-shadow:0 0 16px {c}18;" if mine else ""
        mine_flag  = " ◄ YOU" if mine else ""
        meta       = teams_meta.get(tname, {})
        mbrs       = meta.get("members", [])
        mbr_names  = [all_users.get(m, {}).get("display_name", m) for m in mbrs]
        mbr_str    = " · ".join(mbr_names) if mbr_names else "—"

        # Territory domination bar
        bar_pct = terr  # out of 100

        st.markdown(f"""
        <div class="lb-row" style="{mine_style}background:linear-gradient(135deg,{tinfo['bg']}55 0%,var(--card2) 100%)">
            <div class="lb-rank">{RANK_ICONS[rank]}</div>
            <div>
                <div class="lb-name" style="color:{c}">{tinfo['icon']} TEAM {tname}{mine_flag}</div>
                <div class="lb-members">{mbr_str}</div>
            </div>
            <div class="lb-val" style="color:#D4AF37">{hp:,}</div>
            <div class="lb-val" style="color:#00E5FF">{terr}</div>
            <div class="lb-bar-wrap">
                <div class="lb-bar-fill" style="width:{bar_pct}%;background:{c};box-shadow:0 0 8px {c}88"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── AP Standings ──────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">⚡ ATTACK POINTS STANDINGS</div>', unsafe_allow_html=True)

    ap_ranked = sorted(TEAM_COLORS.items(), key=lambda x: int(gs["ap"].get(x[0], 0)), reverse=True)
    for tname, tinfo in ap_ranked:
        ap  = int(gs["ap"].get(tname, 0))
        c   = tinfo["color"]
        pct = min(ap / 3000, 1.0) * 100
        mine_bg = f"background:{c}08;" if tname == MT else ""
        st.markdown(f"""
        <div style="padding:8px 12px;border-radius:4px;margin-bottom:4px;{mine_bg}
            border:1px solid rgba(255,255,255,0.04);transition:background 0.2s">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
                <span style="font-family:'Orbitron',monospace;font-size:0.55rem;letter-spacing:1.5px;color:{c}">
                    {tinfo['icon']} {tname}
                </span>
                <span style="font-family:'Orbitron',monospace;font-size:0.6rem;color:#00E5FF;font-weight:600">
                    {ap:,} AP
                </span>
            </div>
            <div class="mini-bar">
                <div class="mini-bar-f" style="width:{pct:.0f}%;background:linear-gradient(90deg,{c},{c}aa);box-shadow:0 0 6px {c}88"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Event Stats ───────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">📊 EVENT STATISTICS</div>', unsafe_allow_html=True)
    total_hp    = sum(int(gs["hp"].get(t, 0)) for t in TEAM_COLORS)
    total_ap    = sum(int(gs["ap"].get(t, 0)) for t in TEAM_COLORS)
    total_cells = sum(tc.get(t, 0) for t in TEAM_COLORS)
    st.markdown(f"""
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">
        <div style="flex:1;min-width:80px;background:var(--card);border:1px solid var(--border2);
            border-radius:4px;padding:10px;text-align:center">
            <div style="font-family:'Orbitron',monospace;font-size:0.9rem;color:#D4AF37;font-weight:700">{total_hp:,}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.44rem;letter-spacing:2px;color:var(--dim);margin-top:3px">TOTAL HP</div>
        </div>
        <div style="flex:1;min-width:80px;background:var(--card);border:1px solid var(--border2);
            border-radius:4px;padding:10px;text-align:center">
            <div style="font-family:'Orbitron',monospace;font-size:0.9rem;color:#00E5FF;font-weight:700">{total_ap:,}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.44rem;letter-spacing:2px;color:var(--dim);margin-top:3px">TOTAL AP</div>
        </div>
        <div style="flex:1;min-width:80px;background:var(--card);border:1px solid var(--border2);
            border-radius:4px;padding:10px;text-align:center">
            <div style="font-family:'Orbitron',monospace;font-size:0.9rem;color:#00CC88;font-weight:700">{total_cells}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.44rem;letter-spacing:2px;color:var(--dim);margin-top:3px">CELLS OWNED</div>
        </div>
        <div style="flex:1;min-width:80px;background:var(--card);border:1px solid var(--border2);
            border-radius:4px;padding:10px;text-align:center">
            <div style="font-family:'Orbitron',monospace;font-size:0.9rem;color:#FFB800;font-weight:700">{gs['epoch']}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.44rem;letter-spacing:2px;color:var(--dim);margin-top:3px">EPOCH</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
