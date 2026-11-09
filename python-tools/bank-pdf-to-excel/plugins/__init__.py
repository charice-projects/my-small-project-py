# -*- coding: utf-8 -*-
"""
插件注册中心

所有插件在此注册，PLUGINS 列表的顺序决定了自动检测的优先级。
建议将通用解析器放在最后作为兜底。
"""

from .base import StatementPlugin
from .wechat import WeChatPlugin
from .ccb import CCBPlugin
from .zhaoshang import ZhaoShangPlugin
from .nongye import NongYePlugin
from .alipay import AliPayPlugin
from .jiaotong import JiaoTongPlugin
from .ganzhou import GanZhouPlugin

from .universal import UniversalPlugin

# 按优先级从高到低排列
PLUGINS = [
    WeChatPlugin(),       # 微信支付
    AliPayPlugin(),       # 支付宝
    JiaoTongPlugin(),     # 交通银行
    CCBPlugin(),          # 建设银行
    ZhaoShangPlugin(),    # 招商银行
    NongYePlugin(),       # 农业银行
    GanZhouPlugin(),      # 赣州银行
    UniversalPlugin(),    # 通用后备（最后尝试）
]


def get_plugin_by_identifier(identifier: str) -> StatementPlugin:
    """根据标识符获取插件实例"""
    for p in PLUGINS:
        if p.identifier == identifier:
            return p
    return None