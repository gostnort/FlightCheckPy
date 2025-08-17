#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心情描述生成器
根据航班旅客数量和收入生成描述心情的中文字词
"""

import google.generativeai as genai
import re
import threading
from scripts.api_encoder.api_encoder import APIEncoder


class TimeoutException(Exception):
    """超时异常"""
    pass


def clean_chinese_text(text: str) -> str:
    """
    清理文本，只保留中文字符
    Args:
        text: 原始文本
    Returns:
        只包含中文字符的文本
    """
    # 使用正则表达式只保留中文字符
    chinese_pattern = r'[\u4e00-\u9fff]+'
    chinese_chars = re.findall(chinese_pattern, text)
    return ''.join(chinese_chars)


def calculate_mood_category(cash: float, total_amount: float) -> str:
    """
    根据现金和总金额比例计算心情类别
    Args:
        cash: 现金金额
        total_amount: 总金额
    Returns:
        心情类别描述
    """
    if total_amount <= 0:
        return "数据异常"
    ratio = cash / total_amount
    if ratio <= 0.05:  # 5%及以下
        return "轻松"
    elif ratio <= 0.10:  # 10%及以下
        return "有点累"
    elif ratio <= 0.30:  # 30%及以下
        return "惨兮兮"
    else:  # 50%以上
        return "惨绝人寰"


def generate_mood_description(cash: float, total_amount: float, username: str) -> str:
    """
    生成心情描述
    Args:
        cash: 现金金额
        total_amount: 总金额
        username: 用户名
    Returns:
        心情描述的中文字词
    """
    try:
        # 获取API密钥
        encoder = APIEncoder()
        api_key = encoder.decode_api_key(username)
        if not api_key:
            return "用户名错误"
        # 计算心情类别
        mood_category = calculate_mood_category(cash, total_amount)
        # 配置API
        genai.configure(api_key=api_key)
        # 创建模型（使用1B模型更快）
        model = genai.GenerativeModel("gemma-3-1b-it")
        # 构建提示词
        prompt = f"用十个字以内的中文描述这种{mood_category}的工作心情，只返回心情描述"
        # 使用多线程实现超时
        result = [None]
        exception = [None]


        def api_call():
            try:
                response = model.generate_content(prompt)
                result[0] = response.text.strip()
            except Exception as e:
                exception[0] = e
        # 启动API调用线程
        thread = threading.Thread(target=api_call)
        thread.start()
        thread.join(timeout=4.0)  # 1秒超时
        if thread.is_alive():
            # 超时了
            return "心情失败"
        if exception[0]:
            raise exception[0]
        if result[0]:
            # 提取并清理文本
            raw_text = result[0]
            mood_text = clean_chinese_text(raw_text)
            # 确保返回的是中文心情描述
            if mood_text and len(mood_text) <= 10:
                return mood_text
            elif mood_text:
                # 如果超过10个字，截取前10个字
                return mood_text[:10]
        return "心情复杂"
    except Exception as e:
        print(f"生成心情描述时出错: {e}")
        return "系统异常"


def main():
    """主函数"""
    print("心情描述生成器")
    print("=" * 50)
    try:
        # 获取用户输入
        print("请输入您的用户名:")
        username = input("用户名: ").strip()
        if not username:
            print("用户名不能为空")
            return
        print("\n请输入财务信息:")
        try:
            cash = float(input("现金金额(元): "))
            total_amount = float(input("总金额(元): "))
        except ValueError:
            print("请输入有效的数字")
            return
        # 计算比例和生成心情描述
        ratio = cash / total_amount if total_amount > 0 else 0
        mood_category = calculate_mood_category(cash, total_amount)
        print(f"\n正在生成心情描述...")
        print(f"现金{cash}元，总金额{total_amount}元，比例{ratio:.1%}")
        print(f"心情类别: {mood_category}")
        mood = generate_mood_description(cash, total_amount, username)
        print(f"\n您的心情: {mood}")
    except ValueError as e:
        print(f"错误: {e}")
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()

