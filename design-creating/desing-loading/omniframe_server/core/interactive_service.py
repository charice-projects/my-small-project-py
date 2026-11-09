"""
命令处理API - 增强版，支持会话管理
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid

from utils.logger import logger
from core.intent_parser import IntentParser
from core.enhanced_task_dispatcher import EnhancedTaskDispatcher, get_enhanced_task_dispatcher
from core.context_manager import ContextManager

router = APIRouter()
intent_parser = IntentParser()
context_manager = ContextManager()


class CommandRequest(BaseModel):
    command: str
    session_id: Optional[str] = None


class CommandResponse(BaseModel):
    success: bool
    action: str
    message: str
    data: Optional[Any] = None
    parameters: Optional[Dict] = None
    interactive: Optional[bool] = False
    requires_followup: Optional[bool] = False
    session_id: Optional[str] = None


@router.post("/execute", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """执行命令"""
    try:
        # 生成或使用提供的会话ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # 获取上下文
        context = context_manager.get_context(session_id)
        
        # 解析意图
        intent = intent_parser.parse(request.command, context)
        
        if not intent.get("success", False):
            return CommandResponse(
                success=False,
                action=intent.get("action", "unknown"),
                message=intent.get("message", "命令解析失败"),
                session_id=session_id
            )
        
        # 获取任务分发器
        dispatcher = await get_enhanced_task_dispatcher()
        
        # 添加会话ID到intent
        intent["session_id"] = session_id
        
        # 执行任务
        result = await dispatcher.dispatch(intent, session_id)
        
        # 保存命令历史
        context_manager.add_command_history(
            session_id,
            request.command,
            intent.get("action"),
            result.get("success", False),
            result.get("message", "")
        )
        
        # 构建响应
        response_data = {
            "success": result.get("success", False),
            "action": result.get("action", intent.get("action")),
            "message": result.get("message", ""),
            "data": result.get("data", []),
            "parameters": result.get("parameters", {}),
            "session_id": session_id
        }
        
        # 添加交互式相关字段
        if result.get("interactive"):
            response_data["interactive"] = True
            response_data["requires_followup"] = result.get("requires_followup", False)
        
        return CommandResponse(**response_data)
    
    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"命令执行失败: {str(e)}")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，支持实时交互"""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    try:
        # 初始化上下文
        context_manager.initialize_session(session_id)
        
        while True:
            # 接收命令
            data = await websocket.receive_json()
            command = data.get("command", "")
            
            if not command:
                await websocket.send_json({
                    "success": False,
                    "message": "命令不能为空"
                })
                continue
            
            # 处理命令
            request = CommandRequest(command=command, session_id=session_id)
            response = await execute_command(request)
            
            # 发送响应
            await websocket.send_json(response.dict())
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket处理错误: {e}")
        await websocket.send_json({
            "success": False,
            "message": f"处理错误: {str(e)}",
            "session_id": session_id
        })
