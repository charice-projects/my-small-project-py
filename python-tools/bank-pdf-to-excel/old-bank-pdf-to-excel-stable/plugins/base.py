# -*- coding: utf-8 -*-
"""解析器基类"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

class StatementPlugin(ABC):
    """所有银行/支付平台解析器必须实现的接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """返回插件显示名称"""
        pass
    
    @property
    @abstractmethod
    def identifier(self) -> str:
        """返回插件唯一标识符（用于命令行选择）"""
        pass
    
    @abstractmethod
    def detect(self, pdf_path: str) -> bool:
        """自动检测 PDF 是否属于本插件支持的格式"""
        pass
    
    @abstractmethod
    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        """
        执行解析，返回 (账户信息字典, 交易列表)
        交易列表中的每条交易为字典，字段建议统一（非强制）
        """
        pass