"""
上下文管理器 - 维护跨会话的上下文信息
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from collections import OrderedDict

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils


class ContextManager:
    """上下文管理器"""
    
    def __init__(self, context_file: Optional[str] = None):
        if context_file is None:
            data_dir = PathUtils.get_data_dir()
            self.context_file = data_dir / "context_cache.json"
        else:
            self.context_file = Path(context_file)
        
        self.context = self._load_context()
        self.max_history_size = settings.context_history_size
        
        # 自动保存定时器
        self.last_save_time = time.time()
        self.auto_save_interval = 300  # 5分钟
    
    def _load_context(self) -> Dict[str, Any]:
        """加载上下文"""
        try:
            if self.context_file.exists():
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    context = json.load(f)
                    logger.info(f"上下文已加载: {self.context_file}")
                    return context
            else:
                logger.info("创建新的上下文")
                return self._create_default_context()
        except Exception as e:
            logger.error(f"加载上下文失败: {e}")
            return self._create_default_context()
    
    def _create_default_context(self) -> Dict[str, Any]:
        """创建默认上下文"""
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "session_id": self._generate_session_id(),
            "current_workspace": settings.root_path,
            "user_preferences": {},
            "command_history": [],
            "file_access_history": [],
            "workspace_contexts": {},
            "intent_patterns": {},
            "tags": {},
            "bookmarks": [],
            "recent_files": OrderedDict(),
            "system_state": {
                "last_index_time": None,
                "last_backup_time": None,
                "total_operations": 0,
                "error_count": 0
            }
        }
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def save_context(self, force: bool = False) -> bool:
        """保存上下文"""
        try:
            current_time = time.time()
            
            # 检查是否需要自动保存
            if not force and not settings.context_auto_save:
                return False
            
            if not force and current_time - self.last_save_time < self.auto_save_interval:
                return False
            
            self.context["last_updated"] = datetime.now().isoformat()
            
            # 确保目录存在
            self.context_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(self.context, f, indent=2, ensure_ascii=False)
            
            self.last_save_time = current_time
            logger.debug("上下文已保存")
            return True
        
        except Exception as e:
            logger.error(f"保存上下文失败: {e}")
            return False
    
    def update_context(self, updates: Dict[str, Any]) -> None:
        """更新上下文"""
        self._deep_update(self.context, updates)
        self.save_context()
    
    def _deep_update(self, original: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """深度更新字典"""
        for key, value in updates.items():
            if key in original and isinstance(original[key], dict) and isinstance(value, dict):
                self._deep_update(original[key], value)
            else:
                original[key] = value
    
    def add_command_to_history(self, 
                              command: str, 
                              intent: Dict[str, Any], 
                              result: Dict[str, Any]) -> None:
        """添加命令到历史记录"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "intent": intent,
            "result": {
                "success": result.get("success", False),
                "action": result.get("action", ""),
                "message": result.get("message", ""),
                "data_count": len(result.get("data", [])),
                "execution_time": result.get("execution_time", 0)
            },
            "context_snapshot": {
                "workspace": self.context.get("current_workspace"),
                "user": self.context.get("user_preferences", {}).get("name", "anonymous")
            }
        }
        
        # 添加到历史记录
        self.context["command_history"].append(history_entry)
        
        # 限制历史记录大小
        if len(self.context["command_history"]) > self.max_history_size:
            self.context["command_history"] = self.context["command_history"][-self.max_history_size:]
        
        # 更新系统状态
        self.context["system_state"]["total_operations"] += 1
        if not result.get("success", False):
            self.context["system_state"]["error_count"] += 1
        
        self.save_context()
    
    def add_file_access(self, 
                       file_path: str, 
                       operation: str, 
                       success: bool = True) -> None:
        """记录文件访问"""
        access_entry = {
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "relative_path": PathUtils.get_relative_path(file_path),
            "operation": operation,
            "success": success,
            "user_context": self.context.get("user_preferences", {}).get("name", "anonymous")
        }
        
        self.context["file_access_history"].append(access_entry)
        
        # 限制历史记录大小
        max_file_history = 1000
        if len(self.context["file_access_history"]) > max_file_history:
            self.context["file_access_history"] = self.context["file_access_history"][-max_file_history:]
        
        # 添加到最近文件列表
        if operation in ["read", "write", "open"] and success:
            self.context["recent_files"][file_path] = datetime.now().isoformat()
            
            # 限制最近文件数量
            max_recent_files = 100
            if len(self.context["recent_files"]) > max_recent_files:
                # 删除最旧的条目
                oldest_key = next(iter(self.context["recent_files"]))
                del self.context["recent_files"][oldest_key]
        
        self.save_context()
    
    def get_recent_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近访问的文件"""
        recent_files = []
        
        # 按时间排序
        sorted_files = sorted(
            self.context["recent_files"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for file_path, timestamp in sorted_files[:limit]:
            try:
                file_info = PathUtils.get_file_info(file_path)
                recent_files.append({
                    "path": file_path,
                    "relative_path": PathUtils.get_relative_path(file_path),
                    "name": file_info["name"],
                    "last_accessed": timestamp,
                    "size": file_info["size"],
                    "size_human": file_info["size_human"],
                    "type": "file" if file_info["is_file"] else "directory"
                })
            except Exception as e:
                logger.warning(f"获取文件信息失败 {file_path}: {e}")
                continue
        
        return recent_files
    
    def set_workspace_context(self, 
                             workspace_path: str, 
                             context_data: Dict[str, Any]) -> None:
        """设置工作区上下文"""
        workspace_key = PathUtils.get_relative_path(workspace_path)
        
        if "workspace_contexts" not in self.context:
            self.context["workspace_contexts"] = {}
        
        self.context["workspace_contexts"][workspace_key] = {
            "path": workspace_path,
            "last_accessed": datetime.now().isoformat(),
            "context": context_data,
            "file_count": context_data.get("file_count", 0),
            "index_version": context_data.get("index_version", "1.0")
        }
        
        self.save_context()
    
    def get_workspace_context(self, workspace_path: str) -> Optional[Dict[str, Any]]:
        """获取工作区上下文"""
        workspace_key = PathUtils.get_relative_path(workspace_path)
        
        if (workspace_key in self.context.get("workspace_contexts", {}) and
            self.context["workspace_contexts"][workspace_key]["path"] == workspace_path):
            return self.context["workspace_contexts"][workspace_key]["context"]
        
        return None
    
    def update_intent_pattern(self, 
                             intent_type: str, 
                             pattern: str, 
                             success_rate: float) -> None:
        """更新意图模式"""
        if "intent_patterns" not in self.context:
            self.context["intent_patterns"] = {}
        
        if intent_type not in self.context["intent_patterns"]:
            self.context["intent_patterns"][intent_type] = []
        
        # 查找现有模式
        pattern_found = False
        for p in self.context["intent_patterns"][intent_type]:
            if p["pattern"] == pattern:
                p["success_rate"] = success_rate
                p["last_used"] = datetime.now().isoformat()
                p["use_count"] = p.get("use_count", 0) + 1
                pattern_found = True
                break
        
        # 添加新模式
        if not pattern_found:
            self.context["intent_patterns"][intent_type].append({
                "pattern": pattern,
                "success_rate": success_rate,
                "last_used": datetime.now().isoformat(),
                "use_count": 1,
                "created_at": datetime.now().isoformat()
            })
        
        self.save_context()
    
    def add_bookmark(self, 
                    path: str, 
                    name: Optional[str] = None, 
                    tags: Optional[List[str]] = None) -> None:
        """添加书签"""
        bookmark = {
            "id": len(self.context.get("bookmarks", [])),
            "path": path,
            "relative_path": PathUtils.get_relative_path(path),
            "name": name or Path(path).name,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0
        }
        
        if "bookmarks" not in self.context:
            self.context["bookmarks"] = []
        
        self.context["bookmarks"].append(bookmark)
        self.save_context()
    
    def get_bookmarks(self, 
                     tag_filter: Optional[str] = None, 
                     limit: int = 50) -> List[Dict[str, Any]]:
        """获取书签"""
        bookmarks = self.context.get("bookmarks", [])
        
        if tag_filter:
            bookmarks = [b for b in bookmarks if tag_filter in b.get("tags", [])]
        
        # 按最后访问时间排序
        bookmarks.sort(key=lambda x: x.get("last_accessed", ""), reverse=True)
        
        return bookmarks[:limit]
    
    def update_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """更新用户偏好"""
        if "user_preferences" not in self.context:
            self.context["user_preferences"] = {}
        
        self.context["user_preferences"].update(preferences)
        self.save_context()
    
    def get_command_history(self, 
                           limit: int = 50, 
                           filter_action: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取命令历史"""
        history = self.context.get("command_history", [])
        
        if filter_action:
            history = [h for h in history if h.get("intent", {}).get("action") == filter_action]
        
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return history[:limit]
    
    def clear_history(self, history_type: str = "all") -> bool:
        """清除历史记录"""
        try:
            if history_type in ["all", "command"]:
                self.context["command_history"] = []
            
            if history_type in ["all", "file"]:
                self.context["file_access_history"] = []
                self.context["recent_files"] = OrderedDict()
            
            if history_type in ["all", "bookmarks"]:
                self.context["bookmarks"] = []
            
            self.save_context()
            return True
        
        except Exception as e:
            logger.error(f"清除历史记录失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_commands": len(self.context.get("command_history", [])),
            "total_file_access": len(self.context.get("file_access_history", [])),
            "total_bookmarks": len(self.context.get("bookmarks", [])),
            "recent_files_count": len(self.context.get("recent_files", {})),
            "workspace_contexts_count": len(self.context.get("workspace_contexts", {})),
            "system_state": self.context.get("system_state", {}),
            "session_duration": self._get_session_duration()
        }
    
    def _get_session_duration(self) -> str:
        """获取会话持续时间"""
        try:
            created_at = datetime.fromisoformat(self.context.get("created_at", datetime.now().isoformat()))
            duration = datetime.now() - created_at
            
            days = duration.days
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}天 {hours}小时"
            elif hours > 0:
                return f"{hours}小时 {minutes}分钟"
            else:
                return f"{minutes}分钟"
        except Exception:
            return "未知"
    
    def export_context(self, export_path: str) -> bool:
        """导出上下文到文件"""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "context": self.context,
                "metadata": {
                    "version": "1.0",
                    "export_type": "full_context",
                    "source": "omniframe_context_manager"
                }
            }
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"上下文已导出到: {export_file}")
            return True
        
        except Exception as e:
            logger.error(f"导出上下文失败: {e}")
            return False
    
    def import_context(self, import_path: str) -> bool:
        """从文件导入上下文"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                logger.error(f"导入文件不存在: {import_file}")
                return False
            
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "context" not in import_data:
                logger.error("导入文件格式错误")
                return False
            
            # 合并上下文
            self._deep_update(self.context, import_data["context"])
            self.save_context()
            
            logger.info(f"上下文已从文件导入: {import_file}")
            return True
        
        except Exception as e:
            logger.error(f"导入上下文失败: {e}")
            return False