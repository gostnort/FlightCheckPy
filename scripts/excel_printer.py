#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel文件打印工具模块
直接调用Windows打印命令打印Excel文件，无需格式转换
"""

import subprocess
import os
from pathlib import Path
from typing import Tuple


def print_excel_file(filepath: str) -> Tuple[bool, str]:
    """
    打印Excel文件（直接打印，不转换格式）
    Args:
        filepath: Excel文件路径
    Returns:
        (成功标志, 错误信息)
    """
    # 检查文件是否存在
    if not os.path.exists(filepath):
        return False, f"文件不存在: {filepath}"
    # 检查是否为Windows系统
    if os.name != "nt":
        return False, "打印功能仅在Windows系统上可用"
    try:
        # 方法1: 使用PowerShell Start-Process命令
        try:
            cmd = ["powershell", "-Command", f'Start-Process "{filepath}" -Verb print']
            result = subprocess.run(cmd, check=False, capture_output=True, timeout=10)
            if result.returncode == 0:
                return True, "打印任务已发送到打印机"
            else:
                # 如果PowerShell失败，尝试方法2
                raise subprocess.CalledProcessError(result.returncode, cmd)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # 方法2: 使用os.startfile（Windows特有）
            try:
                os.startfile(filepath, "print")
                return True, "打印任务已发送到打印机"
            except Exception as e:
                return False, f"打印失败: {str(e)}"
    except Exception as e:
        return False, f"打印过程中发生错误: {str(e)}"

