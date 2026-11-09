"""
配置文件管理
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    """应用配置"""
    
    # 服务器配置
    host: str = "127.0.0.1"
    port: int = 8080
    root_path: str = str(Path.home() / "OmniFrame_Workspace")
    debug: bool = False
    
    # 安全配置
    secret_key: str = "development-secret-key-change-in-production"
    enable_auth: bool = False
    allowed_ips: List[str] = ["127.0.0.1", "::1"]
    
    # 索引配置
    index_auto_update: bool = True
    index_update_interval: int = 300  # 秒
    index_exclude_patterns: List[str] = [
        "*.pyc", "*.pyo", "*.exe", "*.dll", "*.so", "*.dylib",
        "__pycache__", ".git", ".idea", ".vscode", "node_modules",
        "*.log", "*.tmp", "*.temp", "thumbs.db", ".DS_Store"
    ]
    
    # 文件操作限制
    max_file_size: int = 1024 * 1024 * 100  # 100MB
    max_upload_size: int = 1024 * 1024 * 500  # 500MB
    allow_delete: bool = True
    allow_overwrite: bool = False
    
    # 宪法规则
    constitution_enabled: bool = True
    constitution_path: str = "config/constitution.yaml"
    safe_mode: bool = True
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/omniframe.log"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 上下文配置
    context_enabled: bool = True
    context_history_size: int = 100
    context_auto_save: bool = True
    
    @validator("root_path")
    def validate_root_path(cls, v):
        """验证根路径"""
        path = Path(v)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"Created workspace directory: {path}")
        return str(path.absolute())
    
    @validator("allowed_ips")
    def parse_allowed_ips(cls, v):
        """解析允许的IP列表"""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_prefix = "omniframe_"

# 全局配置实例
settings = Settings()

def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent

def get_data_dir() -> Path:
    """获取数据目录"""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_logs_dir() -> Path:
    """获取日志目录"""
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir