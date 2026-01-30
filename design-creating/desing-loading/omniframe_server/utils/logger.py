"""
日志配置模块
"""
import logging
import sys
import io

from pathlib import Path
from typing import Optional

from config.settings import settings, get_logs_dir

def setup_logger(name: str = "omniframe", log_file: Optional[str] = None) -> logging.Logger:
    """配置并返回一个日志记录器"""
    
    # 创建日志目录
    logs_dir = get_logs_dir()
    
    # 如果未指定日志文件，则使用配置中的日志文件
    if log_file is None:
        log_file = settings.log_file
    
    if log_file:
        log_file_path = Path(log_file)
        if not log_file_path.is_absolute():
            log_file_path = logs_dir / log_file_path
        # 确保日志文件所在目录存在
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(settings.log_format)
    
    
    # 创建一个支持UTF-8的流
    try:
        # 对于Windows，尝试设置控制台编码
        if sys.platform == "win32":
            import win_unicode_console
            win_unicode_console.enable()
    except:
        pass
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.encoding = 'utf-8'  # 设置编码
    logger.addHandler(console_handler)
    
    # 文件处理器（如果配置了日志文件）
    if log_file:
        # 确保使用UTF-8编码
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# 全局日志记录器
logger = setup_logger()