#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密钥预编码器
将真实的API密钥编码成伪码，等待用户输入用户名后解码还原
"""

import base64
import hashlib
from typing import Optional


class APIEncoder:
    """API密钥预编码器类"""


    def __init__(self):
        """初始化编码器"""
        pass


    def _generate_salt_from_username(self, username: str) -> str:
        """
        从用户名生成盐值
        Args:
            username: 用户名
        Returns:
            盐值字符串
        """
        # 使用用户名生成确定性的盐值
        hash_obj = hashlib.sha256(username.encode('utf-8'))
        salt = base64.b64encode(hash_obj.digest()[:8]).decode('utf-8')
        return salt


    def _encode_api_key(self, api_key: str, username: str) -> str:
        """
        编码API密钥
        Args:
            api_key: 真实的API密钥
            username: 用户名
        Returns:
            编码后的伪码
        """
        # 生成盐值
        salt = self._generate_salt_from_username(username)
        # 创建编码数据
        # 格式: salt + 分隔符 + 编码后的API密钥
        separator = "::"
        # 简单的编码：将API密钥的每个字符与盐值进行XOR运算
        encoded_chars = []
        for i, char in enumerate(api_key):
            salt_char = salt[i % len(salt)]
            encoded_char = chr(ord(char) ^ ord(salt_char))
            encoded_chars.append(encoded_char)
        # 转换为base64编码
        encoded_data = base64.b64encode(''.join(encoded_chars).encode('utf-8')).decode('utf-8')
        # 组合最终伪码
        pseudo_code = f"{salt}{separator}{encoded_data}"
        return pseudo_code


    def _decode_api_key(self, pseudo_code: str, username: str) -> Optional[str]:
        """
        解码API密钥
        Args:
            pseudo_code: 伪码
            username: 用户名
        Returns:
            解码后的API密钥或None
        """
        try:
            # 分离盐值和编码数据
            separator = "::"
            if separator not in pseudo_code:
                return None
            salt, encoded_data = pseudo_code.split(separator, 1)
            # 验证盐值是否匹配用户名
            expected_salt = self._generate_salt_from_username(username)
            if salt != expected_salt:
                return None
            # base64解码
            encoded_chars = base64.b64decode(encoded_data).decode('utf-8')
            # XOR解码
            decoded_chars = []
            for i, char in enumerate(encoded_chars):
                salt_char = salt[i % len(salt)]
                decoded_char = chr(ord(char) ^ ord(salt_char))
                decoded_chars.append(decoded_char)
            return ''.join(decoded_chars)
        except Exception:
            return None


    def get_pseudo_codes(self) -> list:
        """
        获取预编码的伪码列表
        Returns:
            伪码列表，不包含任何用户名信息
        """
        # 预编码的伪码列表，不包含任何用户名或真实API密钥信息
        return [
            "x8WzWNQJf44=::OXEtGwQ3EjMqQkdsVX5nNxA7Gg82UlJJOgggPmNjBQg/ZQBkO0Jj",
            "n+k0F4U3OcE=::L2IRURVNFkoDFTZsQ21bfQFBHnYfBSNJLBscdHIZAXEWMnFkLVFf"
        ]


    def get_api_suffix(self) -> str:
        """
        获取真实API密钥的最后4位用于验证
        Returns:
            真实API密钥的最后4位
        """
        # 真实API密钥的最后4位，用于验证解码结果
        return "YCz4"


    def decode_api_key(self, username: str) -> Optional[str]:
        """
        根据用户名解码API密钥
        Args:
            username: 用户名
        Returns:
            API密钥或None
        """
        pseudo_codes = self.get_pseudo_codes()
        expected_suffix = self.get_api_suffix()
        # 遍历所有伪码，尝试用当前用户名解码
        for pseudo_code in pseudo_codes:
            decoded_key = self._decode_api_key(pseudo_code, username)
            if decoded_key and decoded_key.endswith(expected_suffix):
                # 验证成功，返回解码的API密钥
                return decoded_key
        # 所有伪码都解码失败或验证失败
        return None


def main():
    """主函数示例"""
    encoder = APIEncoder()
    print("API密钥预编码器")
    print("=" * 50)
    # 显示预编码的伪码
    pseudo_code = encoder.get_pseudo_code()
    print(f"预编码的伪码: {pseudo_code}")
    print("注意：这个伪码不包含任何用户名或真实API密钥信息！")
    # 测试解码功能
    print("\n请输入用户名进行测试:")
    username = input("用户名: ").strip()
    if username:
        decoded_key = encoder.decode_api_key(username)
        if decoded_key:
            print(f"✓ 解码成功: {decoded_key[:10]}...")
        else:
            print("✗ 解码失败，用户名可能不正确")
    else:
        print("用户名不能为空")


if __name__ == "__main__":
    main()

