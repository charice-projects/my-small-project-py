"""
main.py
DeepSeek HTML解析器主入口
"""
import os
import sys
import argparse
from datetime import datetime
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


class DeepSeekParserCLI:
    """DeepSeek HTML解析器命令行界面"""
    
    def __init__(self, config_path=None):
        # 加载配置
        self.config = FileOperations.load_config(config_path or 'config.yaml')
        
        # 初始化日志记录器
        self.logger = get_logger(self.config)
        
        # 初始化组件
        self.parser = DeepSeekParser(self.config)
        self.builder = ConversationBuilder(self.config)
        self.formatter = ContentFormatter(self.config)
        self.batch_processor = BatchProcessor(self.config)
        
        self.logger.info("DeepSeek HTML解析器初始化完成")
    
    def parse_single_file(self, input_file, output_file=None, format_type='optimized'):
        """解析单个HTML文件"""
        try:
            self.logger.info(f"开始解析单个文件: {input_file}")
            
            # 读取HTML文件
            html_content = FileOperations.read_file(input_file)
            
            if not html_content:
                self.logger.error("文件内容为空")
                return False
            
            # 解析HTML
            parsed_data = self.parser.parse_html(html_content)
            
            if not parsed_data.get('rounds'):
                self.logger.warning("未解析到对话轮次")
                return False
            
            # 构建对话
            conversation = self.builder.build(parsed_data)
            
            if not conversation.get('rounds'):
                self.logger.warning("未构建出有效对话")
                return False
            
            # 格式化内容
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
            
            # 生成输出文件路径
            if not output_file:
                # 自动生成输出文件名
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                output_dir = self.config.get('paths', {}).get('output_dir', '.')
                output_file = os.path.join(output_dir, f"{base_name}.md")
            
            # 写入Markdown
            markdown_content = writer.write(conversation, output_file)
            
            self.logger.info(f"解析完成，输出文件: {output_file}")
            self.logger.info(f"对话ID: {conversation.get('dialog_id')}")
            self.logger.info(f"有效轮次: {len(conversation['rounds'])}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"解析文件失败: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def batch_process(self, input_dir=None, output_dir=None, incremental=False, verbose=False):
        """批量处理HTML文件"""
        try:
            input_dir = input_dir or self.config.get('paths', {}).get('input_dir', './html_conversations')
            output_dir = output_dir or self.config.get('paths', {}).get('output_dir', './knowledge_base')
            
            # 检查输入目录是否存在
            if not os.path.exists(input_dir):
                self.logger.error(f"输入目录不存在: {input_dir}")
                return False
            
            self.logger.info(f"开始批量处理，输入目录: {input_dir}")
            self.logger.info(f"输出目录: {output_dir}")
            
            # 执行批量处理
            results = self.batch_processor.process_directory(
                input_dir=input_dir,
                output_dir=output_dir,
                incremental=incremental,
                verbose=verbose
            )
            
            # 显示结果摘要
            self._display_batch_results(results)
            
            return True
            
        except Exception as e:
            self.logger.error(f"批量处理失败: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def _display_batch_results(self, results):
        """显示批量处理结果"""
        print("\n" + "="*60)
        print("批量处理结果摘要")
        print("="*60)
        
        print(f"总文件数: {results['total_files']}")
        print(f"成功: {results['success']}")
        print(f"失败: {results['failed']}")
        
        if results['total_files'] > 0:
            success_rate = (results['success'] / results['total_files']) * 100
            print(f"成功率: {success_rate:.1f}%")
        
        print(f"处理时间: {results['processing_time']:.2f} 秒")
        
        if results.get('report_file'):
            print(f"详细报告: {results['report_file']}")
        
        # 显示失败文件
        if results['failed_files']:
            print(f"\n失败文件 ({len(results['failed_files'])}):")
            for file_path in results['failed_files'][:5]:  # 只显示前5个
                print(f"  - {os.path.basename(file_path)}")
            
            if len(results['failed_files']) > 5:
                print(f"  ... 还有 {len(results['failed_files']) - 5} 个失败文件")
        
        print("="*60 + "\n")
    
    def interactive_mode(self):
        """交互式模式"""
        print("\n" + "="*60)
        print("DeepSeek HTML解析器 - 交互模式")
        print("="*60)
        
        while True:
            print("\n请选择操作:")
            print("1. 解析单个HTML文件")
            print("2. 批量处理HTML文件")
            print("3. 查看配置")
            print("4. 退出")
            
            choice = input("\n请输入选项 (1-4): ").strip()
            
            if choice == '1':
                self._interactive_single_file()
            elif choice == '2':
                self._interactive_batch()
            elif choice == '3':
                self._show_config()
            elif choice == '4':
                print("感谢使用，再见！")
                break
            else:
                print("无效选项，请重新选择")
    
    def _interactive_single_file(self):
        """交互式单个文件处理"""
        print("\n" + "-"*40)
        print("单个文件处理")
        print("-"*40)
        
        # 获取输入文件
        input_file = input("请输入HTML文件路径: ").strip()
        
        if not os.path.exists(input_file):
            print(f"文件不存在: {input_file}")
            return
        
        # 选择输出格式
        print("\n请选择输出格式:")
        print("1. 优化格式 (推荐)")
        print("2. 简单格式")
        
        format_choice = input("请输入选项 (1-2, 默认为1): ").strip()
        format_type = 'simple' if format_choice == '2' else 'optimized'
        
        # 选择输出文件
        output_file = input(f"请输入输出文件路径 (回车使用默认): ").strip()
        if not output_file:
            output_file = None
        
        # 执行解析
        print(f"\n开始解析文件: {input_file}")
        
        success = self.parse_single_file(input_file, output_file, format_type)
        
        if success:
            print("解析完成！")
        else:
            print("解析失败，请检查日志获取详细信息")
    
    def _interactive_batch(self):
        """交互式批量处理"""
        print("\n" + "-"*40)
        print("批量文件处理")
        print("-"*40)
        
        # 获取输入目录
        input_dir = input("请输入HTML文件目录路径 (回车使用配置): ").strip()
        if not input_dir:
            input_dir = None
        
        # 获取输出目录
        output_dir = input("请输入输出目录路径 (回车使用配置): ").strip()
        if not output_dir:
            output_dir = None
        
        # 增量处理
        incremental = input("是否增量处理? (y/N): ").strip().lower() == 'y'
        
        # 详细模式
        verbose = input("是否显示详细信息? (y/N): ").strip().lower() == 'y'
        
        # 执行批量处理
        print(f"\n开始批量处理...")
        
        success = self.batch_process(input_dir, output_dir, incremental, verbose)
        
        if success:
            print("批量处理完成！")
        else:
            print("批量处理失败，请检查日志获取详细信息")
    
    def _show_config(self):
        """显示当前配置"""
        print("\n" + "-"*40)
        print("当前配置")
        print("-"*40)
        
        # 显示路径配置
        paths = self.config.get('paths', {})
        print(f"输入目录: {paths.get('input_dir')}")
        print(f"输出目录: {paths.get('output_dir')}")
        print(f"失败目录: {paths.get('failed_dir')}")
        
        # 显示输出配置
        output = self.config.get('output', {})
        print(f"\n输出格式: {output.get('format')}")
        print(f"标题格式: {output.get('title_format')}")
        
        # 显示批量处理配置
        batch = self.config.get('batch', {})
        print(f"\n批量处理:")
        print(f"  覆盖已存在: {batch.get('overwrite_existing')}")
        print(f"  错误时停止: {batch.get('stop_on_error')}")
        
        print("-"*40)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='DeepSeek HTML解析器 - 将DeepSeek对话HTML转换为优化Markdown格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 解析单个文件
  python main.py parse conversation.html --output optimized.md
  
  # 批量处理目录
  python main.py batch ./html_conversations/ --output-dir ./knowledge_base/
  
  # 增量处理
  python main.py batch ./html_conversations/ --incremental
  
  # 交互模式
  python main.py interactive
  
  # 显示帮助
  python main.py --help
        """
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # parse命令
    parse_parser = subparsers.add_parser('parse', help='解析单个HTML文件')
    parse_parser.add_argument('input_file', help='输入HTML文件路径')
    parse_parser.add_argument('--output', '-o', help='输出Markdown文件路径')
    parse_parser.add_argument('--format', '-f', choices=['optimized', 'simple'], 
                             default='optimized', help='输出格式 (默认: optimized)')
    parse_parser.add_argument('--config', '-c', default='config.yaml', 
                             help='配置文件路径 (默认: config.yaml)')
    
    # batch命令
    batch_parser = subparsers.add_parser('batch', help='批量处理HTML文件')
    batch_parser.add_argument('input_dir', help='输入目录路径')
    batch_parser.add_argument('--output-dir', '-o', help='输出目录路径')
    batch_parser.add_argument('--incremental', '-i', action='store_true', 
                             help='增量处理模式')
    batch_parser.add_argument('--verbose', '-v', action='store_true', 
                             help='详细模式')
    batch_parser.add_argument('--config', '-c', default='config.yaml', 
                             help='配置文件路径 (默认: config.yaml)')
    
    # interactive命令
    interactive_parser = subparsers.add_parser('interactive', help='交互模式')
    interactive_parser.add_argument('--config', '-c', default='config.yaml', 
                                   help='配置文件路径 (默认: config.yaml)')
    
    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    # 解析参数
    args = parser.parse_args()
    
    try:
        # 创建CLI实例
        cli = DeepSeekParserCLI(args.config if hasattr(args, 'config') else 'config.yaml')
        
        # 执行命令
        if args.command == 'parse':
            success = cli.parse_single_file(
                args.input_file, 
                args.output, 
                args.format
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'batch':
            success = cli.batch_process(
                args.input_dir,
                args.output_dir,
                args.incremental,
                args.verbose
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'interactive':
            cli.interactive_mode()
            
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()