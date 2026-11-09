"""
意图解析器 - 将自然语言转换为结构化命令
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json

from utils.logger import logger
from utils.validation import InputValidator


class IntentParser:
    """自然语言意图解析器"""
    
    def __init__(self):
        # 按优先级排序的意图模式库
        # 更具体的模式应该放在前面
        self.intent_patterns = {
            # ========== 系统状态相关 ==========
            "system_info": {
                "patterns": [
                    r"^\s*(show\s+status|status|系统状态|显示状态|服务器状态)\s*$",
                    r"^\s*show\s+system\s*$",
                    r"^\s*system\s+status\s*$",
                    r"^\s*system\s+info\s*$",
                    r"^\s*server\s+status\s*$",
                    r"^\s*health\s*$",
                    r"^\s*显示系统状态\s*$",
                    r"^\s*查看系统信息\s*$",
                ],
                "action": "system_info",
                "default_params": {},
                "priority": 1  # 高优先级
            },
            
            # ========== 搜索相关 ==========
            "search": {
                "patterns": [
                    r"^搜索\s+(.+)$",  # 修复：添加^开头，确保"搜索文档"能匹配
                    r"^查找\s+(.+)$",
                    r"^搜索文件\s+(.+)$",
                    r"^find\s+(.+)$",
                    r"^search\s+(.+)$",
                    r"^查询\s+(.+)$",  # 新增：支持"查询文档"
                    r"^搜索文档$",     # 新增：支持"搜索文档"（无参数）
                    r"^查找文档$",     # 新增：支持"查找文档"（无参数）
                ],
                "action": "search",
                "extract_query": True,
                "priority": 2,
                "query_field": "target"  # 新增：指定查询参数字段
            },
            
            # ========== 列表相关 ==========
            "list": {
                "patterns": [
                    r"^显示\s+(.+)\s+列表$",
                    r"^查看\s+(.+)$",
                    r"^浏览\s+(.+)$",
                    r"^list\s+(.+)$",
                    r"^ls\s+(.+)$",
                    r"^dir\s+(.+)$",
                    r"^显示文件$",
                    r"^list$",
                    r"^ls$",
                    r"^dir$",
                    # show files 或 show directory 等才应该匹配到这里
                    r"^show\s+(?:files?|directory|dir|list)\b",
                    r"^show\s+(?:files?|directory|dir|list)\s+(.+)$",
                    r"^列出文件$",      # 修复：添加"列出文件"支持
                    r"^列出\s+(.+)$",   # 修复：支持"列出 某类文件"
                ],
                "action": "list",
                "extract_query": True,
                "priority": 3
            },
            
            # ========== 索引相关 ==========
            "index": {
                "patterns": [
                    r"^初始化索引$",
                    r"^生成索引$",
                    r"^更新索引$",
                    r"^重建索引$",
                    r"^scan\s+files$",
                    r"^index$",        # 修复：添加英文"index"支持
                    r"^index\s+(?:all|files)?$",
                    r"^扫描文件$",
                ],
                "action": "index",
                "default_params": {"force": False},
                "priority": 2
            },
            
            # ========== 文件操作相关 ==========
            "read": {
                "patterns": [
                    r"^读取\s+(.+)$",
                    r"^打开\s+(.+)$",
                    r"^查看文件\s+(.+)$",
                    r"^read\s+(.+)$",
                    r"^open\s+(.+)$",
                ],
                "action": "read",
                "extract_target": True,
                "priority": 2
            },
            
            "delete": {
                "patterns": [
                    r"^删除\s+(.+)$",
                    r"^移除\s+(.+)$",
                    r"^delete\s+(.+)$",
                    r"^remove\s+(.+)$",
                    r"^rm\s+(.+)$",
                ],
                "action": "delete",
                "extract_target": True,
                "requires_confirmation": True,
                "priority": 2
            },
            
            "info": {
                "patterns": [
                    r"^(.+?)\s+的信息$",
                    r"^查看\s+(.+?)\s+详情$",
                    r"^info\s+(.+)$",
                ],
                "action": "info",
                "extract_target": True,
                "priority": 3
            },
            
            "archive": {
                "patterns": [
                    r"^打包\s+(.+)$",
                    r"^压缩\s+(.+)$",
                    r"^归档\s+(.+)$",
                    r"^archive\s+(.+)$",
                    r"^zip\s+(.+)$",
                ],
                "action": "archive",
                "extract_target": True,
                "priority": 2
            },
            
            "create_dir": {
                "patterns": [
                    r"^创建目录\s+(.+)$",
                    r"^新建文件夹\s+(.+)$",
                    r"^mkdir\s+(.+)$",
                ],
                "action": "create_dir",
                "extract_target": True,
                "priority": 2
            },
            
            "sync": {
                "patterns": [
                    r"^同步\s+(.+)$",
                    r"^更新\s+(.+)$",
                    r"^sync\s+(.+)$",
                ],
                "action": "sync",
                "extract_target": True,
                "priority": 2
            },
            
            "monitor": {
                "patterns": [
                    r"^监控\s+(.+)$",
                    r"^监视\s+(.+)$",
                    r"^monitor\s+(.+)$",
                ],
                "action": "monitor",
                "extract_target": True,
                "priority": 2
            },
        }
        
        # 按优先级排序的模式列表
        self.sorted_patterns = self._create_sorted_patterns()
        
        # 时间表达式解析
        self.time_patterns = [
            (r"今天", "today"),
            (r"昨天", "yesterday"),
            (r"明天", "tomorrow"),
            (r"上周", "last_week"),
            (r"本周", "this_week"),
            (r"下周", "next_week"),
            (r"上个月", "last_month"),
            (r"本月", "this_month"),
            (r"最近(\d+)(天|日)", "recent_days"),
            (r"最近(\d+)周", "recent_weeks"),
            (r"最近(\d+)个月", "recent_months"),
        ]
        
        # 文件类型映射
        self.file_type_mapping = {
            "图片": ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"],
            "文档": ["pdf", "doc", "docx", "txt", "md", "rtf"],
            "代码": ["py", "js", "java", "cpp", "c", "h", "html", "css"],
            "视频": ["mp4", "avi", "mov", "mkv", "flv"],
            "音频": ["mp3", "wav", "flac", "aac"],
            "压缩包": ["zip", "rar", "7z", "tar", "gz"],
        }
    
    def _create_sorted_patterns(self):
        """创建按优先级排序的模式列表"""
        patterns = []
        for intent_name, intent_config in self.intent_patterns.items():
            priority = intent_config.get("priority", 10)  # 默认优先级10
            action = intent_config["action"]
            for pattern in intent_config["patterns"]:
                patterns.append({
                    "pattern": pattern,
                    "intent_name": intent_name,
                    "action": action,
                    "config": intent_config,
                    "priority": priority
                })
        
        # 按优先级排序（优先级数字越小越优先）
        patterns.sort(key=lambda x: x["priority"])
        return patterns
    
    def parse(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """解析自然语言命令"""
        logger.info(f"解析命令: {command}")
        
        # 清理命令
        original_command = command
        command = command.strip().lower()
        
        # 检查是否为空
        if not command:
            return self._create_response("error", "命令不能为空")
        
        # 按优先级顺序匹配意图
        for pattern_info in self.sorted_patterns:
            pattern = pattern_info["pattern"]
            match = re.search(pattern, command)
            if match:
                logger.info(f"匹配到意图: {pattern_info['intent_name']}, 模式: {pattern}")
                
                # 提取参数
                params = pattern_info["config"].get("default_params", {}).copy()
                
                # 提取查询条件或目标
                if pattern_info["config"].get("extract_query"):
                    query = self._extract_query(original_command, match, pattern_info["config"])
                    if query:
                        # 根据配置确定查询参数的字段名
                        query_field = pattern_info["config"].get("query_field", "query")
                        params[query_field] = query
                
                if pattern_info["config"].get("extract_target"):
                    target = self._extract_target(original_command, match)
                    if target:
                        params["target"] = target
                
                # 特殊处理：搜索命令的target参数
                if pattern_info["action"] == "search" and "target" not in params:
                    # 尝试从原始命令中提取搜索关键词
                    query = self._extract_search_query(original_command, match)
                    if query:
                        params["target"] = query
                
                # 提取其他参数
                params.update(self._extract_parameters(command))
                
                # 构建响应
                response = self._create_response(
                    action=pattern_info["action"],
                    parameters=params,
                    requires_confirmation=pattern_info["config"].get("requires_confirmation", False),
                    original_command=original_command
                )
                
                # 添加上下文信息
                if context:
                    response["context"] = context
                
                return response
        
        # 如果没有匹配到任何意图
        return self._create_response(
            action="unknown",
            parameters={"original_command": original_command},
            message="无法理解您的命令，请尝试更明确的表达"
        )
    
    def _extract_query(self, command: str, match: re.Match, config: Dict) -> Dict[str, Any]:
        """从命令中提取查询条件"""
        query = {}
        
        # 获取匹配的文本
        matched_text = match.group(1) if match.groups() else ""
        matched_text = matched_text.strip()  # 去除前后空格
        
        # 特殊处理：搜索命令直接返回关键词
        if config.get("action") == "search":
            return matched_text
        
        # 提取文件类型
        for type_name, extensions in self.file_type_mapping.items():
            if type_name in matched_text:
                query["type"] = type_name
                query["extensions"] = extensions
                break
        
        # 提取时间条件
        time_condition = self._extract_time_condition(matched_text)
        if time_condition:
            query["time"] = time_condition
        
        # 提取大小条件
        size_condition = self._extract_size_condition(matched_text)
        if size_condition:
            query["size"] = size_condition
        
        # 提取关键词
        keywords = self._extract_keywords(matched_text)
        if keywords:
            query["keywords"] = keywords
        
        return query
    
    def _extract_search_query(self, command: str, match: re.Match) -> str:
        """专门提取搜索查询"""
        if match.groups():
            return match.group(1).strip()
        
        # 如果没有匹配组，尝试从整个命令中提取
        # 移除命令前缀
        command_lower = command.lower()
        prefixes = ["搜索", "查找", "search", "find", "查询"]
        
        for prefix in prefixes:
            if command_lower.startswith(prefix):
                query = command[len(prefix):].strip()
                return query
        
        return ""
    
    def _extract_target(self, command: str, match: re.Match) -> str:
        """提取目标路径"""
        if match.groups():
            return match.group(1).strip()
        return ""
    
    def _extract_parameters(self, command: str) -> Dict[str, Any]:
        """提取其他参数"""
        params = {}
        
        # 提取强制标志
        if "强制" in command or "force" in command:
            params["force"] = True
        
        # 提取递归标志
        if "递归" in command or "所有" in command or "全部" in command or "recursive" in command:
            params["recursive"] = True
        
        # 提取深度限制
        depth_match = re.search(r"深度\s*(\d+)", command)
        if depth_match:
            params["depth"] = int(depth_match.group(1))
        
        return params
    
    def _extract_time_condition(self, text: str) -> Optional[Dict[str, Any]]:
        """提取时间条件"""
        for pattern, condition_type in self.time_patterns:
            match = re.search(pattern, text)
            if match:
                now = datetime.now()
                
                if condition_type == "today":
                    return {
                        "type": "today",
                        "start": now.replace(hour=0, minute=0, second=0),
                        "end": now.replace(hour=23, minute=59, second=59)
                    }
                elif condition_type == "yesterday":
                    yesterday = now - timedelta(days=1)
                    return {
                        "type": "yesterday",
                        "start": yesterday.replace(hour=0, minute=0, second=0),
                        "end": yesterday.replace(hour=23, minute=59, second=59)
                    }
                elif condition_type == "last_week":
                    start = now - timedelta(days=now.weekday() + 7)
                    end = start + timedelta(days=6)
                    return {
                        "type": "last_week",
                        "start": start.replace(hour=0, minute=0, second=0),
                        "end": end.replace(hour=23, minute=59, second=59)
                    }
                elif condition_type == "recent_days":
                    days = int(match.group(1))
                    start = now - timedelta(days=days)
                    return {
                        "type": "recent_days",
                        "days": days,
                        "start": start,
                        "end": now
                    }
        
        return None
    
    def _extract_size_condition(self, text: str) -> Optional[Dict[str, Any]]:
        """提取大小条件"""
        # 匹配模式：大于10MB，小于1GB，等于500KB
        patterns = [
            (r"大于\s*(\d+(?:\.\d+)?)\s*(MB|KB|GB|B)", ">"),
            (r"小于\s*(\d+(?:\.\d+)?)\s*(MB|KB|GB|B)", "<"),
            (r"等于\s*(\d+(?:\.\d+)?)\s*(MB|KB|GB|B)", "="),
        ]
        
        for pattern, operator in patterns:
            match = re.search(pattern, text)
            if match:
                size = float(match.group(1))
                unit = match.group(2)
                
                # 转换为字节
                multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
                size_bytes = size * multipliers.get(unit, 1)
                
                return {
                    "operator": operator,
                    "value": size_bytes,
                    "unit": unit
                }
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 移除已经匹配的部分
        cleaned = text
        
        # 移除时间表达式
        for pattern, _ in self.time_patterns:
            cleaned = re.sub(pattern, "", cleaned)
        
        # 移除大小表达式
        cleaned = re.sub(r"大于\s*\d+\s*\w+", "", cleaned)
        cleaned = re.sub(r"小于\s*\d+\s*\w+", "", cleaned)
        cleaned = re.sub(r"等于\s*\d+\s*\w+", "", cleaned)
        
        # 移除文件类型
        for type_name in self.file_type_mapping:
            cleaned = cleaned.replace(type_name, "")
        
        # 提取剩余的关键词
        keywords = [kw.strip() for kw in cleaned.split() if kw.strip() and len(kw.strip()) > 1]
        
        return keywords
    
    def _create_response(self, 
                        action: str, 
                        parameters: Dict[str, Any],
                        message: Optional[str] = None,
                        requires_confirmation: bool = False,
                        original_command: Optional[str] = None) -> Dict[str, Any]:
        """创建标准化响应"""
        response = {
            "success": True,
            "action": action,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat(),
            "requires_confirmation": requires_confirmation,
            "status": "parsed"
        }
        
        if message:
            response["message"] = message
        
        if original_command:
            response["original_command"] = original_command
        
        return response
    
    def validate_intent(self, intent: Dict[str, Any]) -> List[str]:
        """验证意图的有效性"""
        errors = []
        
        # 检查必要字段
        required_fields = ["action", "parameters"]
        for field in required_fields:
            if field not in intent:
                errors.append(f"缺少必要字段: {field}")
        
        # 验证 action
        valid_actions = {config["action"] for config in self.intent_patterns.values()}
        if "action" in intent and intent["action"] not in valid_actions and intent["action"] != "unknown":
            errors.append(f"无效的 action: {intent['action']}")
        
        return errors
    
    def generate_confirmation_message(self, intent: Dict[str, Any]) -> str:
        """生成确认消息"""
        action = intent.get("action", "")
        params = intent.get("parameters", {})
        
        messages = {
            "delete": f"您确定要删除 {params.get('target', '未知目标')} 吗？此操作不可撤销。",
            "index": "您确定要重新生成索引吗？这可能需要一些时间。",
            "archive": f"您确定要打包 {params.get('target', '未知目标')} 吗？",
        }
        
        return messages.get(action, "请确认是否执行此操作？")