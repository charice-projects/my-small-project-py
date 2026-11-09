"""
命令处理API - 处理自然语言命令
"""
import time
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
from core.intent_parser import IntentParser
from core.file_indexer import FileIndexer
from core.context_manager import ContextManager
from core.constitution_engine import ConstitutionEngine
from core.task_dispatcher import TaskDispatcher
from services.file_service import FileService
from services.search_service import SearchService
from services.archive_service import ArchiveService

router = APIRouter(prefix="/api/commands", tags=["commands"])

# 全局服务实例
intent_parser = IntentParser()
context_manager = ContextManager()
constitution_engine = ConstitutionEngine()
file_indexer = FileIndexer()
task_dispatcher = TaskDispatcher()

file_service = FileService(constitution_engine)
search_service = SearchService(file_service)
archive_service = ArchiveService(constitution_engine)


@router.post("/execute", response_model=Dict[str, Any])
async def execute_command(
    request_data: Dict[str, Any] = Body(...)
):
    """执行自然语言命令"""
    start_time = time.time()
    
    # 从请求体中提取字段
    command = request_data.get("command", "")
    session_id = request_data.get("session_id")
    auto_index = request_data.get("auto_index", True)
    
    logger.info(f"收到命令执行请求: {command}")
    logger.info(f"请求数据: {request_data}")
    
    try:
        logger.info(f"执行命令: {command}")
        
        # 1. 解析意图
        intent = intent_parser.parse(command)
        logger.debug(f"意图解析结果: {intent}")
        
        if not intent.get("success", False):
            error_msg = intent.get("message", "无法理解命令")
            logger.error(f"意图解析失败: {error_msg}, intent: {intent}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 2. 获取或验证索引
        if auto_index and intent.get("action") in ["list", "search", "find", "locate"]:
            index_status = file_indexer.get_index_status()
            if not index_status.get("has_index", False):
                logger.info("未找到索引，正在生成...")
                file_indexer.generate_index()
        
        # 3. 检查宪法规则
        operation = {
            "action": intent.get("action", "unknown"),
            "target_path": intent.get("target", ""),
            "parameters": intent.get("parameters", {}),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        evaluation = constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "操作被宪法规则阻止",
                    "violations": evaluation.get("violations", []),
                    "requires_confirmation": evaluation.get("requires_confirmation", False)
                }
            )
        
        # 4. 需要确认的操作
        if evaluation["requires_confirmation"]:
            return {
                "success": True,
                "requires_confirmation": True,
                "confirmations": evaluation.get("confirmations", []),
                "intent": intent,
                "execution_time": time.time() - start_time
            }
        
        # 5. 分发和执行任务
        result = await task_dispatcher.dispatch(intent)
        
        # 6. 更新上下文
        context_manager.add_command_to_history(command, intent, result)
        
        # 7. 记录文件访问（如果适用）
        if intent.get("action") in ["read", "write", "open", "edit"]:
            target = intent.get("target", "")
            if target:
                context_manager.add_file_access(target, intent["action"], result["success"])
        
        # 8. 返回结果
        result["execution_time"] = time.time() - start_time
        result["session_id"] = session_id or context_manager.context.get("session_id")
        
        logger.info(f"命令执行完成: {command} (耗时: {result['execution_time']:.2f}s)")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"命令执行失败: {command} - {e}")
        raise HTTPException(status_code=500, detail=f"命令执行失败: {str(e)}")



@router.get("/history", response_model=Dict[str, Any])
async def get_command_history(
    limit: int = Query(50, ge=1, le=1000),
    action: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None)
):
    """获取命令历史"""
    try:
        history = context_manager.get_command_history(limit=limit, filter_action=action)
        
        # 如果提供了session_id，过滤该会话的历史
        if session_id:
            history = [h for h in history if h.get("context_snapshot", {}).get("session_id") == session_id]
        
        return {
            "success": True,
            "total": len(history),
            "history": history,
            "session_id": session_id or context_manager.context.get("session_id"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    except Exception as e:
        logger.error(f"获取命令历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.post("/index/generate", response_model=Dict[str, Any])
async def generate_index(
    force: bool = Body(False),
    incremental: bool = Body(True)
):
    """生成或更新索引"""
    try:
        result = file_indexer.generate_index(force=force, incremental=incremental)
        
        # 更新上下文
        context_manager.update_context({
            "system_state": {
                "last_index_time": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
        })
        
        return {
            "success": True,
            "message": "索引生成完成",
            "result": result,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    except Exception as e:
        logger.error(f"生成索引失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成索引失败: {str(e)}")


@router.get("/index/status", response_model=Dict[str, Any])
async def get_index_status():
    """获取索引状态"""
    try:
        status = file_indexer.get_index_status()
        return {
            "success": True,
            "status": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    except Exception as e:
        logger.error(f"获取索引状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取索引状态失败: {str(e)}")


@router.post("/context/update", response_model=Dict[str, Any])
async def update_context(
    updates: Dict[str, Any] = Body(...)
):
    """更新上下文"""
    try:
        context_manager.update_context(updates)
        
        return {
            "success": True,
            "message": "上下文已更新",
            "session_id": context_manager.context.get("session_id"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    except Exception as e:
        logger.error(f"更新上下文失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新上下文失败: {str(e)}")


@router.get("/context/status", response_model=Dict[str, Any])
async def get_context_status():
    """获取上下文状态"""
    try:
        stats = context_manager.get_statistics()
        recent_files = context_manager.get_recent_files(limit=20)
        
        return {
            "success": True,
            "statistics": stats,
            "recent_files": recent_files,
            "session_id": context_manager.context.get("session_id"),
            "session_duration": stats.get("session_duration", "未知"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    except Exception as e:
        logger.error(f"获取上下文状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取上下文状态失败: {str(e)}")


@router.get("/constitution/rules", response_model=Dict[str, Any])
async def get_constitution_rules():
    """获取宪法规则"""
    try:
        summary = constitution_engine.get_rule_summary()
        
        return {
            "success": True,
            "rules_summary": summary,
            "enabled": settings.constitution_enabled,
            "safe_mode": settings.safe_mode,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    except Exception as e:
        logger.error(f"获取宪法规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取宪法规则失败: {str(e)}")


@router.post("/suggest", response_model=Dict[str, Any])
async def get_suggestions(
    partial_command: str = Body(...),
    context: Optional[Dict[str, Any]] = Body(None)
):
    """获取命令建议"""
    try:
        # 基于历史记录和模式提供建议
        history = context_manager.get_command_history(limit=100)
        
        suggestions = []
        
        # 1. 从历史记录中寻找相似命令
        for entry in history:
            cmd = entry.get("command", "")
            if partial_command.lower() in cmd.lower():
                suggestions.append({
                    "type": "history",
                    "command": cmd,
                    "last_used": entry.get("timestamp"),
                    "success_rate": entry.get("result", {}).get("success", False)
                })
        
        # 2. 基于意图模式提供建议
        intent_patterns = context_manager.context.get("intent_patterns", {})
        for intent_type, patterns in intent_patterns.items():
            for pattern in patterns[:5]:  # 每种意图取前5个模式
                if pattern.get("success_rate", 0) > 0.7:  # 成功率70%以上
                    suggestions.append({
                        "type": "pattern",
                        "intent": intent_type,
                        "pattern": pattern.get("pattern", ""),
                        "success_rate": pattern.get("success_rate", 0),
                        "use_count": pattern.get("use_count", 0)
                    })
        
        # 3. 常见命令模板
        common_commands = [
            "初始化索引",
            "列出所有文件",
            "搜索文档",
            "查找图片",
            "打包下载",
            "查看最近文件",
            "显示系统状态"
        ]
        
        for cmd in common_commands:
            if partial_command.lower() in cmd.lower():
                suggestions.append({
                    "type": "template",
                    "command": cmd,
                    "description": "常见命令模板"
                })
        
        # 去重和排序
        unique_suggestions = []
        seen = set()
        
        for s in suggestions:
            key = s.get("command") or s.get("pattern") or ""
            if key and key not in seen:
                seen.add(key)
                unique_suggestions.append(s)
        
        # 排序：历史记录优先，然后按成功率排序
        unique_suggestions.sort(key=lambda x: (
            0 if x["type"] == "history" else (1 if x["type"] == "pattern" else 2),
            x.get("success_rate", 0) if x["type"] == "pattern" else 0,
            x.get("last_used", "") if x["type"] == "history" else ""
        ), reverse=True)
        
        return {
            "success": True,
            "suggestions": unique_suggestions[:10],  # 返回前10个建议
            "total_found": len(unique_suggestions),
            "partial_command": partial_command,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    except Exception as e:
        logger.error(f"获取建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取建议失败: {str(e)}")


@router.post("/confirm", response_model=Dict[str, Any])
async def confirm_operation(
    confirmation_id: str = Body(...),
    confirmed: bool = Body(True),
    session_id: Optional[str] = Body(None)
):
    """确认操作"""
    try:
        # 这里简化处理，实际应该跟踪待确认的操作
        if confirmed:
            return {
                "success": True,
                "message": "操作已确认",
                "confirmed": True,
                "session_id": session_id or context_manager.context.get("session_id"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
        else:
            return {
                "success": True,
                "message": "操作已取消",
                "confirmed": False,
                "session_id": session_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
    
    except Exception as e:
        logger.error(f"确认操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"确认操作失败: {str(e)}")