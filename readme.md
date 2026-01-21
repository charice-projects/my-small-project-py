```markdown
# Python 小工具集 (Python Small Tools Collection)

这是一个个人 Python 工具集，用于解决日常工作和学习中遇到的各种小问题。包含数据处理、文件转换、实用脚本等功能。

## 📋 项目简介

本项目收集了我日常使用的 Python 脚本工具，主要涵盖以下领域：
- Excel 文件处理与转换
- 数据清洗与去重
- 实用工具脚本
- GUI 界面工具

## 🚀 快速开始

### 环境要求
- Python 3.6+
- 依赖包：pandas, openpyxl, tkinter 等

### 安装使用
```bash
# 克隆项目
git clone https://github.com/yourusername/my-small-project-py.git

# 进入项目目录
cd my-small-project-py

# 安装依赖（如有 requirements.txt）
pip install -r requirements.txt
```

## 📁 工具列表

### 1. Excel 处理工具
- **Excel_To_VCF.py** - 将 Excel 联系人导出为 VCF 格式
- **Excel多表格合并-v003.py** - 合并多个 Excel 工作表
- **GUI-合并Excel-v002.py** - 带界面的 Excel 合并工具

### 2. 数据处理工具
- **数据去重 - 路径cmd中输入 - V004.py** - 命令行数据去重工具
- **Excel多表格合并-v003.py** - 多表格数据合并

### 3. 实用工具
- **号码归属地 - 数据库不全.py** - 手机号码归属地查询

## 🔧 跨平台协作设置

### 换行符问题处理
由于 Windows 和 Unix/Linux 系统的换行符不同，为确保跨平台协作一致：

#### 1. 创建 `.gitattributes` 文件
在项目根目录创建 `.gitattributes`：
```
# 自动检测文本文件
* text=auto

# Python 文件统一使用 LF 换行符
*.py text eol=lf

# 文档文件
*.md text eol=lf
*.txt text eol=lf

# Windows 特有文件
*.bat text eol=crlf
*.ps1 text eol=crlf

# 二进制文件不处理
*.png binary
*.jpg binary
*.pdf binary
```

#### 2. 开发者本地配置
根据你的操作系统执行相应命令：

```bash
# Windows 开发者
git config --global core.autocrlf true

# Mac/Linux 开发者
git config --global core.autocrlf input

# 所有开发者（安全检测）
git config --global core.safecrlf warn
```

#### 3. 验证配置
```bash
# 检查文件状态
git ls-files --eol

# 添加所有文件
git add .

# 提交更改
git commit -m "设置跨平台换行符配置"
```

## 📝 使用说明

### Excel 合并工具
```bash
# 命令行使用
python "python-tools/Excel多表格合并-v003.py"

# GUI 版本
python "python-tools/GUI-合并Excel-v002.py"
```

### 数据去重工具
```bash
# 在命令行中指定文件路径
python "python-tools/数据去重 - 路径cmd中输入 - V004.py"
```

### Excel 转 VCF
```bash
# 转换 Excel 通讯录为 VCF 格式
python "python-tools/Excel_To_VCF.py"
```

### 号码归属地查询
```bash
# 查询手机号码归属地
python "python-tools/号码归属地 - 数据库不全.py"
```

## 🛠️ 开发指南

### 项目结构
```
my-small-project-py/
├── python-tools/          # Python 工具脚本目录
│   ├── Excel_To_VCF.py
│   ├── Excel多表格合并-v003.py
│   ├── GUI-合并Excel-v002.py
│   ├── 号码归属地 - 数据库不全.py
│   └── 数据去重 - 路径cmd中输入 - V004.py
├── .gitattributes         # Git 换行符配置
├── README.md             # 项目说明文档
├── LICENSE               # 许可证文件
└── requirements.txt      # Python 依赖包列表（可选）
```

### 添加新工具
1. 在 `python-tools/` 目录下创建新 Python 文件
2. 确保代码兼容 Python 3.6+
3. 添加必要的注释和文档字符串
4. 更新本 README 中的工具列表

### 代码规范
- 使用英文变量名和注释
- 添加必要的错误处理
- 提供命令行参数或 GUI 界面
- 保持代码简洁易读

### 命名约定
- 功能描述 + 版本号（如：`数据去重-v004.py`）
- 对于中文工具名，确保在代码内使用英文字符串
- 版本号格式：`v001`, `v002` 等

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request 来改进这些工具！

### 提交更改
1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码提交规范
```bash
# 添加所有更改
git add .

# 提交更改
git commit -m "feat: 添加新功能"
# 或
git commit -m "fix: 修复某个问题"
# 或
git commit -m "docs: 更新文档"
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 邮件：your.email@example.com

## 🔄 更新日志

### v1.0.0 (2024-01)
- 初始版本发布
- 包含 5 个 Python 工具脚本
- 添加跨平台换行符配置
- 完善项目文档

---

*最后更新：2024年1月* 
```

这个 README.md 文件包含了：
1. 完整的项目介绍
2. 详细的使用说明
3. 跨平台配置指南
4. 开发规范
5. 项目结构说明
6. 贡献指南
7. 许可证信息

你可以将这个内容保存到你的 `readme.md` 文件中，然后添加到 Git：

```bash
# 保存 readme.md 后
git add readme.md
git commit -m "docs: 添加完整的项目README文档"
git push origin main
```