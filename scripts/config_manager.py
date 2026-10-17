# -*- coding: utf-8 -*-
"""
应用程序配置管理模块 (TOML 格式)
"""

import sys
from pathlib import Path
from typing import Any, Dict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

try:
    import tomli_w

    def dump_toml(data: dict, f) -> None:
        tomli_w.dump(data, f)

except ImportError:
    import toml

    def dump_toml(data: dict, f) -> None:
        toml.dump(data, f)


CONFIG_FILE_PATH = Path("resources/app_config.toml")

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "0.6.4",
    "db_preferences": {
        "default_mode": "encrypted",
        "preload_count": 5,
        "remember_last_db": True,
        "last_selected_db": "",
    },
    "ui_settings": {
        "theme": "Auto",
        "font_family": "Courier New",
        "font_size_percent": 100,
        "show_debug": False,
    },
    "emd_summary": {
        "producer_name": "",
    },
}


def _deep_merge(source: dict, target: dict) -> dict:
    """深度合并字典，以 target 为主，缺失的键从 source 补充"""
    result = source.copy()
    for key, value in target.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_app_config() -> Dict[str, Any]:
    """读取应用程序 TOML 配置"""
    if not CONFIG_FILE_PATH.exists():
        save_app_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE_PATH, "rb") as f:
            cfg = tomllib.load(f)
        legacy = cfg.pop("excel_processor", None)
        if isinstance(legacy, dict):
            current = cfg.get("emd_summary")
            if not isinstance(current, dict):
                cfg["emd_summary"] = legacy
            else:
                for key, value in legacy.items():
                    if key not in current or current[key] in ("", None):
                        current[key] = value
        return _deep_merge(DEFAULT_CONFIG, cfg)
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_app_config(cfg: Dict[str, Any]) -> bool:
    """保存配置到 TOML 文件"""
    try:
        CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE_PATH, "wb") as f:
            dump_toml(cfg, f)
        return True
    except Exception:
        return False


def get_config_value(section: str, key: str, default: Any = None) -> Any:
    """获取指定区段的配置值"""
    cfg = load_app_config()
    return cfg.get(section, {}).get(key, default)


def set_config_value(section: str, key: str, value: Any) -> bool:
    """设置并持久化指定区段的配置值"""
    cfg = load_app_config()
    if section not in cfg:
        cfg[section] = {}
    cfg[section][key] = value
    return save_app_config(cfg)
