#!/bin/bash

# 定义根目录
ROOT_DIR="deepseek-parser"

echo "正在创建目录结构..."

# 创建主目录
mkdir -p "$ROOT_DIR"

# 创建 core 目录和文件
mkdir -p "$ROOT_DIR/core"
touch "$ROOT_DIR/core/__init__.py"
touch "$ROOT_DIR/core/deepseek_parser.py"
touch "$ROOT_DIR/core/conversation_builder.py"
touch "$ROOT_DIR/core/content_formatter.py"

# 创建 batch 目录和文件
mkdir -p "$ROOT_DIR/batch"
touch "$ROOT_DIR/batch/__init__.py"
touch "$ROOT_DIR/batch/processor.py"

# 创建 outputs 目录和文件
mkdir -p "$ROOT_DIR/outputs"
touch "$ROOT_DIR/outputs/__init__.py"
touch "$ROOT_DIR/outputs/optimized_markdown.py"
touch "$ROOT_DIR/outputs/simple_markdown.py"

# 创建 utils 目录和文件
mkdir -p "$ROOT_DIR/utils"
touch "$ROOT_DIR/utils/__init__.py"
touch "$ROOT_DIR/utils/file_ops.py"
touch "$ROOT_DIR/utils/logger.py"

# 创建 tests 目录和文件
mkdir -p "$ROOT_DIR/tests"
touch "$ROOT_DIR/tests/__init__.py"
touch "$ROOT_DIR/tests/test_parser.py"
touch "$ROOT_DIR/tests/test_formatter.py"

# 创建根目录文件
touch "$ROOT_DIR/config.yaml"
touch "$ROOT_DIR/requirements.txt"
touch "$ROOT_DIR/main.py"
touch "$ROOT_DIR/README.md"
touch "$ROOT_DIR/.gitignore"

echo "目录结构创建完成！"
echo ""
echo "创建了以下结构："
echo "deepseek-parser/"
echo "├── core/"
echo "│   ├── __init__.py"
echo "│   ├── deepseek_parser.py"
echo "│   ├── conversation_builder.py"
echo "│   └── content_formatter.py"
echo "├── batch/"
echo "│   ├── __init__.py"
echo "│   └── processor.py"
echo "├── outputs/"
echo "│   ├── __init__.py"
echo "│   ├── optimized_markdown.py"
echo "│   └── simple_markdown.py"
echo "├── utils/"
echo "│   ├── __init__.py"
echo "│   ├── file_ops.py"
echo "│   └── logger.py"
echo "├── tests/"
echo "│   ├── __init__.py"
echo "│   ├── test_parser.py"
echo "│   └── test_formatter.py"
echo "├── config.yaml"
echo "├── requirements.txt"
echo "├── main.py"
echo "├── README.md"
echo "└── .gitignore"