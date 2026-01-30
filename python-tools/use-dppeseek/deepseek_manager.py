#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deepseek对话专业处理工具 v3.0
功能：解析、格式化、管理Deepseek对话内容
作者：Deepseek用户
"""

import re
import json
import os
import sys
import time
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import argparse
import pyperclip
import traceback
import html

# ============================================================================
# 配置系统
# ============================================================================

class Config:
    """配置管理器"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.config_dir = self.home_dir / ".deepseek_manager"
        self.config_file = self.config_dir / "config.json"
        self.db_file = self.config_dir / "conversations.db.json"
        self.index_file = self.config_dir / "search_index.json"
        
        # 输出目录结构
        self.output_base = Path("Deepseek知识库")
        self.dirs = {
            'work': self.output_base / "工作相关",
            'learning': self.output_base / "学习探索", 
            'creative': self.output_base / "创意写作",
            'casual': self.output_base / "闲聊娱乐",
            'other': self.output_base / "其他分类",
            'archive': self.output_base / "_归档",
            'resources': self.output_base / "_资源"
        }
        
        # 默认设置
        self.default_settings = {
            'version': '3.0.0',
            'auto_classify': True,
            'auto_adjust_headings': True,
            'include_metadata': True,
            'include_markers': True,
            'output_format': 'markdown',
            'backup_enabled': True,
            'backup_count': 10,
            'theme': 'light',
            'recent_projects': []
        }
        
        # 初始化
        self.init_directories()
        self.settings = self.load_settings()
    
    def init_directories(self):
        """初始化目录结构"""
        self.config_dir.mkdir(exist_ok=True)
        self.output_base.mkdir(exist_ok=True)
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        # 创建资源子目录
        (self.dirs['resources'] / 'code_snippets').mkdir(exist_ok=True)
        (self.dirs['resources'] / 'images').mkdir(exist_ok=True)
        (self.dirs['resources'] / 'attachments').mkdir(exist_ok=True)
    
    def load_settings(self):
        """加载设置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 合并默认设置
                    return {**self.default_settings, **settings}
            except:
                pass
        return self.default_settings.copy()
    
    def save_settings(self):
        """保存设置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

# ============================================================================
# 数据库系统
# ============================================================================

class ConversationDB:
    """对话数据库"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_file = config.db_file
        self.index_file = config.index_file
        self.data = self.load_db()
        self.index = self.load_index()
    
    def load_db(self):
        """加载数据库"""
        if self.db_file.exists():
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'conversations' in data:
                        return data
            except:
                pass
        
        return {
            'version': '3.0.0',
            'conversations': [],
            'categories': {},
            'tags': {},
            'stats': {
                'total': 0,
                'by_category': {},
                'by_month': {},
                'by_project': {}
            },
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def load_index(self):
        """加载搜索索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'tokens': {},
            'conversations': {},
            'last_updated': None
        }
    
    def save_db(self):
        """保存数据库"""
        self.data['updated_at'] = datetime.now().isoformat()
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def save_index(self):
        """保存索引"""
        self.index['last_updated'] = datetime.now().isoformat()
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def add_conversation(self, conversation: Dict) -> str:
        """添加对话到数据库"""
        # 生成唯一ID
        conv_id = conversation.get('id') or self.generate_id(conversation)
        conversation['id'] = conv_id
        
        # 设置时间戳
        if 'saved_at' not in conversation:
            conversation['saved_at'] = datetime.now().isoformat()
        
        # 添加到数据库
        self.data['conversations'].append(conversation)
        self.data['stats']['total'] = len(self.data['conversations'])
        
        # 更新分类统计
        category = conversation.get('main_category', '未分类')
        self.data['stats']['by_category'][category] = \
            self.data['stats']['by_category'].get(category, 0) + 1
        
        # 更新月份统计
        month = datetime.now().strftime('%Y-%m')
        self.data['stats']['by_month'][month] = \
            self.data['stats']['by_month'].get(month, 0) + 1
        
        # 更新索引
        self.update_index(conversation)
        
        # 保存
        self.save_db()
        self.save_index()
        
        return conv_id
    
    def update_index(self, conversation: Dict):
        """更新搜索索引"""
        conv_id = conversation['id']
        
        # 提取文本内容
        text_content = self.extract_text_for_indexing(conversation)
        
        # 分词（简单实现）
        tokens = self.tokenize(text_content)
        
        # 更新索引
        for token in tokens:
            if token not in self.index['tokens']:
                self.index['tokens'][token] = []
            
            if conv_id not in self.index['tokens'][token]:
                self.index['tokens'][token].append(conv_id)
        
        # 保存对话元数据
        self.index['conversations'][conv_id] = {
            'title': conversation.get('title', ''),
            'category': conversation.get('main_category', ''),
            'timestamp': conversation.get('saved_at', ''),
            'rounds': len(conversation.get('rounds', [])),
            'tokens': len(tokens)
        }
    
    def extract_text_for_indexing(self, conversation: Dict) -> str:
        """提取用于索引的文本"""
        texts = []
        
        # 标题
        texts.append(conversation.get('title', ''))
        
        # 每个轮次的用户指令和AI回复
        for round_data in conversation.get('rounds', []):
            texts.append(round_data.get('userInstruction', ''))
            texts.append(round_data.get('aiResponse', ''))
        
        # 分类和标签
        texts.append(conversation.get('main_category', ''))
        
        return ' '.join(texts)
    
    def tokenize(self, text: str) -> List[str]:
        """简单分词"""
        # 转换为小写
        text = text.lower()
        
        # 移除标点符号
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        
        # 分割单词
        tokens = re.findall(r'[\u4e00-\u9fff]+|\w+', text)
        
        # 过滤停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        tokens = [t for t in tokens if t not in stop_words and len(t) > 1]
        
        return tokens
    
    def generate_id(self, conversation: Dict) -> str:
        """生成唯一ID"""
        # 使用内容哈希
        content = json.dumps(conversation, sort_keys=True, ensure_ascii=False)
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"conv_{hash_obj.hexdigest()[:12]}"
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """搜索对话"""
        query_tokens = self.tokenize(query.lower())
        
        if not query_tokens:
            return []
        
        # 计算相关度得分
        scores = {}
        
        for token in query_tokens:
            if token in self.index['tokens']:
                for conv_id in self.index['tokens'][token]:
                    scores[conv_id] = scores.get(conv_id, 0) + 1
        
        # 按得分排序
        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # 获取完整对话
        results = []
        for conv_id, score in sorted_ids:
            conversation = self.get_conversation(conv_id)
            if conversation:
                conversation['relevance_score'] = score
                results.append(conversation)
        
        return results
    
    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """获取对话"""
        for conv in self.data['conversations']:
            if conv.get('id') == conv_id:
                return conv
        return None
    
    def delete_conversation(self, conv_id: str) -> bool:
        """删除对话"""
        original_count = len(self.data['conversations'])
        self.data['conversations'] = [
            conv for conv in self.data['conversations'] 
            if conv.get('id') != conv_id
        ]
        
        if len(self.data['conversations']) < original_count:
            # 更新统计
            self.data['stats']['total'] = len(self.data['conversations'])
            
            # 从索引中删除
            self.remove_from_index(conv_id)
            
            # 保存
            self.save_db()
            self.save_index()
            
            return True
        
        return False
    
    def remove_from_index(self, conv_id: str):
        """从索引中删除对话"""
        # 从tokens索引中删除
        for token, conv_ids in list(self.index['tokens'].items()):
            if conv_id in conv_ids:
                conv_ids.remove(conv_id)
                if not conv_ids:
                    del self.index['tokens'][token]
        
        # 从对话索引中删除
        if conv_id in self.index['conversations']:
            del self.index['conversations'][conv_id]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.data.get('stats', {})

# ============================================================================
# 内容解析器
# ============================================================================

class ContentParser:
    """内容解析器"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # 解析模式
        self.patterns = {
            'conversation_start': re.compile(r'<!--\s*对话开始\s+([^\s|]+)(?:\s*\|\s*(.+?))?\s*-->'),
            'conversation_end': re.compile(r'<!--\s*对话结束\s+([^\s]+)\s*-->'),
            'round_start': re.compile(r'<!--\s*轮次开始\s+(\d+)(?:\s*\|\s*(.+?))?\s*-->'),
            'round_end': re.compile(r'<!--\s*AI输出结束\s*(?:\|\s*轮次结束\s+(\d+))?\s*-->'),
            'ai_output_start': re.compile(r'<!--\s*AI输出开始\s*-->'),
            'metadata': re.compile(r'<!--\s*元数据:\s*(.+?)\s*-->'),
            'title': re.compile(r'^#\s+(.+)$', re.MULTILINE)
        }
    
    def parse_markdown(self, content: str) -> Optional[Dict]:
        """解析Markdown内容"""
        lines = content.split('\n')
        conversation = None
        current_round = None
        parsing_ai = False
        ai_content = []
        
        for i, line in enumerate(lines):
            # 对话开始
            match = self.patterns['conversation_start'].match(line)
            if match:
                conv_id = match.group(1)
                metadata_str = match.group(2)
                
                conversation = {
                    'id': conv_id,
                    'format': 'markdown',
                    'metadata': self.parse_metadata(metadata_str) if metadata_str else {},
                    'rounds': [],
                    'parsed_from': 'markdown'
                }
                continue
            
            # 对话结束
            if self.patterns['conversation_end'].match(line):
                if conversation and current_round:
                    # 保存最后一个轮次
                    if ai_content:
                        current_round['aiResponse'] = '\n'.join(ai_content).strip()
                        conversation['rounds'].append(current_round)
                break
            
            # 轮次开始
            match = self.patterns['round_start'].match(line)
            if match and conversation:
                # 如果有当前轮次，先保存
                if current_round and ai_content:
                    current_round['aiResponse'] = '\n'.join(ai_content).strip()
                    conversation['rounds'].append(current_round)
                    ai_content = []
                
                round_num = match.group(1)
                round_meta = match.group(2)
                
                current_round = {
                    'number': int(round_num),
                    'metadata': self.parse_metadata(round_meta) if round_meta else {},
                    'userInstruction': '',
                    'aiResponse': ''
                }
                parsing_ai = False
                continue
            
            # AI输出开始
            if self.patterns['ai_output_start'].match(line):
                parsing_ai = True
                continue
            
            # 轮次结束
            match = self.patterns['round_end'].match(line)
            if match and conversation and current_round and parsing_ai:
                # 保存AI内容
                current_round['aiResponse'] = '\n'.join(ai_content).strip()
                conversation['rounds'].append(current_round)
                current_round = None
                ai_content = []
                parsing_ai = False
                continue
            
            # 标题
            if not conversation and i < 10:  # 只在开头检查
                match = self.patterns['title'].match(line)
                if match:
                    if not conversation:
                        conversation = {
                            'id': f"parsed_{int(time.time())}",
                            'format': 'markdown',
                            'rounds': [],
                            'parsed_from': 'markdown'
                        }
                    conversation['title'] = match.group(1)
                    continue
            
            # 用户指令标题
            if line.strip() == '### 👤 我的指令' and current_round:
                # 接下来的内容是用户指令
                user_content = []
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('###'):
                    user_content.append(lines[j])
                    j += 1
                
                if user_content:
                    current_round['userInstruction'] = '\n'.join(user_content).strip()
                continue
            
            # AI输出内容
            if parsing_ai and current_round:
                # 跳过AI输出标题行
                if line.strip() == '### 🤖 AI输出':
                    continue
                ai_content.append(line)
        
        # 如果没有解析到对话结构，尝试其他方法
        if not conversation or not conversation.get('rounds'):
            conversation = self.parse_legacy_format(content)
        
        # 提取标题
        if conversation and not conversation.get('title'):
            conversation['title'] = self.extract_title(content)
        
        # 分类
        if conversation:
            classifier = ContentClassifier(self.config)
            classification = classifier.classify_conversation(conversation)
            conversation['main_category'] = classification['main_category']
            conversation['classification'] = classification
        
        return conversation
    
    def parse_legacy_format(self, content: str) -> Dict:
        """解析旧格式的内容"""
        lines = content.split('\n')
        conversation = {
            'id': f"legacy_{int(time.time())}",
            'format': 'legacy_markdown',
            'rounds': [],
            'parsed_from': 'legacy'
        }
        
        # 尝试提取标题
        title_match = self.patterns['title'].search(content)
        if title_match:
            conversation['title'] = title_match.group(1)
        else:
            conversation['title'] = f"对话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 简单分割轮次
        sections = re.split(r'\n-{3,}\n', content)
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # 尝试识别用户指令和AI输出
            lines = section.strip().split('\n')
            user_content = []
            ai_content = []
            current_part = 'unknown'
            
            for line in lines:
                if line.startswith('## '):
                    # 轮次标题
                    pass
                elif line.startswith('### '):
                    if '指令' in line or '我的指令' in line:
                        current_part = 'user'
                    elif 'AI' in line or '输出' in line:
                        current_part = 'ai'
                    else:
                        current_part = 'unknown'
                else:
                    if current_part == 'user':
                        user_content.append(line)
                    elif current_part == 'ai':
                        ai_content.append(line)
                    else:
                        # 默认添加到用户指令
                        user_content.append(line)
            
            if user_content or ai_content:
                round_data = {
                    'number': i + 1,
                    'userInstruction': '\n'.join(user_content).strip(),
                    'aiResponse': '\n'.join(ai_content).strip()
                }
                
                # 提取轮次标题
                for line in lines:
                    if line.startswith('## '):
                        round_data['title'] = line[3:].strip()
                        break
                
                if not round_data.get('title'):
                    # 从用户指令中提取标题
                    first_line = user_content[0] if user_content else ''
                    if len(first_line) > 50:
                        round_data['title'] = first_line[:47] + '...'
                    else:
                        round_data['title'] = first_line or f"轮次{i+1}"
                
                conversation['rounds'].append(round_data)
        
        return conversation
    
    def parse_metadata(self, metadata_str: str) -> Dict:
        """解析元数据字符串"""
        metadata = {}
        parts = metadata_str.split('|')
        
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                metadata[key.strip()] = value.strip()
        
        return metadata
    
    def extract_title(self, content: str) -> str:
        """从内容中提取标题"""
        # 查找第一个一级标题
        match = self.patterns['title'].search(content)
        if match:
            return match.group(1)
        
        # 查找第一个有意义的行
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 10 and not line.startswith('#'):
                if len(line) > 50:
                    return line[:47] + '...'
                return line
        
        return f"对话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def parse_json(self, content: str) -> Optional[Dict]:
        """解析JSON内容"""
        try:
            data = json.loads(content)
            
            # 验证格式
            if isinstance(data, dict) and 'format' in data:
                return data
            elif isinstance(data, dict) and 'rounds' in data:
                data['format'] = 'json'
                return data
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                # 可能是消息列表
                conversation = {
                    'id': f"json_{int(time.time())}",
                    'format': 'json',
                    'rounds': [],
                    'parsed_from': 'json'
                }
                
                # 组织为轮次
                messages = data
                current_round = None
                
                for msg in messages:
                    if msg.get('role') == 'user':
                        if current_round:
                            conversation['rounds'].append(current_round)
                        
                        current_round = {
                            'number': len(conversation['rounds']) + 1,
                            'userInstruction': msg.get('content', ''),
                            'aiResponse': ''
                        }
                    elif msg.get('role') == 'assistant' and current_round:
                        if current_round['aiResponse']:
                            current_round['aiResponse'] += '\n\n' + msg.get('content', '')
                        else:
                            current_round['aiResponse'] = msg.get('content', '')
                
                if current_round:
                    conversation['rounds'].append(current_round)
                
                return conversation
        except:
            pass
        
        return None

# ============================================================================
# 内容分类器
# ============================================================================

class ContentClassifier:
    """内容分类器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.rules = {
            '工作相关': [
                '代码', '实现', '优化', 'bug', '部署', 'API', '函数', '类', '方法',
                'import', 'def ', 'class ', 'async', 'await', '数据库', '服务器',
                '配置', '调试', '测试', '编译', '运行', '错误', '异常', '日志'
            ],
            '学习探索': [
                '为什么', '如何', '原理', '解释', '概念', '理解', '学习', '教程',
                '指南', '介绍', '说明', '含义', '区别', '对比', '优点', '缺点',
                '历史', '发展', '背景', '基础', '进阶', '高级'
            ],
            '创意写作': [
                '故事', '诗歌', '创意', '想象', '描写', '创作', '小说', '散文',
                '剧本', '歌词', '情节', '角色', '设定', '世界观', '对话', '叙述',
                '文学', '艺术', '灵感', '想象力', '修辞', '比喻'
            ],
            '闲聊娱乐': [
                '哈哈', '有趣', '笑话', '天气', '推荐', '电影', '音乐', '游戏',
                '聊聊', '聊天', '休闲', '娱乐', '放松', '心情', '感受', '想法',
                '分享', '交流', '讨论', '观点', '看法', '意见'
            ]
        }
    
    def classify_conversation(self, conversation: Dict) -> Dict:
        """分类对话"""
        all_text = []
        
        # 收集所有文本
        if conversation.get('title'):
            all_text.append(conversation['title'])
        
        for round_data in conversation.get('rounds', []):
            all_text.append(round_data.get('userInstruction', ''))
            all_text.append(round_data.get('aiResponse', ''))
        
        full_text = ' '.join(all_text).lower()
        
        # 计算每个类别的得分
        scores = {}
        for category, keywords in self.rules.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in full_text:
                    score += 1
            
            # 加权：标题中的关键词权重更高
            title = conversation.get('title', '').lower()
            for keyword in keywords:
                if keyword.lower() in title:
                    score += 2
            
            scores[category] = score
        
        # 确定主要类别
        main_category = '未分类'
        max_score = 0
        
        for category, score in scores.items():
            if score > max_score:
                max_score = score
                main_category = category
        
        # 如果分数太低，标记为未分类
        if max_score < 2:
            main_category = '未分类'
        
        return {
            'main_category': main_category,
            'scores': scores,
            'confidence': max_score / (len(all_text) * 0.5) if all_text else 0
        }

# ============================================================================
# 内容格式化器
# ============================================================================

class ContentFormatter:
    """内容格式化器"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def format_markdown(self, conversation: Dict, options: Dict = None) -> str:
        """格式化为Markdown"""
        if options is None:
            options = {}
        
        include_metadata = options.get('include_metadata', self.config.settings['include_metadata'])
        include_markers = options.get('include_markers', self.config.settings['include_markers'])
        adjust_headings = options.get('adjust_headings', self.config.settings['auto_adjust_headings'])
        
        lines = []
        
        # 对话开始标记
        if include_markers:
            lines.append(f'<!-- 对话开始 {conversation.get("id", "unknown")} -->')
            
            if include_metadata:
                metadata_parts = []
                
                # 时间
                timestamp = conversation.get('saved_at') or conversation.get('timestamp')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        metadata_parts.append(f'时间:{dt.strftime("%Y-%m-%d %H:%M:%S")}')
                    except:
                        metadata_parts.append(f'时间:{timestamp}')
                
                # 分类
                category = conversation.get('main_category', '未分类')
                metadata_parts.append(f'主题:{category}')
                
                # 轮次
                rounds_count = len(conversation.get('rounds', []))
                metadata_parts.append(f'轮次:{rounds_count}')
                
                # 字数统计
                total_chars = self.calculate_total_chars(conversation)
                metadata_parts.append(f'字数:{total_chars}')
                
                if metadata_parts:
                    lines.append(f'<!-- 元数据: {" | ".join(metadata_parts)} -->')
            
            lines.append('')
        
        # 对话标题
        title = conversation.get('title', '未命名对话')
        lines.append(f'# {title}')
        lines.append('')
        
        # 元数据区域（如果不放在标记中）
        if include_metadata and not include_markers:
            lines.append('**对话信息**')
            lines.append('')
            
            timestamp = conversation.get('saved_at') or conversation.get('timestamp')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    lines.append(f'- **时间**: {dt.strftime("%Y年%m月%d日 %H:%M:%S")}')
                except:
                    lines.append(f'- **时间**: {timestamp}')
            
            category = conversation.get('main_category', '未分类')
            lines.append(f'- **分类**: {category}')
            
            rounds_count = len(conversation.get('rounds', []))
            lines.append(f'- **轮次**: {rounds_count}')
            
            stats = self.calculate_stats(conversation)
            lines.append(f'- **统计**: {stats["user_messages"]}条用户消息，{stats["ai_messages"]}条AI回复')
            lines.append(f'- **字数**: 用户{stats["user_chars"]}字，AI{stats["ai_chars"]}字')
            lines.append('')
            lines.append('---')
            lines.append('')
        
        # 处理每个轮次
        for i, round_data in enumerate(conversation.get('rounds', [])):
            round_num = i + 1
            
            # 轮次开始标记
            if include_markers:
                lines.append(f'<!-- 轮次开始 {round_num} -->')
            
            # 轮次标题
            round_title = round_data.get('title') or f'轮次{round_num}'
            lines.append(f'## {round_title}')
            lines.append('')
            
            # 用户指令
            lines.append('### 👤 我的指令')
            lines.append('')
            lines.append(round_data.get('userInstruction', ''))
            lines.append('')
            
            # AI输出开始标记
            if include_markers:
                lines.append('<!-- AI输出开始 -->')
            
            # AI输出
            lines.append('### 🤖 AI输出')
            lines.append('')
            
            ai_content = round_data.get('aiResponse', '')
            if adjust_headings:
                ai_content = self.adjust_headings(ai_content)
            
            lines.append(ai_content)
            lines.append('')
            
            # AI输出结束标记
            if include_markers:
                lines.append(f'<!-- AI输出结束 | 轮次结束 {round_num} -->')
            
            lines.append('---')
            lines.append('')
        
        # 对话结束标记
        if include_markers:
            lines.append(f'<!-- 对话结束 {conversation.get("id", "unknown")} -->')
        
        return '\n'.join(lines)
    
    def adjust_headings(self, content: str) -> str:
        """调整标题级别"""
        lines = content.split('\n')
        min_level = 6
        
        # 找到最低标题级别
        for line in lines:
            match = re.match(r'^(#{1,6})\s', line)
            if match:
                level = len(match.group(1))
                min_level = min(min_level, level)
        
        # 如果最低级别小于3，需要调整
        if min_level < 3:
            offset = 3 - min_level
            adjusted_lines = []
            
            for line in lines:
                match = re.match(r'^(#{1,6})\s(.+)$', line)
                if match:
                    level = len(match.group(1))
                    new_level = min(level + offset, 6)
                    title = match.group(2)
                    adjusted_lines.append('#' * new_level + ' ' + title)
                else:
                    adjusted_lines.append(line)
            
            return '\n'.join(adjusted_lines)
        
        return content
    
    def calculate_total_chars(self, conversation: Dict) -> int:
        """计算总字数"""
        total = 0
        
        if conversation.get('title'):
            total += len(conversation['title'])
        
        for round_data in conversation.get('rounds', []):
            total += len(round_data.get('userInstruction', ''))
            total += len(round_data.get('aiResponse', ''))
        
        return total
    
    def calculate_stats(self, conversation: Dict) -> Dict:
        """计算统计信息"""
        user_messages = 0
        ai_messages = 0
        user_chars = 0
        ai_chars = 0
        
        for round_data in conversation.get('rounds', []):
            user_messages += 1
            user_chars += len(round_data.get('userInstruction', ''))
            
            if round_data.get('aiResponse'):
                ai_messages += 1
                ai_chars += len(round_data['aiResponse'])
        
        return {
            'user_messages': user_messages,
            'ai_messages': ai_messages,
            'user_chars': user_chars,
            'ai_chars': ai_chars
        }

# ============================================================================
# 文件管理器
# ============================================================================

class FileManager:
    """文件管理器"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def save_conversation(self, conversation: Dict, category: str = None) -> Tuple[bool, Path]:
        """保存对话到文件"""
        if not category:
            category = conversation.get('main_category', 'other')
        
        # 确定目标目录
        category_key = self.map_category_to_key(category)
        target_dir = self.config.dirs.get(category_key, self.config.dirs['other'])
        
        # 生成文件名
        title = conversation.get('title', '未命名对话')
        safe_title = self.sanitize_filename(title)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.md"
        
        # 如果文件名太长，截断
        if len(filename) > 150:
            name_part = safe_title[:100]
            filename = f"{name_part}_{timestamp}.md"
        
        filepath = target_dir / filename
        
        # 格式化内容
        formatter = ContentFormatter(self.config)
        content = formatter.format_markdown(conversation)
        
        # 写入文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 创建备份
            if self.config.settings['backup_enabled']:
                self.create_backup(filepath)
            
            return True, filepath
        except Exception as e:
            print(f"保存文件失败: {e}")
            return False, None
    
    def map_category_to_key(self, category: str) -> str:
        """将分类映射到目录键"""
        mapping = {
            '工作相关': 'work',
            '学习探索': 'learning',
            '创意写作': 'creative',
            '闲聊娱乐': 'casual'
        }
        return mapping.get(category, 'other')
    
    def sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        # 移除非法字符
        illegal_chars = r'[<>:"/\\|?*\x00-\x1F]'
        filename = re.sub(illegal_chars, '_', filename)
        
        # 移除多余空格和换行
        filename = filename.replace('\n', ' ').replace('\r', ' ').strip()
        
        # 限制长度
        if len(filename) > 100:
            filename = filename[:97] + '...'
        
        return filename
    
    def create_backup(self, filepath: Path):
        """创建备份"""
        backup_dir = self.config.dirs['archive'] / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # 复制文件
        backup_name = f"{filepath.stem}_{int(time.time())}{filepath.suffix}"
        backup_path = backup_dir / backup_name
        
        try:
            shutil.copy2(filepath, backup_path)
            
            # 清理旧备份
            self.cleanup_old_backups(backup_dir)
        except Exception as e:
            print(f"创建备份失败: {e}")
    
    def cleanup_old_backups(self, backup_dir: Path):
        """清理旧备份"""
        backup_count = self.config.settings.get('backup_count', 10)
        
        # 获取所有备份文件
        backup_files = list(backup_dir.glob("*.md"))
        
        if len(backup_files) > backup_count:
            # 按修改时间排序
            backup_files.sort(key=lambda x: x.stat().st_mtime)
            
            # 删除最旧的
            files_to_delete = backup_files[:-backup_count]
            for file in files_to_delete:
                try:
                    file.unlink()
                except:
                    pass

# ============================================================================
# 主应用程序
# ============================================================================

class DeepseekManager:
    """Deepseek对话管理器主应用程序"""
    
    def __init__(self):
        self.config = Config()
        self.db = ConversationDB(self.config)
        self.parser = ContentParser(self.config)
        self.formatter = ContentFormatter(self.config)
        self.file_manager = FileManager(self.config)
        
        # 初始化命令行参数解析
        self.init_argparse()
    
    def init_argparse(self):
        """初始化命令行参数解析"""
        self.parser_obj = argparse.ArgumentParser(
            description='Deepseek对话专业处理工具 v3.0',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用示例:
  %(prog)s --clipboard           # 从剪贴板处理
  %(prog)s --file input.md       # 处理文件
  %(prog)s --batch ./conversations # 批量处理目录
  %(prog)s --search "Python异步"  # 搜索对话
  %(prog)s --stats               # 显示统计信息
  %(prog)s --gui                 # 启动图形界面
            """
        )
        
        # 输入源
        input_group = self.parser_obj.add_mutually_exclusive_group()
        input_group.add_argument('--clipboard', '-c', action='store_true',
                               help='从剪贴板读取内容')
        input_group.add_argument('--file', '-f', type=str,
                               help='从文件读取内容')
        input_group.add_argument('--batch', '-b', type=str,
                               help='批量处理目录')
        input_group.add_argument('--stdin', action='store_true',
                               help='从标准输入读取内容')
        
        # 操作模式
        self.parser_obj.add_argument('--save', '-s', action='store_true',
                                   help='保存到文件')
        self.parser_obj.add_argument('--search', type=str,
                                   help='搜索对话')
        self.parser_obj.add_argument('--stats', action='store_true',
                                   help='显示统计信息')
        self.parser_obj.add_argument('--list', '-l', action='store_true',
                                   help='列出所有对话')
        self.parser_obj.add_argument('--export', '-e', type=str,
                                   help='导出对话，参数为对话ID或"all"')
        self.parser_obj.add_argument('--delete', '-d', type=str,
                                   help='删除对话')
        self.parser_obj.add_argument('--gui', action='store_true',
                                   help='启动图形界面')
        
        # 输出选项
        self.parser_obj.add_argument('--output', '-o', type=str,
                                   help='输出文件路径')
        self.parser_obj.add_argument('--format', choices=['markdown', 'json'],
                                   help='输出格式')
        self.parser_obj.add_argument('--no-metadata', action='store_true',
                                   help='不包含元数据')
        self.parser_obj.add_argument('--no-markers', action='store_true',
                                   help='不包含标记点')
        self.parser_obj.add_argument('--no-adjust', action='store_true',
                                   help='不调整标题级别')
        
        # 其他选项
        self.parser_obj.add_argument('--verbose', '-v', action='store_true',
                                   help='详细输出')
        self.parser_obj.add_argument('--version', action='store_true',
                                   help='显示版本信息')
    
    def run(self):
        """运行应用程序"""
        args = self.parser_obj.parse_args()
        
        # 显示版本
        if args.version:
            print(f"Deepseek对话处理工具 v{self.config.settings['version']}")
            return
        
        # 显示统计
        if args.stats:
            self.show_stats()
            return
        
        # 列出对话
        if args.list:
            self.list_conversations()
            return
        
        # 搜索对话
        if args.search:
            self.search_conversations(args.search)
            return
        
        # 导出对话
        if args.export:
            self.export_conversation(args.export, args.output)
            return
        
        # 删除对话
        if args.delete:
            self.delete_conversation(args.delete)
            return
        
        # 启动图形界面
        if args.gui:
            self.start_gui()
            return
        
        # 处理输入
        content = self.get_input_content(args)
        if not content:
            print("错误: 未提供输入内容")
            self.parser_obj.print_help()
            return
        
        # 解析内容
        conversation = self.parse_content(content)
        if not conversation:
            print("错误: 无法解析对话内容")
            return
        
        # 显示预览
        self.preview_conversation(conversation)
        
        # 询问是否保存
        if args.save or self.ask_to_save():
            # 保存选项
            options = {
                'include_metadata': not args.no_metadata,
                'include_markers': not args.no_markers,
                'adjust_headings': not args.no_adjust
            }
            
            # 保存到文件
            success, filepath = self.save_conversation(conversation, options)
            if success:
                print(f"✅ 对话已保存到: {filepath}")
            else:
                print("❌ 保存失败")
    
    def get_input_content(self, args) -> Optional[str]:
        """获取输入内容"""
        if args.clipboard:
            try:
                import pyperclip
                return pyperclip.paste()
            except:
                print("错误: 无法访问剪贴板")
                return None
        
        elif args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"错误: 无法读取文件 {args.file}: {e}")
                return None
        
        elif args.batch:
            return self.process_batch(args.batch)
        
        elif args.stdin:
            return sys.stdin.read()
        
        return None
    
    def process_batch(self, directory: str) -> str:
        """批量处理目录"""
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"错误: 目录不存在 {directory}")
            return ""
        
        # 处理所有.md和.json文件
        processed = 0
        for filepath in dir_path.rglob('*'):
            if filepath.is_file() and filepath.suffix.lower() in ['.md', '.json', '.txt']:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    conversation = self.parse_content(content)
                    if conversation:
                        success, saved_path = self.save_conversation(conversation)
                        if success:
                            print(f"✅ 已处理: {filepath.name} -> {saved_path}")
                            processed += 1
                        else:
                            print(f"❌ 处理失败: {filepath.name}")
                    
                except Exception as e:
                    print(f"❌ 读取失败 {filepath.name}: {e}")
        
        print(f"\n✅ 批量处理完成，共处理 {processed} 个文件")
        return ""
    
    def parse_content(self, content: str) -> Optional[Dict]:
        """解析内容"""
        # 尝试JSON格式
        conversation = self.parser.parse_json(content)
        if conversation:
            return conversation
        
        # 尝试Markdown格式
        conversation = self.parser.parse_markdown(content)
        if conversation:
            return conversation
        
        return None
    
    def preview_conversation(self, conversation: Dict):
        """预览对话"""
        title = conversation.get('title', '未命名对话')
        category = conversation.get('main_category', '未分类')
        rounds = len(conversation.get('rounds', []))
        
        print("\n" + "="*60)
        print(f"📋 对话预览: {title}")
        print("="*60)
        print(f"📁 分类: {category}")
        print(f"🔄 轮次: {rounds}")
        print(f"🆔 ID: {conversation.get('id', 'N/A')}")
        print("-"*60)
        
        # 显示前3个轮次
        for i, round_data in enumerate(conversation.get('rounds', [])[:3]):
            print(f"\n轮次 {i+1}: {round_data.get('title', '')}")
            
            user_text = round_data.get('userInstruction', '')
            if len(user_text) > 100:
                user_text = user_text[:97] + '...'
            print(f"  👤 用户: {user_text}")
            
            ai_text = round_data.get('aiResponse', '')
            if len(ai_text) > 100:
                ai_text = ai_text[:97] + '...'
            print(f"  🤖 AI: {ai_text}")
        
        if len(conversation.get('rounds', [])) > 3:
            print(f"\n... 还有 {len(conversation.get('rounds', [])) - 3} 个轮次未显示")
        
        print("="*60)
    
    def ask_to_save(self) -> bool:
        """询问是否保存"""
        while True:
            response = input("\n💾 是否保存此对话? (y/n): ").strip().lower()
            if response in ['y', 'yes', '是']:
                return True
            elif response in ['n', 'no', '否']:
                return False
            else:
                print("请输入 y/n 或 是/否")
    
    def save_conversation(self, conversation: Dict, options: Dict = None) -> Tuple[bool, Optional[Path]]:
        """保存对话"""
        if options is None:
            options = {}
        
        # 添加到数据库
        conv_id = self.db.add_conversation(conversation)
        conversation['id'] = conv_id
        
        # 保存到文件
        success, filepath = self.file_manager.save_conversation(conversation)
        
        return success, filepath
    
    def show_stats(self):
        """显示统计信息"""
        stats = self.db.get_stats()
        
        print("\n" + "="*60)
        print("📊 Deepseek对话统计")
        print("="*60)
        print(f"📁 总对话数: {stats.get('total', 0)}")
        
        # 分类统计
        if stats.get('by_category'):
            print("\n📂 分类统计:")
            for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {category}: {count}")
        
        # 月度统计
        if stats.get('by_month'):
            print("\n📅 月度统计:")
            for month, count in sorted(stats['by_month'].items(), reverse=True)[:6]:
                print(f"  {month}: {count}")
        
        print("="*60)
        
        # 数据库文件信息
        db_size = self.config.db_file.stat().st_size if self.config.db_file.exists() else 0
        print(f"💾 数据库大小: {db_size / 1024:.1f} KB")
        print(f"📁 输出目录: {self.config.output_base}")
    
    def list_conversations(self, limit: int = 20):
        """列出对话"""
        conversations = self.db.data.get('conversations', [])
        
        print("\n" + "="*80)
        print(f"📋 对话列表 (共 {len(conversations)} 个)")
        print("="*80)
        
        if not conversations:
            print("暂无对话")
            return
        
        # 按时间倒序排列
        sorted_conv = sorted(conversations, 
                           key=lambda x: x.get('saved_at', ''), 
                           reverse=True)[:limit]
        
        for i, conv in enumerate(sorted_conv, 1):
            title = conv.get('title', '未命名对话')
            category = conv.get('main_category', '未分类')
            rounds = len(conv.get('rounds', []))
            conv_id = conv.get('id', 'N/A')
            
            # 时间
            timestamp = conv.get('saved_at', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = timestamp[:16]
            else:
                time_str = "未知时间"
            
            print(f"{i:2d}. {title}")
            print(f"    📁 {category} | 🔄 {rounds}轮 | 🕐 {time_str} | 🆔 {conv_id[:12]}...")
            
            # 显示第一个用户指令的预览
            if conv.get('rounds'):
                first_instruction = conv['rounds'][0].get('userInstruction', '')
                if len(first_instruction) > 80:
                    first_instruction = first_instruction[:77] + '...'
                print(f"    💬 {first_instruction}")
            
            print()
        
        if len(conversations) > limit:
            print(f"... 还有 {len(conversations) - limit} 个对话未显示")
        
        print("="*80)
    
    def search_conversations(self, query: str):
        """搜索对话"""
        print(f"\n🔍 搜索: '{query}'")
        print("-"*60)
        
        results = self.db.search(query)
        
        if not results:
            print("未找到相关对话")
            return
        
        print(f"找到 {len(results)} 个相关对话:\n")
        
        for i, conv in enumerate(results, 1):
            title = conv.get('title', '未命名对话')
            category = conv.get('main_category', '未分类')
            score = conv.get('relevance_score', 0)
            
            print(f"{i}. {title}")
            print(f"   匹配度: {'★' * min(5, score)} | 分类: {category}")
            
            # 显示相关片段
            snippet = self.find_relevant_snippet(conv, query)
            if snippet:
                print(f"   相关: {snippet}")
            
            print()
    
    def find_relevant_snippet(self, conversation: Dict, query: str) -> str:
        """查找相关片段"""
        query_words = query.lower().split()
        
        for round_data in conversation.get('rounds', []):
            text = round_data.get('userInstruction', '') + ' ' + round_data.get('aiResponse', '')
            text_lower = text.lower()
            
            # 检查是否包含查询词
            for word in query_words:
                if word in text_lower:
                    # 找到包含查询词的句子
                    sentences = re.split(r'[。！？.!?]', text)
                    for sentence in sentences:
                        if word in sentence.lower():
                            if len(sentence) > 100:
                                return sentence[:97] + '...'
                            return sentence
        
        return ''
    
    def export_conversation(self, conv_id: str, output_path: str = None):
        """导出对话"""
        if conv_id.lower() == 'all':
            self.export_all_conversations(output_path)
            return
        
        # 查找对话
        conversation = None
        for conv in self.db.data.get('conversations', []):
            if conv.get('id') == conv_id:
                conversation = conv
                break
        
        if not conversation:
            print(f"错误: 未找到对话 {conv_id}")
            return
        
        # 格式化
        content = self.formatter.format_markdown(conversation)
        
        # 确定输出路径
        if output_path:
            filepath = Path(output_path)
        else:
            title = self.file_manager.sanitize_filename(conversation.get('title', '对话'))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = Path(f"{title}_export_{timestamp}.md")
        
        # 写入文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 对话已导出到: {filepath}")
        except Exception as e:
            print(f"❌ 导出失败: {e}")
    
    def export_all_conversations(self, output_dir: str = None):
        """导出所有对话"""
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True, parents=True)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"deepseek_export_{timestamp}")
            output_path.mkdir()
        
        conversations = self.db.data.get('conversations', [])
        
        print(f"\n📤 正在导出 {len(conversations)} 个对话到 {output_path}")
        
        success_count = 0
        for conv in conversations:
            content = self.formatter.format_markdown(conv)
            
            title = self.file_manager.sanitize_filename(conv.get('title', '对话'))
            conv_id = conv.get('id', 'unknown')[:8]
            filename = f"{title}_{conv_id}.md"
            filepath = output_path / filename
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                success_count += 1
            except Exception as e:
                print(f"❌ 导出失败 {filename}: {e}")
        
        print(f"✅ 导出完成，成功 {success_count}/{len(conversations)} 个对话")
    
    def delete_conversation(self, conv_id: str):
        """删除对话"""
        if conv_id.lower() == 'all':
            response = input("确定要删除所有对话吗？此操作不可恢复！(y/n): ")
            if response.lower() == 'y':
                self.db.data['conversations'] = []
                self.db.save_db()
                print("✅ 所有对话已删除")
            return
        
        # 查找对话
        conversation = None
        for conv in self.db.data.get('conversations', []):
            if conv.get('id') == conv_id:
                conversation = conv
                break
        
        if not conversation:
            print(f"错误: 未找到对话 {conv_id}")
            return
        
        # 确认删除
        title = conversation.get('title', '未命名对话')
        response = input(f"确定要删除对话 '{title}' 吗？(y/n): ")
        
        if response.lower() == 'y':
            success = self.db.delete_conversation(conv_id)
            if success:
                print("✅ 对话已删除")
            else:
                print("❌ 删除失败")
    
    def start_gui(self):
        """启动图形界面"""
        try:
            import tkinter as tk
            from tkinter import ttk, messagebox, scrolledtext
            import threading
            
            class DeepseekGUI:
                def __init__(self, manager):
                    self.manager = manager
                    self.root = tk.Tk()
                    self.root.title(f"Deepseek对话管理器 v{manager.config.settings['version']}")
                    self.root.geometry("1000x700")
                    
                    self.setup_ui()
                
                def setup_ui(self):
                    """设置UI"""
                    # 菜单栏
                    menubar = tk.Menu(self.root)
                    self.root.config(menu=menubar)
                    
                    # 文件菜单
                    file_menu = tk.Menu(menubar, tearoff=0)
                    menubar.add_cascade(label="文件", menu=file_menu)
                    file_menu.add_command(label="从剪贴板导入", command=self.import_from_clipboard)
                    file_menu.add_command(label="从文件导入", command=self.import_from_file)
                    file_menu.add_separator()
                    file_menu.add_command(label="导出所有", command=self.export_all)
                    file_menu.add_separator()
                    file_menu.add_command(label="退出", command=self.root.quit)
                    
                    # 编辑菜单
                    edit_menu = tk.Menu(menubar, tearoff=0)
                    menubar.add_cascade(label="编辑", menu=edit_menu)
                    edit_menu.add_command(label="设置", command=self.open_settings)
                    
                    # 帮助菜单
                    help_menu = tk.Menu(menubar, tearoff=0)
                    menubar.add_cascade(label="帮助", menu=help_menu)
                    help_menu.add_command(label="关于", command=self.show_about)
                    
                    # 主框架
                    main_frame = ttk.Frame(self.root, padding="10")
                    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
                    
                    # 配置网格权重
                    self.root.columnconfigure(0, weight=1)
                    self.root.rowconfigure(0, weight=1)
                    main_frame.columnconfigure(1, weight=1)
                    main_frame.rowconfigure(1, weight=1)
                    
                    # 工具栏
                    toolbar = ttk.Frame(main_frame)
                    toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
                    
                    ttk.Button(toolbar, text="📋 剪贴板导入", command=self.import_from_clipboard).pack(side=tk.LEFT, padx=2)
                    ttk.Button(toolbar, text="📁 文件导入", command=self.import_from_file).pack(side=tk.LEFT, padx=2)
                    ttk.Button(toolbar, text="🔍 搜索", command=self.open_search).pack(side=tk.LEFT, padx=2)
                    ttk.Button(toolbar, text="📊 统计", command=self.show_stats_gui).pack(side=tk.LEFT, padx=2)
                    
                    # 左侧列表
                    list_frame = ttk.LabelFrame(main_frame, text="对话列表", padding="5")
                    list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
                    
                    # 搜索框
                    search_frame = ttk.Frame(list_frame)
                    search_frame.pack(fill=tk.X, pady=(0, 5))
                    
                    self.search_var = tk.StringVar()
                    self.search_var.trace('w', self.on_search_change)
                    ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
                    ttk.Button(search_frame, text="🔍", width=3, command=self.do_search).pack(side=tk.LEFT, padx=(5, 0))
                    
                    # 列表和滚动条
                    list_container = ttk.Frame(list_frame)
                    list_container.pack(fill=tk.BOTH, expand=True)
                    
                    scrollbar = ttk.Scrollbar(list_container)
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    self.conversation_list = tk.Listbox(list_container, yscrollcommand=scrollbar.set,
                                                       font=('TkDefaultFont', 10))
                    self.conversation_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                    scrollbar.config(command=self.conversation_list.yview)
                    
                    self.conversation_list.bind('<<ListboxSelect>>', self.on_conversation_select)
                    self.conversation_list.bind('<Double-Button-1>', self.on_conversation_double_click)
                    
                    # 列表按钮
                    button_frame = ttk.Frame(list_frame)
                    button_frame.pack(fill=tk.X, pady=(5, 0))
                    
                    ttk.Button(button_frame, text="刷新", command=self.refresh_list).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
                    ttk.Button(button_frame, text="删除", command=self.delete_selected).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
                    
                    # 右侧详情
                    detail_frame = ttk.LabelFrame(main_frame, text="对话详情", padding="10")
                    detail_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
                    detail_frame.columnconfigure(0, weight=1)
                    detail_frame.rowconfigure(1, weight=1)
                    
                    # 标题和基本信息
                    info_frame = ttk.Frame(detail_frame)
                    info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
                    
                    self.title_label = ttk.Label(info_frame, text="未选择对话", font=('TkDefaultFont', 12, 'bold'))
                    self.title_label.pack(anchor=tk.W)
                    
                    self.info_label = ttk.Label(info_frame, text="")
                    self.info_label.pack(anchor=tk.W)
                    
                    # 内容显示
                    text_frame = ttk.Frame(detail_frame)
                    text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
                    text_frame.columnconfigure(0, weight=1)
                    text_frame.rowconfigure(0, weight=1)
                    
                    self.content_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('TkFixedFont', 10))
                    self.content_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
                    
                    # 底部按钮
                    button_frame2 = ttk.Frame(detail_frame)
                    button_frame2.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
                    
                    ttk.Button(button_frame2, text="保存到文件", command=self.save_selected).pack(side=tk.LEFT, padx=(0, 5))
                    ttk.Button(button_frame2, text="复制到剪贴板", command=self.copy_selected).pack(side=tk.LEFT)
                    
                    # 状态栏
                    self.status_var = tk.StringVar(value="就绪")
                    status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
                    status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
                    
                    # 初始加载
                    self.refresh_list()
                
                def import_from_clipboard(self):
                    """从剪贴板导入"""
                    try:
                        import pyperclip
                        content = pyperclip.paste()
                        
                        if not content.strip():
                            messagebox.showwarning("警告", "剪贴板为空")
                            return
                        
                        self.process_content(content, "剪贴板")
                    except Exception as e:
                        messagebox.showerror("错误", f"导入失败: {e}")
                
                def import_from_file(self):
                    """从文件导入"""
                    from tkinter import filedialog
                    
                    filepath = filedialog.askopenfilename(
                        title="选择对话文件",
                        filetypes=[
                            ("所有文件", "*.*"),
                            ("Markdown文件", "*.md"),
                            ("JSON文件", "*.json"),
                            ("文本文件", "*.txt")
                        ]
                    )
                    
                    if not filepath:
                        return
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        self.process_content(content, f"文件: {Path(filepath).name}")
                    except Exception as e:
                        messagebox.showerror("错误", f"读取文件失败: {e}")
                
                def process_content(self, content: str, source: str):
                    """处理内容"""
                    def worker():
                        self.status_var.set(f"正在处理内容...")
                        
                        conversation = self.manager.parse_content(content)
                        if conversation:
                            # 保存到数据库
                            self.manager.save_conversation(conversation)
                            
                            # 刷新列表
                            self.refresh_list()
                            
                            # 选择新添加的对话
                            self.select_conversation(conversation.get('id'))
                            
                            self.status_var.set(f"✅ 已从{source}导入对话")
                            messagebox.showinfo("成功", f"对话已成功导入")
                        else:
                            self.status_var.set("❌ 无法解析内容")
                            messagebox.showerror("错误", "无法解析对话内容")
                    
                    # 在新线程中处理
                    thread = threading.Thread(target=worker)
                    thread.daemon = True
                    thread.start()
                
                def refresh_list(self):
                    """刷新列表"""
                    conversations = self.manager.db.data.get('conversations', [])
                    
                    self.conversation_list.delete(0, tk.END)
                    
                    for conv in conversations:
                        title = conv.get('title', '未命名对话')
                        category = conv.get('main_category', '未分类')
                        rounds = len(conv.get('rounds', []))
                        
                        # 时间
                        timestamp = conv.get('saved_at', '')
                        if timestamp:
                            try:
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                time_str = dt.strftime("%m-%d %H:%M")
                            except:
                                time_str = timestamp[:10]
                        else:
                            time_str = "未知"
                        
                        display_text = f"{title} [{category}] ({rounds}轮, {time_str})"
                        self.conversation_list.insert(tk.END, display_text)
                        self.conversation_list.itemconfig(tk.END, {'data': conv.get('id')})
                    
                    self.status_var.set(f"共 {len(conversations)} 个对话")
                
                def on_conversation_select(self, event):
                    """对话选择事件"""
                    selection = self.conversation_list.curselection()
                    if not selection:
                        return
                    
                    index = selection[0]
                    conv_id = self.conversation_list.itemcget(index, 'data')
                    
                    # 查找对话
                    conversation = None
                    for conv in self.manager.db.data.get('conversations', []):
                        if conv.get('id') == conv_id:
                            conversation = conv
                            break
                    
                    if conversation:
                        self.show_conversation_details(conversation)
                
                def on_conversation_double_click(self, event):
                    """对话双击事件"""
                    selection = self.conversation_list.curselection()
                    if not selection:
                        return
                    
                    self.save_selected()
                
                def show_conversation_details(self, conversation: Dict):
                    """显示对话详情"""
                    title = conversation.get('title', '未命名对话')
                    category = conversation.get('main_category', '未分类')
                    rounds = len(conversation.get('rounds', []))
                    conv_id = conversation.get('id', 'N/A')
                    
                    # 时间
                    timestamp = conversation.get('saved_at', '')
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            time_str = timestamp
                    else:
                        time_str = "未知时间"
                    
                    self.title_label.config(text=title)
                    
                    info_text = f"分类: {category} | 轮次: {rounds} | 时间: {time_str}\nID: {conv_id}"
                    self.info_label.config(text=info_text)
                    
                    # 格式化内容
                    content = self.manager.formatter.format_markdown(conversation)
                    self.content_text.delete(1.0, tk.END)
                    self.content_text.insert(1.0, content)
                
                def select_conversation(self, conv_id: str):
                    """选择指定对话"""
                    for i in range(self.conversation_list.size()):
                        if self.conversation_list.itemcget(i, 'data') == conv_id:
                            self.conversation_list.selection_clear(0, tk.END)
                            self.conversation_list.selection_set(i)
                            self.conversation_list.see(i)
                            self.on_conversation_select(None)
                            break
                
                def save_selected(self):
                    """保存选中的对话"""
                    selection = self.conversation_list.curselection()
                    if not selection:
                        messagebox.showwarning("警告", "请先选择对话")
                        return
                    
                    index = selection[0]
                    conv_id = self.conversation_list.itemcget(index, 'data')
                    
                    # 查找对话
                    conversation = None
                    for conv in self.manager.db.data.get('conversations', []):
                        if conv.get('id') == conv_id:
                            conversation = conv
                            break
                    
                    if not conversation:
                        messagebox.showerror("错误", "未找到对话")
                        return
                    
                    # 保存到文件
                    success, filepath = self.manager.save_conversation(conversation)
                    if success:
                        messagebox.showinfo("成功", f"对话已保存到:\n{filepath}")
                    else:
                        messagebox.showerror("错误", "保存失败")
                
                def copy_selected(self):
                    """复制选中的对话到剪贴板"""
                    selection = self.conversation_list.curselection()
                    if not selection:
                        messagebox.showwarning("警告", "请先选择对话")
                        return
                    
                    index = selection[0]
                    conv_id = self.conversation_list.itemcget(index, 'data')
                    
                    # 查找对话
                    conversation = None
                    for conv in self.manager.db.data.get('conversations', []):
                        if conv.get('id') == conv_id:
                            conversation = conv
                            break
                    
                    if not conversation:
                        messagebox.showerror("错误", "未找到对话")
                        return
                    
                    # 格式化并复制
                    content = self.manager.formatter.format_markdown(conversation)
                    
                    try:
                        import pyperclip
                        pyperclip.copy(content)
                        self.status_var.set("✅ 内容已复制到剪贴板")
                    except Exception as e:
                        messagebox.showerror("错误", f"复制失败: {e}")
                
                def delete_selected(self):
                    """删除选中的对话"""
                    selection = self.conversation_list.curselection()
                    if not selection:
                        messagebox.showwarning("警告", "请先选择对话")
                        return
                    
                    index = selection[0]
                    conv_id = self.conversation_list.itemcget(index, 'data')
                    
                    # 查找对话
                    conversation = None
                    for conv in self.manager.db.data.get('conversations', []):
                        if conv.get('id') == conv_id:
                            conversation = conv
                            break
                    
                    if not conversation:
                        messagebox.showerror("错误", "未找到对话")
                        return
                    
                    title = conversation.get('title', '未命名对话')
                    response = messagebox.askyesno("确认删除", f"确定要删除对话 '{title}' 吗？")
                    
                    if response:
                        success = self.manager.db.delete_conversation(conv_id)
                        if success:
                            self.refresh_list()
                            self.content_text.delete(1.0, tk.END)
                            self.title_label.config(text="未选择对话")
                            self.info_label.config(text="")
                            self.status_var.set("✅ 对话已删除")
                        else:
                            messagebox.showerror("错误", "删除失败")
                
                def do_search(self):
                    """执行搜索"""
                    query = self.search_var.get().strip()
                    if not query:
                        self.refresh_list()
                        return
                    
                    results = self.manager.db.search(query)
                    
                    self.conversation_list.delete(0, tk.END)
                    
                    for conv in results:
                        title = conv.get('title', '未命名对话')
                        category = conv.get('main_category', '未分类')
                        rounds = len(conv.get('rounds', []))
                        score = conv.get('relevance_score', 0)
                        
                        display_text = f"{title} [{category}] ({rounds}轮, 匹配度:{score})"
                        self.conversation_list.insert(tk.END, display_text)
                        self.conversation_list.itemconfig(tk.END, {'data': conv.get('id')})
                    
                    self.status_var.set(f"找到 {len(results)} 个相关对话")
                
                def on_search_change(self, *args):
                    """搜索框内容变化事件"""
                    # 可以在这里实现实时搜索
                    pass
                
                def open_search(self):
                    """打开搜索窗口"""
                    search_window = tk.Toplevel(self.root)
                    search_window.title("高级搜索")
                    search_window.geometry("600x400")
                    
                    ttk.Label(search_window, text="搜索关键词:").pack(anchor=tk.W, padx=20, pady=(20, 5))
                    
                    search_entry = ttk.Entry(search_window, width=50)
                    search_entry.pack(padx=20, pady=(0, 20))
                    search_entry.focus()
                    
                    # 搜索按钮
                    def perform_search():
                        query = search_entry.get().strip()
                        if not query:
                            return
                        
                        results = self.manager.db.search(query)
                        
                        # 显示结果
                        result_text = scrolledtext.ScrolledText(search_window, wrap=tk.WORD)
                        result_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
                        
                        if not results:
                            result_text.insert(1.0, "未找到相关对话")
                        else:
                            result_text.insert(1.0, f"找到 {len(results)} 个相关对话:\n\n")
                            
                            for i, conv in enumerate(results, 1):
                                title = conv.get('title', '未命名对话')
                                category = conv.get('main_category', '未分类')
                                score = conv.get('relevance_score', 0)
                                
                                result_text.insert(tk.END, f"{i}. {title}\n")
                                result_text.insert(tk.END, f"   分类: {category} | 匹配度: {'★' * min(5, score)}\n\n")
                    
                    ttk.Button(search_window, text="搜索", command=perform_search).pack(pady=(0, 20))
                
                def show_stats_gui(self):
                    """显示统计信息"""
                    stats = self.manager.db.get_stats()
                    
                    stats_window = tk.Toplevel(self.root)
                    stats_window.title("统计信息")
                    stats_window.geometry("400x500")
                    
                    stats_text = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
                    stats_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                    
                    stats_text.insert(1.0, "📊 Deepseek对话统计\n")
                    stats_text.insert(tk.END, "="*40 + "\n\n")
                    
                    stats_text.insert(tk.END, f"📁 总对话数: {stats.get('total', 0)}\n\n")
                    
                    # 分类统计
                    if stats.get('by_category'):
                        stats_text.insert(tk.END, "📂 分类统计:\n")
                        for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
                            stats_text.insert(tk.END, f"  {category}: {count}\n")
                        stats_text.insert(tk.END, "\n")
                    
                    # 月度统计
                    if stats.get('by_month'):
                        stats_text.insert(tk.END, "📅 月度统计 (最近6个月):\n")
                        for month, count in sorted(stats['by_month'].items(), reverse=True)[:6]:
                            stats_text.insert(tk.END, f"  {month}: {count}\n")
                    
                    stats_text.config(state=tk.DISABLED)
                
                def export_all(self):
                    """导出所有对话"""
                    from tkinter import filedialog
                    
                    dir_path = filedialog.askdirectory(title="选择导出目录")
                    if not dir_path:
                        return
                    
                    self.manager.export_all_conversations(dir_path)
                    messagebox.showinfo("成功", f"所有对话已导出到:\n{dir_path}")
                
                def open_settings(self):
                    """打开设置窗口"""
                    settings_window = tk.Toplevel(self.root)
                    settings_window.title("设置")
                    settings_window.geometry("500x400")
                    
                    # 创建设置选项
                    notebook = ttk.Notebook(settings_window)
                    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    
                    # 常规设置
                    general_frame = ttk.Frame(notebook, padding=10)
                    notebook.add(general_frame, text="常规")
                    
                    row = 0
                    
                    # 自动分类
                    auto_classify_var = tk.BooleanVar(value=self.manager.config.settings['auto_classify'])
                    ttk.Checkbutton(general_frame, text="自动分类对话", variable=auto_classify_var).grid(row=row, column=0, sticky=tk.W, pady=5)
                    row += 1
                    
                    # 自动调整标题
                    auto_adjust_var = tk.BooleanVar(value=self.manager.config.settings['auto_adjust_headings'])
                    ttk.Checkbutton(general_frame, text="自动调整标题级别", variable=auto_adjust_var).grid(row=row, column=0, sticky=tk.W, pady=5)
                    row += 1
                    
                    # 包含元数据
                    include_meta_var = tk.BooleanVar(value=self.manager.config.settings['include_metadata'])
                    ttk.Checkbutton(general_frame, text="包含元数据", variable=include_meta_var).grid(row=row, column=0, sticky=tk.W, pady=5)
                    row += 1
                    
                    # 包含标记点
                    include_markers_var = tk.BooleanVar(value=self.manager.config.settings['include_markers'])
                    ttk.Checkbutton(general_frame, text="包含标记点", variable=include_markers_var).grid(row=row, column=0, sticky=tk.W, pady=5)
                    row += 1
                    
                    # 输出格式
                    format_frame = ttk.Frame(general_frame)
                    format_frame.grid(row=row, column=0, sticky=tk.W, pady=5)
                    row += 1
                    
                    ttk.Label(format_frame, text="默认输出格式:").pack(side=tk.LEFT, padx=(0, 10))
                    
                    format_var = tk.StringVar(value=self.manager.config.settings['output_format'])
                    ttk.Radiobutton(format_frame, text="Markdown", variable=format_var, value="markdown").pack(side=tk.LEFT, padx=(0, 10))
                    ttk.Radiobutton(format_frame, text="JSON", variable=format_var, value="json").pack(side=tk.LEFT)
                    
                    # 保存设置按钮
                    def save_settings():
                        self.manager.config.settings['auto_classify'] = auto_classify_var.get()
                        self.manager.config.settings['auto_adjust_headings'] = auto_adjust_var.get()
                        self.manager.config.settings['include_metadata'] = include_meta_var.get()
                        self.manager.config.settings['include_markers'] = include_markers_var.get()
                        self.manager.config.settings['output_format'] = format_var.get()
                        
                        self.manager.config.save_settings()
                        messagebox.showinfo("成功", "设置已保存")
                        settings_window.destroy()
                    
                    ttk.Button(general_frame, text="保存设置", command=save_settings).grid(row=row, column=0, pady=20)
                
                def show_about(self):
                    """显示关于信息"""
                    about_text = f"""Deepseek对话管理器 v{self.manager.config.settings['version']}

一个专业的Deepseek对话提取、管理和保存工具。

功能特性:
• 智能提取和解析对话内容
• 自动分类和标记对话
• 结构化保存为Markdown格式
• 强大的搜索和检索功能
• 桌面级用户体验

数据库位置: {self.manager.config.db_file}
输出目录: {self.manager.config.output_base}
"""
                    
                    messagebox.showinfo("关于", about_text)
                
                def run(self):
                    """运行GUI"""
                    self.root.mainloop()
            
            # 启动GUI
            gui = DeepseekGUI(self)
            gui.run()
            
        except ImportError as e:
            print("错误: 需要Tkinter支持才能启动GUI界面")
            print("在Windows/macOS上，Tkinter通常已预装")
            print("在Linux上，请安装python3-tk包")
            return

# ============================================================================
# 主入口
# ============================================================================

def main():
    """主函数"""
    try:
        manager = DeepseekManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n\n程序已终止")
    except Exception as e:
        print(f"\n程序出错: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()