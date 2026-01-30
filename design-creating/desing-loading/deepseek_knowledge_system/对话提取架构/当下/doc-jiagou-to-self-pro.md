# 🏗️ **DeepSeek对话知识库系统 - 优化架构设计**

基于你的要求，我重新设计了一个**标记化、可扩展、定义清晰**的完整架构。重点在于：
1. 增加精准的标记位，方便后续处理
2. 清晰定义所有接口和数据结构
3. 分阶段渐进实施

## 📋 **全局定义与约定**

### **1. 数据结构定义**

```python
# 类型定义（伪代码）
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ContentFormat(Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    PLAIN_TEXT = "plain_text"

class ConversationMetadata:
    """对话元数据"""
    conversation_id: str            # 唯一ID
    source_type: str               # 来源：share_link, mhtml, live_monitor
    source_url: str                # 原始URL
    title: str                     # 对话标题
    created_at: datetime           # 创建时间
    last_modified: datetime        # 最后修改时间
    tags: List[str]                # 标签
    project_name: Optional[str]    # 所属项目
    importance_score: float        # 重要性评分(0-1)
    
class Message:
    """消息结构"""
    message_id: str                # 消息唯一ID
    type: MessageType              # 消息类型
    content: str                   # 消息内容
    content_format: ContentFormat  # 内容格式
    timestamp: Optional[datetime]  # 时间戳
    parent_id: Optional[str]       # 父消息ID（用于多轮）
    metadata: Dict[str, Any]       # 扩展元数据
    
class ConversationRound:
    """对话轮次结构"""
    round_id: str                  # 轮次ID，格式：{conversation_id}-{sequence}
    user_message: Message          # 用户消息
    assistant_message: Message     # AI回复
    round_metadata: Dict[str, Any] # 轮次元数据
    
class ParsedConversation:
    """解析后的对话结构"""
    metadata: ConversationMetadata
    rounds: List[ConversationRound]
    original_source: Optional[str]  # 原始HTML/MHTML内容（用于调试）
```

### **2. 标记位系统设计**

```python
# 标记位定义
class Markers:
    # 文件级标记
    FILE_START = "<!-- DEEPSEEK_CONVERSATION_START -->"
    FILE_END = "<!-- DEEPSEEK_CONVERSATION_END -->"
    FILE_METADATA = "<!-- METADATA: {metadata_json} -->"
    
    # 轮次级标记
    ROUND_START = "<!-- ROUND_START: {round_id} -->"
    ROUND_END = "<!-- ROUND_END: {round_id} -->"
    
    # 消息级标记
    MESSAGE_START = "<!-- {message_type}_START: {message_id} -->"
    MESSAGE_END = "<!-- {message_type}_END: {message_id} -->"
    
    # 内容类型标记
    HAS_CODE = "<!-- CONTENT_TYPE: HAS_CODE -->"
    HAS_TABLE = "<!-- CONTENT_TYPE: HAS_TABLE -->"
    HAS_DIAGRAM = "<!-- CONTENT_TYPE: HAS_DIAGRAM -->"
    
    # 语义标记
    TOPIC = "<!-- TOPIC: {topic_name} -->"
    CONCEPT = "<!-- CONCEPT: {concept_name} -->"
    DECISION = "<!-- DECISION: {decision_text} -->"
    
    # 处理标记
    PROCESSED_BY = "<!-- PROCESSED_BY: {processor_name} v{version} -->"
    PROCESSING_DATE = "<!-- PROCESSING_DATE: {timestamp} -->"
```

### **3. 输出格式约定**

```markdown
# 最终的Markdown文件结构示例
<!-- DEEPSEEK_CONVERSATION_START -->
<!-- METADATA: {"conversation_id": "conv_001", "source": "share_link", ...} -->
<!-- PROCESSED_BY: DeepSeekParser v1.0 -->
<!-- PROCESSING_DATE: 2024-01-25T10:30:00Z -->

# [conv_001-1] 关键词1 关键词2 关键词3

<!-- ROUND_START: conv_001-1 -->
<!-- TOPIC: HTML解析 -->
<!-- CONCEPT: BeautifulSoup解析 -->

<!-- USER_START: msg_001 -->
<details class="user-query" data-collapsed="true">
<summary>用户提问</summary>

这里是我要解决的问题，具体是...

</details>
<!-- USER_END: msg_001 -->

<!-- ASSISTANT_START: msg_002 -->
<!-- CONTENT_TYPE: HAS_CODE -->
<!-- CONTENT_TYPE: HAS_TABLE -->

## AI回答

### 解决方案概述

这里是我的回答内容...

```python
# 示例代码
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
```

### 详细步骤

1. 第一步...
2. 第二步...

<!-- ASSISTANT_END: msg_002 -->
<!-- ROUND_END: conv_001-1 -->

# [conv_001-2] 后续问题 技术细节

<!-- ROUND_START: conv_001-2 -->
...
<!-- ROUND_END: conv_001-2 -->

<!-- DEEPSEEK_CONVERSATION_END -->
```

## 🏗️ **系统架构设计**

### **整体架构图**
```
┌─────────────────────────────────────────────────────────┐
│                   用户界面层                            │
│  CLI / GUI / 浏览器扩展                                 │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                   控制层                                │
│  CommandHandler / APIServer / EventRouter              │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                   业务逻辑层                            │
│  ConversationManager / ParserOrchestrator              │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                   核心处理层                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                │
│  │ 解析器  │  │ 构建器  │  │ 格式化器│                │
│  │ Parser  │  │ Builder │  │Formatter│                │
│  └─────────┘  └─────────┘  └─────────┘                │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                   数据访问层                            │
│  SourceReader / StorageWriter / CacheManager           │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                   存储层                                │
│  文件系统 / 数据库 / 云存储                             │
└─────────────────────────────────────────────────────────┘
```

## 🚀 **阶段1：分享链接解析器（V1.0）**

### **模块设计**
```
phase1_share_parser/
├── interfaces.py          # 接口定义
├── models.py             # 数据模型
├── readers/
│   ├── share_link_reader.py
│   └── http_client.py
├── parsers/
│   ├── html_parser.py
│   ├── dom_extractor.py
│   └── content_detector.py
├── builders/
│   ├── conversation_builder.py
│   ├── metadata_extractor.py
│   └── marker_injector.py
├── formatters/
│   ├── markdown_formatter.py
│   ├── marker_formatter.py
│   └── html_converter.py
├── writers/
│   ├── file_writer.py
│   └── naming_strategy.py
├── utils/
│   ├── id_generator.py
│   ├── logger.py
│   └── validator.py
└── main.py
```

### **核心接口定义**

```python
# interfaces.py

class ISourceReader:
    """源数据读取器接口"""
    def read(self, source: str) -> str:
        """从源读取原始数据"""
        pass
        
    def validate(self, source: str) -> bool:
        """验证源是否可读"""
        pass

class IParser:
    """解析器接口"""
    def parse(self, raw_data: str) -> Dict[str, Any]:
        """解析原始数据为中间格式"""
        pass
        
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式"""
        pass

class IConversationBuilder:
    """对话构建器接口"""
    def build(self, parsed_data: Dict[str, Any]) -> ParsedConversation:
        """构建结构化对话"""
        pass
        
    def generate_round_ids(self, conversation_id: str, count: int) -> List[str]:
        """生成轮次ID"""
        pass

class IMarkerInjector:
    """标记注入器接口"""
    def inject_markers(self, conversation: ParsedConversation) -> ParsedConversation:
        """注入标记位"""
        pass
        
    def get_marker_schema(self) -> Dict[str, str]:
        """获取标记模式定义"""
        pass

class IFormatter:
    """格式化器接口"""
    def format(self, conversation: ParsedConversation) -> str:
        """格式化为目标格式"""
        pass
        
    def get_supported_formats(self) -> List[str]:
        """获取支持的输出格式"""
        pass

class IWriter:
    """写入器接口"""
    def write(self, content: str, path: str) -> bool:
        """写入内容"""
        pass
        
    def generate_filename(self, metadata: ConversationMetadata) -> str:
        """生成文件名"""
        pass
```

### **处理流程**
```
1. 读取阶段
   ↓
2. 解析阶段（HTML → 中间结构）
   ↓
3. 构建阶段（中间结构 → ParsedConversation）
   ↓
4. 标记注入（添加所有标记位）
   ↓
5. 格式化阶段（ParsedConversation → Markdown）
   ↓
6. 写入阶段（保存到文件系统）
```

### **关键数据结构流转**
```
原始HTML
    ↓ parse()
中间结构: {
    "title": "xxx",
    "messages": [
        {"type": "user", "content": "..."},
        {"type": "assistant", "content": "..."}
    ]
}
    ↓ build()
ParsedConversation {
    metadata: ConversationMetadata {...},
    rounds: [
        ConversationRound {
            round_id: "conv_001-1",
            user_message: Message {...},
            assistant_message: Message {...}
        }
    ]
}
    ↓ inject_markers()
ParsedConversation（带标记元数据）
    ↓ format()
标记化Markdown字符串
    ↓ write()
最终文件
```

## 🔧 **阶段2：MHTML全量保存器（V2.0）**

### **架构扩展**
```
phase2_mhtml_archiver/
├── core/                    # 继承阶段1的核心
│   ├── interfaces.py       # 扩展接口
│   └── models.py          # 扩展模型
├── capture/
│   ├── browser_controller.py
│   ├── mhtml_capturer.py
│   ├── auto_scroller.py
│   └── resource_collector.py
├── parsers/
│   ├── mhtml_parser.py    # 新增MHTML解析器
│   ├── json_extractor.py  # 从JS中提取JSON数据
│   └── dom_analyzer.py    # DOM结构分析
├── processors/
│   ├── content_validator.py
│   ├── duplicate_detector.py
│   └── quality_scorer.py
├── organizers/
│   ├── project_detector.py
│   ├── timeline_builder.py
│   └── knowledge_organizer.py
└── integration/
    ├── phase1_adapter.py   # 与阶段1的适配器
    └── unified_orchestrator.py
```

### **新增接口定义**

```python
# phase2/interfaces.py

class IBrowserController:
    """浏览器控制器接口"""
    def launch(self, profile_path: Optional[str] = None) -> bool:
        """启动浏览器"""
        pass
        
    def navigate(self, url: str) -> bool:
        """导航到URL"""
        pass
        
    def capture_complete_page(self) -> str:
        """捕获完整页面内容"""
        pass
        
    def save_as_mhtml(self, output_path: str) -> bool:
        """保存为MHTML格式"""
        pass

class IMHTMLParser(IParser):
    """MHTML解析器接口（扩展IParser）"""
    def extract_main_html(self, mhtml_content: str) -> str:
        """从MHTML中提取主HTML"""
        pass
        
    def extract_resources(self, mhtml_content: str) -> Dict[str, bytes]:
        """提取所有资源文件"""
        pass

class IContentValidator:
    """内容验证器接口"""
    def validate_completeness(self, conversation: ParsedConversation) -> ValidationResult:
        """验证对话完整性"""
        pass
        
    def estimate_missing_content(self, conversation: ParsedConversation) -> float:
        """估计缺失内容比例"""
        pass

class IProjectDetector:
    """项目检测器接口"""
    def detect_projects(self, conversations: List[ParsedConversation]) -> Dict[str, List[ParsedConversation]]:
        """检测并分组项目"""
        pass
        
    def generate_project_metadata(self, project_conversations: List[ParsedConversation]) -> ProjectMetadata:
        """生成项目元数据"""
        pass
```

### **MHTML处理流程**
```
1. URL验证与预处理
   ↓
2. 浏览器启动与导航
   ↓
3. 智能滚动加载（确保完整性）
   ↓
4. MHTML捕获与保存
   ↓
5. MHTML解析（提取HTML+资源）
   ↓
6. 结构化解析（复用阶段1解析器）
   ↓
7. 内容验证与完整性检查
   ↓
8. 标记注入与格式化
   ↓
9. 智能组织与存储
```

### **完整性验证算法**
```python
class CompletenessValidator(IContentValidator):
    def validate_completeness(self, conversation: ParsedConversation) -> ValidationResult:
        result = ValidationResult()
        
        # 1. 检查轮次连续性
        for i in range(len(conversation.rounds) - 1):
            current = conversation.rounds[i]
            next_round = conversation.rounds[i + 1]
            
            # 检查时间顺序
            if current.assistant_message.timestamp and next_round.user_message.timestamp:
                time_gap = next_round.user_message.timestamp - current.assistant_message.timestamp
                if time_gap.total_seconds() > 3600:  # 1小时以上间隔
                    result.add_warning(f"轮次 {i} 和 {i+1} 时间间隔异常: {time_gap}")
        
        # 2. 检查内容完整性
        for round in conversation.rounds:
            user_len = len(round.user_message.content.strip())
            assistant_len = len(round.assistant_message.content.strip())
            
            if user_len < 10:
                result.add_warning(f"轮次 {round.round_id} 用户消息过短")
            if assistant_len < 50:
                result.add_warning(f"轮次 {round.round_id} AI回答过短")
        
        # 3. 检查标记完整性
        marker_count = count_markers(conversation)
        expected_markers = calculate_expected_markers(conversation)
        
        if marker_count < expected_markers:
            result.add_error(f"标记不完整: 找到 {marker_count} 个，预期 {expected_markers} 个")
        
        return result
```

## 🎮 **阶段3：实时监听扩展（V3.0）**

### **架构设计**
```
phase3_live_monitor/
├── browser_extension/
│   ├── manifest.json          # 扩展清单
│   ├── content_scripts/
│   │   ├── deepseek_detector.js
│   │   ├── message_capture.js
│   │   └── ui_injector.js
│   ├── background/
│   │   ├── background.js
│   │   └── storage_manager.js
│   ├── popup/
│   │   ├── popup.html
│   │   ├── popup.js
│   │   └── popup.css
│   └── options/
│       ├── options.html
│       └── options.js
├── local_server/
│   ├── server.py
│   ├── api_handlers.py
│   ├── websocket_server.py
│   └── conversation_manager.py
├── shared/
│   ├── protocol.py           # 通信协议定义
│   ├── data_models.py        # 共享数据模型
│   └── constants.py          # 共享常量
└── integration/
    ├── phase2_integration.py
    └── realtime_processor.py
```

### **通信协议定义**

```python
# shared/protocol.py

class MessageType:
    HELLO = "hello"
    NEW_CONVERSATION = "new_conversation"
    NEW_MESSAGE = "new_message"
    CONVERSATION_END = "conversation_end"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    ERROR = "error"

class Message:
    """通信消息"""
    type: str
    version: str = "1.0"
    timestamp: str
    data: Dict[str, Any]
    message_id: str

class ConversationData:
    """实时对话数据"""
    conversation_id: str
    title: str
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    is_complete: bool = False

# WebSocket消息格式
WEBSOCKET_MESSAGE = {
    "type": MessageType.NEW_MESSAGE,
    "version": "1.0",
    "timestamp": "2024-01-25T10:30:00Z",
    "message_id": "msg_123",
    "data": {
        "conversation_id": "conv_001",
        "message": {
            "id": "msg_456",
            "type": "assistant",
            "content": "这里是AI回复...",
            "timestamp": "2024-01-25T10:30:00Z"
        }
    }
}
```

### **扩展-服务端交互流程**
```
浏览器扩展（Content Script） → 后台脚本（Background） → 本地服务器

1. 内容脚本检测到DeepSeek页面
2. 注入消息监听器
3. 捕获新消息，发送到后台脚本
4. 后台脚本通过WebSocket发送到本地服务器
5. 本地服务器实时处理并保存
```

### **实时处理状态机**
```python
class ConversationStateMachine:
    """对话状态管理"""
    
    states = {
        "IDLE": "空闲",
        "MONITORING": "监听中",
        "CAPTURING": "捕获中",
        "PAUSED": "已暂停",
        "COMPLETED": "已完成"
    }
    
    transitions = {
        ("IDLE", "start_monitoring"): "MONITORING",
        ("MONITORING", "first_message"): "CAPTURING",
        ("CAPTURING", "pause"): "PAUSED",
        ("PAUSED", "resume"): "CAPTURING",
        ("CAPTURING", "conversation_end"): "COMPLETED",
        ("COMPLETED", "reset"): "IDLE"
    }
    
    def __init__(self):
        self.current_state = "IDLE"
        self.conversation_id = None
        self.messages = []
        self.state_history = []
```

## 📊 **数据处理流水线**

### **完整处理流水线**
```
输入源
  ↓
[输入适配器] → 统一为 RawInput 格式
  ↓
[预处理器] → 清理、标准化
  ↓
[解析器链] → 尝试多种解析策略
  ↓
[构建器] → 创建结构化对象
  ↓
[标记注入器] → 添加语义标记
  ↓
[验证器] → 完整性验证
  ↓
[组织器] → 项目分类、时间线
  ↓
[格式化器] → 转换为输出格式
  ↓
[写入器] → 持久化存储
  ↓
[索引器] → 创建搜索索引
  ↓
最终知识库
```

### **解析器链策略**
```python
class ParserChain:
    """解析器链：按顺序尝试多种解析策略"""
    
    def __init__(self):
        self.parsers = [
            ShareLinkParser(),      # 策略1：分享链接解析
            MHTMLParser(),          # 策略2：MHTML解析
            JSONDataParser(),       # 策略3：JSON数据解析
            DOMStructureParser(),   # 策略4：DOM结构解析
            GenericHTMLParser()     # 策略5：通用HTML解析
        ]
    
    def parse(self, raw_input: RawInput) -> ParsedConversation:
        """按顺序尝试解析"""
        errors = []
        
        for parser in self.parsers:
            if parser.can_handle(raw_input):
                try:
                    result = parser.parse(raw_input)
                    if self.validate_result(result):
                        return result
                except Exception as e:
                    errors.append(f"{parser.__class__.__name__}: {str(e)}")
                    continue
        
        # 所有解析器都失败
        raise ParserChainError(f"所有解析器都失败: {errors}")
```

## 🗂️ **存储架构**

### **文件系统布局**
```
knowledge_base/
├── conversations/           # 原始对话存储
│   ├── raw/               # 原始文件（HTML/MHTML）
│   │   ├── 2024-01/
│   │   │   ├── conv_001.mhtml
│   │   │   └── conv_002.mhtml
│   │   └── 2024-02/
│   ├── parsed/            # 解析后的JSON
│   └── processed/         # 处理完成的Markdown
├── projects/              # 项目组织
│   ├── 元宙项目/
│   │   ├── metadata.json
│   │   ├── conversations.json
│   │   ├── 2024-01-25_概念定义.md
│   │   └── timeline.md
│   └── HTML解析器/
├── index/                 # 搜索索引
│   ├── fulltext.idx
│   ├── tags.idx
│   └── projects.idx
├── config/               # 配置
│   ├── settings.yaml
│   └── tags_vocabulary.txt
└── logs/                # 日志
    ├── parser.log
    └── system.log
```

### **数据库结构（可选SQLite）**
```sql
-- 对话表
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    source_type TEXT,
    source_url TEXT,
    title TEXT,
    content_hash TEXT,
    created_at DATETIME,
    processed_at DATETIME,
    importance_score FLOAT,
    is_archived BOOLEAN DEFAULT 0,
    raw_file_path TEXT,
    parsed_file_path TEXT,
    metadata_json TEXT
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    round_id TEXT,
    message_type TEXT,
    content TEXT,
    content_format TEXT,
    timestamp DATETIME,
    parent_id TEXT,
    has_code BOOLEAN,
    has_table BOOLEAN,
    word_count INTEGER,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 标签表
CREATE TABLE tags (
    conversation_id TEXT,
    tag_name TEXT,
    tag_type TEXT,
    confidence FLOAT,
    PRIMARY KEY (conversation_id, tag_name),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 项目表
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    conversations_count INTEGER
);

-- 对话-项目关联表
CREATE TABLE conversation_projects (
    conversation_id TEXT,
    project_id TEXT,
    relevance_score FLOAT,
    PRIMARY KEY (conversation_id, project_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

## 🔌 **API接口定义**

### **REST API（本地服务）**
```python
# API端点定义
class ConversationAPI:
    # 对话管理
    POST   /api/conversations/import        # 导入对话
    GET    /api/conversations/             # 获取对话列表
    GET    /api/conversations/{id}         # 获取对话详情
    PUT    /api/conversations/{id}/tags    # 更新标签
    DELETE /api/conversations/{id}         # 删除对话
    
    # 实时捕获
    WS     /ws/capture                     # WebSocket实时捕获
    POST   /api/capture/start              # 开始捕获
    POST   /api/capture/stop               # 停止捕获
    GET    /api/capture/status             # 获取捕获状态
    
    # 项目管理
    POST   /api/projects/                  # 创建项目
    GET    /api/projects/                  # 获取项目列表
    PUT    /api/projects/{id}              # 更新项目
    GET    /api/projects/{id}/timeline     # 获取项目时间线
    
    # 搜索
    GET    /api/search/                    # 全文搜索
    GET    /api/search/tags                # 按标签搜索
    GET    /api/search/projects            # 按项目搜索
    
    # 系统管理
    GET    /api/system/health              # 系统健康检查
    GET    /api/system/stats               # 系统统计
    POST   /api/system/reindex             # 重建索引
```

### **Python SDK接口**
```python
class DeepSeekKnowledgeSDK:
    """Python SDK，用于二次开发"""
    
    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        self.db = DatabaseConnection(self.config)
        
    # 对话操作
    def import_conversation(self, source: str, source_type: str) -> Conversation:
        """导入对话"""
        pass
        
    def get_conversation(self, conversation_id: str) -> Conversation:
        """获取对话"""
        pass
        
    def search_conversations(self, query: str, filters: Dict = None) -> List[Conversation]:
        """搜索对话"""
        pass
    
    # 项目管理
    def create_project(self, name: str, description: str = "") -> Project:
        """创建项目"""
        pass
        
    def add_to_project(self, conversation_id: str, project_id: str) -> bool:
        """添加到项目"""
        pass
    
    # 导出功能
    def export_markdown(self, conversation_id: str, output_path: str) -> str:
        """导出为Markdown"""
        pass
        
    def export_project(self, project_id: str, output_dir: str) -> List[str]:
        """导出整个项目"""
        pass
    
    # 批处理
    def batch_import(self, sources: List[str]) -> BatchResult:
        """批量导入"""
        pass
        
    def batch_export(self, conversation_ids: List[str], output_dir: str) -> BatchResult:
        """批量导出"""
        pass
```

## 🔧 **配置系统**

### **分层配置结构**
```yaml
# config/base.yaml
system:
  version: "1.0.0"
  data_dir: "~/deepseek_knowledge"
  log_level: "INFO"
  max_file_size_mb: 50

# config/parsers.yaml
parsers:
  share_link:
    enabled: true
    timeout_seconds: 30
    user_agent: "Mozilla/5.0 ..."
    
  mhtml:
    enabled: true
    browser_profile_path: "auto_detect"
    scroll_wait_seconds: 2
    max_scroll_attempts: 10
    
  realtime:
    enabled: false
    websocket_port: 8765
    auto_start: false

# config/formatters.yaml
formatters:
  markdown:
    enabled: true
    add_markers: true
    fold_user_queries: true
    fold_long_code_blocks: 30
    add_metadata_comments: true
    
  html:
    enabled: false
    include_styles: true
    
  json:
    enabled: true
    pretty_print: true

# config/organizers.yaml
organizers:
  projects:
    auto_detect: true
    min_conversations_per_project: 3
    default_project_name: "未分类"
    
  tags:
    auto_tag: true
    tag_vocabulary: "config/tags_vocabulary.txt"
    
  timeline:
    generate_timeline: true
    timeline_format: "markdown"

# config/storage.yaml
storage:
  file_system:
    conversations_dir: "conversations"
    projects_dir: "projects"
    index_dir: "index"
    
  database:
    enabled: true
    type: "sqlite"
    path: "knowledge_base/knowledge.db"
    
  backup:
    enabled: true
    backup_dir: "backups"
    keep_days: 30
    auto_backup: true
```

### **运行时配置**
```python
class RuntimeConfig:
    """运行时配置管理"""
    
    def __init__(self):
        self.base_config = self.load_yaml("config/base.yaml")
        self.user_config = self.load_user_config()
        self.runtime_overrides = {}
        
    def get(self, key: str, default=None):
        """获取配置（优先级：runtime > user > base）"""
        # 1. 检查运行时覆盖
        if key in self.runtime_overrides:
            return self.runtime_overrides[key]
            
        # 2. 检查用户配置
        value = self.user_config.get(key)
        if value is not None:
            return value
            
        # 3. 检查基础配置
        value = self.get_nested(self.base_config, key)
        if value is not None:
            return value
            
        # 4. 返回默认值
        return default
        
    def set_runtime(self, key: str, value: Any):
        """设置运行时配置"""
        self.runtime_overrides[key] = value
        
    def save_user_config(self):
        """保存用户配置"""
        save_yaml(self.user_config, "config/user_settings.yaml")
```

## 🧪 **测试架构**

### **测试层级**
```
tests/
├── unit/                 # 单元测试
│   ├── test_parsers.py
│   ├── test_builders.py
│   └── test_formatters.py
├── integration/         # 集成测试
│   ├── test_share_link.py
│   ├── test_mhtml.py
│   └── test_realtime.py
├── e2e/                # 端到端测试
│   ├── test_full_pipeline.py
│   └── test_batch_processing.py
├── fixtures/           # 测试数据
│   ├── sample_share_page.html
│   ├── sample_mhtml.mhtml
│   └── sample_conversation.json
└── utils/             # 测试工具
    ├── test_helpers.py
    └── mock_servers.py
```

### **测试数据生成器**
```python
class TestDataGenerator:
    """生成测试数据"""
    
    def generate_sample_conversation(self, round_count: int = 3) -> ParsedConversation:
        """生成示例对话"""
        conversation = ParsedConversation()
        conversation.metadata = ConversationMetadata(
            conversation_id=f"test_{uuid4()}",
            source_type="test",
            title="测试对话",
            created_at=datetime.now(),
            tags=["test", "sample"]
        )
        
        for i in range(round_count):
            round_id = f"{conversation.metadata.conversation_id}-{i+1}"
            round = ConversationRound(
                round_id=round_id,
                user_message=self._generate_message("user", f"用户问题 {i+1}"),
                assistant_message=self._generate_message("assistant", f"AI回答 {i+1}"),
                round_metadata={"test_round": True}
            )
            conversation.rounds.append(round)
        
        return conversation
    
    def _generate_message(self, msg_type: str, content: str) -> Message:
        """生成消息"""
        return Message(
            message_id=f"msg_{uuid4()}",
            type=MessageType(msg_type),
            content=content,
            content_format=ContentFormat.MARKDOWN,
            timestamp=datetime.now()
        )
```

## 📈 **部署与维护**

### **部署方式**
```
# 方式1：本地Python包
pip install -e .
deepseek-knowledge import --url https://chat.deepseek.com/share/xxx

# 方式2：独立可执行文件（PyInstaller）
deepseek-knowledge.exe --config my_config.yaml

# 方式3：Docker容器
docker run -v ./knowledge:/app/knowledge deepseek-knowledge

# 方式4：系统服务（Linux）
sudo systemctl enable deepseek-knowledge
```

### **更新机制**
```python
class UpdateManager:
    """更新管理器"""
    
    def check_for_updates(self) -> UpdateInfo:
        """检查更新"""
        pass
        
    def download_update(self, version: str) -> bool:
        """下载更新"""
        pass
        
    def apply_update(self, version: str) -> bool:
        """应用更新"""
        pass
        
    def rollback_update(self) -> bool:
        """回滚更新"""
        pass
        
    def migrate_data(self, old_version: str, new_version: str) -> MigrationResult:
        """数据迁移"""
        pass
```

## 📚 **文档架构**

### **文档结构**
```
docs/
├── user_guide/           # 用户指南
│   ├── getting_started.md
│   ├── phase1_usage.md
│   ├── phase2_usage.md
│   └── phase3_usage.md
├── developer/           # 开发者文档
│   ├── architecture.md
│   ├── api_reference.md
│   ├── extension_guide.md
│   └── contributing.md
├── api/                 # API文档
│   ├── rest_api.md
│   ├── python_sdk.md
│   └── data_models.md
├── examples/            # 示例
│   ├── basic_usage.py
│   ├── batch_processing.py
│   └── custom_parser.py
└── troubleshooting/     # 故障排除
    ├── common_issues.md
    ├── debugging.md
    └── faq.md
```

## 🎯 **总结与路线图**

### **完整实施路线图**

**阶段1：分享链接解析器（1-2周）**
- ✅ 完成核心解析器
- ✅ 实现标记注入系统
- ✅ 建立基础架构
- ✅ 提供CLI工具

**阶段2：MHTML全量保存器（2-3周）**
- 🔄 扩展浏览器控制功能
- 🔄 实现完整性验证
- 🔄 添加智能组织功能
- 🔄 集成阶段1的功能

**阶段3：实时监听扩展（3-4周）**
- ⏳ 开发浏览器扩展
- ⏳ 实现本地WebSocket服务
- ⏳ 创建实时处理流水线
- ⏳ 提供UI控制界面

**阶段4：高级功能（后续）**
- ⏳ AI辅助整理
- ⏳ 多平台支持
- ⏳ 云同步功能
- ⏳ 移动端应用

### **关键成功指标**
1. **完整性**：100%对话内容保存
2. **格式保持**：完美保持Markdown格式
3. **易用性**：简单直观的操作流程
4. **扩展性**：方便添加新功能
5. **性能**：快速处理大量对话

这个架构设计提供了：
- **清晰的接口定义**，便于后期扩展
- **完整的标记系统**，方便后续处理
- **分阶段的实现路径**，降低风险
- **详细的文档和测试**，确保质量

所有设计都围绕你的**个人使用场景**优化，避免过度设计，同时保持足够的灵活性和可扩展性。