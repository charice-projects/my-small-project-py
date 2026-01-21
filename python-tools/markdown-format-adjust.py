#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown格式智能调整工具 (MFAT)
专门解决对话记录中的结构嵌套问题，优化AI查阅体验
版本：3.1.0
核心策略：取消文档大标题 + 智能标题层级压缩 + 结构保留
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

class MarkdownFormatAdjust:
    """
    Markdown格式智能调整工具 (MFAT)
    核心目标：优化文档结构，便于AI快速查阅和学习
    """
    
    VERSION = "3.1.0"
    DEFAULT_SUFFIX = "_adjusted"
    
    # 响应开始标记（用于检测AI回答开始）
    RESPONSE_MARKERS = [
        r'^#{1,3}\s+(响应|Response|回答|回复|Output|🤖|📝|💡)',
        r'^(作为|As an|I am|I\'m an|I\'m a)',
        r'^(好的|收到|我明白了|我来|根据)',
        r'^(首先|第一|接下来|然后|最后|总的来说)',
        r'^\*\*\*+\s*$',  # 分隔线
        r'^---+\s*$',
        r'^===+\s*$',
    ]
    
    # 指令标记（用于检测用户指令）
    INSTRUCTION_MARKERS = [
        r'^#{1,3}\s+([A-Z]{2})?我的指令\s*',
        r'^#{1,3}\s+指令\s*',
        r'^#{1,3}\s+Q\s*',
        r'^#{1,3}\s+问题\s*',
        r'^#{1,3}\s+要求\s*',
    ]

    def __init__(self, config: Dict = None):
        """
        初始化MFAT工具
        
        Args:
            config: 配置字典
        """
        # 默认配置 - 针对AI查阅优化
        self.config = {
            # 文件处理
            "input_file": None,
            "output_file": None,
            "suffix": self.DEFAULT_SUFFIX,
            "encoding": "utf-8",
            
            # AI内容处理 - 核心配置
            "ai_processing": "smart_compress",  # smart_compress, remap, preserve
            "ai_max_level": 6,  # AI内容最高标题级别
            "ai_min_level": 3,  # AI内容最低标题级别 (从###开始)
            "preserve_structure": True,  # 保留AI回答的结构层次
            "compress_ratio": 0.7,  # 压缩比例，越高保留越多层级
            
            # 结构处理
            "generate_toc": True,
            "toc_max_depth": 3,
            "exclude_instructions_from_toc": True,
            "exclude_ai_headings_from_toc": True,
            
            # 格式处理
            "collapse_blank_lines": True,
            "max_blank_lines": 2,
            "trim_trailing_spaces": True,
            "normalize_headings": True,
            "remove_document_title": True,  # 取消文档大标题
            
            # 交互模式
            "interactive": False,
            "verbose": False,
            "quiet": False,
            
            # 特殊处理
            "detect_dialog_sections": True,
            "fix_markdown_links": True,
            "add_metadata_footer": True,  # 添加元数据脚注
        }
        
        # 更新用户配置
        if config:
            self.config.update(config)
        
        # 处理统计
        self.stats = {
            "input_file": None,
            "output_file": None,
            "dialogs": 0,
            "instructions": 0,
            "responses": 0,
            "headings_processed": 0,
            "headings_compressed": 0,
            "blank_lines_collapsed": 0,
            "processing_time": None,
            "file_size": {
                "input": 0,
                "output": 0
            },
            "structure_preserved": True,
        }
        
        # 状态跟踪
        self.state = {
            "in_code_block": False,
            "code_block_language": "",
            "current_dialog": None,
            "current_instruction": None,
            "ai_heading_levels": [],  # 记录AI标题层级分布
        }

    def print_banner(self):
        """打印程序横幅"""
        banner = f"""
╔═══════════════════════════════════════════════════════════╗
║     Markdown格式智能调整工具 v{self.VERSION} (MFAT)         ║
║     优化对话结构，便于AI快速查阅和学习                   ║
╚═══════════════════════════════════════════════════════════╝
        """
        if not self.config["quiet"]:
            print(banner)

    def print_help(self, full=False):
        """打印帮助信息"""
        help_text = """
🤖 MFAT - 专为AI查阅优化的Markdown结构调整工具

核心策略:
  • 取消文档大标题，释放标题层级
  • 智能压缩AI回答的标题结构
  • 保留层次关系，便于AI理解

快速开始:
  mfat conversation.md                    # 智能调整
  mfat -i                                 # 交互式向导
  mfat input.md -o output.md              # 指定输出

常用选项:
  -h, --help            显示此帮助信息
  -v, --version         显示版本信息
  -i, --interactive     交互式向导模式
  -o, --output FILE     指定输出文件
  -s, --suffix SUFFIX   输出文件后缀 (默认: "_adjusted")
  
AI内容处理:
  --mode MODE           处理模式: smart_compress, remap, preserve
  --compress RATIO      压缩比例 (0.1-1.0，默认: 0.7)
  --max-level N         AI标题最大级别 (默认: 6)
  --min-level N         AI标题最小级别 (默认: 3，即###)

目录控制:
  --no-toc              不生成目录
  --toc-depth N         目录最大深度 (默认: 3)
  --keep-instructions   在目录中保留指令标题

格式调整:
  --no-collapse         不合并多余空行
  --max-blank N         最大连续空行数 (默认: 2)
  --keep-title          保留文档大标题 (默认不保留)

示例:
  mfat dialog.md                          # 智能压缩模式
  mfat -i                                 # 交互式向导
  mfat input.md --mode smart_compress     # 指定智能压缩
  mfat *.md -s "_optimized"               # 批量优化
        """
        
        if full:
            help_text += """
高级选项:
  --encoding ENCODING    文件编码 (默认: utf-8)
  --config FILE          从JSON文件加载配置
  --verbose              显示详细处理信息
  --quiet                静默模式，仅输出错误
  --overwrite            覆盖已存在文件
  --dry-run              试运行，不实际修改文件

处理模式说明:
  smart_compress (默认): 智能压缩AI标题层级，保留结构
  remap: 简单重映射，可能丢失层次关系
  preserve: 保持原样，仅基础清理

输出结构:
  1. 对话标题 (# 对话-V001: 标题)
  2. 指令标题 (## 指令 N: 类型)
  3. AI响应 (### 到 ######，智能压缩)
  4. 元数据脚注 (不影响结构)
            """
        
        print(help_text)

    def interactive_mode(self):
        """交互式向导模式"""
        self.print_banner()
        print("🎯 专为AI查阅优化的结构调整向导")
        print("我将引导您完成优化流程，确保文档便于AI学习。\n")
        
        steps = [
            self._get_input_file,
            self._get_output_settings,
            self._get_ai_processing_settings,
            self._get_toc_settings,
            self._confirm_settings,
        ]
        
        for i, step_func in enumerate(steps, 1):
            print(f"\n[步骤 {i}/{len(steps)}]")
            if not step_func():
                print("已取消操作。")
                return False
        
        print("\n" + "="*60)
        print("✅ 配置完成! 开始优化文档结构...")
        print("="*60)
        
        return True
    
    def _get_input_file(self):
        """获取输入文件"""
        while True:
            file_path = input("请输入要处理的Markdown文件路径: ").strip()
            
            if not file_path:
                print("错误: 请输入文件路径。")
                continue
            
            if file_path.lower() == 'q':
                return False
            
            try:
                path = Path(file_path).resolve()
                if not path.exists():
                    print(f"错误: 文件不存在: {path}")
                    continue
                
                if not path.is_file():
                    print(f"错误: 这不是一个文件: {path}")
                    continue
                
                # 预览文件开头
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        preview = f.read(500)
                    
                    print(f"\n📄 文件预览 (前500字符):")
                    print("-" * 40)
                    print(preview[:200] + "..." if len(preview) > 200 else preview)
                    print("-" * 40)
                    
                    confirm = input("\n确认处理此文件? (Y/n): ").strip().lower()
                    if confirm == 'n':
                        continue
                        
                except UnicodeDecodeError:
                    print("⚠️  文件可能不是UTF-8编码，将尝试自动检测")
                
                self.config["input_file"] = str(path)
                print(f"✅ 已选择文件: {path}")
                return True
                
            except Exception as e:
                print(f"错误: {e}")
    
    def _get_output_settings(self):
        """获取输出设置"""
        input_path = Path(self.config["input_file"])
        
        # 默认输出路径
        default_output = input_path.parent / f"{input_path.stem}{self.config['suffix']}.md"
        
        print(f"\n默认输出路径: {default_output}")
        
        choice = input("使用默认输出路径? (Y/n): ").strip().lower()
        if choice == 'n':
            while True:
                output_path = input("请输入输出文件路径: ").strip()
                if not output_path:
                    print("错误: 请输入文件路径。")
                    continue
                
                try:
                    path = Path(output_path).resolve()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    self.config["output_file"] = str(path)
                    break
                except Exception as e:
                    print(f"错误: {e}")
        else:
            self.config["output_file"] = str(default_output)
        
        # 文件后缀
        print(f"\n当前文件后缀: {self.config['suffix']}")
        choice = input("修改文件后缀? (y/N): ").strip().lower()
        if choice == 'y':
            new_suffix = input(f"请输入新的后缀 (当前: {self.config['suffix']}): ").strip()
            if new_suffix:
                self.config["suffix"] = new_suffix
        
        return True
    
    def _get_ai_processing_settings(self):
        """获取AI处理设置"""
        print("\n🧠 AI内容处理设置 (核心)")
        print("智能压缩模式会分析AI回答的结构，并压缩到合适的标题层级。")
        
        modes = {
            "1": "smart_compress",
            "2": "remap", 
            "3": "preserve"
        }
        
        print("\n请选择处理模式:")
        print("  1. smart_compress - 智能压缩 (推荐，保留结构)")
        print("  2. remap - 简单重映射 (快速，可能丢失层次)")
        print("  3. preserve - 保持原样 (仅基础清理)")
        
        while True:
            choice = input("请选择 (1-3, 默认:1): ").strip()
            if not choice:
                choice = "1"
            
            if choice in modes:
                self.config["ai_processing"] = modes[choice]
                
                if choice == "1":
                    # 获取压缩比例
                    while True:
                        ratio = input("压缩比例 (0.1-1.0，越高保留越多层级，默认:0.7): ").strip()
                        if not ratio:
                            ratio = "0.7"
                        
                        try:
                            ratio_val = float(ratio)
                            if 0.1 <= ratio_val <= 1.0:
                                self.config["compress_ratio"] = ratio_val
                                break
                            else:
                                print("错误: 比例必须在0.1到1.0之间。")
                        except ValueError:
                            print("错误: 请输入有效的数字。")
                
                print(f"✅ 已选择: {modes[choice]} 模式")
                return True
            else:
                print("错误: 请选择 1-3 之间的数字。")
    
    def _get_toc_settings(self):
        """获取目录设置"""
        print("\n📑 目录设置")
        
        choice = input("生成目录? (Y/n): ").strip().lower()
        self.config["generate_toc"] = not (choice == 'n')
        
        if self.config["generate_toc"]:
            depth = input("目录最大深度 (1-4, 默认:3): ").strip()
            if depth and depth.isdigit():
                d = int(depth)
                if 1 <= d <= 4:
                    self.config["toc_max_depth"] = d
            
            print("\n目录优化建议:")
            print("  1. 排除指令标题 - 目录更简洁，便于AI导航")
            print("  2. 排除AI内部标题 - 避免目录过于臃肿")
            
            choice = input("在目录中排除指令标题? (Y/n): ").strip().lower()
            self.config["exclude_instructions_from_toc"] = not (choice == 'n')
            
            choice = input("在目录中排除AI内部标题? (Y/n): ").strip().lower()
            self.config["exclude_ai_headings_from_toc"] = not (choice == 'n')
        
        return True
    
    def _confirm_settings(self):
        """确认设置"""
        print("\n" + "="*60)
        print("📋 配置摘要")
        print("="*60)
        
        summary = [
            ("输入文件", self.config["input_file"]),
            ("输出文件", self.config.get("output_file", "未指定")),
            ("处理模式", self.config["ai_processing"]),
            ("压缩比例", f"{self.config.get('compress_ratio', 0.7):.1f}" 
                if self.config["ai_processing"] == "smart_compress" else "不适用"),
            ("生成目录", "是" if self.config["generate_toc"] else "否"),
            ("目录深度", self.config.get("toc_max_depth", 3) 
                if self.config["generate_toc"] else "不适用"),
            ("排除指令", "是" if self.config.get("exclude_instructions_from_toc", True) else "否"),
            ("文档标题", "不保留" if self.config.get("remove_document_title", True) else "保留"),
        ]
        
        for label, value in summary:
            print(f"  {label:>10}: {value}")
        
        print("="*60)
        
        confirm = input("\n确认以上设置并开始处理? (Y/n): ").strip().lower()
        return confirm != 'n'

    def read_file(self, file_path: str) -> str:
        """读取文件，支持多种编码"""
        path = Path(file_path).resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                
                self.stats["file_size"]["input"] = len(content)
                self.stats["input_file"] = str(path)
                
                if encoding != 'utf-8' and not self.config["quiet"]:
                    print(f"[信息] 使用 {encoding} 编码读取文件")
                
                if not self.config["quiet"]:
                    print(f"✅ 成功读取文件，大小: {len(content):,} 字符")
                    print(f"   对话结构分析中...")
                
                return content
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                if encoding == encodings[-1]:
                    raise Exception(f"无法读取文件: {e}")
        
        raise Exception("无法解码文件，请检查文件编码")

    def write_file(self, content: str, file_path: str):
        """写入文件"""
        path = Path(file_path).resolve()
        
        # 确保目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 检查文件是否存在
        if path.exists():
            if self.config["interactive"]:
                print(f"⚠️  文件已存在: {path}")
                choice = input("是否覆盖? (y/N): ").strip().lower()
                if choice != 'y':
                    # 生成新的文件名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_name = f"{path.stem}_{timestamp}{path.suffix}"
                    path = path.parent / new_name
                    print(f"[信息] 使用新文件名: {path}")
            elif not self.config.get("overwrite", False):
                raise FileExistsError(f"文件已存在: {path}")
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.stats["output_file"] = str(path)
            self.stats["file_size"]["output"] = len(content)
            
            if not self.config["quiet"]:
                print(f"✅ 已写入优化后的文件: {path}")
                print(f"   文件大小: {len(content):,} 字符")
                
        except Exception as e:
            raise Exception(f"写入文件失败: {e}")

    def normalize_headings(self, content: str) -> str:
        """规范化标题格式"""
        if not self.config["normalize_headings"]:
            return content
        
        lines = content.split('\n')
        result = []
        
        for line in lines:
            # 检测标题行
            match = re.match(r'^(#+)\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                
                # 规范化：确保#后面有空格，标题前后无空格
                new_line = f"{'#' * level} {title}"
                result.append(new_line)
            else:
                result.append(line)
        
        return '\n'.join(result)

    def collapse_blank_lines(self, content: str) -> str:
        """合并多余空行"""
        if not self.config["collapse_blank_lines"]:
            return content
        
        max_blanks = self.config.get("max_blank_lines", 2)
        lines = content.split('\n')
        result = []
        blank_count = 0
        
        for line in lines:
            stripped = line.rstrip()
            
            # 修剪行尾空格
            if self.config["trim_trailing_spaces"]:
                line = stripped
            
            # 检查是否为空行
            if stripped == '':
                blank_count += 1
                if blank_count <= max_blanks:
                    result.append(line)
                else:
                    self.stats["blank_lines_collapsed"] += 1
            else:
                blank_count = 0
                result.append(line)
        
        return '\n'.join(result)

    def detect_dialogs(self, content: str) -> List[Dict]:
        """检测文档中的对话段落"""
        dialogs = []
        lines = content.split('\n')
        
        current_dialog = None
        dialog_lines = []
        in_dialog = False
        
        for i, line in enumerate(lines):
            # 检测对话段落开始 - 支持多种格式
            dialog_patterns = [
                r'^(#{1,2})\s+对话-([A-Za-z0-9]+)\s+(.+)$',  # ## 对话-V001 标题
                r'^(#{1,2})\s+对话([A-Za-z0-9]+)\s+(.+)$',   # ## 对话V001 标题
                r'^(#{1,2})\s+([A-Za-z0-9]+)\s+对话\s+(.+)$', # ## V001 对话 标题
            ]
            
            dialog_match = None
            for pattern in dialog_patterns:
                dialog_match = re.match(pattern, line)
                if dialog_match:
                    break
            
            if dialog_match:
                # 保存前一个对话
                if current_dialog is not None:
                    current_dialog["content"] = '\n'.join(dialog_lines)
                    dialogs.append(current_dialog)
                
                # 开始新对话
                level = len(dialog_match.group(1))
                dialog_id = dialog_match.group(2)
                title = dialog_match.group(3).strip()
                
                current_dialog = {
                    "id": dialog_id,
                    "title": title,
                    "level": level,
                    "start_line": i,
                    "end_line": -1,
                    "content": "",
                    "instructions": [],
                    "metadata": {
                        "original_heading": line,
                        "has_structure": False,
                    }
                }
                
                dialog_lines = [line]
                in_dialog = True
                self.stats["dialogs"] += 1
            
            elif in_dialog:
                dialog_lines.append(line)
        
        # 添加最后一个对话
        if current_dialog is not None:
            current_dialog["content"] = '\n'.join(dialog_lines)
            current_dialog["end_line"] = len(lines) - 1
            dialogs.append(current_dialog)
        
        # 如果没有检测到标准格式，尝试其他格式
        if not dialogs:
            dialogs = self._detect_alternative_dialogs(content)
        
        if not self.config["quiet"]:
            print(f"📊 检测到 {len(dialogs)} 个对话段落")
        
        return dialogs

    def _detect_alternative_dialogs(self, content: str) -> List[Dict]:
        """检测其他格式的对话段落"""
        dialogs = []
        lines = content.split('\n')
        
        current_dialog = None
        dialog_lines = []
        
        for i, line in enumerate(lines):
            # 检测任何2-3级标题行
            if re.match(r'^#{2,3}\s+', line):
                if current_dialog is not None:
                    current_dialog["content"] = '\n'.join(dialog_lines)
                    dialogs.append(current_dialog)
                
                # 提取标题信息
                level = len(re.match(r'^(#+)', line).group(1))
                title = line.replace('#', '').strip()
                
                # 尝试从标题中提取ID
                import uuid
                dialog_id = str(uuid.uuid4())[:8]  # 生成简短ID
                
                # 查找标题中的数字或字母组合
                id_match = re.search(r'([A-Za-z0-9]+)', title.split()[0] if title else '')
                if id_match:
                    potential_id = id_match.group(1)
                    if len(potential_id) >= 2:  # 至少2个字符才认为是ID
                        dialog_id = potential_id
                
                current_dialog = {
                    "id": dialog_id,
                    "title": title,
                    "level": level,
                    "start_line": i,
                    "end_line": -1,
                    "content": "",
                    "instructions": [],
                    "metadata": {
                        "original_heading": line,
                        "has_structure": False,
                        "auto_generated_id": True,
                    }
                }
                
                dialog_lines = [line]
                self.stats["dialogs"] += 1
            
            elif current_dialog is not None:
                dialog_lines.append(line)
        
        if current_dialog is not None:
            current_dialog["content"] = '\n'.join(dialog_lines)
            dialogs.append(current_dialog)
        
        return dialogs

    def extract_instructions(self, dialog: Dict) -> List[Dict]:
        """从对话中提取指令-响应对"""
        instructions = []
        content = dialog["content"]
        lines = content.split('\n')
        
        current_instruction = None
        instruction_lines = []
        in_instruction = False
        in_response = False
        
        for i, line in enumerate(lines):
            # 跳过对话标题行
            if i == 0 and re.match(r'^#{1,2}\s+', line):
                continue
            
            # 检测指令开始
            is_instruction = False
            instruction_type = "指令"
            
            for pattern in self.INSTRUCTION_MARKERS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    is_instruction = True
                    # 提取指令类型
                    if match.group(0):
                        instruction_type = match.group(0).strip('#').strip()
                    break
            
            if is_instruction:
                # 保存前一个指令
                if current_instruction is not None:
                    current_instruction["content"] = '\n'.join(instruction_lines)
                    self._process_instruction(current_instruction)
                    instructions.append(current_instruction)
                
                # 开始新指令
                current_instruction = {
                    "id": len(instructions) + 1,
                    "type": instruction_type,
                    "start_line": i,
                    "end_line": -1,
                    "instruction": "",
                    "response": "",
                    "content": "",
                    "processed_response": "",
                    "metadata": {
                        "has_ai_response": False,
                        "response_length": 0,
                        "heading_levels": [],
                    }
                }
                
                instruction_lines = [line]
                in_instruction = True
                in_response = False
                self.stats["instructions"] += 1
            
            elif in_instruction:
                instruction_lines.append(line)
        
        # 添加最后一个指令
        if current_instruction is not None:
            current_instruction["content"] = '\n'.join(instruction_lines)
            self._process_instruction(current_instruction)
            instructions.append(current_instruction)
        
        if not self.config["quiet"]:
            print(f"   发现 {len(instructions)} 个指令")
        
        return instructions

    def _process_instruction(self, instruction: Dict):
        """处理单个指令，分离指令和响应"""
        lines = instruction["content"].split('\n')
        
        instruction_lines = []
        response_lines = []
        in_response = False
        response_start_line = -1
        
        for i, line in enumerate(lines):
            # 跳过指令标题行（已经记录在instruction['type']中）
            if i == 0 and any(marker in line.lower() for marker in ['指令', 'instruction', 'q:']):
                continue
            
            # 检测响应开始
            if not in_response:
                is_response_start = False
                
                # 检查响应标记
                for pattern in self.RESPONSE_MARKERS:
                    if re.search(pattern, line, re.IGNORECASE):
                        is_response_start = True
                        response_start_line = i
                        break
                
                # 检查是否是典型的AI输出开头
                if not is_response_start and len(instruction_lines) > 0:
                    ai_patterns = [
                        r'^#{1,6}\s+',  # 任何标题
                        r'^>\s+',       # 引用块
                        r'^[-\*]\s+',   # 列表项
                        r'^\d+\.\s+',   # 数字列表
                        r'^`{3}',       # 代码块开始
                        r'^(\||\+|\-){3,}',  # 表格或分隔线
                    ]
                    for pattern in ai_patterns:
                        if re.match(pattern, line):
                            is_response_start = True
                            response_start_line = i
                            break
            
                if is_response_start:
                    in_response = True
                    instruction["metadata"]["has_ai_response"] = True
                    self.stats["responses"] += 1
            
            if in_response:
                response_lines.append(line)
            else:
                instruction_lines.append(line)
        
        instruction["instruction"] = '\n'.join(instruction_lines).strip()
        instruction["response"] = '\n'.join(response_lines).strip()
        instruction["metadata"]["response_length"] = len(response_lines)
        
        # 分析响应中的标题层级
        self._analyze_response_headings(instruction)
        
        # 处理AI响应
        instruction["processed_response"] = self._process_ai_response(
            instruction["response"],
            instruction["metadata"]["heading_levels"]
        )

    def _analyze_response_headings(self, instruction: Dict):
        """分析响应中的标题层级分布"""
        response = instruction["response"]
        heading_levels = []
        
        lines = response.split('\n')
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                continue
            
            match = re.match(r'^(#+)\s+', line)
            if match:
                level = len(match.group(1))
                heading_levels.append(level)
        
        instruction["metadata"]["heading_levels"] = heading_levels
        
        # 记录到全局统计
        self.state["ai_heading_levels"].extend(heading_levels)

    def _process_ai_response(self, response: str, heading_levels: List[int]) -> str:
        """处理AI响应内容"""
        if not response:
            return ""
        
        mode = self.config["ai_processing"]
        
        if mode == "preserve":
            return response
        elif mode == "remap":
            return self._remap_ai_headings(response)
        else:  # smart_compress (默认)
            return self._smart_compress_headings(response, heading_levels)

    def _remap_ai_headings(self, content: str) -> str:
        """简单重映射AI响应中的标题层级"""
        min_level = self.config["ai_min_level"]  # 通常为3 (###)
        lines = content.split('\n')
        result = []
        
        self.state["in_code_block"] = False
        
        for line in lines:
            if line.strip().startswith('```'):
                self.state["in_code_block"] = not self.state["in_code_block"]
                result.append(line)
                continue
            
            if self.state["in_code_block"]:
                result.append(line)
                continue
            
            match = re.match(r'^(#+)\s+(.+)$', line)
            if match:
                original_level = len(match.group(1))
                title_text = match.group(2)
                
                # 简单偏移：AI的#标题变为###标题
                new_level = min(6, max(min_level, original_level + min_level - 1))
                
                new_heading = '#' * new_level + ' ' + title_text
                result.append(new_heading)
                self.stats["headings_processed"] += 1
            else:
                result.append(line)
        
        return '\n'.join(result)

    def _smart_compress_headings(self, content: str, heading_levels: List[int]) -> str:
        """
        智能压缩标题层级
        核心算法：分析标题层级分布，按比例压缩到可用范围内
        """
        if not heading_levels:
            return content
        
        lines = content.split('\n')
        result = []
        
        # 分析标题层级分布
        if heading_levels:
            min_original = min(heading_levels)
            max_original = max(heading_levels)
            original_range = max_original - min_original + 1
        else:
            # 如果没有标题，直接返回
            return content
        
        # 计算可用范围
        min_allowed = self.config["ai_min_level"]  # 通常为3 (###)
        max_allowed = self.config["ai_max_level"]  # 通常为6 (######)
        allowed_range = max_allowed - min_allowed + 1
        
        # 计算压缩比例
        compress_ratio = self.config.get("compress_ratio", 0.7)
        
        # 如果原始范围小于等于可用范围，不需要压缩，只需偏移
        if original_range <= allowed_range:
            # 只需偏移，不压缩
            offset = min_allowed - min_original
        else:
            # 需要压缩：计算压缩后的范围
            compressed_range = max(2, int(allowed_range * compress_ratio))
            offset = min_allowed - min_original
        
        self.state["in_code_block"] = False
        
        for line in lines:
            if line.strip().startswith('```'):
                self.state["in_code_block"] = not self.state["in_code_block"]
                result.append(line)
                continue
            
            if self.state["in_code_block"]:
                result.append(line)
                continue
            
            match = re.match(r'^(#+)\s+(.+)$', line)
            if match:
                original_level = len(match.group(1))
                title_text = match.group(2)
                
                # 计算新层级
                if original_range <= allowed_range:
                    # 不压缩，只偏移
                    new_level = original_level + offset
                else:
                    # 智能压缩：保持相对位置比例
                    relative_pos = (original_level - min_original) / (original_range - 1)
                    new_level = min_allowed + int(relative_pos * (compressed_range - 1))
                
                # 确保在允许范围内
                new_level = max(min_allowed, min(max_allowed, new_level))
                
                new_heading = '#' * new_level + ' ' + title_text
                result.append(new_heading)
                
                self.stats["headings_processed"] += 1
                if original_range > allowed_range:
                    self.stats["headings_compressed"] += 1
                    self.stats["structure_preserved"] = False
            else:
                result.append(line)
        
        return '\n'.join(result)

    def generate_table_of_contents(self, dialogs: List[Dict]) -> str:
        """生成目录"""
        if not self.config["generate_toc"]:
            return ""
        
        toc_lines = ["## 📑 目录\n"]
        
        for dialog in dialogs:
            # 添加对话标题
            dialog_title = f"对话-{dialog['id']}: {dialog['title']}"
            toc_lines.append(f"- [{dialog_title}](#{self._slugify(dialog_title)})")
            
            # 添加指令（如果配置允许）
            max_depth = self.config.get("toc_max_depth", 3)
            
            if max_depth >= 2 and not self.config["exclude_instructions_from_toc"]:
                for instr in dialog.get("instructions", []):
                    instr_title = f"指令 {instr['id']}"
                    if instr.get('type') and instr['type'] != '指令':
                        instr_title += f" ({instr['type']})"
                    
                    toc_lines.append(f"  - [{instr_title}](#{self._slugify(instr_title)})")
        
        return '\n'.join(toc_lines) + '\n'

    def _slugify(self, text: str) -> str:
        """生成锚点链接ID"""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text

    def organize_content_optimized(self, dialogs: List[Dict]) -> str:
        """
        重新组织内容 - 优化版
        策略：取消文档大标题，直接以对话开始
        """
        output_lines = []
        
        # 不添加文档大标题，直接从对话开始
        # 只添加简短的元数据行（不影响结构）
        if self.config.get("add_metadata_footer", True):
            metadata_line = f"*文档优化时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | MFAT v{self.VERSION}*"
            output_lines.append(metadata_line)
            output_lines.append("")
        
        # 添加目录（可选）
        if self.config["generate_toc"]:
            toc = self.generate_table_of_contents(dialogs)
            output_lines.append(toc)
        
        # 处理每个对话
        for dialog_idx, dialog in enumerate(dialogs, 1):
            # 对话标题：一级标题 (#)
            output_lines.append(f"# 对话-{dialog['id']}: {dialog['title']}")
            output_lines.append("")
            
            # 处理指令和响应
            for instr in dialog.get("instructions", []):
                # 指令标题：二级标题 (##)
                instr_title = f"指令 {instr['id']}"
                if instr.get('type') and instr['type'] != '指令':
                    instr_title += f" ({instr['type']})"
                
                output_lines.append(f"## {instr_title}")
                output_lines.append("")
                
                # 指令内容
                if instr.get("instruction"):
                    output_lines.append("**📝 指令内容**")
                    output_lines.append("```")
                    output_lines.append(instr["instruction"])
                    output_lines.append("```")
                    output_lines.append("")
                
                # AI响应
                if instr.get("processed_response"):
                    output_lines.append("**🤖 AI响应**")
                    output_lines.append("")
                    output_lines.append(instr["processed_response"])
                    output_lines.append("")
                elif instr.get("response"):
                    # 如果没有处理过的响应，使用原始响应
                    output_lines.append("**🤖 AI响应**")
                    output_lines.append("")
                    output_lines.append(instr["response"])
                    output_lines.append("")
            
            # 对话分隔线（除非是最后一个）
            if dialog_idx < len(dialogs):
                output_lines.append("---")
                output_lines.append("")
        
        # 添加处理摘要（放在最后，不影响结构）
        if not self.config["quiet"] and self.config.get("add_metadata_footer", True):
            output_lines.append("---")
            output_lines.append("")
            output_lines.append(self._generate_processing_summary())
        
        return '\n'.join(output_lines)

    def _generate_processing_summary(self) -> str:
        """生成处理摘要"""
        summary_lines = ["## 📊 处理摘要", ""]
        
        # 基本统计
        summary_lines.append(f"- **对话段落:** {self.stats.get('dialogs', 0)} 个")
        summary_lines.append(f"- **指令数量:** {self.stats.get('instructions', 0)} 个")
        summary_lines.append(f"- **AI响应:** {self.stats.get('responses', 0)} 个")
        
        # 标题处理统计
        if self.stats.get('headings_processed', 0) > 0:
            summary_lines.append(f"- **标题处理:** {self.stats['headings_processed']} 个")
            
            if self.stats.get('headings_compressed', 0) > 0:
                compression_rate = self.stats['headings_compressed'] / self.stats['headings_processed']
                summary_lines.append(f"- **标题压缩:** {self.stats['headings_compressed']} 个 ({compression_rate:.1%})")
        
        # 格式优化统计
        if self.stats.get('blank_lines_collapsed', 0) > 0:
            summary_lines.append(f"- **空行优化:** {self.stats['blank_lines_collapsed']} 处")
        
        # 处理信息
        summary_lines.append(f"- **处理模式:** {self.config.get('ai_processing', 'smart_compress')}")
        
        if self.config["ai_processing"] == "smart_compress":
            summary_lines.append(f"- **压缩比例:** {self.config.get('compress_ratio', 0.7):.1f}")
        
        summary_lines.append(f"- **结构保留:** {'是' if self.stats.get('structure_preserved', True) else '部分压缩'}")
        summary_lines.append(f"- **标题层级:** #{self.config.get('ai_min_level', 3)} 到 #{self.config.get('ai_max_level', 6)}")
        
        if self.stats.get("processing_time"):
            summary_lines.append(f"- **处理耗时:** {self.stats['processing_time']}")
        
        return '\n'.join(summary_lines)

    def process(self, input_file: str = None, output_file: str = None) -> bool:
        """主处理流程"""
        start_time = datetime.now()
        
        try:
            # 设置文件路径
            if input_file:
                self.config["input_file"] = input_file
            if output_file:
                self.config["output_file"] = output_file
            
            # 交互式模式
            if self.config["interactive"] and not self.config["input_file"]:
                if not self.interactive_mode():
                    return False
            
            # 验证输入文件
            if not self.config["input_file"]:
                raise ValueError("未指定输入文件")
            
            input_path = Path(self.config["input_file"]).resolve()
            if not input_path.exists():
                raise FileNotFoundError(f"输入文件不存在: {input_path}")
            
            # 设置默认输出路径
            if not self.config["output_file"]:
                suffix = self.config.get("suffix", self.DEFAULT_SUFFIX)
                self.config["output_file"] = str(
                    input_path.parent / f"{input_path.stem}{suffix}.md"
                )
            
            # 打印处理信息
            if not self.config["quiet"]:
                self.print_banner()
                print(f"📥 输入文件: {input_path}")
                print(f"📤 输出文件: {self.config['output_file']}")
                print(f"🎯 处理模式: {self.config['ai_processing']}")
                
                if self.config["ai_processing"] == "smart_compress":
                    print(f"📊 压缩比例: {self.config.get('compress_ratio', 0.7):.1f}")
                
                print(f"🏗️  结构优化: {'取消文档大标题' if self.config.get('remove_document_title', True) else '保留原始结构'}")
                print("")
            
            # 读取文件
            content = self.read_file(self.config["input_file"])
            
            # 基础格式处理
            content = self.normalize_headings(content)
            content = self.collapse_blank_lines(content)
            
            # 检测对话结构
            dialogs = self.detect_dialogs(content)
            
            if not dialogs:
                print("⚠️  未检测到标准对话结构，将整个文档作为单个对话处理")
                # 创建默认对话
                dialogs = [{
                    "id": "001",
                    "title": "完整对话记录",
                    "level": 1,
                    "content": content,
                    "instructions": [],
                    "metadata": {"auto_generated": True}
                }]
            
            # 提取和处理指令
            total_instructions = 0
            for dialog in dialogs:
                instructions = self.extract_instructions(dialog)
                dialog["instructions"] = instructions
                total_instructions += len(instructions)
            
            if not self.config["quiet"]:
                print(f"📈 总计: {len(dialogs)} 个对话，{total_instructions} 个指令")
                print("")
            
            # 重新组织内容（使用优化版）
            organized_content = self.organize_content_optimized(dialogs)
            
            # 写入输出文件
            self.write_file(organized_content, self.config["output_file"])
            
            # 计算处理时间
            end_time = datetime.now()
            self.stats["processing_time"] = str(end_time - start_time).split('.')[0]
            
            # 打印统计信息
            if not self.config["quiet"]:
                self._print_statistics()
            
            return True
            
        except Exception as e:
            error_msg = f"处理失败: {type(e).__name__}: {e}"
            if self.config["verbose"]:
                import traceback
                error_msg += f"\n\n{traceback.format_exc()}"
            
            print(f"\n❌ {error_msg}")
            
            if self.config["interactive"]:
                retry = input("\n是否重试? (y/N): ").strip().lower()
                if retry == 'y':
                    return self.process()
            
            return False
    
    def _print_statistics(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("🎉 优化完成! 统计信息")
        print("="*60)
        
        stats = [
            ("输入文件", self.stats.get("input_file")),
            ("输出文件", self.stats.get("output_file")),
            ("文件大小", f"{self.stats.get('file_size', {}).get('input', 0):,} → "
                       f"{self.stats.get('file_size', {}).get('output', 0):,} 字符"),
            ("对话段落", f"{self.stats.get('dialogs', 0)} 个"),
            ("指令数量", f"{self.stats.get('instructions', 0)} 个"),
            ("AI响应", f"{self.stats.get('responses', 0)} 个"),
        ]
        
        if self.stats.get('headings_processed', 0) > 0:
            stats.append(("标题处理", f"{self.stats['headings_processed']} 个"))
            
            if self.stats.get('headings_compressed', 0) > 0:
                compression_rate = self.stats['headings_compressed'] / self.stats['headings_processed']
                stats.append(("标题压缩", f"{self.stats['headings_compressed']} 个 ({compression_rate:.1%})"))
        
        if self.stats.get('blank_lines_collapsed', 0) > 0:
            stats.append(("空行优化", f"{self.stats['blank_lines_collapsed']} 处"))
        
        stats.append(("处理耗时", self.stats.get("processing_time", "未知")))
        stats.append(("结构保留", "完整" if self.stats.get('structure_preserved', True) else "压缩"))
        
        for label, value in stats:
            if value:
                print(f"  {label:>10}: {value}")
        
        print("="*60)
        print("✅ 文档已优化完成，便于AI快速查阅和学习")
        print("="*60)


# 简化别名
MFA = MarkdownFormatAdjust


def main():
    """主函数入口"""
    parser = argparse.ArgumentParser(
        description="MFAT - 专为AI查阅优化的Markdown结构调整工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  mfat conversation.md                    # 智能调整
  mfat -i                                 # 交互式向导
  mfat input.md -o output.md              # 指定输出文件
  mfat *.md -s "_optimized"               # 批量处理多个文件

核心模式:
  智能压缩 (推荐): mfat input.md --mode smart_compress --compress 0.7
  简单重映射:       mfat input.md --mode remap
  保持原样:         mfat input.md --mode preserve

优化说明:
  • 取消文档大标题，释放标题层级
  • 智能压缩AI回答的标题结构
  • 保留层次关系，便于AI理解
  • 输出结构: #对话 → ##指令 → ###AI响应
        """
    )
    
    # 输入输出参数
    parser.add_argument(
        "input_file",
        nargs="?",
        help="输入文件路径"
    )
    
    parser.add_argument(
        "-o", "--output",
        dest="output_file",
        help="输出文件路径"
    )
    
    parser.add_argument(
        "-s", "--suffix",
        default=MFA.DEFAULT_SUFFIX,
        help=f"输出文件后缀 (默认: '{MFA.DEFAULT_SUFFIX}')"
    )
    
    # 模式选择
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="启用交互式向导模式"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式"
    )
    
    # AI内容处理
    parser.add_argument(
        "--mode",
        choices=["smart_compress", "remap", "preserve"],
        default="smart_compress",
        help="AI内容处理模式 (默认: smart_compress)"
    )
    
    parser.add_argument(
        "--compress",
        type=float,
        default=0.7,
        help="智能压缩比例 (0.1-1.0，默认: 0.7)"
    )
    
    parser.add_argument(
        "--min-level",
        type=int,
        default=3,
        help="AI标题最小级别 (默认: 3，即###)"
    )
    
    parser.add_argument(
        "--max-level",
        type=int,
        default=6,
        help="AI标题最大级别 (默认: 6)"
    )
    
    # 目录控制
    parser.add_argument(
        "--no-toc",
        action="store_true",
        help="不生成目录"
    )
    
    parser.add_argument(
        "--toc-depth",
        type=int,
        default=3,
        help="目录最大深度 (默认: 3)"
    )
    
    parser.add_argument(
        "--keep-instructions",
        action="store_true",
        help="在目录中保留指令标题"
    )
    
    parser.add_argument(
        "--keep-ai-toc",
        action="store_true",
        help="在目录中保留AI标题"
    )
    
    # 格式调整
    parser.add_argument(
        "--no-collapse",
        action="store_true",
        help="不合并多余空行"
    )
    
    parser.add_argument(
        "--max-blank",
        type=int,
        default=2,
        help="最大连续空行数 (默认: 2)"
    )
    
    parser.add_argument(
        "--no-trim",
        action="store_true",
        help="不修剪行尾空格"
    )
    
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="不规范化标题格式"
    )
    
    parser.add_argument(
        "--keep-title",
        action="store_true",
        help="保留文档大标题 (默认取消)"
    )
    
    # 信息选项
    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="显示版本信息"
    )
    
    parser.add_argument(
        "--help-full",
        action="store_true",
        help="显示完整帮助信息"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细处理信息"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，仅输出错误信息"
    )
    
    # 其他选项
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="文件编码 (默认: utf-8)"
    )
    
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在的输出文件"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行，不实际修改文件"
    )
    
    args = parser.parse_args()
    
    # 显示版本信息
    if args.version:
        print(f"Markdown格式智能调整工具 (MFAT) v{MFA.VERSION}")
        print("专为AI查阅优化，取消文档大标题 + 智能标题压缩")
        sys.exit(0)
    
    # 显示完整帮助
    if args.help_full:
        mfa = MFA()
        mfa.print_help(full=True)
        sys.exit(0)
    
    # 如果没有输入文件且没有指定交互模式，显示基本帮助
    if not args.input_file and not args.interactive:
        parser.print_help()
        print("\n💡 提示: 使用 mfat -i 进入交互式向导模式")
        print("     或 mfat --help-full 查看完整帮助")
        sys.exit(0)
    
    # 构建配置
    config = {
        "input_file": args.input_file,
        "output_file": args.output_file,
        "suffix": args.suffix,
        "interactive": args.interactive,
        "verbose": args.verbose,
        "quiet": args.quiet,
        "encoding": args.encoding,
        "overwrite": args.overwrite,
        
        # AI处理
        "ai_processing": args.mode,
        "compress_ratio": args.compress,
        "ai_min_level": args.min_level,
        "ai_max_level": args.max_level,
        
        # 目录控制
        "generate_toc": not args.no_toc,
        "toc_max_depth": args.toc_depth,
        "exclude_instructions_from_toc": not args.keep_instructions,
        "exclude_ai_headings_from_toc": not args.keep_ai_toc,
        
        # 格式调整
        "collapse_blank_lines": not args.no_collapse,
        "max_blank_lines": args.max_blank,
        "trim_trailing_spaces": not args.no_trim,
        "normalize_headings": not args.no_normalize,
        "remove_document_title": not args.keep_title,  # 默认取消文档大标题
    }
    
    # 创建处理器
    mfat = MFA(config)
    
    # 运行处理
    try:
        success = mfat.process()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()