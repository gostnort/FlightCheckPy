#!/usr/bin/env python3
"""
Login and authentication page for HBPR UI
"""

import streamlit as st
from ui.common import (authenticate_user, get_icon_base64, ensure_memdb_server, 
                       logout_current_user, restart_db_server, shutdown_db_server,
                       get_server_status, _port_for_username)
from remote_db.db_port_client import DbPortClient


def _check_auto_login():
    """
    快速自动登录检查 - 只检查上次使用的端口
    返回: (should_auto_login: bool, username: str, port: int)
    """
    # 只检查session state中存储的上次登录信息
    if 'last_username' not in st.session_state:
        return False, None, None
    
    username = st.session_state.last_username
    port = _port_for_username(username)
    
    if not port:
        return False, None, None
    
    try:
        client = DbPortClient("127.0.0.1", port)
        status = client.auth_status()
        # 如果服务器上有登录状态，且用户名匹配，则自动登录
        if status.get("logged_in") and status.get("username") == username:
            return True, username, port
    except Exception:
        pass
    
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
                logout_button = st.form_submit_button("🚪 Logout", use_container_width=True)
            
            if logout_button:
                # 登出当前用户
                success, message = logout_current_user()
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
                    if not ok:
                        st.error(f"❌ Failed to prepare DB service: {msg}")
                        return
                    # 保存用户名用于自动登录
                    st.session_state.last_username = username
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.db_service_host = '127.0.0.1'
                    st.session_state.db_service_port = port
                    st.success(f"✅ Welcome, {username}! DB service on port {port} is ready.")
                    st.rerun()
                else:
                    st.error("❌ Invalid username. Please try again.")
        
        st.markdown("---")
        
        # 服务器控制按钮区域 - 始终显示
        st.markdown("#### 🔧 Server Control")
        st.caption("Manage the database server lifecycle")
        
        # 显示当前服务器状态
        # 尝试显示状态，即使没有登录过
        username_for_status = st.session_state.get('last_username')
        if username_for_status:
            port_for_status = _port_for_username(username_for_status)
            if port_for_status:
                status = get_server_status(port_for_status)
                
                if status["running"]:
                    auth = status.get("auth_status", {})
                    if auth and auth.get("logged_in"):
                        st.info(f"🟢 Server running on port {port_for_status} | User: {auth.get('username')}")
                    else:
                        st.info(f"🟡 Server running on port {port_for_status} | No user logged in")
                else:
                    st.warning(f"🔴 Server not running (port {port_for_status})")
            else:
                st.info("ℹ️ No server port assigned yet")
        else:
            st.info("ℹ️ Login to see server status")
        
        # 服务器控制按钮 - 始终显示，但根据状态调整行为
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
        
        with ctrl_col1:
            if st.button("▶️ Start", use_container_width=True, help="Start the database server"):
                if 'last_username' in st.session_state:
                    username = st.session_state.last_username
                    with st.spinner("Starting server... (may take up to 10 seconds)"):
                        ok, port, msg = ensure_memdb_server(username)
                    if ok:
                        st.success(f"✅ Server started on port {port}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to start server: {msg}")
                else:
                    st.warning("⚠️ Please login first to determine which server to start")
        
        with ctrl_col2:
            if st.button("🔄 Restart", use_container_width=True, help="Restart the database server"):
                if 'last_username' in st.session_state:
                    username = st.session_state.last_username
                    with st.spinner("Restarting server... (may take up to 10 seconds)"):
                        ok, port, msg = restart_db_server(username)
                    if ok:
                        st.success(f"✅ Server restarted on port {port}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to restart server: {msg}")
                else:
                    st.warning("⚠️ Please login first to determine which server to restart")
        
        with ctrl_col3:
            if st.button("⏹️ Shutdown", use_container_width=True, help="Shutdown the database server"):
                username_to_shutdown = st.session_state.get('last_username')
                if username_to_shutdown:
                    port_to_shutdown = _port_for_username(username_to_shutdown)
                    # Create a temporary client to shutdown the specific port
                    try:
                        from ui.common import get_db_port_client
                        # Temporarily set the port for shutdown
                        old_port = st.session_state.get('db_service_port')
                        st.session_state.db_service_port = port_to_shutdown
                        if shutdown_db_server():
                            st.success("✅ Server shutdown complete")
                            st.rerun()
                        else:
                            st.warning("⚠️ Server may already be down")
                        # Restore old port
                        if old_port:
                            st.session_state.db_service_port = old_port
                    except Exception as e:
                        st.error(f"❌ Shutdown error: {e}")
                else:
                    st.warning("⚠️ Login first to determine which server to shutdown")
        
        st.markdown("---")
        st.caption("🔐 **Contact administrator for access credentials**")

