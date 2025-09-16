#!/usr/bin/env python3
"""
Login and authentication page for HBPR UI
"""

import streamlit as st
from ui.common import authenticate_user, get_icon_base64, ensure_memdb_server


def show_login_page():
    """Display the login page"""
    st.markdown("""
    <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 30px;">
        <img src="data:image/x-icon;base64,{}" width="64" height="64">
        <h1 style="margin: 0;">Flight Check 0.62.1 --- Python</h1>
    </div>
    """.format(get_icon_base64("resources/fcp.ico")), unsafe_allow_html=True)
    st.markdown("---")
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 User Authentication")
        st.caption("Please enter your username to access the system")
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter username")
            col1, col2 = st.columns(2)
            with col1:
                submit_button = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("🔄 Clear", use_container_width=True):
                    st.rerun()
            if submit_button:
                if not username:
                    st.error("❌ Please enter a username")
                elif authenticate_user(username):
                    ok, port, msg = ensure_memdb_server(username)
                    if not ok and msg == "User already logged in on this host":
                        st.error("❌ This user is already logged in. Please use another username.")
                        return
                    if not ok:
                        st.error(f"❌ Failed to prepare DB service: {msg}")
                        return
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.db_service_host = '127.0.0.1'
                    st.session_state.db_service_port = port
                    st.success(f"✅ Welcome, {username}! DB service on port {port} is ready.")
                    st.rerun()
                else:
                    st.error("❌ Invalid username. Please try again.")
        st.markdown("---")
        st.caption("🔐 **Contact administrator for access credentials**")

