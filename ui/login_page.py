#!/usr/bin/env python3
"""
Login and authentication page for HBPR UI
"""

import streamlit as st
from ui.common import (
    authenticate_user,
    get_icon_base64,
    ensure_memdb_server,
    logout_current_user,
    get_server_status,
    _port_for_username,
)
from remote_db.db_port_client import DbPortClient


def _check_auto_login():
    """
    快速自动登录检查 - 只检查上次使用的端口
    返回: (should_auto_login: bool, username: str, port: int)
    """
    # 只检查session state中存储的上次登录信息
    if "last_username" not in st.session_state:
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
    st.markdown(
        """
    <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 30px;">
        <img src="data:image/x-icon;base64,{}" width="64" height="64">
        <h1 style="margin: 0;">Flight Check 0.63.1 --- Python</h1>
    </div>
    """.format(get_icon_base64("resources/fcp.ico")),
        unsafe_allow_html=True,
    )
    st.markdown("---")
    # 检查自动登录
    should_auto_login, username, port = _check_auto_login()
    if should_auto_login and username and port:
        st.info("🔄 Welcome back! Restoring your session...")
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.db_service_host = "127.0.0.1"
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
                submit_button = st.form_submit_button(
                    "🚀 Login", type="primary", use_container_width=True
                )
            with col2:
                logout_button = st.form_submit_button(
                    "🚪 Logout", use_container_width=True
                )
            if logout_button:
                # 登出当前用户
                success, message = logout_current_user()
                if success:
                    st.success(f"✅ {message}")
                    # 清除session state中的用户名
                    if "last_username" in st.session_state:
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
                    st.session_state.db_service_host = "127.0.0.1"
                    st.session_state.db_service_port = port
                    st.success(
                        f"✅ Welcome, {username}! DB service on port {port} is ready."
                    )
                    st.rerun()
                else:
                    st.error("❌ Invalid username. Please try again.")
        st.markdown("---")
        # 服务器控制按钮区域 - 无需登录即可使用
        st.markdown("#### 🔧 Server Control")
        st.caption("Manage the database server lifecycle (no authentication required)")
        # 获取所有可用的用户端口状态
        all_ports = [51201, 51202, 51203]  # 3个固定端口
        port_statuses = {}
        for p in all_ports:
            port_statuses[p] = get_server_status(p)
        # 显示服务器状态概览
        any_running = any(s["running"] for s in port_statuses.values())
        if any_running:
            running_ports = [p for p, s in port_statuses.items() if s["running"]]
            running_info = ", ".join(str(p) for p in running_ports)
            auth_users = []
            for p in running_ports:
                auth = port_statuses[p].get("auth_status", {})
                if auth and auth.get("logged_in"):
                    auth_users.append(f"Port {p}: {auth.get('username')}")
            if auth_users:
                st.info(
                    f"🟢 Servers running on ports: {running_info}\n\n"
                    + "\n".join(auth_users)
                )
            else:
                st.info(
                    f"🟡 Servers running on ports: {running_info} | No users logged in"
                )
        else:
            st.info("🔴 No servers running")
        # 服务器控制按钮
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
        # 仅保留Shutdown按钮，显示运行中的端口信息
        with ctrl_col2:
            if st.button(
                "⏹️ Shutdown All",
                use_container_width=True,
                help="Shutdown all running database servers",
            ):
                with st.spinner("Shutting down servers..."):
                    shutdown_count = 0
                    # 关闭所有运行中的服务器
                    for port in all_ports:
                        if port_statuses[port]["running"]:
                            try:
                                client = DbPortClient("127.0.0.1", port)
                                client.shutdown()
                                shutdown_count += 1
                            except Exception:
                                pass
                    if shutdown_count > 0:
                        st.success(f"✅ Shut down {shutdown_count} server(s)")
                        st.rerun()
                    else:
                        st.warning("⚠️ No servers were running")
        st.markdown("---")
        st.caption("🔐 **Contact administrator for access credentials**")

