"""
文件监控服务 - 监控文件系统变化
"""
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils


class FileChangeHandler(FileSystemEventHandler):
    """文件变化处理器"""
    
    def __init__(self, callback: Callable[[Dict[str, Any]], None]):
        super().__init__()
        self.callback = callback
        self.last_event_time = {}
    
    def on_any_event(self, event: FileSystemEvent):
        """处理任何文件系统事件"""
        try:
            # 防抖动：避免短时间内重复事件
            event_key = f"{event.src_path}-{event.event_type}"
            current_time = time.time()
            
            if event_key in self.last_event_time:
                if current_time - self.last_event_time[event_key] < 0.1:  # 100ms防抖
                    return
            
            self.last_event_time[event_key] = current_time
            
            # 构建事件数据
            event_data = {
                "event_type": event.event_type,
                "src_path": event.src_path,
                "is_directory": event.is_directory,
                "timestamp": datetime.now().isoformat(),
                "human_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 如果是移动事件，添加目标路径
            if hasattr(event, 'dest_path'):
                event_data["dest_path"] = event.dest_path
            
            # 调用回调函数
            self.callback(event_data)
            
            logger.debug(f"文件事件: {event.event_type} - {event.src_path}")
        
        except Exception as e:
            logger.error(f"处理文件事件失败: {e}")
    
    def on_created(self, event: FileSystemEvent):
        """文件/目录创建"""
        if not event.is_directory:
            logger.info(f"文件创建: {event.src_path}")
    
    def on_deleted(self, event: FileSystemEvent):
        """文件/目录删除"""
        if not event.is_directory:
            logger.info(f"文件删除: {event.src_path}")
    
    def on_modified(self, event: FileSystemEvent):
        """文件/目录修改"""
        if not event.is_directory:
            logger.info(f"文件修改: {event.src_path}")
    
    def on_moved(self, event: FileSystemEvent):
        """文件/目录移动"""
        logger.info(f"文件移动: {event.src_path} -> {event.dest_path}")


class MonitorService:
    """文件监控服务"""
    
    def __init__(self):
        self.observer = None
        self.handlers = []
        self.is_running = False
        self.watch_paths = []
        self.event_callbacks = []
        self.event_history = []
        self.max_history = 1000
        
        # 启动监控线程
        self._start_monitor()
    
    def _start_monitor(self):
        """启动监控"""
        if self.is_running:
            return
        
        try:
            self.observer = Observer()
            
            # 添加默认监控路径（工作空间根目录）
            root_path = Path(settings.root_path)
            if root_path.exists():
                self.add_watch_path(root_path, recursive=True)
            
            self.observer.start()
            self.is_running = True
            
            logger.info("文件监控服务已启动")
        
        except Exception as e:
            logger.error(f"启动文件监控失败: {e}")
    
    def add_watch_path(self, path: Path, recursive: bool = True):
        """添加监控路径"""
        try:
            if not path.exists():
                logger.warning(f"监控路径不存在: {path}")
                return
            
            # 创建事件处理器
            handler = FileChangeHandler(self._handle_event)
            self.handlers.append(handler)
            
            # 安排监控
            self.observer.schedule(handler, str(path), recursive=recursive)
            self.watch_paths.append(str(path))
            
            logger.info(f"已添加监控路径: {path} (递归: {recursive})")
        
        except Exception as e:
            logger.error(f"添加监控路径失败: {path} - {e}")
    
    def remove_watch_path(self, path: Path):
        """移除监控路径"""
        path_str = str(path)
        
        for handler in self.handlers[:]:
            # 这里简化处理，实际需要更精确的匹配
            if path_str in self.watch_paths:
                try:
                    self.observer.unschedule(handler)
                    self.handlers.remove(handler)
                    self.watch_paths.remove(path_str)
                    
                    logger.info(f"已移除监控路径: {path}")
                
                except Exception as e:
                    logger.error(f"移除监控路径失败: {path} - {e}")
    
    def add_event_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """添加事件回调"""
        self.event_callbacks.append(callback)
        logger.info(f"已添加事件回调，当前总数: {len(self.event_callbacks)}")
    
    def remove_event_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """移除事件回调"""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
            logger.info(f"已移除事件回调，剩余: {len(self.event_callbacks)}")
    
    def _handle_event(self, event_data: Dict[str, Any]):
        """处理事件"""
        try:
            # 添加到历史记录
            self.event_history.append(event_data)
            
            # 限制历史记录大小
            if len(self.event_history) > self.max_history:
                self.event_history = self.event_history[-self.max_history:]
            
            # 调用所有回调
            for callback in self.event_callbacks:
                try:
                    callback(event_data)
                except Exception as e:
                    logger.error(f"事件回调执行失败: {e}")
        
        except Exception as e:
            logger.error(f"处理事件数据失败: {e}")
    
    def get_recent_events(self, 
                         limit: int = 50, 
                         event_type: Optional[str] = None,
                         path_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取最近事件"""
        events = self.event_history
        
        # 过滤事件类型
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        
        # 过滤路径
        if path_filter:
            events = [e for e in events if path_filter in e.get("src_path", "")]
        
        # 按时间倒序排序并限制数量
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return events[:limit]
    
    def get_event_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取事件统计"""
        try:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            
            recent_events = []
            for event in self.event_history:
                try:
                    event_time = datetime.fromisoformat(event["timestamp"]).timestamp()
                    if event_time > cutoff_time:
                        recent_events.append(event)
                except Exception:
                    continue
            
            # 统计事件类型
            type_counts = {}
            for event in recent_events:
                event_type = event.get("event_type", "unknown")
                type_counts[event_type] = type_counts.get(event_type, 0) + 1
            
            # 统计最活跃路径
            path_counts = {}
            for event in recent_events:
                path = event.get("src_path", "")
                if path:
                    path_counts[path] = path_counts.get(path, 0) + 1
            
            top_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "total_events": len(recent_events),
                "time_period_hours": hours,
                "event_type_counts": type_counts,
                "most_active_paths": [{"path": p, "count": c} for p, c in top_paths],
                "directory_events": sum(1 for e in recent_events if e.get("is_directory", False)),
                "file_events": sum(1 for e in recent_events if not e.get("is_directory", False)),
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"获取事件统计失败: {e}")
            return {}
    
    def stop(self):
        """停止监控"""
        if self.is_running and self.observer:
            try:
                self.observer.stop()
                self.observer.join()
                self.is_running = False
                
                logger.info("文件监控服务已停止")
            
            except Exception as e:
                logger.error(f"停止文件监控失败: {e}")
    
    def restart(self):
        """重启监控"""
        self.stop()
        time.sleep(1)
        self._start_monitor()
        logger.info("文件监控服务已重启")
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "is_running": self.is_running,
            "watch_paths": self.watch_paths,
            "total_handlers": len(self.handlers),
            "total_callbacks": len(self.event_callbacks),
            "event_history_size": len(self.event_history),
            "observer_alive": self.observer and self.observer.is_alive(),
            "timestamp": datetime.now().isoformat()
        }