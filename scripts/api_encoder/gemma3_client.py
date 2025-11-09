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
    清理文本，只保留中文字符，移除所有标点符号（中英文）
    Args:
        text: 原始文本
    Returns:
        只包含中文字符的文本（无标点符号）
    """
    # 移除所有标点符号（英文和中文）
    # 英文标点: . , ! ? ; : - _ ( ) [ ] { } " ' ` ~ @ # $ % ^ & * + = | \ / < >
    # 中文标点: 。，、；！？：""''（）【】《》〈〉「」『』
    punctuation_pattern = (
        r'[。，、；！？：""'
        r"（）【】《》〈〉「」『』\.\,\!\?\;\:\-\_\(\)\[\]\{\}\"\'"
        r"\`\~\@\#\$\%\^\&\*\+\=\|\\\/\<\>]+"
    )
    text_no_punct = re.sub(punctuation_pattern, "", text)
    # 使用正则表达式只保留中文字符
    chinese_pattern = r"[\u4e00-\u9fff]+"
    chinese_chars = re.findall(chinese_pattern, text_no_punct)
    return "".join(chinese_chars)


def process_gemma_response(response_text: str) -> str:
    """
    处理Gemma API返回结果，提取中文内容并移除所有标点符号
    Args:
        response_text: Gemma API返回的原始文本
    Returns:
        str: 处理后的文件名用中文描述（无标点符号）
    """
    if not response_text:
        return "未知心情"
    # 直接提取所有中文字符并移除标点符号
    cleaned_text = clean_chinese_text(response_text)
    if cleaned_text:
        # 限制长度为15个字符
        trimmed = cleaned_text[:15]
        return trimmed if trimmed else "默认心情"
    return "默认心情"


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
        if total_amount <= 0:
            mood_category = "数据异常"
        else:
            ratio = cash / total_amount
            if ratio <= 0.05:  # 5%及以下
                mood_category = "轻松"
            elif ratio <= 0.10:  # 10%及以下
                mood_category = "有点累"
            elif ratio <= 0.20:  # 20%及以下
                mood_category = "一般般"
            elif ratio <= 0.30:  # 30%及以下
                mood_category = "惨兮兮"
            elif ratio <= 0.50:  # 50%及以下
                mood_category = "没人性"
            else:  # 50%以上
                mood_category = "惨绝人寰"
        # 配置API
        genai.configure(api_key=api_key)
        # 创建模型（使用12B模型）
        model = genai.GenerativeModel("gemma-3-12b-it")
        # 构建提示词
        prompt = f'用十五个字描述"{mood_category}"相关的心情'
        # 使用多线程实现超时
        result = [None]
        exception = [None]
        print(f"prompt: {prompt}")

        def api_call():
            try:
                # 简单配置，只使用温度参数增加随机性
                generation_config = {
                    "temperature": 1.2,  # 适中温度平衡质量和随机性
                    "max_output_tokens": 120,  # 减少输出长度提高速度
                    "top_p": 0.9,  # 添加top_p提高多样性
                }
                response = model.generate_content(
                    prompt, generation_config=generation_config
                )
                result[0] = response.text.strip()
                print(f"response: {response.text.strip()}")
            except Exception as e:
                exception[0] = e

        # 启动API调用线程
        thread = threading.Thread(target=api_call)
        thread.start()
        thread.join(timeout=6.0)  # 6秒超时
        if thread.is_alive():
            # 超时了
            return "心情失败"
        if exception[0]:
            raise exception[0]
        if result[0]:
            # 使用新的处理逻辑来提取心情描述
            raw_text = result[0]
            processed_mood = process_gemma_response(raw_text)
            return processed_mood if processed_mood else "心情复杂"
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
