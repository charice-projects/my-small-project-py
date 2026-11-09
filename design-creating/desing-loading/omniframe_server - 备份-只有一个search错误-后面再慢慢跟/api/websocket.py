"""
WebSocket支持 - 实时通信（预留功能）
"""
import asyncio
import json
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from config.settings import settings
from utils.logger import logger
from core.task_dispatcher import task_dispatcher


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket连接已关闭，剩余连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    await manager.connect(websocket)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type", "command")
                
                if message_type == "command":
                    # 处理命令
                    command = message.get("command", "")
                    if command:
                        # 这里可以集成实时命令处理
                        response = {
                            "type": "response",
                            "timestamp": asyncio.get_event_loop().time(),
                            "data": {"received": command}
                        }
                        await manager.send_personal_message(
                            json.dumps(response), websocket
                        )
                
                elif message_type == "ping":
                    # 心跳响应
                    await manager.send_personal_message(
                        json.dumps({"type": "pong"}), websocket
                    )
            
            except json.JSONDecodeError:
                logger.error("WebSocket消息JSON解析失败")
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": "消息格式错误"}), websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)