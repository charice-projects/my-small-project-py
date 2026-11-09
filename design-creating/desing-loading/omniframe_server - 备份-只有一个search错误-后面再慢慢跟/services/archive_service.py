"""
归档服务 - 提供文件打包、压缩、解压功能
"""
import zipfile
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, BinaryIO
from datetime import datetime

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
from core.constitution_engine import ConstitutionEngine


class ArchiveService:
    """归档服务"""
    
    def __init__(self, constitution_engine: Optional[ConstitutionEngine] = None):
        self.constitution_engine = constitution_engine or ConstitutionEngine()
        self.root_path = Path(settings.root_path)
    
    def create_zip_archive(self, 
                          source_paths: List[Union[str, Path]], 
                          output_path: Union[str, Path],
                          compression_level: int = 6) -> Dict[str, Any]:
        """创建ZIP归档"""
        output_path = PathUtils.normalize_path(output_path)
        
        # 检查宪法规则
        operation = {
            "action": "create_archive",
            "source_paths": [str(p) for p in source_paths],
            "target_path": str(output_path),
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许创建归档: {evaluation.get('violations', [])}")
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            total_files = 0
            total_size = 0
            
            with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zipf:
                for source_path in source_paths:
                    source = PathUtils.normalize_path(source_path)
                    
                    if not source.exists():
                        logger.warning(f"源路径不存在: {source}")
                        continue
                    
                    if source.is_file():
                        # 添加单个文件
                        zipf.write(source, source.relative_to(self.root_path))
                        total_files += 1
                        total_size += source.stat().st_size
                    
                    elif source.is_dir():
                        # 递归添加目录
                        for file_path in source.rglob('*'):
                            if file_path.is_file():
                                try:
                                    relative_path = file_path.relative_to(source)
                                    zipf.write(file_path, source.name / relative_path)
                                    total_files += 1
                                    total_size += file_path.stat().st_size
                                except Exception as e:
                                    logger.warning(f"添加文件失败 {file_path}: {e}")
                    
                    logger.info(f"已添加: {source}")
            
            result = {
                "success": True,
                "output_path": str(output_path),
                "output_size": output_path.stat().st_size,
                "output_size_human": PathUtils.humanize_size(output_path.stat().st_size),
                "total_files": total_files,
                "total_original_size": total_size,
                "compression_ratio": output_path.stat().st_size / total_size if total_size > 0 else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"ZIP归档已创建: {output_path} (共 {total_files} 个文件)")
            return result
        
        except Exception as e:
            logger.error(f"创建ZIP归档失败: {output_path} - {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def extract_zip_archive(self, 
                           archive_path: Union[str, Path], 
                           output_dir: Union[str, Path],
                           overwrite: bool = False) -> Dict[str, Any]:
        """解压ZIP归档"""
        archive_path = PathUtils.normalize_path(archive_path)
        output_dir = PathUtils.normalize_path(output_dir)
        
        if not archive_path.exists():
            raise FileNotFoundError(f"归档文件不存在: {archive_path}")
        
        if not zipfile.is_zipfile(archive_path):
            raise ValueError(f"不是有效的ZIP文件: {archive_path}")
        
        # 检查宪法规则
        operation = {
            "action": "extract_archive",
            "source_path": str(archive_path),
            "target_path": str(output_dir),
            "overwrite": overwrite,
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许解压归档: {evaluation.get('violations', [])}")
        
        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            extracted_files = []
            total_size = 0
            
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                # 检查文件是否已存在
                for file_info in zipf.infolist():
                    output_path = output_dir / file_info.filename
                    
                    if output_path.exists() and not overwrite:
                        raise FileExistsError(f"文件已存在: {output_path}")
                
                # 解压所有文件
                for file_info in zipf.infolist():
                    output_path = output_dir / file_info.filename
                    
                    # 确保目录存在
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 提取文件
                    zipf.extract(file_info, output_dir)
                    
                    extracted_files.append(str(output_path.relative_to(output_dir)))
                    total_size += file_info.file_size
            
            result = {
                "success": True,
                "archive_path": str(archive_path),
                "output_dir": str(output_dir),
                "extracted_files": extracted_files,
                "total_files": len(extracted_files),
                "total_size": total_size,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"ZIP归档已解压: {archive_path} -> {output_dir} (共 {len(extracted_files)} 个文件)")
            return result
        
        except Exception as e:
            logger.error(f"解压ZIP归档失败: {archive_path} - {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def create_tar_archive(self, 
                          source_paths: List[Union[str, Path]], 
                          output_path: Union[str, Path],
                          compression: str = 'gz') -> Dict[str, Any]:
        """创建TAR归档"""
        output_path = PathUtils.normalize_path(output_path)
        
        # 检查宪法规则
        operation = {
            "action": "create_archive",
            "source_paths": [str(p) for p in source_paths],
            "target_path": str(output_path),
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许创建归档: {evaluation.get('violations', [])}")
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            total_files = 0
            total_size = 0
            
            mode = 'w'
            if compression == 'gz':
                mode = 'w:gz'
            elif compression == 'bz2':
                mode = 'w:bz2'
            elif compression == 'xz':
                mode = 'w:xz'
            
            with tarfile.open(output_path, mode) as tarf:
                for source_path in source_paths:
                    source = PathUtils.normalize_path(source_path)
                    
                    if not source.exists():
                        logger.warning(f"源路径不存在: {source}")
                        continue
                    
                    if source.is_file():
                        # 添加单个文件
                        tarf.add(source, arcname=source.relative_to(self.root_path))
                        total_files += 1
                        total_size += source.stat().st_size
                    
                    elif source.is_dir():
                        # 递归添加目录
                        tarf.add(source, arcname=source.name)
                        total_files += sum(1 for _ in source.rglob('*') if _.is_file())
                        total_size += sum(_.stat().st_size for _ in source.rglob('*') if _.is_file())
                    
                    logger.info(f"已添加: {source}")
            
            result = {
                "success": True,
                "output_path": str(output_path),
                "output_size": output_path.stat().st_size,
                "output_size_human": PathUtils.humanize_size(output_path.stat().st_size),
                "total_files": total_files,
                "total_original_size": total_size,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"TAR归档已创建: {output_path} (共 {total_files} 个文件)")
            return result
        
        except Exception as e:
            logger.error(f"创建TAR归档失败: {output_path} - {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def extract_tar_archive(self, 
                           archive_path: Union[str, Path], 
                           output_dir: Union[str, Path],
                           overwrite: bool = False) -> Dict[str, Any]:
        """解压TAR归档"""
        archive_path = PathUtils.normalize_path(archive_path)
        output_dir = PathUtils.normalize_path(output_dir)
        
        if not archive_path.exists():
            raise FileNotFoundError(f"归档文件不存在: {archive_path}")
        
        # 检查宪法规则
        operation = {
            "action": "extract_archive",
            "source_path": str(archive_path),
            "target_path": str(output_dir),
            "overwrite": overwrite,
            "timestamp": datetime.now().isoformat()
        }
        
        evaluation = self.constitution_engine.evaluate_operation(operation)
        if not evaluation["allowed"]:
            raise PermissionError(f"不允许解压归档: {evaluation.get('violations', [])}")
        
        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            extracted_files = []
            
            with tarfile.open(archive_path, 'r:*') as tarf:
                # 检查文件是否已存在
                for member in tarf.getmembers():
                    output_path = output_dir / member.name
                    
                    if output_path.exists() and not overwrite:
                        raise FileExistsError(f"文件已存在: {output_path}")
                
                # 提取所有文件
                tarf.extractall(output_dir)
                
                for member in tarf.getmembers():
                    if member.isfile():
                        extracted_files.append(member.name)
            
            result = {
                "success": True,
                "archive_path": str(archive_path),
                "output_dir": str(output_dir),
                "extracted_files": extracted_files,
                "total_files": len(extracted_files),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"TAR归档已解压: {archive_path} -> {output_dir} (共 {len(extracted_files)} 个文件)")
            return result
        
        except Exception as e:
            logger.error(f"解压TAR归档失败: {archive_path} - {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def list_archive_contents(self, archive_path: Union[str, Path]) -> Dict[str, Any]:
        """列出归档内容"""
        archive_path = PathUtils.normalize_path(archive_path)
        
        if not archive_path.exists():
            raise FileNotFoundError(f"归档文件不存在: {archive_path}")
        
        try:
            contents = []
            total_size = 0
            
            if zipfile.is_zipfile(archive_path):
                # ZIP文件
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    for file_info in zipf.infolist():
                        item = {
                            "name": file_info.filename,
                            "size": file_info.file_size,
                            "size_human": PathUtils.humanize_size(file_info.file_size),
                            "compressed_size": file_info.compress_size,
                            "compressed_ratio": file_info.compress_size / file_info.file_size if file_info.file_size > 0 else 0,
                            "modified": datetime(*file_info.date_time).isoformat(),
                            "is_dir": file_info.filename.endswith('/')
                        }
                        contents.append(item)
                        total_size += file_info.file_size
                
                archive_type = "zip"
            
            else:
                # 尝试TAR文件
                try:
                    with tarfile.open(archive_path, 'r:*') as tarf:
                        for member in tarf.getmembers():
                            item = {
                                "name": member.name,
                                "size": member.size,
                                "size_human": PathUtils.humanize_size(member.size),
                                "modified": datetime.fromtimestamp(member.mtime).isoformat(),
                                "is_dir": member.isdir(),
                                "is_file": member.isfile(),
                                "is_link": member.issym(),
                                "mode": oct(member.mode),
                                "user": member.uid,
                                "group": member.gid
                            }
                            contents.append(item)
                            total_size += member.size
                    
                    archive_type = "tar"
                
                except tarfile.ReadError:
                    raise ValueError(f"不支持的文件格式: {archive_path}")
            
            result = {
                "archive_path": str(archive_path),
                "archive_type": archive_type,
                "total_files": len([c for c in contents if not c["is_dir"]]),
                "total_dirs": len([c for c in contents if c["is_dir"]]),
                "total_size": total_size,
                "total_size_human": PathUtils.humanize_size(total_size),
                "contents": contents,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
        
        except Exception as e:
            logger.error(f"列出归档内容失败: {archive_path} - {e}")
            raise