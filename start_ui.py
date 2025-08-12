import os
import webbrowser
import subprocess
from pystray import Icon, MenuItem
from PIL import Image
from winotify import Notification, audio
import time
import requests
import threading

streamlit_proc = None


def setup_working_directory():
    """
    设置正确的工作目录为脚本所在目录
    确保资源文件能正确访问
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    return script_dir


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径
    Args:
        relative_path: 相对于项目根目录的路径
    Returns:
        str: 资源文件的绝对路径
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)


def get_python_executable():
    """
    获取合适的Python执行文件路径，优先使用虚拟环境
    Returns:
        tuple: (python_path: str, is_venv: bool) - Python执行文件的完整路径和是否为虚拟环境
    """
    # 常见的虚拟环境目录名
    venv_dirs = ['venv', '.venv', 'env', '.env']
    # 检查是否在虚拟环境中
    for venv_dir in venv_dirs:
        if os.path.exists(venv_dir):
            print(f"找到虚拟环境目录: {venv_dir}")
            # Windows虚拟环境路径（转换为绝对路径）
            python_path = os.path.abspath(os.path.join(venv_dir, 'Scripts', 'python.exe'))
            pythonw_path = os.path.abspath(os.path.join(venv_dir, 'Scripts', 'pythonw.exe'))
            print(f"检查Python路径: {pythonw_path}")
            print(f"Python文件存在: {os.path.exists(pythonw_path)}")
            # 优先使用pythonw.exe（不显示控制台窗口）
            if os.path.exists(pythonw_path):
                print(f"✓ 使用虚拟环境Python: {pythonw_path}")
                return pythonw_path, True
            elif os.path.exists(python_path):
                print(f"✓ 使用虚拟环境Python: {python_path}")
                return python_path, True
            else:
                print("! 虚拟环境目录存在但Python执行文件不存在")
    # 如果没有找到虚拟环境，使用系统Python
    print("! 未找到虚拟环境，使用系统Python")
    return "pythonw", False


def notify_winotify(title: str, msg: str, icon_path: str = None):
    """
    Show a Windows toast notification.
    title:      Toast title
    msg:        Toast message body
    icon_path:  Path to a .ico file (optional)
    """
    # 检查图标文件是否存在
    if icon_path and not os.path.exists(icon_path):
        print(f"Warning: Icon file not found: {icon_path}")
        icon_path = None
    toast = Notification(
        app_id="StreamlitLauncher",
        title=title,
        msg=msg,
        icon=icon_path,
        duration="short"
    )
    toast.set_audio(audio.Default, loop=False)
    toast.show()


def wait_for_streamlit(url="http://localhost:8501/_stcore/health", timeout: int = 60) -> bool:
    """
    Polls the Streamlit health endpoint until success or timeout.
    Returns True on HTTP 200, False on timeout.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(url).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def start_streamlit():
    global streamlit_proc
    icon_path = get_resource_path("resources/fcp.ico")
    if streamlit_proc and streamlit_proc.poll() is None:
        notify_winotify("Streamlit Launcher", "Streamlit is already running!", icon_path=icon_path)
        return  # already running
    # 先停止现有的进程
    stop_streamlit()
    # 等待一小段时间确保进程完全终止
    time.sleep(1)
    notify_winotify("Streamlit Launcher", "Starting Streamlit...", icon_path=icon_path)
    # 获取合适的Python执行文件（优先虚拟环境）
    python_exec, is_venv = get_python_executable()
    print(f"启动Streamlit使用的Python: {python_exec}")
    print(f"是否使用虚拟环境: {'是' if is_venv else '否'}")
    # 构建自定义命令
    main_py_path = get_resource_path("ui/main.py")
    cmd = [
        python_exec,
        "-m", "streamlit", "run", main_py_path,
        "--server.address", "0.0.0.0",
        "--server.port", "8501",
        "--browser.serverAddress", "localhost",
        "--server.headless", "false"
    ]
    print(f"执行命令: {' '.join(cmd)}")
    streamlit_proc = subprocess.Popen(cmd,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL)
    def watch_and_notify():
        if wait_for_streamlit():
            notify_winotify("Streamlit Launcher", "Streamlit is ready!", icon_path=icon_path)
        else:
            notify_winotify("Streamlit Launcher", "Streamlit failed to start in time.", icon_path=icon_path)
    threading.Thread(target=watch_and_notify, daemon=True).start()
    return False


def stop_streamlit():
    global streamlit_proc
    icon_path = get_resource_path("resources/fcp.ico")
    if streamlit_proc:
        try:
            # 强制终止进程
            streamlit_proc.kill()
            streamlit_proc.wait(timeout=5)
            notify_winotify("Streamlit Launcher", "Streamlit stopped successfully!", icon_path=icon_path)
        except subprocess.TimeoutExpired:
            # 如果超时，强制杀死进程
            streamlit_proc.kill()
            notify_winotify("Streamlit Launcher", "Streamlit force stopped!", icon_path=icon_path)
        except Exception as e:
            print(f"Error stopping streamlit: {e}")
        finally:
            streamlit_proc = None
    else:
        notify_winotify("Streamlit Launcher", "No Streamlit process to stop!", icon_path=icon_path)


def restart_streamlit(icon, item):
    threading.Thread(target=lambda: (stop_streamlit(), start_streamlit())).start()


def open_in_browser(icon, item):
    icon_path = get_resource_path("resources/fcp.ico")
    try:
        webbrowser.open("http://localhost:8501")
        notify_winotify("Streamlit Launcher", "Opening browser...", icon_path=icon_path)
    except Exception as e:
        notify_winotify("Streamlit Launcher", f"Failed to open browser: {e}", icon_path=icon_path)


def build_tray():
    icon_path = get_resource_path("resources/fcp.ico")
    icon_image = Image.open(icon_path)
    menu = (
        MenuItem("Start Streamlit", lambda icon, item: threading.Thread(target=start_streamlit).start()),
        MenuItem("Stop Streamlit", lambda icon, item: stop_streamlit()),
        MenuItem("Restart Streamlit", restart_streamlit),
        MenuItem("Open in Browser", open_in_browser),
        MenuItem("Quit", lambda icon, item: (stop_streamlit(), icon.stop()))
    )
    tray_icon = Icon("StreamlitTray", icon_image, "Streamlit Tray", menu)
    return tray_icon

if __name__ == "__main__":
    # 设置正确的工作目录
    project_dir = setup_working_directory()
    print(f"工作目录: {project_dir}")
    # 显示检测到的Python执行文件路径
    python_path, is_venv = get_python_executable()
    print(f"检测到的Python执行文件: {python_path}")
    # 检查是否使用了虚拟环境
    if is_venv:
        print("✓ 使用虚拟环境中的Python")
    else:
        print("! 使用系统Python（未检测到虚拟环境）")
    # Launch Streamlit on startup
    threading.Thread(target=start_streamlit).start()
    # Start the tray icon event loop
    tray = build_tray()
    tray.run()

