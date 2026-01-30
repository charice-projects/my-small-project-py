#!/bin/bash

# 定义根目录
ROOT_DIR="deepseek_knowledge_system"

echo "正在创建目录结构..."

# 创建主目录
mkdir -p "$ROOT_DIR"

# 创建根目录文件
touch "$ROOT_DIR/pyproject.toml"
touch "$ROOT_DIR/README.md"
touch "$ROOT_DIR/requirements.txt"

# 创建 config 目录和文件
mkdir -p "$ROOT_DIR/config"
touch "$ROOT_DIR/config/base.yaml"
touch "$ROOT_DIR/config/parsers.yaml"
touch "$ROOT_DIR/config/formatters.yaml"

# 创建 src 目录结构
mkdir -p "$ROOT_DIR/src/deepseek_knowledge"
touch "$ROOT_DIR/src/deepseek_knowledge/__init__.py"
touch "$ROOT_DIR/src/deepseek_knowledge/cli.py"

# 创建 phase1_share_parser 目录和文件
mkdir -p "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/__init__.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/interfaces.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/models.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/exceptions.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/main.py"

# 创建 readers 目录和文件
mkdir -p "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/readers"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/readers/__init__.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/readers/share_link_reader.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/readers/http_client.py"

# 创建 parsers 目录和文件
mkdir -p "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/parsers"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/parsers/__init__.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/parsers/html_parser.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/parsers/dom_extractor.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/parsers/content_detector.py"

# 创建 builders 目录和文件
mkdir -p "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/builders"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/builders/__init__.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/builders/conversation_builder.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/builders/metadata_extractor.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/builders/marker_injector.py"

# 创建 formatters 目录和文件
mkdir -p "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/formatters"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/formatters/__init__.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/formatters/markdown_formatter.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/formatters/marker_formatter.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/formatters/html_converter.py"

# 创建 writers 目录和文件
mkdir -p "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/writers"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/writers/__init__.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/writers/file_writer.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/writers/naming_strategy.py"

# 创建 utils 目录和文件
mkdir -p "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/utils"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/utils/__init__.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/utils/id_generator.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/utils/logger.py"
touch "$ROOT_DIR/src/deepseek_knowledge/phase1_share_parser/utils/validator.py"

# 创建 tests 目录和文件
mkdir -p "$ROOT_DIR/tests"
touch "$ROOT_DIR/tests/__init__.py"
touch "$ROOT_DIR/tests/test_share_link_reader.py"
touch "$ROOT_DIR/tests/test_html_parser.py"

# 创建 fixtures 目录和文件
mkdir -p "$ROOT_DIR/tests/fixtures"
touch "$ROOT_DIR/tests/fixtures/sample_share_page.html"

# 创建 knowledge_base 目录结构
mkdir -p "$ROOT_DIR/knowledge_base/conversations"
mkdir -p "$ROOT_DIR/knowledge_base/projects"

echo "目录结构创建完成！"
echo ""
echo "创建了以下结构："
echo "deepseek_knowledge_system/"
echo "├── pyproject.toml"
echo "├── README.md"
echo "├── requirements.txt"
echo "├── config/"
echo "│   ├── base.yaml"
echo "│   ├── parsers.yaml"
echo "│   └── formatters.yaml"
echo "├── src/"
echo "│   └── deepseek_knowledge/"
echo "│       ├── __init__.py"
echo "│       ├── cli.py"
echo "│       └── phase1_share_parser/"
echo "│           ├── __init__.py"
echo "│           ├── interfaces.py"
echo "│           ├── models.py"
echo "│           ├── exceptions.py"
echo "│           ├── main.py"
echo "│           ├── readers/"
echo "│           │   ├── __init__.py"
echo "│           │   ├── share_link_reader.py"
echo "│           │   └── http_client.py"
echo "│           ├── parsers/"
echo "│           │   ├── __init__.py"
echo "│           │   ├── html_parser.py"
echo "│           │   ├── dom_extractor.py"
echo "│           │   └── content_detector.py"
echo "│           ├── builders/"
echo "│           │   ├── __init__.py"
echo "│           │   ├── conversation_builder.py"
echo "│           │   ├── metadata_extractor.py"
echo "│           │   └── marker_injector.py"
echo "│           ├── formatters/"
echo "│           │   ├── __init__.py"
echo "│           │   ├── markdown_formatter.py"
echo "│           │   ├── marker_formatter.py"
echo "│           │   └── html_converter.py"
echo "│           ├── writers/"
echo "│           │   ├── __init__.py"
echo "│           │   ├── file_writer.py"
echo "│           │   └── naming_strategy.py"
echo "│           └── utils/"
echo "│               ├── __init__.py"
echo "│               ├── id_generator.py"
echo "│               ├── logger.py"
echo "│               └── validator.py"
echo "├── tests/"
echo "│   ├── __init__.py"
echo "│   ├── test_share_link_reader.py"
echo "│   ├── test_html_parser.py"
echo "│   └── fixtures/"
echo "│       └── sample_share_page.html"
echo "└── knowledge_base/"
echo "    ├── conversations/"
echo "    └── projects/"