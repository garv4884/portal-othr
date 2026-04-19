"""
OVERTHRONE :: components/panels/strategy_deck.py
Strategy / action cards panel — full card UI + target selection.
"""

import streamlit as st
import random
from db import save_gs, push_ev
from config import TEAM_COLORS, ACTION_CARDS


def render_strategy_deck(gs, MT, dn):
    other_teams = [t for t in TEAM_COLORS if t != MT]

    st.markdown('<div class="sec-lbl">🃏 YOUR ACTIVE DECK</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-banner" style="background:rgba(255,34,68,0.05);border-left-color:#FF2244;color:#8890b0;margin-bottom:14px">
        Each card is a weapon. Attack to seize land, forge alliances for mutual defense,
        or play Backstab to betray an ally for massive territory gain.
        Use Suspicion to expose traitors — or be exposed yourself.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="small")
    for i, card in enumerate(ACTION_CARDS):
        cname = card["id"]
        cc    = card["color"]
        with (c1 if i % 2 == 0 else c2):
            cost_txt = f"Costs {card['cost']} AP" if card["cost"] > 0 else "No AP cost"
            st.markdown(f"""
            <div class="ac" style="border-top:2px solid {cc}">
                <div class="ac-top" style="background:linear-gradient(90deg,{cc},transparent)"></div>
                <span class="ac-icon">{card['icon']}</span>
                <div class="ac-label" style="color:{cc}">{card['label']}</div>
                <div class="ac-desc">{card['desc']}</div>
                <div class="ac-cost" style="color:{cc}88">{cost_txt}</div>
            </div>
            """, unsafe_allow_html=True)
            target = st.selectbox(
                f"Target", other_teams,
                key=f"deck_sel_{cname}",
                label_visibility="collapsed",
            )
            if st.button(f"PLAY {cname}", key=f"deck_play_{cname}", use_container_width=True):
                _handle_card(cname, target, gs, MT, dn)

    # ── Armory Reference ──────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">📚 ARMORY REFERENCE</div>', unsafe_allow_html=True)
    for card in ACTION_CARDS:
        cc = card["color"]
        cost_txt = f"· {card['cost']} AP" if card["cost"] > 0 else "· Free"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:8px 12px;
            background:linear-gradient(135deg,var(--card),var(--card2));
            border:1px solid {cc}1a;border-left:3px solid {cc};
            border-radius:4px;margin-bottom:4px;transition:background 0.2s">
            <span style="font-size:1.1rem;flex-shrink:0">{card['icon']}</span>
            <div style="flex:1">
                <div style="font-family:'Orbitron',monospace;font-size:0.5rem;
                    letter-spacing:2px;color:{cc};margin-bottom:2px">{card['label']} <span style="color:{cc}66;font-size:0.42rem">{cost_txt}</span></div>
                <div style="font-size:0.72rem;color:var(--text-dim)">{card['desc']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _handle_card(cname: str, target: str, gs: dict, MT: str, dn: str):
    """Execute an action card play."""
    if cname == "ATTACK":
        cost = 500
        my_ap = int(gs["ap"].get(MT, 0))
        if my_ap >= cost:
            enemy_cells = [i for i, o in enumerate(gs["grid"]) if o == target]
            if enemy_cells:
                tgt = random.choice(enemy_cells)
                gs["grid"][tgt]  = MT
                gs["ap"][MT]     = my_ap - cost
                gs["hp"][target] = max(0, int(gs["hp"].get(target, 5000)) - 100)
                save_gs(gs)
                push_ev("ATTACK", f"Team {MT} attacked {target} — cell {tgt} captured!", MT)
                st.success(f"⚔️ Cell {tgt} captured from {target}!")
            else:
                st.warning("No enemy cells to capture.")
        else:
            st.error(f"Insufficient AP — need {cost} AP (have {my_ap}).")
        st.rerun()

    elif cname == "ALLIANCE":
        push_ev("ALLIANCE", f"Non-Aggression Pact: {MT} ↔ {target}", MT)
        st.success(f"🤝 Alliance forged with Team {target}!")

    elif cname == "BACKSTAB":
        enemy_cells = [i for i, o in enumerate(gs["grid"]) if o == target]
        captured    = random.randint(3, min(6, max(1, len(enemy_cells)))) if enemy_cells else 0
        chosen      = random.sample(enemy_cells, captured) if enemy_cells else []
        for c in chosen:
            gs["grid"][c] = MT
        gs["hp"][target] = max(0, int(gs["hp"].get(target, 5000)) - captured * 250)
        save_gs(gs)
        push_ev("BACKSTAB", f"BACKSTAB! {MT} betrayed {target} — {captured} cells seized!", MT)
        st.success(f"🗡️ Backstab! {captured} cells captured from {target}!")
        st.rerun()

    elif cname == "SUSPICION":
        correct = random.random() < 0.5
        if correct:
            push_ev("SUSPICION", f"Team {MT} correctly accused {target} — ELIMINATED!", MT)
            st.success(f"👁️ Correct! {target} was plotting — ELIMINATED from the map!")
        else:
            push_ev("SUSPICION", f"Team {MT} falsely accused {target} — self-eliminated!", MT)
            st.error("⚠️ False accusation — your kingdom pays the price!")
        st.rerun()
