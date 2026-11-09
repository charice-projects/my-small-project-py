"""
Omniframe Server - 主服务器文件
"""
import asyncio
import sys
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from config.settings import settings
from utils.logger import logger, setup_logger
from utils.path_utils import PathUtils

# 导入API路由
from api.commands import router as commands_router
from api.files import router as files_router
from api.websocket import websocket_endpoint

# 导入服务
from services.monitor_service import MonitorService

# 引入版本管理
from core.version_manager import VersionManager
version_manager = VersionManager()


def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# 生命周期管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 Omniframe Server Opening...")
    
    # 创建必要目录
    data_dir = PathUtils.get_data_dir()
    logs_dir = PathUtils.get_logs_dir()
    
    logger.info(f"工作空间: {settings.root_path}")
    logger.info(f"数据目录: {data_dir}")
    logger.info(f"日志目录: {logs_dir}")
    
    # 启动文件监控服务
    monitor_service = MonitorService()
    app.state.monitor_service = monitor_service
    
    yield
    
    # 关闭时
    logger.info("🛑 Omniframe Server Closed...")
    
    if hasattr(app.state, 'monitor_service'):
        monitor_service = app.state.monitor_service
        monitor_service.stop()
    
    logger.info("服务已安全关闭")


# 创建FastAPI应用
app = FastAPI(
    title="Omniframe Server",
    description="智能文件协同服务器",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板引擎
templates = Jinja2Templates(directory="static")

# 注册路由
app.include_router(commands_router)
app.include_router(files_router)


# 中间件：请求日志
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    # 记录请求基本信息
    logger.info(f"请求: {request.method} {request.url.path}")
    
    # 只记录POST请求的简要信息
    if request.method == "POST":
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            # 复制请求体，以便记录
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_str = body_bytes.decode('utf-8')[:200]  # 只记录前200字符
                    logger.info(f"JSON请求体: {body_str}")
                except:
                    logger.info(f"请求体长度: {len(body_bytes)} 字节")
            
            # 由于已经消耗了body，需要重新设置
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
    
    response = await call_next(request)
    
    logger.info(f"响应: {response.status_code}")
    return response


# 根路由
@app.get("/")
async def root(request: Request):
    """返回前端页面"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Omniframe Server",
            "version": "1.0.0",
            "root_path": settings.root_path
        }
    )


# WebSocket路由
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


# 健康检查
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "Omniframe Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "workspace": settings.root_path,
        "debug": settings.debug
    }


# 系统信息
@app.get("/system/info")
async def system_info() -> Dict[str, Any]:
    """获取系统信息"""
    import platform
    import psutil
    
    return {
        "status": "success",
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "processor": platform.processor()
        },
        "resources": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage(settings.root_path)._asdict()
        },
        "service": {
            "host": settings.host,
            "port": settings.port,
            "root_path": settings.root_path,
            "safe_mode": settings.safe_mode,
            "constitution_enabled": settings.constitution_enabled
        },
        "timestamp": datetime.now().isoformat()
    }


# 上下文状态重定向（保持向前端兼容）
@app.get("/api/context/status")
async def context_status():
    """重定向到 /api/commands/context/status"""
    from api.commands import get_context_status
    return await get_context_status()


# 错误处理
@app.exception_handler(404)
async def not_found(request: Request, exc):
    """404错误处理"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "资源未找到",
            "path": request.url.path
        }
    )


@app.exception_handler(500)
async def server_error(request: Request, exc):
    """500错误处理"""
    logger.error(f"服务器错误: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "内部服务器错误",
            "message": str(exc) if settings.debug else "请查看服务器日志"
        }
    )


# 启动函数
def run_server():
    """启动服务器"""
    try:
        # 设置日志
        setup_logger()
        
        local_ip = get_local_ip()
        host = settings.host
        
        # 打印启动信息
        print("\n" + "="*50)
        print("🚀 Omniframe Server")
        print("="*50)
        print(f"工作空间: {settings.root_path}")
        
        if host == "0.0.0.0":
            print(f"本地访问: http://localhost:{settings.port}")
            print(f"网络访问: http://{local_ip}:{settings.port}")
        else:
            print(f"访问地址: http://{host}:{settings.port}")
            
        print(f"API文档: http://{host}:{settings.port}/docs")
        print(f"调试模式: {settings.debug}")
        print(f"安全模式: {settings.safe_mode}")
        print(f"宪法引擎: {'启用' if settings.constitution_enabled else '禁用'}")
        print("="*50 + "\n")
        
        # 启动服务器
        uvicorn.run(
            "server:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info" if settings.debug else "warning",
            access_log=True
        )
    
    except KeyboardInterrupt:
        print("\n服务器被用户中断")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        print(f"错误: {e}")
        sys.exit(1)


# 命令行接口
if __name__ == "__main__":
    run_server()