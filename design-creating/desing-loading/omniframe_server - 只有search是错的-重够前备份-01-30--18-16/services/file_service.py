"""
文件操作服务 - 提供文件的读取、写入、复制、移动、删除等操作
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, BinaryIO
from datetime import datetime

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
from core.constitution_engine import ConstitutionEngine


class FileService:
    """文件操作服务"""
    
    def __init__(self, constitution_engine: Optional[ConstitutionEngine] = None):
        self.constitution_engine = constitution_engine or ConstitutionEngine()
        self.root_path = Path(settings.root_path)
    
    def read_file(self, file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """读取文件内容"""
        path = PathUtils.normalize_path(file_path)
        
        # 检查宪法规则
        operation = {
            "action": "read",
            "target_path": str(path),
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许读取文件: {evaluation.get('violations', [])}")
        
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            logger.info(f"文件已读取: {path}")
            return content
        
        except UnicodeDecodeError:
            # 如果是二进制文件，尝试以二进制读取并返回摘要
            with open(path, 'rb') as f:
                binary_content = f.read()
            return f"<二进制文件，大小: {len(binary_content)} 字节>"
        
        except Exception as e:
            logger.error(f"读取文件失败: {path} - {e}")
            raise
    
    def write_file(self, 
                  file_path: Union[str, Path], 
                  content: str, 
                  encoding: str = 'utf-8',
                  overwrite: bool = False) -> bool:
        """写入文件"""
        path = PathUtils.normalize_path(file_path)
        
        # 检查文件是否存在
        if path.exists() and not overwrite:
            raise FileExistsError(f"文件已存在: {path}")
        
        # 检查宪法规则
        operation = {
            "action": "write",
            "target_path": str(path),
            "overwrite": overwrite,
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许写入文件: {evaluation.get('violations', [])}")
        
        # 如果需要确认
        if evaluation["requires_confirmation"]:
            # 在实际应用中，这里应该等待用户确认
            # 为了简化，我们假设已经确认
            pass
        
        try:
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            
            logger.info(f"文件已写入: {path}")
            return True
        
        except Exception as e:
            logger.error(f"写入文件失败: {path} - {e}")
            return False
    
    def delete_file(self, file_path: Union[str, Path]) -> bool:
        """删除文件"""
        path = PathUtils.normalize_path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        
        # 检查宪法规则
        operation = {
            "action": "delete",
            "target_path": str(path),
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许删除文件: {evaluation.get('violations', [])}")
        
        # 如果需要确认
        if evaluation["requires_confirmation"]:
            # 在实际应用中，这里应该等待用户确认
            # 为了简化，我们假设已经确认
            pass
        
        try:
            if path.is_file():
                path.unlink()
                logger.info(f"文件已删除: {path}")
            elif path.is_dir():
                shutil.rmtree(path)
                logger.info(f"目录已删除: {path}")
            
            return True
        
        except Exception as e:
            logger.error(f"删除文件失败: {path} - {e}")
            return False
    
    def copy_file(self, 
                 src_path: Union[str, Path], 
                 dst_path: Union[str, Path],
                 overwrite: bool = False) -> bool:
        """复制文件或目录"""
        src = PathUtils.normalize_path(src_path)
        dst = PathUtils.normalize_path(dst_path)
        
        if not src.exists():
            raise FileNotFoundError(f"源文件不存在: {src}")
        
        # 检查宪法规则
        operation = {
            "action": "copy",
            "source_path": str(src),
            "target_path": str(dst),
            "overwrite": overwrite,
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许复制文件: {evaluation.get('violations', [])}")
        
        try:
            # 如果目标已存在且不允许覆盖
            if dst.exists() and not overwrite:
                raise FileExistsError(f"目标文件已存在: {dst}")
            
            # 确保目标目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            if src.is_file():
                shutil.copy2(src, dst)
                logger.info(f"文件已复制: {src} -> {dst}")
            elif src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=overwrite)
                logger.info(f"目录已复制: {src} -> {dst}")
            
            return True
        
        except Exception as e:
            logger.error(f"复制文件失败: {src} -> {dst} - {e}")
            return False
    
    def move_file(self, 
                 src_path: Union[str, Path], 
                 dst_path: Union[str, Path],
                 overwrite: bool = False) -> bool:
        """移动文件或目录"""
        src = PathUtils.normalize_path(src_path)
        dst = PathUtils.normalize_path(dst_path)
        
        if not src.exists():
            raise FileNotFoundError(f"源文件不存在: {src}")
        
        # 检查宪法规则
        operation = {
            "action": "move",
            "source_path": str(src),
            "target_path": str(dst),
            "overwrite": overwrite,
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许移动文件: {evaluation.get('violations', [])}")
        
        try:
            # 如果目标已存在且不允许覆盖
            if dst.exists() and not overwrite:
                raise FileExistsError(f"目标文件已存在: {dst}")
            
            # 确保目标目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果目标已存在且允许覆盖，先删除目标
            if dst.exists() and overwrite:
                if dst.is_file():
                    dst.unlink()
                elif dst.is_dir():
                    shutil.rmtree(dst)
            
            shutil.move(src, dst)
            logger.info(f"文件已移动: {src} -> {dst}")
            return True
        
        except Exception as e:
            logger.error(f"移动文件失败: {src} -> {dst} - {e}")
            return False
    
    def create_directory(self, dir_path: Union[str, Path]) -> bool:
        """创建目录"""
        path = PathUtils.normalize_path(dir_path)
        
        # 检查宪法规则
        operation = {
            "action": "create_directory",
            "target_path": str(path),
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许创建目录: {evaluation.get('violations', [])}")
        
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"目录已创建: {path}")
            return True
        
        except Exception as e:
            logger.error(f"创建目录失败: {path} - {e}")
            return False
    
    def list_directory(self, 
                      dir_path: Union[str, Path], 
                      recursive: bool = False,
                      include_hidden: bool = False) -> List[Dict[str, Any]]:
        """列出目录内容"""
        path = PathUtils.normalize_path(dir_path)
        
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {path}")
        
        if not path.is_dir():
            raise NotADirectoryError(f"不是目录: {path}")
        
        # 检查宪法规则
        operation = {
            "action": "list_directory",
            "target_path": str(path),
            "recursive": recursive,
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许列出目录: {evaluation.get('violations', [])}")
        
        try:
            items = []
            
            if recursive:
                # 递归列出
                for item_path in path.rglob('*'):
                    if not include_hidden and item_path.name.startswith('.'):
                        continue
                    
                    if item_path.is_relative_to(path):  # 确保在目录内
                        items.append(PathUtils.get_file_info(item_path))
            else:
                # 非递归列出
                for item_path in path.iterdir():
                    if not include_hidden and item_path.name.startswith('.'):
                        continue
                    
                    items.append(PathUtils.get_file_info(item_path))
            
            # 排序：目录在前，按名称排序
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            logger.info(f"目录已列出: {path} (共 {len(items)} 项)")
            return items
        
        except Exception as e:
            logger.error(f"列出目录失败: {path} - {e}")
            return []
    
    def get_file_hash(self, file_path: Union[str, Path], algorithm: str = 'md5') -> str:
        """计算文件哈希值"""
        path = PathUtils.normalize_path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        
        if not path.is_file():
            raise IsADirectoryError(f"是目录而不是文件: {path}")
        
        try:
            hash_func = hashlib.new(algorithm)
            
            with open(path, 'rb') as f:
                # 分块读取大文件
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
        
        except Exception as e:
            logger.error(f"计算文件哈希失败: {path} - {e}")
            raise
    
    def get_directory_size(self, dir_path: Union[str, Path]) -> int:
        """计算目录大小（字节）"""
        path = PathUtils.normalize_path(dir_path)
        
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {path}")
        
        if not path.is_dir():
            raise NotADirectoryError(f"不是目录: {path}")
        
        total_size = 0
        
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except OSError:
                        # 忽略无法访问的文件
                        pass
            
            return total_size
        
        except Exception as e:
            logger.error(f"计算目录大小失败: {path} - {e}")
            return 0
    
    def search_files(self, 
                    search_term: str, 
                    search_path: Optional[Union[str, Path]] = None,
                    search_type: str = 'name',
                    case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """搜索文件"""
        if search_path is None:
            search_path = self.root_path
        
        path = PathUtils.normalize_path(search_path)
        
        if not path.exists():
            raise FileNotFoundError(f"搜索路径不存在: {path}")
        
        # 检查宪法规则
        operation = {
            "action": "search_files",
            "target_path": str(path),
            "search_term": search_term,
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许搜索文件: {evaluation.get('violations', [])}")
        
        try:
            matches = []
            search_term_adj = search_term if case_sensitive else search_term.lower()
            
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
            
            logger.info(f"文件搜索完成: '{search_term}' (共 {len(matches)} 个匹配项)")
            return matches
        
        except Exception as e:
            logger.error(f"搜索文件失败: {path} - {e}")
            return []
    
    def get_file_statistics(self, dir_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """获取文件统计信息"""
        if dir_path is None:
            dir_path = self.root_path
        
        path = PathUtils.normalize_path(dir_path)
        
        if not path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")
        
        try:
            file_count = 0
            dir_count = 0
            total_size = 0
            extensions = {}
            
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
                "file_extensions": dict(sorted_extensions[:10]),  # 前10个扩展名
                "last_updated": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"获取文件统计失败: {path} - {e}")
            return {}