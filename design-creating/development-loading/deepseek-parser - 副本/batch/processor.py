"""
batch/processor.py
批量处理器 - 批量处理多个HTML文件
"""
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from tqdm import tqdm
import logging

from utils.logger import logger
from utils.file_ops import FileOperations
from core.deepseek_parser import DeepSeekParser
from core.conversation_builder import ConversationBuilder
from core.content_formatter import ContentFormatter
from outputs.optimized_markdown import OptimizedMarkdownWriter


class BatchProcessor:
    """批量处理多个HTML文件"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logger
        
        # 初始化组件
        self.parser = DeepSeekParser(config)
        self.builder = ConversationBuilder(config)
        self.formatter = ContentFormatter(config)
        self.writer = OptimizedMarkdownWriter(config)
        
        # 批量处理配置
        batch_config = self.config.get('batch', {})
        self.overwrite_existing = batch_config.get('overwrite_existing', False)
        self.stop_on_error = batch_config.get('stop_on_error', False)
        self.generate_report = batch_config.get('generate_report', True)
        self.parallel_processing = batch_config.get('parallel_processing', False)
        
        # 路径配置
        paths_config = self.config.get('paths', {})
        self.input_dir = paths_config.get('input_dir', './html_conversations')
        self.output_dir = paths_config.get('output_dir', './knowledge_base')
        self.failed_dir = paths_config.get('failed_dir', './failed')
        
        # 确保目录存在
        FileOperations.ensure_directory(self.input_dir)
        FileOperations.ensure_directory(self.output_dir)
        FileOperations.ensure_directory(self.failed_dir)
        
        # 状态跟踪
        self.processed_files = []
        self.failed_files = []
        self.start_time = None
        self.end_time = None
    
    def process_directory(self, input_dir: Optional[str] = None, 
                         output_dir: Optional[str] = None,
                         incremental: bool = False,
                         verbose: bool = False) -> Dict[str, Any]:
        """
        批量处理目录下的所有HTML文件
        
        Args:
            input_dir: 输入目录路径（默认使用配置）
            output_dir: 输出目录路径（默认使用配置）
            incremental: 是否增量处理（只处理新文件）
            verbose: 是否显示详细信息
        
        Returns:
            处理结果统计
        """
        # 设置路径
        input_dir = input_dir or self.input_dir
        output_dir = output_dir or self.output_dir
        
        # 记录开始时间
        self.start_time = datetime.now()
        self.logger.info(f"开始批量处理，输入目录: {input_dir}")
        self.logger.info(f"输出目录: {output_dir}")
        
        # 查找HTML文件
        html_files = FileOperations.find_files(input_dir, ['.html', '.htm'])
        
        if not html_files:
            self.logger.warning(f"在目录 {input_dir} 中未找到HTML文件")
            return {
                'total_files': 0,
                'success': 0,
                'failed': 0,
                'failed_files': [],
                'message': '未找到HTML文件'
            }
        
        self.logger.info(f"找到 {len(html_files)} 个HTML文件")
        
        # 增量处理：过滤已处理的文件
        if incremental:
            html_files = self._filter_new_files(html_files, output_dir)
            self.logger.info(f"增量处理模式，剩余 {len(html_files)} 个新文件")
        
        # 处理文件
        results = {
            'total_files': len(html_files),
            'success': 0,
            'failed': 0,
            'failed_files': [],
            'processing_time': 0,
            'details': []
        }
        
        # 显示进度条
        with tqdm(total=len(html_files), desc="处理HTML文件", unit="文件") as pbar:
            for file_path in html_files:
                try:
                    # 处理单个文件
                    file_result = self.process_single_file(file_path, output_dir, verbose)
                    
                    if file_result['success']:
                        results['success'] += 1
                        self.processed_files.append({
                            'file': file_path,
                            'output': file_result.get('output_file'),
                            'dialog_id': file_result.get('dialog_id'),
                            'rounds': file_result.get('total_rounds', 0)
                        })
                    else:
                        results['failed'] += 1
                        results['failed_files'].append(file_path)
                        self.failed_files.append({
                            'file': file_path,
                            'error': file_result.get('error', '未知错误')
                        })
                        
                        # 如果配置为遇到错误就停止
                        if self.stop_on_error:
                            self.logger.error(f"处理失败，已停止: {file_path}")
                            break
                    
                    results['details'].append(file_result)
                    
                except Exception as e:
                    results['failed'] += 1
                    results['failed_files'].append(file_path)
                    self.failed_files.append({
                        'file': file_path,
                        'error': str(e)
                    })
                    self.logger.error(f"处理文件异常 {file_path}: {e}")
                    
                    if self.stop_on_error:
                        self.logger.error(f"遇到异常，已停止: {file_path}")
                        break
                
                finally:
                    pbar.update(1)
                    if verbose:
                        pbar.set_postfix_str(file_path)
        
        # 记录结束时间
        self.end_time = datetime.now()
        processing_time = (self.end_time - self.start_time).total_seconds()
        results['processing_time'] = processing_time
        
        # 生成报告
        if self.generate_report:
            report = self._generate_report(results)
            results['report'] = report
            
            # 保存报告
            report_file = self._save_report(report, output_dir)
            results['report_file'] = report_file
        
        # 移动失败的文件
        if self.failed_files:
            self._move_failed_files()
        
        self.logger.info(f"批量处理完成，成功: {results['success']}/{results['total_files']}")
        self.logger.info(f"处理时间: {processing_time:.2f} 秒")
        
        return results
    
    def process_single_file(self, file_path: str, 
                           output_dir: Optional[str] = None,
                           verbose: bool = False) -> Dict[str, Any]:
        """
        处理单个HTML文件
        
        Args:
            file_path: HTML文件路径
            output_dir: 输出目录路径
            verbose: 是否显示详细信息
        
        Returns:
            处理结果
        """
        result = {
            'file': file_path,
            'success': False,
            'error': None,
            'dialog_id': None,
            'total_rounds': 0,
            'output_file': None,
            'processing_time': 0
        }
        
        start_time = time.time()
        
        try:
            if verbose:
                self.logger.info(f"处理文件: {file_path}")
            
            # 1. 读取HTML文件
            html_content = FileOperations.read_file(file_path)
            
            if not html_content:
                result['error'] = '文件内容为空'
                return result
            
            # 2. 解析HTML
            parsed_data = self.parser.parse_html(html_content)
            
            if not parsed_data.get('rounds'):
                result['error'] = '未解析到对话轮次'
                return result
            
            # 3. 构建对话
            conversation = self.builder.build(parsed_data)
            
            if not conversation.get('rounds'):
                result['error'] = '未构建出有效对话'
                return result
            
            dialog_id = conversation.get('dialog_id')
            result['dialog_id'] = dialog_id
            result['total_rounds'] = len(conversation['rounds'])
            
            # 4. 格式化内容
            for round_data in conversation['rounds']:
                # 格式化用户内容
                user_content = round_data['user']['content']
                round_data['user']['content'] = self.formatter.format_content(user_content, 'user')
                
                # 格式化AI内容
                ai_content = round_data['ai']['content']
                round_data['ai']['content'] = self.formatter.format_content(ai_content, 'ai')
            
            # 5. 生成输出文件名
            if not output_dir:
                output_dir = self.output_dir
            
            output_filename = FileOperations.generate_output_filename(
                conversation, 
                output_dir,
                '.md'
            )
            
            output_file = os.path.join(output_dir, output_filename)
            
            # 检查文件是否已存在
            if os.path.exists(output_file) and not self.overwrite_existing:
                # 生成新文件名
                base_name, ext = os.path.splitext(output_filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{base_name}_{timestamp}{ext}"
                output_file = os.path.join(output_dir, output_filename)
            
            # 6. 写入Markdown
            markdown_content = self.writer.write(conversation)
            FileOperations.write_file(output_file, markdown_content)
            
            # 7. 记录结果
            result['success'] = True
            result['output_file'] = output_file
            
            if verbose:
                self.logger.info(f"成功处理: {file_path} -> {output_file}")
                self.logger.info(f"对话ID: {dialog_id}, 轮次: {result['total_rounds']}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"处理文件失败 {file_path}: {e}")
        
        finally:
            # 计算处理时间
            end_time = time.time()
            result['processing_time'] = end_time - start_time
        
        return result
    
    def _filter_new_files(self, html_files: List[str], output_dir: str) -> List[str]:
        """过滤新文件（增量处理）"""
        new_files = []
        
        for file_path in html_files:
            # 检查输出目录中是否已有对应的Markdown文件
            file_name = os.path.basename(file_path)
            base_name, _ = os.path.splitext(file_name)
            
            # 可能的输出文件名模式
            possible_patterns = [
                f"{base_name}.md",
                f"{base_name}_*.md",
                f"V*_{base_name}.md",
            ]
            
            # 检查是否存在匹配的文件
            existing = False
            for pattern in possible_patterns:
                import fnmatch
                for existing_file in os.listdir(output_dir):
                    if fnmatch.fnmatch(existing_file, pattern):
                        existing = True
                        break
                if existing:
                    break
            
            if not existing:
                new_files.append(file_path)
        
        return new_files
    
    def _generate_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成处理报告"""
        report = {
            'report_id': f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_files': results['total_files'],
                'success': results['success'],
                'failed': results['failed'],
                'success_rate': results['success'] / results['total_files'] * 100 if results['total_files'] > 0 else 0,
                'processing_time_seconds': results['processing_time'],
                'files_per_second': results['total_files'] / results['processing_time'] if results['processing_time'] > 0 else 0
            },
            'configuration': {
                'input_dir': self.input_dir,
                'output_dir': self.output_dir,
                'failed_dir': self.failed_dir,
                'overwrite_existing': self.overwrite_existing,
                'stop_on_error': self.stop_on_error
            },
            'processed_files': self.processed_files,
            'failed_files': self.failed_files,
            'details': results['details']
        }
        
        return report
    
    def _save_report(self, report: Dict[str, Any], output_dir: str) -> str:
        """保存处理报告"""
        report_filename = f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file = os.path.join(output_dir, report_filename)
        
        FileOperations.save_json(report, report_file)
        self.logger.info(f"处理报告已保存: {report_file}")
        
        return report_file
    
    def _move_failed_files(self):
        """移动处理失败的文件到失败目录"""
        for failed_file in self.failed_files:
            file_path = failed_file['file']
            
            if os.path.exists(file_path):
                try:
                    # 生成失败目录中的新路径
                    file_name = os.path.basename(file_path)
                    failed_path = os.path.join(self.failed_dir, file_name)
                    
                    # 确保不重名
                    counter = 1
                    base_name, ext = os.path.splitext(file_name)
                    while os.path.exists(failed_path):
                        failed_path = os.path.join(
                            self.failed_dir, 
                            f"{base_name}_failed_{counter}{ext}"
                        )
                        counter += 1
                    
                    # 移动文件
                    import shutil
                    shutil.move(file_path, failed_path)
                    
                    # 记录错误信息
                    error_file = os.path.splitext(failed_path)[0] + '.error.txt'
                    with open(error_file, 'w', encoding='utf-8') as f:
                        f.write(f"文件: {file_path}\n")
                        f.write(f"错误: {failed_file['error']}\n")
                        f.write(f"时间: {datetime.now().isoformat()}\n")
                    
                    self.logger.debug(f"失败文件已移动: {file_path} -> {failed_path}")
                    
                except Exception as e:
                    self.logger.error(f"移动失败文件出错 {file_path}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取批量处理器状态"""
        return {
            'is_processing': self.start_time is not None and self.end_time is None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'processed_count': len(self.processed_files),
            'failed_count': len(self.failed_files),
            'current_file': self.processed_files[-1]['file'] if self.processed_files else None
        }
    
    def reset(self):
        """重置批量处理器状态"""
        self.processed_files = []
        self.failed_files = []
        self.start_time = None
        self.end_time = None
        self.logger.info("批量处理器已重置")