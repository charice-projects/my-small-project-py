"""
outputs/simple_markdown.py
简单Markdown格式输出器（备用）
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from utils.logger import logger


class SimpleMarkdownWriter:
    """简单Markdown格式输出器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logger
    
    def write(self, conversation: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """生成简单格式的Markdown文档"""
        try:
            self.logger.info(f"开始生成简单Markdown，对话ID: {conversation.get('dialog_id')}")
            
            content = ""
            
            # 1. 文档标题
            dialog_id = conversation.get('dialog_id', '未知对话')
            content += f"# 对话 {dialog_id}\n\n"
            
            # 2. 元数据
            metadata = conversation.get('metadata', {})
            content += "## 元数据\n\n"
            content += f"- **总轮次:** {metadata.get('total_rounds', 0)}\n"
            content += f"- **创建时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            source_file = metadata.get('source_file')
            if source_file:
                content += f"- **来源文件:** {source_file}\n"
            
            content += "\n---\n\n"
            
            # 3. 对话内容
            content += "## 对话内容\n\n"
            
            rounds = conversation.get('rounds', [])
            for i, round_data in enumerate(rounds):
                round_id = round_data.get('round_id', f"轮次{i+1}")
                
                content += f"### {round_id}\n\n"
                
                # 用户问题
                user_content = round_data['user'].get('content', '').strip()
                if user_content:
                    content += f"**用户:**\n\n{user_content}\n\n"
                
                # AI回答
                ai_content = round_data['ai'].get('content', '').strip()
                if ai_content:
                    content += f"**AI:**\n\n{ai_content}\n\n"
                
                # 分隔线
                if i < len(rounds) - 1:
                    content += "---\n\n"
            
            # 4. 保存到文件（如果提供了路径）
            if output_path:
                from utils.file_ops import FileOperations
                FileOperations.write_file(output_path, content)
                self.logger.info(f"简单Markdown文档已保存到: {output_path}")
            
            return content
            
        except Exception as e:
            self.logger.error(f"生成简单Markdown失败: {e}")
            raise