#!/usr/bin/env python3
"""
简化版部署修复脚本
"""
import os
import sys
import shutil
import time
from pathlib import Path
from datetime import datetime

def backup_file(file_path):
    """备份文件"""
    backup_dir = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    if Path(file_path).exists():
        backup_path = backup_dir / Path(file_path).name
        shutil.copy2(file_path, backup_path)
        print(f"✅ 已备份: {file_path} -> {backup_path}")
        return True
    else:
        print(f"⚠️  文件不存在: {file_path}")
        return False

def deploy_enhanced_parser():
    """部署增强版意图解析器"""
    print("\n2. 部署增强版意图解析器")
    
    # 增强版意图解析器的完整代码
    enhanced_parser_code = '''
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
        # 意图模式库  
        self.intent_patterns = {  
            # ========== 系统状态相关 ==========  
            "system_info": {  
                "patterns": [  
                    r"^\\s*(show\\s+status|status|系统状态|显示状态|服务器状态)\\s*$",  
                    r"^\\s*show\\s+system\\s*$",  
                    r"^\\s*system\\s+status\\s*$",  
                    r"^\\s*system\\s+info\\s*$",  
                    r"^\\s*server\\s+status\\s*$",  
                    r"^\\s*health\\s*$",  
                    r"^\\s*显示系统状态\\s*$",  
                    r"^\\s*查看系统信息\\s*$",  
                ],  
                "action": "system_info",  
                "default_params": {}  
            },  
            
            # ========== 搜索相关 ==========  
            "search": {  
                "patterns": [  
                    r"^搜索\\s+(.+)$",  
                    r"^查找\\s+(.+)$",  
                    r"^搜索文件\\s+(.+)$",  
                    r"^find\\s+(.+)$",  
                    r"^search\\s+(.+)$",  
                    r"^查询\\s+(.+)$",  
                    r"^搜索文档$",  
                    r"^查找文档$",  
                    r"^查找图片$",  
                ],  
                "action": "search",  
                "extract_query": True  
            },  
            
            # ========== 列表相关 ==========  
            "list": {  
                "patterns": [  
                    r"^显示\\s+(.+)\\s+列表$",  
                    r"^查看\\s+(.+)$",  
                    r"^浏览\\s+(.+)$",  
                    r"^list\\s+(.+)$",  
                    r"^ls\\s+(.+)$",  
                    r"^dir\\s+(.+)$",  
                    r"^显示文件$",  
                    r"^list$",  
                    r"^ls$",  
                    r"^dir$",  
                    r"^列出文件$",  
                    r"^列出\\s+(.+)$",  
                    r"^列出文档$",  
                ],  
                "action": "list",  
                "extract_query": True  
            },  
            
            # ========== 最近文件相关 ==========  
            "recent": {  
                "patterns": [  
                    r"^recent$",  
                    r"^recent files$",  
                    r"^recently accessed$",  
                    r"^最近文件$",  
                    r"^查看最近文件$",  
                    r"^最近访问$",  
                ],  
                "action": "recent",  
                "default_params": {}  
            },  
            
            # ========== 历史记录相关 ==========  
            "history": {  
                "patterns": [  
                    r"^history$",  
                    r"^command history$",  
                    r"^历史记录$",  
                    r"^查看历史$",  
                ],  
                "action": "history",  
                "default_params": {}  
            },  
            
            # ========== 目录树相关 ==========  
            "tree": {  
                "patterns": [  
                    r"^tree$",  
                    r"^directory tree$",  
                    r"^目录树$",  
                    r"^查看目录结构$",  
                ],  
                "action": "tree",  
                "default_params": {}  
            },  
            
            # ========== 索引相关 ==========  
            "index": {  
                "patterns": [  
                    r"^初始化索引$",  
                    r"^生成索引$",  
                    r"^更新索引$",  
                    r"^重建索引$",  
                    r"^scan\\s+files$",  
                    r"^index$",  
                    r"^index\\s+(?:all|files)?$",  
                    r"^扫描文件$",  
                ],  
                "action": "index",  
                "default_params": {"force": False}  
            },  
            
            # ========== 其他意图 ==========  
            "read": {  
                "patterns": [  
                    r"^读取\\s+(.+)$",  
                    r"^打开\\s+(.+)$",  
                    r"^查看文件\\s+(.+)$",  
                    r"^read\\s+(.+)$",  
                    r"^open\\s+(.+)$",  
                ],  
                "action": "read",  
                "extract_target": True  
            },  
            
            "delete": {  
                "patterns": [  
                    r"^删除\\s+(.+)$",  
                    r"^移除\\s+(.+)$",  
                    r"^delete\\s+(.+)$",  
                    r"^remove\\s+(.+)$",  
                    r"^rm\\s+(.+)$",  
                ],  
                "action": "delete",  
                "extract_target": True,  
                "requires_confirmation": True  
            },  
            
            "info": {  
                "patterns": [  
                    r"^(.+?)\\s+的信息$",  
                    r"^查看\\s+(.+?)\\s+详情$",  
                    r"^info\\s+(.+)$",  
                ],  
                "action": "info",  
                "extract_target": True  
            },  
            
            "archive": {  
                "patterns": [  
                    r"^打包\\s+(.+)$",  
                    r"^压缩\\s+(.+)$",  
                    r"^归档\\s+(.+)$",  
                    r"^archive\\s+(.+)$",  
                    r"^zip\\s+(.+)$",  
                ],  
                "action": "archive",  
                "extract_target": True  
            },  
        }  
        
        logger.info("意图解析器初始化完成")  
    
    def parse(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:  
        """解析自然语言命令"""  
        logger.info(f"解析命令: {command}")  
        
        # 清理命令  
        original_command = command  
        command = command.strip().lower()  
        
        # 检查是否为空  
        if not command:  
            return self._create_error_response("命令不能为空")  
        
        # 按优先级顺序匹配意图  
        priority_order = ["system_info", "search", "recent", "history", "tree", "list", "index", "read", "delete"]  
        
        for intent_name in priority_order:  
            intent_config = self.intent_patterns.get(intent_name)  
            if not intent_config:  
                continue  
                
            for pattern in intent_config["patterns"]:  
                match = re.search(pattern, command)  
                if match:  
                    logger.info(f"匹配到意图: {intent_name}, 模式: {pattern}")  
                    
                    # 提取参数  
                    params = intent_config.get("default_params", {}).copy()  
                    
                    # 提取查询条件或目标  
                    if intent_config.get("extract_query"):  
                        query = self._extract_query(original_command, match)  
                        if query:  
                            params["query"] = query  
                    
                    if intent_config.get("extract_target"):  
                        target = self._extract_target(original_command, match)  
                        if target:  
                            params["target"] = target  
                    
                    # 对于搜索命令，如果没有参数，设置target为空  
                    if intent_config["action"] == "search" and "target" not in params:  
                        params["target"] = ""  
                    
                    # 构建响应  
                    response = self._create_response(  
                        action=intent_config["action"],  
                        parameters=params,  
                        requires_confirmation=intent_config.get("requires_confirmation", False),  
                        original_command=original_command  
                    )  
                    
                    # 添加上下文信息  
                    if context:  
                        response["context"] = context  
                    
                    return response  
        
        # 如果没有匹配到任何意图  
        return self._create_error_response(  
            "无法理解您的命令，请尝试更明确的表达"  
        )  
    
    def _extract_query(self, command: str, match: re.Match) -> Dict[str, Any]:  
        """从命令中提取查询条件"""  
        query = {}  
        
        # 获取匹配的文本  
        matched_text = match.group(1) if match.groups() else ""  
        matched_text = matched_text.strip()  
        
        # 特殊处理：搜索命令直接返回关键词  
        if matched_text:  
            return matched_text  
        
        return query  
    
    def _extract_target(self, command: str, match: re.Match) -> str:  
        """提取目标路径"""  
        if match.groups():  
            return match.group(1).strip()  
        return ""  
    
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
'''
    
    # 写入到文件
    with open("core/intent_parser.py", "w", encoding="utf-8") as f:
        f.write(enhanced_parser_code)
    
    print("✅ 意图解析器部署完成")

def deploy_files():
    """部署所有修复文件"""
    print("=" * 60)
    print("开始部署修复文件")
    print("=" * 60)
    
    # 1. 备份原文件
    print("\n1. 备份原文件")
    files_to_backup = [
        "core/intent_parser.py",
        "core/task_dispatcher.py",
    ]
    
    for file in files_to_backup:
        backup_file(file)
    
    # 2. 部署增强版意图解析器
    deploy_enhanced_parser()
    
    print("\n" + "=" * 60)
    print("部署完成!")
    print("请手动重启服务器: python cli.py stop && python cli.py start")
    print("然后运行测试: python test_commands.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    deploy_files()