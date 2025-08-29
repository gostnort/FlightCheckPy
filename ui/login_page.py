#!/usr/bin/env python3
"""
Login and authentication page for HBPR UI
"""

import streamlit as st
from ui.db_management import authenticate_user, get_icon_base64


def show_login_page():
    """Display the login page"""
    st.markdown("""
    <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 30px;">
        <img src="data:image/x-icon;base64,{}" width="64" height="64">
        <h1 style="margin: 0;">Flight Check 0.62 --- Python</h1>
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
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"✅ Welcome, {username}! Authentication successful.")
                    st.rerun()
                else:
                    st.error("❌ Invalid username. Please try again.")
        st.markdown("---")
        st.caption("🔐 **Contact administrator for access credentials**")

