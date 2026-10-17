import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# 设置环境变量以解决所有Python进程的编码问题（包括子进程）
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"  # Python 3.7+ 强制使用UTF-8模式

import requests
from PIL import Image
from pystray import Icon, MenuItem
from winotify import Notification, audio

# 确保当前进程的标准流使用UTF-8编码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

streamlit_proc = None


def project_root() -> Path:
    """脚本所在目录就是项目根目录。"""
    return Path(__file__).resolve().parent


def setup_working_directory():
    """
    设置正确的工作目录为脚本所在目录
    确保资源文件能正确访问
    """
    root = project_root()
    os.chdir(root)
    return str(root)


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径
    Args:
        relative_path: 相对于项目根目录的路径
    Returns:
        str: 资源文件的绝对路径
    """
    return str(project_root() / relative_path)


_env_ready = False


def ensure_uv_environment() -> Path:
    """用 uv 准备 .venv，并按 requirements.txt 安装依赖。"""
    global _env_ready
    root = project_root()
    venv_dir = root / ".venv"
    if _env_ready and (venv_dir / "Scripts" / "python.exe").exists():
        return venv_dir
    uv_path = shutil.which("uv")
    if not uv_path:
        raise FileNotFoundError("uv is not installed or not in PATH")
    if not (venv_dir / "Scripts" / "python.exe").exists():
        print("用 uv 创建虚拟环境...")
        subprocess.run(
            [uv_path, "venv", "--python", "3.12", str(venv_dir)],
            cwd=root,
            check=True,
        )
    print("用 uv 安装 requirements.txt ...")
    subprocess.run(
        [uv_path, "pip", "install", "-r", "requirements.txt", "--python", str(venv_dir)],
        cwd=root,
        check=True,
    )
    _env_ready = True
    return venv_dir


def get_python_executable():
    """
    获取 uv 虚拟环境里的 Python。托盘启动优先用 pythonw.exe。
    Returns:
        tuple: (python_path: str, is_venv: bool)
    """
    scripts_dir = project_root() / ".venv" / "Scripts"
    pythonw_path = scripts_dir / "pythonw.exe"
    python_path = scripts_dir / "python.exe"
    print(f"检查Python路径: {pythonw_path}")
    if pythonw_path.exists():
        print(f"✓ 使用虚拟环境Python: {pythonw_path}")
        return str(pythonw_path), True
    if python_path.exists():
        print(f"✓ 使用虚拟环境Python: {python_path}")
        return str(python_path), True
    print("! 未找到 uv 虚拟环境")
    return "", False


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
        duration="short",
    )
    toast.set_audio(audio.Default, loop=False)
    toast.show()


def wait_for_streamlit(
    url="http://localhost:8501/_stcore/health", timeout: int = 60
) -> bool:
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
        notify_winotify(
            "Streamlit Launcher", "Streamlit is already running!", icon_path=icon_path
        )
        return  # already running
    # 先停止现有的进程
    stop_streamlit()
    # 等待一小段时间确保进程完全终止
    time.sleep(1)
    notify_winotify("Streamlit Launcher", "Starting Streamlit...", icon_path=icon_path)
    try:
        ensure_uv_environment()
    except (OSError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"uv 环境准备失败: {exc}")
        notify_winotify(
            "Streamlit Launcher",
            "uv environment setup failed.",
            icon_path=icon_path,
        )
        return
    python_exec, is_venv = get_python_executable()
    print(f"启动Streamlit使用的Python: {python_exec}")
    print(f"是否使用虚拟环境: {'是' if is_venv else '否'}")
    if not python_exec:
        notify_winotify(
            "Streamlit Launcher",
            "uv virtual environment was not found.",
            icon_path=icon_path,
        )
        return
    # 构建自定义命令
    main_py_path = get_resource_path("ui/main.py")
    cmd = [
        python_exec,
        "-m",
        "streamlit",
        "run",
        main_py_path,
        "--server.address",
        "0.0.0.0",
        "--server.port",
        "8501",
        "--browser.serverAddress",
        "localhost",
        "--server.headless",
        "false",
    ]
    print(f"执行命令: {' '.join(cmd)}")
    # 确保环境变量传递给子进程，并使用UTF-8处理
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = str(project_root())

    streamlit_proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
    )

    def watch_and_notify():
        if wait_for_streamlit():
            notify_winotify(
                "Streamlit Launcher", "Streamlit is ready!", icon_path=icon_path
            )
        else:
            notify_winotify(
                "Streamlit Launcher",
                "Streamlit failed to start in time.",
                icon_path=icon_path,
            )

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
            notify_winotify(
                "Streamlit Launcher",
                "Streamlit stopped successfully!",
                icon_path=icon_path,
            )
        except subprocess.TimeoutExpired:
            # 如果超时，强制杀死进程
            streamlit_proc.kill()
            notify_winotify(
                "Streamlit Launcher", "Streamlit force stopped!", icon_path=icon_path
            )
        except Exception as e:
            print(f"Error stopping streamlit: {e}")
        finally:
            streamlit_proc = None
    else:
        notify_winotify(
            "Streamlit Launcher", "No Streamlit process to stop!", icon_path=icon_path
        )


def restart_streamlit(icon, item):
    threading.Thread(target=lambda: (stop_streamlit(), start_streamlit())).start()


def open_in_browser(icon, item):
    icon_path = get_resource_path("resources/fcp.ico")
    try:
        webbrowser.open("http://localhost:8501")
        notify_winotify("Streamlit Launcher", "Opening browser...", icon_path=icon_path)
    except Exception as e:
        notify_winotify(
            "Streamlit Launcher", f"Failed to open browser: {e}", icon_path=icon_path
        )


def build_tray():
    icon_path = get_resource_path("resources/fcp.ico")
    icon_image = Image.open(icon_path)
    menu = (
        MenuItem(
            "Start Streamlit",
            lambda icon, item: threading.Thread(target=start_streamlit).start(),
        ),
        MenuItem("Stop Streamlit", lambda icon, item: stop_streamlit()),
        MenuItem("Restart Streamlit", restart_streamlit),
        MenuItem("Open in Browser", open_in_browser),
        MenuItem("Quit", lambda icon, item: (stop_streamlit(), icon.stop())),
    )
    tray_icon = Icon("StreamlitTray", icon_image, "Flight Check-0.6.4", menu)
    return tray_icon


if __name__ == "__main__":
    # 设置正确的工作目录
    project_dir = setup_working_directory()
    print(f"工作目录: {project_dir}")
    # 显示环境变量设置情况
    print(f"PYTHONIOENCODING环境变量: {os.environ.get('PYTHONIOENCODING', '未设置')}")
    print(f"PYTHONUTF8环境变量: {os.environ.get('PYTHONUTF8', '未设置')}")
    try:
        ensure_uv_environment()
    except (OSError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"uv 环境准备失败: {exc}")
        raise SystemExit(1) from exc
    python_path, is_venv = get_python_executable()
    print(f"检测到的Python执行文件: {python_path}")
    if is_venv:
        print("✓ 使用 uv 虚拟环境中的 Python")
    else:
        print("! 未检测到 uv 虚拟环境")
    # Launch Streamlit on startup
    threading.Thread(target=start_streamlit).start()
    # Start the tray icon event loop
    tray = build_tray()
    tray.run()
