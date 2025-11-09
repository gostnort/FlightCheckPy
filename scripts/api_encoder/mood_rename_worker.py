#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心情描述重命名工作进程模块
使用多进程在后台生成心情描述并重命名Excel文件
"""

import multiprocessing
import logging
import sys
from pathlib import Path


# 延迟导入 - 在进程内部导入，避免multiprocessing spawn问题


def generate_mood_description(cash: float, total_amount: float, username: str) -> str:
    """延迟导入并调用生成心情描述"""
    try:
        from scripts.api_encoder.gemma3_client import generate_mood_description as _gen

        return _gen(cash, total_amount, username)
    except ImportError as e:
        print(f"无法导入生成心情描述函数: {e}")
        return "系统异常"


# 配置日志 - 仅输出到控制台


def setup_logger() -> logging.Logger:
    """设置日志记录器，仅输出到控制台"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    # 清除已有的处理器
    logger.handlers = []
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    return logger


def _rename_worker_process(
    cash: float,
    total_amount: float,
    username: str,
    timestamp_file: str,
    fn: str,
    fd: str,
) -> None:
    """
    后台工作进程：生成心情描述并重命名文件
    Args:
        cash: 现金金额
        total_amount: 总金额
        username: 用户名
        timestamp_file: 带时间戳的文件路径
        fn: 航班号
        fd: 航班日期（已格式化字符串）
    """
    # 确保能找到 scripts 模块
    if str(Path(__file__).parent.parent.parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    # 设置日志记录器（仅控制台）
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("开始重命名进程")
    logger.info(f"timestamp_file={timestamp_file}")
    logger.info(f"cash={cash}, total_amount={total_amount}, username={username}")
    logger.info(f"航班信息: fn={fn}, fd={fd}")
    logger.info("=" * 60)
    try:
        # 生成心情描述 - 默认值为平静
        mood_description = "平静"
        if cash > 0 and total_amount > 0 and username != "unknown":
            logger.info("开始调用LLM生成心情描述...")
            try:
                mood_description = generate_mood_description(
                    cash, total_amount, username
                )
                logger.info(f"LLM返回心情描述: {mood_description}")
            except Exception as e:
                logger.error(f"LLM生成心情描述失败: {e}", exc_info=True)
                mood_description = "复杂"
        else:
            logger.info(
                f"跳过LLM调用: cash={cash}, total_amount={total_amount}, username={username}"
            )
        # 生成新文件名
        base_mood = mood_description
        attempt = 0
        new_filename = None
        new_filepath = None
        logger.info(f"生成新文件名，心情描述: {mood_description}")
        while attempt < 100:  # 最多尝试100次
            if attempt == 0:
                filename = f"{fn}_{fd}_EMD_{mood_description}.xlsx"
            else:
                filename = f"{fn}_{fd}_EMD_{base_mood}{attempt}.xlsx"
            file_dir = Path(timestamp_file).parent
            new_filepath = file_dir / filename
            # 检查文件是否已存在
            if not new_filepath.exists():
                new_filename = filename
                logger.info(f"找到可用文件名: {new_filename}")
                break
            logger.info(f"文件名已存在，尝试下一个: {filename}")
            attempt += 1
        if new_filename is None:
            error_msg = "无法生成唯一文件名，已尝试100次"
            logger.error(error_msg)
            raise Exception(error_msg)
        # 重命名文件
        old_path = Path(timestamp_file)
        new_path = Path(new_filepath)
        logger.info(f"准备重命名文件: {old_path} -> {new_path}")
        # 检查原文件是否存在
        if not old_path.exists():
            error_msg = f"原文件不存在: {timestamp_file}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        # 如果目标文件已存在（理论上不应该），先删除
        if new_path.exists() and new_path != old_path:
            logger.warning(f"目标文件已存在，将删除: {new_path}")
            new_path.unlink()
        # 执行重命名
        old_path.rename(new_path)
        logger.info(f"文件重命名成功: {new_filename}")
        logger.info(f"重命名完成，新文件名: {new_filename}")
    except Exception as e:
        # 记录错误
        error_msg = str(e)
        logger.error(f"重命名过程中发生错误: {error_msg}", exc_info=True)


def start_mood_rename_process(
    cash: float,
    total_amount: float,
    username: str,
    timestamp_file: str,
    fn: str,
    fd: str,
) -> multiprocessing.Process:
    """
    启动后台进程进行心情描述生成和文件重命名
    Args:
        cash: 现金金额
        total_amount: 总金额
        username: 用户名
        timestamp_file: 带时间戳的文件路径
        fn: 航班号
        fd: 航班日期（已格式化字符串）
    Returns:
        启动的进程对象
    """
    # 使用主进程的logger记录启动信息
    main_logger = logging.getLogger(__name__)
    if not main_logger.handlers:
        logging.basicConfig(level=logging.INFO)
        main_logger = logging.getLogger(__name__)
    main_logger.info(f"启动重命名后台进程: timestamp_file={timestamp_file}")
    # Windows上需要设置multiprocessing启动方法
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # 已经设置过了
    process = multiprocessing.Process(
        target=_rename_worker_process,
        args=(cash, total_amount, username, timestamp_file, fn, fd),
        daemon=False,
    )
    process.start()
    main_logger.info(f"后台进程已启动，PID: {process.pid}")
    return process
