# Omniframe Server

> 🤖 智能文件协同服务器 - 人类主导方向，AI实现逻辑

## 🎯 简介

Omniframe Server 是一个智能文件协同服务器，它允许您使用自然语言命令来管理本地文件系统。基于"人类主导方向，AI实现逻辑"的协作理念，它将传统的文件操作转化为智能、语义化的交互体验。

## ✨ 核心特性

### 🧠 智能意图理解
- **自然语言命令**：使用自然语言管理文件，如"查找所有PDF文档"、"打包上周修改的文件"
- **意图解析引擎**：智能解析用户意图，转化为具体的文件操作
- **上下文感知**：记住您的操作历史和工作模式

### 🛡️ 安全与规则
- **宪法规则引擎**：所有操作必须符合预设的宪法规则
- **安全沙盒**：操作限制在工作空间内，保护系统文件
- **操作确认**：高风险操作需要明确确认

### 📁 文件管理
- **智能索引**：自动创建和维护文件索引
- **高级搜索**：按名称、内容、类型、时间等多维度搜索
- **批量操作**：支持批量打包、移动、复制等操作
- **文件监控**：实时监控文件变化

### 🖥️ 多种访问方式
- **Web界面**：现代化的Web界面，支持自然语言输入
- **命令行工具**：功能强大的CLI，支持脚本化操作
- **REST API**：完整的API接口，支持第三方集成

## 🚀 快速开始

### 系统要求
- Python 3.8+
- Windows 10+ (推荐) 或 Linux/macOS
- 至少 100MB 可用空间

### 安装步骤

1. **克隆或下载项目**
   ```bash
   git clone <项目地址>
   cd omniframe_server
   
  ```
  
  
  omniframe_server/
├── server.py                    # 主启动文件
├── cli.py                      # 命令行接口
├── requirements.txt            # 项目依赖
├── README.md                   # 项目说明
├── .env.example                # 环境变量示例
├── .gitignore                  # Git忽略文件
│
├── core/                       # 核心模块
│   ├── __init__.py
│   ├── intent_parser.py        # 意图解析器
│   ├── file_indexer.py         # 智能索引生成器
│   ├── context_manager.py      # 上下文管理器
│   ├── constitution_engine.py  # 宪法规则引擎
│   └── task_dispatcher.py      # 任务分发器
│
├── services/                   # 服务层
│   ├── __init__.py
│   ├── file_service.py         # 文件操作服务
│   ├── search_service.py       # 搜索服务
│   ├── archive_service.py      # 打包服务
│   ├── monitor_service.py      # 文件监控服务
│   └── ai_suggestion.py        # AI建议服务（预留）
│
├── api/                        # API路由
│   ├── __init__.py
│   ├── commands.py             # 命令处理路由
│   ├── files.py                # 文件操作路由
│   └── websocket.py            # WebSocket路由（预留）
│
├── static/                     # 静态文件
│   ├── index.html              # 前端主页面
│   ├── css/
│   │   └── style.css           # 样式文件
│   └── js/
│       └── app.js              # 前端逻辑
│
├── config/                     # 配置目录
│   ├── __init__.py
│   ├── settings.py             # 配置管理
│   └── constitution.yaml       # 宪法规则
│
├── data/                       # 数据存储
│   ├── __init__.py
│   ├── file_index.yaml         # 生成的索引文件
│   └── context_cache.json      # 上下文缓存
│
└── utils/                      # 工具函数
    ├── __init__.py
    ├── path_utils.py           # 路径处理工具
    ├── logger.py               # 日志配置
    └── validation.py           # 输入验证
	
	
