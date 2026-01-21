#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConversationArchitect CLI 简易启动器
"""

import sys
import os
from pathlib import Path

def main():
    """主函数"""
    print("对话记录处理工具 - 命令行版")
    print("-" * 40)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要 Python 3.7 或更高版本")
        print(f"当前版本: {sys.version}")
        return
    
    # 检查主程序文件
    if not Path("conversation_architect_cli.py").exists():
        print("❌ 未找到主程序文件 conversation_architect_cli.py")
        print("请确保主程序文件与启动器在同一目录")
        return
    
    # 获取用户输入
    print("\n请选择操作方式:")
    print("1. 使用命令行参数")
    print("2. 交互式输入文件路径")
    print("3. 查看帮助")
    
    choice = input("\n请输入选择 (1-3): ").strip()
    
    if choice == "1":
        # 使用命令行参数
        print("\n使用方式:")
        print("  python conversation_architect_cli.py 输入文件.md [选项]")
        print("\n选项:")
        print("  -o, --output    输出文件路径")
        print("  -s, --suffix    输出文件后缀（默认: _organized）")
        print("  --no-toc        不生成目录")
        print("  --no-title      不添加总标题")
        print("  --no-summary    不生成总结报告")
        print("\n示例:")
        print("  python conversation_architect_cli.py conversation.md")
        print("  python conversation_architect_cli.py conversation.md -o clean.md")
        print("  python conversation_architect_cli.py conversation.md --no-toc")
        
    elif choice == "2":
        # 交互式输入
        print("\n" + "="*40)
        print("交互式文件处理")
        print("="*40)
        
        # 输入文件路径
        input_file = input("请输入对话文件路径: ").strip()
        
        if not input_file:
            print("❌ 未输入文件路径")
            return
        
        if not Path(input_file).exists():
            print(f"❌ 文件不存在: {input_file}")
            return
        
        # 输出文件路径
        output_file = input("输出文件路径（留空使用默认）: ").strip()
        
        # 其他选项
        print("\n可选设置（留空使用默认）:")
        suffix = input("文件后缀（默认: _organized）: ").strip() or "_organized"
        
        generate_toc = input("生成目录？(y/n, 默认: y): ").strip().lower()
        no_toc = generate_toc == 'n'
        
        generate_title = input("添加总标题？(y/n, 默认: y): ").strip().lower()
        no_title = generate_title == 'n'
        
        # 构建命令
        cmd = f'python conversation_architect_cli.py "{input_file}"'
        
        if output_file:
            cmd += f' -o "{output_file}"'
        elif suffix != "_organized":
            cmd += f' -s "{suffix}"'
        
        if no_toc:
            cmd += ' --no-toc'
        
        if no_title:
            cmd += ' --no-title'
        
        print(f"\n执行命令: {cmd}")
        print("\n开始处理...")
        print("-" * 40)
        
        # 执行命令
        os.system(cmd)
        
    elif choice == "3":
        # 显示帮助
        print("\n" + "="*40)
        print("帮助文档")
        print("="*40)
        
        print("\n功能:")
        print("  1. 智能处理嵌套对话记录")
        print("  2. 修复标题层级（包括单个#开头）")
        print("  3. 自动生成/更新目录")
        print("  4. 添加文档总标题")
        print("  5. 智能合并已优化和未优化内容")
        print("  6. 生成详细分析报告")
        
        print("\n支持格式:")
        print("  - 原始对话: ## 对话-V001 标题")
        print("  - 已优化内容: 包含目录和结构化格式")
        print("  - 混合内容: 部分已优化，部分未优化")
        
        print("\n输出文件:")
        print("  - 输入文件_organized.md      结构化文档")
        print("  - 输入文件_organized_summary.md 分析报告")
        print("  - 输入文件_organized_statistics.json 统计数据")
        
        print("\n建议:")
        print("  1. 首次使用时先处理小文件测试")
        print("  2. 定期备份原始对话文件")
        print("  3. 使用默认设置处理大多数情况")
        
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    main()