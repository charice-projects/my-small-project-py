# api/v1/router.py
"""
API V1 路由 - 提供版本化的API接口
"""
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.intent_parser_v2 import IntentParserV2, ParsedIntent
from core.task_dispatcher_v2 import TaskDispatcherV2, TaskResult
from utils.logger import logger
from utils.rate_limiter import RateLimiter


# 请求/响应模型
class CommandRequest(BaseModel):
    """命令请求模型"""
    command: str = Field(..., min_length=1, max_length=1000, description="自然语言命令")
    session_id: Optional[str] = Field(None, description="会话ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "command": "search test",
                "session_id": "session_123",
                "context": {"current_path": "/home/user"}
            }
        }


class CommandResponse(BaseModel):
    """命令响应模型"""
    success: bool = Field(..., description="是否成功")
    action: str = Field(..., description="执行的动作")
    data: Optional[Any] = Field(None, description="返回数据")
    message: str = Field(..., description="消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    suggestions: Optional[list[str]] = Field(None, description="建议")
    execution_time: float = Field(..., description="执行时间")
    timestamp: str = Field(..., description="时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "action": "search",
                "data": [{"name": "test.txt", "path": "/home/user/test.txt"}],
                "message": "搜索完成",
                "error_code": None,
                "suggestions": ["试试: search document", "试试: find image"],
                "execution_time": 0.123,
                "timestamp": "2024-01-01T00:00:00.000000"
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="状态")
    version: str = Field(..., description="版本")
    uptime: float = Field(..., description="运行时间")
    services: Dict[str, bool] = Field(..., description="服务状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime": 12345.6,
                "services": {
                    "intent_parser": True,
                    "task_dispatcher": True,
                    "file_service": True
                }
            }
        }


# 创建路由器
router = APIRouter(
    prefix="/api/v1",
    tags=["commands"],
    responses={
        400: {"description": "请求参数错误"},
        429: {"description": "请求过于频繁"},
        500: {"description": "服务器内部错误"}
    }
)

# 初始化组件
intent_parser = IntentParserV2()
task_dispatcher = TaskDispatcherV2()
rate_limiter = RateLimiter(max_requests=100, time_window=60)

# 系统启动时间
start_time = datetime.now()


async def get_session_context(session_id: Optional[str] = None) -> Dict[str, Any]:
    """获取会话上下文"""
    if session_id:
        # 这里应该从数据库或缓存中获取上下文
        return {"session_id": session_id, "current_path": "."}
    else:
        # 创建新会话
        import uuid
        new_session_id = str(uuid.uuid4())
        return {
            "session_id": new_session_id,
            "current_path": ".",
            "created_at": datetime.now().isoformat()
        }


def format_error_response(error: Exception, status_code: int = 500) -> JSONResponse:
    """格式化错误响应"""
    error_info = {
        "success": False,
        "error": str(error),
        "error_type": error.__class__.__name__,
        "timestamp": datetime.now().isoformat()
    }
    
    # 开发环境下包含堆栈跟踪
    import os
    if os.getenv("DEBUG", "false").lower() == "true":
        error_info["traceback"] = traceback.format_exc()
    
    return JSONResponse(
        content=error_info,
        status_code=status_code
    )


@router.post("/commands/execute", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    background_tasks: BackgroundTasks,
    context: Dict[str, Any] = Depends(get_session_context)
):
    """
    执行自然语言命令
    
    - **command**: 自然语言命令，如 "search test" 或 "显示文件"
    - **session_id**: 可选的会话ID，用于保持上下文
    - **context**: 可选的上下文信息
    
    返回解析和执行结果
    """
    start_execution = datetime.now()
    
    try:
        # 速率限制检查
        client_ip = "127.0.0.1"  # 实际应用中从请求中获取
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试"
            )
        
        logger.info(f"执行命令: {request.command}, 会话: {context.get('session_id')}")
        
        # 1. 解析意图
        parsed_intent = intent_parser.parse(request.command)
        
        if not parsed_intent.success:
            # 解析失败
            execution_time = (datetime.now() - start_execution).total_seconds()
            
            return CommandResponse(
                success=False,
                action="unknown",
                data=None,
                message=parsed_intent.get("message", "解析失败"),
                error_code="INTENT_PARSE_ERROR",
                suggestions=parsed_intent.get("suggestions", []),
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )
        
        # 2. 合并上下文
        intent_with_context = parsed_intent.to_dict()
        if context:
            intent_with_context["context"] = context
        
        # 3. 分发和执行任务
        task_result = await task_dispatcher.dispatch(intent_with_context)
        
        # 4. 记录执行历史（后台任务）
        background_tasks.add_task(
            _record_execution_history,
            request.command,
            intent_with_context,
            task_result,
            context.get("session_id")
        )
        
        execution_time = (datetime.now() - start_execution).total_seconds()
        
        # 5. 构建响应
        response_data = CommandResponse(
            success=task_result.success,
            action=task_result.action,
            data=task_result.data,
            message=task_result.message,
            error_code=task_result.error_code,
            suggestions=task_result.suggestions,
            execution_time=execution_time,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"命令执行完成: {request.command}, "
                   f"耗时: {execution_time:.3f}s, "
                   f"成功: {task_result.success}")
        
        return response_data
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"命令执行异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    系统健康检查
    
    返回系统状态和服务健康状况
    """
    try:
        # 检查各个服务
        services_status = {
            "intent_parser": _check_intent_parser(),
            "task_dispatcher": _check_task_dispatcher(),
            "file_service": _check_file_service(),
            "database": _check_database(),
            "cache": _check_cache()
        }
        
        # 计算运行时间
        uptime = (datetime.now() - start_time).total_seconds()
        
        # 确定整体状态
        all_healthy = all(services_status.values())
        status = "healthy" if all_healthy else "degraded"
        
        return HealthResponse(
            status=status,
            version="1.0.0",
            uptime=uptime,
            services=services_status
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            uptime=(datetime.now() - start_time).total_seconds(),
            services={}
        )


@router.get("/commands/suggestions")
async def get_command_suggestions(
    query: str,
    limit: int = 5
):
    """
    获取命令建议
    
    - **query**: 部分命令或搜索词
    - **limit**: 返回的建议数量
    
    返回可能的命令建议
    """
    try:
        suggestions = []
        
        # 从搜索服务获取搜索建议
        from services.search_service_v2 import SearchServiceV2
        search_service = SearchServiceV2(None)  # 需要实际初始化
        search_suggestions = await search_service.get_suggestions(query)
        suggestions.extend(search_suggestions)
        
        # 添加常见命令
        common_commands = [
            "show status",
            "list files",
            "search [关键词]",
            "index",
            "recent",
            "history",
            "tree"
        ]
        
        for cmd in common_commands:
            if query.lower() in cmd.lower():
                suggestions.append(cmd)
        
        # 去重并限制数量
        unique_suggestions = []
        seen = set()
        
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
                
            if len(unique_suggestions) >= limit:
                break
        
        return {
            "success": True,
            "query": query,
            "suggestions": unique_suggestions,
            "count": len(unique_suggestions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取建议失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "suggestions": [],
            "timestamp": datetime.now().isoformat()
        }


@router.get("/commands/history")
async def get_command_history(
    session_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    获取命令历史
    
    - **session_id**: 会话ID（可选）
    - **limit**: 返回的历史记录数量
    - **offset**: 偏移量
    
    返回命令执行历史
    """
    try:
        # 这里应该从数据库或缓存中获取历史记录
        # 暂时返回示例数据
        example_history = [
            {
                "command": "show status",
                "action": "system_info",
                "success": True,
                "execution_time": 0.123,
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "command": "search test",
                "action": "search",
                "success": True,
                "execution_time": 0.456,
                "timestamp": "2024-01-01T10:01:00"
            }
        ]
        
        return {
            "success": True,
            "history": example_history,
            "count": len(example_history),
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "history": [],
            "timestamp": datetime.now().isoformat()
        }


# 辅助函数
async def _record_execution_history(
    command: str,
    intent: Dict[str, Any],
    result: TaskResult,
    session_id: Optional[str]
):
    """记录执行历史"""
    try:
        history_entry = {
            "command": command,
            "action": result.action,
            "success": result.success,
            "execution_time": result.execution_time,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "parameters": intent.get("parameters", {}),
            "error_code": result.error_code
        }
        
        # 这里应该将历史记录保存到数据库
        logger.debug(f"记录执行历史: {history_entry}")
        
    except Exception as e:
        logger.error(f"记录执行历史失败: {e}")


def _check_intent_parser() -> bool:
    """检查意图解析器"""
    try:
        test_command = "show status"
        result = intent_parser.parse(test_command)
        return result.success and result.action == "system_info"
    except Exception as e:
        logger.error(f"意图解析器检查失败: {e}")
        return False


def _check_task_dispatcher() -> bool:
    """检查任务分发器"""
    try:
        # 简单的检查
        return len(task_dispatcher.handlers) > 0
    except Exception as e:
        logger.error(f"任务分发器检查失败: {e}")
        return False


def _check_file_service() -> bool:
    """检查文件服务"""
    try:
        # 检查根目录是否存在
        from config.settings import settings
        import os
        return os.path.exists(settings.root_path)
    except Exception as e:
        logger.error(f"文件服务检查失败: {e}")
        return False


def _check_database() -> bool:
    """检查数据库"""
    # 如果没有使用数据库，返回True
    return True


def _check_cache() -> bool:
    """检查缓存"""
    # 简单的缓存检查
    return True