"""
AI建议服务 - 提供智能建议和预测（预留功能）
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
from core.context_manager import ContextManager


class AISuggestionService:
    """AI建议服务"""
    
    def __init__(self):
        self.context_manager = ContextManager()
        self.suggestion_cache = {}
        self.last_analysis_time = None
        
    def analyze_work_patterns(self) -> Dict[str, Any]:
        """分析工作模式"""
        try:
            history = self.context_manager.get_command_history(limit=100)
            
            if not history:
                return {"patterns": [], "common_actions": []}
            
            # 分析常用操作
            action_counts = {}
            time_patterns = []
            
            for entry in history:
                action = entry.get("intent", {}).get("action", "unknown")
                action_counts[action] = action_counts.get(action, 0) + 1
                
                # 分析时间模式
                timestamp = entry.get("timestamp")
                if timestamp:
                    try:
                        time_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_patterns.append({
                            "hour": time_obj.hour,
                            "weekday": time_obj.weekday()
                        })
                    except Exception:
                        pass
            
            # 识别常见操作
            common_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 识别高峰时段
            hour_counts = {}
            for pattern in time_patterns:
                hour = pattern["hour"]
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            return {
                "common_actions": [{"action": a, "count": c} for a, c in common_actions],
                "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
                "total_operations": len(history),
                "analysis_time": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"工作模式分析失败: {e}")
            return {"error": str(e)}
    
    def get_file_suggestions(self, current_path: str) -> List[Dict[str, Any]]:
        """获取文件建议"""
        try:
            suggestions = []
            
            # 基于最近访问的建议
            recent_files = self.context_manager.get_recent_files(limit=10)
            
            # 基于当前目录的建议
            current_dir = PathUtils.normalize_path(current_path)
            if current_dir.exists() and current_dir.is_dir():
                try:
                    items = list(current_dir.iterdir())
                    
                    # 建议最近修改的文件
                    recent_items = sorted(
                        [item for item in items if item.is_file()],
                        key=lambda x: x.stat().st_mtime,
                        reverse=True
                    )[:5]
                    
                    for item in recent_items:
                        suggestions.append({
                            "type": "recent_in_dir",
                            "path": str(item),
                            "name": item.name,
                            "reason": "最近修改的文件",
                            "confidence": 0.7
                        })
                
                except PermissionError:
                    pass
            
            # 基于历史访问的建议
            for file_info in recent_files[:5]:
                suggestions.append({
                    "type": "frequently_accessed",
                    "path": file_info["path"],
                    "name": file_info["name"],
                    "reason": "经常访问的文件",
                    "confidence": 0.8
                })
            
            return suggestions
        
        except Exception as e:
            logger.error(f"获取文件建议失败: {e}")
            return []
    
    def predict_next_actions(self) -> List[Dict[str, Any]]:
        """预测下一步操作"""
        try:
            predictions = []
            
            # 分析历史模式
            patterns = self.analyze_work_patterns()
            
            # 基于常见操作的预测
            for action_info in patterns.get("common_actions", [])[:3]:
                action = action_info["action"]
                
                if action in ["list", "search"]:
                    predictions.append({
                        "action": "list",
                        "command": "列出最近文件",
                        "reason": "您经常查看文件列表",
                        "confidence": 0.6
                    })
                elif action in ["read", "open"]:
                    predictions.append({
                        "action": "read",
                        "command": "打开最近文档",
                        "reason": "您经常阅读文档",
                        "confidence": 0.7
                    })
            
            # 基于时间的预测
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 12:
                predictions.append({
                    "action": "index",
                    "command": "更新文件索引",
                    "reason": "上午通常是整理文件的好时机",
                    "confidence": 0.5
                })
            elif 14 <= current_hour <= 17:
                predictions.append({
                    "action": "archive",
                    "command": "打包今天的工作",
                    "reason": "下午适合归档文件",
                    "confidence": 0.5
                })
            
            return predictions
        
        except Exception as e:
            logger.error(f"预测操作失败: {e}")
            return []
    
    def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """提供优化建议"""
        suggestions = []
        
        try:
            # 检查索引状态
            from core.file_indexer import FileIndexer
            indexer = FileIndexer()
            index_status = indexer.get_index_status()
            
            if not index_status.get("has_index", False):
                suggestions.append({
                    "type": "index",
                    "title": "创建文件索引",
                    "description": "尚未创建文件索引，建议初始化索引以提高搜索效率",
                    "priority": "high",
                    "command": "初始化索引"
                })
            
            # 检查工作空间使用情况
            import psutil
            try:
                disk = psutil.disk_usage(settings.root_path)
                if disk.percent > 80:
                    suggestions.append({
                        "type": "cleanup",
                        "title": "清理磁盘空间",
                        "description": f"工作空间磁盘使用率较高 ({disk.percent}%)",
                        "priority": "medium",
                        "command": "找出大文件"
                    })
            except Exception:
                pass
            
            # 检查上下文历史
            stats = self.context_manager.get_statistics()
            total_commands = stats.get("total_commands", 0)
            
            if total_commands > 100:
                suggestions.append({
                    "type": "maintenance",
                    "title": "清理历史记录",
                    "description": f"已有 {total_commands} 条命令历史，建议清理",
                    "priority": "low",
                    "command": "清理历史"
                })
            
            return suggestions
        
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            return []
    
    def get_contextual_help(self, current_command: str) -> Dict[str, Any]:
        """获取上下文帮助"""
        help_info = {
            "current_command": current_command,
            "suggestions": [],
            "related_commands": [],
            "examples": []
        }
        
        # 基于命令类型提供帮助
        if "list" in current_command.lower():
            help_info["related_commands"] = [
                "列出所有文件",
                "列出图片文件",
                "列出最近修改的文件",
                "列出大文件"
            ]
            help_info["examples"] = [
                "list /path/to/dir - 列出目录内容",
                "list --recursive - 递归列出",
                "list --sort size --desc - 按大小降序排列"
            ]
        
        elif "search" in current_command.lower():
            help_info["related_commands"] = [
                "搜索文档",
                "查找图片",
                "按内容搜索",
                "按名称搜索"
            ]
            help_info["examples"] = [
                "search 'keyword' - 搜索关键词",
                "search '*.md' --type name - 按名称搜索",
                "search 'TODO' --path /src - 在指定路径搜索"
            ]
        
        elif "index" in current_command.lower():
            help_info["related_commands"] = [
                "初始化索引",
                "更新索引",
                "重建索引",
                "索引状态"
            ]
        
        return help_info


# 全局实例
ai_suggestion_service = AISuggestionService()