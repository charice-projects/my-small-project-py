"""
增强版意图解析器 - 支持更复杂的自然语言命令
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
import json

from utils.logger import logger
from utils.validation import InputValidator


class EnhancedIntentParser:
    """增强版自然语言意图解析器"""
    
    def __init__(self):
        # 命令-意图映射词典
        self.command_vocabulary = {
            # ========== 系统状态 ==========
            "system_info": {
                "en": ["show status", "status", "system info", "system status", 
                       "server status", "health", "system health", "show system",
                       "server info", "system"],
                "zh": ["显示系统状态", "系统状态", "显示状态", "服务器状态",
                       "查看系统信息", "系统信息", "服务器信息", "系统健康",
                       "健康状态", "状态", "信息"],
                "action": "system_info",
                "priority": 1
            },
            
            # ========== 列表操作 ==========
            "list": {
                "en": ["show files", "list files", "ls", "list", "dir", 
                       "show directory", "dir list", "show list"],
                "zh": ["显示文件", "列出文件", "列表", "文件列表", "目录列表",
                       "查看文件", "浏览文件", "显示目录", "列出目录", "列出文档",
                       "显示文档", "文档列表", "查看文档"],
                "action": "list",
                "priority": 2
            },
            
            # ========== 搜索操作 ==========
            "search": {
                "en": ["search", "find", "locate", "search for", "look for",
                       "search file", "find file"],
                "zh": ["搜索", "查找", "查询", "搜索文件", "查找文件", "查询文件",
                       "搜索文档", "查找文档", "查询文档", "搜索图片", "查找图片",
                       "查询图片", "搜索图片", "查找图片", "查询图片"],
                "action": "search",
                "priority": 2,
                "needs_query": True
            },
            
            # ========== 最近文件 ==========
            "recent": {
                "en": ["recent files", "show recent", "recent", "latest files",
                       "recent documents", "recently accessed"],
                "zh": ["最近文件", "查看最近文件", "最近文档", "最近访问",
                       "最近打开", "近期文件", "最新文件", "最近", "近期"],
                "action": "recent",
                "priority": 3
            },
            
            # ========== 历史记录 ==========
            "history": {
                "en": ["history", "command history", "show history", "history list",
                       "recent commands"],
                "zh": ["历史记录", "命令历史", "查看历史", "历史列表",
                       "历史命令", "操作历史", "历史", "记录"],
                "action": "history",
                "priority": 3
            },
            
            # ========== 目录树 ==========
            "tree": {
                "en": ["tree", "directory tree", "show tree", "folder tree",
                       "directory structure"],
                "zh": ["目录树", "文件夹树", "显示目录树", "查看目录结构",
                       "目录结构", "文件夹结构", "树形结构", "目录"],
                "action": "tree",
                "priority": 3
            },
            
            # ========== 索引操作 ==========
            "index": {
                "en": ["index", "index files", "generate index", "create index",
                       "rebuild index", "update index", "scan files"],
                "zh": ["索引", "生成索引", "创建索引", "重建索引", "更新索引",
                       "扫描文件", "初始化索引", "建立索引"],
                "action": "index",
                "priority": 2
            },
            
            # ========== 文件操作 ==========
            "read": {
                "en": ["read", "open", "view", "open file", "read file"],
                "zh": ["读取", "打开", "查看", "打开文件", "读取文件"],
                "action": "read",
                "priority": 2,
                "needs_target": True
            },
            
            "delete": {
                "en": ["delete", "remove", "rm", "delete file", "remove file"],
                "zh": ["删除", "移除", "清除", "删除文件", "移除文件"],
                "action": "delete",
                "priority": 2,
                "needs_target": True,
                "requires_confirmation": True
            },
            
            # ========== 其他操作 ==========
            "create_dir": {
                "en": ["mkdir", "create dir", "create directory", "make dir"],
                "zh": ["创建目录", "新建文件夹", "建立目录", "创建文件夹"],
                "action": "create_dir",
                "priority": 2,
                "needs_target": True
            },
            
            "archive": {
                "en": ["archive", "zip", "compress", "pack", "create archive"],
                "zh": ["打包", "压缩", "归档", "创建压缩包", "打包文件"],
                "action": "archive",
                "priority": 2
            },
            
            "info": {
                "en": ["info", "information", "file info", "get info"],
                "zh": ["信息", "详情", "文件信息", "获取信息", "查看详情"],
                "action": "info",
                "priority": 3,
                "needs_target": True
            }
        }
        
        # 参数提取模式
        self.param_patterns = {
            "target": [
                (r"(.+?)(?:的|文件|文档|图片|文件夹|目录)?$", "direct"),  # 直接目标
                (r"^(?:打开|读取|查看|删除|编辑|创建)\s+(.+)", "action_prefix"),  # 动作前缀
                (r"^(?:file|document|folder|dir)\s+(.+)", "english_prefix"),  # 英文前缀
            ],
            "query": [
                (r"搜索\s+(.+)", "search_chinese"),
                (r"查找\s+(.+)", "find_chinese"),
                (r"查询\s+(.+)", "query_chinese"),
                (r"search\s+(.+)", "search_english"),
                (r"find\s+(.+)", "find_english"),
                (r"locate\s+(.+)", "locate_english"),
            ],
            "type": [
                (r"(图片|照片|图像)", "image"),
                (r"(文档|文件|文本)", "document"),
                (r"(代码|程序|源码)", "code"),
                (r"(视频|影片|电影)", "video"),
                (r"(音频|音乐|声音)", "audio"),
                (r"(压缩包|压缩文件|zip|rar)", "archive"),
            ]
        }
        
        # 构建正则表达式模式
        self.patterns = self._build_patterns()
        
        # 文件类型扩展名映射
        self.file_extensions = {
            "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
            "document": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".doc"],
            "code": [".py", ".js", ".java", ".cpp", ".c", ".h", ".html", ".css", ".json"],
            "video": [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"],
            "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"],
            "archive": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
        }
        
        # 同义词映射
        self.synonyms = {
            "文件": ["文档", "档案", "资料"],
            "图片": ["图像", "照片", "相片", "图"],
            "文档": ["文件", "文书", "文本"],
            "目录": ["文件夹", "目录夹", "路径"],
            "搜索": ["查找", "查询", "检索"],
            "显示": ["展示", "查看", "列出"],
        }
        
        logger.info("增强版意图解析器初始化完成")
    
    def _build_patterns(self):
        """构建正则表达式模式"""
        patterns = []
        
        for intent_name, intent_config in self.command_vocabulary.items():
            # 构建英文模式
            for en_cmd in intent_config["en"]:
                pattern = self._create_pattern(en_cmd, intent_config, is_english=True)
                patterns.append({
                    "pattern": pattern,
                    "intent_name": intent_name,
                    "action": intent_config["action"],
                    "config": intent_config,
                    "language": "en"
                })
            
            # 构建中文模式
            for zh_cmd in intent_config["zh"]:
                pattern = self._create_pattern(zh_cmd, intent_config, is_english=False)
                patterns.append({
                    "pattern": pattern,
                    "intent_name": intent_name,
                    "action": intent_config["action"],
                    "config": intent_config,
                    "language": "zh"
                })
        
        # 按优先级排序
        patterns.sort(key=lambda x: x["config"].get("priority", 10))
        return patterns
    
    def _create_pattern(self, command: str, config: Dict, is_english: bool = True) -> str:
        """创建正则表达式模式"""
        # 清理命令
        command = command.strip().lower()
        
        # 构建基本模式
        if is_english:
            # 英文模式：允许单词间有可选空格
            words = command.split()
            pattern_parts = []
            for word in words:
                # 允许单词有多种变体
                if word in ["file", "files"]:
                    pattern_parts.append(r"(?:file|files)?")
                elif word in ["dir", "directory", "folder"]:
                    pattern_parts.append(r"(?:dir|directory|folder)?")
                elif word in ["show", "display", "list"]:
                    pattern_parts.append(r"(?:show|display|list)?")
                else:
                    pattern_parts.append(re.escape(word))
            
            pattern = r"\s*" + r"\s+".join(pattern_parts) + r"\s*"
        else:
            # 中文模式：更灵活，允许同义词
            pattern = command
            for key, synonyms in self.synonyms.items():
                if key in pattern:
                    synonym_pattern = f"(?:{'|'.join([key] + synonyms)})"
                    pattern = pattern.replace(key, synonym_pattern)
            
            pattern = re.escape(pattern)
        
        # 添加开始和结束锚点
        return f"^{pattern}$"
    
    def parse(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """解析自然语言命令"""
        logger.info(f"增强版解析命令: {command}")
        
        original_command = command
        command = command.strip()
        command_lower = command.lower()
        
        # 空命令检查
        if not command:
            return self._create_error_response("命令不能为空")
        
        # 1. 精确匹配
        exact_match = self._exact_match(command_lower)
        if exact_match:
            logger.info(f"精确匹配到意图: {exact_match['intent_name']}")
            return self._build_response(exact_match, original_command)
        
        # 2. 模式匹配
        pattern_match = self._pattern_match(command_lower)
        if pattern_match:
            logger.info(f"模式匹配到意图: {pattern_match['intent_name']}")
            return self._build_response(pattern_match, original_command)
        
        # 3. 模糊匹配（编辑距离）
        fuzzy_match = self._fuzzy_match(command_lower)
        if fuzzy_match and fuzzy_match["confidence"] > 0.7:
            logger.info(f"模糊匹配到意图: {fuzzy_match['intent_name']} (置信度: {fuzzy_match['confidence']:.2f})")
            return self._build_response(fuzzy_match, original_command)
        
        # 4. 关键字提取匹配
        keyword_match = self._keyword_match(command_lower)
        if keyword_match:
            logger.info(f"关键字匹配到意图: {keyword_match['intent_name']}")
            return self._build_response(keyword_match, original_command)
        
        # 没有匹配到任何意图
        logger.warning(f"无法解析命令: {original_command}")
        return self._create_error_response(
            "无法理解您的命令，请尝试以下命令之一:\n" +
            "1. 显示系统状态 / show status\n" +
            "2. 列出文件 / list files\n" +
            "3. 搜索文档 / search documents\n" +
            "4. 查看最近文件 / recent files\n" +
            "5. 历史记录 / history\n" +
            "6. 目录树 / tree\n" +
            "7. 生成索引 / index"
        )
    
    def _exact_match(self, command: str) -> Optional[Dict]:
        """精确匹配"""
        for pattern_info in self.patterns:
            pattern = pattern_info["pattern"]
            if re.match(pattern, command, re.IGNORECASE):
                return pattern_info
        return None
    
    def _pattern_match(self, command: str) -> Optional[Dict]:
        """模式匹配（更灵活的匹配）"""
        best_match = None
        best_score = 0
        
        for pattern_info in self.patterns:
            pattern = pattern_info["pattern"]
            # 放宽匹配条件，允许部分匹配
            relaxed_pattern = pattern.replace("^", "^.*?").replace("$", ".*?$")
            
            match = re.match(relaxed_pattern, command, re.IGNORECASE)
            if match:
                # 计算匹配分数
                match_length = len(match.group(0))
                command_length = len(command)
                score = match_length / command_length
                
                if score > best_score:
                    best_score = score
                    best_match = pattern_info
        
        return best_match if best_score > 0.6 else None
    
    def _fuzzy_match(self, command: str) -> Optional[Dict]:
        """模糊匹配（编辑距离）"""
        from difflib import SequenceMatcher
        
        best_match = None
        best_ratio = 0
        
        for pattern_info in self.patterns:
            # 获取模式的文本表示
            pattern_text = pattern_info["pattern"]
            # 移除正则表达式标记
            pattern_text = re.sub(r'[\^\$\.\*\?\+\(\)\[\]\{\}\\\|]', '', pattern_text)
            
            ratio = SequenceMatcher(None, command, pattern_text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = pattern_info
        
        if best_match and best_ratio > 0.7:
            best_match = best_match.copy()
            best_match["confidence"] = best_ratio
            return best_match
        
        return None
    
    def _keyword_match(self, command: str) -> Optional[Dict]:
        """关键字提取匹配"""
        keyword_scores = {}
        
        for intent_name, intent_config in self.command_vocabulary.items():
            score = 0
            
            # 检查英文关键词
            for keyword in intent_config["en"]:
                if keyword in command:
                    score += 1
            
            # 检查中文关键词
            for keyword in intent_config["zh"]:
                if keyword in command:
                    score += 1
            
            if score > 0:
                keyword_scores[intent_name] = {
                    "score": score,
                    "config": intent_config
                }
        
        if keyword_scores:
            # 找到得分最高的意图
            best_intent = max(keyword_scores.items(), key=lambda x: x[1]["score"])
            intent_name, intent_data = best_intent
            
            return {
                "intent_name": intent_name,
                "action": intent_data["config"]["action"],
                "config": intent_data["config"],
                "confidence": intent_data["score"] / 10.0  # 归一化到0-1
            }
        
        return None
    
    def _extract_parameters(self, command: str, intent_config: Dict) -> Dict[str, Any]:
        """提取命令参数"""
        params = {}
        
        # 提取目标
        if intent_config.get("needs_target"):
            target = self._extract_target(command)
            if target:
                params["target"] = target
        
        # 提取查询
        if intent_config.get("needs_query"):
            query = self._extract_query(command)
            if query:
                params["target"] = query  # 搜索查询放在target字段
            elif intent_config["action"] == "search":
                # 对于搜索命令，如果没有查询词，使用默认值
                params["target"] = ""
        
        # 提取文件类型
        file_type = self._extract_file_type(command)
        if file_type:
            params["type"] = file_type
            params["extensions"] = self.file_extensions.get(file_type, [])
        
        # 提取其他参数
        if "递归" in command or "recursive" in command:
            params["recursive"] = True
        
        if "强制" in command or "force" in command:
            params["force"] = True
        
        return params
    
    def _extract_target(self, command: str) -> Optional[str]:
        """提取目标路径"""
        # 简单实现：返回命令中最后一个词
        words = command.split()
        if len(words) > 1:
            return words[-1]
        return None
    
    def _extract_query(self, command: str) -> Optional[str]:
        """提取搜索查询"""
        # 移除命令前缀
        prefixes = ["搜索", "查找", "查询", "search", "find", "locate"]
        
        for prefix in prefixes:
            if command.startswith(prefix):
                query = command[len(prefix):].strip()
                if query:
                    return query
        
        # 如果没有明确前缀，尝试提取名词
        words = command.split()
        if len(words) > 1:
            return words[-1]
        
        return None
    
    def _extract_file_type(self, command: str) -> Optional[str]:
        """提取文件类型"""
        for type_name in self.file_extensions.keys():
            if type_name in command:
                return type_name
        
        # 检查中文类型名
        type_mapping = {
            "图片": "image",
            "文档": "document",
            "代码": "code",
            "视频": "video",
            "音频": "audio",
            "压缩包": "archive"
        }
        
        for chinese_type, english_type in type_mapping.items():
            if chinese_type in command:
                return english_type
        
        return None
    
    def _build_response(self, match_info: Dict, original_command: str) -> Dict[str, Any]:
        """构建响应"""
        action = match_info["action"]
        config = match_info["config"]
        
        # 提取参数
        params = self._extract_parameters(original_command, config)
        
        response = {
            "success": True,
            "action": action,
            "parameters": params,
            "timestamp": datetime.now().isoformat(),
            "requires_confirmation": config.get("requires_confirmation", False),
            "original_command": original_command,
            "parser_version": "enhanced_v1.0"
        }
        
        # 添加置信度信息（如果可用）
        if "confidence" in match_info:
            response["confidence"] = match_info["confidence"]
        
        # 对于搜索命令，如果查询为空，添加提示
        if action == "search" and not params.get("target"):
            response["message"] = "请输入要搜索的关键词，例如：搜索文档、search test"
        
        logger.info(f"解析结果: action={action}, params={params}")
        return response
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "action": "unknown",
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "requires_confirmation": False,
            "status": "parse_error"
        }
    
    def validate_intent(self, intent: Dict[str, Any]) -> List[str]:
        """验证意图的有效性"""
        errors = []
        
        required_fields = ["action", "parameters"]
        for field in required_fields:
            if field not in intent:
                errors.append(f"缺少必要字段: {field}")
        
        # 检查action是否有效
        valid_actions = {config["action"] for config in self.command_vocabulary.values()}
        if "action" in intent and intent["action"] not in valid_actions and intent["action"] != "unknown":
            errors.append(f"无效的 action: {intent['action']}")
        
        return errors


# 向后兼容的包装器
class IntentParser(EnhancedIntentParser):
    """兼容原有接口的意图解析器"""
    def __init__(self):
        super().__init__()


# 全局实例
intent_parser = IntentParser()