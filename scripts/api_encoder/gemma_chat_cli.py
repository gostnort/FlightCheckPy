#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemma3聊天命令行界面
提供完整的对话体验，支持多种Gemma模型，显示token使用情况
"""

import google.generativeai as genai
import threading
import time
import sys
from typing import Optional
from api_encoder import APIEncoder


class ChatInterface:
    """Gemma3聊天命令行界面类"""
    
    
    def __init__(self):
        """初始化聊天界面"""
        self.api_key = None
        self.username = None
        self.model = None
        self.model_name = None
        self.conversation_history = []
        self.max_input_tokens = 128000  # 默认输入token限制
        self.max_output_tokens = 8000   # 默认输出token限制
        self.current_tokens = 0
        
        # 可用的Gemma模型配置 (仅Google官方模型)
        self.available_models = {
            "1": {
                "name": "gemma-3-1b-it", 
                "display": "Gemma 3 1B IT (文本生成，轻量快速)",
                "max_input_tokens": 128000,
                "max_output_tokens": 8000,
                "optimization": "文本生成优化"
            },
            "2": {
                "name": "gemma-3-270m-it",
                "display": "Gemma 3 270M IT (超轻量，移动设备优化)",
                "max_input_tokens": 128000,
                "max_output_tokens": 8000,
                "optimization": "移动设备优化"
            },
            "3": {
                "name": "gemma-3-4b-it",
                "display": "Gemma 3 4B IT (图像文本转换，中等性能)", 
                "max_input_tokens": 128000,
                "max_output_tokens": 8000,
                "optimization": "图像文本处理优化"
            },
            "4": {
                "name": "gemma-3-12b-it",
                "display": "Gemma 3 12B IT (图像文本转换，高性能)",
                "max_input_tokens": 128000,
                "max_output_tokens": 8000,
                "optimization": "图像文本处理优化"
            },
            "5": {
                "name": "gemma-3-27b-it",
                "display": "Gemma 3 27B IT (图像文本转换，最高性能)",
                "max_input_tokens": 128000,
                "max_output_tokens": 8000,
                "optimization": "图像文本处理优化"
            },
            "6": {
                "name": "gemma-3n-E4B-it",
                "display": "Gemma 3N E4B IT (图像文本转换，实验版)",
                "max_input_tokens": 32000,
                "max_output_tokens": 32000,
                "optimization": "图像文本处理实验"
            },
            "7": {
                "name": "gemma-3n-E4B-it-litert-lm",
                "display": "Gemma 3N E4B LiteRT LM (文本生成，轻量运行时)",
                "max_input_tokens": 32000,
                "max_output_tokens": 32000,
                "optimization": "轻量运行时优化"
            },
            "8": {
                "name": "gemma-3n-E4B-it-litert-preview",
                "display": "Gemma 3N E4B LiteRT Preview (图像文本转换，预览版)",
                "max_input_tokens": 32000,
                "max_output_tokens": 32000,
                "optimization": "图像文本处理预览"
            }
        }


    def setup_authentication(self) -> bool:
        """
        设置用户认证
        Returns:
            认证是否成功
        """
        print("=== Gemma3 聊天界面 ===")
        print("请输入您的用户名进行身份验证")
        print()
        
        username = input("用户名: ").strip()
        if not username:
            print("❌ 用户名不能为空")
            return False
            
        # 验证API密钥
        encoder = APIEncoder()
        api_key = encoder.decode_api_key(username)
        if not api_key:
            print("❌ 用户名验证失败，无法获取API密钥")
            return False
            
        self.username = username
        self.api_key = api_key
        print(f"✅ 用户验证成功！欢迎, {username}")
        print()
        return True


    def setup_model_selection(self) -> bool:
        """
        设置模型选择
        Returns:
            模型选择是否成功
        """
        print("请选择要使用的Gemma模型:")
        print()
        
        for key, model_info in self.available_models.items():
            print(f"{key}. {model_info['display']}")
        print()
        
        while True:
            choice = input("请选择模型 (1-8): ").strip()
            if choice in self.available_models:
                model_info = self.available_models[choice]
                self.model_name = model_info["name"]
                self.max_input_tokens = model_info["max_input_tokens"]
                self.max_output_tokens = model_info["max_output_tokens"]
                
                try:
                    # 配置API并创建模型
                    genai.configure(api_key=self.api_key)
                    self.model = genai.GenerativeModel(self.model_name)
                    print(f"✅ 已选择模型: {model_info['display']}")
                    print(f"📊 输入Token限制: {self.max_input_tokens:,}")
                    print(f"📊 输出Token限制: {self.max_output_tokens:,}")
                    print()
                    return True
                except Exception as e:
                    print(f"❌ 模型初始化失败: {e}")
                    return False
            else:
                print("❌ 无效选择，请输入1-8之间的数字")


    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量
        Args:
            text: 输入文本
        Returns:
            估算的token数量
        """
        # 简单估算：中文字符*1.5 + 英文单词*1.3
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in text.split() if any(c.isalpha() for c in w)])
        other_chars = len(text) - chinese_chars - sum(len(w) for w in text.split() if any(c.isalpha() for c in w))
        
        estimated = int(chinese_chars * 1.5 + english_words * 1.3 + other_chars * 0.5)
        return max(estimated, len(text) // 4)  # 最低估算为字符数的1/4


    def update_token_count(self):
        """更新当前对话的token数量"""
        total_text = ""
        for msg in self.conversation_history:
            total_text += msg["content"] + " "
        self.current_tokens = self.estimate_tokens(total_text)


    def display_token_info(self):
        """显示token使用信息"""
        input_percentage = (self.current_tokens / self.max_input_tokens) * 100
        bar_length = 30
        filled_length = int(bar_length * input_percentage / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        print(f"\n📊 输入Token使用情况: {self.current_tokens:,}/{self.max_input_tokens:,} ({input_percentage:.1f}%)")
        print(f"[{bar}]")
        print(f"📤 输出Token限制: {self.max_output_tokens:,}")
        
        if input_percentage > 90:
            print("⚠️  警告: 输入Token使用接近上限，考虑清理对话历史")
        elif input_percentage > 70:
            print("💡 提示: 输入Token使用较多，建议适度控制对话长度")


    def build_conversation_context(self) -> str:
        """
        构建对话上下文
        Returns:
            完整的对话上下文字符串
        """
        if not self.conversation_history:
            return ""
            
        context_parts = ["以下是我们的对话历史：\n"]
        for msg in self.conversation_history[-10:]:  # 只保留最近10轮对话
            role = "用户" if msg["role"] == "user" else "助手"
            context_parts.append(f"{role}: {msg['content']}\n")
        
        context_parts.append("\n请根据以上对话历史回答新的问题。")
        return "".join(context_parts)


    def send_message_to_gemma(self, user_input: str) -> Optional[str]:
        """
        发送消息到Gemma并获取回复
        Args:
            user_input: 用户输入
        Returns:
            Gemma的回复或None
        """
        try:
            # 构建完整的prompt
            context = self.build_conversation_context()
            full_prompt = f"{context}\n\n用户新问题: {user_input}"
            
            # 配置生成参数，使用模型的实际输出限制
            generation_config = {
                'temperature': 0.7,
                'max_output_tokens': min(2048, self.max_output_tokens),
                'top_p': 0.9,
                'top_k': 40
            }
            
            # 使用多线程实现超时
            result = [None]
            exception = [None]
            
            def api_call():
                try:
                    response = self.model.generate_content(
                        full_prompt, 
                        generation_config=generation_config
                    )
                    result[0] = response.text.strip()
                except Exception as e:
                    exception[0] = e
            
            # 显示正在思考的动画
            thread = threading.Thread(target=api_call)
            thread.start()
            
            # 等待响应，显示加载动画
            loading_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            char_index = 0
            
            while thread.is_alive():
                print(f"\r🤖 Gemma正在思考 {loading_chars[char_index]}", end="", flush=True)
                char_index = (char_index + 1) % len(loading_chars)
                time.sleep(0.1)
                
            thread.join(timeout=15.0)  # 15秒超时
            print("\r" + " " * 50 + "\r", end="")  # 清除加载动画
            
            if thread.is_alive():
                print("⏰ 请求超时，请稍后重试")
                return None
                
            if exception[0]:
                print(f"❌ API调用出错: {exception[0]}")
                return None
                
            return result[0]
            
        except Exception as e:
            print(f"❌ 发送消息时出错: {e}")
            return None


    def add_to_history(self, role: str, content: str):
        """
        添加消息到对话历史
        Args:
            role: 角色 (user/assistant)
            content: 消息内容
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self.update_token_count()


    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        self.current_tokens = 0
        print("🗑️  对话历史已清空")


    def show_help(self):
        """显示帮助信息"""
        help_text = """
📖 聊天命令帮助:

基本对话:
  - 直接输入消息与Gemma对话
  - Gemma会记住整个对话历史
  - 支持文本生成和图像文本转换模型

特殊命令:
  /help     - 显示此帮助信息
  /clear    - 清空对话历史
  /tokens   - 显示当前token使用情况
  /history  - 显示对话历史摘要
  /model    - 显示当前模型信息和优化特性
  /exit     - 退出聊天界面

🚀 可用模型类型 (8种Google官方模型):
  1-2. 文本生成优化 (1B, 270M) - 128K输入/8K输出
  3-5. 图像文本处理 (4B, 12B, 27B) - 128K输入/8K输出
  6-8. 实验版本 (E4B系列) - 32K输入输出

💡 提示:
  - 对话历史会影响回复质量和token消耗
  - 当token使用过多时建议使用 /clear 清理历史
  - 使用中文或英文都可以与Gemma对话
  - 不同模型有不同的优化特性，选择适合的模型
        """
        print(help_text)


    def show_history_summary(self):
        """显示对话历史摘要"""
        if not self.conversation_history:
            print("📝 暂无对话历史")
            return
            
        print(f"📝 对话历史摘要 (共{len(self.conversation_history)}条消息):")
        print("-" * 50)
        
        for i, msg in enumerate(self.conversation_history[-5:], 1):  # 显示最近5条
            role = "👤 用户" if msg["role"] == "user" else "🤖 Gemma"
            content_preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            print(f"{i}. {role}: {content_preview}")


    def show_model_info(self):
        """显示当前模型信息"""
        # 查找当前模型的详细信息
        current_model_info = None
        for model_info in self.available_models.values():
            if model_info["name"] == self.model_name:
                current_model_info = model_info
                break
        
        print(f"🤖 当前模型: {self.model_name}")
        if current_model_info:
            print(f"⚡ 优化特性: {current_model_info['optimization']}")
        print(f"👤 用户: {self.username}")
        print(f"📊 输入Token限制: {self.max_input_tokens:,}")
        print(f"📤 输出Token限制: {self.max_output_tokens:,}")
        print(f"💬 对话轮次: {len(self.conversation_history)}")


    def start_chat(self):
        """开始聊天循环"""
        print("🚀 聊天界面已启动！")
        print("💡 输入 /help 查看可用命令")
        print("💡 输入 /exit 退出聊天")
        print("=" * 50)
        
        while True:
            try:
                # 显示token信息（每5轮对话显示一次）
                if len(self.conversation_history) % 10 == 0 and len(self.conversation_history) > 0:
                    self.display_token_info()
                
                # 获取用户输入
                user_input = input(f"\n👤 {self.username}: ").strip()
                
                if not user_input:
                    continue
                    
                # 处理特殊命令
                if user_input.startswith('/'):
                    command = user_input.lower()
                    
                    if command == '/exit':
                        print("👋 再见！感谢使用Gemma聊天界面")
                        break
                    elif command == '/help':
                        self.show_help()
                        continue
                    elif command == '/clear':
                        self.clear_history()
                        continue
                    elif command == '/tokens':
                        self.display_token_info()
                        continue
                    elif command == '/history':
                        self.show_history_summary()
                        continue
                    elif command == '/model':
                        self.show_model_info()
                        continue
                    else:
                        print("❌ 未知命令，输入 /help 查看可用命令")
                        continue
                
                # 添加用户消息到历史
                self.add_to_history("user", user_input)
                
                # 发送到Gemma并获取回复
                response = self.send_message_to_gemma(user_input)
                
                if response:
                    print(f"\n🤖 Gemma: {response}")
                    self.add_to_history("assistant", response)
                else:
                    print("\n❌ 抱歉，无法获取回复，请稍后重试")
                    
            except KeyboardInterrupt:
                print("\n\n👋 检测到Ctrl+C，正在退出...")
                break
            except Exception as e:
                print(f"\n❌ 程序出错: {e}")
                print("💡 请尝试重新输入或使用 /help 查看帮助")


    def run(self) -> bool:
        """
        运行聊天界面
        Returns:
            是否成功启动
        """
        # 1. 用户认证
        if not self.setup_authentication():
            return False
            
        # 2. 模型选择  
        if not self.setup_model_selection():
            return False
            
        # 3. 开始聊天
        self.start_chat()
        return True




def main():
    """主函数"""
    try:
        chat = ChatInterface()
        chat.run()
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
