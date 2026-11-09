"""
搜索服务 - 提供高级文件搜索功能
"""
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
from services.file_service import FileService


class SearchService:
    """搜索服务"""
    
    def __init__(self, file_service: Optional[FileService] = None):
        self.file_service = file_service or FileService()
        self.root_path = Path(settings.root_path)
    
    def search_by_name(self, 
                      name_pattern: str, 
                      search_path: Optional[Union[str, Path]] = None,
                      regex: bool = False,
                      case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """按名称搜索文件"""
        if search_path is None:
            search_path = self.root_path
        
        path = PathUtils.normalize_path(search_path)
        
        try:
            matches = []
            
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    file_name = file_path.name
                    
                    if regex:
                        # 正则表达式匹配
                        try:
                            flags = 0 if case_sensitive else re.IGNORECASE
                            if re.search(name_pattern, file_name, flags=flags):
                                matches.append(PathUtils.get_file_info(file_path))
                        except re.error:
                            # 正则表达式无效，回退到普通搜索
                            pass
                    else:
                        # 普通字符串匹配
                        if case_sensitive:
                            if name_pattern in file_name:
                                matches.append(PathUtils.get_file_info(file_path))
                        else:
                            if name_pattern.lower() in file_name.lower():
                                matches.append(PathUtils.get_file_info(file_path))
            
            logger.info(f"按名称搜索完成: '{name_pattern}' (共 {len(matches)} 个匹配项)")
            return matches
        
        except Exception as e:
            logger.error(f"按名称搜索失败: {path} - {e}")
            return []
    
    def search_by_content(self, 
                         content_pattern: str, 
                         search_path: Optional[Union[str, Path]] = None,
                         file_extensions: Optional[List[str]] = None,
                         max_file_size: int = 10 * 1024 * 1024,  # 10MB
                         regex: bool = False,
                         case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """按内容搜索文件"""
        if search_path is None:
            search_path = self.root_path
        
        path = PathUtils.normalize_path(search_path)
        
        # 默认搜索文本文件
        if file_extensions is None:
            file_extensions = ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']
        
        try:
            matches = []
            content_pattern_adj = content_pattern
            
            if not case_sensitive and not regex:
                content_pattern_adj = content_pattern.lower()
            
            for file_path in path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # 检查文件扩展名
                if file_extensions and file_path.suffix.lower() not in file_extensions:
                    continue
                
                # 检查文件大小
                try:
                    file_size = file_path.stat().st_size
                    if file_size > max_file_size:
                        continue
                except OSError:
                    continue
                
                try:
                    # 读取文件内容
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 搜索内容
                    found = False
                    
                    if regex:
                        # 正则表达式匹配
                        flags = 0 if case_sensitive else re.IGNORECASE
                        if re.search(content_pattern, content, flags=flags):
                            found = True
                    else:
                        # 普通字符串匹配
                        if case_sensitive:
                            if content_pattern in content:
                                found = True
                        else:
                            if content_pattern_adj in content.lower():
                                found = True
                    
                    if found:
                        file_info = PathUtils.get_file_info(file_path)
                        # 添加上下文片段
                        context = self._get_content_context(content, content_pattern, regex, case_sensitive)
                        file_info['content_context'] = context
                        matches.append(file_info)
                
                except Exception:
                    # 忽略无法读取的文件
                    continue
            
            logger.info(f"按内容搜索完成: '{content_pattern}' (共 {len(matches)} 个匹配项)")
            return matches
        
        except Exception as e:
            logger.error(f"按内容搜索失败: {path} - {e}")
            return []
    
    def _get_content_context(self, 
                           content: str, 
                           pattern: str, 
                           regex: bool = False,
                           case_sensitive: bool = False,
                           context_lines: int = 3) -> List[str]:
        """获取内容上下文片段"""
        lines = content.split('\n')
        context_snippets = []
        
        for i, line in enumerate(lines):
            found = False
            
            if regex:
                # 正则表达式匹配
                flags = 0 if case_sensitive else re.IGNORECASE
                if re.search(pattern, line, flags=flags):
                    found = True
            else:
                # 普通字符串匹配
                if case_sensitive:
                    if pattern in line:
                        found = True
                else:
                    if pattern.lower() in line.lower():
                        found = True
            
            if found:
                # 获取上下文行
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = lines[start:end]
                
                # 标记匹配行
                context[context_lines if i >= context_lines else i] = f"▶ {context[context_lines if i >= context_lines else i]}"
                
                context_snippets.append('\n'.join(context))
        
        return context_snippets[:5]  # 最多返回5个片段
    
    def search_by_date(self, 
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      search_path: Optional[Union[str, Path]] = None,
                      date_type: str = 'modified') -> List[Dict[str, Any]]:
        """按日期搜索文件"""
        if search_path is None:
            search_path = self.root_path
        
        path = PathUtils.normalize_path(search_path)
        
        # 设置默认日期范围
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        
        if end_date is None:
            end_date = datetime.now()
        
        try:
            matches = []
            
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    try:
                        stats = file_path.stat()
                        
                        if date_type == 'modified':
                            file_date = datetime.fromtimestamp(stats.st_mtime)
                        elif date_type == 'created':
                            file_date = datetime.fromtimestamp(stats.st_ctime)
                        elif date_type == 'accessed':
                            file_date = datetime.fromtimestamp(stats.st_atime)
                        else:
                            file_date = datetime.fromtimestamp(stats.st_mtime)
                        
                        if start_date <= file_date <= end_date:
                            file_info = PathUtils.get_file_info(file_path)
                            file_info[f'{date_type}_date'] = file_date.isoformat()
                            matches.append(file_info)
                    
                    except OSError:
                        # 忽略无法访问的文件
                        continue
            
            logger.info(f"按日期搜索完成: {start_date.date()} 到 {end_date.date()} (共 {len(matches)} 个匹配项)")
            return matches
        
        except Exception as e:
            logger.error(f"按日期搜索失败: {path} - {e}")
            return []
    
    def search_by_size(self, 
                      min_size: int = 0,
                      max_size: Optional[int] = None,
                      search_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """按大小搜索文件"""
        if search_path is None:
            search_path = self.root_path
        
        path = PathUtils.normalize_path(search_path)
        
        try:
            matches = []
            
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        
                        if file_size >= min_size and (max_size is None or file_size <= max_size):
                            file_info = PathUtils.get_file_info(file_path)
                            matches.append(file_info)
                    
                    except OSError:
                        # 忽略无法访问的文件
                        continue
            
            logger.info(f"按大小搜索完成: {min_size} 到 {max_size or '无限制'} 字节 (共 {len(matches)} 个匹配项)")
            return matches
        
        except Exception as e:
            logger.error(f"按大小搜索失败: {path} - {e}")
            return []
    
    def advanced_search(self, 
                       criteria: Dict[str, Any],
                       search_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """高级搜索（组合多个条件）"""
        if search_path is None:
            search_path = self.root_path
        
        path = PathUtils.normalize_path(search_path)
        
        try:
            # 初始结果集
            all_files = []
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    all_files.append(file_path)
            
            # 应用过滤条件
            filtered_files = []
            
            for file_path in all_files:
                try:
                    file_info = PathUtils.get_file_info(file_path)
                    stats = file_path.stat()
                    
                    match = True
                    
                    # 名称过滤
                    if 'name_pattern' in criteria and criteria['name_pattern']:
                        name_pattern = criteria['name_pattern']
                        case_sensitive = criteria.get('case_sensitive', False)
                        
                        if case_sensitive:
                            if name_pattern not in file_path.name:
                                match = False
                        else:
                            if name_pattern.lower() not in file_path.name.lower():
                                match = False
                    
                    # 扩展名过滤
                    if 'extensions' in criteria and criteria['extensions']:
                        extensions = criteria['extensions']
                        if file_path.suffix.lower() not in extensions:
                            match = False
                    
                    # 大小过滤
                    if 'min_size' in criteria:
                        if stats.st_size < criteria['min_size']:
                            match = False
                    
                    if 'max_size' in criteria and criteria['max_size']:
                        if stats.st_size > criteria['max_size']:
                            match = False
                    
                    # 日期过滤
                    if 'start_date' in criteria and criteria['start_date']:
                        start_date = criteria['start_date']
                        file_date = datetime.fromtimestamp(stats.st_mtime)
                        
                        if file_date < start_date:
                            match = False
                    
                    if 'end_date' in criteria and criteria['end_date']:
                        end_date = criteria['end_date']
                        file_date = datetime.fromtimestamp(stats.st_mtime)
                        
                        if file_date > end_date:
                            match = False
                    
                    if match:
                        filtered_files.append(file_info)
                
                except OSError:
                    continue
            
            logger.info(f"高级搜索完成 (共 {len(filtered_files)} 个匹配项)")
            return filtered_files
        
        except Exception as e:
            logger.error(f"高级搜索失败: {path} - {e}")
            return []