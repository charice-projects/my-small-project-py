"""
任务分发器 - 将解析后的意图分发给对应的处理函数
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
from core.context_manager import ContextManager
from core.constitution_engine import ConstitutionEngine

# 导入服务
from services.file_service import FileService
from services.search_service import SearchService
from services.archive_service import ArchiveService
from services.monitor_service import MonitorService


class TaskDispatcher:
    """任务分发器"""
    
    def __init__(self):
        self.handlers = {}
        self.context_manager = ContextManager()
        self.constitution_engine = ConstitutionEngine()
        
        # 初始化服务
        self.file_service = FileService(self.constitution_engine)
        self.search_service = SearchService(self.file_service)
        self.archive_service = ArchiveService(self.constitution_engine)
        self.monitor_service = MonitorService()
        
        # 注册所有处理函数
        self._register_handlers()
        
    #zel
    def _register_handlers(self):
        """注册所有处理函数"""
        
        # ========== 索引相关 ==========
        self.register_handler("index", self.handle_index)
        self.register_handler("generate_index", self.handle_index)
        self.register_handler("reindex", self.handle_index)
        self.register_handler("update_index", self.handle_index)
        
        # ========== 文件列表相关 ==========
        self.register_handler("list", self.handle_list)
        self.register_handler("list_files", self.handle_list)
        self.register_handler("ls", self.handle_list)
        # 注意：show 现在应该被正确解析为 system_info 或 list，不单独注册
        
        # ========== 搜索相关 ==========
        self.register_handler("search", self.handle_search)
        self.register_handler("find", self.handle_search)
        self.register_handler("locate", self.handle_search)
        
        # ========== 文件操作相关 ==========
        self.register_handler("read", self.handle_read)
        self.register_handler("open", self.handle_read)
        self.register_handler("view", self.handle_read)
        
        self.register_handler("write", self.handle_write)
        self.register_handler("edit", self.handle_write)
        self.register_handler("create", self.handle_create)
        
        self.register_handler("delete", self.handle_delete)
        self.register_handler("remove", self.handle_delete)
        self.register_handler("rm", self.handle_delete)
        
        self.register_handler("copy", self.handle_copy)
        self.register_handler("cp", self.handle_copy)
        
        self.register_handler("move", self.handle_move)
        self.register_handler("rename", self.handle_move)
        self.register_handler("mv", self.handle_move)
        
        # ========== 打包相关 ==========
        self.register_handler("archive", self.handle_archive)
        self.register_handler("zip", self.handle_archive)
        self.register_handler("compress", self.handle_archive)
        self.register_handler("pack", self.handle_archive)
        
        # ========== 系统相关 ==========
        self.register_handler("system_info", self.handle_system_info)
        self.register_handler("status", self.handle_system_info)  # status 别名
        self.register_handler("health", self.handle_system_info)  # health 别名
        # show 不再单独注册，由意图解析器决定是 list 还是 system_info
        
        self.register_handler("recent", self.handle_recent)
        self.register_handler("history", self.handle_history)
        
        # ========== 目录操作 ==========
        self.register_handler("mkdir", self.handle_mkdir)
        self.register_handler("create_dir", self.handle_mkdir)
        
        self.register_handler("tree", self.handle_tree)
        self.register_handler("directory_tree", self.handle_tree)
        
        logger.info(f"已注册 {len(self.handlers)} 个任务处理器")
    
    
    def register_handler(self, action: str, handler: Callable):
        """注册处理函数"""
        self.handlers[action] = handler
    
    async def dispatch(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """分发任务"""
        try:
            action = intent.get("action", "").lower()
            
            if not action:
                return {
                    "success": False,
                    "message": "未指定操作类型",
                    "action": "unknown"
                }
            
            # 查找处理函数
            handler = self.handlers.get(action)
            
            if not handler:
                # 尝试模糊匹配
                for key in self.handlers.keys():
                    if key in action or action in key:
                        handler = self.handlers[key]
                        break
            
            if not handler:
                return {
                    "success": False,
                    "message": f"不支持的操作类型: {action}",
                    "action": action,
                    "supported_actions": list(self.handlers.keys())
                }
            
            # 执行处理函数
            logger.info(f"分发任务: {action}")
            result = await handler(intent)
            
            # 确保结果包含必要字段
            if "success" not in result:
                result["success"] = True
            
            if "action" not in result:
                result["action"] = action
            
            # 记录执行时间
            if "execution_time" not in result:
                result["execution_time"] = intent.get("execution_time", 0)
            
            return result
        
        except Exception as e:
            logger.error(f"任务分发失败: {e}")
            return {
                "success": False,
                "message": f"任务执行失败: {str(e)}",
                "action": intent.get("action", "unknown"),
                "error": str(e)
            }
    
    # ========== 处理函数实现 ==========
    
    async def handle_index(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理索引操作"""
        from core.file_indexer import FileIndexer
        
        try:
            force = intent.get("parameters", {}).get("force", False)
            incremental = intent.get("parameters", {}).get("incremental", True)
            
            indexer = FileIndexer()
            result = indexer.generate_index(force=force, incremental=incremental)
            
            return {
                "success": True,
                "message": "索引生成完成",
                "data": [result],
                "text_output": f"索引生成完成:\n"
                              f"- 总文件数: {result.get('total_files', 0)}\n"
                              f"- 总目录数: {result.get('total_dirs', 0)}\n"
                              f"- 耗时: {result.get('execution_time', 0):.2f}秒\n"
                              f"- 索引文件: {result.get('index_file', '')}"
            }
        
        except Exception as e:
            logger.error(f"索引生成失败: {e}")
            return {
                "success": False,
                "message": f"索引生成失败: {str(e)}"
            }
    
    async def handle_list(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理列表操作"""
        try:
            target = intent.get("target", settings.root_path)
            recursive = intent.get("parameters", {}).get("recursive", False)
            include_hidden = intent.get("parameters", {}).get("hidden", False)
            
            # 如果没有指定路径，使用最近访问的目录
            if not target or target == "here":
                target = self.context_manager.context.get("current_workspace", settings.root_path)
            
            # 处理特殊路径
            if target in ["recent", "最近"]:
                return await self.handle_recent(intent)
            elif target in ["home", "主目录"]:
                target = settings.root_path
            
            items = self.file_service.list_directory(
                target, 
                recursive=recursive, 
                include_hidden=include_hidden
            )
            
            # 排序
            sort_by = intent.get("parameters", {}).get("sort_by", "name")
            order = intent.get("parameters", {}).get("order", "asc")
            
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
            
            return {
                "success": True,
                "message": f"找到 {len(items)} 个项目",
                "data": items,
                "text_output": f"目录: {target}\n项目数: {len(items)}"
            }
        
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return {
                "success": False,
                "message": f"列出文件失败: {str(e)}"
            }
    
    async def handle_search(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理搜索操作"""
        try:
            # 修复：支持多种参数名
            query = intent.get("target", "") or intent.get("parameters", {}).get("target", "") or intent.get("parameters", {}).get("query", "")
            
            if not query:
                return {
                    "success": False,
                    "message": "请提供搜索关键词",
                    "action": "search"
                }
            
            path = intent.get("parameters", {}).get("path", settings.root_path)
            search_type = intent.get("parameters", {}).get("type", "both")
            recursive = intent.get("parameters", {}).get("recursive", True)
            case_sensitive = intent.get("parameters", {}).get("case_sensitive", False)
            
            results = []
            
            # 按名称搜索
            if search_type in ["name", "both"]:
                name_results = self.search_service.search_by_name(
                    query, path, case_sensitive=case_sensitive
                )
                results.extend(name_results)
            
            # 按内容搜索
            if search_type in ["content", "both"]:
                content_results = self.search_service.search_by_content(
                    query, path, case_sensitive=case_sensitive
                )
                results.extend(content_results)
            
            # 去重
            unique_results = []
            seen_paths = set()
            
            for result in results:
                if result["path"] not in seen_paths:
                    seen_paths.add(result["path"])
                    unique_results.append(result)
            
            # 按相关性排序（简化：匹配度高的在前）
            unique_results.sort(key=lambda x: (
                x.get("name", "").lower().count(query.lower()),
                x.get("content_match_count", 0)
            ), reverse=True)
            
            # 限制数量
            limit = intent.get("parameters", {}).get("limit", 100)
            if len(unique_results) > limit:
                unique_results = unique_results[:limit]
            
            # 更新上下文
            if unique_results:
                search_context = {
                    "last_search": {
                        "query": query,
                        "results_count": len(unique_results),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                self.context_manager.update_context(search_context)
            
            if unique_results:
                return {
                    "success": True,
                    "message": f"搜索 '{query}' 找到 {len(unique_results)} 个结果",
                    "data": unique_results,
                    "text_output": f"搜索: '{query}'\n结果数: {len(unique_results)}"
                }
            else:
                return {
                    "success": True,
                    "message": f"搜索 '{query}' 未找到结果",
                    "data": [],
                    "text_output": f"搜索: '{query}'\n未找到匹配的结果"
                }
        
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {
                "success": False,
                "message": f"搜索失败: {str(e)}"
            }
    
    
    async def handle_read(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理读取操作"""
        try:
            target = intent.get("target", "")
            if not target:
                return {
                    "success": False,
                    "message": "请指定要读取的文件"
                }
            
            # 尝试读取文件内容
            content = self.file_service.read_file(target)
            
            # 记录访问
            self.context_manager.add_file_access(target, "read", True)
            
            # 限制输出长度
            max_preview = 5000
            preview = content[:max_preview]
            truncated = len(content) > max_preview
            
            return {
                "success": True,
                "message": f"文件读取成功: {PathUtils.get_relative_path(target)}",
                "data": [{
                    "path": target,
                    "name": Path(target).name,
                    "size": len(content),
                    "size_human": PathUtils.humanize_size(len(content)),
                    "content": content,
                    "preview": preview,
                    "truncated": truncated
                }],
                "text_output": f"文件: {PathUtils.get_relative_path(target)}\n"
                              f"大小: {PathUtils.humanize_size(len(content))}\n"
                              f"内容预览:\n{'='*40}\n{preview}\n{'='*40}"
                              f"{'... (内容被截断)' if truncated else ''}"
            }
        
        except FileNotFoundError:
            return {
                "success": False,
                "message": f"文件不存在: {target}"
            }
        except PermissionError:
            return {
                "success": False,
                "message": f"无权限读取文件: {target}"
            }
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return {
                "success": False,
                "message": f"读取文件失败: {str(e)}"
            }
    
    async def handle_write(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理写入操作"""
        try:
            target = intent.get("target", "")
            if not target:
                return {
                    "success": False,
                    "message": "请指定要写入的文件"
                }
            
            content = intent.get("parameters", {}).get("content", "")
            if not content:
                return {
                    "success": False,
                    "message": "请提供要写入的内容"
                }
            
            encoding = intent.get("parameters", {}).get("encoding", "utf-8")
            overwrite = intent.get("parameters", {}).get("overwrite", True)
            
            success = self.file_service.write_file(target, content, encoding, overwrite)
            
            if success:
                # 记录访问
                self.context_manager.add_file_access(target, "write", True)
                
                return {
                    "success": True,
                    "message": f"文件写入成功: {PathUtils.get_relative_path(target)}",
                    "data": [{
                        "path": target,
                        "name": PathUtils.get_file_info(target)["name"],
                        "size": len(content),
                        "size_human": PathUtils.humanize_size(len(content))
                    }]
                }
            else:
                return {
                    "success": False,
                    "message": "文件写入失败"
                }
        
        except Exception as e:
            logger.error(f"写入文件失败: {e}")
            return {
                "success": False,
                "message": f"写入文件失败: {str(e)}"
            }
    
    async def handle_create(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理创建操作"""
        try:
            target = intent.get("target", "")
            if not target:
                return {
                    "success": False,
                    "message": "请指定要创建的文件或目录"
                }
            
            type_ = intent.get("parameters", {}).get("type", "file")
            content = intent.get("parameters", {}).get("content", "")
            
            if type_ == "directory":
                success = self.file_service.create_directory(target)
                message = "目录创建成功"
            else:
                success = self.file_service.write_file(target, content, overwrite=False)
                message = "文件创建成功"
            
            if success:
                return {
                    "success": True,
                    "message": f"{message}: {PathUtils.get_relative_path(target)}",
                    "data": [{
                        "path": target,
                        "name": PathUtils.get_file_info(target)["name"],
                        "type": type_
                    }]
                }
            else:
                return {
                    "success": False,
                    "message": f"创建失败: {PathUtils.get_relative_path(target)}"
                }
        
        except Exception as e:
            logger.error(f"创建失败: {e}")
            return {
                "success": False,
                "message": f"创建失败: {str(e)}"
            }
    
    async def handle_delete(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理删除操作"""
        try:
            target = intent.get("target", "")
            if not target:
                return {
                    "success": False,
                    "message": "请指定要删除的文件或目录"
                }
            
            # 安全检查
            target_path = PathUtils.normalize_path(target)
            root_path = PathUtils.normalize_path(settings.root_path)
            
            if target_path == root_path:
                return {
                    "success": False,
                    "message": "不能删除工作空间根目录"
                }
            
            success = self.file_service.delete_file(target)
            
            if success:
                return {
                    "success": True,
                    "message": f"删除成功: {PathUtils.get_relative_path(target)}"
                }
            else:
                return {
                    "success": False,
                    "message": f"删除失败: {PathUtils.get_relative_path(target)}"
                }
        
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }
    
    async def handle_copy(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理复制操作"""
        try:
            source = intent.get("target", "")
            destination = intent.get("parameters", {}).get("destination", "")
            
            if not source or not destination:
                return {
                    "success": False,
                    "message": "请指定源路径和目标路径"
                }
            
            overwrite = intent.get("parameters", {}).get("overwrite", False)
            
            success = self.file_service.copy_file(source, destination, overwrite)
            
            if success:
                return {
                    "success": True,
                    "message": f"复制成功: {PathUtils.get_relative_path(source)} -> {PathUtils.get_relative_path(destination)}"
                }
            else:
                return {
                    "success": False,
                    "message": "复制失败"
                }
        
        except Exception as e:
            logger.error(f"复制失败: {e}")
            return {
                "success": False,
                "message": f"复制失败: {str(e)}"
            }
    
    async def handle_move(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理移动操作"""
        try:
            source = intent.get("target", "")
            destination = intent.get("parameters", {}).get("destination", "")
            
            if not source or not destination:
                return {
                    "success": False,
                    "message": "请指定源路径和目标路径"
                }
            
            overwrite = intent.get("parameters", {}).get("overwrite", False)
            
            success = self.file_service.move_file(source, destination, overwrite)
            
            if success:
                return {
                    "success": True,
                    "message": f"移动成功: {PathUtils.get_relative_path(source)} -> {PathUtils.get_relative_path(destination)}"
                }
            else:
                return {
                    "success": False,
                    "message": "移动失败"
                }
        
        except Exception as e:
            logger.error(f"移动失败: {e}")
            return {
                "success": False,
                "message": f"移动失败: {str(e)}"
            }
    
    async def handle_archive(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理打包操作"""
        try:
            target = intent.get("target", "")
            
            # 如果没有指定目标，使用默认名称
            if not target:
                target = f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            files = intent.get("parameters", {}).get("files", [])
            output_path = intent.get("parameters", {}).get("output", "")
            format_ = intent.get("parameters", {}).get("format", "zip")
            
            # 如果指定了文件列表，使用这些文件
            if files:
                result = self.archive_service.create_archive_from_list(
                    files, output_path or target, format_
                )
            else:
                # 否则对指定目录打包
                result = self.archive_service.create_archive(target, output_path, format_)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"打包成功: {result['archive_path']}",
                    "data": [{
                        "path": result["archive_path"],
                        "name": Path(result["archive_path"]).name,
                        "size": result.get("size", 0),
                        "size_human": PathUtils.humanize_size(result.get("size", 0)),
                        "file_count": result.get("file_count", 0)
                    }]
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", "打包失败")
                }
        
        except Exception as e:
            logger.error(f"打包失败: {e}")
            return {
                "success": False,
                "message": f"打包失败: {str(e)}"
            }
    
    async def handle_system_info(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理系统信息操作"""
        try:
            import platform
            import psutil
            
            # 系统信息
            sys_info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
                "processor": platform.processor()
            }
            
            # 资源信息
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            try:
                disk = psutil.disk_usage(settings.root_path)
            except Exception:
                disk = psutil.disk_usage("/")
            
            # 服务信息
            service_info = {
                "host": settings.host,
                "port": settings.port,
                "root_path": settings.root_path,
                "safe_mode": settings.safe_mode,
                "constitution_enabled": settings.constitution_enabled,
                "session_id": self.context_manager.context.get("session_id"),
                "total_commands": len(self.context_manager.context.get("command_history", [])),
                "session_duration": self.context_manager.get_statistics().get("session_duration", "未知")
            }
            
            # 索引信息
            try:
                from core.file_indexer import FileIndexer
                indexer = FileIndexer()
                index_status = indexer.get_index_status()
            except Exception:
                index_status = {"has_index": False}
            
            return {
                "success": True,
                "message": "系统信息获取成功",
                "data": [{
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
                    "service": service_info,
                    "index": index_status
                }],
                "text_output": f"系统状态:\n"
                              f"- CPU使用率: {cpu_percent}%\n"
                              f"- 内存使用率: {memory.percent}%\n"
                              f"- 磁盘使用率: {disk.percent}%\n"
                              f"- 会话ID: {service_info['session_id']}\n"
                              f"- 总命令数: {service_info['total_commands']}"
            }
        
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {
                "success": False,
                "message": f"获取系统信息失败: {str(e)}"
            }
    
    async def handle_recent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理最近文件操作"""
        try:
            limit = intent.get("parameters", {}).get("limit", 20)
            recent_files = self.context_manager.get_recent_files(limit=limit)
            
            return {
                "success": True,
                "message": f"最近访问的 {len(recent_files)} 个文件",
                "data": recent_files
            }
        
        except Exception as e:
            logger.error(f"获取最近文件失败: {e}")
            return {
                "success": False,
                "message": f"获取最近文件失败: {str(e)}"
            }
    
    async def handle_history(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理历史记录操作"""
        try:
            limit = intent.get("parameters", {}).get("limit", 50)
            action_filter = intent.get("parameters", {}).get("action")
            
            history = self.context_manager.get_command_history(
                limit=limit, 
                filter_action=action_filter
            )
            
            return {
                "success": True,
                "message": f"命令历史记录 ({len(history)} 条)",
                "data": history
            }
        
        except Exception as e:
            logger.error(f"获取历史记录失败: {e}")
            return {
                "success": False,
                "message": f"获取历史记录失败: {str(e)}"
            }
    
    async def handle_mkdir(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理创建目录操作"""
        try:
            target = intent.get("target", "")
            if not target:
                return {
                    "success": False,
                    "message": "请指定要创建的目录路径"
                }
            
            success = self.file_service.create_directory(target)
            
            if success:
                return {
                    "success": True,
                    "message": f"目录创建成功: {PathUtils.get_relative_path(target)}"
                }
            else:
                return {
                    "success": False,
                    "message": "目录创建失败"
                }
        
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return {
                "success": False,
                "message": f"创建目录失败: {str(e)}"
            }
    
    async def handle_tree(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """处理目录树操作"""
        try:
            target = intent.get("target", settings.root_path)
            max_depth = intent.get("parameters", {}).get("max_depth", 3)
            
            tree = PathUtils.get_directory_tree(target, max_depth=max_depth)
            
            return {
                "success": True,
                "message": f"目录树: {PathUtils.get_relative_path(target)}",
                "data": [tree]
            }
        
        except Exception as e:
            logger.error(f"获取目录树失败: {e}")
            return {
                "success": False,
                "message": f"获取目录树失败: {str(e)}"
            }


# 全局实例
task_dispatcher = TaskDispatcher()

async def get_task_dispatcher() -> TaskDispatcher:
    """获取任务分发器实例"""
    return task_dispatcher