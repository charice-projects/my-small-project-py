"""
utils/logger.py
日志记录模块
"""
import logging
import sys
import os
from datetime import datetime
from colorama import init, Fore, Style

# 初始化colorama
init(autoreset=True)


class ColorFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }
    
    def format(self, record):
        # 添加颜色
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


class ParserLogger:
    """解析器专用日志记录器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger('deepseek_parser')
        self._setup_logger()
    
    def _setup_logger(self):
        """配置日志记录器"""
        # 设置日志级别
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        self.logger.setLevel(getattr(logging, log_level))
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColorFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器（如果配置了日志文件）
        log_file = self.config.get('logging', {}).get('file')
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            file_handler = logging.FileHandler(
                log_file,
                encoding='utf-8'
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, msg, *args, **kwargs):
        """调试日志"""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        """信息日志"""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        """警告日志"""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        """错误日志"""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """严重错误日志"""
        self.logger.critical(msg, *args, **kwargs)
    
    def progress(self, current, total, msg=""):
        """进度日志"""
        percentage = (current / total) * 100 if total > 0 else 0
        progress_bar = self._create_progress_bar(percentage)
        sys.stdout.write(f"\r{progress_bar} {percentage:.1f}% - {msg}")
        sys.stdout.flush()
        
        if current >= total:
            print()  # 完成时换行
    
    def _create_progress_bar(self, percentage, length=30):
        """创建进度条"""
        filled_length = int(length * percentage // 100)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return f"[{bar}]"


def get_logger(config=None):
    """获取日志记录器实例"""
    return ParserLogger(config)


# 全局日志记录器
logger = get_logger()