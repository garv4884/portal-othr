"""
OVERTHRONE :: _pages/admin.py
Game Master / Admin utility for resetting the database and resolving states.
"""
import streamlit as st
from db import R
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
                    if pwd == "overlord":
                        st.session_state.admin_unlocked = True
                        st.rerun()
                    else:
                        st.error("ACCESS DENIED.")
        return

    # ── ADMIN DASHBOARD ─────────────────────────────────────────
    st.markdown("### Command Center")
    st.warning("⚠️ Warning: Flushing the database is irreversible. All connected users will be dropped and their progress wiped immediately.")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("☠️ NUKE DATABASE & RESET GAME", use_container_width=True):
            # Erase all keys in the local Redis
            R.flushdb()
            st.success("DATABASE FLUSHED SUCCESSFULLY. Redirecting...")
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
        
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("EXIT ADMIN MODE", use_container_width=True):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
