#!/usr/bin/env python3
"""
Login and authentication page for HBPR UI
"""

import streamlit as st
from ui.common import (authenticate_user, get_icon_base64, ensure_memdb_server, 
                       get_client_ip, logout_current_ip, get_db_port_client)
from remote_db.db_port_client import DbPortClient


def _check_auto_login():
    """
    检查当前IP是否有有效session，如果有则自动登录
    返回: (should_auto_login: bool, username: str, port: int)
    """
    # 获取所有可能的用户端口
    import hashlib
    valid_users = {
        'c7c5b358d4097f8e2798c54f2ab6c3574a0cc82c87a3acf4ac9f038af4f75d2c': (51201, 'User1'),
        '9fe93417853739c1c18c2e8b051860d1a317824f1aa91304d16f3fe832486f7a': (51202, 'User2'),
        '239127e09157cbafb6212123b102aa1103241946b3684c232c44b8367c3a4d47': (51203, 'User3')
    }
    
    client_ip = get_client_ip()
    
    # 检查每个端口是否有当前IP的session
    for user_hash, (port, username_hint) in valid_users.items():
        try:
            client = DbPortClient("127.0.0.1", port)
            # 检查服务器是否运行
            health = client.health()
            if not health.get("ok"):
                continue
            
            # 检查当前IP是否有session
            session_check = client.check_session(client_ip)
            if session_check.get("has_session"):
                # 找到有效session，返回username（从session state获取）
                if 'last_username' in st.session_state:
                    return True, st.session_state.last_username, port
        except Exception:
            continue
    
    return False, None, None


def show_login_page():
    """Display the login page"""
    st.markdown("""
    <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 30px;">
        <img src="data:image/x-icon;base64,{}" width="64" height="64">
        <h1 style="margin: 0;">Flight Check 0.63 --- Python</h1>
    </div>
    """.format(get_icon_base64("resources/fcp.ico")), unsafe_allow_html=True)
    st.markdown("---")
    
    # 检查自动登录
    should_auto_login, username, port = _check_auto_login()
    if should_auto_login and username and port:
        st.info(f"🔄 Welcome back! Restoring your session...")
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.db_service_host = '127.0.0.1'
        st.session_state.db_service_port = port
        st.rerun()
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
                clear_button = st.form_submit_button("🔄 Clear Session", use_container_width=True)
            
            if clear_button:
                # 登出当前IP的session
                success, message = logout_current_ip()
                if success:
                    st.success(f"✅ {message}")
                    # 清除session state中的用户名
                    if 'last_username' in st.session_state:
                        del st.session_state.last_username
                    st.rerun()
                else:
                    st.warning(f"⚠️ {message}")
                    st.rerun()
            
            if submit_button:
                if not username:
                    st.error("❌ Please enter a username")
                elif authenticate_user(username):
                    ok, port, msg = ensure_memdb_server(username)
                    if not ok and msg == "Another IP is currently logged in":
                        st.error("❌ Another IP is currently logged in. Please use the 'Clear Session' button if you want to force login.")
                        return
                    if not ok:
                        st.error(f"❌ Failed to prepare DB service: {msg}")
                        return
                    # 保存用户名用于自动登录
                    st.session_state.last_username = username
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.db_service_host = '127.0.0.1'
                    st.session_state.db_service_port = port
                    if msg == "Session restored":
                        st.success(f"✅ Welcome back, {username}! Your session has been restored.")
                    else:
                        st.success(f"✅ Welcome, {username}! DB service on port {port} is ready.")
                    st.rerun()
                else:
                    st.error("❌ Invalid username. Please try again.")
        st.markdown("---")
        st.caption("🔐 **Contact administrator for access credentials**")

