
"""
增强版上下文管理器 - 支持交互式会话
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from utils.logger import logger


class EnhancedContextManager:
    """增强版上下文管理器"""
    
    def __init__(self, data_dir: str = "./data/context"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.contexts = {}
        self.interactive_sessions = {}
        
        # 加载持久化数据
        self._load_persisted_contexts()
    
    def _load_persisted_contexts(self):
        """加载持久化的上下文"""
        try:
            context_file = self.data_dir / "contexts.json"
            if context_file.exists():
                with open(context_file, 'r', encoding='utf-8') as f:
                    self.contexts = json.load(f)
                logger.info(f"已加载 {len(self.contexts)} 个持久化上下文")
        except Exception as e:
            logger.error(f"加载上下文失败: {e}")
            self.contexts = {}
    
    def _save_persisted_contexts(self):
        """保存持久化的上下文"""
        try:
            context_file = self.data_dir / "contexts.json"
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(self.contexts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存上下文失败: {e}")
    
    def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """初始化会话"""
        context = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "command_history": [],
            "file_access_history": [],
            "interactive_state": {},
            "preferences": {
                "language": "auto",
                "theme": "default",
                "notifications": True
            }
        }
        
        self.contexts[session_id] = context
        self._save_persisted_contexts()
        
        logger.info(f"初始化会话: {session_id}")
        return context
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """获取会话上下文"""
        context = self.contexts.get(session_id)
        
        if not context:
            context = self.initialize_session(session_id)
        
        # 更新最后活动时间
        context["last_activity"] = datetime.now().isoformat()
        
        return context
    
    def update_context(self, session_id: str, updates: Dict[str, Any]):
        """更新会话上下文"""
        context = self.get_context(session_id)
        context.update(updates)
        self.contexts[session_id] = context
        self._save_persisted_contexts()
    
    def add_command_history(self, session_id: str, command: str, action: str, success: bool, message: str = ""):
        """添加命令历史"""
        context = self.get_context(session_id)
        
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "action": action,
            "success": success,
            "message": message
        }
        
        context["command_history"].append(history_entry)
        
        # 限制历史记录数量
        if len(context["command_history"]) > 1000:
            context["command_history"] = context["command_history"][-1000:]
        
        self.contexts[session_id] = context
        self._save_persisted_contexts()
    
    def add_file_access(self, session_id: str, file_path: str, action: str, success: bool):
        """添加文件访问记录"""
        context = self.get_context(session_id)
        
        access_entry = {
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "action": action,
            "success": success
        }
        
        context["file_access_history"].append(access_entry)
        
        # 限制历史记录数量
        if len(context["file_access_history"]) > 500:
            context["file_access_history"] = context["file_access_history"][-500:]
        
        self.contexts[session_id] = context
        self._save_persisted_contexts()
    
    def set_interactive_state(self, session_id: str, state: Dict[str, Any]):
        """设置交互式状态"""
        context = self.get_context(session_id)
        context["interactive_state"] = state
        self.contexts[session_id] = context
        self._save_persisted_contexts()
    
    def get_interactive_state(self, session_id: str) -> Dict[str, Any]:
        """获取交互式状态"""
        context = self.get_context(session_id)
        return context.get("interactive_state", {})
    
    def clear_interactive_state(self, session_id: str):
        """清除交互式状态"""
        context = self.get_context(session_id)
        context["interactive_state"] = {}
        self.contexts[session_id] = context
        self._save_persisted_contexts()
    
    def get_command_history(self, session_id: str, limit: int = 50, filter_action: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取命令历史"""
        context = self.get_context(session_id)
        history = context.get("command_history", [])
        
        if filter_action:
            history = [h for h in history if h.get("action") == filter_action]
        
        return history[-limit:] if limit > 0 else history
    
    def get_recent_files(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近访问的文件"""
        context = self.get_context(session_id)
        access_history = context.get("file_access_history", [])
        
        # 按时间戳排序
        sorted_history = sorted(access_history, key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # 去重（基于文件路径）
        unique_files = []
        seen_paths = set()
        
        for entry in sorted_history:
            file_path = entry.get("file_path")
            if file_path and file_path not in seen_paths:
                seen_paths.add(file_path)
                unique_files.append(entry)
            
            if len(unique_files) >= limit:
                break
        
        return unique_files
    
    def get_statistics(self, session_id: str) -> Dict[str, Any]:
        """获取统计信息"""
        context = self.get_context(session_id)
        
        created_at = datetime.fromisoformat(context.get("created_at", datetime.now().isoformat()))
        duration = datetime.now() - created_at
        
        command_history = context.get("command_history", [])
        successful_commands = len([c for c in command_history if c.get("success", False)])
        failed_commands = len([c for c in command_history if not c.get("success", False)])
        
        return {
            "session_duration": str(duration),
            "total_commands": len(command_history),
            "successful_commands": successful_commands,
            "failed_commands": failed_commands,
            "success_rate": (successful_commands / len(command_history) * 100) if command_history else 0,
            "recent_activity": context.get("last_activity", "未知")
        }
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """清理旧的会话"""
        now = datetime.now()
        sessions_to_remove = []
        
        for session_id, context in self.contexts.items():
            last_activity = datetime.fromisoformat(context.get("last_activity", datetime.now().isoformat()))
            age = now - last_activity
            
            if age.total_seconds() / 3600 > max_age_hours:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.contexts[session_id]
        
        if sessions_to_remove:
            logger.info(f"清理了 {len(sessions_to_remove)} 个旧会话")
            self._save_persisted_contexts()
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话"""
        sessions = []
        
        for session_id, context in self.contexts.items():
            sessions.append({
                "session_id": session_id,
                "created_at": context.get("created_at"),
                "last_activity": context.get("last_activity"),
                "command_count": len(context.get("command_history", [])),
                "statistics": self.get_statistics(session_id)
            })
        
        return sessions
