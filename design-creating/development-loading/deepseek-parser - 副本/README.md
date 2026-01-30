# DeepSeek HTML 解析器

专门用于解析DeepSeek对话HTML并将其转换为优化Markdown格式的工具。

## 功能特性

- ✅ 专门针对DeepSeek对话HTML结构优化
- ✅ 支持批量处理多个HTML文件
- ✅ 生成符合标准格式的Markdown文档
- ✅ 智能识别技术对话并过滤无效内容
- ✅ 保留代码块、表格、列表等富文本格式
- ✅ 用户问题自动折叠，提升阅读体验
- ✅ 详细的处理日志和错误报告

## 安装依赖

```
bash
pip install -r requirements.txt
```


# DeepSeek HTML解析器 - 使用说明

## 项目概述

这是一个专门用于解析DeepSeek对话HTML并将其转换为优化Markdown格式的工具。转换后的文档格式清晰，适合作为知识库保存。

## 快速开始

### 1. 环境设置

```bash
# 1. 克隆或下载项目
# 2. 创建虚拟环境（推荐）
python -m venv venv

# Windows激活
venv\Scripts\activate

# Linux/Mac激活
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 设置项目目录
python setup_project.py


# 解析单个HTML文件
python main.py parse example_conversation.html --output output.md

# 使用简单格式
python main.py parse example_conversation.html --format simple

# 处理目录下的所有HTML文件
python main.py batch ./html_conversations/ --output-dir ./knowledge_base/

# 增量处理（只处理新文件）
python main.py batch ./html_conversations/ --incremental

# 详细模式
python main.py batch ./html_conversations/ --verbose


```
