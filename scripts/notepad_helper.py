#!/usr/bin/env python3
"""
记事本辅助工具 - Windows系统下打开/前置记事本并粘贴内容
"""

import subprocess
import time
import threading


# 模块级别的记事本进程ID和窗口句柄跟踪
_notepad_pid = None
_notepad_hwnd = None


def get_notepad_pid_and_hwnd():
    """获取记事本的进程ID和窗口句柄"""
    global _notepad_pid, _notepad_hwnd
    try:
        import win32gui
        import psutil

        def enum_windows_callback(hwnd_param, result):
            if win32gui.IsWindowVisible(hwnd_param):
                window_title = win32gui.GetWindowText(hwnd_param)
                class_name = win32gui.GetClassName(hwnd_param)
                if "notepad" in window_title.lower() or class_name == "Notepad":
                    # 获取窗口对应的进程ID
                    try:
                        _, pid = win32gui.GetWindowThreadProcessId(hwnd_param)
                        result.append((pid, hwnd_param))
                    except Exception:
                        pass
            return True

        result = []
        win32gui.EnumWindows(enum_windows_callback, result)
        if result:
            # 如果已跟踪PID，优先返回跟踪的窗口
            if _notepad_pid:
                for pid, hwnd in result:
                    if pid == _notepad_pid:
                        # 验证进程仍然存在
                        try:
                            psutil.Process(pid)
                            _notepad_hwnd = hwnd
                            return pid, hwnd
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # PID已失效，清除跟踪
                            _notepad_pid = None
                            _notepad_hwnd = None
                            break
            # 返回第一个找到的Notepad
            pid, hwnd = result[0]
            _notepad_pid = pid
            _notepad_hwnd = hwnd
            return pid, hwnd
        return None, None
    except ImportError:
        # 如果没有pywin32或psutil，使用备用方法
        try:
            import psutil

            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if proc.info["name"] and proc.info["name"].lower() == "notepad.exe":
                        pid = proc.info["pid"]
                        if _notepad_pid == pid:
                            return pid, None
                        elif _notepad_pid is None:
                            _notepad_pid = pid
                            return pid, None
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            pass
        return None, None
    except Exception:
        return None, None


def is_notepad_running():
    """检查跟踪的Notepad进程是否正在运行"""
    global _notepad_pid
    if _notepad_pid is None:
        return False
    try:
        import psutil

        psutil.Process(_notepad_pid)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        _notepad_pid = None
        _notepad_hwnd = None
        return False
    except ImportError:
        # 如果没有psutil，使用tasklist命令（Windows）
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {_notepad_pid}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if str(_notepad_pid) in result.stdout:
                return True
            else:
                _notepad_pid = None
                _notepad_hwnd = None
                return False
        except Exception:
            return False


def open_or_focus_notepad():
    """打开Notepad或将其窗口置于前台，并记住PID"""
    global _notepad_pid, _notepad_hwnd
    try:
        # 首先检查是否已有跟踪的Notepad进程
        if is_notepad_running():
            # 使用跟踪的窗口句柄
            if _notepad_hwnd:
                try:
                    import win32gui
                    import win32con

                    # 先恢复窗口（如果最小化）
                    win32gui.ShowWindow(_notepad_hwnd, win32con.SW_RESTORE)
                    time.sleep(0.2)
                    # 激活窗口
                    win32gui.SetForegroundWindow(_notepad_hwnd)
                    time.sleep(0.3)
                    return True
                except Exception:
                    pass
        # 尝试查找现有的Notepad窗口
        pid, hwnd = get_notepad_pid_and_hwnd()
        if pid and hwnd:
            _notepad_pid = pid
            _notepad_hwnd = hwnd
            try:
                import win32gui
                import win32con

                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
                return True
            except Exception:
                pass
        # 如果没有找到，启动新的Notepad实例
        proc = subprocess.Popen(["notepad.exe"], shell=True)
        time.sleep(1.0)  # 等待Notepad启动
        # 获取新启动的Notepad PID和窗口句柄
        pid, hwnd = get_notepad_pid_and_hwnd()
        if pid:
            _notepad_pid = pid
            _notepad_hwnd = hwnd
        else:
            # 如果无法获取窗口句柄，至少记住PID
            try:
                _notepad_pid = proc.pid
            except Exception:
                pass
        return True
    except Exception as e:
        raise Exception(f"无法打开或激活Notepad: {str(e)}")


def _paste_to_notepad_internal(content):
    """内部函数：将内容复制到剪贴板并粘贴到跟踪的Notepad PID"""
    global _notepad_pid, _notepad_hwnd
    try:
        import pyperclip
        import pyautogui

        # 确保Notepad在前台（使用跟踪的PID）
        open_or_focus_notepad()
        time.sleep(0.5)  # 增加等待时间，确保窗口完全激活
        # 将内容复制到剪贴板
        pyperclip.copy(content)
        time.sleep(0.3)  # 增加等待时间，确保剪贴板操作完成
        # 使用跟踪的窗口句柄
        hwnd = _notepad_hwnd
        if not hwnd:
            # 如果窗口句柄丢失，尝试重新获取
            pid, hwnd = get_notepad_pid_and_hwnd()
            if pid == _notepad_pid:
                _notepad_hwnd = hwnd
        # 确保窗口在前台
        if hwnd:
            try:
                import win32gui
                import win32con

                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except ImportError:
                pass
        # 尝试使用Windows API SendMessage方法（更可靠）
        if hwnd:
            try:
                import win32gui
                import win32con
                import win32clipboard

                # 验证剪贴板内容
                win32clipboard.OpenClipboard()
                try:
                    clipboard_data = win32clipboard.GetClipboardData()
                    if clipboard_data == content:
                        # 使用SendMessage发送WM_PASTE消息到跟踪的窗口
                        win32gui.SendMessage(hwnd, win32con.WM_PASTE, 0, 0)
                        win32clipboard.CloseClipboard()
                        time.sleep(0.2)
                        return True
                finally:
                    try:
                        win32clipboard.CloseClipboard()
                    except Exception:
                        pass
            except ImportError:
                pass
            except Exception:
                # 如果Windows API方法失败，回退到pyautogui
                pass
        # 回退方法：使用pyautogui模拟Ctrl+V
        # 确保窗口在前台
        if hwnd:
            try:
                import win32gui

                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
            except Exception:
                pass
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)  # 等待粘贴完成
        return True
    except ImportError as e:
        missing_module = str(e).split("'")[1] if "'" in str(e) else "未知模块"
        raise Exception(
            f"缺少必需的模块: {missing_module}。请安装 pyperclip 和 pyautogui"
        )
    except Exception as e:
        raise Exception(f"粘贴到Notepad失败: {str(e)}")


def paste_to_notepad(content):
    """将内容复制到剪贴板并粘贴到跟踪的Notepad PID（在后台线程中执行）"""
    # 在后台线程中执行，避免阻塞主线程
    thread = threading.Thread(
        target=_paste_to_notepad_internal, args=(content,), daemon=True
    )
    thread.start()
    return True


def open_notepad_with_content(content):
    """打开Notepad并将内容粘贴到当前光标位置（主函数）"""
    try:
        paste_to_notepad(content)
        return True
    except Exception as e:
        raise Exception(f"操作失败: {str(e)}")
