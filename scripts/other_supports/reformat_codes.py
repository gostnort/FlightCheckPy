#!/usr/bin/env python3
"""
Python代码格式化工具 - 重新格式化ui/目录下的Python文件以符合用户偏好的样式

功能特点:
- 顶级类之间使用3个空行
- 顶级函数之间使用2个空行
- 缩进块内部不使用空行（函数/方法/类主体内部）
- 支持任意缩进级别的代码块
- 正确处理装饰器和注释

使用方法:
  python scripts/other_supports/reformat_codes.py [文件或目录...]

如果不提供参数，默认处理ui/目录
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def read_text(path: Path) -> str:
    """
    读取文本文件内容
    使用UTF-8编码，忽略解码错误以确保程序稳定运行
    Args:
        path (Path): 文件路径
    Returns:
        str: 文件内容
    """
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str) -> None:
    """
    写入文本文件内容
    使用UTF-8编码保存格式化后的内容
    Args:
        path (Path): 文件路径
        content (str): 要写入的内容
    """
    path.write_text(content, encoding="utf-8")


def remove_inner_blank_lines(lines: List[str]) -> List[str]:
    """
    移除缩进块内部的空行
    保留分隔顶级语句的空行，但移除函数/方法/类内部以及条件块内部的空行
    规则说明:
    - 如果前一行是非空行且有缩进（>0），则移除该空行
    - 这包括缩进块内的注释前面的空行
    - 保留顶级语句（缩进为0）之间的空行，用于逻辑分隔
    处理逻辑:
    1. 预计算每行的下一个非空行位置（向后查找）
    2. 遍历每一行，判断是否为需要移除的空行
    3. 保留顶级边界处的空行，移除块内部的空行
    Args:
        lines (List[str]): 文件的所有行列表
    Returns:
        List[str]: 处理后的行列表，已移除不必要的空行
    """
    result: List[str] = []  # 存储处理结果
    n = len(lines)  # 总行数


    def indent_of(idx: int) -> int:
        """
        计算指定行的缩进级别
        对于空行或注释行，返回其本身的缩进；对于代码行，计算实际缩进
        Args:
            idx (int): 行索引
        Returns:
            int: 缩进空格数
        """
        raw = lines[idx]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            # 对于空行或注释行，返回行本身的缩进
            return len(raw) - len(raw.lstrip(" \t"))
        else:
            # 对于代码行，计算实际缩进（去除制表符和空格）
            return len(raw) - len(raw.lstrip(" \t"))
    # 预计算每行的下一个非空行位置（从后向前扫描，提高效率）
    next_non_empty: List[int] = [-1] * n  # 初始化为-1，表示没有找到
    j = n - 1  # 从最后一行开始向前遍历
    last_seen = -1  # 记录最近找到的非空行位置
    while j >= 0:
        if lines[j].strip() != "":  # 如果当前行不是空行
            last_seen = j  # 更新最近的非空行位置
        next_non_empty[j] = last_seen  # 记录当前位置的下一个非空行
        j -= 1
    prev_non_empty_indent = 0  # 上一行非空行的缩进级别
    for i, line in enumerate(lines):
        if line.strip() == "":  # 当前行为空行
            nxt = next_non_empty[i]  # 获取下一个非空行位置
            if nxt == -1:
                # 文件末尾的连续空行，暂时保留，稍后处理
                result.append(line)
                continue
            next_indent = indent_of(nxt)  # 计算下一个非空行的缩进
            # 判断是否应该移除此空行
            # 条件1：前一行和下一行都有缩进（都在代码块内）
            # 条件2：前一行有缩进，且下一行是注释且缩进级别合适
            if (prev_non_empty_indent > 0 and next_indent > 0) or \
               (prev_non_empty_indent > 0 and lines[nxt].strip().startswith("#") and indent_of(nxt) >= prev_non_empty_indent):
                # 在代码块内部，应移除此空行
                continue
            # 其他情况：保留空行（顶级边界或文件结构分隔）
            result.append(line)
            continue
        # 非空行：记录其缩进级别，用于下一行的判断
        prev_non_empty_indent = indent_of(i)
        result.append(line)
    return result


def find_block_starts(lines: List[str]) -> Dict[int, str]:
    """
    查找所有代码块的起始位置（任意缩进级别）
    识别类定义和函数定义，并将装饰器行关联到对应的函数/类
    识别规则:
    1. 直接识别以"class "或"def "开头的行
    2. 对于装饰器(@开头)，查找后续的函数/类定义
    3. 确保装饰器和对应定义有相同的缩进级别
    4. 支持连续多个装饰器的情况
    处理逻辑:
    - 遍历每一行，寻找代码块定义
    - 对于装饰器，向前查找对应的函数/类
    - 记录行号到块类型的映射关系
    Args:
        lines (List[str]): 文件的所有行列表
    Returns:
        Dict[int, str]: 行号到块类型("class"或"def")的映射字典
    """
    idx_to_type: Dict[int, str] = {}  # 存储行号到块类型的映射
    n = len(lines)  # 总行数
    i = 0  # 当前处理的行索引
    while i < n:
        raw = lines[i]  # 当前行的原始内容
        stripped = raw.lstrip()  # 去除左侧空白后的内容
        # 直接识别类定义
        if stripped.startswith("class "):
            idx_to_type[i] = "class"
        # 直接识别函数定义
        elif stripped.startswith("def "):
            idx_to_type[i] = "def"
        # 处理装饰器情况
        elif stripped.startswith("@"):
            # 获取当前装饰器的缩进级别
            curr_indent = len(raw) - len(stripped)
            j = i + 1  # 从下一行开始查找
            block_type = None  # 记录找到的块类型
            # 向前查找对应的函数或类定义
            while j < n:
                nxt_raw = lines[j]
                nxt_stripped = nxt_raw.lstrip()
                # 跳过空行
                if nxt_stripped == "":
                    j += 1
                    continue
                # 检查缩进是否匹配
                next_indent = len(nxt_raw) - len(nxt_stripped)
                if next_indent != curr_indent:
                    # 缩进不匹配，停止查找
                    break
                # 找到对应的类定义
                if nxt_stripped.startswith("class "):
                    block_type = "class"
                    break
                # 找到对应的函数定义
                elif nxt_stripped.startswith("def "):
                    block_type = "def"
                    break
                # 遇到另一个装饰器，继续查找
                elif nxt_stripped.startswith("@"):
                    j += 1
                    continue
                # 其他情况，停止查找
                else:
                    break
            # 如果找到了对应的块类型，将装饰器行标记为此类型
            if block_type:
                idx_to_type[i] = block_type
        i += 1  # 处理下一行
    return idx_to_type


def enforce_block_spacing(lines: List[str]) -> List[str]:
    """
    强制执行代码块间距规则
    确保类前有3个空行，函数前有2个空行（适用于任意缩进级别）
    间距规则:
    - 类定义前：3个空行（包括装饰器行）
    - 函数定义前：2个空行（包括装饰器行）
    - 文件开头的内容：不插入前导空行
    - 移除已存在的多余空行，插入正确数量
    处理逻辑:
    1. 首先找到所有代码块的起始位置
    2. 遍历每一行，遇到块定义时调整前面的空行数量
    3. 移除多余的空行，插入正确数量的空行
    4. 对于文件开头的块，不添加前导空行
    Args:
        lines (List[str]): 文件的所有行列表
    Returns:
        List[str]: 处理后的行列表，已调整块间距
    """
    # 获取所有代码块的起始位置和类型
    idx_to_type = find_block_starts(lines)
    result: List[str] = []  # 存储处理结果
    i = 0  # 当前处理的行索引
    n = len(lines)  # 总行数
    while i < n:
        # 检查当前行是否是代码块的起始行
        if i in idx_to_type:
            # 根据块类型确定需要的空行数量
            need = 3 if idx_to_type[i] == "class" else 2
            # 移除结果列表末尾已存在的空行
            while result and result[-1].strip() == "":
                result.pop()
            # 只有当结果列表不为空时（即不在文件开头），才插入空行
            if result:
                for _ in range(need):
                    result.append("\n")
            # 添加当前行（块定义行）
            result.append(lines[i])
            i += 1
            continue
        # 普通行，直接添加到结果中
        result.append(lines[i])
        i += 1
    return result


def normalize_newlines(text: str) -> str:
    """
    规范化换行符
    将Windows(CRLF)和Mac(CR)格式的换行符统一转换为Unix(LF)格式
    Args:
        text (str): 原始文本内容
    Returns:
        str: 规范化后的文本内容
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def reformat_content(text: str) -> str:
    """
    执行完整的代码重新格式化流程
    按照预定的规则重新排列代码的空行和间距
    处理步骤:
    1. 规范化换行符格式
    2. 移除缩进块内部的空行
    3. 强制执行代码块间距规则
    4. 压缩顶级多余的连续空行
    5. 移除文件末尾的多余空行
    Args:
        text (str): 原始文件内容
    Returns:
        str: 格式化后的文件内容
    """
    # 第一步：规范化换行符
    text = normalize_newlines(text)
    # 拆分文本为行列表，确保每行都以换行符结尾
    lines = [ln if ln.endswith("\n") else ln + "\n" for ln in text.split("\n")]
    # 第二步：移除缩进块内部的空行
    lines = remove_inner_blank_lines(lines)
    # 第三步：强制执行代码块间距规则
    lines = enforce_block_spacing(lines)
    # 第四步：压缩顶级多余的连续空行
    collapsed: List[str] = []
    blank_run = 0  # 连续空行计数器
    for ln in lines:
        if ln.strip() == "":  # 当前行为空行
            blank_run += 1
            # 在顶级位置最多允许2个连续空行（类/函数间距已由前一步处理）
            if blank_run <= 2:
                collapsed.append(ln)
        else:
            blank_run = 0  # 重置计数器
            collapsed.append(ln)
    # 第五步：移除文件末尾的多余空行，但保留一个换行符
    while collapsed and collapsed[-1].strip() == "":
        collapsed.pop()
    collapsed.append("\n")  # 确保文件以单个换行符结尾
    return "".join(collapsed)


def collect_python_files(paths: List[Path]) -> List[Path]:
    """
    收集所有需要处理的Python文件
    从指定的路径列表中递归查找所有.py文件
    处理逻辑:
    - 如果路径是文件且后缀为.py，直接添加
    - 如果路径是目录，递归查找其中的所有.py文件
    - 返回所有找到的Python文件的路径列表
    Args:
        paths (List[Path]): 要搜索的路径列表（文件或目录）
    Returns:
        List[Path]: 找到的所有Python文件路径
    """
    files: List[Path] = []  # 存储找到的Python文件
    for p in paths:
        if p.is_file() and p.suffix == ".py":
            # 直接添加Python文件
            files.append(p)
        elif p.is_dir():
            # 递归查找目录中的所有Python文件
            files.extend(list(p.rglob("*.py")))
    return files


def main() -> int:
    """
    主程序入口
    解析命令行参数，查找目标文件并执行格式化操作
    执行流程:
    1. 查找项目根目录（通过寻找requirements.txt或README.md）
    2. 解析命令行参数，确定要处理的文件/目录
    3. 收集所有需要处理的Python文件
    4. 对每个文件执行格式化操作
    5. 报告格式化结果
    Returns:
        int: 程序退出码（0表示成功）
    """
    # 第一步：查找项目根目录
    current = Path(__file__).resolve().parent
    repo_root = current
    while repo_root.parent != repo_root:  # 确保没有到达文件系统根目录
        if (repo_root / "requirements.txt").exists() or (repo_root / "README.md").exists():
            break  # 找到项目根目录的标志文件
        repo_root = repo_root.parent
    # 第二步：解析命令行参数
    args = sys.argv[1:]
    target_paths: List[Path] = []
    if args:
        # 处理用户指定的路径
        for a in args:
            if Path(a).is_absolute():
                p = Path(a)  # 绝对路径直接使用
            else:
                p = Path.cwd() / a  # 相对路径相对于当前工作目录
            p = p.resolve()  # 解析为绝对路径
            target_paths.append(p)
    else:
        # 默认处理ui目录
        target_paths = [repo_root / "ui"]
    # 第三步：收集所有需要处理的Python文件
    targets = collect_python_files(target_paths)
    # 第四步：对每个文件执行格式化
    changed: List[Tuple[Path, int]] = []  # 记录被修改的文件
    for path in targets:
        original = read_text(path)  # 读取原始内容
        reformatted = reformat_content(original)  # 格式化内容
        # 如果内容有变化，写入文件并记录
        if reformatted != original:
            write_text(path, reformatted)
            changed.append((path, len(reformatted)))
    # 第五步：报告格式化结果
    if args:
        scope = ", ".join(args)
    else:
        scope = "ui/"
    print(f"Reformatted {len(changed)} files in {scope}.")
    for p, _ in changed:
        print(f" - {p.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

