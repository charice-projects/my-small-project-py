"""
输入验证工具 - 验证用户输入和参数
"""
import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from config.settings import settings
from utils.path_utils import PathUtils


class ValidationError(Exception):
    """验证错误异常"""
    pass


class InputValidator:
    """输入验证器"""
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = False) -> Path:
        """验证路径"""
        try:
            normalized = PathUtils.normalize_path(path)
            
            # 检查是否在工作空间内
            root = PathUtils.normalize_path(settings.root_path)
            if not (normalized == root or normalized.is_relative_to(root)):
                raise ValidationError(f"路径必须在工作空间内: {path}")
            
            # 检查路径是否存在
            if must_exist and not normalized.exists():
                raise ValidationError(f"路径不存在: {path}")
            
            return normalized
        
        except Exception as e:
            raise ValidationError(f"路径验证失败: {str(e)}")
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """验证文件名"""
        # 检查非法字符
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in illegal_chars:
            if char in filename:
                raise ValidationError(f"文件名包含非法字符: {char}")
        
        # 检查保留名称（Windows）
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        name_without_ext = filename.split('.')[0].upper()
        if name_without_ext in reserved_names:
            raise ValidationError(f"文件名是系统保留名称: {filename}")
        
        # 检查长度
        if len(filename) > 255:
            raise ValidationError(f"文件名过长 (最大255字符): {filename}")
        
        # 检查路径分隔符
        if '/' in filename or '\\' in filename:
            raise ValidationError("文件名不能包含路径分隔符")
        
        return True
    
    @staticmethod
    def validate_file_size(size_bytes: int, max_size: Optional[int] = None) -> bool:
        """验证文件大小"""
        if max_size is None:
            max_size = settings.max_file_size
        
        if size_bytes > max_size:
            raise ValidationError(
                f"文件大小超出限制: {PathUtils.humanize_size(size_bytes)} > "
                f"{PathUtils.humanize_size(max_size)}"
            )
        
        return True
    
    @staticmethod
    def validate_command(command: str) -> Dict[str, Any]:
        """验证命令"""
        if not command or not command.strip():
            raise ValidationError("命令不能为空")
        
        # 检查命令长度
        if len(command) > 1000:
            raise ValidationError("命令过长 (最大1000字符)")
        
        # 检查危险命令模式（简单检查）
        dangerous_patterns = [
            r'rm\s+-rf',
            r'del\s+/\s*[qf]',
            r'format\s+',
            r'chmod\s+777',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValidationError(f"检测到可能危险的命令: {command}")
        
        return {
            "command": command.strip(),
            "length": len(command.strip()),
            "valid": True
        }
    
    @staticmethod
    def validate_intent(intent: Dict[str, Any]) -> bool:
        """验证意图"""
        required_fields = ["action", "confidence"]
        
        for field in required_fields:
            if field not in intent:
                raise ValidationError(f"意图缺少必要字段: {field}")
        
        # 验证置信度
        confidence = intent.get("confidence", 0)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            raise ValidationError(f"置信度必须在0-1之间: {confidence}")
        
        # 验证操作类型
        action = intent.get("action", "")
        if not action or not isinstance(action, str):
            raise ValidationError(f"无效的操作类型: {action}")
        
        return True
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL"""
        try:
            result = urlparse(url)
            
            # 检查协议
            if result.scheme not in ['http', 'https', 'file']:
                raise ValidationError(f"不支持的协议: {result.scheme}")
            
            # 检查主机名（对于http/https）
            if result.scheme in ['http', 'https'] and not result.netloc:
                raise ValidationError("URL缺少主机名")
            
            return True
        
        except Exception as e:
            raise ValidationError(f"URL验证失败: {str(e)}")
    
    @staticmethod
    def validate_search_query(query: str) -> bool:
        """验证搜索查询"""
        if not query or not query.strip():
            raise ValidationError("搜索查询不能为空")
        
        # 检查查询长度
        if len(query) > 200:
            raise ValidationError("搜索查询过长 (最大200字符)")
        
        # 检查非法字符
        illegal_chars = ['\0', '\n', '\r']
        for char in illegal_chars:
            if char in query:
                raise ValidationError(f"搜索查询包含非法字符")
        
        return True
    
    @staticmethod
    def validate_parameters(parameters: Dict[str, Any], 
                           required: List[str] = None,
                           optional: List[str] = None) -> bool:
        """验证参数"""
        if required:
            for param in required:
                if param not in parameters:
                    raise ValidationError(f"缺少必要参数: {param}")
        
        # 检查未知参数（如果提供了可选参数列表）
        if optional is not None:
            all_params = (required or []) + optional
            for param in parameters.keys():
                if param not in all_params:
                    raise ValidationError(f"未知参数: {param}")
        
        # 验证布尔参数
        for key, value in parameters.items():
            if key.endswith('_bool') or key in ['recursive', 'overwrite', 'hidden']:
                if not isinstance(value, bool):
                    raise ValidationError(f"参数 {key} 必须是布尔值")
        
        # 验证数值参数
        for key, value in parameters.items():
            if key.endswith('_int') or key in ['limit', 'max_depth', 'port']:
                if not isinstance(value, int) or value < 0:
                    raise ValidationError(f"参数 {key} 必须是非负整数")
        
        return True
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名"""
        # 移除前后空格
        filename = filename.strip()
        
        # 替换非法字符
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 移除控制字符
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # 限制长度
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255 - len(ext)] + ext
        
        return filename
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """清理路径"""
        # 标准化路径分隔符
        path = path.replace('\\', '/')
        
        # 移除多余的斜杠
        path = re.sub(r'/+', '/', path)
        
        # 移除开头的点
        if path.startswith('./'):
            path = path[2:]
        
        # 移除对父目录的引用（安全限制）
        parts = path.split('/')
        new_parts = []
        for part in parts:
            if part == '..':
                if new_parts:
                    new_parts.pop()
            elif part != '.' and part:
                new_parts.append(part)
        
        return '/'.join(new_parts) if new_parts else '.'