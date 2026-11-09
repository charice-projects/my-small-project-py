# services/file_service_v2.py
"""
文件服务 V2 - 高性能文件操作服务
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Set
from datetime import datetime
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
from core.constitution_engine import ConstitutionEngine


class FileCache:
    """文件缓存管理器"""
    
    def __init__(self, max_size: int = 10000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl  # 缓存存活时间（秒）
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._cleanup_task = None
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                # 检查是否过期
                if datetime.now().timestamp() - entry['timestamp'] < self.ttl:
                    return entry['data']
                else:
                    del self._cache[key]
            return None
    
    def set(self, key: str, data: Any):
        """设置缓存"""
        with self._lock:
            # 清理过期缓存
            self._clean_expired()
            
            # 如果超过最大大小，清理最旧的
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[key] = {
                'data': data,
                'timestamp': datetime.now().timestamp()
            }
    
    def invalidate(self, key: str = None):
        """使缓存失效"""
        with self._lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
            else:
                self._cache.clear()
    
    def _clean_expired(self):
        """清理过期缓存"""
        now = datetime.now().timestamp()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if now - entry['timestamp'] > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
    
    def _evict_oldest(self, count: int = 100):
        """淘汰最旧的缓存"""
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1]['timestamp']
        )
        
        for key, _ in sorted_items[:count]:
            del self._cache[key]


class AsyncFileService:
    """异步文件服务"""
    
    def __init__(self, constitution_engine: Optional[ConstitutionEngine] = None):
        self.constitution_engine = constitution_engine or ConstitutionEngine()
        self.root_path = Path(settings.root_path)
        self.cache = FileCache()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 初始化索引
        self._index = {}
        self._index_lock = threading.RLock()
        
        logger.info("异步文件服务初始化完成")
    
    async def list_directory(self, 
                           dir_path: Union[str, Path],
                           recursive: bool = False,
                           include_hidden: bool = False,
                           use_cache: bool = True) -> List[Dict[str, Any]]:
        """异步列出目录"""
        path = PathUtils.normalize_path(dir_path)
        
        # 生成缓存键
        cache_key = f"list:{path}:{recursive}:{include_hidden}"
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        # 在线程池中执行IO操作
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(
            self.executor,
            self._list_directory_sync,
            path, recursive, include_hidden
        )
        
        # 缓存结果
        if use_cache:
            self.cache.set(cache_key, items)
        
        return items
    
    def _list_directory_sync(self, 
                           path: Path,
                           recursive: bool,
                           include_hidden: bool) -> List[Dict[str, Any]]:
        """同步列出目录（在线程池中执行）"""
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {path}")
        
        if not path.is_dir():
            raise NotADirectoryError(f"不是目录: {path}")
        
        try:
            items = []
            
            if recursive:
                # 递归列出
                for item_path in path.rglob('*'):
                    if not include_hidden and item_path.name.startswith('.'):
                        continue
                    
                    if item_path.is_relative_to(path):
                        items.append(PathUtils.get_file_info(item_path))
            else:
                # 非递归列出
                for item_path in path.iterdir():
                    if not include_hidden and item_path.name.startswith('.'):
                        continue
                    
                    items.append(PathUtils.get_file_info(item_path))
            
            # 排序：目录在前，按名称排序
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            return items
            
        except Exception as e:
            logger.error(f"列出目录失败: {path} - {e}")
            return []
    
    async def search_files(self,
                          search_term: str,
                          search_path: Optional[Union[str, Path]] = None,
                          search_type: str = 'name',
                          case_sensitive: bool = False,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """异步搜索文件"""
        if search_path is None:
            search_path = self.root_path
        
        path = PathUtils.normalize_path(search_path)
        
        if not path.exists():
            raise FileNotFoundError(f"搜索路径不存在: {path}")
        
        # 生成缓存键
        cache_key = f"search:{path}:{search_term}:{search_type}:{case_sensitive}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached[:limit]  # 返回限制数量的缓存结果
        
        # 使用线程池执行搜索
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            self._search_files_sync,
            search_term, path, search_type, case_sensitive
        )
        
        # 缓存结果
        self.cache.set(cache_key, results)
        
        # 返回限制数量的结果
        return results[:limit]
    
    def _search_files_sync(self,
                          search_term: str,
                          path: Path,
                          search_type: str,
                          case_sensitive: bool) -> List[Dict[str, Any]]:
        """同步搜索文件（在线程池中执行）"""
        matches = []
        search_term_adj = search_term if case_sensitive else search_term.lower()
        
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    file_name = file_path.name
                    
                    if not case_sensitive:
                        file_name = file_name.lower()
                    
                    if search_type == 'name' and search_term_adj in file_name:
                        matches.append(PathUtils.get_file_info(file_path))
                    elif search_type == 'extension' and file_path.suffix.lower() == f'.{search_term_adj}':
                        matches.append(PathUtils.get_file_info(file_path))
                    elif search_type == 'path' and search_term_adj in str(file_path).lower():
                        matches.append(PathUtils.get_file_info(file_path))
                    
                    # 限制内存使用
                    if len(matches) > 1000:
                        break
            
            return matches
            
        except Exception as e:
            logger.error(f"搜索文件失败: {path} - {e}")
            return []
    
    async def get_file_statistics(self, 
                                dir_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """异步获取文件统计信息"""
        if dir_path is None:
            dir_path = self.root_path
        
        path = PathUtils.normalize_path(dir_path)
        
        if not path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")
        
        # 生成缓存键
        cache_key = f"stats:{path}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # 使用线程池执行统计
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            self.executor,
            self._get_file_statistics_sync,
            path
        )
        
        # 缓存结果（统计信息缓存时间较短）
        self.cache.set(cache_key, stats)
        
        return stats
    
    def _get_file_statistics_sync(self, path: Path) -> Dict[str, Any]:
        """同步获取文件统计信息"""
        file_count = 0
        dir_count = 0
        total_size = 0
        extensions = {}
        
        try:
            for item_path in path.rglob('*'):
                if item_path.is_file():
                    file_count += 1
                    total_size += item_path.stat().st_size
                    
                    # 统计扩展名
                    ext = item_path.suffix.lower()
                    if ext:
                        extensions[ext] = extensions.get(ext, 0) + 1
                elif item_path.is_dir():
                    dir_count += 1
            
            # 按数量排序扩展名
            sorted_extensions = sorted(extensions.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "path": str(path),
                "total_files": file_count,
                "total_directories": dir_count,
                "total_size": total_size,
                "total_size_human": PathUtils.humanize_size(total_size),
                "file_extensions": dict(sorted_extensions[:10]),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取文件统计失败: {path} - {e}")
            return {}
    
    async def build_index(self, force: bool = False) -> Dict[str, Any]:
        """异步构建文件索引"""
        # 生成索引键
        cache_key = f"index:{self.root_path}"
        
        if not force:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        # 使用线程池构建索引
        loop = asyncio.get_event_loop()
        index = await loop.run_in_executor(
            self.executor,
            self._build_index_sync
        )
        
        # 更新内存索引
        with self._index_lock:
            self._index = index
        
        # 缓存索引
        self.cache.set(cache_key, index)
        
        return index
    
    def _build_index_sync(self) -> Dict[str, Any]:
        """同步构建文件索引"""
        index = {
            "files": {},
            "directories": {},
            "extensions": {},
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            start_time = datetime.now()
            
            for item_path in self.root_path.rglob('*'):
                if item_path.is_file():
                    file_info = PathUtils.get_file_info(item_path)
                    rel_path = str(item_path.relative_to(self.root_path))
                    
                    index["files"][rel_path] = file_info
                    
                    # 统计扩展名
                    ext = item_path.suffix.lower()
                    if ext:
                        index["extensions"][ext] = index["extensions"].get(ext, 0) + 1
                
                elif item_path.is_dir():
                    dir_info = PathUtils.get_file_info(item_path)
                    rel_path = str(item_path.relative_to(self.root_path))
                    index["directories"][rel_path] = dir_info
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            index["total_files"] = len(index["files"])
            index["total_directories"] = len(index["directories"])
            index["execution_time"] = execution_time
            
            logger.info(f"索引构建完成: {index['total_files']} 个文件, "
                       f"{index['total_directories']} 个目录, "
                       f"耗时 {execution_time:.2f} 秒")
            
            return index
            
        except Exception as e:
            logger.error(f"构建索引失败: {e}")
            return {"error": str(e)}
    
    async def fast_search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """快速搜索（使用索引）"""
        # 确保索引已构建
        if not self._index:
            await self.build_index()
        
        results = []
        query_lower = query.lower()
        
        with self._index_lock:
            # 在索引中搜索
            for rel_path, file_info in self._index.get("files", {}).items():
                if query_lower in file_info.get("name", "").lower():
                    results.append(file_info)
                
                if len(results) >= limit:
                    break
        
        return results
    
    async def cleanup(self):
        """清理资源"""
        self.executor.shutdown(wait=True)
        self.cache.invalidate()


# 全局实例
async_file_service = AsyncFileService()


async def get_file_service() -> AsyncFileService:
    """获取文件服务实例"""
    return async_file_service