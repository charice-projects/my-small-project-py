#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown格式智能调整工具 (MFAT) - 增强交互版
专门解决对话记录中的结构嵌套问题，优化AI查阅体验
版本：5.0.0
核心特性：启动即用的交互式控制台 + 智能边界检测 + Syntaxnom项目优化
"""

import re
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
import shutil

class MarkdownFormatAdjust:
    """
    Markdown格式智能调整工具 (MFAT)
    针对Syntaxnom项目文档的优化版本，带交互式控制台
    """
    
    VERSION = "5.0.0"
    DEFAULT_SUFFIX = "_adjusted"
    
    # ==================== 可自定义配置区域 ====================
    # 您可以在这里修改这些配置，无需深入代码
    
    # 对话标题检测模式 - 针对"## 对话-V001"格式
    DIALOG_PATTERNS = [
        r'^#{1,2}\s+对话-([A-Za-z0-9]+)\s+(.+)$',  # ## 对话-V001 标题
        r'^#{1,2}\s+对话([A-Za-z0-9]+)\s+(.+)$',   # ## 对话V001 标题
        r'^#{1,2}\s+([A-Za-z0-9]+)\s+对话\s+(.+)$', # ## V001 对话 标题
        r'^#{1,2}\s+对话\s*[:：]?\s*(.+)$',         # ## 对话: 标题
    ]
    
    # 指令标记检测 - 针对"### AA我的指令"格式
    INSTRUCTION_MARKERS = [
        # 精确匹配整行
        ("## 指令", True),
        ("### 指令", True),
        ("### AA我的指令", True),
        ("### aa我的指令", True),
        ("aa我的指令", True),
        ("### BB我的指令", True),
        ("### Q:", True),
        ("### 问题:", True),
        
        # 包含即可
        ("我的指令", False),
        ("指令", False),
        ("Q:", False),
        ("问题:", False),
        ("要求:", False),
    ]
    
    # AI响应开始标记 - 针对您的文档特点优化
    RESPONSE_MARKERS = [
        # 精确匹配整行
        ("🤖 AI响应", True),
        ("dd-AI回复", True),
        ("## AI响应", True),
        ("### 🤖 响应", True),
        ("### 响应", True),
        ("--- AI回复开始 ---", True),
        
        # 包含即可 - 针对您的文档内容
        ("针对你", False),          # 您的文档中AI常用开头
        ("核心结论是", False),      # 您的文档中AI常用开头
        ("为你梳理", False),        # 您的文档中AI常用开头
        ("根据你", False),          # 潜在AI开头
        ("以下是", False),          # 潜在AI开头
        ("AI回复", False),
        ("AI回答", False),
        ("🤖回复", False),
        ("🤖回答", False),
        ("回答", False),
        ("Response:", False),
        ("Output:", False),
    ]
    
    # AI内容特征模式（用于辅助检测）
    AI_CONTENT_PATTERNS = [
        r'^#{1,6}\s+',          # 任何标题
        r'^>\s+',               # 引用块
        r'^[-\*]\s+',           # 无序列表
        r'^\d+\.\s+',           # 有序列表
        r'^`{3}',               # 代码块开始
        r'^(\||\+|\-){3,}',     # 表格或分隔线
        r'^```',                # 代码块
        r'^(\*\*|__).+(\*\*|__)',  # 粗体文本
        r'^\*\*.+\*\*',         # 粗体文本
        r'^📊\s+',              # 您的文档中的表情符号标题
        r'^💡\s+',              # 您的文档中的表情符号标题
        r'^✅\s+',              # 您的文档中的表情符号标题
        r'^🚀\s+',              # 您的文档中的表情符号标题
    ]
    
    # 智能压缩配置
    COMPRESS_CONFIG = {
        "default_ratio": 0.7,      # 默认压缩比例
        "min_level": 3,           # AI标题最小级别 (###)
        "max_level": 6,           # AI标题最大级别 (######)
        "preserve_structure": True, # 保留结构层次
    }
    
    # 边界检测配置
    BOUNDARY_CONFIG = {
        "mode": "smart",          # smart, strict, auto
        "tolerance_lines": 2,     # 容错行数：允许指令包含AI开头几行
        "min_instruction_lines": 3, # 指令最少行数（少于这个可能不是完整指令）
    }
    
    # ==================== 配置区域结束 ====================
    
    def __init__(self, config: Dict = None):
        """
        初始化MFAT工具
        
        Args:
            config: 配置字典
        """
        # 默认配置
        self.config = {
            # 文件处理
            "input_file": None,
            "output_file": None,
            "suffix": self.DEFAULT_SUFFIX,
            "encoding": "utf-8",
            
            # AI内容处理
            "ai_processing": "smart_compress",  # smart_compress, remap, preserve
            "ai_max_level": self.COMPRESS_CONFIG["max_level"],
            "ai_min_level": self.COMPRESS_CONFIG["min_level"],
            "preserve_structure": self.COMPRESS_CONFIG["preserve_structure"],
            "compress_ratio": self.COMPRESS_CONFIG["default_ratio"],
            
            # 边界检测
            "boundary_detection": self.BOUNDARY_CONFIG["mode"],
            "tolerance_lines": self.BOUNDARY_CONFIG["tolerance_lines"],
            "min_instruction_lines": self.BOUNDARY_CONFIG["min_instruction_lines"],
            
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
            "remove_document_title": True,
            
            # 交互模式
            "interactive": False,
            "verbose": False,
            "quiet": False,
            
            # 特殊处理
            "detect_dialog_sections": True,
            "fix_markdown_links": True,
            "add_metadata_footer": True,
            "skip_processed": True,
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
            "boundary_detection_methods": {
                "marker": 0,
                "heading": 0,
                "smart": 0,
                "fallback": 0
            },
            "headings_processed": 0,
            "headings_compressed": 0,
            "blank_lines_collapsed": 0,
            "processing_time": None,
            "file_size": {
                "input": 0,
                "output": 0
            },
            "structure_preserved": True,
            "already_processed": False,
        }
        
        # 状态跟踪
        self.state = {
            "in_code_block": False,
            "code_block_language": "",
            "current_dialog": None,
            "current_instruction": None,
            "ai_heading_levels": [],
        }
    
    # ==================== 交互式控制台方法 ====================
    
    def run_interactive_console(self):
        """
        运行交互式控制台主循环
        这是程序的核心交互入口
        """
        self._clear_screen()
        self._print_console_banner()
        
        # 主循环
        while True:
            print("\n" + "="*60)
            print("📁 主菜单 - 请选择操作")
            print("="*60)
            print("1. 🚀 处理单个Markdown文件")
            print("2. 📂 批量处理多个Markdown文件")
            print("3. ⚙️  查看/修改默认配置")
            print("4. 📖 查看使用说明")
            print("5. 🧹 清理输出目录的旧文件")
            print("6. 🔧 测试文档格式检测")
            print("7. 🚪 退出程序")
            print("="*60)
            
            choice = input("\n请输入选项编号 (1-7): ").strip()
            
            if choice == "1":
                self._handle_single_file()
            elif choice == "2":
                self._handle_batch_files()
            elif choice == "3":
                self._handle_configuration()
            elif choice == "4":
                self._show_help()
            elif choice == "5":
                self._cleanup_old_files()
            elif choice == "6":
                self._test_document_format()
            elif choice == "7":
                print("\n👋 感谢使用，再见！")
                sys.exit(0)
            else:
                print("❌ 无效选项，请重新输入。")
    
    def _print_console_banner(self):
        """打印控制台横幅"""
        banner = f"""
╔═══════════════════════════════════════════════════════════╗
║    Markdown格式智能调整工具 v{self.VERSION}                ║
║     专为Syntaxnom项目优化的交互式控制台                  ║
║     🎯 精准边界检测 + 智能标题压缩 + 启动即用             ║
╚═══════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def _clear_screen(self):
        """清空控制台屏幕"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _handle_single_file(self):
        """处理单个文件"""
        print("\n" + "-"*50)
        print("📄 单文件处理模式")
        print("-"*50)
        
        # 1. 获取文件路径
        file_path = self._prompt_file_input("请输入要处理的Markdown文件路径: ")
        if not file_path:
            return
        
        # 2. 快速预览文件
        self._preview_file(file_path)
        
        # 3. 选择处理模式
        print("\n🎯 请选择处理模式:")
        print("  1. 智能模式 (推荐，自动检测和压缩)")
        print("  2. 自定义模式 (手动设置参数)")
        print("  3. 快速模式 (使用默认配置)")
        
        mode_choice = input("\n请选择模式 (1-3，默认:1): ").strip() or "1"
        
        if mode_choice == "1":
            config = self._get_smart_config()
        elif mode_choice == "2":
            config = self._get_custom_config()
        else:
            config = self._get_quick_config()
        
        # 4. 设置输出路径
        output_path = self._prompt_output_path(file_path, config.get("suffix", "_adjusted"))
        
        # 5. 确认并开始处理
        print("\n" + "="*50)
        print("📋 处理任务摘要")
        print("="*50)
        print(f"输入文件: {file_path}")
        print(f"输出文件: {output_path}")
        print(f"处理模式: {config.get('ai_processing', 'smart_compress')}")
        print(f"边界检测: {config.get('boundary_detection', 'smart')}")
        print("="*50)
        
        confirm = input("\n确认开始处理? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("操作已取消。")
            return
        
        # 6. 执行处理
        print("\n🔄 开始处理文件...")
        processor = MarkdownFormatAdjust(config)
        processor.config["input_file"] = file_path
        processor.config["output_file"] = output_path
        processor.config["quiet"] = False
        
        try:
            success = processor.process()
            if success:
                print("\n" + "="*50)
                print("✅ 处理完成!")
                print("="*50)
                print(f"输出文件: {output_path}")
                
                # 询问是否打开文件
                open_file = input("\n是否打开输出文件? (y/N): ").strip().lower()
                if open_file == 'y':
                    self._open_file(output_path)
                
                input("\n按Enter键返回主菜单...")
            else:
                input("\n❌ 处理失败。按Enter键返回主菜单...")
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
            input("\n按Enter键返回主菜单...")
    
    def _handle_batch_files(self):
        """批量处理多个文件"""
        print("\n" + "-"*50)
        print("📂 批量处理模式")
        print("-"*50)
        
        # 1. 获取目录路径
        while True:
            dir_path = input("请输入包含Markdown文件的目录路径: ").strip()
            if not dir_path:
                print("操作已取消。")
                return
            
            dir_path = Path(dir_path).expanduser().resolve()
            
            if not dir_path.exists():
                print(f"❌ 目录不存在: {dir_path}")
                continue
            
            if not dir_path.is_dir():
                print(f"❌ 这不是一个目录: {dir_path}")
                continue
            
            # 查找Markdown文件
            md_files = list(dir_path.glob("*.md")) + list(dir_path.glob("*.markdown"))
            
            if not md_files:
                print(f"❌ 目录中没有找到Markdown文件 (*.md, *.markdown)")
                continue
            
            print(f"✅ 找到 {len(md_files)} 个Markdown文件:")
            for i, file in enumerate(md_files[:10], 1):
                size_kb = file.stat().st_size / 1024
                print(f"  {i:2d}. {file.name} ({size_kb:.1f} KB)")
            
            if len(md_files) > 10:
                print(f"  ... 还有 {len(md_files) - 10} 个文件")
            
            confirm = input("\n确认处理这些文件? (Y/n): ").strip().lower()
            if confirm != 'n':
                break
        
        # 2. 选择处理配置
        print("\n🎯 批量处理配置:")
        print("  1. 统一配置 (所有文件使用相同设置)")
        print("  2. 智能配置 (根据文件内容自动调整)")
        
        batch_choice = input("请选择配置模式 (1-2，默认:1): ").strip() or "1"
        
        if batch_choice == "1":
            config = self._get_batch_config()
        else:
            config = self._get_smart_config()
        
        # 3. 确认并开始批量处理
        print("\n" + "="*50)
        print("📋 批量处理任务摘要")
        print("="*50)
        print(f"目标目录: {dir_path}")
        print(f"文件数量: {len(md_files)}")
        print(f"处理模式: {config.get('ai_processing', 'smart_compress')}")
        print("="*50)
        
        confirm = input("\n确认开始批量处理? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("操作已取消。")
            return
        
        # 4. 执行批量处理
        print("\n🔄 开始批量处理...")
        success_count = 0
        fail_count = 0
        results = []
        
        for i, file_path in enumerate(md_files, 1):
            print(f"\n[{i}/{len(md_files)}] 处理: {file_path.name}")
            
            output_file = file_path.parent / f"{file_path.stem}{config.get('suffix', '_adjusted')}{file_path.suffix}"
            
            processor = MarkdownFormatAdjust(config.copy())
            processor.config["input_file"] = str(file_path)
            processor.config["output_file"] = str(output_file)
            processor.config["quiet"] = True  # 批量处理时静默
            
            try:
                if processor.process():
                    print(f"   ✅ 完成: {output_file.name}")
                    success_count += 1
                    results.append((file_path.name, "成功", str(output_file)))
                else:
                    print(f"   ❌ 失败")
                    fail_count += 1
                    results.append((file_path.name, "失败", "无"))
            except Exception as e:
                print(f"   ❌ 错误: {e}")
                fail_count += 1
                results.append((file_path.name, "错误", str(e)))
        
        # 5. 显示批量处理结果
        print("\n" + "="*50)
        print("📊 批量处理完成!")
        print("="*50)
        print(f"成功处理: {success_count} 个文件")
        print(f"处理失败: {fail_count} 个文件")
        print(f"总文件数: {len(md_files)} 个")
        
        # 询问是否保存处理报告
        save_report = input("\n是否保存处理报告? (y/N): ").strip().lower()
        if save_report == 'y':
            report_file = dir_path / f"mfat_batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"MFAT批量处理报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"目录: {dir_path}\n")
                f.write(f"成功: {success_count} 个\n")
                f.write(f"失败: {fail_count} 个\n")
                f.write(f"总计: {len(md_files)} 个\n\n")
                
                f.write("处理详情:\n")
                for filename, status, info in results:
                    f.write(f"  {filename}: {status} - {info}\n")
            
            print(f"✅ 报告已保存: {report_file}")
        
        print("="*50)
        input("\n按Enter键返回主菜单...")
    
    def _prompt_file_input(self, prompt_text: str) -> Optional[str]:
        """提示用户输入文件路径，支持智能补全和验证"""
        while True:
            file_path = input(f"\n{prompt_text}").strip()
            
            if file_path.lower() in ['q', 'quit', 'exit', 'cancel', '返回', '取消']:
                return None
            
            if not file_path:
                print("❌ 请输入文件路径。")
                continue
            
            # 支持 ~ 扩展
            file_path = Path(file_path).expanduser().resolve()
            
            # 验证文件
            if not file_path.exists():
                print(f"❌ 文件不存在: {file_path}")
                
                # 智能建议：检查是否有类似文件
                parent_dir = file_path.parent
                if parent_dir.exists():
                    similar_files = list(parent_dir.glob(f"*{file_path.suffix}"))
                    if similar_files:
                        print("   附近找到以下文件:")
                        for f in similar_files[:5]:
                            print(f"   - {f.name}")
                continue
            
            if not file_path.is_file():
                print(f"❌ 这不是一个文件: {file_path}")
                continue
            
            # 检查文件扩展名
            if file_path.suffix.lower() not in ['.md', '.markdown', '.txt']:
                print(f"⚠️  文件扩展名不是 .md/.markdown/.txt: {file_path.suffix}")
                confirm = input("是否继续处理? (y/N): ").strip().lower()
                if confirm != 'y':
                    continue
            
            return str(file_path)
    
    def _preview_file(self, file_path: str, lines: int = 20):
        """预览文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            file_size = os.path.getsize(file_path)
            line_count = content.count('\n') + 1
            
            print(f"\n📄 文件预览: {Path(file_path).name}")
            print(f"   大小: {file_size:,} 字节, 行数: {line_count}")
            print("-" * 50)
            
            # 显示前N行
            preview_lines = content.split('\n')[:lines]
            for i, line in enumerate(preview_lines, 1):
                display_line = line[:80] + ('...' if len(line) > 80 else '')
                print(f"{i:3d}: {display_line}")
            
            if line_count > lines:
                print(f"... 还有 {line_count - lines} 行未显示")
            
            # 检测文档特征
            features = []
            if "对话-V" in content:
                features.append("对话-V格式")
            if "AA我的指令" in content:
                features.append("AA我的指令")
            if "我的指令" in content:
                features.append("我的指令")
            if "# " in content[:500]:
                features.append("Markdown标题")
            
            if features:
                print(f"🔍 检测到特征: {', '.join(features)}")
                
        except Exception as e:
            print(f"⚠️  无法预览文件: {e}")
    
    def _get_smart_config(self) -> Dict:
        """获取智能推荐配置"""
        print("\n🔧 智能配置模式")
        print("系统将根据文件内容自动推荐最佳配置。")
        
        return {
            "ai_processing": "smart_compress",
            "compress_ratio": 0.7,
            "boundary_detection": "smart",
            "tolerance_lines": 2,
            "generate_toc": True,
            "toc_max_depth": 3,
            "normalize_headings": True,
            "collapse_blank_lines": True,
            "remove_document_title": True,
        }
    
    def _get_custom_config(self) -> Dict:
        """获取自定义配置"""
        config = self._get_smart_config()  # 以智能配置为起点
        
        print("\n⚙️  自定义配置模式")
        print("请逐项设置处理参数:")
        
        # AI处理模式
        print("\n1. AI内容处理模式:")
        print("  [1] smart_compress - 智能压缩 (推荐)")
        print("  [2] remap - 简单重映射")
        print("  [3] preserve - 保持原样")
        ai_choice = input("请选择 (1-3，默认:1): ").strip() or "1"
        config["ai_processing"] = ["smart_compress", "remap", "preserve"][int(ai_choice)-1]
        
        if config["ai_processing"] == "smart_compress":
            while True:
                ratio = input("压缩比例 (0.1-1.0，默认:0.7): ").strip() or "0.7"
                try:
                    ratio_val = float(ratio)
                    if 0.1 <= ratio_val <= 1.0:
                        config["compress_ratio"] = ratio_val
                        break
                    else:
                        print("❌ 比例必须在0.1到1.0之间。")
                except ValueError:
                    print("❌ 请输入有效的数字。")
        
        # 边界检测
        print("\n2. 边界检测模式:")
        print("  [1] smart - 智能模式 (推荐)")
        print("  [2] strict - 严格模式")
        print("  [3] auto - 自动模式")
        boundary_choice = input("请选择 (1-3，默认:1): ").strip() or "1"
        config["boundary_detection"] = ["smart", "strict", "auto"][int(boundary_choice)-1]
        
        if config["boundary_detection"] in ["smart", "auto"]:
            while True:
                tolerance = input("容错行数 (0-5，默认:2): ").strip() or "2"
                if tolerance.isdigit():
                    tol_val = int(tolerance)
                    if 0 <= tol_val <= 5:
                        config["tolerance_lines"] = tol_val
                        break
                    else:
                        print("❌ 必须在0-5之间。")
                else:
                    print("❌ 请输入有效的数字。")
        
        # 其他设置
        print("\n3. 其他设置:")
        config["generate_toc"] = input("生成目录? (Y/n，默认:Y): ").strip().lower() != 'n'
        
        if config["generate_toc"]:
            while True:
                depth = input("目录深度 (1-4，默认:3): ").strip() or "3"
                if depth.isdigit():
                    depth_val = int(depth)
                    if 1 <= depth_val <= 4:
                        config["toc_max_depth"] = depth_val
                        break
                    else:
                        print("❌ 必须在1-4之间。")
                else:
                    print("❌ 请输入有效的数字。")
        
        config["remove_document_title"] = input("移除文档大标题? (Y/n，默认:Y): ").strip().lower() != 'n'
        config["normalize_headings"] = input("规范化标题格式? (Y/n，默认:Y): ").strip().lower() != 'n'
        config["collapse_blank_lines"] = input("合并多余空行? (Y/n，默认:Y): ").strip().lower() != 'n'
        
        # 输出设置
        suffix = input("输出文件后缀 (默认:_adjusted): ").strip()
        if suffix:
            config["suffix"] = suffix
        
        return config
    
    def _get_quick_config(self) -> Dict:
        """获取快速配置"""
        print("\n⚡ 快速配置模式")
        print("使用推荐默认配置，适合大多数文档。")
        
        return {
            "ai_processing": "smart_compress",
            "compress_ratio": 0.7,
            "boundary_detection": "smart",
            "tolerance_lines": 2,
            "generate_toc": True,
            "toc_max_depth": 3,
            "normalize_headings": True,
            "collapse_blank_lines": True,
            "remove_document_title": True,
            "quiet": False,
        }
    
    def _get_batch_config(self) -> Dict:
        """获取批量处理配置"""
        config = self._get_quick_config()
        
        print("\n📦 批量处理配置")
        suffix = input("输出文件后缀 (默认:_adjusted): ").strip()
        if suffix:
            config["suffix"] = suffix
        
        overwrite = input("覆盖已存在文件? (y/N，默认:N): ").strip().lower()
        config["overwrite"] = overwrite == 'y'
        
        return config
    
    def _prompt_output_path(self, input_path: str, suffix: str) -> str:
        """提示用户设置输出路径"""
        input_path = Path(input_path)
        
        # 默认输出路径
        default_output = input_path.parent / f"{input_path.stem}{suffix}{input_path.suffix}"
        
        print(f"\n📤 输出文件设置")
        print(f"默认输出路径: {default_output}")
        
        choice = input("使用默认路径? (Y/n): ").strip().lower()
        if choice == 'n':
            while True:
                output_path = input("请输入自定义输出路径: ").strip()
                if not output_path:
                    print("❌ 请输入有效的路径。")
                    continue
                
                output_path = Path(output_path).expanduser().resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                if output_path.exists():
                    print(f"⚠️  文件已存在: {output_path}")
                    overwrite = input("是否覆盖? (y/N): ").strip().lower()
                    if overwrite != 'y':
                        continue
                
                return str(output_path)
        else:
            return str(default_output)
    
    def _handle_configuration(self):
        """处理配置管理"""
        while True:
            print("\n" + "="*50)
            print("⚙️  配置管理")
            print("="*50)
            print("1. 查看当前配置")
            print("2. 修改指令检测标记")
            print("3. 修改AI响应检测标记")
            print("4. 修改AI内容特征模式")
            print("5. 保存配置到文件")
            print("6. 从文件加载配置")
            print("7. 重置为默认配置")
            print("8. 返回主菜单")
            print("="*50)
            
            choice = input("\n请选择操作 (1-8): ").strip()
            
            if choice == "1":
                self._show_current_config()
            elif choice == "2":
                self._modify_instruction_markers()
            elif choice == "3":
                self._modify_response_markers()
            elif choice == "4":
                self._modify_ai_patterns()
            elif choice == "5":
                self._save_config_to_file()
            elif choice == "6":
                self._load_config_from_file()
            elif choice == "7":
                self._reset_to_default_config()
            elif choice == "8":
                return
            else:
                print("❌ 无效选项。")
    
    def _show_current_config(self):
        """显示当前配置"""
        print("\n📋 当前配置:")
        print("-" * 40)
        
        print("📝 指令检测标记:")
        for i, (marker, exact) in enumerate(self.INSTRUCTION_MARKERS[:10], 1):
            exact_str = "精确匹配" if exact else "包含即可"
            print(f"  {i:2d}. {marker} ({exact_str})")
        
        if len(self.INSTRUCTION_MARKERS) > 10:
            print(f"  ... 还有 {len(self.INSTRUCTION_MARKERS) - 10} 个标记")
        
        print("\n🤖 AI响应检测标记:")
        for i, (marker, exact) in enumerate(self.RESPONSE_MARKERS[:10], 1):
            exact_str = "精确匹配" if exact else "包含即可"
            print(f"  {i:2d}. {marker} ({exact_str})")
        
        if len(self.RESPONSE_MARKERS) > 10:
            print(f"  ... 还有 {len(self.RESPONSE_MARKERS) - 10} 个标记")
        
        print("\n🔧 压缩配置:")
        for key, value in self.COMPRESS_CONFIG.items():
            print(f"  {key}: {value}")
        
        print("\n🎯 边界检测配置:")
        for key, value in self.BOUNDARY_CONFIG.items():
            print(f"  {key}: {value}")
        
        print("-" * 40)
    
    def _modify_instruction_markers(self):
        """修改指令检测标记"""
        print("\n✏️  修改指令检测标记")
        print("当前标记:")
        for i, (marker, exact) in enumerate(self.INSTRUCTION_MARKERS, 1):
            exact_str = "精确匹配" if exact else "包含即可"
            print(f"  {i:2d}. {marker} ({exact_str})")
        
        print("\n操作选项:")
        print("  [a] 添加新标记")
        print("  [d] 删除标记")
        print("  [e] 编辑标记")
        print("  [r] 返回")
        
        choice = input("请选择操作: ").strip().lower()
        
        if choice == 'a':
            new_marker = input("请输入新标记: ").strip()
            if new_marker:
                exact = input("精确匹配整行? (y/N): ").strip().lower() == 'y'
                self.INSTRUCTION_MARKERS.append((new_marker, exact))
                print(f"✅ 已添加标记: {new_marker}")
        elif choice == 'd':
            try:
                index = int(input("请输入要删除的标记编号: ").strip()) - 1
                if 0 <= index < len(self.INSTRUCTION_MARKERS):
                    removed = self.INSTRUCTION_MARKERS.pop(index)
                    print(f"✅ 已删除标记: {removed[0]}")
                else:
                    print("❌ 无效的编号。")
            except ValueError:
                print("❌ 请输入有效的编号。")
        elif choice == 'e':
            try:
                index = int(input("请输入要编辑的标记编号: ").strip()) - 1
                if 0 <= index < len(self.INSTRUCTION_MARKERS):
                    old_marker, old_exact = self.INSTRUCTION_MARKERS[index]
                    print(f"当前: {old_marker} (精确匹配: {old_exact})")
                    
                    new_marker = input(f"新标记 (留空保持 '{old_marker}'): ").strip() or old_marker
                    exact_input = input(f"精确匹配整行? (当前: {old_exact}, y/N): ").strip().lower()
                    new_exact = old_exact if exact_input == '' else (exact_input == 'y')
                    
                    self.INSTRUCTION_MARKERS[index] = (new_marker, new_exact)
                    print(f"✅ 已更新标记")
                else:
                    print("❌ 无效的编号。")
            except ValueError:
                print("❌ 请输入有效的编号。")
    
    def _modify_response_markers(self):
        """修改AI响应检测标记"""
        print("\n✏️  修改AI响应检测标记")
        print("当前标记:")
        for i, (marker, exact) in enumerate(self.RESPONSE_MARKERS, 1):
            exact_str = "精确匹配" if exact else "包含即可"
            print(f"  {i:2d}. {marker} ({exact_str})")
        
        print("\n操作选项:")
        print("  [a] 添加新标记")
        print("  [d] 删除标记")
        print("  [e] 编辑标记")
        print("  [r] 返回")
        
        choice = input("请选择操作: ").strip().lower()
        
        if choice == 'a':
            new_marker = input("请输入新标记: ").strip()
            if new_marker:
                exact = input("精确匹配整行? (y/N): ").strip().lower() == 'y'
                self.RESPONSE_MARKERS.append((new_marker, exact))
                print(f"✅ 已添加标记: {new_marker}")
        elif choice == 'd':
            try:
                index = int(input("请输入要删除的标记编号: ").strip()) - 1
                if 0 <= index < len(self.RESPONSE_MARKERS):
                    removed = self.RESPONSE_MARKERS.pop(index)
                    print(f"✅ 已删除标记: {removed[0]}")
                else:
                    print("❌ 无效的编号。")
            except ValueError:
                print("❌ 请输入有效的编号。")
    
    def _modify_ai_patterns(self):
        """修改AI内容特征模式"""
        print("\n✏️  修改AI内容特征模式")
        print("当前模式 (正则表达式):")
        for i, pattern in enumerate(self.AI_CONTENT_PATTERNS, 1):
            print(f"  {i:2d}. {pattern}")
        
        print("\n操作选项:")
        print("  [a] 添加新模式")
        print("  [d] 删除模式")
        print("  [r] 返回")
        
        choice = input("请选择操作: ").strip().lower()
        
        if choice == 'a':
            new_pattern = input("请输入新的正则表达式模式: ").strip()
            if new_pattern:
                try:
                    re.compile(new_pattern)  # 验证正则表达式
                    self.AI_CONTENT_PATTERNS.append(new_pattern)
                    print(f"✅ 已添加模式: {new_pattern}")
                except re.error as e:
                    print(f"❌ 无效的正则表达式: {e}")
        elif choice == 'd':
            try:
                index = int(input("请输入要删除的模式编号: ").strip()) - 1
                if 0 <= index < len(self.AI_CONTENT_PATTERNS):
                    removed = self.AI_CONTENT_PATTERNS.pop(index)
                    print(f"✅ 已删除模式: {removed}")
                else:
                    print("❌ 无效的编号。")
            except ValueError:
                print("❌ 请输入有效的编号。")
    
    def _save_config_to_file(self):
        """保存配置到文件"""
        config_file = input("请输入配置文件名 (默认:mfat_config.json): ").strip() or "mfat_config.json"
        
        config_data = {
            "INSTRUCTION_MARKERS": self.INSTRUCTION_MARKERS,
            "RESPONSE_MARKERS": self.RESPONSE_MARKERS,
            "AI_CONTENT_PATTERNS": self.AI_CONTENT_PATTERNS,
            "COMPRESS_CONFIG": self.COMPRESS_CONFIG,
            "BOUNDARY_CONFIG": self.BOUNDARY_CONFIG,
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 配置已保存到: {config_file}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def _load_config_from_file(self):
        """从文件加载配置"""
        config_file = input("请输入配置文件名 (默认:mfat_config.json): ").strip() or "mfat_config.json"
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 更新配置
            if "INSTRUCTION_MARKERS" in config_data:
                self.INSTRUCTION_MARKERS = [(m[0], m[1]) for m in config_data["INSTRUCTION_MARKERS"]]
            
            if "RESPONSE_MARKERS" in config_data:
                self.RESPONSE_MARKERS = [(m[0], m[1]) for m in config_data["RESPONSE_MARKERS"]]
            
            if "AI_CONTENT_PATTERNS" in config_data:
                self.AI_CONTENT_PATTERNS = config_data["AI_CONTENT_PATTERNS"]
            
            if "COMPRESS_CONFIG" in config_data:
                self.COMPRESS_CONFIG.update(config_data["COMPRESS_CONFIG"])
            
            if "BOUNDARY_CONFIG" in config_data:
                self.BOUNDARY_CONFIG.update(config_data["BOUNDARY_CONFIG"])
            
            print(f"✅ 配置已从 {config_file} 加载")
            
        except FileNotFoundError:
            print(f"❌ 配置文件不存在: {config_file}")
        except json.JSONDecodeError:
            print(f"❌ 配置文件格式错误: {config_file}")
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
    
    def _reset_to_default_config(self):
        """重置为默认配置"""
        confirm = input("确定要重置为默认配置吗? (y/N): ").strip().lower()
        if confirm == 'y':
            # 重新初始化配置
            self.__init__()
            print("✅ 已重置为默认配置")
    
    def _show_help(self):
        """显示帮助信息"""
        self._clear_screen()
        print("="*60)
        print("📖 MFAT 使用帮助")
        print("="*60)
        print("\n🎯 核心功能:")
        print("  • 智能调整Markdown文档结构")
        print("  • 精准分离指令与AI响应")
        print("  • 压缩标题层级，便于AI查阅")
        print("  • 支持批量处理")
        
        print("\n🚀 快速开始:")
        print("  1. 启动程序，进入交互式控制台")
        print("  2. 选择'处理单个Markdown文件'")
        print("  3. 输入文件路径")
        print("  4. 选择处理模式")
        print("  5. 确认并开始处理")
        
        print("\n⚙️  配置说明:")
        print("  • 智能模式: 自动检测最佳参数")
        print("  • 自定义模式: 手动设置各项参数")
        print("  • 快速模式: 使用推荐默认值")
        
        print("\n📁 支持的文件格式:")
        print("  • .md (Markdown文件)")
        print("  • .markdown (Markdown文件)")
        print("  • .txt (文本文件)")
        
        print("\n🛠️  高级功能:")
        print("  • 批量处理: 一次处理多个文件")
        print("  • 配置管理: 保存/加载处理配置")
        print("  • 文件清理: 清理旧的输出文件")
        print("  • 格式测试: 测试文档格式检测")
        
        print("\n🔑 快捷键:")
        print("  • 在任何输入处输入 'q' 或 'quit' 可以取消操作")
        print("  • 在主菜单输入数字选择功能")
        
        print("\n📝 针对Syntaxnom项目的优化:")
        print("  • 专为'对话-V001'格式优化")
        print("  • 支持'AA我的指令'识别")
        print("  • 智能检测'针对你'等AI开头")
        
        print("="*60)
        input("\n按Enter键返回主菜单...")
    
    def _cleanup_old_files(self):
        """清理旧的输出文件"""
        print("\n" + "="*50)
        print("🧹 清理旧文件")
        print("="*50)
        
        while True:
            dir_path = input("\n请输入要清理的目录路径: ").strip()
            if not dir_path:
                print("操作已取消。")
                return
            
            dir_path = Path(dir_path).expanduser().resolve()
            
            if not dir_path.exists():
                print(f"❌ 目录不存在: {dir_path}")
                continue
            
            # 查找调整过的文件
            patterns = [f"*{self.DEFAULT_SUFFIX}*", "*_adjusted*", "*_优化*", "*_processed*"]
            old_files = []
            for pattern in patterns:
                old_files.extend(list(dir_path.rglob(pattern)))
            
            # 去重
            old_files = list(set(old_files))
            
            if not old_files:
                print(f"✅ 目录中没有找到符合条件的旧文件")
                return
            
            # 只保留文件，排除目录
            old_files = [f for f in old_files if f.is_file()]
            
            if not old_files:
                print(f"✅ 目录中没有找到符合条件的旧文件")
                return
            
            print(f"\n找到 {len(old_files)} 个可能为旧文件的文件:")
            for i, file in enumerate(old_files[:15], 1):
                file_time = datetime.fromtimestamp(file.stat().st_mtime)
                size_kb = file.stat().st_size / 1024
                print(f"  {i:2d}. {file.name} ({size_kb:.1f} KB, {file_time.strftime('%Y-%m-%d')})")
            
            if len(old_files) > 15:
                print(f"  ... 还有 {len(old_files) - 15} 个文件")
            
            print("\n清理选项:")
            print("  1. 删除所有找到的文件")
            print("  2. 只删除超过30天的文件")
            print("  3. 手动选择要删除的文件")
            print("  4. 取消")
            
            clean_choice = input("\n请选择清理选项 (1-4): ").strip()
            
            if clean_choice == "1":
                confirm = input(f"\n确认删除这 {len(old_files)} 个文件? (y/N): ").strip().lower()
                if confirm == 'y':
                    deleted_count = 0
                    for file in old_files:
                        try:
                            file.unlink()
                            deleted_count += 1
                        except Exception as e:
                            print(f"  删除失败 {file.name}: {e}")
                    
                    print(f"\n✅ 已删除 {deleted_count} 个文件")
                    break
            elif clean_choice == "2":
                cutoff_date = datetime.now().timestamp() - (30 * 24 * 60 * 60)  # 30天前
                old_files_to_delete = [f for f in old_files if f.stat().st_mtime < cutoff_date]
                
                if not old_files_to_delete:
                    print("✅ 没有找到超过30天的旧文件")
                    break
                
                print(f"\n找到 {len(old_files_to_delete)} 个超过30天的文件:")
                for file in old_files_to_delete[:10]:
                    file_time = datetime.fromtimestamp(file.stat().st_mtime)
                    print(f"  - {file.name} ({file_time.strftime('%Y-%m-%d')})")
                
                if len(old_files_to_delete) > 10:
                    print(f"  ... 还有 {len(old_files_to_delete) - 10} 个文件")
                
                confirm = input(f"\n确认删除这 {len(old_files_to_delete)} 个文件? (y/N): ").strip().lower()
                if confirm == 'y':
                    deleted_count = 0
                    for file in old_files_to_delete:
                        try:
                            file.unlink()
                            deleted_count += 1
                        except Exception as e:
                            print(f"  删除失败 {file.name}: {e}")
                    
                    print(f"\n✅ 已删除 {deleted_count} 个超过30天的文件")
                    break
            elif clean_choice == "3":
                print("\n手动选择要删除的文件 (输入编号，多个用逗号分隔):")
                file_map = {}
                for i, file in enumerate(old_files[:20], 1):
                    file_time = datetime.fromtimestamp(file.stat().st_mtime)
                    size_kb = file.stat().st_size / 1024
                    print(f"  {i:2d}. {file.name} ({size_kb:.1f} KB, {file_time.strftime('%Y-%m-%d')})")
                    file_map[str(i)] = file
                
                selections = input("\n请输入要删除的文件编号: ").strip()
                if selections:
                    indices = [s.strip() for s in selections.split(',')]
                    files_to_delete = []
                    for idx in indices:
                        if idx in file_map:
                            files_to_delete.append(file_map[idx])
                    
                    if files_to_delete:
                        print(f"\n将删除以下 {len(files_to_delete)} 个文件:")
                        for file in files_to_delete:
                            print(f"  - {file.name}")
                        
                        confirm = input("\n确认删除? (y/N): ").strip().lower()
                        if confirm == 'y':
                            deleted_count = 0
                            for file in files_to_delete:
                                try:
                                    file.unlink()
                                    deleted_count += 1
                                except Exception as e:
                                    print(f"  删除失败 {file.name}: {e}")
                            
                            print(f"\n✅ 已删除 {deleted_count} 个文件")
                    else:
                        print("❌ 没有选择有效的文件")
                break
            elif clean_choice == "4":
                print("操作已取消。")
                break
            else:
                print("❌ 无效选项")
    
    def _test_document_format(self):
        """测试文档格式检测"""
        print("\n" + "="*50)
        print("🔧 文档格式测试")
        print("="*50)
        
        file_path = self._prompt_file_input("请输入要测试的Markdown文件路径: ")
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            print(f"\n📊 文档分析结果:")
            print("-" * 40)
            
            # 基本统计
            lines = content.split('\n')
            print(f"总行数: {len(lines)}")
            print(f"文件大小: {len(content):,} 字符")
            
            # 检测对话格式
            dialog_count = 0
            dialog_matches = []
            for pattern in self.DIALOG_PATTERNS:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    dialog_count += 1
                    dialog_matches.append(match.group(0))
            
            print(f"\n对话检测:")
            print(f"  找到 {dialog_count} 个对话标题")
            for i, dialog in enumerate(dialog_matches[:3], 1):
                print(f"  {i}. {dialog[:50]}{'...' if len(dialog) > 50 else ''}")
            if dialog_count > 3:
                print(f"  ... 还有 {dialog_count - 3} 个")
            
            # 检测指令
            instruction_count = 0
            instruction_matches = []
            for marker, exact in self.INSTRUCTION_MARKERS:
                if exact:
                    pattern = re.escape(marker)
                else:
                    pattern = re.escape(marker)
                
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    instruction_count += 1
                    # 获取包含匹配的整行
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    line_end = content.find('\n', match.start())
                    if line_end == -1:
                        line_end = len(content)
                    instruction_matches.append(content[line_start:line_end])
            
            print(f"\n指令检测:")
            print(f"  找到 {instruction_count} 个指令标记")
            for i, instr in enumerate(instruction_matches[:3], 1):
                print(f"  {i}. {instr[:60]}{'...' if len(instr) > 60 else ''}")
            if instruction_count > 3:
                print(f"  ... 还有 {instruction_count - 3} 个")
            
            # 检测AI响应标记
            response_count = 0
            response_matches = []
            for marker, exact in self.RESPONSE_MARKERS:
                if exact:
                    pattern = re.escape(marker)
                else:
                    pattern = marker
                
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    response_count += 1
                    # 获取包含匹配的整行
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    line_end = content.find('\n', match.start())
                    if line_end == -1:
                        line_end = len(content)
                    response_matches.append(content[line_start:line_end])
            
            print(f"\nAI响应标记检测:")
            print(f"  找到 {response_count} 个响应标记")
            for i, resp in enumerate(response_matches[:3], 1):
                print(f"  {i}. {resp[:60]}{'...' if len(resp) > 60 else ''}")
            if response_count > 3:
                print(f"  ... 还有 {response_count - 3} 个")
            
            # 检测标题层级
            heading_levels = {}
            for match in re.finditer(r'^(#+)\s+(.+)$', content, re.MULTILINE):
                level = len(match.group(1))
                heading_levels[level] = heading_levels.get(level, 0) + 1
            
            print(f"\n标题层级分布:")
            if heading_levels:
                for level in sorted(heading_levels.keys()):
                    print(f"  {'#' * level}: {heading_levels[level]} 个")
            else:
                print("  未找到标题")
            
            # 评估文档结构化程度
            structure_score = 0
            if dialog_count > 0:
                structure_score += 30
            if instruction_count > 0:
                structure_score += 30
            if response_count > 0:
                structure_score += 20
            if len(heading_levels) >= 2:
                structure_score += 20
            
            print(f"\n📈 文档结构化程度评估:")
            print(f"  得分: {structure_score}/100")
            if structure_score >= 80:
                print("  评级: 优秀 - 文档结构清晰，易于处理")
            elif structure_score >= 60:
                print("  评级: 良好 - 文档有基本结构")
            elif structure_score >= 40:
                print("  评级: 一般 - 文档结构需要优化")
            else:
                print("  评级: 较差 - 文档结构不清晰")
            
            print("-" * 40)
            
        except Exception as e:
            print(f"❌ 分析文件时出错: {e}")
        
        input("\n按Enter键返回主菜单...")
    
    def _open_file(self, file_path: str):
        """打开文件"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS, Linux
                if sys.platform == 'darwin':  # macOS
                    os.system(f'open "{file_path}"')
                else:  # Linux
                    os.system(f'xdg-open "{file_path}"')
            print(f"✅ 已尝试打开文件: {file_path}")
        except Exception as e:
            print(f"❌ 无法打开文件: {e}")
    
    # ==================== 核心处理算法 ====================
    # 以下为原有的核心处理方法，保持与之前版本相同
    
    def detect_dialogs(self, content: str) -> List[Dict]:
        """检测文档中的对话段落 - 针对'对话-V001'格式优化"""
        lines = content.split('\n')
        dialogs = []
        
        current_dialog = None
        dialog_lines = []
        in_dialog = False
        
        for i, line in enumerate(lines):
            # 检测对话段落开始
            dialog_match = None
            for pattern in self.DIALOG_PATTERNS:
                dialog_match = re.match(pattern, line)
                if dialog_match:
                    break
            
            if dialog_match:
                # 保存前一个对话
                if current_dialog is not None:
                    current_dialog["content"] = '\n'.join(dialog_lines)
                    dialogs.append(current_dialog)
                
                # 解析对话信息
                if len(dialog_match.groups()) >= 2:
                    dialog_id = dialog_match.group(1) if dialog_match.group(1) else f"D{len(dialogs)+1:03d}"
                    title = dialog_match.group(2) if len(dialog_match.groups()) >= 2 else "对话记录"
                else:
                    dialog_id = f"D{len(dialogs)+1:03d}"
                    title = dialog_match.group(1) if dialog_match.group(1) else "对话记录"
                
                # 开始新对话
                current_dialog = {
                    "id": dialog_id,
                    "title": title.strip(),
                    "level": len(re.match(r'^(#+)', line).group(1)) if re.match(r'^(#+)', line) else 2,
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
                # 检查是否遇到下一个对话或文档结束
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_is_dialog = any(re.match(pattern, next_line) for pattern in self.DIALOG_PATTERNS)
                    
                    if next_is_dialog:
                        # 下一个对话开始，结束当前对话
                        current_dialog["content"] = '\n'.join(dialog_lines)
                        dialogs.append(current_dialog)
                        current_dialog = None
                        in_dialog = False
                        dialog_lines = []
                    else:
                        dialog_lines.append(line)
                else:
                    dialog_lines.append(line)
        
        # 添加最后一个对话
        if current_dialog is not None:
            current_dialog["content"] = '\n'.join(dialog_lines)
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
                dialog_id = str(uuid.uuid4())[:8]
                
                # 查找标题中的数字或字母组合
                id_match = re.search(r'([A-Za-z0-9]+)', title.split()[0] if title else '')
                if id_match:
                    potential_id = id_match.group(1)
                    if len(potential_id) >= 2:
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
        """从对话中提取指令-响应对 - 针对'AA我的指令'格式优化"""
        instructions = []
        content = dialog["content"]
        lines = content.split('\n')
        
        current_instruction = None
        instruction_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 跳过对话标题行
            if i == 0 and re.match(r'^#{1,2}\s+', line):
                i += 1
                continue
            
            # 检测指令开始
            is_instruction = False
            instruction_type = "指令"
            
            # 检查是否是已处理的指令标题
            if re.match(r'^##\s+指令\s+\d+', line):
                is_instruction = True
                instruction_type = "指令"
            else:
                # 检查其他指令标记
                for marker, exact in self.INSTRUCTION_MARKERS:
                    if exact:
                        if line.strip() == marker:
                            is_instruction = True
                            break
                    else:
                        if marker in line:
                            is_instruction = True
                            # 尝试提取更具体的指令类型
                            if "AA" in line:
                                instruction_type = "AA指令"
                            elif "BB" in line:
                                instruction_type = "BB指令"
                            break
            
            if is_instruction:
                # 保存前一个指令
                if current_instruction is not None:
                    current_instruction["content"] = '\n'.join(instruction_lines)
                    self._process_instruction_smart(current_instruction)
                    instructions.append(current_instruction)
                
                # 开始新指令
                instruction_id = len(instructions) + 1
                
                # 尝试从指令标题中提取ID
                id_match = re.search(r'指令\s*(\d+)', line)
                if id_match:
                    instruction_id = int(id_match.group(1))
                
                current_instruction = {
                    "id": instruction_id,
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
                        "detection_method": "unknown",
                    }
                }
                
                instruction_lines = [line]
                self.stats["instructions"] += 1
            
            elif current_instruction is not None:
                instruction_lines.append(line)
            
            i += 1
        
        # 添加最后一个指令
        if current_instruction is not None:
            current_instruction["content"] = '\n'.join(instruction_lines)
            self._process_instruction_smart(current_instruction)
            instructions.append(current_instruction)
        
        if not self.config["quiet"]:
            print(f"   发现 {len(instructions)} 个指令")
        
        return instructions
    
    def _process_instruction_smart(self, instruction: Dict):
        """
        处理单个指令，分离指令和响应 - 智能版本
        针对您的文档特点优化
        """
        lines = instruction["content"].split('\n')
        
        # 跳过指令标题行
        start_idx = 0
        if lines and any(marker in lines[0] for marker in ['指令', 'Instruction', 'Q:', '问题', '我的指令']):
            start_idx = 1
        
        # 使用智能边界检测算法
        boundary_idx = self._detect_boundary_smart(lines, start_idx)
        
        # 分离指令和响应
        instruction_lines = lines[:boundary_idx]
        response_lines = lines[boundary_idx:] if boundary_idx < len(lines) else []
        
        # 应用容错逻辑
        tolerance = self.config.get("tolerance_lines", 2)
        if response_lines and tolerance > 0:
            # 检查响应开头几行是否可能是误判的指令内容
            lines_to_move = []
            for j in range(min(tolerance, len(response_lines))):
                line_text = response_lines[j].strip()
                
                # 判断标准：行很短、没有结束标点、像是指令的延续
                if (len(line_text) < 60 and 
                    not any(p in line_text for p in ['.', '。', '!', '！', '?', '？', ':', '：']) and
                    not any(marker in line_text for marker in ["首先", "第一", "针对", "根据", "📊", "💡", "✅"])):
                    lines_to_move.append(j)
            
            # 移动误判的行
            for j in sorted(lines_to_move, reverse=True):
                instruction_lines.append(response_lines.pop(j))
            
            if lines_to_move and not self.config["quiet"]:
                print(f"   应用容错: 将 {len(lines_to_move)} 行移回指令")
        
        instruction["instruction"] = '\n'.join(instruction_lines).strip()
        instruction["response"] = '\n'.join(response_lines).strip()
        
        # 更新统计
        if response_lines:
            instruction["metadata"]["has_ai_response"] = True
            instruction["metadata"]["response_length"] = len(response_lines)
            self.stats["responses"] += 1
            instruction["metadata"]["detection_method"] = "smart"
        
        # 分析响应中的标题层级
        self._analyze_response_headings(instruction)
        
        # 处理AI响应
        instruction["processed_response"] = self._process_ai_response(
            instruction["response"],
            instruction["metadata"]["heading_levels"]
        )
    
    def _detect_boundary_smart(self, lines: List[str], start_idx: int) -> int:
        """
        智能边界检测算法 - 针对您的文档特点优化
        返回边界索引
        """
        # 策略1: 响应标记检测
        for i in range(start_idx, len(lines)):
            line = lines[i]
            
            # 检查所有响应标记
            for marker, exact in self.RESPONSE_MARKERS:
                if exact:
                    if line.strip() == marker:
                        return i
                else:
                    if marker in line:
                        # 额外检查：确保这不是指令内容的一部分
                        if i > start_idx + self.config["min_instruction_lines"]:
                            return i
        
        # 策略2: AI内容特征检测
        for i in range(start_idx, len(lines)):
            line = lines[i]
            
            # 跳过空行
            if line.strip() == "":
                continue
                
            # 检查AI内容特征
            for pattern in self.AI_CONTENT_PATTERNS:
                if re.match(pattern, line):
                    # 找到了AI内容特征
                    # 向前检查几行，看是否有更合适的边界
                    look_back = min(3, i - start_idx)
                    for j in range(1, look_back + 1):
                        prev_line = lines[i - j].strip()
                        # 如果前一行很短且没有结束标点，可能是误判的AI开头
                        if len(prev_line) < 50 and not any(p in prev_line for p in ['.', '。', '!', '！', '?', '？']):
                            # 检查是否是AI开头常用语
                            ai_starters = ["针对", "根据", "首先", "关于", "这个方案", "综上所述"]
                            if any(starter in prev_line for starter in ai_starters):
                                return i - j
                    
                    return i
        
        # 策略3: 基于内容的智能分析
        instruction_text = '\n'.join(lines[start_idx:min(start_idx+20, len(lines))])
        
        # 检查指令是否包含问题结尾特征
        question_indicators = ["？", "?", "吗", "呢", "如何", "怎样", "什么", "为什么"]
        has_question = any(indicator in instruction_text for indicator in question_indicators)
        
        # 如果指令包含问题，尝试找到回答开始
        if has_question:
            for i in range(start_idx, len(lines)):
                line = lines[i].strip()
                if line and len(line) > 20:  # 非空且有一定长度
                    # 检查是否是回答开头
                    answer_indicators = ["首先", "第一", "针对", "根据", "这个", "关于", "对于"]
                    if any(indicator in line[:10] for indicator in answer_indicators):
                        return i
        
        # 策略4: 后备策略 - 基于统计
        instruction_length = len(lines) - start_idx
        if instruction_length > 30:
            # 取最后1/4作为响应
            return start_idx + (instruction_length * 3 // 4)
        
        # 默认：没有找到明确的边界
        return len(lines)
    
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
    
    def _smart_compress_headings(self, content: str, heading_levels: List[int]) -> str:
        """
        智能压缩标题层级 - 针对您的文档特点优化
        """
        if not heading_levels:
            return content
        
        lines = content.split('\n')
        result = []
        
        # 分析标题层级分布
        min_original = min(heading_levels)
        max_original = max(heading_levels)
        original_range = max_original - min_original + 1
        
        # 计算可用范围
        min_allowed = self.config["ai_min_level"]  # 通常为3 (###)
        max_allowed = self.config["ai_max_level"]  # 通常为6 (######)
        allowed_range = max_allowed - min_allowed + 1
        
        # 计算压缩比例
        compress_ratio = self.config.get("compress_ratio", 0.7)
        
        # 特殊处理：如果原始标题层级已经以###开始，保持相对关系
        if min_original >= 3:
            # 原始已经以###开始，只需确保不超过最大层级
            offset = min_allowed - min_original
        else:
            # 原始以#或##开始，需要提升到###
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
                    relative_pos = (original_level - min_original) / max(1, (original_range - 1))
                    compressed_range = max(2, int(allowed_range * compress_ratio))
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
    
    def _remap_ai_headings(self, content: str) -> str:
        """简单重映射AI响应中的标题层级"""
        min_level = self.config["ai_min_level"]
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
    
    def process(self, input_file: str = None, output_file: str = None) -> bool:
        """主处理流程"""
        start_time = datetime.now()
        
        try:
            # 设置文件路径
            if input_file:
                self.config["input_file"] = input_file
            if output_file:
                self.config["output_file"] = output_file
            
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
                print(f"🔍 边界检测: {self.config['boundary_detection']}")
                
                if self.config["ai_processing"] == "smart_compress":
                    print(f"📊 压缩比例: {self.config.get('compress_ratio', 0.7):.1f}")
                
                if self.config["boundary_detection"] in ["smart", "auto"]:
                    print(f"🛡️  容错行数: {self.config.get('tolerance_lines', 2)}")
                
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
                if not self.config["quiet"]:
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
    
    # ==================== 辅助方法 ====================
    
    def print_banner(self):
        """打印程序横幅"""
        banner = f"""
╔═══════════════════════════════════════════════════════════╗
║    Markdown格式智能调整工具 v{self.VERSION} - Syntaxnom版   ║
║     专为"对话-V001"和"AA我的指令"格式优化                ║
║     🎯 精准边界检测 + 智能标题压缩 + 结构保留             ║
╚═══════════════════════════════════════════════════════════╝
        """
        if not self.config["quiet"]:
            print(banner)
    
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
        
        # 边界检测统计
        boundary_stats = self.stats.get("boundary_detection_methods", {})
        if any(boundary_stats.values()):
            summary_lines.append(f"- **边界检测:**")
            for method, count in boundary_stats.items():
                if count > 0:
                    summary_lines.append(f"  - {method}: {count} 次")
        
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
        
        summary_lines.append(f"- **边界模式:** {self.config.get('boundary_detection', 'smart')}")
        if self.config["boundary_detection"] in ["smart", "auto"]:
            summary_lines.append(f"- **容错行数:** {self.config.get('tolerance_lines', 2)}")
        
        summary_lines.append(f"- **结构保留:** {'是' if self.stats.get('structure_preserved', True) else '部分压缩'}")
        summary_lines.append(f"- **标题层级:** #{self.config.get('ai_min_level', 3)} 到 #{self.config.get('ai_max_level', 6)}")
        
        if self.stats.get("processing_time"):
            summary_lines.append(f"- **处理耗时:** {self.stats['processing_time']}")
        
        return '\n'.join(summary_lines)
    
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
        
        # 边界检测统计
        boundary_stats = self.stats.get("boundary_detection_methods", {})
        if any(boundary_stats.values()):
            methods = []
            for method, count in boundary_stats.items():
                if count > 0:
                    methods.append(f"{method}:{count}")
            if methods:
                stats.append(("边界检测", ", ".join(methods)))
        
        # 标题处理统计
        if self.stats.get('headings_processed', 0) > 0:
            stats.append(("标题处理", f"{self.stats['headings_processed']} 个"))
            
            if self.stats.get('headings_compressed', 0) > 0:
                compression_rate = self.stats['headings_compressed'] / self.stats['headings_processed']
                stats.append(("标题压缩", f"{self.stats['headings_compressed']} 个 ({compression_rate:.1%})"))
        
        # 格式优化统计
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


def main():
    """主函数入口"""
    parser = argparse.ArgumentParser(
        description="MFAT - 专为Syntaxnom项目优化的Markdown结构调整工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用模式:
  交互模式:   直接运行程序               python mfat.py
  单文件模式: 指定输入文件               python mfat.py input.md
  批处理模式: 使用通配符                python mfat.py *.md
  静默模式:   使用 --quiet 参数          python mfat.py input.md --quiet
  
交互控制台特性:
  • 启动即用，无需记忆参数
  • 直观菜单引导操作
  • 支持文件预览和格式测试
  • 可自定义配置并保存
        """
    )
    
    # 输入输出参数
    parser.add_argument(
        "input_files",
        nargs="*",
        help="输入文件路径（支持通配符，留空则进入交互模式）"
    )
    
    # 模式选择
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="强制进入交互式向导模式（旧版）"
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
    
    # 边界检测增强
    parser.add_argument(
        "--boundary",
        choices=["smart", "strict", "auto"],
        default="smart",
        help="边界检测模式 (默认: smart)"
    )
    
    parser.add_argument(
        "--tolerance",
        type=int,
        default=2,
        help="容错行数 (0-5，允许指令包含AI开头几行，默认: 2)"
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
        print(f"Markdown格式智能调整工具 (MFAT) v{MarkdownFormatAdjust.VERSION}")
        print("专为Syntaxnom项目优化的交互式控制台")
        sys.exit(0)
    
    # 决定运行模式
    if not args.input_files or args.interactive:
        # 进入增强交互控制台模式
        try:
            processor = MarkdownFormatAdjust()
            processor.run_interactive_console()
        except KeyboardInterrupt:
            print("\n\n👋 程序已退出")
            sys.exit(0)
    else:
        # 传统命令行模式（处理传入的文件）
        config = {
            "ai_processing": args.mode,
            "compress_ratio": args.compress,
            "ai_min_level": args.min_level,
            "ai_max_level": args.max_level,
            "boundary_detection": args.boundary,
            "tolerance_lines": args.tolerance,
            "generate_toc": not args.no_toc,
            "toc_max_depth": args.toc_depth,
            "collapse_blank_lines": not args.no_collapse,
            "max_blank_lines": args.max_blank,
            "trim_trailing_spaces": not args.no_trim,
            "normalize_headings": not args.no_normalize,
            "remove_document_title": not args.keep_title,
            "verbose": args.verbose,
            "quiet": args.quiet,
            "encoding": args.encoding,
            "overwrite": args.overwrite,
        }
        
        processor = MarkdownFormatAdjust(config)
        
        # 处理所有输入文件
        success_count = 0
        for input_file in args.input_files:
            try:
                print(f"\n处理文件: {input_file}")
                if processor.process(input_file):
                    success_count += 1
            except Exception as e:
                print(f"❌ 处理失败 {input_file}: {e}")
        
        if len(args.input_files) > 1:
            print(f"\n📊 批量处理完成: {success_count}/{len(args.input_files)} 个文件成功")


if __name__ == "__main__":
    main()