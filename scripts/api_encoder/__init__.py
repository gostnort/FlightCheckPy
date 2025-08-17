#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API编码器模块
用于安全地处理Google Gemma3 API密钥和生成心情描述
"""

from .api_encoder import APIEncoder
from .gemma3_client import generate_mood_description, calculate_mood_category, clean_chinese_text

__version__ = "1.0.0"
__author__ = "FlightCheckPy"

__all__ = [
    "APIEncoder",
    "generate_mood_description", 
    "calculate_mood_category",
    "clean_chinese_text"
]

