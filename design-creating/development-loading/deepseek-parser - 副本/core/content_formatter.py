"""
core/content_formatter.py
内容格式化器 - 处理特殊内容格式：代码、表格、公式等
"""
import re
import html
from typing import Dict, List, Any, Optional, Tuple
import logging

from utils.logger import logger


class ContentFormatter:
    """处理特殊内容格式：代码、表格、公式等"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logger
        
        # 配置选项
        parsing_config = self.config.get('parsing', {})
        self.preserve_code_blocks = parsing_config.get('preserve_code_blocks', True)
        self.extract_tables = parsing_config.get('extract_tables', True)
        self.clean_html_tags = parsing_config.get('clean_html_tags', True)
        self.remove_emojis = parsing_config.get('remove_emojis', False)
        
        # 代码块配置
        self.code_block_config = {
            'min_lines_for_folding': self.config.get('output', {}).get('fold_long_code_blocks', 30),
            'preserve_indentation': True,
            'add_line_numbers': False
        }
        
        # 表格配置
        self.table_config = {
            'convert_to_markdown': True,
            'min_rows': 2,
            'min_cols': 2
        }
        
        # 初始化正则表达式
        self._init_regex_patterns()
    
    def _init_regex_patterns(self):
        """初始化正则表达式模式"""
        # HTML标签模式
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        
        # 代码块模式
        self.code_block_pattern = re.compile(r'```(\w*)\n([\s\S]*?)```')
        
        # 表格模式（简单Markdown表格）
        self.table_pattern = re.compile(r'\|(.+)\|\n\|[-:\s|]+\|\n((?:\|.*\|\n?)*)')
        
        # 链接模式
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        # 图片模式
        self.image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        
        # 标题模式
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        
        # 列表模式
        self.list_pattern = re.compile(r'^(\s*)[\-\*\+]\s', re.MULTILINE)
        self.ordered_list_pattern = re.compile(r'^(\s*)\d+\.\s', re.MULTILINE)
        
        # 表情符号模式
        self.emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F'  # 表情符号
            r'\U0001F300-\U0001F5FF'  # 符号和象形文字
            r'\U0001F680-\U0001F6FF'  # 交通和地图符号
            r'\U0001F1E0-\U0001F1FF'  # 国旗（iOS）
            r'\U00002702-\U000027B0'  # 其他符号
            r'\U000024C2-\U0001F251]+', 
            flags=re.UNICODE
        )
    
    def format_content(self, content: str, content_type: str = 'ai') -> str:
        """
        将HTML内容转换为优化的Markdown格式
        
        特别处理：
        1. 代码块：保留语言标识和缩进
        2. 表格：转换为Markdown表格
        3. 列表：保持层级
        4. 链接：转换为Markdown链接
        5. 标题：确保正确的层级（从##开始）
        6. 清理：移除多余的HTML标签
        """
        if not content:
            return ""
        
        self.logger.debug(f"开始格式化内容，类型: {content_type}, 长度: {len(content)}")
        
        # 步骤1: 提取和保护代码块
        protected_content = self._protect_code_blocks(content)
        
        # 步骤2: 处理表格
        if self.extract_tables:
            protected_content = self._process_tables(protected_content)
        
        # 步骤3: 清理HTML标签
        if self.clean_html_tags:
            protected_content = self._clean_html_tags(protected_content)
        
        # 步骤4: 恢复代码块
        formatted_content = self._restore_code_blocks(protected_content)
        
        # 步骤5: 处理标题层级（AI回答从##开始）
        if content_type == 'ai':
            formatted_content = self._adjust_heading_levels(formatted_content)
        
        # 步骤6: 移除表情符号（如果配置）
        if self.remove_emojis:
            formatted_content = self._remove_emojis(formatted_content)
        
        # 步骤7: 规范化空白字符
        formatted_content = self._normalize_whitespace(formatted_content)
        
        # 步骤8: 确保以换行符结束
        formatted_content = formatted_content.rstrip() + '\n'
        
        self.logger.debug(f"格式化完成，新长度: {len(formatted_content)}")
        
        return formatted_content
    
    def _protect_code_blocks(self, content: str) -> Tuple[str, Dict[str, str]]:
        """保护代码块，防止后续处理破坏它们"""
        # 查找所有代码块
        code_blocks = {}
        protected_content = content
        
        def replace_code_block(match):
            """替换代码块为占位符"""
            language = match.group(1) or 'text'
            code = match.group(2)
            
            # 生成唯一ID
            block_id = f"__CODE_BLOCK_{len(code_blocks)}__"
            
            # 保存原始代码块
            code_blocks[block_id] = {
                'language': language,
                'code': code,
                'original': match.group(0)
            }
            
            return block_id
        
        # 替换所有代码块
        protected_content = self.code_block_pattern.sub(replace_code_block, protected_content)
        
        return protected_content, code_blocks
    
    def _process_tables(self, content: str) -> str:
        """处理表格，转换为Markdown格式"""
        # 这个功能比较复杂，这里先实现基本功能
        # 在实际实现中，可能需要使用更复杂的HTML表格解析
        
        # 查找简单的HTML表格模式
        html_table_pattern = re.compile(
            r'<table[^>]*>([\s\S]*?)</table>',
            re.IGNORECASE
        )
        
        def convert_html_table(match):
            """转换HTML表格为Markdown"""
            table_html = match.group(1)
            
            try:
                # 简单的表格转换逻辑
                # 在实际应用中，可能需要使用BeautifulSoup来解析表格结构
                rows = []
                
                # 提取行
                row_pattern = re.compile(r'<tr[^>]*>([\s\S]*?)</tr>', re.IGNORECASE)
                cell_pattern = re.compile(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', re.IGNORECASE)
                
                for row_match in row_pattern.finditer(table_html):
                    row_html = row_match.group(1)
                    cells = []
                    
                    for cell_match in cell_pattern.finditer(row_html):
                        cell_content = cell_match.group(1)
                        # 清理HTML标签
                        cell_content = re.sub(r'<[^>]+>', '', cell_content)
                        cell_content = cell_content.strip()
                        cells.append(cell_content)
                    
                    if cells:
                        rows.append(cells)
                
                if len(rows) >= 2:
                    # 生成Markdown表格
                    markdown_table = []
                    
                    # 表头
                    header = '| ' + ' | '.join(rows[0]) + ' |'
                    markdown_table.append(header)
                    
                    # 分隔线
                    separator = '| ' + ' | '.join(['---' for _ in rows[0]]) + ' |'
                    markdown_table.append(separator)
                    
                    # 数据行
                    for row in rows[1:]:
                        if len(row) == len(rows[0]):
                            markdown_table.append('| ' + ' | '.join(row) + ' |')
                    
                    return '\n'.join(markdown_table) + '\n\n'
                
            except Exception as e:
                self.logger.debug(f"表格转换失败: {e}")
            
            # 转换失败，返回原始HTML
            return f"\n<!-- 表格（原始HTML） -->\n{match.group(0)}\n<!-- 表格结束 -->\n"
        
        # 转换HTML表格
        content = html_table_pattern.sub(convert_html_table, content)
        
        return content
    
    def _clean_html_tags(self, content: str) -> str:
        """清理HTML标签"""
        if not content:
            return ""
        
        # 移除HTML注释
        content = re.sub(r'<!--[\s\S]*?-->', '', content)
        
        # 处理特定的HTML标签
        replacements = [
            (r'<br\s*/?>', '\n'),  # <br> 换行
            (r'<p[^>]*>', '\n\n'),  # <p> 段落
            (r'</p>', '\n\n'),
            (r'<div[^>]*>', '\n'),  # <div> 换行
            (r'</div>', '\n'),
            (r'<span[^>]*>', ''),  # <span> 移除
            (r'</span>', ''),
            (r'<strong[^>]*>', '**'),  # <strong> 加粗
            (r'</strong>', '**'),
            (r'<b[^>]*>', '**'),  # <b> 加粗
            (r'</b>', '**'),
            (r'<em[^>]*>', '*'),  # <em> 斜体
            (r'</em>', '*'),
            (r'<i[^>]*>', '*'),  # <i> 斜体
            (r'</i>', '*'),
            (r'<code[^>]*>', '`'),  # <code> 内联代码
            (r'</code>', '`'),
            (r'<pre[^>]*>', '\n```\n'),  # <pre> 代码块
            (r'</pre>', '\n```\n'),
            (r'<h1[^>]*>', '\n\n# '),  # <h1> 一级标题
            (r'</h1>', '\n\n'),
            (r'<h2[^>]*>', '\n\n## '),  # <h2> 二级标题
            (r'</h2>', '\n\n'),
            (r'<h3[^>]*>', '\n\n### '),  # <h3> 三级标题
            (r'</h3>', '\n\n'),
            (r'<h4[^>]*>', '\n\n#### '),  # <h4> 四级标题
            (r'</h4>', '\n\n'),
            (r'<h5[^>]*>', '\n\n##### '),  # <h5> 五级标题
            (r'</h5>', '\n\n'),
            (r'<h6[^>]*>', '\n\n###### '),  # <h6> 六级标题
            (r'</h6>', '\n\n'),
            (r'<ul[^>]*>', '\n'),  # <ul> 无序列表
            (r'</ul>', '\n'),
            (r'<ol[^>]*>', '\n'),  # <ol> 有序列表
            (r'</ol>', '\n'),
            (r'<li[^>]*>', '\n* '),  # <li> 列表项
            (r'</li>', ''),
            (r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r'[\2](\1)'),  # <a> 链接
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # 移除所有其他HTML标签
        content = self.html_tag_pattern.sub('', content)
        
        # 解码HTML实体
        content = html.unescape(content)
        
        return content
    
    def _restore_code_blocks(self, protected_content: str, code_blocks: Dict[str, Dict]) -> str:
        """恢复代码块"""
        content = protected_content
        
        for block_id, block_info in code_blocks.items():
            language = block_info['language']
            code = block_info['code']
            
            # 重新构建代码块
            code_block = f"```{language}\n{code}\n```"
            
            # 替换占位符
            content = content.replace(block_id, code_block)
        
        return content
    
    def _adjust_heading_levels(self, content: str, base_level: int = 2) -> str:
        """
        调整标题层级，确保AI回答中的标题从指定级别开始
        
        Args:
            content: Markdown内容
            base_level: 基础标题级别（1-6）
        
        Returns:
            调整后的内容
        """
        if base_level < 1 or base_level > 6:
            base_level = 2
        
        lines = content.split('\n')
        adjusted_lines = []
        
        for line in lines:
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                current_level = len(heading_match.group(1))
                heading_text = heading_match.group(2)
                
                # 计算新级别
                new_level = min(6, max(1, current_level + (base_level - 1)))
                new_heading = '#' * new_level + ' ' + heading_text
                
                adjusted_lines.append(new_heading)
            else:
                adjusted_lines.append(line)
        
        return '\n'.join(adjusted_lines)
    
    def _remove_emojis(self, content: str) -> str:
        """移除表情符号"""
        return self.emoji_pattern.sub('', content)
    
    def _normalize_whitespace(self, content: str) -> str:
        """规范化空白字符"""
        # 替换多个连续换行符为2个
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 移除行首尾的空格
        lines = [line.strip() for line in content.split('\n')]
        
        # 合并连续的空行
        normalized_lines = []
        prev_was_empty = False
        
        for line in lines:
            is_empty = not line.strip()
            
            if not is_empty:
                normalized_lines.append(line)
                prev_was_empty = False
            elif not prev_was_empty:
                normalized_lines.append('')
                prev_was_empty = True
        
        return '\n'.join(normalized_lines)
    
    def extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """从内容中提取代码块信息"""
        code_blocks = []
        
        for match in self.code_block_pattern.finditer(content):
            language = match.group(1) or 'text'
            code = match.group(2)
            lines = code.count('\n') + 1
            
            code_blocks.append({
                'language': language,
                'content': code,
                'lines': lines,
                'characters': len(code)
            })
        
        return code_blocks
    
    def extract_tables(self, content: str) -> List[Dict[str, Any]]:
        """从内容中提取表格"""
        tables = []
        
        for match in self.table_pattern.finditer(content):
            headers = [h.strip() for h in match.group(1).split('|') if h.strip()]
            rows_text = match.group(2)
            
            rows = []
            for row_line in rows_text.strip().split('\n'):
                cells = [c.strip() for c in row_line.split('|') if c.strip()]
                if len(cells) == len(headers):
                    rows.append(cells)
            
            if headers and rows:
                tables.append({
                    'headers': headers,
                    'rows': rows,
                    'row_count': len(rows),
                    'col_count': len(headers)
                })
        
        return tables
    
    def format_code_block(self, code: str, language: str = '') -> str:
        """格式化单个代码块"""
        # 添加语言标识
        if language:
            header = f"```{language}"
        else:
            header = "```"
        
        # 检查是否需要折叠
        lines = code.split('\n')
        should_fold = len(lines) > self.code_block_config['min_lines_for_folding']
        
        if should_fold:
            # 创建可折叠的代码块
            summary = f"{language} 代码 ({len(lines)} 行)"
            # 修复：避免在f-string中直接使用三个反引号
            formatted = f"""<details class="code-block" data-collapsed="true">
<summary>{summary}</summary>

{header}
{code}
```  <!-- 代码块结束标记 -->
</details>"""
        else:
            # 普通代码块 - 修复：避免在f-string中直接使用三个反引号
            formatted = f"""{header}
{code}
```  <!-- 代码块结束标记 -->"""
        
        return formatted
        