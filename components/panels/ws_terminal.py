"""
OVERTHRONE :: components/panels/ws_terminal.py
WebSocket terminal panel: live stream viewer + transmit.
"""

import streamlit as st
from datetime import datetime
from db import push_ev


def render_ws_terminal(MT: str):
    st.markdown('<div class="sec-lbl">📡 REAL-TIME WEBSOCKET STREAM</div>', unsafe_allow_html=True)

    wc1, wc2 = st.columns([3, 1], gap="small")
    with wc1:
        ws_in = st.text_input(
            "Transmit",
            placeholder="e.g. ATTACK:team_alpha:cell42",
            label_visibility="collapsed",
        )
    with wc2:
        if st.button("TRANSMIT", use_container_width=True):
            if ws_in:
                push_ev("WS_TX", f"TX: {ws_in}", MT)
                st.session_state.ws_log.append({"t": "info", "m": f">>> {ws_in}"})
                st.session_state.ws_log.append(
                    {"t": "sys", "m": f"[{datetime.utcnow().strftime('%H:%M:%S')}] Queued for broadcast"}
                )
                st.rerun()

    base_lines = [
        {"t": "sys",  "m": "[SYSTEM] ws://localhost:8765 · Status: LISTENING"},
        {"t": "sys",  "m": "[SYSTEM] Connected clients: 4 · Redis pub/sub: ACTIVE"},
        {"t": "info", "m": "[00:01:12] EPOCH_START · Epoch 1 · Phase: MOBILIZATION"},
        {"t": "info", "m": "[00:02:44] TASK_COMPLETE · Team Alpha · +750 AP"},
        {"t": "err",  "m": "[00:03:11] ATTACK · Crimson → Alpha · Cell 15 captured"},
        {"t": "info", "m": "[00:05:30] ALLIANCE · Verdant + Aurum pact formed"},
        {"t": "err",  "m": "[00:08:01] BACKSTAB · Aurum betrayed Verdant · 5 cells!"},
    ] + st.session_state.ws_log[-8:]

    lines_html = "".join(
        f'<div class="ws-ln {l["t"]}">{l["m"]}</div>' for l in base_lines
    )
    st.markdown(f'<div class="ws-term">{lines_html}</div>', unsafe_allow_html=True)

    with st.expander("ws_server.py — run in separate terminal"):
        st.code("""import asyncio, websockets, json, redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
CLIENTS = set()

async def handler(ws, path="/"):
    CLIENTS.add(ws)
    try:
        async for msg in ws:
            data = json.loads(msg)
            r.lpush("ot:events", json.dumps(data))
            r.publish("ot:ws", json.dumps(data))
            if CLIENTS:
                await asyncio.gather(*[c.send(json.dumps(data)) for c in CLIENTS])
    finally:
        CLIENTS.discard(ws)

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WS Server ready · ws://localhost:8765")
        await asyncio.Future()

asyncio.run(main())""", language="python")
