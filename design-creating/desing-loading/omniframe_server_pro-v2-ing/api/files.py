"""
文件操作API - 提供传统的文件操作接口
"""
import os
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Body, File, UploadFile, Form
from fastapi.responses import FileResponse, StreamingResponse

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
from core.constitution_engine import ConstitutionEngine
from services.file_service import FileService
from services.search_service import SearchService
from services.archive_service import ArchiveService

router = APIRouter(prefix="/api/files", tags=["files"])

# 全局服务实例
constitution_engine = ConstitutionEngine()
file_service = FileService(constitution_engine)
search_service = SearchService(file_service)
archive_service = ArchiveService(constitution_engine)


@router.get("/list", response_model=Dict[str, Any])
async def list_files(
    path: Optional[str] = Query(None),
    recursive: bool = Query(False),
    include_hidden: bool = Query(False),
    sort_by: str = Query("name"),
    order: str = Query("asc")
):
    """列出目录内容"""
    try:
        target_path = path if path else settings.root_path
        items = file_service.list_directory(
            target_path, 
            recursive=recursive, 
            include_hidden=include_hidden
        )
        
        # 排序
        reverse = order.lower() == "desc"
        
        if sort_by == "name":
            items.sort(key=lambda x: x["name"].lower(), reverse=reverse)
        elif sort_by == "size":
            items.sort(key=lambda x: x["size"], reverse=reverse)
        elif sort_by == "modified":
            items.sort(key=lambda x: x["modified"], reverse=reverse)
        
        return {
            "success": True,
            "path": target_path,
            "total": len(items),
            "items": items,
            "recursive": recursive,
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(target_path))
        }
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"列出文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")


@router.get("/download")
async def download_file(
    path: str = Query(...),
    as_attachment: bool = Query(True)
):
    """下载文件"""
    try:
        file_path = PathUtils.normalize_path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="不是文件")
        
        # 检查宪法规则
        operation = {
            "action": "download",
            "target_path": str(file_path),
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(file_path)))
        }
        
        evaluation = constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise HTTPException(
                status_code=403, 
                detail=f"下载被阻止: {evaluation.get('violations', [])}"
            )
        
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"{'attachment' if as_attachment else 'inline'}; "
                                      f"filename=\"{file_path.name}\""
            } if as_attachment else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")


@router.post("/upload", response_model=Dict[str, Any])
async def upload_files(
    path: str = Form(...),
    files: List[UploadFile] = File(...),
    overwrite: bool = Form(False)
):
    """上传文件"""
    try:
        target_dir = PathUtils.normalize_path(path)
        
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail="目标目录不存在")
        
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="目标路径不是目录")
        
        uploaded_files = []
        failed_files = []
        
        for upload_file in files:
            try:
                file_path = target_dir / upload_file.filename
                
                # 检查宪法规则
                operation = {
                    "action": "upload",
                    "target_path": str(file_path),
                    "overwrite": overwrite,
                    "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(target_dir)))
                }
                
                evaluation = constitution_engine.evaluate_operation(operation)
                if not evaluation["allowed"]:
                    failed_files.append({
                        "filename": upload_file.filename,
                        "error": "上传被宪法规则阻止",
                        "violations": evaluation.get("violations", [])
                    })
                    continue
                
                # 检查文件是否已存在
                if file_path.exists() and not overwrite:
                    failed_files.append({
                        "filename": upload_file.filename,
                        "error": "文件已存在"
                    })
                    continue
                
                # 写入文件
                content = await upload_file.read()
                
                with open(file_path, "wb") as f:
                    f.write(content)
                
                uploaded_files.append({
                    "filename": upload_file.filename,
                    "path": str(file_path),
                    "size": len(content),
                    "size_human": PathUtils.humanize_size(len(content))
                })
                
                logger.info(f"文件上传成功: {upload_file.filename}")
            
            except Exception as e:
                failed_files.append({
                    "filename": upload_file.filename,
                    "error": str(e)
                })
                logger.error(f"上传文件失败 {upload_file.filename}: {e}")
        
        return {
            "success": True,
            "message": f"上传完成，成功 {len(uploaded_files)} 个，失败 {len(failed_files)} 个",
            "uploaded_files": uploaded_files,
            "failed_files": failed_files,
            "total": len(files),
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(target_dir)))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@router.get("/info", response_model=Dict[str, Any])
async def get_file_info(
    path: str = Query(...)
):
    """获取文件信息"""
    try:
        file_path = PathUtils.normalize_path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        info = PathUtils.get_file_info(file_path)
        
        return {
            "success": True,
            "info": info,
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(file_path)))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")


@router.post("/create", response_model=Dict[str, Any])
async def create_file_or_dir(
    path: str = Body(...),
    type: str = Body("file"),  # "file" 或 "directory"
    content: Optional[str] = Body(None)
):
    """创建文件或目录"""
    try:
        target_path = PathUtils.normalize_path(path)
        
        # 检查宪法规则
        operation = {
            "action": "create",
            "target_path": str(target_path),
            "type": type,
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(target_path.parent)))
        }
        
        evaluation = constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise HTTPException(
                status_code=403, 
                detail=f"创建被阻止: {evaluation.get('violations', [])}"
            )
        
        if type == "directory":
            success = file_service.create_directory(target_path)
            message = "目录创建成功"
        else:
            success = file_service.write_file(target_path, content or "", overwrite=False)
            message = "文件创建成功"
        
        if success:
            return {
                "success": True,
                "message": message,
                "path": str(target_path),
                "type": type,
                "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(target_path)))
            }
        else:
            raise HTTPException(status_code=500, detail="创建失败")
    
    except HTTPException:
        raise
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"创建失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/write", response_model=Dict[str, Any])
async def write_file_content(
    path: str = Body(...),
    content: str = Body(...),
    encoding: str = Body("utf-8"),
    overwrite: bool = Body(True)
):
    """写入文件内容"""
    try:
        file_path = PathUtils.normalize_path(path)
        
        # 检查宪法规则
        operation = {
            "action": "write",
            "target_path": str(file_path),
            "overwrite": overwrite,
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(file_path)))
        }
        
        evaluation = constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise HTTPException(
                status_code=403, 
                detail=f"写入被阻止: {evaluation.get('violations', [])}"
            )
        
        success = file_service.write_file(file_path, content, encoding, overwrite)
        
        if success:
            return {
                "success": True,
                "message": "文件写入成功",
                "path": str(file_path),
                "size": len(content),
                "size_human": PathUtils.humanize_size(len(content)),
                "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(file_path)))
            }
        else:
            raise HTTPException(status_code=500, detail="写入失败")
    
    except HTTPException:
        raise
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"写入文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"写入文件失败: {str(e)}")


@router.delete("/delete", response_model=Dict[str, Any])
async def delete_file_or_dir(
    path: str = Query(...)
):
    """删除文件或目录"""
    try:
        file_path = PathUtils.normalize_path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查宪法规则
        operation = {
            "action": "delete",
            "target_path": str(file_path),
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(file_path)))
        }
        
        evaluation = constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise HTTPException(
                status_code=403, 
                detail=f"删除被阻止: {evaluation.get('violations', [])}"
            )
        
        # 如果需要确认
        if evaluation["requires_confirmation"]:
            return {
                "success": True,
                "requires_confirmation": True,
                "confirmations": evaluation.get("confirmations", []),
                "path": str(file_path),
                "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(file_path)))
            }
        
        success = file_service.delete_file(file_path)
        
        if success:
            return {
                "success": True,
                "message": "删除成功",
                "path": str(file_path),
                "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(str(file_path.parent)))
            }
        else:
            raise HTTPException(status_code=500, detail="删除失败")
    
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/copy", response_model=Dict[str, Any])
async def copy_file_or_dir(
    source: str = Body(...),
    destination: str = Body(...),
    overwrite: bool = Body(False)
):
    """复制文件或目录"""
    try:
        success = file_service.copy_file(source, destination, overwrite)
        
        if success:
            return {
                "success": True,
                "message": "复制成功",
                "source": source,
                "destination": destination,
                "overwrite": overwrite,
                "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(destination))
            }
        else:
            raise HTTPException(status_code=500, detail="复制失败")
    
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"复制失败: {e}")
        raise HTTPException(status_code=500, detail=f"复制失败: {str(e)}")


@router.post("/move", response_model=Dict[str, Any])
async def move_file_or_dir(
    source: str = Body(...),
    destination: str = Body(...),
    overwrite: bool = Body(False)
):
    """移动文件或目录"""
    try:
        success = file_service.move_file(source, destination, overwrite)
        
        if success:
            return {
                "success": True,
                "message": "移动成功",
                "source": source,
                "destination": destination,
                "overwrite": overwrite,
                "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(destination))
            }
        else:
            raise HTTPException(status_code=500, detail="移动失败")
    
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"移动失败: {e}")
        raise HTTPException(status_code=500, detail=f"移动失败: {str(e)}")


@router.get("/search", response_model=Dict[str, Any])
async def search_files(
    query: str = Query(...),
    path: Optional[str] = Query(None),
    search_type: str = Query("name"),  # "name", "content", "both"
    recursive: bool = Query(True),
    case_sensitive: bool = Query(False)
):
    """搜索文件"""
    try:
        results = []
        
        if search_type in ["name", "both"]:
            name_results = search_service.search_by_name(
                query, path, case_sensitive=case_sensitive
            )
            results.extend(name_results)
        
        if search_type in ["content", "both"]:
            content_results = search_service.search_by_content(
                query, path, case_sensitive=case_sensitive
            )
            results.extend(content_results)
        
        # 去重
        unique_results = []
        seen_paths = set()
        
        for result in results:
            if result["path"] not in seen_paths:
                seen_paths.add(result["path"])
                unique_results.append(result)
        
        return {
            "success": True,
            "query": query,
            "search_type": search_type,
            "total": len(unique_results),
            "results": unique_results,
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(path or settings.root_path))
        }
    
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/tree", response_model=Dict[str, Any])
async def get_directory_tree(
    path: Optional[str] = Query(None),
    max_depth: int = Query(3, ge=1, le=10)
):
    """获取目录树"""
    try:
        target_path = path if path else settings.root_path
        tree = PathUtils.get_directory_tree(target_path, max_depth)
        
        return {
            "success": True,
            "path": target_path,
            "tree": tree,
            "max_depth": max_depth,
            "timestamp": PathUtils.timestamp_to_iso(os.path.getctime(target_path))
        }
    
    except Exception as e:
        logger.error(f"获取目录树失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取目录树失败: {str(e)}")