"""
core/conversation_builder.py
对话构建器 - 构建符合优化格式的对话结构
"""
import re
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

from utils.logger import logger


class ConversationBuilder:
    """构建符合优化格式的对话结构"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logger
        
        # 关键词提取配置
        self.keyword_config = {
            'min_word_length': 2,
            'max_keywords': 5,
            'exclude_words': [
                '请问', '如何', '怎么', '什么', '为什么', '哪个', '哪些',
                '帮忙', '帮助', '一下', '一个', '这个', '那个',
                '你好', '谢谢', '抱歉', '对不起', '请问'
            ]
        }
        
        # 对话ID生成配置
        self.id_config = {
            'prefix': 'V',
            'start_number': 1,
            'digits': 3
        }
        
        # 标题生成配置
        self.title_config = self.config.get('output', {}).get('title_format', '[{dialog_id}-{round_id}] {keywords}')
        
        # 初始化计数器
        self.dialog_counter = self.id_config.get('start_number', 1)
        
    def build(self, parsed_data: Dict[str, Any], dialog_id: Optional[str] = None) -> Dict[str, Any]:
        """
        构建对话结构，包含：
        1. 为每个轮次生成唯一ID
        2. 提取关键词用于标题
        3. 分析内容结构（代码块、标题等）
        
        返回结构：
        {
            'dialog_id': 'V001',
            'metadata': {
                'total_rounds': 5,
                'technical_rounds': 4,
                'title_keywords': 'python 异步编程 示例',
                'created_at': '2024-01-24T10:30:00',
                'source_file': 'conversation.html'
            },
            'rounds': [
                {
                    'round_id': 'V001-1',
                    'user': {
                        'content': '...',
                        'timestamp': '...',
                        'keywords': ['python', '异步', '示例'],
                        'has_code': False,
                        'word_count': 45
                    },
                    'ai': {
                        'content': '...',
                        'timestamp': '...',
                        'keywords': ['async', 'await', '协程'],
                        'has_code': True,
                        'code_blocks': 2,
                        'headings': ['## 异步编程基础', '### async/await用法'],
                        'word_count': 350
                    },
                    'metadata': {
                        'is_technical': True,
                        'main_topic': '异步编程',
                        'estimated_read_time': '3分钟'
                    }
                }
            ]
        }
        """
        try:
            self.logger.info("开始构建对话结构...")
            
            # 生成对话ID
            dialog_id = dialog_id or self._generate_dialog_id()
            self.logger.debug(f"对话ID: {dialog_id}")
            
            # 提取元数据
            metadata = self._extract_metadata(parsed_data, dialog_id)
            
            # 构建轮次
            rounds = []
            for i, round_data in enumerate(parsed_data.get('rounds', [])):
                round_num = i + 1
                
                # 跳过无效轮次
                if not self._is_valid_round(round_data):
                    self.logger.debug(f"跳过无效轮次 {round_num}")
                    continue
                
                # 格式化轮次
                formatted_round = self._format_round(round_data, dialog_id, round_num)
                if formatted_round:
                    rounds.append(formatted_round)
            
            # 更新元数据
            metadata.update({
                'total_rounds': len(rounds),
                'technical_rounds': sum(1 for r in rounds if r['metadata']['is_technical']),
                'title_keywords': self._extract_dialog_keywords(rounds),
                'created_at': datetime.now().isoformat()
            })
            
            conversation = {
                'dialog_id': dialog_id,
                'metadata': metadata,
                'rounds': rounds
            }
            
            self.logger.info(f"对话构建完成，共 {len(rounds)} 个有效轮次")
            self.logger.info(f"技术对话轮次: {metadata['technical_rounds']}")
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"构建对话结构失败: {e}")
            raise
    
    def _generate_dialog_id(self) -> str:
        """生成对话ID"""
        prefix = self.id_config.get('prefix', 'V')
        digits = self.id_config.get('digits', 3)
        
        # 生成数字部分
        dialog_number = self.dialog_counter
        self.dialog_counter += 1
        
        # 格式化为固定位数
        number_str = str(dialog_number).zfill(digits)
        
        return f"{prefix}{number_str}"
    
    def _extract_metadata(self, parsed_data: Dict[str, Any], dialog_id: str) -> Dict[str, Any]:
        """从解析数据中提取元数据"""
        metadata = parsed_data.get('metadata', {}).copy()
        
        # 添加对话ID
        metadata['dialog_id'] = dialog_id
        
        # 添加基础统计
        total_rounds = len(parsed_data.get('rounds', []))
        metadata['total_rounds_raw'] = total_rounds
        
        # 估计总字数
        total_words = 0
        for round_data in parsed_data.get('rounds', []):
            user_content = round_data.get('user', {}).get('content', '')
            ai_content = round_data.get('ai', {}).get('content', '')
            total_words += len(user_content.split()) + len(ai_content.split())
        
        metadata['estimated_total_words'] = total_words
        
        return metadata
    
    def _is_valid_round(self, round_data: Dict[str, Any]) -> bool:
        """判断轮次是否有效"""
        if not round_data:
            return False
        
        user_content = round_data.get('user', {}).get('content', '')
        ai_content = round_data.get('ai', {}).get('content', '')
        
        # 检查内容是否为空
        if not user_content.strip() or not ai_content.strip():
            return False
        
        # 检查是否为技术对话
        return self._is_technical_conversation(user_content, ai_content)
    
    def _is_technical_conversation(self, user_content: str, ai_content: str) -> bool:
        """判断是否是技术对话"""
        # 排除模式
        exclusion_patterns = [
            r'^你好$', r'^谢谢$', r'^再见$', r'^好的$', r'^明白了$',
            r'哈哈+', r'呵呵+', r'嘿嘿+',
            r'请帮我.*测试', r'测试一下', r'随便问问',
            r'^[\s\W]*$',  # 只有标点和空格
        ]
        
        # 检查用户问题
        user_lower = user_content.lower()
        for pattern in exclusion_patterns:
            if re.search(pattern, user_lower, re.IGNORECASE):
                return False
        
        # 检查AI回答是否有技术内容
        technical_indicators = [
            '```',  # 代码块
            '##',   # 二级标题
            '###',  # 三级标题
            '1.', '2.', '3.',  # 编号列表
            '- ', '* ',  # 无序列表
            '步骤', '方法', '配置', '代码', '示例',
            '参数', '函数', '变量', '类', '对象',
            '安装', '部署', '配置', '优化', '调试',
            'python', 'java', 'javascript', 'html', 'css',
            'docker', 'kubernetes', 'database', 'api',
        ]
        
        ai_lower = ai_content.lower()
        for indicator in technical_indicators:
            if indicator.lower() in ai_lower:
                return True
        
        # 较长的回答通常有内容
        return len(ai_content.strip()) > 100
    
    def _format_round(self, round_data: Dict[str, Any], dialog_id: str, round_num: int) -> Optional[Dict[str, Any]]:
        """格式化单个轮次"""
        try:
            round_id = f"{dialog_id}-{round_num}"
            
            # 处理用户内容
            user_data = self._analyze_content(round_data['user']['content'], 'user')
            user_data.update({
                'timestamp': round_data['user'].get('timestamp'),
                'raw_html': round_data['user'].get('raw_html', '')
            })
            
            # 处理AI内容
            ai_data = self._analyze_content(round_data['ai']['content'], 'ai')
            ai_data.update({
                'timestamp': round_data['ai'].get('timestamp'),
                'raw_html': round_data['ai'].get('raw_html', '')
            })
            
            # 提取轮次元数据
            round_metadata = self._extract_round_metadata(user_data, ai_data, round_id)
            
            formatted_round = {
                'round_id': round_id,
                'user': user_data,
                'ai': ai_data,
                'metadata': round_metadata
            }
            
            return formatted_round
            
        except Exception as e:
            self.logger.warning(f"格式化轮次 {round_num} 失败: {e}")
            return None
    
    def _analyze_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """分析内容特征"""
        if not content:
            return {}
        
        # 基础分析
        word_count = len(content.split())
        char_count = len(content)
        line_count = content.count('\n') + 1
        
        # 提取关键词
        keywords = self._extract_keywords(content)
        
        # 检查代码块
        code_blocks = self._extract_code_blocks_info(content)
        has_code = len(code_blocks) > 0
        
        # 检查标题
        headings = self._extract_headings(content)
        has_headings = len(headings) > 0
        
        # 检查列表
        has_lists = bool(re.search(r'^\s*[\-\*\+]\s|\d+\.\s', content, re.MULTILINE))
        
        # 检查链接
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        
        # 估算阅读时间（按200字/分钟）
        read_time_minutes = max(1, word_count // 200)
        
        return {
            'content': content,
            'word_count': word_count,
            'char_count': char_count,
            'line_count': line_count,
            'keywords': keywords,
            'has_code': has_code,
            'code_blocks': code_blocks,
            'has_headings': has_headings,
            'headings': headings,
            'has_lists': has_lists,
            'links': links,
            'estimated_read_time': f"{read_time_minutes}分钟",
            'content_type': content_type
        }
    
    def _extract_keywords(self, content: str, max_keywords: int = 5) -> List[str]:
        """从内容中提取关键词"""
        if not content:
            return []
        
        # 清理内容
        content_lower = content.lower()
        
        # 移除代码块
        content_without_code = re.sub(r'```[\s\S]*?```', '', content_lower)
        
        # 移除标点符号
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', content_without_code)
        
        # 分词（简单的中英文分词）
        words = []
        for word in text.split():
            word = word.strip()
            if len(word) >= self.keyword_config['min_word_length']:
                words.append(word)
        
        # 排除常见词
        exclude_words = set(self.keyword_config['exclude_words'])
        filtered_words = [w for w in words if w not in exclude_words]
        
        # 计算词频
        from collections import Counter
        word_freq = Counter(filtered_words)
        
        # 获取最常见的关键词
        common_words = word_freq.most_common(max_keywords)
        keywords = [word for word, count in common_words]
        
        # 去重并返回
        return list(dict.fromkeys(keywords))[:max_keywords]
    
    def _extract_code_blocks_info(self, content: str) -> List[Dict[str, Any]]:
        """提取代码块信息"""
        code_blocks = []
        
        # 查找所有代码块
        pattern = r'```(\w*)\n([\s\S]*?)```'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            language = match.group(1) or 'text'
            code = match.group(2)
            lines = code.count('\n') + 1
            
            code_blocks.append({
                'language': language,
                'line_count': lines,
                'char_count': len(code),
                'has_complexity': len(code) > 100  # 简单判断是否复杂
            })
        
        return code_blocks
    
    def _extract_headings(self, content: str) -> List[Dict[str, Any]]:
        """提取标题信息"""
        headings = []
        
        # 查找Markdown标题
        pattern = r'^(#{1,6})\s+(.+)$'
        lines = content.split('\n')
        
        for line in lines:
            match = re.match(pattern, line.strip())
            if match:
                level = len(match.group(1))  # #的数量
                text = match.group(2).strip()
                
                headings.append({
                    'level': level,
                    'text': text,
                    'keywords': self._extract_keywords(text, 3)
                })
        
        return headings
    
    def _extract_round_metadata(self, user_data: Dict[str, Any], ai_data: Dict[str, Any], round_id: str) -> Dict[str, Any]:
        """提取轮次元数据"""
        # 判断是否是技术对话
        is_technical = self._is_round_technical(user_data, ai_data)
        
        # 提取主要主题
        main_topic = self._extract_main_topic(user_data, ai_data)
        
        # 估算总阅读时间
        user_time = int(user_data.get('estimated_read_time', '0分钟').replace('分钟', '')) or 0
        ai_time = int(ai_data.get('estimated_read_time', '0分钟').replace('分钟', '')) or 0
        total_time = user_time + ai_time
        
        # 计算技术复杂度
        complexity_score = self._calculate_complexity_score(ai_data)
        
        return {
            'round_id': round_id,
            'is_technical': is_technical,
            'main_topic': main_topic,
            'estimated_total_read_time': f"{total_time}分钟",
            'complexity_score': complexity_score,
            'has_code': ai_data.get('has_code', False),
            'has_headings': ai_data.get('has_headings', False),
            'created_at': datetime.now().isoformat()
        }
    
    def _is_round_technical(self, user_data: Dict[str, Any], ai_data: Dict[str, Any]) -> bool:
        """判断轮次是否是技术对话"""
        # 检查是否有代码
        if ai_data.get('has_code', False):
            return True
        
        # 检查是否有标题
        if ai_data.get('has_headings', False):
            return True
        
        # 检查关键词中是否包含技术词汇
        technical_keywords = [
            '代码', '编程', '开发', '配置', '部署', '安装',
            '函数', '变量', '类', '对象', '算法', '数据结构',
            'python', 'java', 'javascript', 'html', 'css',
            'docker', 'kubernetes', 'database', 'api', '服务器'
        ]
        
        ai_keywords = ' '.join(ai_data.get('keywords', [])).lower()
        for keyword in technical_keywords:
            if keyword.lower() in ai_keywords:
                return True
        
        # 较长的回答通常有技术内容
        return ai_data.get('word_count', 0) > 200
    
    def _extract_main_topic(self, user_data: Dict[str, Any], ai_data: Dict[str, Any]) -> str:
        """提取主要主题"""
        # 合并关键词
        all_keywords = user_data.get('keywords', []) + ai_data.get('keywords', [])
        
        if not all_keywords:
            return "未分类"
        
        # 返回最多出现的关键词
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        main_keyword = keyword_counts.most_common(1)[0][0]
        
        return main_keyword
    
    def _calculate_complexity_score(self, ai_data: Dict[str, Any]) -> int:
        """计算技术复杂度分数（0-10）"""
        score = 0
        
        # 代码块加分
        code_blocks = ai_data.get('code_blocks', [])
        if code_blocks:
            score += min(5, len(code_blocks) * 2)
            
            # 复杂代码块额外加分
            complex_blocks = sum(1 for cb in code_blocks if cb.get('has_complexity', False))
            score += min(3, complex_blocks)
        
        # 标题加分
        headings = ai_data.get('headings', [])
        if headings:
            score += min(3, len(headings))
        
        # 字数加分
        word_count = ai_data.get('word_count', 0)
        if word_count > 500:
            score += 3
        elif word_count > 200:
            score += 2
        elif word_count > 100:
            score += 1
        
        # 限制在0-10之间
        return min(10, max(0, score))
    
    def _extract_dialog_keywords(self, rounds: List[Dict[str, Any]]) -> str:
        """从所有轮次中提取对话关键词"""
        if not rounds:
            return "未分类"
        
        # 收集所有关键词
        all_keywords = []
        for round_data in rounds:
            user_keywords = round_data['user'].get('keywords', [])
            ai_keywords = round_data['ai'].get('keywords', [])
            all_keywords.extend(user_keywords + ai_keywords)
        
        if not all_keywords:
            return "未分类"
        
        # 统计词频
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        
        # 获取前3个关键词
        top_keywords = [word for word, count in keyword_counts.most_common(3)]
        
        # 组合成字符串
        return ' '.join(top_keywords)