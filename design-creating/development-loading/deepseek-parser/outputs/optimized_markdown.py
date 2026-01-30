"""
outputs/optimized_markdown.py
按照第二份文档格式输出优化Markdown
"""
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

from utils.logger import logger


class OptimizedMarkdownWriter:
    """按照第二份文档格式输出优化Markdown"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logger
        
        # 输出配置
        output_config = self.config.get('output', {})
        self.title_format = output_config.get('title_format', '[{dialog_id}-{round_id}] {keywords}')
        self.max_title_length = output_config.get('max_title_length', 80)
        
        # 折叠设置
        self.fold_user_queries = output_config.get('fold_user_queries', True)
        self.fold_long_code_blocks = output_config.get('fold_long_code_blocks', 30)
        
        # 标记点设置
        self.add_round_markers = output_config.get('add_round_markers', True)
        self.add_metadata_comments = output_config.get('add_metadata_comments', True)
        
        # 空行设置
        blank_lines_config = output_config.get('blank_lines', {})
        self.blank_between_rounds = blank_lines_config.get('between_rounds', 3)
        self.blank_before_user_query = blank_lines_config.get('before_user_query', 0)
        self.blank_after_user_query = blank_lines_config.get('after_user_query', 1)
        self.blank_before_ai_response = blank_lines_config.get('before_ai_response', 0)
        
        # 导航设置
        self.generate_navigation = output_config.get('generate_navigation', False)
        
        # 初始化计数器
        self.code_block_counter = 0
    
    def write(self, conversation: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        生成优化格式的Markdown文档
        
        Args:
            conversation: 对话数据
            output_path: 输出文件路径（可选）
        
        Returns:
            Markdown文档内容
        """
        try:
            self.logger.info(f"开始生成优化Markdown，对话ID: {conversation.get('dialog_id')}")
            
            # 1. 生成文档标题
            content = self._generate_document_header(conversation)
            
            # 2. 如果需要，生成导航
            if self.generate_navigation:
                content += self._generate_navigation(conversation)
                content += self._add_blank_lines(2)
            
            # 3. 按轮次生成内容
            rounds = conversation.get('rounds', [])
            total_rounds = len(rounds)
            
            for i, round_data in enumerate(rounds):
                round_num = i + 1
                
                # 生成轮次内容
                round_content = self._generate_round_content(round_data, round_num, total_rounds)
                content += round_content
                
                # 添加轮次之间的空行（最后一个轮次后不加）
                if i < total_rounds - 1:
                    content += self._add_blank_lines(self.blank_between_rounds)
            
            # 4. 添加文档脚注
            content += self._generate_document_footer(conversation)
            
            # 5. 保存到文件（如果提供了路径）
            if output_path:
                from utils.file_ops import FileOperations
                FileOperations.write_file(output_path, content)
                self.logger.info(f"Markdown文档已保存到: {output_path}")
            
            return content
            
        except Exception as e:
            self.logger.error(f"生成优化Markdown失败: {e}")
            raise
    
    def _generate_document_header(self, conversation: Dict[str, Any]) -> str:
        """生成文档标题和头部信息"""
        dialog_id = conversation.get('dialog_id', '未知')
        metadata = conversation.get('metadata', {})
        
        # 生成主标题
        title_keywords = metadata.get('title_keywords', '技术对话')
        main_title = f"# {title_keywords}\n\n"
        
        # 添加元数据信息
        header_comment = f"<!--\n"
        header_comment += f"对话ID: {dialog_id}\n"
        header_comment += f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header_comment += f"总轮次: {metadata.get('total_rounds', 0)}\n"
        header_comment += f"技术轮次: {metadata.get('technical_rounds', 0)}\n"
        header_comment += f"估计字数: {metadata.get('estimated_total_words', 0)}\n"
        
        source_file = metadata.get('source_file')
        if source_file:
            header_comment += f"来源文件: {source_file}\n"
        
        header_comment += f"-->\n\n"
        
        return main_title + header_comment
    
    def _generate_navigation(self, conversation: Dict[str, Any]) -> str:
        """生成目录导航"""
        rounds = conversation.get('rounds', [])
        
        if not rounds:
            return ""
        
        navigation = "## 目录\n\n"
        
        for i, round_data in enumerate(rounds):
            round_id = round_data.get('round_id', f"轮次{i+1}")
            user_keywords = ' '.join(round_data['user'].get('keywords', []))
            
            if not user_keywords:
                user_keywords = round_data['metadata'].get('main_topic', '未命名主题')
            
            # 生成导航项
            navigation += f"{i+1}. [{round_id} {user_keywords}](#{self._generate_anchor(round_id, user_keywords)})\n"
        
        return navigation + "\n"
    
    def _generate_round_content(self, round_data: Dict[str, Any], round_num: int, total_rounds: int) -> str:
        """生成单个轮次的内容"""
        content = ""
        
        # 1. 轮次标题
        content += self._generate_round_title(round_data)
        
        # 2. 轮次开始标记点
        if self.add_round_markers:
            content += self._generate_round_marker(round_data, 'start')
        
        # 3. 用户问题（可能折叠）
        content += self._wrap_user_query(round_data['user'])
        
        # 4. AI回答
        content += self._format_ai_response(round_data['ai'])
        
        # 5. 轮次结束标记点
        if self.add_round_markers:
            content += self._generate_round_marker(round_data, 'end')
        
        # 6. 添加进度信息（可选）
        if self.add_metadata_comments:
            content += self._generate_round_progress(round_num, total_rounds)
        
        return content
    
    def _generate_round_title(self, round_data: Dict[str, Any]) -> str:
        """生成轮次标题"""
        round_id = round_data.get('round_id', '未知轮次')
        user_data = round_data.get('user', {})
        
        # 提取关键词
        keywords = user_data.get('keywords', [])
        if not keywords:
            # 从AI回答中提取关键词
            ai_keywords = round_data.get('ai', {}).get('keywords', [])
            keywords = ai_keywords[:3]
        
        # 生成标题文本
        keywords_text = ' '.join(keywords[:3])  # 最多3个关键词
        
        # 应用标题格式
        title = self.title_format.format(
            dialog_id=round_id.split('-')[0] if '-' in round_id else round_id,
            round_id=round_id.split('-')[1] if '-' in round_id else '1',
            keywords=keywords_text
        )
        
        # 限制标题长度
        if len(title) > self.max_title_length:
            title = title[:self.max_title_length - 3] + "..."
        
        # 添加Markdown标题标记
        return f"# {title}\n\n"
    
    def _generate_round_marker(self, round_data: Dict[str, Any], marker_type: str) -> str:
        """生成轮次标记点"""
        round_id = round_data.get('round_id', '未知轮次')
        timestamp = round_data.get('metadata', {}).get('created_at', '')
        topic = round_data.get('metadata', {}).get('main_topic', '未分类')
        
        if marker_type == 'start':
            marker_text = f"轮次开始 {round_id}"
        elif marker_type == 'end':
            marker_text = f"轮次结束 {round_id}"
        else:
            marker_text = f"轮次标记 {round_id}"
        
        comment = f"<!-- {marker_text}"
        
        if timestamp:
            comment += f" | 时间: {timestamp}"
        
        if topic:
            comment += f" | 主题: {topic}"
        
        comment += " -->\n\n"
        
        return comment
    
    def _wrap_user_query(self, user_data: Dict[str, Any]) -> str:
        """包装用户问题（可能折叠）"""
        content = ""
        
        # 添加用户问题前的空行
        if self.blank_before_user_query > 0:
            content += self._add_blank_lines(self.blank_before_user_query)
        
        # 用户问题内容
        user_content = user_data.get('content', '').strip()
        
        if not user_content:
            return content
        
        if self.fold_user_queries:
            # 生成折叠的用户问题
            summary_text = "用户提问（点击展开）"
            
            # 如果有时间戳，添加到摘要
            timestamp = user_data.get('timestamp')
            if timestamp:
                summary_text += f" - {self._format_timestamp(timestamp)}"
            
            folded_content = f"""<details class="user-query" data-collapsed="true">
<summary>{summary_text}</summary>

{user_content}

</details>

"""
            content += folded_content
        else:
            # 直接显示用户问题
            content += f"**用户提问:**\n\n{user_content}\n\n"
        
        # 添加用户问题后的空行
        if self.blank_after_user_query > 0:
            content += self._add_blank_lines(self.blank_after_user_query)
        
        return content
    
    def _format_ai_response(self, ai_data: Dict[str, Any]) -> str:
        """格式化AI回答"""
        content = ""
        
        # 添加AI回答前的空行
        if self.blank_before_ai_response > 0:
            content += self._add_blank_lines(self.blank_before_ai_response)
        
        # AI回答内容
        ai_content = ai_data.get('content', '').strip()
        
        if not ai_content:
            return content
        
        # 处理代码块（如果需要折叠长代码块）
        if self.fold_long_code_blocks > 0:
            ai_content = self._process_code_blocks_for_folding(ai_content)
        
        # 确保AI回答中的标题层级从##开始
        ai_content = self._ensure_heading_levels(ai_content)
        
        content += ai_content + "\n"
        
        return content
    
    def _process_code_blocks_for_folding(self, content: str) -> str:
        """处理代码块，对长代码块进行折叠"""
        lines = content.split('\n')
        processed_lines = []
        in_code_block = False
        code_block_lines = []
        code_block_start = 0
        current_language = ''
        
        for i, line in enumerate(lines):
            # 检测代码块开始
            if line.strip().startswith('```'):
                if not in_code_block:
                    # 代码块开始
                    in_code_block = True
                    code_block_start = i
                    current_language = line.strip()[3:].strip()
                    code_block_lines = [line]
                else:
                    # 代码块结束
                    code_block_lines.append(line)
                    in_code_block = False
                    
                    # 检查代码块长度
                    code_block_content = '\n'.join(code_block_lines)
                    
                    if len(code_block_lines) - 2 > self.fold_long_code_blocks:  # 减去开始和结束标记
                        # 需要折叠
                        self.code_block_counter += 1
                        code_id = f"code-block-{self.code_block_counter}"
                        
                        folded_code = f"""<details class="long-code-block" id="{code_id}" data-collapsed="true">
<summary>{current_language or '代码'} ({len(code_block_lines)-2} 行)</summary>

{code_block_content}

</details>"""
                        
                        processed_lines.append(folded_code)
                    else:
                        # 不需要折叠，直接添加
                        processed_lines.extend(code_block_lines)
                    
                    code_block_lines = []
            elif in_code_block:
                # 在代码块内
                code_block_lines.append(line)
            else:
                # 不在代码块内
                processed_lines.append(line)
        
        # 如果仍在代码块内（异常情况），直接添加剩余内容
        if code_block_lines:
            processed_lines.extend(code_block_lines)
        
        return '\n'.join(processed_lines)
    
    def _ensure_heading_levels(self, content: str, base_level: int = 2) -> str:
        """确保标题层级从指定级别开始"""
        lines = content.split('\n')
        adjusted_lines = []
        
        for line in lines:
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                current_level = len(heading_match.group(1))
                heading_text = heading_match.group(2)
                
                # 计算新级别
                new_level = min(6, max(1, current_level))
                
                # 如果当前级别小于基础级别，提升到基础级别
                if new_level < base_level:
                    new_level = base_level
                
                new_heading = '#' * new_level + ' ' + heading_text
                adjusted_lines.append(new_heading)
            else:
                adjusted_lines.append(line)
        
        return '\n'.join(adjusted_lines)
    
    def _generate_round_progress(self, current_round: int, total_rounds: int) -> str:
        """生成轮次进度信息"""
        if total_rounds <= 1:
            return ""
        
        progress = f"<!-- 进度: {current_round}/{total_rounds} ({current_round/total_rounds*100:.0f}%) -->\n"
        
        # 添加进度条（ASCII）
        bar_length = 20
        filled_length = int(bar_length * current_round / total_rounds)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        progress += f"<!-- [{bar}] -->\n"
        
        return progress + "\n"
    
    def _generate_document_footer(self, conversation: Dict[str, Any]) -> str:
        """生成文档脚注"""
        metadata = conversation.get('metadata', {})
        dialog_id = conversation.get('dialog_id', '未知')
        
        footer = "\n---\n\n"
        footer += "## 文档信息\n\n"
        footer += f"- **对话ID:** {dialog_id}\n"
        footer += f"- **创建时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        footer += f"- **总轮次:** {metadata.get('total_rounds', 0)}\n"
        footer += f"- **技术轮次:** {metadata.get('technical_rounds', 0)}\n"
        footer += f"- **估计阅读时间:** {metadata.get('estimated_total_words', 0) // 200 + 1} 分钟\n"
        
        # 添加生成器信息
        footer += f"- **生成工具:** DeepSeek HTML解析器\n"
        footer += f"- **生成格式:** 优化Markdown (v1.0)\n"
        
        return footer
    
    def _add_blank_lines(self, count: int) -> str:
        """添加指定数量的空行"""
        return '\n' * max(0, count)
    
    def _generate_anchor(self, text: str, fallback: str = '') -> str:
        """生成Markdown锚点"""
        # 使用round_id或关键词生成锚点
        anchor_text = text if text else fallback
        
        # 转换为小写，移除特殊字符，用横线替换空格
        anchor = anchor_text.lower()
        anchor = re.sub(r'[^\w\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        anchor = anchor.strip('-')
        
        return anchor
    
    def _format_timestamp(self, timestamp: str) -> str:
        """格式化时间戳"""
        if not timestamp:
            return ""
        
        try:
            # 尝试解析ISO格式
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M')
            else:
                return timestamp
        except Exception:
            return timestamp