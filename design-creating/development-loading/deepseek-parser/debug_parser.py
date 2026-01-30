"""
debug_parser.py
调试解析器的详细错误
"""
import os
import sys
import traceback

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.file_ops import FileOperations
from utils.logger import get_logger
from core.deepseek_parser import DeepSeekParser
from core.conversation_builder import ConversationBuilder
from core.content_formatter import ContentFormatter
from outputs.optimized_markdown import OptimizedMarkdownWriter


def debug_single_file(file_path):
    """调试单个文件解析过程"""
    print(f"\n{'='*60}")
    print(f"调试文件: {file_path}")
    print(f"{'='*60}")
    
    # 加载配置
    config = FileOperations.load_config('config.yaml')
    
    # 设置详细日志
    config['logging']['level'] = 'DEBUG'
    logger = get_logger(config)
    
    try:
        # 步骤1: 读取文件
        print("\n1. 读取文件...")
        html_content = FileOperations.read_file(file_path)
        print(f"   文件大小: {len(html_content)} 字节")
        
        # 步骤2: 解析HTML
        print("\n2. 解析HTML...")
        parser = DeepSeekParser(config)
        parsed_data = parser.parse_html(html_content)
        print(f"   解析到的轮次: {len(parsed_data.get('rounds', []))}")
        
        # 打印解析数据（部分）
        if parsed_data.get('rounds'):
            print(f"   第一个轮次的结构:")
            round_data = parsed_data['rounds'][0]
            print(f"     - user类型: {type(round_data.get('user'))}")
            print(f"     - user content类型: {type(round_data.get('user', {}).get('content'))}")
            print(f"     - ai类型: {type(round_data.get('ai'))}")
            print(f"     - ai content类型: {type(round_data.get('ai', {}).get('content'))}")
        
        # 步骤3: 构建对话
        print("\n3. 构建对话...")
        builder = ConversationBuilder(config)
        conversation = builder.build(parsed_data)
        print(f"   对话ID: {conversation.get('dialog_id')}")
        print(f"   有效轮次: {len(conversation.get('rounds', []))}")
        
        # 检查对话数据
        if conversation.get('rounds'):
            round_data = conversation['rounds'][0]
            print(f"   第一个轮次的数据类型检查:")
            print(f"     - round_data类型: {type(round_data)}")
            print(f"     - user类型: {type(round_data.get('user'))}")
            print(f"     - user content类型: {type(round_data.get('user', {}).get('content'))}")
            print(f"     - ai类型: {type(round_data.get('ai'))}")
            print(f"     - ai content类型: {type(round_data.get('ai', {}).get('content'))}")
            
            # 检查内容是否为元组
            user_content = round_data.get('user', {}).get('content')
            ai_content = round_data.get('ai', {}).get('content')
            
            if isinstance(user_content, tuple):
                print(f"   ❌ user content是元组: {user_content}")
            if isinstance(ai_content, tuple):
                print(f"   ❌ ai content是元组: {ai_content}")
        
        # 步骤4: 格式化内容
        print("\n4. 格式化内容...")
        formatter = ContentFormatter(config)
        
        if conversation.get('rounds'):
            round_data = conversation['rounds'][0]
            
            # 尝试格式化用户内容
            print("   尝试格式化用户内容...")
            user_content = round_data['user']['content']
            print(f"     user content类型: {type(user_content)}")
            print(f"     user content值前50字符: {str(user_content)[:50] if user_content else '空'}")
            
            try:
                formatted_user = formatter.format_content(user_content, 'user')
                print(f"     ✅ 用户内容格式化成功，长度: {len(formatted_user)}")
            except Exception as e:
                print(f"     ❌ 用户内容格式化失败: {e}")
                print(f"     错误详情: {traceback.format_exc()}")
            
            # 尝试格式化AI内容
            print("   尝试格式化AI内容...")
            ai_content = round_data['ai']['content']
            print(f"     ai content类型: {type(ai_content)}")
            print(f"     ai content值前50字符: {str(ai_content)[:50] if ai_content else '空'}")
            
            try:
                formatted_ai = formatter.format_content(ai_content, 'ai')
                print(f"     ✅ AI内容格式化成功，长度: {len(formatted_ai)}")
            except Exception as e:
                print(f"     ❌ AI内容格式化失败: {e}")
                print(f"     错误详情: {traceback.format_exc()}")
        
        # 步骤5: 生成Markdown
        print("\n5. 生成Markdown...")
        writer = OptimizedMarkdownWriter(config)
        
        try:
            output_content = writer.write(conversation)
            print(f"   ✅ Markdown生成成功，长度: {len(output_content)}")
            print(f"   前200字符预览:\n{output_content[:200]}...")
        except Exception as e:
            print(f"   ❌ Markdown生成失败: {e}")
            print(f"   错误详情: {traceback.format_exc()}")
        
        print(f"\n{'='*60}")
        print("调试完成")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ 调试过程中发生错误: {e}")
        print(f"错误详情: {traceback.format_exc()}")
        print(f"{'='*60}")


def main():
    """主函数"""
    # 检查文件路径
    file_path = "./html_conversations/example_conversation.html"
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        
        # 尝试查找文件
        print("尝试在当前目录查找HTML文件...")
        import glob
        html_files = glob.glob("*.html") + glob.glob("html_conversations/*.html")
        
        if html_files:
            print(f"找到HTML文件: {html_files[0]}")
            file_path = html_files[0]
        else:
            print("未找到HTML文件")
            return
    
    debug_single_file(file_path)


if __name__ == '__main__':
    main()