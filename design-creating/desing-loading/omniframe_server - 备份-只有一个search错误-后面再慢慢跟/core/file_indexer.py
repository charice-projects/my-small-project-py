"""
智能索引生成器
"""
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import yaml

from config.settings import settings
from utils.path_utils import PathUtils
from utils.logger import logger


class FileIndexer:
    """智能文件索引器"""
    
    def __init__(self, root_path: Optional[str] = None):
        self.root_path = Path(root_path or settings.root_path).resolve()
        self.index_file = PathUtils.get_data_dir() / "file_index.yaml"
        self.index_version = "1.0"
        self.index_data = {
            "version": self.index_version,
            "generated_at": datetime.now().isoformat(),
            "root_path": str(self.root_path),
            "total_files": 0,
            "total_directories": 0,
            "total_size": 0,
            "categories": {},
            "files": [],
            "directories": [],
            "file_types": {},
            "tags": {},
            "workspaces": {},
        }
        
        # 分类规则
        self.category_rules = {
            "code": {
                "extensions": ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php'],
                "keywords": ['src', 'lib', 'module', 'package', 'class', 'function']
            },
            "document": {
                "extensions": ['.md', '.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt'],
                "keywords": ['doc', 'docs', 'documentation', 'readme', 'guide']
            },
            "image": {
                "extensions": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
                "keywords": ['image', 'img', 'picture', 'photo', 'screenshot']
            },
            "data": {
                "extensions": ['.json', '.xml', '.yaml', '.yml', '.csv', '.xlsx', '.db', '.sqlite'],
                "keywords": ['data', 'config', 'configuration', 'setting', 'database']
            },
            "archive": {
                "extensions": ['.zip', '.tar', '.gz', '.7z', '.rar', '.bz2'],
                "keywords": ['archive', 'backup', 'zip', 'compressed']
            },
            "executable": {
                "extensions": ['.exe', '.bat', '.cmd', '.sh', '.bin', '.app'],
                "keywords": ['bin', 'executable', 'program', 'application']
            }
        }
    
    def should_index(self, path: Path) -> bool:
        """判断是否应该索引该路径"""
        # 跳过隐藏文件/目录（以点开头）
        if path.name.startswith('.'):
            return False
        
        # 检查排除模式
        for pattern in settings.index_exclude_patterns:
            if path.match(pattern):
                return False
        
        # 安全检查
        if not PathUtils.is_safe_path(path):
            return False
        
        return True
    
    def categorize_file(self, path: Path, info: Dict[str, Any]) -> List[str]:
        """对文件进行分类"""
        categories = []
        
        # 基于扩展名分类
        suffix = path.suffix.lower()
        for category, rules in self.category_rules.items():
            if suffix in rules['extensions']:
                categories.append(category)
        
        # 基于路径关键词分类
        path_str = str(path).lower()
        for category, rules in self.category_rules.items():
            for keyword in rules['keywords']:
                if keyword in path_str:
                    if category not in categories:
                        categories.append(category)
                    break
        
        # 如果没有分类，使用'other'
        if not categories:
            categories.append('other')
        
        return categories
    
    def extract_tags(self, path: Path, info: Dict[str, Any]) -> List[str]:
        """从文件中提取标签"""
        tags = []
        
        # 基于文件名提取标签
        name_lower = path.stem.lower()
        
        # 常见标签规则
        tag_rules = {
            'important': ['重要', '紧急', 'critical', 'important', 'urgent'],
            'draft': ['草稿', 'draft', 'temp', 'temporary', 'tmp'],
            'final': ['最终', 'final', 'release', 'published'],
            'backup': ['备份', 'backup', 'archive', 'old', 'previous'],
            'config': ['配置', 'config', 'setting', 'preference'],
            'test': ['测试', 'test', 'example', 'demo', 'sample'],
        }
        
        for tag, keywords in tag_rules.items():
            for keyword in keywords:
                if keyword in name_lower:
                    tags.append(tag)
                    break
        
        # 基于目录名称的标签
        for parent in path.parents:
            if parent == self.root_path:
                break
            parent_name = parent.name.lower()
            if parent_name not in tags and len(parent_name) > 1:
                tags.append(parent_name)
        
        return tags
    
    def calculate_file_hash(self, path: Path) -> Optional[str]:
        """计算文件哈希（用于检测变化）"""
        if not path.is_file():
            return None
        
        try:
            hasher = hashlib.sha256()
            with open(path, 'rb') as f:
                # 只读取前1MB来计算哈希（对于大文件）
                chunk = f.read(1024 * 1024)
                hasher.update(chunk)
            
            # 加上文件大小和修改时间
            stat = path.stat()
            hasher.update(str(stat.st_size).encode())
            hasher.update(str(int(stat.st_mtime)).encode())
            
            return hasher.hexdigest()[:16]  # 截断为16字符
        except Exception as e:
            logger.warning(f"计算文件哈希失败 {path}: {e}")
            return None
    
    def index_path(self, path: Path, recursive: bool = True) -> Dict[str, Any]:
        """索引单个路径"""
        if not self.should_index(path):
            return {}
        
        info = PathUtils.get_file_info(path)
        categories = self.categorize_file(path, info)
        tags = self.extract_tags(path, info)
        file_hash = self.calculate_file_hash(path) if path.is_file() else None
        
        indexed_info = {
            "name": path.name,
            "path": str(path),
            "relative_path": PathUtils.get_relative_path(path),
            "type": "file" if path.is_file() else "directory",
            "size": info["size"],
            "size_human": info["size_human"],
            "created": info["created_iso"],
            "modified": info["modified_iso"],
            "categories": categories,
            "tags": tags,
            "hash": file_hash,
            "mime_type": info["mime_type"] if path.is_file() else None,
            "permissions": info["permissions"],
        }
        
        # 如果是目录且需要递归
        if path.is_dir() and recursive:
            indexed_info["children"] = []
            try:
                for child in path.iterdir():
                    if self.should_index(child):
                        child_info = self.index_path(child, recursive)
                        if child_info:
                            indexed_info["children"].append(child_info)
            except PermissionError as e:
                logger.warning(f"无权限访问目录 {path}: {e}")
                indexed_info["access_error"] = True
        
        return indexed_info
    
    
  
    def get_index_status(self) -> Dict[str, Any]:
        """获取索引状态"""
        try:
            if not self.index_file.exists():
                return {
                    "has_index": False,
                    "status": "not_generated",
                    "message": "索引未生成",
                    "last_generated": None,
                    "file_count": 0,
                    "directory_count": 0,
                    "total_size": 0
                }
            
            # 加载索引数据
            self.load_index()
            
            return {
                "has_index": True,
                "status": "ready",
                "last_generated": self.index_data.get("generated_at"),
                "file_count": self.index_data.get("total_files", 0),
                "directory_count": self.index_data.get("total_directories", 0),
                "total_size": self.index_data.get("total_size", 0),
                "categories": self.index_data.get("categories", {}),
                "file_types": self.index_data.get("file_types", {}),
                "workspaces": list(self.index_data.get("workspaces", {}).keys()),
                "index_path": str(self.index_file),
                "root_path": str(self.root_path)
            }
        
        except Exception as e:
            return {
                "has_index": False,
                "status": "error",
                "error": str(e),
                "message": f"获取索引状态失败: {e}"
            }
        
    

    def generate_index(self, force: bool = False, incremental: bool = False) -> Dict[str, Any]:
        """生成完整的文件索引
        Args:
            force: 是否强制重新生成（忽略现有索引）
            incremental: 是否增量更新（当前版本暂时忽略此参数）
        """       
        start_time = time.time()
               
        logger.info(f"开始生成索引: {self.root_path}, 增量模式: {incremental}, 强制模式: {force}")   
        # 如果不需要强制重新生成，且已有索引，则加载现有索引
        if not force and self.index_file.exists():
            existing_index = self.load_index()
            if existing_index:
                logger.info(f"使用现有索引，包含 {self.index_data['total_files']} 个文件")
                return self.index_data
       
        
        # 重置索引数据
        self.index_data = {
            "version": self.index_version,
            "generated_at": datetime.now().isoformat(),
            "root_path": str(self.root_path),
            "total_files": 0,
            "total_directories": 0,
            "total_size": 0,
            "categories": {cat: 0 for cat in self.category_rules.keys()},
            "file_types": {},
            "tags": {},
            "files": [],
            "directories": [],
            "workspaces": self._generate_workspaces(),
        }
        
        # 遍历根目录
        try:
            for item in self.root_path.iterdir():
                if self.should_index(item):
                    indexed = self.index_path(item, recursive=True)
                    if indexed:
                        self._add_to_index(indexed)
        except Exception as e:
            logger.error(f"索引生成失败: {e}")
        
        # 计算统计信息
        self._calculate_statistics()
        
        # 保存索引
        self.save_index()
        
        elapsed = time.time() - start_time
        logger.info(f"索引生成完成: {self.index_data['total_files']} 个文件, "
                   f"{self.index_data['total_directories']} 个目录, "
                   f"耗时 {elapsed:.2f} 秒")
        
        return self.index_data
    
    def _add_to_index(self, item: Dict[str, Any]):
        """将索引项添加到索引数据中"""
        if item["type"] == "file":
            self.index_data["files"].append(item)
            self.index_data["total_files"] += 1
            self.index_data["total_size"] += item["size"]
            
            # 更新分类统计
            for category in item["categories"]:
                if category in self.index_data["categories"]:
                    self.index_data["categories"][category] += 1
            
            # 更新文件类型统计
            ext = Path(item["path"]).suffix.lower()
            if ext:
                self.index_data["file_types"][ext] = self.index_data["file_types"].get(ext, 0) + 1
            
            # 更新标签统计
            for tag in item["tags"]:
                self.index_data["tags"][tag] = self.index_data["tags"].get(tag, 0) + 1
                
        elif item["type"] == "directory":
            self.index_data["directories"].append(item)
            self.index_data["total_directories"] += 1
    
    def _calculate_statistics(self):
        """计算统计信息"""
        # 按大小排序文件
        self.index_data["files"] = sorted(
            self.index_data["files"], 
            key=lambda x: x["size"], 
            reverse=True
        )
        
        # 按修改时间排序
        self.index_data["recent_files"] = sorted(
            self.index_data["files"],
            key=lambda x: x["modified"],
            reverse=True
        )[:100]  # 最近100个文件
        
        # 大文件列表
        self.index_data["large_files"] = [
            f for f in self.index_data["files"] 
            if f["size"] > 10 * 1024 * 1024  # 大于10MB
        ][:50]
    
    def _generate_workspaces(self) -> Dict[str, Any]:
        """生成预定义的工作区"""
        workspaces = {
            "recent": {
                "name": "最近文件",
                "description": "最近修改的文件",
                "type": "dynamic",
                "query": "recent:7d"  # 最近7天
            },
            "large_files": {
                "name": "大文件",
                "description": "占用空间较大的文件",
                "type": "dynamic",
                "query": "size:>10MB"
            },
            "images": {
                "name": "图片",
                "description": "所有图片文件",
                "type": "category",
                "category": "image"
            },
            "documents": {
                "name": "文档",
                "description": "所有文档文件",
                "type": "category",
                "category": "document"
            },
            "code": {
                "name": "代码",
                "description": "所有代码文件",
                "type": "category",
                "category": "code"
            }
        }
        
        return workspaces
    
    def save_index(self):
        """保存索引到文件"""
        try:
            # 创建数据目录
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存为YAML
            with open(self.index_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.index_data, f, allow_unicode=True, sort_keys=False)
            
            logger.info(f"索引已保存到: {self.index_file}")
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
    
    def load_index(self) -> Optional[Dict[str, Any]]:
        """从文件加载索引"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.index_data = yaml.safe_load(f) or {}
                
                logger.info(f"索引已加载: {self.index_file}")
                return self.index_data
            else:
                logger.warning(f"索引文件不存在: {self.index_file}")
                return None
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
            return None
    
    def find_files(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据查询条件查找文件"""
        results = []
        
        for file_info in self.index_data.get("files", []):
            if self._matches_query(file_info, query):
                results.append(file_info)
        
        return results
    
    def _matches_query(self, file_info: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """检查文件是否匹配查询条件"""
        # 支持多种查询条件
        for key, value in query.items():
            if key == "name" and value not in file_info["name"].lower():
                return False
            elif key == "category" and value not in file_info["categories"]:
                return False
            elif key == "tag" and value not in file_info["tags"]:
                return False
            elif key == "type" and value != file_info["type"]:
                return False
            elif key == "extension" and not file_info["path"].lower().endswith(value.lower()):
                return False
            elif key == "size":
                # 支持大小比较: ">10MB", "<1GB", "=500KB"
                pass  # 简化的实现
        
        return True
    
    def update_index(self, changes: Dict[str, Any]) -> bool:
        """更新索引（增量更新）"""
        try:
            # 加载现有索引
            current_index = self.load_index() or {}
            
            # 应用更改
            # 这里可以实现增量更新逻辑
            
            # 重新生成索引
            self.generate_index(force=True)
            
            return True
        except Exception as e:
            logger.error(f"更新索引失败: {e}")
            return False