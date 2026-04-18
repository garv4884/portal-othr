"""
OVERTHRONE :: _pages/admin.py
Game Master / Admin utility for resetting the database and resolving states.
"""
import streamlit as st
from db import R, check_admin_auth, load_gs, save_gs, simulate_epoch, acquire_epoch_lock, push_ev, load_teams
from styles.theme import get_auth_css

def show_admin_page():
    st.markdown(get_auth_css(), unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-bottom:1.5rem; text-align:center;">
        <div style="font-family:'Orbitron',monospace;font-size:1.8rem;font-weight:900;
            letter-spacing:5px;color:#FF2244;margin-bottom:6px">OVERTHRONE : ADMIN</div>
        <div style="font-family:'Rajdhani',sans-serif;font-size:0.9rem;color:#dde0f5">
            Restricted Game Master Access
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── SECURITY GATE ───────────────────────────────────────────
    if not st.session_state.get("admin_unlocked", False):
        with st.container():
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                pwd = st.text_input("Enter Game Master Password", type="password", key="admin_pwd")
                if st.button("AUTHENTICATE", use_container_width=True):
                    ok, msg = check_admin_auth(pwd)
                    if ok:
                        st.session_state.admin_unlocked = True
                        st.rerun()
                    else:
                        st.error(msg)
        return

    # ── ADMIN DASHBOARD ─────────────────────────────────────────
    st.markdown("### Command Center")
    
    # Show stats
    gs = load_gs()
    teams = load_teams()
    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.03); padding:1rem; border-radius:10px; border:1px solid rgba(255,255,255,0.1)'>
        <strong>System Metrics:</strong> Epoch {gs['epoch']} | Grid Size: {len(gs['grid'])} | Kingdoms: {len(teams)}
    </div>
    """, unsafe_allow_html=True)
    
    st.warning("⚠️ Warning: These actions are irreversible.")

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        # ── Option C: Emergency Force Rollover ──────────────────
        st.markdown("#### ⚡ Emergency Protocols")
        if st.button("🚀 FORCE ADVANCE EPOCH (MANUAL ROLLOVER)", use_container_width=True):
            if acquire_epoch_lock(gs["epoch"]):
                simulate_epoch(gs)
                push_ev("SYS", "ADMIN: Manual Epoch Advance triggered by Game Master.")
                st.success(f"Epoch advanced to {gs['epoch'] + 1}")
                st.rerun()
            else:
                st.error("Failed override: Epoch simulation is already in progress.")
        
        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Option A: Reset Teams only (keep user accounts) ──────
        st.markdown("#### 🧹 Reset Teams Only")
        st.caption("Wipes all teams & game state. User accounts are preserved so players can re-register.")
        if st.button("🗑️ DELETE ALL TEAMS & RESET GAME STATE", use_container_width=True):
            import json
            # Delete team metadata and game state
            R.delete("ot:teams_meta")
            R.delete("ot:state")
            R.delete("ot:events")
            # Clear team field from every user account
            raw = R.get("ot:users")
            if raw:
                try:
                    users = json.loads(raw)
                    for u in users.values():
                        u["team"] = None
                    R.set("ot:users", json.dumps(users))
                except Exception as e:
                    st.error(f"Could not clear user teams: {e}")
            st.success("✅ All teams cleared. Users can now form new kingdoms.")
            st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Option B: Full nuke (wipes everything) ────────────────
        st.markdown("#### ☠️ Full Database Wipe")
        st.caption("Deletes every key including all user accounts. Everyone must re-register.")
        if st.button("☠️ NUKE DATABASE & RESET GAME", use_container_width=True):
            R.flushdb()
            st.success("DATABASE FLUSHED SUCCESSFULLY. Redirecting...")
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

        if st.button("RESET ADMIN LOCKOUTS & FAIL COUNTS", use_container_width=True):
            R.delete("ot:admin_lockout")
            R.delete("ot:admin_fail_count")
            st.success("Security throttles reset.")
            st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("EXIT ADMIN MODE", use_container_width=True):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
