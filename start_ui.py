import os
import sys
import webbrowser
import subprocess
from pystray import Icon, MenuItem
from PIL import Image
from winotify import Notification, audio
import time
import requests
import threading

streamlit_proc = None

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
    if streamlit_proc and streamlit_proc.poll() is None:
        notify_winotify("Streamlit Launcher", "Streamlit is already running!", icon_path="resources/fcp.ico")
        return  # already running
    # 先停止现有的进程
    stop_streamlit()
    # 等待一小段时间确保进程完全终止
    time.sleep(1)
    notify_winotify("Streamlit Launcher", "Starting Streamlit...", icon_path="resources/fcp.ico")
    # On Windows, use pythonw to suppress console
    python_exec = "pythonw" if sys.platform.startswith("win") else "python3"
    # Build your custom command
    cmd = [
        python_exec,
        "-m", "streamlit", "run", "ui/main.py",
        "--server.address", "0.0.0.0",
        "--server.port", "8501",
        "--browser.serverAddress", "localhost",
        "--server.headless", "false"
    ]
    streamlit_proc = subprocess.Popen(cmd,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL)
    def watch_and_notify():
        if wait_for_streamlit():
            notify_winotify("Streamlit Launcher", "Streamlit is ready!", icon_path="resources/fcp.ico")
        else:
            notify_winotify("Streamlit Launcher", "Streamlit failed to start in time.", icon_path="resources/fcp.ico")

    threading.Thread(target=watch_and_notify, daemon=True).start()
    return False


def stop_streamlit():
    global streamlit_proc
    if streamlit_proc:
        try:
            # 强制终止进程
            streamlit_proc.kill()
            streamlit_proc.wait(timeout=5)
            notify_winotify("Streamlit Launcher", "Streamlit stopped successfully!", icon_path="resources/fcp.ico")
        except subprocess.TimeoutExpired:
            # 如果超时，强制杀死进程
            streamlit_proc.kill()
            notify_winotify("Streamlit Launcher", "Streamlit force stopped!", icon_path="resources/fcp.ico")
        except Exception as e:
            print(f"Error stopping streamlit: {e}")
        finally:
            streamlit_proc = None
    else:
        notify_winotify("Streamlit Launcher", "No Streamlit process to stop!", icon_path="resources/fcp.ico")


def restart_streamlit(icon, item):
    threading.Thread(target=lambda: (stop_streamlit(), start_streamlit())).start()


def open_in_browser(icon, item):
    try:
        webbrowser.open("http://localhost:8501")
        notify_winotify("Streamlit Launcher", "Opening browser...", icon_path="resources/fcp.ico")
    except Exception as e:
        notify_winotify("Streamlit Launcher", f"Failed to open browser: {e}", icon_path="resources/fcp.ico")


def build_tray():
    icon_image = Image.open("resources/fcp.ico")
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
    # Launch Streamlit on startup
    threading.Thread(target=start_streamlit).start()
    # Start the tray icon event loop
    tray = build_tray()
    tray.run()