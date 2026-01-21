#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话记录结构化处理工具 CLI 版
功能：智能处理嵌套对话，生成清晰结构化的文档
优化：纯命令行，支持路径输入，智能处理混合内容
"""

import re
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
import hashlib


class ConversationArchitectCLI:
    """对话记录建筑师 CLI 版 - 纯命令行对话记录处理"""
    
    def __init__(self, input_path: str, output_path: str = None, suffix: str = "_organized"):
        """
        初始化对话处理器
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径（可选）
            suffix: 输出文件后缀（默认：_organized）
        """
        self.input_path = Path(input_path).resolve()
        
        # 设置输出路径
        if output_path:
            self.output_path = Path(output_path).resolve()
        else:
            # 使用默认后缀
            input_stem = self.input_path.stem
            input_parent = self.input_path.parent
            self.output_path = input_parent / f"{input_stem}{suffix}.md"
        
        # 确保输出目录存在
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 配置文件
        self.config = {
            "max_nesting_level": 6,
            "preserve_code_blocks": True,
            "auto_adjust_headings": True,
            "extract_key_points": True,
            "generate_summary": True,
            "generate_toc": True,
            "toc_max_depth": 4,
            "fix_single_hash": True,
            "smart_merge": True,  # 智能合并已优化和未优化内容
            "auto_update_existing_toc": True,  # 自动更新已有目录
            "add_main_title": True,  # 添加总标题
        }
        
        # 处理统计
        self.stats = {
            "input_file": str(self.input_path),
            "output_file": str(self.output_path),
            "dialogs_count": 0,
            "turns_count": 0,
            "headings_fixed": 0,
            "sections_merged": 0,
            "toc_updated": False,
            "processing_time": None,
            "file_size": {
                "input": 0,
                "output": 0
            }
        }
        
        print(f"[ConversationArchitectCLI] 初始化完成")
        print(f"  输入文件: {self.input_path}")
        print(f"  输出文件: {self.output_path}")
    
    def read_conversation_file(self) -> str:
        """读取对话文件"""
        try:
            with open(self.input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            self.stats["file_size"]["input"] = len(content)
            print(f"[√] 成功读取文件，大小: {len(content):,} 字符")
            return content
        except Exception as e:
            print(f"[×] 读取文件失败: {e}")
            return ""
    
    def detect_content_structure(self, content: str) -> Dict[str, Any]:
        """
        智能检测内容结构
        区分：已优化内容、原始对话、混合内容
        """
        structure = {
            "has_existing_toc": False,
            "toc_start": -1,
            "toc_end": -1,
            "main_title": "",
            "is_already_organized": False,
            "sections": [],
            "dialogs": []
        }
        
        lines = content.split('\n')
        
        # 检测是否已有目录
        for i, line in enumerate(lines):
            if re.match(r'^#{1,2}\s*[📑目录|Table of Contents]', line):
                structure["has_existing_toc"] = True
                structure["toc_start"] = i
                # 查找目录结束位置
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() == "" or re.match(r'^#{1,2}\s+', lines[j]):
                        structure["toc_end"] = j
                        break
                break
        
        # 检测是否已有总标题
        for i, line in enumerate(lines):
            if i < 5 and re.match(r'^#\s+[^#]', line):  # 前5行中的一级标题
                structure["main_title"] = line.strip()
                break
        
        # 检测是否已经是优化后的格式
        organized_markers = [
            '对话历史档案馆',
            '回合 \\d+:',
            '📋 指令',
            '🤖 响应'
        ]
        
        marker_count = 0
        for marker in organized_markers:
            if marker in content:
                marker_count += 1
        
        structure["is_already_organized"] = marker_count >= 2
        
        # 检测对话分段
        if structure["is_already_organized"]:
            print("[!] 检测到已优化的内容，将进行智能合并")
            return self._parse_organized_content(content, structure)
        else:
            print("[!] 检测到原始对话内容，将进行完整处理")
            return self._parse_raw_content(content, structure)
    
    def _parse_organized_content(self, content: str, structure: Dict) -> Dict:
        """解析已优化的内容"""
        lines = content.split('\n')
        
        # 提取现有标题结构
        current_section = None
        sections = []
        
        for i, line in enumerate(lines):
            # 检测章节标题
            if line.startswith('## ') and '对话-' in line:
                if current_section:
                    sections.append(current_section)
                
                # 提取对话信息
                dialog_match = re.match(r'^##\s+([^-\s]+)-?\s*(.+)$', line)
                if dialog_match:
                    dialog_id = dialog_match.group(1)
                    dialog_title = dialog_match.group(2)
                else:
                    dialog_id = f"dialog{len(sections)+1}"
                    dialog_title = line.replace('##', '').strip()
                
                current_section = {
                    "type": "dialog",
                    "dialog_id": dialog_id,
                    "title": dialog_title,
                    "start_line": i,
                    "end_line": -1,
                    "content": [line],
                    "turns": []
                }
            elif current_section:
                current_section["content"].append(line)
        
        # 添加最后一个章节
        if current_section:
            sections.append(current_section)
        
        structure["sections"] = sections
        
        # 提取对话内容
        dialogs = self._extract_dialogs_from_sections(sections)
        structure["dialogs"] = dialogs
        
        return structure
    
    def _parse_raw_content(self, content: str, structure: Dict) -> Dict:
        """解析原始内容"""
        # 检测对话分段
        dialogs = self.detect_conversation_sections(content)
        structure["dialogs"] = dialogs
        return structure
    
    def detect_conversation_sections(self, content: str) -> List[Dict]:
        """
        检测对话分段
        
        支持格式: 
        ## 对话-V001 标题
        # 对话-V001 标题
        ## 对话-001 标题
        """
        # 正则匹配对话标题
        dialog_pattern = r'^(?:#{1,2})\s+对话-([A-Za-z0-9]+)\s+(.+?)(?=^(?:#{1,2})\s+对话-|\Z)'
        
        # 由于对话可能跨越多行，我们逐行处理
        lines = content.split('\n')
        dialogs = []
        current_dialog = None
        dialog_content = []
        dialog_start_line = 0
        
        for i, line in enumerate(lines):
            # 检测对话开始
            match = re.match(r'^(#{1,2})\s+对话-([A-Za-z0-9]+)\s+(.+)$', line)
            if match:
                # 保存前一个对话（如果有）
                if current_dialog is not None:
                    current_dialog["content"] = '\n'.join(dialog_content)
                    current_dialog["end_line"] = i - 1
                    dialogs.append(current_dialog)
                
                # 开始新对话
                level = len(match.group(1))
                dialog_id = match.group(2)
                dialog_title = match.group(3).strip()
                
                current_dialog = {
                    "id": dialog_id,
                    "raw_title": line,
                    "title": dialog_title,
                    "starting_level": level,
                    "content": "",
                    "start_line": i,
                    "end_line": -1,
                    "turns": [],
                    "metadata": {
                        "starting_line": i,
                        "raw_level": level,
                        "is_processed": False
                    }
                }
                
                dialog_content = [line]
                dialog_start_line = i
            elif current_dialog is not None:
                dialog_content.append(line)
        
        # 添加最后一个对话
        if current_dialog is not None:
            current_dialog["content"] = '\n'.join(dialog_content)
            current_dialog["end_line"] = len(lines) - 1
            dialogs.append(current_dialog)
        
        # 如果没有检测到对话格式，尝试其他格式
        if not dialogs:
            print("[!] 未检测到标准对话格式，尝试其他检测方法...")
            dialogs = self._detect_alternative_sections(content)
        
        # 处理每个对话的回合
        total_turns = 0
        for dialog in dialogs:
            dialog_turns = self.extract_conversation_turns(dialog)
            dialog["turns"] = dialog_turns
            total_turns += len(dialog_turns)
        
        self.stats["dialogs_count"] = len(dialogs)
        self.stats["turns_count"] = total_turns
        
        print(f"[√] 检测到 {len(dialogs)} 个对话，共 {total_turns} 个回合")
        return dialogs
    
    def _detect_alternative_sections(self, content: str) -> List[Dict]:
        """检测非标准格式的对话分段"""
        lines = content.split('\n')
        sections = []
        current_section = None
        section_content = []
        
        for i, line in enumerate(lines):
            # 检测任何标题（1-3级）
            if re.match(r'^#{1,3}\s+', line):
                # 保存前一个章节
                if current_section is not None:
                    current_section["content"] = '\n'.join(section_content)
                    sections.append(current_section)
                
                # 开始新章节
                level = len(re.match(r'^(#+)', line).group(1))
                title = line.replace('#', '').strip()
                
                # 尝试提取ID
                id_match = re.search(r'([A-Za-z0-9]+)', title.split()[0] if title else '')
                dialog_id = id_match.group(1) if id_match else f"s{len(sections)+1:03d}"
                
                current_section = {
                    "id": dialog_id,
                    "raw_title": line,
                    "title": title,
                    "starting_level": level,
                    "content": "",
                    "start_line": i,
                    "end_line": -1,
                    "turns": [],
                    "metadata": {
                        "starting_line": i,
                        "raw_level": level,
                        "is_processed": False
                    }
                }
                
                section_content = [line]
            elif current_section is not None:
                section_content.append(line)
        
        # 添加最后一个章节
        if current_section is not None:
            current_section["content"] = '\n'.join(section_content)
            sections.append(current_section)
        
        return sections
    
    def _extract_dialogs_from_sections(self, sections: List[Dict]) -> List[Dict]:
        """从已有章节中提取对话"""
        dialogs = []
        
        for section in sections:
            if section["type"] == "dialog":
                # 已经是对话格式
                dialog = {
                    "id": section["dialog_id"],
                    "raw_title": f"## {section['dialog_id']} - {section['title']}",
                    "title": section["title"],
                    "content": '\n'.join(section["content"]),
                    "turns": self.extract_conversation_turns_from_content('\n'.join(section["content"])),
                    "metadata": {
                        "starting_line": section["start_line"],
                        "raw_level": 2,
                        "is_processed": True
                    }
                }
                dialogs.append(dialog)
        
        return dialogs
    
    def extract_conversation_turns(self, dialog: Dict) -> List[Dict]:
        """
        提取对话中的每个回合（指令-响应对）
        
        支持格式: 
        ### AA我的指令
        ### WW我的指令
        ## 我的指令
        # 我的指令
        """
        return self.extract_conversation_turns_from_content(dialog["content"])
    
    def extract_conversation_turns_from_content(self, content: str) -> List[Dict]:
        """从内容中提取对话回合"""
        lines = content.split('\n')
        turns = []
        
        # 支持多种指令格式
        instruction_patterns = [
            (r'^(#{1,3})\s+([A-Z]{2})我的指令\s*\n?', 'AA我的指令'),  # ### AA我的指令
            (r'^(#{1,3})\s+我的指令\s*\n?', '我的指令'),  # ### 我的指令
            (r'^(#{1,3})\s+指令\s*\n?', '指令'),  # ### 指令
            (r'^(#{1,3})\s+Q\s*\n?', 'Q'),  # ### Q
        ]
        
        current_turn = None
        turn_lines = []
        in_turn = False
        
        for i, line in enumerate(lines):
            # 检查是否是指令行
            is_instruction = False
            instruction_type = "未知指令"
            
            for pattern, itype in instruction_patterns:
                match = re.match(pattern, line)
                if match:
                    is_instruction = True
                    instruction_type = itype
                    break
            
            if is_instruction:
                # 保存前一个回合
                if current_turn is not None and turn_lines:
                    turn_content = '\n'.join(turn_lines)
                    self._finalize_turn(current_turn, turn_content)
                    turns.append(current_turn)
                
                # 开始新回合
                current_turn = {
                    "turn_id": len(turns) + 1,
                    "instruction_type": instruction_type,
                    "raw_instruction_line": line,
                    "instruction": "",
                    "response": "",
                    "metadata": {
                        "line_number": i,
                        "is_processed": False
                    }
                }
                
                turn_lines = [line]
                in_turn = True
            elif in_turn:
                turn_lines.append(line)
        
        # 添加最后一个回合
        if current_turn is not None and turn_lines:
            turn_content = '\n'.join(turn_lines)
            self._finalize_turn(current_turn, turn_content)
            turns.append(current_turn)
        
        # 如果没有检测到指令，将整个内容作为一个回合
        if not turns:
            turns.append({
                "turn_id": 1,
                "instruction_type": "完整内容",
                "instruction": "完整对话",
                "response": content,
                "metadata": {
                    "line_number": 0,
                    "is_processed": False
                }
            })
        
        return turns
    
    def _finalize_turn(self, turn: Dict, content: str):
        """完成回合内容提取"""
        lines = content.split('\n')
        
        # 第一行是指令行
        instruction_line = lines[0] if lines else ""
        
        # 提取指令文本（指令行之后的内容，直到下一个标题或结束）
        instruction_text_lines = []
        response_lines = []
        
        in_instruction = True
        for line in lines[1:]:
            # 检查是否开始响应部分
            if in_instruction and (line.strip() == '' or re.match(r'^#{1,6}\s', line)):
                in_instruction = False
            
            if in_instruction:
                instruction_text_lines.append(line)
            else:
                response_lines.append(line)
        
        turn["instruction"] = '\n'.join(instruction_text_lines).strip()
        turn["response"] = '\n'.join(response_lines).strip()
        
        # 提取附加信息
        turn["has_nesting"] = self._check_nesting(turn["response"])
        turn["code_blocks"] = self._extract_code_blocks(turn["response"])
        turn["tables"] = self._extract_tables(turn["response"])
        turn["diagrams"] = self._extract_diagrams(turn["response"])
        turn["action_items"] = self._extract_action_items(turn["response"])
    
    def _check_nesting(self, content: str) -> bool:
        """检查内容中是否存在标题嵌套问题"""
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        headings = []
        
        for line in content.split('\n'):
            match = re.match(heading_pattern, line)
            if match:
                level = len(match.group(1))
                headings.append(level)
        
        # 如果标题层级超过4级或存在跳跃，认为有嵌套问题
        if len(headings) > 1:
            max_level = max(headings) if headings else 0
            
            # 检查层级跳跃
            for i in range(1, len(headings)):
                if headings[i] - headings[i-1] > 2:
                    return True
            
            # 如果最大层级很深，可能有问题
            if max_level > 5:
                return True
        
        return False
    
    def _extract_code_blocks(self, content: str) -> List[Dict]:
        """提取代码块"""
        code_blocks = []
        pattern = r'```([a-zA-Z0-9_+-]*)\n(.*?)```'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            
            code_blocks.append({
                "language": language,
                "code": code,
                "length": len(code),
                "lines": code.count('\n') + 1
            })
        
        return code_blocks
    
    def _extract_tables(self, content: str) -> List[Dict]:
        """提取表格"""
        tables = []
        lines = content.split('\n')
        
        in_table = False
        table_lines = []
        table_start = 0
        
        for i, line in enumerate(lines):
            if '|' in line and line.count('|') >= 2:
                if not in_table:
                    in_table = True
                    table_start = i
                table_lines.append(line)
            elif in_table:
                # 表格结束
                if table_lines:
                    row_count = len([l for l in table_lines if '|' in l and '---' not in l])
                    col_count = table_lines[0].count('|') - 1 if table_lines else 0
                    
                    tables.append({
                        "start_line": table_start,
                        "lines": table_lines.copy(),
                        "row_count": row_count,
                        "col_count": col_count
                    })
                in_table = False
                table_lines = []
        
        # 处理最后一个表格
        if in_table and table_lines:
            row_count = len([l for l in table_lines if '|' in l and '---' not in l])
            col_count = table_lines[0].count('|') - 1 if table_lines else 0
            
            tables.append({
                "start_line": table_start,
                "lines": table_lines.copy(),
                "row_count": row_count,
                "col_count": col_count
            })
        
        return tables
    
    def _extract_diagrams(self, content: str) -> List[Dict]:
        """提取图表和流程图"""
        diagrams = []
        
        # Mermaid 图表
        mermaid_pattern = r'```mermaid\s*\n(.*?)```'
        for match in re.finditer(mermaid_pattern, content, re.DOTALL):
            diagrams.append({
                "type": "mermaid",
                "content": match.group(1).strip(),
                "lines": match.group(1).count('\n') + 1
            })
        
        return diagrams
    
    def _extract_action_items(self, content: str) -> List[Dict]:
        """提取行动项"""
        action_items = []
        
        patterns = [
            (r'^\s*[-*•]\s*(?:\[[ x]?\])?\s*(.+?)(?:\n|$)', 'bullet'),
            (r'^\d+\.\s*(.+?)(?:\n|$)', 'numbered'),
            (r'(?:下一步|行动|任务|TODO|待办|行动项)[：:]\s*(.+?)(?:\n|$)', 'labeled'),
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            for pattern, pattern_type in patterns:
                matches = re.findall(pattern, line_stripped, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match_text = match[0]
                    else:
                        match_text = match
                    
                    match_text = match_text.strip()
                    if match_text and len(match_text) > 2:
                        action_items.append({
                            "text": match_text,
                            "line": line_num + 1,
                            "type": pattern_type,
                            "original": line_stripped
                        })
        
        return action_items
    
    def fix_all_headings(self, content: str, base_level: int = 2) -> Tuple[str, List[Dict]]:
        """
        修复所有标题层级，包括单个#开头的标题
        
        Args:
            content: 原始内容
            base_level: 基础层级
            
        Returns:
            (修复后的内容, 标题信息列表)
        """
        lines = content.split('\n')
        fixed_lines = []
        headings_info = []
        
        current_context = 'normal'
        code_block_language = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 检测代码块
            if line.strip().startswith('```'):
                fixed_lines.append(line)
                
                if current_context == 'code_block':
                    current_context = 'normal'
                    code_block_language = None
                else:
                    language_match = re.match(r'^```([a-zA-Z0-9_+-]*)', line)
                    code_block_language = language_match.group(1) if language_match else None
                    current_context = 'code_block'
                
                i += 1
                continue
            
            # 在代码块中不处理标题
            if current_context == 'code_block':
                fixed_lines.append(line)
                i += 1
                continue
            
            # 检测表格
            if '|' in line and ('---' in line or '--' in line or '===' in line):
                current_context = 'table'
                fixed_lines.append(line)
                i += 1
                continue
            elif current_context == 'table' and '|' not in line:
                current_context = 'normal'
            
            # 处理标题行
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                original_level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # 修复单个#开头的标题
                if original_level == 1 and self.config["fix_single_hash"]:
                    # 单个#通常是文档标题
                    new_level = 1
                else:
                    # 计算新的层级
                    if "对话-" in title_text:
                        new_level = base_level
                    elif "我的指令" in title_text or "回合" in title_text:
                        new_level = base_level + 1
                    elif original_level <= 2:
                        new_level = base_level + 2
                    else:
                        new_level = min(original_level + 2, self.config["max_nesting_level"])
                
                # 确保层级合理
                new_level = max(1, min(new_level, self.config["max_nesting_level"]))
                
                # 生成新的标题行
                new_heading = '#' * new_level + ' ' + title_text
                fixed_lines.append(new_heading)
                
                # 记录标题信息
                if new_level <= self.config["toc_max_depth"]:
                    headings_info.append({
                        "level": new_level,
                        "text": title_text,
                        "original_level": original_level,
                        "line_num": i + 1
                    })
                
                # 统计修复的标题
                if original_level != new_level:
                    self.stats["headings_fixed"] += 1
            else:
                fixed_lines.append(line)
            
            i += 1
        
        fixed_content = '\n'.join(fixed_lines)
        return fixed_content, headings_info
    
    def generate_table_of_contents(self, headings: List[Dict], existing_toc: str = None) -> str:
        """
        生成目录，可基于现有目录更新
        
        Args:
            headings: 标题信息列表
            existing_toc: 现有目录内容（可选）
            
        Returns:
            目录字符串
        """
        if not headings or not self.config["generate_toc"]:
            return ""
        
        # 如果有现有目录且启用了智能更新
        if existing_toc and self.config["auto_update_existing_toc"]:
            print("[!] 检测到现有目录，尝试智能更新...")
            return self._update_existing_toc(existing_toc, headings)
        
        # 生成新目录
        toc_lines = ["## 📑 目录", ""]
        
        for heading in headings:
            level = heading["level"]
            text = heading["text"]
            
            # 为标题生成锚点
            anchor = self._create_anchor(text)
            
            # 根据层级添加缩进
            indent = "  " * (level - 1)
            
            # 创建目录项
            if level == 1:
                toc_lines.append(f"{indent}- [{text}](#{anchor})")
            else:
                bullet = "•" if level <= 3 else "◦"
                toc_lines.append(f"{indent}  {bullet} [{text}](#{anchor})")
        
        toc_lines.append("")
        toc_lines.append("---")
        toc_lines.append("")
        
        return '\n'.join(toc_lines)
    
    def _update_existing_toc(self, existing_toc: str, new_headings: List[Dict]) -> str:
        """更新现有目录"""
        # 解析现有目录
        toc_lines = existing_toc.split('\n')
        
        # 提取现有条目
        existing_items = []
        for line in toc_lines:
            match = re.search(r'\[([^\]]+)\]\(#([^)]+)\)', line)
            if match:
                existing_items.append({
                    "text": match.group(1),
                    "anchor": match.group(2)
                })
        
        # 合并新旧条目
        merged_items = []
        
        # 首先添加新标题
        for heading in new_headings:
            anchor = self._create_anchor(heading["text"])
            
            # 检查是否已存在
            exists = any(item["text"] == heading["text"] for item in existing_items)
            
            if not exists:
                indent = "  " * (heading["level"] - 1)
                bullet = "•" if heading["level"] <= 3 else "◦"
                merged_items.append({
                    "level": heading["level"],
                    "text": heading["text"],
                    "anchor": anchor,
                    "line": f"{indent}  {bullet} [{heading['text']}](#{anchor})",
                    "is_new": True
                })
                self.stats["sections_merged"] += 1
        
        # 添加现有条目（保留顺序）
        for item in existing_items:
            # 找到对应的标题层级
            heading_level = 2  # 默认
            for heading in new_headings:
                if self._create_anchor(heading["text"]) == item["anchor"]:
                    heading_level = heading["level"]
                    break
            
            indent = "  " * (heading_level - 1)
            bullet = "•" if heading_level <= 3 else "◦"
            merged_items.append({
                "level": heading_level,
                "text": item["text"],
                "anchor": item["anchor"],
                "line": f"{indent}  {bullet} [{item['text']}](#{item['anchor']})",
                "is_new": False
            })
        
        # 按层级和是否为新的排序
        merged_items.sort(key=lambda x: (x["level"], x["is_new"]))
        
        # 重新构建目录
        updated_toc_lines = ["## 📑 目录", ""]
        
        for item in merged_items:
            if item["is_new"]:
                updated_toc_lines.append(f"{item['line']} *(新)*")
            else:
                updated_toc_lines.append(item["line"])
        
        updated_toc_lines.append("")
        updated_toc_lines.append("---")
        updated_toc_lines.append("")
        
        return '\n'.join(updated_toc_lines)
    
    def _create_anchor(self, text: str) -> str:
        """为标题创建锚点ID"""
        anchor = re.sub(r'[^\w\s-]', '', text)
        anchor = re.sub(r'[-\s]+', '-', anchor)
        anchor = anchor.lower().strip('-')
        
        if not anchor:
            anchor_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            anchor = f"section-{anchor_hash}"
        
        return anchor
    
    def get_main_title(self, existing_title: str = "") -> str:
        """获取主标题"""
        if existing_title and self.config["add_main_title"]:
            # 如果已有标题，使用它
            return existing_title
        
        # 生成新标题
        if self.config["add_main_title"]:
            filename = self.input_path.stem
            return f"# 📚 {filename} - 对话历史档案馆"
        
        return ""
    
    def reorganize_content(self, structure: Dict[str, Any]) -> str:
        """
        重新组织内容，创建清晰的文档
        
        Args:
            structure: 内容结构信息
            
        Returns:
            重新组织后的内容
        """
        output_lines = []
        all_headings = []
        
        # 添加主标题
        main_title = self.get_main_title(structure.get("main_title", ""))
        if main_title:
            output_lines.append(main_title)
            output_lines.append("")
            
            # 记录主标题
            all_headings.append({
                "level": 1,
                "text": main_title.replace('#', '').strip(),
                "original_level": 1,
                "line_num": 0
            })
        
        # 处理每个对话
        for dialog in structure["dialogs"]:
            dialog_id = dialog["id"]
            dialog_title = dialog["title"]
            
            # 对话标题
            dialog_heading = f'## {dialog_id} - {dialog_title}'
            output_lines.append(dialog_heading)
            output_lines.append('')
            
            # 记录对话标题
            all_headings.append({
                "level": 2,
                "text": f"{dialog_id} - {dialog_title}",
                "original_level": 2,
                "line_num": len(output_lines) - 2
            })
            
            # 对话元数据
            output_lines.append('**对话信息**')
            output_lines.append(f'- **对话ID**: `{dialog_id}`')
            output_lines.append(f'- **对话标题**: {dialog_title}')
            output_lines.append(f'- **对话轮次**: {len(dialog["turns"])}')
            output_lines.append('')
            
            # 处理每个回合
            for turn in dialog["turns"]:
                turn_id = turn["turn_id"]
                instruction_type = turn["instruction_type"]
                
                # 回合标题
                turn_heading = f'### 回合 {turn_id}: {instruction_type}'
                output_lines.append(turn_heading)
                output_lines.append('')
                
                # 记录回合标题
                all_headings.append({
                    "level": 3,
                    "text": f"回合 {turn_id}: {instruction_type}",
                    "original_level": 3,
                    "line_num": len(output_lines) - 2
                })
                
                # 指令内容
                output_lines.append('#### 📋 指令')
                if turn["instruction"]:
                    output_lines.append('```')
                    output_lines.append(turn["instruction"])
                    output_lines.append('```')
                else:
                    output_lines.append('*(无指令文本)*')
                output_lines.append('')
                
                # 响应内容（修复嵌套）
                output_lines.append('#### 🤖 响应')
                fixed_response, response_headings = self.fix_all_headings(
                    turn["response"], 
                    base_level=4  # 响应从4级开始
                )
                output_lines.append(fixed_response)
                
                # 记录响应中的标题
                for heading in response_headings:
                    heading["line_num"] += len(output_lines) - fixed_response.count('\n') - 2
                    all_headings.append(heading)
                
                # 回合元数据
                if self.config["extract_key_points"]:
                    has_elements = False
                    elements_lines = []
                    
                    if turn["code_blocks"]:
                        has_elements = True
                        elements_lines.append('##### 💻 本回合代码块')
                        for cb in turn["code_blocks"]:
                            elements_lines.append(f'- `{cb["language"]}`: {cb["lines"]}行，{cb["length"]}字符')
                    
                    if turn["tables"]:
                        has_elements = True
                        elements_lines.append('##### 📊 本回合表格')
                        for table in turn["tables"]:
                            elements_lines.append(f'- {table["row_count"]}行 × {table["col_count"]}列表格')
                    
                    if turn["action_items"]:
                        has_elements = True
                        elements_lines.append('##### ✅ 本回合行动项')
                        for action in turn["action_items"][:5]:
                            elements_lines.append(f'- {action["text"]}')
                        if len(turn["action_items"]) > 5:
                            elements_lines.append(f'- ... 还有 {len(turn["action_items"]) - 5} 个行动项')
                    
                    if has_elements:
                        output_lines.extend(elements_lines)
                        output_lines.append('')
                
                output_lines.append('---')
                output_lines.append('')
        
        # 生成目录
        if self.config["generate_toc"] and all_headings:
            existing_toc = None
            if structure["has_existing_toc"]:
                # 提取现有目录内容
                lines = structure.get("full_content", "").split('\n')
                toc_start = structure["toc_start"]
                toc_end = structure["toc_end"] if structure["toc_end"] > 0 else len(lines)
                
                if 0 <= toc_start < toc_end <= len(lines):
                    existing_toc = '\n'.join(lines[toc_start:toc_end])
            
            toc_content = self.generate_table_of_contents(all_headings, existing_toc)
            
            if toc_content:
                # 将目录插入到主标题之后
                header_end = 0
                for i, line in enumerate(output_lines):
                    if line.startswith('# ') and i < len(output_lines) - 1:
                        if output_lines[i+1] == '':
                            header_end = i + 2
                            break
                
                # 插入目录
                if header_end > 0:
                    toc_lines = toc_content.split('\n')
                    output_lines = output_lines[:header_end] + toc_lines + output_lines[header_end:]
                    self.stats["toc_updated"] = True
        
        return '\n'.join(output_lines)
    
    def generate_summary_report(self, structure: Dict[str, Any]) -> str:
        """生成总结报告"""
        summary_lines = []
        
        summary_lines.append(f'# 📊 对话分析报告 - {self.input_path.name}')
        summary_lines.append('')
        summary_lines.append(f'**报告生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        summary_lines.append(f'**分析工具**: ConversationArchitect CLI v1.0')
        summary_lines.append('')
        
        # 总体统计
        summary_lines.append('## 📈 总体统计')
        summary_lines.append('')
        summary_lines.append(f'- **输入文件**: {self.input_path.name}')
        summary_lines.append(f'- **文件大小**: {self.stats["file_size"]["input"]:,} 字符')
        summary_lines.append(f'- **对话总数**: {self.stats["dialogs_count"]}')
        summary_lines.append(f'- **对话轮次总数**: {self.stats["turns_count"]}')
        summary_lines.append(f'- **修复标题数**: {self.stats["headings_fixed"]}')
        summary_lines.append(f'- **合并章节数**: {self.stats["sections_merged"]}')
        summary_lines.append(f'- **目录更新**: {"是" if self.stats["toc_updated"] else "否"}')
        summary_lines.append('')
        
        # 对话详情
        summary_lines.append('## 📅 对话详情')
        summary_lines.append('')
        
        for dialog in structure["dialogs"]:
            summary_lines.append(f'### {dialog["id"]}: {dialog["title"]}')
            summary_lines.append(f'  - **轮次**: {len(dialog["turns"])}')
            
            # 统计指令类型
            instruction_types = {}
            for turn in dialog["turns"]:
                itype = turn["instruction_type"]
                instruction_types[itype] = instruction_types.get(itype, 0) + 1
            
            if instruction_types:
                type_str = ', '.join([f'{k}({v})' for k, v in instruction_types.items()])
                summary_lines.append(f'  - **指令类型**: {type_str}')
            
            summary_lines.append('')
        
        # 处理建议
        summary_lines.append('## 💡 处理建议')
        summary_lines.append('')
        
        if self.stats["headings_fixed"] > 0:
            summary_lines.append(f'1. **标题层级已修复**: {self.stats["headings_fixed"]}个标题层级已调整')
        
        if self.stats["sections_merged"] > 0:
            summary_lines.append(f'2. **内容已合并**: {self.stats["sections_merged"]}个新章节已添加到目录')
        
        if self.stats["toc_updated"]:
            summary_lines.append('3. **目录已更新**: 文档目录已更新以反映最新内容')
        
        if len(structure["dialogs"]) > 5:
            summary_lines.append('4. **对话较多**: 建议考虑将长对话拆分为多个文件')
        
        summary_lines.append('')
        summary_lines.append('---')
        summary_lines.append('*报告结束*')
        
        return '\n'.join(summary_lines)
    
    def save_output_file(self, content: str) -> Path:
        """保存输出文件"""
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 更新统计
            file_size = len(content.encode('utf-8'))
            self.stats["file_size"]["output"] = file_size
            
            print(f"[√] 已保存: {self.output_path} ({file_size:,} 字节)")
            return self.output_path
        except Exception as e:
            print(f"[×] 保存文件失败: {e}")
            raise
    
    def export_statistics_json(self) -> Path:
        """导出处理统计为JSON"""
        if self.stats["processing_time"] is None:
            self.stats["processing_time"] = datetime.now().isoformat()
        
        # 计算处理摘要
        self.stats["summary"] = {
            "status": "success",
            "dialogs_processed": self.stats["dialogs_count"],
            "turns_processed": self.stats["turns_count"],
            "file_saved": str(self.output_path)
        }
        
        output_path = self.output_path.parent / f"{self.output_path.stem}_statistics.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        print(f"[√] 统计信息已导出: {output_path}")
        return output_path
    
    def process(self) -> Dict[str, Any]:
        """
        主处理流程
        
        Returns:
            处理结果字典
        """
        print("\n" + "="*60)
        print("🤖 ConversationArchitect CLI - 开始处理对话记录")
        print("="*60)
        
        start_time = datetime.now()
        
        try:
            # 1. 读取文件
            print("\n[1/5] 📖 读取对话文件...")
            content = self.read_conversation_file()
            if not content:
                return {"success": False, "error": "无法读取文件或文件为空"}
            
            # 2. 分析内容结构
            print("[2/5] 🔍 分析内容结构...")
            structure = self.detect_content_structure(content)
            structure["full_content"] = content
            
            if not structure["dialogs"]:
                return {"success": False, "error": "未检测到对话内容"}
            
            # 3. 重新组织内容
            print("[3/5] 🏗️ 重新组织内容...")
            organized_content = self.reorganize_content(structure)
            
            # 4. 生成总结报告
            print("[4/5] 📊 生成总结报告...")
            summary_content = self.generate_summary_report(structure)
            
            # 5. 保存输出文件
            print("[5/5] 💾 保存输出文件...")
            
            # 保存主要文档
            main_doc_path = self.save_output_file(organized_content)
            
            # 保存总结报告
            summary_path = self.output_path.parent / f"{self.output_path.stem}_summary.md"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            print(f"[√] 总结报告已保存: {summary_path}")
            
            # 导出统计
            stats_path = self.export_statistics_json()
            
            # 计算处理时间
            end_time = datetime.now()
            processing_duration = end_time - start_time
            self.stats["processing_duration_seconds"] = processing_duration.total_seconds()
            
            print("\n" + "="*60)
            print("🎉 处理完成！")
            print("="*60)
            print(f"📊 处理统计:")
            print(f"  - 对话数量: {self.stats['dialogs_count']}")
            print(f"  - 回合数量: {self.stats['turns_count']}")
            print(f"  - 修复标题: {self.stats['headings_fixed']}")
            print(f"  - 合并章节: {self.stats['sections_merged']}")
            print(f"  - 处理时间: {processing_duration.total_seconds():.2f}秒")
            print(f"\n📁 输出文件:")
            print(f"  📄 {main_doc_path.name}")
            print(f"  📊 {summary_path.name}")
            print(f"  📋 {stats_path.name}")
            print(f"\n📂 输出目录: {self.output_path.parent}")
            print("="*60)
            
            return {
                "success": True,
                "dialogs_count": self.stats["dialogs_count"],
                "turns_count": self.stats["turns_count"],
                "headings_fixed": self.stats["headings_fixed"],
                "sections_merged": self.stats["sections_merged"],
                "processing_time": processing_duration.total_seconds(),
                "output_files": {
                    "main": str(main_doc_path),
                    "summary": str(summary_path),
                    "statistics": str(stats_path)
                }
            }
            
        except Exception as e:
            print(f"\n❌ 处理过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='对话记录结构化处理工具 CLI 版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s "对话记录.md"                    # 基本使用（输出到同目录）
  %(prog)s "对话记录.md" -o "输出文件.md"    # 指定输出文件
  %(prog)s "对话记录.md" -s "_clean"        # 指定输出文件后缀
  %(prog)s "对话记录.md" --no-toc           # 不生成目录
  %(prog)s "对话记录.md" --no-title         # 不添加总标题
        """
    )
    
    parser.add_argument(
        'input',
        help='输入文件路径（必须）'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='输出文件路径（可选，默认：输入文件_organized.md）'
    )
    
    parser.add_argument(
        '-s', '--suffix',
        dest='suffix',
        default='_organized',
        help='输出文件后缀（当不指定-o时使用，默认：_organized）'
    )
    
    parser.add_argument(
        '--no-toc',
        action='store_true',
        help='不生成目录'
    )
    
    parser.add_argument(
        '--no-title',
        action='store_true',
        help='不添加总标题'
    )
    
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='不生成总结报告'
    )
    
    parser.add_argument(
        '--no-merge',
        action='store_true',
        help='不合并已优化内容'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细处理信息'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    print("="*60)
    print("🤖 ConversationArchitect CLI v1.0")
    print("纯命令行对话记录处理工具")
    print("="*60)
    
    # 检查输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 错误：输入文件不存在 - {args.input}")
        sys.exit(1)
    
    if not input_path.is_file():
        print(f"❌ 错误：输入路径不是文件 - {args.input}")
        sys.exit(1)
    
    # 创建处理器
    try:
        architect = ConversationArchitectCLI(
            input_path=str(input_path),
            output_path=args.output_file,
            suffix=args.suffix
        )
        
        # 根据参数调整配置
        if args.no_toc:
            architect.config["generate_toc"] = False
        
        if args.no_title:
            architect.config["add_main_title"] = False
        
        if args.no_summary:
            architect.config["generate_summary"] = False
        
        if args.no_merge:
            architect.config["smart_merge"] = False
        
        # 处理对话
        result = architect.process()
        
        if result["success"]:
            print("\n✅ 处理成功完成！")
            print("\n📋 下一步建议:")
            print(f"1. 打开 '{Path(result['output_files']['main']).name}' 查看结构化对话")
            print(f"2. 查看 '{Path(result['output_files']['summary']).name}' 获取分析报告")
            print(f"3. 使用 '{Path(result['output_files']['statistics']).name}' 进行数据分析")
            print(f"4. 如需重新处理，删除输出文件并重新运行本程序")
        else:
            print(f"\n❌ 处理失败: {result.get('error', '未知错误')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序执行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()