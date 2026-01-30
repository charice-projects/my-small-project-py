"""
setup_project.py
项目设置脚本 - 创建必要的目录和示例文件
"""
import os
import sys
from pathlib import Path


def setup_project():
    """设置项目目录结构"""
    print("开始设置DeepSeek HTML解析器项目...")
    
    # 项目根目录
    root_dir = Path(__file__).parent
    
    # 需要创建的目录
    directories = [
        'html_conversations',
        'knowledge_base',
        'failed',
        'test_data',
        'logs'
    ]
    
    # 创建目录
    for dir_name in directories:
        dir_path = root_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"创建目录: {dir_path}")
    
    # 复制示例HTML文件到输入目录
    example_file = root_dir / 'example_conversation.html'
    if example_file.exists():
        import shutil
        target_file = root_dir / 'html_conversations' / 'example_conversation.html'
        shutil.copy2(example_file, target_file)
        print(f"复制示例文件到: {target_file}")
    
    # 创建虚拟环境（可选）
    print("\n建议设置虚拟环境:")
    print("  python -m venv venv")
    print("  # Windows:")
    print("  venv\\Scripts\\activate")
    print("  # Linux/Mac:")
    print("  source venv/bin/activate")
    
    # 安装依赖
    print("\n安装依赖:")
    print("  pip install -r requirements.txt")
    
    # 测试项目
    print("\n测试项目:")
    print("  python -m pytest tests/")
    print("  python main.py --help")
    
    print("\n项目设置完成！")
    print("\n使用示例:")
    print("  1. 将DeepSeek对话HTML文件放入 html_conversations/ 目录")
    print("  2. 运行批量处理: python main.py batch html_conversations/")
    print("  3. 查看生成的知识库文件: knowledge_base/")


if __name__ == '__main__':
    setup_project()