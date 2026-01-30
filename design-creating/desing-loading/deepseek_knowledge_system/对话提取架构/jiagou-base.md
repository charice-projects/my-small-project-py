# 🎯 DeepSeek对话文档化系统 - 最小可行架构(MVP)

基于我们的深度讨论，我为您设计一个**最小可行架构**，保留所有核心功能，确保快速实现和立即使用。

## 🏗️ 一、MVP架构总览

### 1.1 核心原则
```
1. 最小功能集：解决最痛的点
2. 最大自动化：最少手动操作  
3. 最快路径：从对话到文档的最短路径
```

### 1.2 三层最小架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  浏览器提取层   │    │  Python处理层   │    │   文档输出层    │
│  (JS/插件)      │    │  (本地运行)     │    │  (Markdown)     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • 内容提取      │───▶│ • 标记解析      │───▶│ • 结构优化      │
│ • 标记生成      │    │ • 标题调整      │    │ • 空行布局      │
│ • 一键导出      │    │ • 文档组装      │    │ • 最终输出      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 二、浏览器提取层（最小实现）

### 2.1 核心文件：`deepseek-extractor.js`
```javascript
// ==UserScript==
// @name         DeepSeek对话提取器
// @namespace    deepseek
// @version      1.0
// @description  提取DeepSeek对话并添加标记
// @author       You
// @match        https://www.deepseek.com/chat/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 核心配置
    const CONFIG = {
        // 对话元素选择器（可能需要根据实际页面调整）
        SELECTORS: {
            messageContainer: '.message-container', // 示例，需实际调整
            userMessage: '[data-role="user"]',
            aiMessage: '[data-role="assistant"]',
            contentArea: '.prose'
        },
        
        // 标记格式
        MARKERS: {
            conversationStart: '<!-- 对话开始 | 时间:{timestamp} -->',
            conversationEnd: '<!-- 对话结束 -->',
            roundStart: '<!-- 轮次开始 | 序号:{index} -->',
            roundEnd: '<!-- 轮次结束 -->',
            userInput: '<!-- 用户输入 -->',
            aiOutputStart: '<!-- AI输出开始 -->',
            aiOutputEnd: '<!-- AI输出结束 -->'
        }
    };

    class DeepSeekExtractor {
        constructor() {
            this.conversationRounds = [];
            this.initUI();
        }

        // 初始化UI
        initUI() {
            const button = document.createElement('button');
            button.id = 'deepseek-extract-btn';
            button.innerHTML = '📥 提取对话';
            button.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 9999;
                background: #10a37f;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 20px;
                font-size: 14px;
                cursor: pointer;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            `;
            
            button.addEventListener('click', () => this.extractAndDownload());
            document.body.appendChild(button);
        }

        // 提取对话
        extractConversation() {
            this.conversationRounds = [];
            
            // 方法1：通过特定选择器获取消息
            const messages = document.querySelectorAll(CONFIG.SELECTORS.messageContainer);
            
            // 方法2：如果选择器无效，尝试通过结构识别
            if (messages.length === 0) {
                this.extractByStructure();
                return;
            }
            
            // 识别用户和AI消息
            let currentRound = null;
            
            messages.forEach((message, index) => {
                const isUser = message.querySelector(CONFIG.SELECTORS.userMessage);
                const isAI = message.querySelector(CONFIG.SELECTORS.aiMessage);
                
                if (isUser) {
                    // 新轮次开始
                    if (currentRound) {
                        this.conversationRounds.push(currentRound);
                    }
                    currentRound = {
                        user: this.extractContent(isUser),
                        ai: ''
                    };
                } else if (isAI && currentRound) {
                    currentRound.ai = this.extractContent(isAI);
                    this.conversationRounds.push(currentRound);
                    currentRound = null;
                }
            });
            
            // 处理最后一轮
            if (currentRound && currentRound.user) {
                this.conversationRounds.push(currentRound);
            }
            
            console.log(`提取到 ${this.conversationRounds.length} 轮对话`);
        }

        // 通过DOM结构识别消息（备用方法）
        extractByStructure() {
            // 寻找所有包含文本的div
            const allDivs = document.querySelectorAll('div');
            const candidateDivs = [];
            
            allDivs.forEach(div => {
                if (div.textContent.trim().length > 50 && 
                    div.children.length > 0 &&
                    !div.querySelector('button')) {
                    candidateDivs.push(div);
                }
            });
            
            // 简单的交替识别（假设用户和AI交替出现）
            for (let i = 0; i < candidateDivs.length; i += 2) {
                if (i + 1 < candidateDivs.length) {
                    this.conversationRounds.push({
                        user: this.simpleExtract(candidateDivs[i]),
                        ai: this.simpleExtract(candidateDivs[i + 1])
                    });
                }
            }
        }

        // 提取内容
        extractContent(element) {
            // 尝试获取Markdown格式
            const markdownElement = element.querySelector(CONFIG.SELECTORS.contentArea);
            if (markdownElement) {
                return this.convertToMarkdown(markdownElement);
            }
            
            // 回退到简单提取
            return this.simpleExtract(element);
        }

        // 简单提取（保持换行）
        simpleExtract(element) {
            return element.innerText.replace(/\n\s*\n/g, '\n\n').trim();
        }

        // 转换为Markdown（简化版）
        convertToMarkdown(element) {
            // 克隆以避免修改原DOM
            const clone = element.cloneNode(true);
            
            // 处理代码块
            const codeBlocks = clone.querySelectorAll('pre code, pre');
            codeBlocks.forEach(code => {
                const language = this.detectLanguage(code);
                const codeContent = code.textContent;
                code.parentNode.replaceChild(
                    document.createTextNode(`\`\`\`${language}\n${codeContent}\n\`\`\``), 
                    code
                );
            });
            
            // 处理标题（h1-h6）
            const headings = clone.querySelectorAll('h1, h2, h3, h4, h5, h6');
            headings.forEach(heading => {
                const level = heading.tagName[1];
                const text = heading.textContent;
                heading.parentNode.replaceChild(
                    document.createTextNode(`${'#'.repeat(level)} ${text}`),
                    heading
                );
            });
            
            return clone.textContent.trim();
        }

        // 检测代码语言
        detectLanguage(codeElement) {
            const className = codeElement.className || '';
            const match = className.match(/language-(\w+)/);
            return match ? match[1] : '';
        }

        // 生成标记文本
        generateMarkedText() {
            const lines = [];
            const timestamp = new Date().toISOString().split('T')[0];
            
            // 对话开始标记
            lines.push(CONFIG.MARKERS.conversationStart.replace('{timestamp}', timestamp));
            lines.push('');
            
            // 每轮对话
            this.conversationRounds.forEach((round, index) => {
                lines.push(CONFIG.MARKERS.roundStart.replace('{index}', index + 1));
                lines.push('');
                
                // 用户输入
                lines.push(CONFIG.MARKERS.userInput);
                lines.push(round.user);
                lines.push('');
                
                // AI输出
                lines.push(CONFIG.MARKERS.aiOutputStart);
                lines.push(round.ai);
                lines.push(CONFIG.MARKERS.aiOutputEnd);
                lines.push('');
                
                lines.push(CONFIG.MARKERS.roundEnd);
                lines.push('');
                lines.push('---');
                lines.push('');
            });
            
            // 对话结束标记
            lines.push(CONFIG.MARKERS.conversationEnd);
            
            return lines.join('\n');
        }

        // 下载文件
        downloadFile(content, filename) {
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        // 主流程：提取并下载
        extractAndDownload() {
            try {
                // 提取对话
                this.extractConversation();
                
                if (this.conversationRounds.length === 0) {
                    alert('未检测到对话内容，请确保页面已加载完成');
                    return;
                }
                
                // 生成标记文本
                const markedText = this.generateMarkedText();
                
                // 生成文件名
                const timestamp = new Date().toISOString()
                    .replace(/[:.]/g, '-')
                    .split('.')[0];
                const filename = `deepseek-conversation-${timestamp}.txt`;
                
                // 下载
                this.downloadFile(markedText, filename);
                
                // 提示用户
                alert(`成功提取 ${this.conversationRounds.length} 轮对话，文件已下载: ${filename}\n\n请使用Python处理器进一步优化。`);
                
            } catch (error) {
                console.error('提取失败:', error);
                alert('提取失败，请打开开发者工具查看错误信息');
            }
        }
    }

    // 页面加载完成后初始化
    window.addEventListener('load', () => {
        // 延迟初始化，确保页面完全加载
        setTimeout(() => {
            new DeepSeekExtractor();
        }, 2000);
    });

})();
```

### 2.2 安装说明
```
1. 安装浏览器用户脚本管理器：
   - Chrome: Tampermonkey
   - Firefox: Greasemonkey
   - Edge: Tampermonkey

2. 新建用户脚本
3. 粘贴上面的代码
4. 保存并启用

5. 访问DeepSeek对话页面
6. 页面右上角会出现"📥 提取对话"按钮
```

## 🐍 三、Python处理层（最小实现）

### 3.1 项目结构
```
deepseek-processor/
├── deepseek_processor.py    # 主处理程序
├── requirements.txt         # 依赖文件
├── config.yaml             # 配置文件
└── samples/                # 示例文件
    └── conversation.txt    # 示例对话
```

### 3.2 主处理文件：`deepseek_processor.py`
```python
#!/usr/bin/env python3
"""
DeepSeek对话文档优化处理器 - MVP版本
"""

import re
import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import yaml

# ==================== 数据结构 ====================

class ConversationRound:
    """对话轮次"""
    def __init__(self, index: int, user_input: str, ai_output: str):
        self.index = index
        self.user_input = user_input.strip()
        self.ai_output = ai_output.strip()
    
    def __repr__(self):
        return f"Round {self.index}: {self.user_input[:50]}..."

class Conversation:
    """完整对话"""
    def __init__(self, timestamp: str, rounds: List[ConversationRound]):
        self.timestamp = timestamp
        self.rounds = rounds
    
    @property
    def total_rounds(self):
        return len(self.rounds)

# ==================== 标记解析器 ====================

class MarkedFileParser:
    """解析浏览器生成的标记文件"""
    
    def __init__(self):
        self.patterns = {
            'conversation_start': r'<!-- 对话开始 \| 时间:([^ ]+) -->',
            'conversation_end': r'<!-- 对话结束 -->',
            'round_start': r'<!-- 轮次开始 \| 序号:(\d+) -->',
            'round_end': r'<!-- 轮次结束 -->',
            'user_input': r'<!-- 用户输入 -->',
            'ai_output_start': r'<!-- AI输出开始 -->',
            'ai_output_end': r'<!-- AI输出结束 -->'
        }
    
    def parse_file(self, file_path: str) -> Optional[Conversation]:
        """解析标记文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取对话时间
            time_match = re.search(self.patterns['conversation_start'], content)
            if not time_match:
                print(f"警告: {file_path} 中未找到对话开始标记")
                return None
            
            timestamp = time_match.group(1)
            
            # 提取所有轮次
            rounds = self._extract_rounds(content)
            
            if not rounds:
                print(f"警告: {file_path} 中未找到有效轮次")
                return None
            
            return Conversation(timestamp, rounds)
            
        except Exception as e:
            print(f"解析文件 {file_path} 时出错: {e}")
            return None
    
    def _extract_rounds(self, content: str) -> List[ConversationRound]:
        """提取所有对话轮次"""
        rounds = []
        
        # 分割轮次（基于轮次开始标记）
        round_parts = re.split(self.patterns['round_start'], content)
        
        for i in range(1, len(round_parts), 2):
            if i >= len(round_parts):
                break
                
            round_index = int(round_parts[i])
            round_content = round_parts[i + 1]
            
            # 提取用户输入
            user_match = re.search(
                r'<!-- 用户输入 -->\s*(.*?)\s*(?:<!-- AI输出开始 -->|<!-- 轮次结束 -->)',
                round_content,
                re.DOTALL
            )
            
            # 提取AI输出
            ai_match = re.search(
                r'<!-- AI输出开始 -->\s*(.*?)\s*<!-- AI输出结束 -->',
                round_content,
                re.DOTALL
            )
            
            if user_match and ai_match:
                rounds.append(ConversationRound(
                    index=round_index,
                    user_input=user_match.group(1).strip(),
                    ai_output=ai_match.group(1).strip()
                ))
        
        return rounds

# ==================== 标题优化器 ====================

class HeadingOptimizer:
    """标题层级优化器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    def optimize_headings(self, content: str) -> str:
        """优化标题层级"""
        if not content:
            return content
        
        # 查找所有标题
        headings = list(self.heading_pattern.finditer(content))
        
        if not headings:
            return content
        
        # 分析标题层级
        levels = [len(match.group(1)) for match in headings]
        min_level = min(levels)
        
        # 计算调整偏移量
        adjustment = self._calculate_adjustment(min_level)
        
        if adjustment == 0:
            return content
        
        # 应用调整
        def replace_heading(match):
            level = len(match.group(1))
            text = match.group(2)
            new_level = min(6, max(1, level + adjustment))
            return f"{'#' * new_level} {text}"
        
        return self.heading_pattern.sub(replace_heading, content)
    
    def _calculate_adjustment(self, min_level: int) -> int:
        """计算标题调整偏移量"""
        strategy = self.config.get('heading_strategy', 'balanced')
        target_min = self.config.get('min_heading_level', 3)
        
        if strategy == 'conservative':
            # 保守：只在绝对必要时调整
            if min_level == 1:
                return 2
            elif min_level == 2:
                return 1
            return 0
        
        elif strategy == 'aggressive':
            # 激进：确保最小层级为目标值
            return target_min - min_level
        
        else:  # balanced (默认)
            # 平衡：智能调整
            if min_level == 1:
                return 2
            elif min_level == 2:
                return 1
            elif min_level >= 4:
                return -1  # 如果层级过深，稍微提升
            return 0

# ==================== 文档生成器 ====================

class DocumentGenerator:
    """生成优化后的文档"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.heading_optimizer = HeadingOptimizer(config)
    
    def generate_document(self, conversation: Conversation, source_file: str) -> str:
        """生成完整文档"""
        lines = []
        
        # 1. 文档标题
        doc_title = self._generate_document_title(conversation)
        lines.append(f"# {doc_title}")
        lines.append("")
        
        # 2. 元数据块
        lines.extend(self._generate_metadata_block(conversation, source_file))
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 3. 对话轮次
        for round_data in conversation.rounds:
            lines.extend(self._generate_round_section(round_data))
            lines.append("")  # 轮次间空行
        
        # 4. 文档结束
        lines.append("---")
        lines.append("")
        lines.append(f"*文档生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return '\n'.join(lines)
    
    def _generate_document_title(self, conversation: Conversation) -> str:
        """生成文档标题"""
        if conversation.rounds:
            # 从第一轮用户输入提取标题
            first_input = conversation.rounds[0].user_input
            first_line = first_input.split('\n')[0].strip()
            
            # 清理标题（移除特殊字符，限制长度）
            title = re.sub(r'[#*`\[\]]', '', first_line)
            title = title[:60].strip()
            
            if len(first_line) > 60:
                title += "..."
            
            return title or "DeepSeek对话记录"
        return "未命名对话"
    
    def _generate_metadata_block(self, conversation: Conversation, source_file: str) -> List[str]:
        """生成元数据块"""
        meta_lines = []
        
        # 基础信息
        meta_lines.append(f"**对话时间**: {conversation.timestamp}")
        meta_lines.append(f"**对话轮次**: {conversation.total_rounds}")
        meta_lines.append(f"**源文件**: {os.path.basename(source_file)}")
        meta_lines.append(f"**生成工具**: DeepSeek对话处理器 v1.0")
        
        # 格式化为列表
        return [f"- {line}" for line in meta_lines]
    
    def _generate_round_section(self, round_data: ConversationRound) -> List[str]:
        """生成单个轮次部分"""
        lines = []
        
        # 轮次标题
        lines.append(f"## 轮次 {round_data.index}")
        lines.append("")
        
        # 用户输入
        lines.append("### 用户输入")
        lines.append("")
        lines.append(self._format_user_input(round_data.user_input))
        lines.append("")
        
        # AI输出（应用标题优化）
        lines.append("### DeepSeek回复")
        lines.append("")
        
        optimized_ai_output = self.heading_optimizer.optimize_headings(round_data.ai_output)
        lines.append(optimized_ai_output)
        lines.append("")
        
        # 分隔线
        lines.append("---")
        
        return lines
    
    def _format_user_input(self, user_input: str) -> str:
        """格式化用户输入"""
        # 移除多余的空行
        lines = user_input.strip().split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.rstrip()
            if line or (formatted_lines and formatted_lines[-1]):
                formatted_lines.append(line)
        
        # 确保最后不是空行
        while formatted_lines and not formatted_lines[-1]:
            formatted_lines.pop()
        
        return '\n'.join(formatted_lines)

# ==================== 配置文件管理 ====================

class ConfigManager:
    """配置文件管理"""
    
    DEFAULT_CONFIG = {
        'processing': {
            'heading_strategy': 'balanced',  # conservative|balanced|aggressive
            'min_heading_level': 3,
            'compress_excessive_depth': True,
        },
        'output': {
            'default_dir': './processed_docs',
            'auto_create_dir': True,
            'filename_template': '{title}_{date}.md',
        }
    }
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f) or {}
            
            # 深度合并配置
            self._deep_merge(self.config, user_config)
            print(f"已加载配置文件: {config_path}")
            
        except Exception as e:
            print(f"加载配置文件失败，使用默认配置: {e}")
    
    def _deep_merge(self, base: Dict, update: Dict):
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

# ==================== 命令行界面 ====================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='DeepSeek对话文档优化处理器 - MVP版本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s conversation.txt              # 处理单个文件
  %(prog)s *.txt -o ./docs              # 批量处理
  %(prog)s input.txt --no-optimize      # 不优化标题层级
  
输出示例:
  ./docs/项目架构设计讨论_20240123.md
        """
    )
    
    parser.add_argument(
        'input_files',
        nargs='+',
        help='输入文件（支持通配符，如 *.txt）'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='./processed_docs',
        help='输出目录（默认: ./processed_docs）'
    )
    
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='配置文件路径（默认: config.yaml）'
    )
    
    parser.add_argument(
        '--no-optimize',
        action='store_true',
        help='不优化标题层级（保持原样）'
    )
    
    parser.add_argument(
        '--strategy',
        choices=['conservative', 'balanced', 'aggressive'],
        default='balanced',
        help='标题优化策略（默认: balanced）'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细处理信息'
    )
    
    args = parser.parse_args()
    
    # 初始化配置
    config_manager = ConfigManager(args.config)
    
    # 更新命令行参数
    if args.no_optimize:
        config_manager.config['processing']['heading_strategy'] = 'none'
    else:
        config_manager.config['processing']['heading_strategy'] = args.strategy
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"DeepSeek对话处理器 v1.0")
    print(f"输出目录: {output_dir.absolute()}")
    print("-" * 50)
    
    # 处理文件
    processed_count = 0
    failed_files = []
    
    for input_pattern in args.input_files:
        # 展开通配符
        input_files = list(Path().glob(input_pattern))
        
        for input_file in input_files:
            if not input_file.is_file():
                continue
            
            try:
                if args.verbose:
                    print(f"处理: {input_file.name}")
                
                # 解析文件
                parser = MarkedFileParser()
                conversation = parser.parse_file(str(input_file))
                
                if not conversation:
                    print(f"  ✗ 无法解析: {input_file.name}")
                    failed_files.append((input_file.name, "解析失败"))
                    continue
                
                # 生成文档
                generator = DocumentGenerator(config_manager.config)
                document = generator.generate_document(conversation, str(input_file))
                
                # 生成输出文件名
                output_filename = generate_output_filename(conversation, input_file)
                output_path = output_dir / output_filename
                
                # 保存文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(document)
                
                processed_count += 1
                
                if args.verbose:
                    print(f"  ✓ 已保存: {output_filename} ({conversation.total_rounds}轮)")
                
            except Exception as e:
                print(f"  ✗ 处理失败: {input_file.name} - {str(e)}")
                failed_files.append((input_file.name, str(e)))
    
    # 输出结果
    print("\n" + "=" * 50)
    print(f"处理完成!")
    print("=" * 50)
    print(f"✓ 成功处理: {processed_count} 个文件")
    
    if failed_files:
        print(f"✗ 处理失败: {len(failed_files)} 个文件")
        for filename, error in failed_files:
            print(f"  - {filename}: {error}")
    
    print(f"\n输出文件位于: {output_dir.absolute()}")
    print("请查看该目录下的.md文件获取处理结果。")

def generate_output_filename(conversation: Conversation, input_file: Path) -> str:
    """生成输出文件名"""
    # 从对话生成标题
    if conversation.rounds:
        title = conversation.rounds[0].user_input[:30]
        title = re.sub(r'[^\w\s-]', '', title)  # 移除特殊字符
        title = re.sub(r'[-\s]+', '_', title)   # 替换空格为下划线
        title = title.strip('_')
    else:
        title = "conversation"
    
    # 添加日期
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 限制长度
    if len(title) > 40:
        title = title[:37] + "..."
    
    return f"{title}_{date_str}.md"

# ==================== 配置文件 ====================

def create_default_config():
    """创建默认配置文件"""
    config_content = """# DeepSeek对话处理器配置文件

# 处理配置
processing:
  # 标题优化策略: conservative|balanced|aggressive
  heading_strategy: "balanced"
  
  # AI标题最小级别 (1-6)
  min_heading_level: 3
  
  # 压缩过深的标题层级
  compress_excessive_depth: true

# 输出配置
output:
  # 默认输出目录
  default_dir: "./processed_docs"
  
  # 自动创建输出目录
  auto_create_dir: true
  
  # 文件名模板
  # 可用变量: {title}, {date}, {time}, {rounds}
  filename_template: "{title}_{date}.md"

# 空行布局配置
spacing:
  # 对话之间空行数
  between_conversations: 2
  
  # 轮次之间空行数  
  between_rounds: 1
  
  # 用户输入与AI输出之间空行数
  between_qa: 1
"""
    
    with open('config.yaml', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print("已创建默认配置文件: config.yaml")

# ==================== 入口点 ====================

if __name__ == "__main__":
    # 检查是否首次运行（没有配置文件）
    if not os.path.exists('config.yaml'):
        print("首次运行，创建默认配置文件...")
        create_default_config()
    
    # 运行主程序
    main()
```

### 3.3 依赖文件：`requirements.txt`
```txt
# DeepSeek对话处理器依赖
PyYAML>=6.0
```

### 3.4 安装和使用说明

```
1. 安装Python 3.8+
2. 克隆或创建项目目录

3. 安装依赖：
   pip install -r requirements.txt

4. 首次运行会自动创建配置文件

5. 使用浏览器脚本提取对话，保存为.txt文件

6. 运行处理器：
   python deepseek_processor.py conversation.txt

7. 批量处理：
   python deepseek_processor.py *.txt -o ./docs -v

8. 查看生成的文档：
   ls ./docs/*.md
```

## 📋 四、最小功能清单

### 4.1 核心功能（已实现）
```
✅ 浏览器端：
   - 一键提取DeepSeek对话
   - 自动识别用户/AI消息
   - 保持代码块格式
   - 添加结构化标记
   - 下载为.txt文件

✅ Python处理端：
   - 解析标记文件
   - 智能标题层级优化
   - 生成标准Markdown
   - 添加元数据信息
   - 批量处理支持
   - 配置文件管理

✅ 用户体验：
   - 简单命令行界面
   - 清晰进度反馈
   - 错误处理
   - 输出文档美观可用
```

### 4.2 工作流程（最小）
```
步骤1：在DeepSeek完成对话
步骤2：点击浏览器插件"提取对话"按钮
步骤3：自动下载标记文件（.txt）
步骤4：运行Python处理器
步骤5：获得优化后的Markdown文档
步骤6：直接使用文档或放入项目
```

## 🚀 五、快速开始指南

### 5.1 30秒安装测试
```bash
# 1. 安装浏览器脚本管理器（如Tampermonkey）

# 2. 创建新用户脚本，粘贴JS代码

# 3. 创建Python项目目录
mkdir deepseek-processor
cd deepseek-processor

# 4. 创建Python文件
# （粘贴上面的Python代码到deepseek_processor.py）

# 5. 安装依赖
pip install PyYAML

# 6. 测试运行
python deepseek_processor.py --help
```

### 5.2 测试对话文件示例
```markdown
<!-- 对话开始 | 时间:2024-01-23 -->
<!-- 轮次开始 | 序号:1 -->
<!-- 用户输入 -->
帮我设计一个REST API的用户认证系统

<!-- AI输出开始 -->
## 用户认证系统设计

### JWT认证流程

```python
from datetime import datetime, timedelta
import jwt

def create_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

#### 安全考虑
1. 使用HTTPS
2. 令牌有效期
3. 刷新令牌机制

<!-- AI输出结束 -->
<!-- 轮次结束 -->
<!-- 对话结束 -->
```

### 5.3 预期输出文档
```markdown
# 帮我设计一个REST API的用户认证系统

**对话时间**: 2024-01-23
**对话轮次**: 1
**源文件**: deepseek-conversation-2024-01-23.txt
**生成工具**: DeepSeek对话处理器 v1.0

---

## 轮次 1

### 用户输入

帮我设计一个REST API的用户认证系统

### DeepSeek回复

#### 用户认证系统设计

##### JWT认证流程

```python
from datetime import datetime, timedelta
import jwt

def create_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

###### 安全考虑
1. 使用HTTPS
2. 令牌有效期
3. 刷新令牌机制

---

*文档生成时间: 2024-01-23 15:30:45*
```

## 📈 六、后续扩展点（可暂不实现）

```
阶段2扩展（稳定后）：
1. 更智能的DOM识别
2. 视觉节奏引擎（智能空行）
3. 可折叠内容
4. 导航系统
5. HTML输出格式

阶段3扩展（高级）：
1. 实时预览
2. 项目集成
3. 团队协作
4. 云同步
```

## 💡 七、故障排除

### 常见问题
```
Q1: 浏览器脚本无法识别对话
A1: 调整SELECTORS中的选择器，或使用开发者工具检查DOM结构

Q2: Python处理失败
A2: 检查标记文件格式，确保符合规范

Q3: 标题优化不符合预期
A3: 修改config.yaml中的heading_strategy配置

Q4: 生成的文档乱码
A4: 确保所有文件使用UTF-8编码
```

## 🎯 八、总结

这个最小架构实现了：
1. **一键提取**：浏览器插件简化操作
2. **智能优化**：自动调整标题层级
3. **标准输出**：生成可直接使用的Markdown
4. **配置灵活**：支持不同优化策略
5. **快速实现**：总共约500行代码

**立即行动建议**：
1. 先实现浏览器脚本（1小时）
2. 测试提取功能（30分钟）
3. 实现Python处理器（2小时）
4. 完整测试工作流（1小时）
5. 开始使用并收集反馈

这个最小架构完全可用，解决了最核心的痛点：**从对话到结构化文档的自动转换**。后续可以根据实际使用情况逐步增强功能。