# core/task_dispatcher_v2.py 完整版
"""
任务分发器 V2 - 基于插件化的任务分发系统
完整重构版
"""
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
from pathlib import Path
import logging

from utils.logger import logger
from utils.path_utils import PathUtils
from services.file_service_v2 import AsyncFileService
from services.search_service_v2 import SearchServiceV2
from core.context_manager import ContextManager


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    action: str
    data: Any = None
    message: str = ""
    error_code: str = ""
    suggestions: List[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "success": self.success,
            "action": self.action,
            "data": self.data,
            "message": self.message,
            "error_code": self.error_code,
            "execution_time": self.execution_time,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.suggestions:
            result["suggestions"] = self.suggestions
            
        return result


class TaskHandler(ABC):
    """任务处理器基类"""
    
    def __init__(self, action_name: str, aliases: List[str] = None):
        self.action_name = action_name
        self.aliases = aliases or []
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    async def execute(self, intent: Dict[str, Any], 
                     context: Dict[str, Any]) -> TaskResult:
        """执行任务"""
        pass
    
    def can_handle(self, action: str) -> bool:
        """检查是否能处理该动作"""
        return action == self.action_name or action in self.aliases


class SearchTaskHandler(TaskHandler):
    """搜索任务处理器"""
    
    def __init__(self, search_service: SearchServiceV2, context_manager: ContextManager):
        super().__init__("search", ["find", "locate", "查询", "查找"])
        self.search_service = search_service
        self.context_manager = context_manager
    
    async def execute(self, intent: Dict[str, Any], 
                     context: Dict[str, Any]) -> TaskResult:
        """执行搜索任务"""
        start_time = datetime.now()
        
        try:
            # 验证参数
            query = intent.get("parameters", {}).get("query")
            if not query:
                return TaskResult(
                    success=False,
                    action=self.action_name,
                    message="请提供搜索关键词",
                    error_code="SEARCH_NO_QUERY",
                    suggestions=["请输入要搜索的内容", "例如: search test"]
                )
            
            # 获取其他参数
            search_path = intent.get("parameters", {}).get("path", ".")
            search_type = intent.get("parameters", {}).get("type", "name")
            limit = intent.get("parameters", {}).get("limit", 100)
            
            # 执行搜索
            results = []
            if search_type == "name":
                results = await self.search_service.search_by_name(
                    query, search_path, limit
                )
            elif search_type == "content":
                results = await self.search_service.search_by_content(
                    query, search_path, limit
                )
            elif search_type == "index":
                results = await self.search_service.search_by_index(query, limit)
            else:
                results = await self.search_service.search_by_name(query, search_path, limit)
            
            # 记录搜索历史
            search_history = {
                "query": query,
                "results_count": len(results),
                "timestamp": datetime.now().isoformat()
            }
            self.context_manager.update_context(
                {"last_search": search_history}
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if results:
                return TaskResult(
                    success=True,
                    action=self.action_name,
                    data=results,
                    message=f"搜索 '{query}' 找到 {len(results)} 个结果",
                    execution_time=execution_time,
                    suggestions=[
                        "试试按内容搜索: search type:content [关键词]",
                        "试试使用索引搜索: search type:index [关键词]"
                    ]
                )
            else:
                return TaskResult(
                    success=True,
                    action=self.action_name,
                    data=[],
                    message=f"搜索 '{query}' 未找到结果",
                    execution_time=execution_time,
                    suggestions=[
                        "尝试不同的关键词",
                        "扩大搜索范围",
                        "检查搜索路径是否正确"
                    ]
                )
            
        except Exception as e:
            self.logger.error(f"搜索任务执行失败: {e}", exc_info=True)
            return TaskResult(
                success=False,
                action=self.action_name,
                message=f"搜索失败: {str(e)}",
                error_code="SEARCH_EXECUTION_ERROR",
                suggestions=["请检查网络连接", "确认搜索服务正常运行"]
            )


class ListTaskHandler(TaskHandler):
    """列表任务处理器"""
    
    def __init__(self, file_service: AsyncFileService, context_manager: ContextManager):
        super().__init__("list", ["ls", "dir", "显示", "列出", "show"])
        self.file_service = file_service
        self.context_manager = context_manager
    
    async def execute(self, intent: Dict[str, Any], 
                     context: Dict[str, Any]) -> TaskResult:
        """执行列表任务"""
        start_time = datetime.now()
        
        try:
            # 获取路径参数
            path = intent.get("parameters", {}).get("path", ".")
            recursive = intent.get("parameters", {}).get("recursive", False)
            include_hidden = intent.get("parameters", {}).get("hidden", False)
            
            # 获取排序参数
            sort_by = intent.get("parameters", {}).get("sort_by", "name")
            order = intent.get("parameters", {}).get("order", "asc")
            
            # 执行列表操作
            items = await self.file_service.list_directory(
                path, 
                recursive=recursive,
                include_hidden=include_hidden
            )
            
            # 排序
            reverse = order.lower() == "desc"
            if sort_by == "size":
                items.sort(key=lambda x: x.get("size", 0), reverse=reverse)
            elif sort_by == "modified":
                items.sort(key=lambda x: x.get("modified", 0), reverse=reverse)
            elif sort_by == "type":
                items.sort(key=lambda x: (x.get("is_dir", False), x.get("name", "")), 
                          reverse=reverse)
            else:  # name
                items.sort(key=lambda x: x.get("name", "").lower(), reverse=reverse)
            
            # 过滤
            filter_type = intent.get("parameters", {}).get("filter")
            if filter_type:
                if filter_type == "file":
                    items = [i for i in items if i.get("is_file", False)]
                elif filter_type == "dir":
                    items = [i for i in items if i.get("is_dir", False)]
                elif filter_type == "image":
                    items = [i for i in items if i.get("name", "").lower().endswith(
                        ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'))]
                elif filter_type == "document":
                    items = [i for i in items if i.get("name", "").lower().endswith(
                        ('.pdf', '.doc', '.docx', '.txt', '.md', '.rtf'))]
                elif filter_type == "code":
                    items = [i for i in items if i.get("name", "").lower().endswith(
                        ('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.html', '.css', '.json'))]
            
            # 限制数量
            limit = intent.get("parameters", {}).get("limit", 1000)
            if len(items) > limit:
                items = items[:limit]
            
            # 更新当前工作目录
            if path != ".":
                self.context_manager.update_context(
                    {"current_workspace": str(Path(path).absolute())}
                )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                success=True,
                action=self.action_name,
                data=items,
                message=f"列出 {path} 中的 {len(items)} 个项目",
                execution_time=execution_time
            )
            
        except FileNotFoundError:
            return TaskResult(
                success=False,
                action=self.action_name,
                message=f"路径不存在: {path}",
                error_code="PATH_NOT_FOUND",
                suggestions=["请检查路径是否正确", "使用绝对路径或相对路径"]
            )
        except PermissionError:
            return TaskResult(
                success=False,
                action=self.action_name,
                message=f"无权限访问路径: {path}",
                error_code="PERMISSION_DENIED",
                suggestions=["检查文件权限", "以管理员身份运行"]
            )
        except Exception as e:
            self.logger.error(f"列表任务执行失败: {e}", exc_info=True)
            return TaskResult(
                success=False,
                action=self.action_name,
                message=f"列出文件失败: {str(e)}",
                error_code="LIST_EXECUTION_ERROR"
            )


class SystemInfoHandler(TaskHandler):
    """系统信息任务处理器"""
    
    def __init__(self):
        super().__init__("system_info", ["status", "health", "系统状态"])
    
    async def execute(self, intent: Dict[str, Any], 
                     context: Dict[str, Any]) -> TaskResult:
        """执行系统信息任务"""
        start_time = datetime.now()
        
        try:
            import platform
            import psutil
            from config.settings import settings
            
            # 系统信息
            sys_info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
                "processor": platform.processor(),
                "architecture": platform.architecture()[0]
            }
            
            # 资源信息
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(settings.root_path)
            
            # 进程信息
            process = psutil.Process()
            process_info = {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent()
            }
            
            # 服务信息
            service_info = {
                "root_path": settings.root_path,
                "safe_mode": settings.safe_mode,
                "constitution_enabled": settings.constitution_enabled,
                "debug_mode": settings.debug
            }
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                success=True,
                action=self.action_name,
                data=[{
                    "system": sys_info,
                    "resources": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "memory_total": memory.total,
                        "memory_used": memory.used,
                        "disk_usage": {
                            "total": disk.total,
                            "used": disk.used,
                            "free": disk.free,
                            "percent": disk.percent
                        }
                    },
                    "process": process_info,
                    "service": service_info
                }],
                message="系统信息获取成功",
                execution_time=execution_time,
                suggestions=["使用 'show status' 查看实时状态", "使用 'health' 检查服务健康"]
            )
            
        except Exception as e:
            self.logger.error(f"系统信息任务执行失败: {e}", exc_info=True)
            return TaskResult(
                success=False,
                action=self.action_name,
                message=f"获取系统信息失败: {str(e)}",
                error_code="SYSTEM_INFO_ERROR"
            )


class IndexTaskHandler(TaskHandler):
    """索引任务处理器"""
    
    def __init__(self, file_service: AsyncFileService):
        super().__init__("index", ["生成索引", "更新索引", "重建索引"])
        self.file_service = file_service
    
    async def execute(self, intent: Dict[str, Any], 
                     context: Dict[str, Any]) -> TaskResult:
        """执行索引任务"""
        start_time = datetime.now()
        
        try:
            force = intent.get("parameters", {}).get("force", False)
            
            # 执行索引构建
            index_result = await self.file_service.build_index(force=force)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if "error" in index_result:
                return TaskResult(
                    success=False,
                    action=self.action_name,
                    message=f"索引构建失败: {index_result['error']}",
                    error_code="INDEX_BUILD_ERROR",
                    execution_time=execution_time
                )
            
            return TaskResult(
                success=True,
                action=self.action_name,
                data=[index_result],
                message=f"索引构建完成: {index_result.get('total_files', 0)} 个文件",
                execution_time=execution_time,
                suggestions=["使用 'search type:index [关键词]' 进行快速搜索"]
            )
            
        except Exception as e:
            self.logger.error(f"索引任务执行失败: {e}", exc_info=True)
            return TaskResult(
                success=False,
                action=self.action_name,
                message=f"索引构建失败: {str(e)}",
                error_code="INDEX_EXECUTION_ERROR"
            )


class TaskDispatcherV2:
    """第二代任务分发器 - 完整版"""
    
    def __init__(self):
        self.handlers: Dict[str, TaskHandler] = {}
        self.context_manager = ContextManager()
        
        # 初始化服务
        self.file_service = AsyncFileService()
        self.search_service = SearchServiceV2(self.file_service)
        
        # 注册处理器
        self._register_handlers()
        
        logger.info(f"任务分发器V2初始化完成，已注册 {len(self.handlers)} 个处理器")
    
    def _register_handlers(self):
        """注册所有任务处理器"""
        # 系统信息处理器
        system_handler = SystemInfoHandler()
        self.register_handler(system_handler)
        
        # 列表处理器
        list_handler = ListTaskHandler(self.file_service, self.context_manager)
        self.register_handler(list_handler)
        
        # 搜索处理器
        search_handler = SearchTaskHandler(self.search_service, self.context_manager)
        self.register_handler(search_handler)
        
        # 索引处理器
        index_handler = IndexTaskHandler(self.file_service)
        self.register_handler(index_handler)
        
        # 其他处理器可以在这里添加...
    
    def register_handler(self, handler: TaskHandler):
        """注册任务处理器"""
        # 注册主动作名
        self.handlers[handler.action_name] = handler
        
        # 注册别名
        for alias in handler.aliases:
            self.handlers[alias] = handler
    
    async def dispatch(self, intent: Dict[str, Any]) -> TaskResult:
        """分发任务"""
        try:
            action = intent.get("action", "").lower()
            
            if not action:
                return TaskResult(
                    success=False,
                    action="unknown",
                    message="未指定操作类型",
                    error_code="NO_ACTION_SPECIFIED",
                    suggestions=["请提供要执行的操作"]
                )
            
            # 查找处理器
            handler = self.handlers.get(action)
            
            if not handler:
                # 尝试模糊匹配
                for key, h in self.handlers.items():
                    if h.can_handle(action):
                        handler = h
                        break
            
            if not handler:
                return TaskResult(
                    success=False,
                    action=action,
                    message=f"不支持的操作类型: {action}",
                    error_code="UNSUPPORTED_ACTION",
                    suggestions=[f"支持的操作: {', '.join(list(self.handlers.keys())[:5])}..."]
                )
            
            # 获取上下文
            context = self.context_manager.get_context()
            
            # 执行任务
            result = await handler.execute(intent, context)
            
            # 记录执行历史
            if result.success:
                self._record_success(intent, result)
            else:
                self._record_failure(intent, result)
            
            return result
            
        except Exception as e:
            logger.error(f"任务分发失败: {e}", exc_info=True)
            return TaskResult(
                success=False,
                action=intent.get("action", "unknown"),
                message=f"任务分发失败: {str(e)}",
                error_code="DISPATCHER_ERROR"
            )
    
    def _record_success(self, intent: Dict[str, Any], result: TaskResult):
        """记录成功执行"""
        execution_record = {
            "action": result.action,
            "success": True,
            "execution_time": result.execution_time,
            "timestamp": datetime.now().isoformat(),
            "parameters": intent.get("parameters", {}),
            "message": result.message
        }
        self.context_manager.add_command_history(execution_record)
    
    def _record_failure(self, intent: Dict[str, Any], result: TaskResult):
        """记录失败执行"""
        failure_record = {
            "action": result.action,
            "success": False,
            "error": result.message,
            "error_code": result.error_code,
            "timestamp": datetime.now().isoformat(),
            "parameters": intent.get("parameters", {})
        }
        self.context_manager.add_command_history(failure_record)
    
    def get_available_actions(self) -> List[str]:
        """获取所有可用操作"""
        return list(self.handlers.keys())
    
    async def cleanup(self):
        """清理资源"""
        if hasattr(self.file_service, 'cleanup'):
            await self.file_service.cleanup()
        
        logger.info("任务分发器清理完成")


# 全局实例
task_dispatcher_v2 = TaskDispatcherV2()


async def get_task_dispatcher_v2() -> TaskDispatcherV2:
    """获取任务分发器V2实例"""
    return task_dispatcher_v2