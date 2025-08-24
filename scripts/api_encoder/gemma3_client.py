#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心情描述生成器
根据航班旅客数量和收入生成描述心情的中文字词
"""

import google.generativeai as genai
import re
import threading
import random
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


def process_gemma_response(response_text: str) -> str:
    """
    处理Gemma API返回结果，根据不同格式提取中文内容并生成文件名
    处理逻辑：
    1. 如果有**，找下一对**，中间的中文存入list，随机使用其中的两个index作为文件名
    2. 如果有序号，每个序号的中文存入list，随机使用其中的两个index作为文件名  
    3. 如果都没有，则直接把中文部分作为文件名
    Args:
        response_text: Gemma API返回的原始文本  
    Returns:
        str: 处理后的文件名用中文描述
    """
    if not response_text:
        return "未知心情"
    chinese_list = []
    # 方法1：查找**包围的中文内容
    star_pattern = r'\*\*([^*]*?)\*\*'
    star_matches = re.findall(star_pattern, response_text)
    if star_matches:
        for match in star_matches:
            chinese_text = clean_chinese_text(match)
            if chinese_text and len(chinese_text) >= 2:  # 至少2个中文字符
                chinese_list.append(chinese_text)
    # 方法2：查找序号后的中文内容 (如 "1. 阳光暖心" 或 "1、快乐无比")
    if not chinese_list:
        # 更精确的序号匹配模式
        number_pattern = r'\d+[.\s、]\s*([^\d\n]*?)(?=[.\s]*\d+[.\s、]|$)'
        number_matches = re.findall(number_pattern, response_text)
        for match in number_matches:
            # 清理匹配结果，去除标点符号
            cleaned_match = re.sub(r'[。，、；！？\s]+', '', match.strip())
            chinese_text = clean_chinese_text(cleaned_match)
            if chinese_text and len(chinese_text) >= 2:
                chinese_list.append(chinese_text)
    # 方法3：如果前两种方法都没找到，直接提取所有中文
    if not chinese_list:
        all_chinese = clean_chinese_text(response_text)
        if all_chinese:
            # 尝试按标点符号分割
            segments = re.split(r'[，。、；！？\s]+', all_chinese)
            for segment in segments:
                if len(segment) >= 2:
                    chinese_list.append(segment)
    # 如果还是没有找到，返回默认值
    if not chinese_list:
        return "默认心情"
    # 随机选择1-2个词组合成文件名
    if len(chinese_list) == 1:
        return chinese_list[0][:8]  # 限制长度
    elif len(chinese_list) >= 2:
        # 随机选择两个不同的index
        indices = random.sample(range(len(chinese_list)), min(2, len(chinese_list)))
        selected_words = [chinese_list[i] for i in indices]
        combined = ''.join(selected_words)
        return combined[:8]  # 限制总长度
    return chinese_list[0][:8]


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
        # 创建模型（使用1B模型，增强随机性策略）
        model = genai.GenerativeModel("gemma-3-1b-it")
        # 构建多样化提示词，增加随机性
        random_element = random.randint(1, 10000)
        prompt_styles = [
            f"用十个字以内的中文描述{mood_category}心情。随机种子{random_element}",
            f"十个字以内{mood_category}的心情状态，用中文简短描述。#{random_element}",
            f"工作时{mood_category}的感觉，中文表达，不超过十字。ID{random_element}",
            f"描述{mood_category}心境，简洁中文，最多十个字。编号{random_element}",
        ]
        prompt = random.choice(prompt_styles)
        # 使用多线程实现超时
        result = [None]
        exception = [None]
        print(f"prompt: {prompt}")

        def api_call():
            try:
                # 简单配置，只使用温度参数增加随机性
                generation_config = {
                    'temperature': 1.0,  # 适中温度平衡质量和随机性
                    'max_output_tokens': 120,  # 减少输出长度提高速度
                    'top_p': 0.9,  # 添加top_p提高多样性
                }
                response = model.generate_content(prompt, generation_config=generation_config)
                result[0] = response.text.strip()
                print(f"response: {response.text.strip()}")
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

