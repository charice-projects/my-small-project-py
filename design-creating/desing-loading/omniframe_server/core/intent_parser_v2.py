# core/intent_parser_v2.py
"""  
意图解析器 V2 - 基于意图优先级的智能解析系统  
"""
from typing import Dict, List, Optional, Any, Tuple
import re
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

from utils.logger import logger


class IntentType(Enum):
    """意图类型枚举"""
    SYSTEM_INFO = "system_info"
    FILE_LIST = "list"
    FILE_SEARCH = "search"
    FILE_READ = "read"
    FILE_WRITE = "write"
    FILE_DELETE = "delete"
    FILE_COPY = "copy"
    FILE_MOVE = "move"
    FILE_INDEX = "index"
    RECENT_FILES = "recent"
    COMMAND_HISTORY = "history"
    DIRECTORY_TREE = "tree"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """解析后的意图结果"""
    type: IntentType
    parameters: Dict[str, Any]
    confidence: float  # 置信度，0.0-1.0
    original_command: str
    suggestions: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.type != IntentType.UNKNOWN,
            "action": self.type.value,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "original_command": self.original_command,
            "suggestions": self.suggestions or [],
            "timestamp": datetime.now().isoformat()
        }


@dataclass
class IntentPattern:
    """意图模式定义"""
    intent_type: IntentType
    patterns: List[str]
    priority: int = 5  # 1-10，越高越优先
    extractors: Dict[str, Any] = None
    validator: Any = None
    suggestions: List[str] = None


class IntentParserV2:
    """第二代意图解析器"""
    
    def __init__(self):
        self.intent_patterns = self._initialize_intent_patterns()
        self.logger = logger
        
    def _initialize_intent_patterns(self) -> List[IntentPattern]:
        """初始化意图模式"""
        return [
            # 系统信息意图
            IntentPattern(
                intent_type=IntentType.SYSTEM_INFO,
                patterns=[
                    r"^(show\s+status|status|系统状态|显示状态|服务器状态)$",
                    r"^show\s+system$",
                    r"^system\s+status$",
                    r"^health$",
                    r"^显示系统状态$",
                    r"^查看系统信息$",
                ],
                priority=10,
                suggestions=["查看服务器资源使用情况", "检查服务健康状态"]
            ),
            
            # 文件列表意图
            IntentPattern(
                intent_type=IntentType.FILE_LIST,
                patterns=[
                    r"^show\s+files$",
                    r"^list\s+files$",
                    r"^ls(?:\s+([^\s]+))?$",
                    r"^list(?:\s+([^\s]+))?$",
                    r"^显示文件$",
                    r"^列出文件$",
                    r"^列出文档$",
                    r"^查看\s+(.+)$",
                ],
                priority=9,
                extractors={
                    "path": self._extract_path_parameter,
                },
                suggestions=["ls", "list", "列出文件 [路径]"]
            ),
            
            # 文件搜索意图
            IntentPattern(
                intent_type=IntentType.FILE_SEARCH,
                patterns=[
                    r"^search\s+(.+)$",
                    r"^find\s+(.+)$",
                    r"^搜索\s+(.+)$",
                    r"^查找\s+(.+)$",
                    r"^搜索文件\s+(.+)$",
                    r"^搜索文档$",  # 固定短语
                    r"^查找图片$",  # 固定短语
                ],
                priority=8,
                extractors={
                    "query": self._extract_search_query,
                    "path": self._extract_search_path,
                },
                validator=self._validate_search_parameters,
                suggestions=["search [关键词]", "find [文件名]", "搜索 [内容]"]
            ),
            
            # 索引操作意图
            IntentPattern(
                intent_type=IntentType.FILE_INDEX,
                patterns=[
                    r"^index$",
                    r"^generate\s+index$",
                    r"^生成索引$",
                    r"^初始化索引$",
                    r"^更新索引$",
                ],
                priority=7,
                suggestions=["重新生成文件索引", "更新搜索数据库"]
            ),
            
            # 最近文件意图
            IntentPattern(
                intent_type=IntentType.RECENT_FILES,
                patterns=[
                    r"^recent$",
                    r"^recent\s+files$",
                    r"^最近文件$",
                    r"^查看最近文件$",
                ],
                priority=6,
                suggestions=["查看最近访问的文件", "显示近期操作记录"]
            ),
            
            # 命令历史意图
            IntentPattern(
                intent_type=IntentType.COMMAND_HISTORY,
                patterns=[
                    r"^history$",
                    r"^command\s+history$",
                    r"^历史记录$",
                    r"^查看历史$",
                ],
                priority=5,
                suggestions=["查看命令历史", "显示最近执行的命令"]
            ),
            
            # 目录树意图
            IntentPattern(
                intent_type=IntentType.DIRECTORY_TREE,
                patterns=[
                    r"^tree$",
                    r"^directory\s+tree$",
                    r"^目录树$",
                    r"^查看目录结构$",
                ],
                priority=4,
                suggestions=["显示目录结构", "查看文件夹层次"]
            ),
        ]
    
    def parse(self, command: str) -> ParsedIntent:
        """解析命令"""
        self.logger.info(f"解析命令: {command}")
        
        # 清理命令
        cleaned_command = self._clean_command(command)
        
        # 特殊处理：单独的搜索命令
        if cleaned_command.lower() in ["search", "find", "搜索", "查找"]:
            return ParsedIntent(
                type=IntentType.UNKNOWN,
                parameters={"original_command": cleaned_command},
                confidence=0.0,
                original_command=command,
                suggestions=["请提供搜索关键词，例如:", 
                           "search test", 
                           "find document", 
                           "搜索文档", 
                           "查找图片"]
            )
        
        # 匹配所有可能的意图
        possible_intents = []
        
        for pattern_config in self.intent_patterns:
            for pattern in pattern_config.patterns:
                # 编译正则，忽略大小写
                regex = re.compile(pattern, re.IGNORECASE)
                match = regex.match(cleaned_command)
                
                if match:
                    # 提取参数
                    params = self._extract_parameters(
                        cleaned_command, match, pattern_config
                    )
                    
                    # 验证参数
                    if pattern_config.validator:
                        validation_result = pattern_config.validator(params)
                        if not validation_result.get("valid", True):
                            continue  # 跳过无效的匹配
                    
                    # 计算置信度
                    confidence = self._calculate_confidence(
                        pattern, cleaned_command, match
                    )
                    
                    possible_intents.append({
                        "config": pattern_config,
                        "params": params,
                        "confidence": confidence * pattern_config.priority / 10,
                        "match": match
                    })
                    break  # 每个意图只取第一个匹配的模式
        
        if not possible_intents:
            return ParsedIntent(
                type=IntentType.UNKNOWN,
                parameters={"original_command": cleaned_command},
                confidence=0.0,
                original_command=command,
                suggestions=self._generate_suggestions(cleaned_command)
            )
        
        # 选择置信度最高的意图
        best_intent = max(possible_intents, key=lambda x: x["confidence"])
        
        return ParsedIntent(
            type=best_intent["config"].intent_type,
            parameters=best_intent["params"],
            confidence=best_intent["confidence"],
            original_command=command,
            suggestions=best_intent["config"].suggestions
        )
    
    def _clean_command(self, command: str) -> str:
        """清理命令"""
        # 去除首尾空格，合并多个空格
        cleaned = re.sub(r'\s+', ' ', command.strip())
        return cleaned
    
    def _extract_parameters(self, command: str, match: re.Match, 
                           pattern_config: IntentPattern) -> Dict[str, Any]:
        """提取参数"""
        params = {"original_command": command}
        
        if pattern_config.extractors:
            for param_name, extractor in pattern_config.extractors.items():
                try:
                    value = extractor(command, match)
                    if value is not None:
                        params[param_name] = value
                except Exception as e:
                    self.logger.warning(f"参数提取失败 {param_name}: {e}")
        
        return params
    
    def _extract_path_parameter(self, command: str, match: re.Match) -> Optional[str]:
        """提取路径参数"""
        if match.groups():
            path = match.group(1)
            if path:
                return path.strip()
        return "."
    
    def _extract_search_query(self, command: str, match: re.Match) -> Optional[str]:
        """提取搜索查询"""
        # 处理固定短语
        fixed_phrases = {
            "搜索文档": "文档",
            "查找图片": "图片",
            "查找文件": "文件",
            "搜索文件": "文件"
        }
        
        for phrase, keyword in fixed_phrases.items():
            if phrase in command:
                return keyword
        
        # 从正则匹配中提取
        if match.groups():
            query = match.group(1)
            if query:
                return query.strip()
        
        return None
    
    def _extract_search_path(self, command: str, match: re.Match) -> Optional[str]:
        """提取搜索路径"""
        # 默认在当前目录搜索
        return "."
    
    def _validate_search_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证搜索参数"""
        query = params.get("query", "")
        
        if not query or query.strip() == "":
            return {
                "valid": False,
                "message": "搜索关键词不能为空",
                "suggestions": ["请输入要搜索的内容"]
            }
        
        return {"valid": True}
    
    def _calculate_confidence(self, pattern: str, command: str, 
                             match: re.Match) -> float:
        """计算匹配置信度"""
        # 基础置信度
        confidence = 0.7
        
        # 完全匹配加分
        if match.group() == command:
            confidence += 0.2
        
        # 参数匹配加分
        if match.groups():
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_suggestions(self, command: str) -> List[str]:
        """生成命令建议"""
        # 基于常见错误生成建议
        common_commands = [
            "show status",
            "list files",
            "search [关键词]",
            "index",
            "recent",
            "history"
        ]
        
        return [f"试试: {cmd}" for cmd in common_commands[:3]]