"""
路径处理工具
"""
import os
import re
import shutil
from pathlib import Path, PurePath
from typing import List, Tuple, Optional, Union
from urllib.parse import unquote, quote
import mimetypes

from config.settings import settings


class PathUtils:
    """路径处理工具类"""
    
    @staticmethod
    def normalize_path(path: Union[str, Path]) -> Path:
        """标准化路径"""
        if isinstance(path, str):
            path = Path(path)
        
        # 处理相对路径
        if not path.is_absolute():
            # 如果是相对路径，基于工作空间根目录
            root = Path(settings.root_path)
            path = root / path
        
        # 解析路径中的 .. 和 .
        try:
            # 获取绝对路径并标准化
            normalized = path.resolve()
            
            # 确保路径在工作空间内（安全检查）
            root = Path(settings.root_path).resolve()
            if normalized == root or normalized.is_relative_to(root):
                return normalized
            else:
                # 尝试转换为基于工作空间的相对路径
                try:
                    relative = normalized.relative_to(root)
                    return root / relative
                except ValueError:
                    # 如果路径不在工作空间内，返回工作空间内的安全路径
                    # 或者抛出异常，根据安全模式决定
                    if settings.safe_mode:
                        raise PermissionError(f"路径 {path} 不在工作空间内")
                    else:
                        # 记录警告但允许访问
                        print(f"警告：访问工作空间外的路径: {path}")
                        return normalized
        except Exception as e:
            print(f"路径标准化错误: {e}")
            return Path(settings.root_path)
    
    @staticmethod
    def is_safe_path(path: Union[str, Path]) -> bool:
        """检查路径是否安全"""
        try:
            normalized = PathUtils.normalize_path(path)
            root = Path(settings.root_path).resolve()
            
            # 检查是否在工作空间内
            if not (normalized == root or normalized.is_relative_to(root)):
                return False
            
            # 检查是否为保护目录
            for protected in settings.get("protected_directories", []):
                protected_path = root / protected.lstrip("/")
                if normalized == protected_path or normalized.is_relative_to(protected_path):
                    return False
            
            # 检查文件扩展名
            if normalized.is_file():
                suffix = normalized.suffix.lower()
                blocked_extensions = ['.exe', '.bat', '.cmd', '.ps1', '.sh', '.dll', '.sys']
                if suffix in blocked_extensions and settings.safe_mode:
                    return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_relative_path(full_path: Union[str, Path]) -> str:
        """获取相对于工作空间的路径"""
        try:
            full_path = PathUtils.normalize_path(full_path)
            root = Path(settings.root_path).resolve()
            relative = full_path.relative_to(root)
            return str(relative)
        except ValueError:
            return str(full_path)
    
    @staticmethod
    def get_file_info(path: Union[str, Path]) -> dict:
        """获取文件信息"""
        path = PathUtils.normalize_path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        
        stats = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))
        
        return {
            "name": path.name,
            "path": str(path),
            "relative_path": PathUtils.get_relative_path(path),
            "size": stats.st_size,
            "size_human": PathUtils.humanize_size(stats.st_size),
            "created": stats.st_ctime,
            "created_iso": PathUtils.timestamp_to_iso(stats.st_ctime),
            "modified": stats.st_mtime,
            "modified_iso": PathUtils.timestamp_to_iso(stats.st_mtime),
            "accessed": stats.st_atime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
            "parent": str(path.parent),
            "suffix": path.suffix,
            "mime_type": mime_type or "application/octet-stream",
            "permissions": oct(stats.st_mode)[-3:],
        }
    
    @staticmethod
    def humanize_size(size_bytes: int) -> str:
        """将字节数转换为人类可读的格式"""
        if size_bytes == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        i = 0
        size = float(size_bytes)
        
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        
        return f"{size:.2f} {units[i]}"
    
    @staticmethod
    def timestamp_to_iso(timestamp: float) -> str:
        """时间戳转ISO格式"""
        from datetime import datetime, timezone
        
        # 处理可能为0或无效的时间戳
        if timestamp <= 0:
            return datetime.now(timezone.utc).isoformat()
        
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            return datetime.now(timezone.utc).isoformat()
    
    
    
    
    @staticmethod
    def path_to_url(path: Union[str, Path]) -> str:
        """将路径转换为URL编码的字符串"""
        relative = PathUtils.get_relative_path(path)
        # URL编码，但保留斜杠
        parts = relative.split('/')
        encoded_parts = [quote(part, safe='') for part in parts]
        return '/'.join(encoded_parts)
    
    @staticmethod
    def url_to_path(url_path: str) -> Path:
        """将URL路径转换回文件系统路径"""
        # URL解码
        decoded = unquote(url_path)
        # 转换为绝对路径
        return PathUtils.normalize_path(decoded)
    
    @staticmethod
    def get_directory_tree(root_path: Union[str, Path], max_depth: int = 3) -> dict:
        """获取目录树结构"""
        root = PathUtils.normalize_path(root_path)
        
        def build_tree(path: Path, depth: int = 0) -> Optional[dict]:
            if depth > max_depth:
                return None
            
            if not path.exists():
                return None
            
            info = PathUtils.get_file_info(path)
            tree = {
                "name": path.name,
                "path": str(path),
                "relative_path": PathUtils.get_relative_path(path),
                "type": "directory" if path.is_dir() else "file",
                "size": info["size"],
                "size_human": info["size_human"],
                "modified": info["modified_iso"],
                "children": []
            }
            
            if path.is_dir():
                try:
                    for child in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                        # 跳过隐藏文件（以点开头）
                        if child.name.startswith('.'):
                            continue
                        
                        child_tree = build_tree(child, depth + 1)
                        if child_tree:
                            tree["children"].append(child_tree)
                except PermissionError:
                    tree["error"] = "无访问权限"
            
            return tree
        
        return build_tree(root) or {}
    
    @staticmethod
    def find_files(pattern: str, root_path: Optional[Union[str, Path]] = None) -> List[Path]:
        """查找匹配模式的文件"""
        if root_path is None:
            root_path = settings.root_path
        
        root = PathUtils.normalize_path(root_path)
        matches = []
        
        # 支持简单的通配符模式
        if '*' in pattern or '?' in pattern:
            import fnmatch
            for file_path in root.rglob('*'):
                if fnmatch.fnmatch(file_path.name, pattern):
                    matches.append(file_path)
        else:
            # 简单文本搜索
            pattern_lower = pattern.lower()
            for file_path in root.rglob('*'):
                if pattern_lower in file_path.name.lower():
                    matches.append(file_path)
        
        return matches
      
    # 这里
    @staticmethod
    def get_data_dir() -> Path:
        """获取应用程序数据目录"""
        import platform
        
        # 优先使用环境变量指定的数据目录
        data_dir_env = os.getenv('OMNIFRAME_DATA_DIR')
        if data_dir_env:
            data_dir = Path(data_dir_env)
        else:
            # 根据操作系统选择合适的数据目录
            system = platform.system()
            
            if system == "Windows":
                # Windows: 使用 %APPDATA% 目录
                appdata = os.getenv('APPDATA')
                if appdata:
                    data_dir = Path(appdata) / "OmniframeServer"
                else:
                    # 备用方案：使用项目目录下的 data 文件夹
                    project_root = Path(__file__).parent.parent.parent
                    data_dir = project_root / "data"
            elif system == "Darwin":  # macOS
                data_dir = Path.home() / "Library" / "Application Support" / "OmniframeServer"
            else:  # Linux 和其他 Unix 系统
                data_dir = Path.home() / ".omniframe_server"
        
        # 确保目录存在
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建必要的子目录
        subdirs = ["cache", "logs", "contexts", "backups"]
        for subdir in subdirs:
            (data_dir / subdir).mkdir(exist_ok=True)
        
        return data_dir
        
    
    @staticmethod
    def get_logs_dir() -> Path:
        """获取日志目录"""
        # 从数据目录获取logs子目录
        data_dir = PathUtils.get_data_dir()
        logs_dir = data_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir
        
        
        
     
    
    