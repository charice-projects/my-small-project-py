"""
utils/file_ops.py
文件操作工具函数
"""
import os
import shutil
import json
import yaml
from datetime import datetime
from pathlib import Path
import hashlib


class FileOperations:
    """文件操作类"""
    
    @staticmethod
    def ensure_directory(directory):
        """确保目录存在，如果不存在则创建"""
        if not directory:
            return False
        
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            print(f"创建目录失败 {directory}: {e}")
            return False
    
    @staticmethod
    def read_file(file_path, encoding='utf-8'):
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
            except Exception as e:
                raise Exception(f"无法读取文件 {file_path}: {e}")
        except Exception as e:
            raise Exception(f"无法读取文件 {file_path}: {e}")
    
    @staticmethod
    def write_file(file_path, content, encoding='utf-8'):
        """写入文件内容"""
        try:
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        except Exception as e:
            raise Exception(f"写入文件失败 {file_path}: {e}")
    
    @staticmethod
    def find_files(directory, extensions=None, recursive=True):
        """查找指定扩展名的文件"""
        if not os.path.exists(directory):
            return []
        
        extensions = extensions or ['.html', '.htm']
        files = []
        
        if recursive:
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    if any(filename.lower().endswith(ext) for ext in extensions):
                        files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory):
                if any(filename.lower().endswith(ext) for ext in extensions):
                    files.append(os.path.join(directory, filename))
        
        return sorted(files)
    
    @staticmethod
    def get_file_hash(file_path):
        """获取文件哈希值（用于检测文件变化）"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None
    
    @staticmethod
    def load_config(config_path):
        """加载YAML配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"加载配置文件失败 {config_path}: {e}")
            # 返回默认配置
            return {
                'paths': {
                    'input_dir': './html_conversations',
                    'output_dir': './knowledge_base',
                    'failed_dir': './failed'
                }
            }
    
    @staticmethod
    def save_json(data, file_path):
        """保存JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存JSON文件失败 {file_path}: {e}")
            return False
    
    @staticmethod
    def backup_file(file_path):
        """备份文件（添加时间戳）"""
        if not os.path.exists(file_path):
            return file_path
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(file_path)
        backup_path = f"{base}_{timestamp}{ext}"
        
        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"备份文件失败 {file_path}: {e}")
            return file_path
    
    @staticmethod
    def get_safe_filename(filename, max_length=100):
        """获取安全的文件名（去除特殊字符）"""
        # 保留字母、数字、中文、下划线、点、连字符
        import re
        safe_name = re.sub(r'[^\w\u4e00-\u9fff\-\.]', '_', filename)
        
        # 限制长度
        if len(safe_name) > max_length:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:max_length - len(ext)] + ext
        
        return safe_name
    
    @staticmethod
    def generate_output_filename(conversation_data, base_dir, extension='.md'):
        """根据对话数据生成输出文件名"""
        dialog_id = conversation_data.get('metadata', {}).get('dialog_id', 'unknown')
        title_keywords = conversation_data.get('metadata', {}).get('title_keywords', 'conversation')
        
        # 生成文件名
        safe_keywords = FileOperations.get_safe_filename(title_keywords, 50)
        filename = f"{dialog_id}_{safe_keywords}{extension}"
        
        # 确保不重名
        counter = 1
        base_name = filename
        while os.path.exists(os.path.join(base_dir, filename)):
            name, ext = os.path.splitext(base_name)
            filename = f"{name}_{counter}{ext}"
            counter += 1
        
        return filename