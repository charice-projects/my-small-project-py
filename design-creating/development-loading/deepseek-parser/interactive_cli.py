"""
interactive_cli.py
DeepSeek HTML解析器 - 增强交互式命令行界面
"""
import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import traceback

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.file_ops import FileOperations
from utils.logger import get_logger
from core.deepseek_parser import DeepSeekParser
from core.conversation_builder import ConversationBuilder
from core.content_formatter import ContentFormatter
from outputs.optimized_markdown import OptimizedMarkdownWriter
from outputs.simple_markdown import SimpleMarkdownWriter
from batch.processor import BatchProcessor

try:
    from colorama import init, Fore, Back, Style, Cursor
    from pyfiglet import Figlet
    from tqdm import tqdm
    import inquirer
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    HAS_RICH = True
except ImportError:
    print("正在安装增强依赖...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                             "colorama", "pyfiglet", "tqdm", "inquirer", "rich"])
        from colorama import init, Fore, Back, Style, Cursor
        from pyfiglet import Figlet
        from tqdm import tqdm
        import inquirer
        from rich.console import Console
        from rich.table import Table
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
        from rich.panel import Panel
        from rich.layout import Layout
        from rich.text import Text
        from rich.prompt import Prompt, Confirm, IntPrompt
        from rich.syntax import Syntax
        from rich.markdown import Markdown
        HAS_RICH = True
        print("增强依赖安装完成！")
    except:
        HAS_RICH = False
        print("无法安装增强依赖，将使用基础界面")

# 初始化colorama
init(autoreset=True)


class EnhancedInteractiveCLI:
    """增强的交互式命令行界面"""
    
    def __init__(self, config_path=None):
        self.config = FileOperations.load_config(config_path or 'config.yaml')
        self.logger = get_logger(self.config)
        
        # 初始化组件
        self.parser = DeepSeekParser(self.config)
        self.builder = ConversationBuilder(self.config)
        self.formatter = ContentFormatter(self.config)
        self.batch_processor = BatchProcessor(self.config)
        
        # 初始化富文本控制台
        self.console = Console() if HAS_RICH else None
        
        # 状态变量
        self.current_mode = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.stats = {
            'files_processed': 0,
            'total_rounds': 0,
            'total_words': 0,
            'start_time': None,
            'end_time': None
        }
        
        self.logger.info("增强交互式CLI初始化完成")
    
    def run(self):
        """运行主交互循环"""
        try:
            # 显示欢迎界面
            self._show_welcome()
            
            # 主循环
            while True:
                try:
                    # 显示主菜单
                    choice = self._show_main_menu()
                    
                    if choice == '1':  # 解析单个文件
                        self._handle_single_file()
                    elif choice == '2':  # 批量处理
                        self._handle_batch_processing()
                    elif choice == '3':  # 目录管理
                        self._handle_directory_management()
                    elif choice == '4':  # 配置管理
                        self._handle_config_management()
                    elif choice == '5':  # 查看统计
                        self._show_statistics()
                    elif choice == '6':  # 使用教程
                        self._show_tutorial()
                    elif choice == '7':  # 关于
                        self._show_about()
                    elif choice == '0':  # 退出
                        if self._confirm_exit():
                            break
                    else:
                        self._show_message("无效选项，请重新选择", "error")
                
                except KeyboardInterrupt:
                    self._show_message("\n操作被用户中断", "warning")
                    continue
                except Exception as e:
                    self._show_message(f"发生错误: {str(e)}", "error")
                    self.logger.error(f"交互循环错误: {e}")
                    self.logger.debug(traceback.format_exc())
        
        except Exception as e:
            self._show_message(f"程序运行出错: {str(e)}", "error")
            self.logger.error(f"程序运行错误: {e}")
            self.logger.debug(traceback.format_exc())
        finally:
            self._show_goodbye()
    
    def _show_welcome(self):
        """显示欢迎界面"""
        self._clear_screen()
        
        if HAS_RICH and self.console:
            # 使用富文本显示欢迎界面
            self.console.print("\n")
            
            # ASCII艺术标题
            try:
                f = Figlet(font='slant')
                ascii_art = f.renderText('DeepSeek Parser')
                self.console.print(f"[bold cyan]{ascii_art}[/bold cyan]")
            except:
                self.console.print("[bold cyan]" + "="*60 + "[/bold cyan]")
                self.console.print("[bold cyan]          DeepSeek HTML 解析器 - 增强交互版          [/bold cyan]")
                self.console.print("[bold cyan]" + "="*60 + "[/bold cyan]")
            
            # 欢迎信息
            welcome_text = Text()
            welcome_text.append("\n欢迎使用 DeepSeek HTML 解析器！\n", style="bold yellow")
            welcome_text.append("这是一个强大的工具，专门用于将DeepSeek对话HTML转换为优化Markdown格式。\n", style="green")
            welcome_text.append(f"会话ID: {self.session_id}\n", style="dim")
            welcome_text.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n", style="dim")
            
            self.console.print(Panel(
                welcome_text,
                title="[bold]欢迎信息[/bold]",
                border_style="cyan",
                padding=(1, 2)
            ))
            
            # 快速提示
            tips = [
                "💡 提示: 使用数字键选择菜单选项",
                "💡 提示: 按 Ctrl+C 可以中断当前操作",
                "💡 提示: 配置保存在 config.yaml 文件中",
                "💡 提示: 日志文件: deepseek_parser.log"
            ]
            
            for tip in tips:
                self.console.print(f"[dim]{tip}[/dim]")
            
            self.console.print("\n")
        else:
            # 基础文本界面
            print("\n" + "="*60)
            print(Fore.CYAN + "      DeepSeek HTML 解析器 - 增强交互版      " + Style.RESET_ALL)
            print("="*60)
            print(Fore.YELLOW + "\n欢迎使用 DeepSeek HTML 解析器！" + Style.RESET_ALL)
            print(Fore.GREEN + "这是一个强大的工具，专门用于将DeepSeek对话HTML转换为优化Markdown格式。" + Style.RESET_ALL)
            print(Fore.WHITE + f"\n会话ID: {self.session_id}" + Style.RESET_ALL)
            print(Fore.WHITE + f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + Style.RESET_ALL)
            print("\n" + "="*60)
    
    def _show_main_menu(self) -> str:
        """显示主菜单并获取用户选择"""
        if HAS_RICH and self.console:
            # 富文本菜单
            menu_options = [
                ("1", "📄 解析单个HTML文件", "处理单个DeepSeek对话HTML文件"),
                ("2", "📁 批量处理HTML文件", "处理目录下的所有HTML文件"),
                ("3", "🗂️  目录管理", "管理输入/输出目录和文件"),
                ("4", "⚙️  配置管理", "查看和修改解析配置"),
                ("5", "📊 查看统计", "查看处理统计信息"),
                ("6", "📚 使用教程", "查看详细使用教程"),
                ("7", "ℹ️  关于", "关于本程序和版本信息"),
                ("0", "🚪 退出程序", "安全退出程序")
            ]
            
            # 创建菜单表格
            table = Table(title="主菜单", show_header=False, box=None)
            table.add_column("选项", style="cyan", width=4)
            table.add_column("功能", style="yellow", width=25)
            table.add_column("描述", style="green")
            
            for option, name, desc in menu_options:
                table.add_row(f"[bold]{option}[/bold]", name, desc)
            
            self.console.print("\n")
            self.console.print(table)
            self.console.print("\n")
            
            # 获取用户选择
            while True:
                choice = Prompt.ask(
                    "[bold yellow]请选择操作 (输入数字)[/bold yellow]",
                    choices=['0', '1', '2', '3', '4', '5', '6', '7'],
                    show_choices=False
                )
                return choice
        
        else:
            # 基础文本菜单
            print(Fore.CYAN + "\n" + "="*60 + Style.RESET_ALL)
            print(Fore.YELLOW + "                    主菜单                    " + Style.RESET_ALL)
            print(Fore.CYAN + "="*60 + Style.RESET_ALL)
            print(Fore.GREEN + "1. 📄 解析单个HTML文件" + Style.RESET_ALL)
            print(Fore.GREEN + "2. 📁 批量处理HTML文件" + Style.RESET_ALL)
            print(Fore.GREEN + "3. 🗂️  目录管理" + Style.RESET_ALL)
            print(Fore.GREEN + "4. ⚙️  配置管理" + Style.RESET_ALL)
            print(Fore.GREEN + "5. 📊 查看统计" + Style.RESET_ALL)
            print(Fore.GREEN + "6. 📚 使用教程" + Style.RESET_ALL)
            print(Fore.GREEN + "7. ℹ️  关于" + Style.RESET_ALL)
            print(Fore.RED + "0. 🚪 退出程序" + Style.RESET_ALL)
            print(Fore.CYAN + "="*60 + Style.RESET_ALL)
            
            while True:
                choice = input(Fore.YELLOW + "\n请选择操作 (输入数字 0-7): " + Style.RESET_ALL).strip()
                if choice in ['0', '1', '2', '3', '4', '5', '6', '7']:
                    return choice
                else:
                    print(Fore.RED + "无效选项，请输入 0-7 之间的数字" + Style.RESET_ALL)
    
    def _handle_single_file(self):
        """处理单个文件"""
        self._clear_screen()
        
        if HAS_RICH and self.console:
            self.console.print(Panel(
                "[bold yellow]📄 单个文件解析模式[/bold yellow]\n\n"
                "在此模式下，您可以处理单个DeepSeek对话HTML文件，\n"
                "并将其转换为优化格式的Markdown文档。",
                title="模式说明",
                border_style="yellow"
            ))
        
        else:
            print(Fore.YELLOW + "\n" + "="*60 + Style.RESET_ALL)
            print(Fore.YELLOW + "              📄 单个文件解析模式              " + Style.RESET_ALL)
            print(Fore.YELLOW + "="*60 + Style.RESET_ALL)
            print(Fore.GREEN + "\n在此模式下，您可以处理单个DeepSeek对话HTML文件，" + Style.RESET_ALL)
            print(Fore.GREEN + "并将其转换为优化格式的Markdown文档。" + Style.RESET_ALL)
        
        # 获取输入文件路径
        input_file = self._ask_for_file("请输入HTML文件路径")
        if not input_file:
            return
        
        # 检查文件是否存在
        if not os.path.exists(input_file):
            self._show_message(f"文件不存在: {input_file}", "error")
            return
        
        # 选择输出格式
        format_choice = self._ask_choice(
            "请选择输出格式",
            ["优化格式 (推荐)", "简单格式"],
            default=0
        )
        format_type = 'optimized' if format_choice == 0 else 'simple'
        
        # 选择输出位置
        output_choice = self._ask_choice(
            "输出文件位置",
            ["自动生成 (推荐)", "自定义路径"],
            default=0
        )
        
        if output_choice == 1:
            output_file = self._ask_for_path("请输入输出文件路径", is_file=True)
            if not output_file:
                return
        else:
            # 自动生成输出文件名
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_dir = self.config.get('paths', {}).get('output_dir', '.')
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成不重复的文件名
            counter = 1
            output_file = os.path.join(output_dir, f"{base_name}.md")
            while os.path.exists(output_file):
                output_file = os.path.join(output_dir, f"{base_name}_{counter}.md")
                counter += 1
        
        # 显示处理配置摘要
        self._show_processing_summary({
            '输入文件': input_file,
            '输出文件': output_file,
            '输出格式': format_type,
            '文件大小': f"{os.path.getsize(input_file) / 1024:.1f} KB"
        })
        
        # 确认开始处理
        if not self._ask_confirmation("是否开始处理？"):
            self._show_message("已取消处理", "info")
            return
        
        # 开始处理
        try:
            # 读取HTML文件
            self._show_progress("正在读取HTML文件...", 0)
            html_content = FileOperations.read_file(input_file)
            
            if not html_content:
                self._show_message("文件内容为空", "error")
                return
            
            # 解析HTML
            self._show_progress("正在解析HTML结构...", 25)
            parsed_data = self.parser.parse_html(html_content)
            
            if not parsed_data.get('rounds'):
                self._show_message("未解析到对话轮次", "warning")
                return
            
            # 构建对话
            self._show_progress("正在构建对话结构...", 50)
            conversation = self.builder.build(parsed_data)
            
            if not conversation.get('rounds'):
                self._show_message("未构建出有效对话", "warning")
                return
            
            # 格式化内容
            self._show_progress("正在格式化内容...", 75)
            for round_data in conversation['rounds']:
                # 格式化用户内容
                user_content = round_data['user']['content']
                round_data['user']['content'] = self.formatter.format_content(user_content, 'user')
                
                # 格式化AI内容
                ai_content = round_data['ai']['content']
                round_data['ai']['content'] = self.formatter.format_content(ai_content, 'ai')
            
            # 选择输出格式
            if format_type == 'simple':
                writer = SimpleMarkdownWriter(self.config)
            else:
                writer = OptimizedMarkdownWriter(self.config)
            
            # 写入Markdown
            self._show_progress("正在生成Markdown文档...", 90)
            markdown_content = writer.write(conversation, output_file)
            
            # 完成
            self._show_progress("处理完成！", 100)
            
            # 显示结果
            self._show_processing_result({
                '状态': '✅ 成功',
                '对话ID': conversation.get('dialog_id', '未知'),
                '有效轮次': len(conversation['rounds']),
                '输出文件': output_file,
                '文件大小': f"{len(markdown_content) / 1024:.1f} KB",
                '生成时间': datetime.now().strftime('%H:%M:%S')
            })
            
            # 更新统计
            self.stats['files_processed'] += 1
            self.stats['total_rounds'] += len(conversation['rounds'])
            
            # 询问是否查看文件
            if self._ask_confirmation("是否查看生成的Markdown文件？"):
                self._preview_file(output_file)
            
            # 询问是否打开目录
            if self._ask_confirmation("是否打开输出目录？"):
                self._open_directory(os.path.dirname(output_file))
            
        except Exception as e:
            self._show_message(f"处理失败: {str(e)}", "error")
            self.logger.error(f"单文件处理失败: {e}")
            self.logger.debug(traceback.format_exc())
    
    def _handle_batch_processing(self):
        """处理批量处理"""
        self._clear_screen()
        
        if HAS_RICH and self.console:
            self.console.print(Panel(
                "[bold yellow]📁 批量处理模式[/bold yellow]\n\n"
                "在此模式下，您可以批量处理目录下的所有DeepSeek对话HTML文件，\n"
                "自动转换为优化格式的Markdown文档并保存到知识库。",
                title="模式说明",
                border_style="yellow"
            ))
        
        else:
            print(Fore.YELLOW + "\n" + "="*60 + Style.RESET_ALL)
            print(Fore.YELLOW + "              📁 批量处理模式              " + Style.RESET_ALL)
            print(Fore.YELLOW + "="*60 + Style.RESET_ALL)
            print(Fore.GREEN + "\n在此模式下，您可以批量处理目录下的所有DeepSeek对话HTML文件，" + Style.RESET_ALL)
            print(Fore.GREEN + "自动转换为优化格式的Markdown文档并保存到知识库。" + Style.RESET_ALL)
        
        # 获取输入目录
        input_dir = self._ask_for_directory("请输入HTML文件目录路径")
        if not input_dir:
            return
        
        # 检查目录是否存在
        if not os.path.exists(input_dir):
            self._show_message(f"目录不存在: {input_dir}", "error")
            
            # 询问是否创建目录
            if self._ask_confirmation("是否创建该目录？"):
                try:
                    os.makedirs(input_dir, exist_ok=True)
                    self._show_message(f"目录已创建: {input_dir}", "success")
                    
                    # 询问是否查看目录
                    if self._ask_confirmation("是否打开目录添加文件？"):
                        self._open_directory(input_dir)
                    return
                except Exception as e:
                    self._show_message(f"创建目录失败: {str(e)}", "error")
                    return
            else:
                return
        
        # 获取输出目录
        output_dir = self._ask_for_directory("请输入输出目录路径", 
                                           default=self.config.get('paths', {}).get('output_dir', './knowledge_base'))
        if not output_dir:
            return
        
        # 创建输出目录（如果不存在）
        os.makedirs(output_dir, exist_ok=True)
        
        # 选择处理模式
        mode_choice = self._ask_choice(
            "请选择处理模式",
            ["标准模式 (处理所有文件)", "增量模式 (只处理新文件)", "测试模式 (仅扫描不处理)"],
            default=0
        )
        
        incremental = (mode_choice == 1)
        test_mode = (mode_choice == 2)
        
        # 其他选项
        overwrite = False
        verbose = False
        
        if not test_mode:
            overwrite = self._ask_confirmation("是否覆盖已存在的输出文件？")
            verbose = self._ask_confirmation("是否显示详细处理信息？")
        
        # 显示处理配置摘要
        summary = {
            '输入目录': input_dir,
            '输出目录': output_dir,
            '处理模式': ['标准模式', '增量模式', '测试模式'][mode_choice],
            '覆盖文件': '是' if overwrite else '否',
            '详细输出': '是' if verbose else '否'
        }
        
        # 扫描文件
        self._show_progress("正在扫描目录...", 0)
        html_files = FileOperations.find_files(input_dir, ['.html', '.htm'])
        
        if not html_files:
            self._show_message(f"在目录中未找到HTML文件: {input_dir}", "warning")
            
            # 询问是否查看示例
            if self._ask_confirmation("是否查看示例文件？"):
                self._show_example_structure()
            return
        
        summary['文件数量'] = len(html_files)
        summary['总大小'] = f"{sum(os.path.getsize(f) for f in html_files) / 1024:.1f} KB"
        
        self._show_processing_summary(summary)
        
        # 确认开始处理
        if not self._ask_confirmation("是否开始批量处理？"):
            self._show_message("已取消处理", "info")
            return
        
        # 开始批量处理
        try:
            self.stats['start_time'] = datetime.now()
            
            if HAS_RICH and self.console and not test_mode:
                # 使用富文本进度条
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    console=self.console
                ) as progress:
                    
                    task = progress.add_task("[cyan]批量处理中...", total=len(html_files))
                    
                    results = {
                        'total_files': len(html_files),
                        'success': 0,
                        'failed': 0,
                        'failed_files': [],
                        'details': []
                    }
                    
                    for i, file_path in enumerate(html_files):
                        try:
                            # 更新进度描述
                            progress.update(task, description=f"[cyan]处理: {os.path.basename(file_path)[:30]}...")
                            
                            if test_mode:
                                # 测试模式：只检查不处理
                                results['details'].append({
                                    'file': file_path,
                                    'status': 'checked',
                                    'size': os.path.getsize(file_path)
                                })
                                results['success'] += 1
                            else:
                                # 实际处理
                                file_result = self._process_single_file_in_batch(
                                    file_path, output_dir, overwrite
                                )
                                
                                if file_result['success']:
                                    results['success'] += 1
                                else:
                                    results['failed'] += 1
                                    results['failed_files'].append(file_path)
                                
                                results['details'].append(file_result)
                            
                            # 更新进度
                            progress.update(task, advance=1)
                            
                        except Exception as e:
                            results['failed'] += 1
                            results['failed_files'].append(file_path)
                            self.logger.error(f"处理文件失败 {file_path}: {e}")
                            progress.update(task, advance=1)
                    
                    # 完成进度条
                    progress.update(task, description="[green]批量处理完成！")
                    
            else:
                # 基础进度条或测试模式
                results = {
                    'total_files': len(html_files),
                    'success': 0,
                    'failed': 0,
                    'failed_files': [],
                    'details': []
                }
                
                print(Fore.CYAN + "\n开始批量处理..." + Style.RESET_ALL)
                
                for i, file_path in enumerate(html_files):
                    try:
                        file_name = os.path.basename(file_path)
                        progress = (i + 1) / len(html_files) * 100
                        
                        print(f"\r[{Fore.CYAN}{'█' * int(progress/2)}{Fore.WHITE}{'░' * (50 - int(progress/2))}{Style.RESET_ALL}] "
                              f"{progress:.1f}% - 处理: {file_name[:40]}", end="")
                        
                        if test_mode:
                            # 测试模式
                            results['details'].append({
                                'file': file_path,
                                'status': 'checked',
                                'size': os.path.getsize(file_path)
                            })
                            results['success'] += 1
                        else:
                            # 实际处理
                            file_result = self._process_single_file_in_batch(
                                file_path, output_dir, overwrite
                            )
                            
                            if file_result['success']:
                                results['success'] += 1
                            else:
                                results['failed'] += 1
                                results['failed_files'].append(file_path)
                            
                            results['details'].append(file_result)
                        
                    except Exception as e:
                        results['failed'] += 1
                        results['failed_files'].append(file_path)
                        self.logger.error(f"处理文件失败 {file_path}: {e}")
                
                print()  # 换行
            
            # 处理完成
            self.stats['end_time'] = datetime.now()
            processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            results['processing_time'] = processing_time
            
            # 更新统计
            self.stats['files_processed'] += results['success']
            
            # 显示结果
            self._show_batch_results(results, test_mode)
            
            # 生成报告
            if not test_mode and results['total_files'] > 0:
                if self._ask_confirmation("是否生成详细处理报告？"):
                    report_file = self._generate_batch_report(results, output_dir)
                    self._show_message(f"报告已生成: {report_file}", "success")
            
            # 询问是否查看输出目录
            if results['success'] > 0 and self._ask_confirmation("是否打开输出目录？"):
                self._open_directory(output_dir)
            
        except Exception as e:
            self._show_message(f"批量处理失败: {str(e)}", "error")
            self.logger.error(f"批量处理失败: {e}")
            self.logger.debug(traceback.format_exc())
    
    def _process_single_file_in_batch(self, file_path: str, output_dir: str, overwrite: bool) -> Dict[str, Any]:
        """在批量处理中处理单个文件"""
        result = {
            'file': file_path,
            'success': False,
            'error': None,
            'processing_time': 0
        }
        
        start_time = time.time()
        
        try:
            # 读取HTML文件
            html_content = FileOperations.read_file(file_path)
            
            if not html_content:
                result['error'] = '文件内容为空'
                return result
            
            # 解析HTML
            parsed_data = self.parser.parse_html(html_content)
            
            if not parsed_data.get('rounds'):
                result['error'] = '未解析到对话轮次'
                return result
            
            # 构建对话
            conversation = self.builder.build(parsed_data)
            
            if not conversation.get('rounds'):
                result['error'] = '未构建出有效对话'
                return result
            
            # 格式化内容
            for round_data in conversation['rounds']:
                user_content = round_data['user']['content']
                round_data['user']['content'] = self.formatter.format_content(user_content, 'user')
                
                ai_content = round_data['ai']['content']
                round_data['ai']['content'] = self.formatter.format_content(ai_content, 'ai')
            
            # 生成输出文件名
            output_filename = FileOperations.generate_output_filename(
                conversation, 
                output_dir,
                '.md'
            )
            
            output_file = os.path.join(output_dir, output_filename)
            
            # 检查文件是否已存在
            if os.path.exists(output_file) and not overwrite:
                # 生成新文件名
                base_name, ext = os.path.splitext(output_filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{base_name}_{timestamp}{ext}"
                output_file = os.path.join(output_dir, output_filename)
            
            # 写入Markdown
            writer = OptimizedMarkdownWriter(self.config)
            markdown_content = writer.write(conversation, output_file)
            
            # 记录结果
            result['success'] = True
            result['output_file'] = output_file
            result['dialog_id'] = conversation.get('dialog_id')
            result['rounds'] = len(conversation['rounds'])
            
        except Exception as e:
            result['error'] = str(e)
        
        finally:
            # 计算处理时间
            end_time = time.time()
            result['processing_time'] = end_time - start_time
        
        return result
    
    def _handle_directory_management(self):
        """处理目录管理"""
        self._clear_screen()
        
        if HAS_RICH and self.console:
            self.console.print(Panel(
                "[bold yellow]🗂️  目录管理[/bold yellow]\n\n"
                "在此模式下，您可以管理输入/输出目录，查看文件列表，\n"
                "清理旧文件，以及检查目录结构。",
                title="模式说明",
                border_style="yellow"
            ))
        
        else:
            print(Fore.YELLOW + "\n" + "="*60 + Style.RESET_ALL)
            print(Fore.YELLOW + "              🗂️  目录管理              " + Style.RESET_ALL)
            print(Fore.YELLOW + "="*60 + Style.RESET_ALL)
        
        # 目录管理选项
        options = [
            ("查看输入目录", self._view_input_directory),
            ("查看输出目录", self._view_output_directory),
            ("查看失败目录", self._view_failed_directory),
            ("清理旧文件", self._cleanup_old_files),
            ("检查目录结构", self._check_directory_structure),
            ("创建示例文件", self._create_example_files),
            ("返回主菜单", None)
        ]
        
        while True:
            choice = self._ask_choice(
                "请选择目录管理操作",
                [opt[0] for opt in options],
                allow_cancel=True
            )
            
            if choice == len(options) - 1:  # 返回主菜单
                break
            
            # 执行选中的操作
            if options[choice][1]:
                options[choice][1]()
    
    def _handle_config_management(self):
        """处理配置管理"""
        self._clear_screen()
        
        if HAS_RICH and self.console:
            self.console.print(Panel(
                "[bold yellow]⚙️  配置管理[/bold yellow]\n\n"
                "在此模式下，您可以查看和修改解析配置，\n"
                "调整输出格式，以及管理全局设置。",
                title="模式说明",
                border_style="yellow"
            ))
        
        else:
            print(Fore.YELLOW + "\n" + "="*60 + Style.RESET_ALL)
            print(Fore.YELLOW + "              ⚙️  配置管理              " + Style.RESET_ALL)
            print(Fore.YELLOW + "="*60 + Style.RESET_ALL)
        
        # 配置管理选项
        options = [
            ("查看当前配置", self._view_current_config),
            ("修改路径配置", self._modify_path_config),
            ("修改解析配置", self._modify_parsing_config),
            ("修改输出配置", self._modify_output_config),
            ("修改批量处理配置", self._modify_batch_config),
            ("重置为默认配置", self._reset_to_default_config),
            ("保存配置到文件", self._save_config_to_file),
            ("加载配置文件", self._load_config_from_file),
            ("返回主菜单", None)
        ]
        
        while True:
            choice = self._ask_choice(
                "请选择配置管理操作",
                [opt[0] for opt in options],
                allow_cancel=True
            )
            
            if choice == len(options) - 1:  # 返回主菜单
                break
            
            # 执行选中的操作
            if options[choice][1]:
                options[choice][1]()
    
    def _show_statistics(self):
        """显示统计信息"""
        self._clear_screen()
        
        if HAS_RICH and self.console:
            # 创建统计表格
            table = Table(title="📊 处理统计", box=None)
            table.add_column("统计项", style="cyan")
            table.add_column("数值", style="yellow")
            table.add_column("备注", style="green")
            
            table.add_row("处理的文件数", str(self.stats['files_processed']), 
                         "本次会话处理的总文件数")
            table.add_row("总对话轮次", str(self.stats['total_rounds']), 
                         "所有文件中的对话轮次总数")
            table.add_row("会话ID", self.session_id, "当前会话的唯一标识")
            table.add_row("会话开始时间", 
                         self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S') 
                         if self.stats['start_time'] else "未开始",
                         "本次会话的开始时间")
            table.add_row("会话结束时间", 
                         self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S') 
                         if self.stats['end_time'] else "进行中",
                         "本次会话的结束时间")
            
            if self.stats['start_time'] and self.stats['end_time']:
                duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
                table.add_row("总处理时间", f"{duration:.2f} 秒", 
                             f"平均 {duration/max(1, self.stats['files_processed']):.2f} 秒/文件")
            
            self.console.print("\n")
            self.console.print(Panel(table, border_style="cyan"))
            
            # 显示目录信息
            paths = self.config.get('paths', {})
            dir_info = "\n".join([
                f"输入目录: {paths.get('input_dir', '未设置')}",
                f"输出目录: {paths.get('output_dir', '未设置')}",
                f"失败目录: {paths.get('failed_dir', '未设置')}"
            ])
            
            self.console.print(Panel(
                dir_info,
                title="目录信息",
                border_style="yellow"
            ))
            
        else:
            print(Fore.YELLOW + "\n" + "="*60 + Style.RESET_ALL)
            print(Fore.YELLOW + "              📊 处理统计              " + Style.RESET_ALL)
            print(Fore.YELLOW + "="*60 + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n基本统计:" + Style.RESET_ALL)
            print(Fore.WHITE + f"  处理的文件数: {self.stats['files_processed']}" + Style.RESET_ALL)
            print(Fore.WHITE + f"  总对话轮次: {self.stats['total_rounds']}" + Style.RESET_ALL)
            print(Fore.WHITE + f"  会话ID: {self.session_id}" + Style.RESET_ALL)
            
            if self.stats['start_time']:
                print(Fore.WHITE + f"  会话开始时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}" + Style.RESET_ALL)
            
            if self.stats['end_time']:
                print(Fore.WHITE + f"  会话结束时间: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}" + Style.RESET_ALL)
            
            if self.stats['start_time'] and self.stats['end_time']:
                duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
                print(Fore.WHITE + f"  总处理时间: {duration:.2f} 秒" + Style.RESET_ALL)
                print(Fore.WHITE + f"  平均时间: {duration/max(1, self.stats['files_processed']):.2f} 秒/文件" + Style.RESET_ALL)
            
            paths = self.config.get('paths', {})
            print(Fore.CYAN + "\n目录信息:" + Style.RESET_ALL)
            print(Fore.WHITE + f"  输入目录: {paths.get('input_dir', '未设置')}" + Style.RESET_ALL)
            print(Fore.WHITE + f"  输出目录: {paths.get('output_dir', '未设置')}" + Style.RESET_ALL)
            print(Fore.WHITE + f"  失败目录: {paths.get('failed_dir', '未设置')}" + Style.RESET_ALL)
            
            print(Fore.YELLOW + "\n" + "="*60 + Style.RESET_ALL)
        
        # 等待用户按键
        self._wait_for_keypress()
    
    def _show_tutorial(self):
        """显示使用教程"""
        self._clear_screen()
        
        tutorial_content = """
# 📚 DeepSeek HTML解析器 - 使用教程

## 🎯 工具简介
DeepSeek HTML解析器是一个专门用于将DeepSeek对话HTML文件转换为优化Markdown格式的工具。

## 🚀 快速开始

### 1. 准备工作
1. 将DeepSeek对话保存为HTML文件
2. 将HTML文件放入 `html_conversations/` 目录

### 2. 使用方法
- **单个文件处理**: 处理单个HTML文件
- **批量处理**: 处理目录下的所有HTML文件
- **增量处理**: 只处理新文件或修改过的文件

### 3. 输出格式
生成的Markdown文件具有以下特点:
- 智能标题生成
- 用户问题自动折叠
- 代码块智能处理
- 完整的格式保留

## 💡 使用技巧

### 最佳实践
1. **文件命名**: 使用有意义的文件名，如 `python_异步编程对话.html`
2. **目录结构**: 保持输入/输出目录结构清晰
3. **定期备份**: 定期备份生成的知识库文件

### 故障排除
1. **解析失败**: 检查HTML文件结构是否符合DeepSeek格式
2. **内容丢失**: 检查配置中的选择器设置
3. **性能问题**: 对于大量文件，使用增量处理模式

## 🔧 高级功能

### 配置自定义
编辑 `config.yaml` 文件可以:
- 调整HTML元素选择器
- 修改输出格式
- 配置批量处理参数

### 脚本集成
可以通过Python API集成到其他工作流程中:
```python
from deepseek_parser import DeepSeekParser
parser = DeepSeekParser()
result = parser.parse_file("conversation.html")