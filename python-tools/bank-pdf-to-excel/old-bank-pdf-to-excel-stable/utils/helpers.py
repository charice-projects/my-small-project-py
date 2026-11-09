# -*- coding: utf-8 -*-
"""
公共工具函数

本模块提供所有插件共用的基础工具函数，包括：
    - 文本清洗 (clean_text)
    - 安全浮点数转换 (safe_float)
    - 路径规范化 (normalize_path) —— 支持 Git Bash 拖拽路径（/e/...）
    - 字符串相似度 (similarity)
"""

import re
from pathlib import Path
from typing import Any, Optional


def clean_text(text: str) -> str:
    """
    清理文本中的控制字符、ANSI转义序列、全角空格和制表符

    参数:
        text: 原始文本

    返回:
        清洗后的文本，首尾空白已去除
    """
    if not text:
        return ""
    # 移除 ANSI 转义序列（如终端颜色码）
    text = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)
    # 移除不可打印的控制字符（保留换行和回车）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    # 将全角空格和制表符替换为普通空格
    text = text.replace('\u3000', ' ').replace('\t', ' ')
    return text.strip()


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """
    将各种格式的字符串或数值安全转换为浮点数

    支持：
        - 千分位逗号（如 "1,234.56"）
        - 括号表示负数（如 "(123.45)" 转为 -123.45）
        - 末尾 CR/DR 标记（如 "123.45CR" 转为 -123.45）
        - 带正负号的数字（如 "+123.45" 或 "-123.45"）

    参数:
        value: 待转换的值（字符串、整数、浮点数或其他）
        default: 转换失败时返回的默认值，默认为 None

    返回:
        转换后的浮点数，或 default
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        v = value.strip().replace(',', '').replace(' ', '')
        if not v or v == '-':
            return default
        # 处理括号负数
        if v.startswith('(') and v.endswith(')'):
            v = '-' + v[1:-1]
        # 处理 CR/DR 标记
        if v.upper().endswith('CR'):
            v = '-' + v[:-2]
        # 提取数字部分（包括符号）
        match = re.search(r'[-+]?\d*\.?\d+', v)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
    return default


def normalize_path(input_str: str) -> Path:
    """
    将用户输入的路径字符串规范化为 Path 对象

    支持：
        - Windows 路径（如 "C:\\Users\\file.pdf"）
        - Git Bash 拖拽路径（如 "/e/我的下载/浏览器下载/file.pdf"）
        - 带引号的路径（自动去除首尾引号）
        - 混合斜杠（统一转为正斜杠）

    参数:
        input_str: 用户输入的路径字符串

    返回:
        Path 对象
    """
    path_str = input_str.strip().strip('"\'')
    path_str = path_str.replace('\\', '/')

    # 处理 Git Bash 风格的 /x/... 格式（x 为盘符，如 /e/...）
    match = re.match(r'^/([a-zA-Z])/(.*)$', path_str)
    if match:
        drive = match.group(1).upper()  # 将盘符转为大写
        rest = match.group(2)
        path_str = f"{drive}:/{rest}"
    # 处理 Windows 盘符无斜杠的情况（如 "C:Users" -> "C:/Users"）
    elif len(path_str) > 1 and path_str[1] == ':' and not path_str[2:].startswith('/'):
        path_str = path_str[:2] + '/' + path_str[2:]

    return Path(path_str)


def similarity(a: str, b: str) -> float:
    """
    计算两个字符串的相似度（0~1）

    优先使用 Levenshtein 库（精确编辑距离），
    若未安装则退化为包含关系检查。

    参数:
        a: 字符串1
        b: 字符串2

    返回:
        相似度（0~1 浮点数）
    """
    try:
        import Levenshtein
        dist = Levenshtein.distance(a.lower(), b.lower())
        max_len = max(len(a), len(b))
        return 1.0 - (dist / max_len)
    except ImportError:
        # 简单回退：包含关系
        return 1.0 if a in b or b in a else 0.0