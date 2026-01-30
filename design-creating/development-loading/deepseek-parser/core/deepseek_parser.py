"""
core/deepseek_parser.py
DeepSeek专用HTML解析器
"""
import re
from bs4 import BeautifulSoup
import html2text
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from utils.logger import logger


class DeepSeekParser:
    """专门针对DeepSeek对话HTML结构的解析器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logger
        
        # 从配置加载选择器
        parsing_config = self.config.get('parsing', {})
        
        # DeepSeek特定的选择器模式
        self.USER_SELECTORS = parsing_config.get('user_selectors', [
            '[class*="user"][class*="message"]',
            '[class*="human"][class*="message"]',
            'div[data-role="user"]',
            '.message-user',
            '.human-message',
            '.user-message',
        ])
        
        self.AI_SELECTORS = parsing_config.get('ai_selectors', [
            '[class*="assistant"][class*="message"]',
            '[class*="ai"][class*="message"]',
            'div[data-role="assistant"]',
            '.message-assistant',
            '.ai-message',
            '.assistant-message',
        ])
        
        # 时间戳选择器
        self.TIME_SELECTORS = [
            'time',
            '[class*="time"]',
            '[class*="timestamp"]',
            '[data-time]',
        ]
        
        # 初始化HTML到Markdown转换器
        self.html2text_converter = html2text.HTML2Text()
        self.html2text_converter.ignore_links = False
        self.html2text_converter.ignore_images = True
        self.html2text_converter.body_width = 0  # 不换行
        
        # 缓存上次解析的结构，用于启发式匹配
        self.last_structure = None
    
    def parse_html(self, html_content: str) -> Dict[str, Any]:
        """
        解析DeepSeek对话HTML
        
        返回结构：
        {
            'metadata': {
                'source': 'html',
                'parsed_at': '2024-01-24T10:30:00',
                'total_rounds': 5,
                'structure_type': 'new_version'
            },
            'rounds': [
                {
                    'user': {
                        'content': '...',
                        'timestamp': '2024-01-24T10:00:00',
                        'raw_html': '...'
                    },
                    'ai': {
                        'content': '...',
                        'timestamp': '2024-01-24T10:01:00',
                        'raw_html': '...'
                    }
                }
            ]
        }
        """
        try:
            self.logger.info("开始解析HTML内容...")
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 识别DeepSeek结构
            structure_type = self._identify_structure(soup)
            self.logger.debug(f"识别到结构类型: {structure_type}")
            
            # 根据结构类型选择解析策略
            if structure_type == 'new_version':
                parsed_data = self._parse_new_version(soup)
            elif structure_type == 'old_version':
                parsed_data = self._parse_old_version(soup)
            elif structure_type == 'mobile_version':
                parsed_data = self._parse_mobile_version(soup)
            else:
                parsed_data = self._generic_parse(soup)
            
            # 清理和验证数据
            parsed_data = self._clean_parsed_data(parsed_data)
            
            # 添加元数据
            parsed_data['metadata'] = {
                'source': 'html',
                'parsed_at': datetime.now().isoformat(),
                'total_rounds': len(parsed_data.get('rounds', [])),
                'structure_type': structure_type,
                'valid_rounds': self._count_valid_rounds(parsed_data.get('rounds', []))
            }
            
            self.logger.info(f"解析完成，共发现 {parsed_data['metadata']['total_rounds']} 轮对话")
            self.logger.info(f"有效对话轮次: {parsed_data['metadata']['valid_rounds']}")
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"解析HTML失败: {e}")
            raise
    
    def _identify_structure(self, soup: BeautifulSoup) -> str:
        """识别DeepSeek特定的HTML结构"""
        
        # 检查是否有已知的DeepSeek特定元素
        deepseek_indicators = [
            ('deepseek', lambda s: s.find(string=re.compile(r'deepseek', re.I))),
            ('api_version', lambda s: s.find('meta', {'name': 'deepseek-version'})),
            ('new_version_div', lambda s: s.select_one('.deepseek-chat-container')),
            ('old_version_div', lambda s: s.select_one('.chat-container.legacy')),
        ]
        
        for name, check_func in deepseek_indicators:
            if check_func(soup):
                self.logger.debug(f"发现DeepSeek标识: {name}")
                # 根据标识判断版本
                if 'new' in name:
                    return 'new_version'
                elif 'old' in name or 'legacy' in name:
                    return 'old_version'
        
        # 检查移动端特征
        mobile_indicators = [
            'viewport',
            'mobile',
            'Mozilla/5.0 (iPhone',
            'Android'
        ]
        
        html_str = str(soup)
        for indicator in mobile_indicators:
            if indicator.lower() in html_str.lower():
                self.logger.debug("发现移动端特征")
                return 'mobile_version'
        
        # 使用启发式方法
        user_elements = self._find_elements(soup, self.USER_SELECTORS)
        ai_elements = self._find_elements(soup, self.AI_SELECTORS)
        
        if len(user_elements) > 0 and len(ai_elements) > 0:
            # 检查是否是成对出现
            if abs(len(user_elements) - len(ai_elements)) <= 1:
                self.logger.debug("使用新版本结构（成对对话）")
                return 'new_version'
            else:
                self.logger.debug("使用旧版本结构（非成对）")
                return 'old_version'
        
        # 默认使用通用解析
        self.logger.warning("无法识别具体版本，使用通用解析")
        return 'generic'
    
    def _parse_new_version(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """解析新版本DeepSeek结构（对话成对出现）"""
        rounds = []
        
        # 找到所有对话容器
        conversation_containers = soup.select('.conversation-container, .chat-round, [class*="round"]')
        
        if conversation_containers:
            # 按容器解析
            for container in conversation_containers:
                round_data = self._parse_conversation_container(container)
                if round_data:
                    rounds.append(round_data)
        else:
            # 尝试按消息顺序解析
            all_messages = self._find_all_messages(soup)
            rounds = self._pair_messages(all_messages)
        
        return {'rounds': rounds}
    
    def _parse_old_version(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """解析旧版本DeepSeek结构"""
        # 旧版本可能没有明确的容器，需要按顺序配对
        all_messages = self._find_all_messages(soup)
        rounds = self._pair_messages(all_messages)
        
        return {'rounds': rounds}
    
    def _parse_mobile_version(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """解析移动版本"""
        # 移动版本通常更简单
        rounds = []
        
        # 尝试找到消息列表
        message_list = soup.select('.message-list, .chat-history, ul.messages')
        
        if message_list:
            for msg_container in message_list[0].find_all('li', recursive=False):
                round_data = self._parse_message_container(msg_container)
                if round_data:
                    rounds.append(round_data)
        else:
            # 回退到通用解析
            return self._generic_parse(soup)
        
        return {'rounds': rounds}
    
    def _generic_parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """通用解析方法"""
        self.logger.info("使用通用解析方法")
        
        # 尝试多种策略
        strategies = [
            self._parse_by_message_pairs,
            self._parse_by_alternating_elements,
            self._parse_by_class_patterns,
        ]
        
        for strategy in strategies:
            try:
                result = strategy(soup)
                if result and len(result.get('rounds', [])) > 0:
                    self.logger.info(f"策略 {strategy.__name__} 成功，找到 {len(result['rounds'])} 轮对话")
                    return result
            except Exception as e:
                self.logger.debug(f"策略 {strategy.__name__} 失败: {e}")
                continue
        
        # 所有策略都失败，返回空结果
        self.logger.warning("所有解析策略都失败")
        return {'rounds': []}
    
    def _parse_conversation_container(self, container) -> Optional[Dict[str, Any]]:
        """解析单个对话容器"""
        try:
            # 在容器内查找用户和AI消息
            user_element = self._find_first_element(container, self.USER_SELECTORS)
            ai_element = self._find_first_element(container, self.AI_SELECTORS)
            
            if not user_element or not ai_element:
                return None
            
            user_content = self._extract_content(user_element)
            ai_content = self._extract_content(ai_element)
            
            user_timestamp = self._extract_timestamp(user_element)
            ai_timestamp = self._extract_timestamp(ai_element)
            
            return {
                'user': {
                    'content': user_content,
                    'timestamp': user_timestamp,
                    'raw_html': str(user_element)
                },
                'ai': {
                    'content': ai_content,
                    'timestamp': ai_timestamp,
                    'raw_html': str(ai_element)
                }
            }
        except Exception as e:
            self.logger.debug(f"解析对话容器失败: {e}")
            return None
    
    def _find_all_messages(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """查找所有消息元素"""
        messages = []
        
        # 查找用户消息
        user_elements = self._find_elements(soup, self.USER_SELECTORS)
        for elem in user_elements:
            messages.append({
                'type': 'user',
                'element': elem,
                'content': self._extract_content(elem),
                'timestamp': self._extract_timestamp(elem),
                'order': self._get_element_order(elem)
            })
        
        # 查找AI消息
        ai_elements = self._find_elements(soup, self.AI_SELECTORS)
        for elem in ai_elements:
            messages.append({
                'type': 'ai',
                'element': elem,
                'content': self._extract_content(elem),
                'timestamp': self._extract_timestamp(elem),
                'order': self._get_element_order(elem)
            })
        
        # 按顺序排序
        messages.sort(key=lambda x: x['order'])
        
        return messages
    
    def _pair_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将消息配对成对话轮次"""
        rounds = []
        i = 0
        
        while i < len(messages):
            current_msg = messages[i]
            
            if current_msg['type'] == 'user':
                # 查找下一个AI消息
                ai_msg = None
                for j in range(i + 1, len(messages)):
                    if messages[j]['type'] == 'ai':
                        ai_msg = messages[j]
                        break
                
                if ai_msg:
                    rounds.append({
                        'user': {
                            'content': current_msg['content'],
                            'timestamp': current_msg['timestamp'],
                            'raw_html': str(current_msg['element'])
                        },
                        'ai': {
                            'content': ai_msg['content'],
                            'timestamp': ai_msg['timestamp'],
                            'raw_html': str(ai_msg['element'])
                        }
                    })
                    i = j + 1  # 跳过已使用的AI消息
                else:
                    # 没有配对的AI消息
                    i += 1
            else:
                # 跳过孤立的AI消息
                i += 1
        
        return rounds
    
    def _extract_content(self, element) -> str:
        """从元素中提取内容"""
        if not element:
            return ""
        
        # 转换为Markdown
        html_content = str(element)
        markdown = self.html2text_converter.handle(html_content)
        
        # 清理Markdown
        markdown = self._clean_markdown(markdown)
        
        return markdown.strip()
    
    def _clean_markdown(self, markdown: str) -> str:
        """清理Markdown内容"""
        # 移除多余的空行
        lines = markdown.split('\n')
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1]:  # 保留一个空行
                cleaned_lines.append('')
        
        # 限制最大长度
        max_length = self.config.get('parsing', {}).get('max_content_length', 10000)
        result = '\n'.join(cleaned_lines)
        
        if len(result) > max_length:
            result = result[:max_length] + "...\n[内容过长已截断]"
        
        return result
    
    def _extract_timestamp(self, element) -> Optional[str]:
        """从元素中提取时间戳"""
        if not element:
            return None
        
        # 尝试多种方式获取时间戳
        timestamp = None
        
        # 1. 查找time元素
        time_elem = element.find('time')
        if time_elem and time_elem.get('datetime'):
            timestamp = time_elem['datetime']
        elif time_elem:
            timestamp = time_elem.text.strip()
        
        # 2. 查找data-time属性
        if not timestamp:
            timestamp = element.get('data-time')
        
        # 3. 查找包含时间的类
        if not timestamp:
            for cls in element.get('class', []):
                if 'time' in cls.lower():
                    # 尝试从文本中提取时间
                    text = element.get_text()
                    time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}', text)
                    if time_match:
                        timestamp = time_match.group(0)
                        break
        
        # 清理时间戳
        if timestamp:
            # 统一格式为ISO格式
            timestamp = timestamp.replace(' ', 'T')
            if 'T' not in timestamp and len(timestamp) >= 10:
                timestamp = timestamp[:10] + 'T' + (timestamp[10:] if len(timestamp) > 10 else '00:00')
        
        return timestamp
    
    def _get_element_order(self, element) -> int:
        """获取元素在文档中的顺序"""
        # 使用元素的源码位置作为顺序
        try:
            return element.sourceline or 0
        except:
            return 0
    
    def _find_elements(self, soup: BeautifulSoup, selectors: List[str]) -> List:
        """使用多个选择器查找元素"""
        all_elements = []
        seen = set()
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    elem_id = id(elem)
                    if elem_id not in seen:
                        seen.add(elem_id)
                        all_elements.append(elem)
            except Exception as e:
                self.logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        
        return all_elements
    
    def _find_first_element(self, container, selectors: List[str]):
        """在容器内查找第一个匹配的元素"""
        for selector in selectors:
            try:
                element = container.select_one(selector)
                if element:
                    return element
            except:
                continue
        return None
    
    def _parse_by_message_pairs(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """按消息对解析策略"""
        messages = self._find_all_messages(soup)
        rounds = self._pair_messages(messages)
        return {'rounds': rounds}
    
    def _parse_by_alternating_elements(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """按交替元素解析策略"""
        # 查找所有可能是消息的元素
        potential_messages = soup.find_all(['div', 'section', 'article'], 
                                          class_=re.compile(r'message|chat|bubble', re.I))
        
        rounds = []
        current_user = None
        
        for elem in potential_messages:
            elem_text = elem.get_text(strip=True)
            if not elem_text:
                continue
            
            # 判断是用户还是AI消息
            elem_classes = ' '.join(elem.get('class', []))
            elem_html = str(elem).lower()
            
            is_user = any(word in elem_classes.lower() or word in elem_html 
                         for word in ['user', 'human', 'question', 'input'])
            is_ai = any(word in elem_classes.lower() or word in elem_html 
                       for word in ['assistant', 'ai', 'answer', 'response', 'deepseek'])
            
            if is_user and not is_ai:
                current_user = {
                    'content': self._extract_content(elem),
                    'timestamp': self._extract_timestamp(elem),
                    'raw_html': str(elem)
                }
            elif is_ai and current_user:
                rounds.append({
                    'user': current_user,
                    'ai': {
                        'content': self._extract_content(elem),
                        'timestamp': self._extract_timestamp(elem),
                        'raw_html': str(elem)
                    }
                })
                current_user = None
        
        return {'rounds': rounds}
    
    def _parse_by_class_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """按类名模式解析"""
        rounds = []
        
        # 查找所有具有常见对话类名的元素
        for elem in soup.find_all(class_=re.compile(r'message|msg|chat', re.I)):
            parent = elem.parent
            if parent and parent not in [r['user']['raw_html'] for r in rounds if 'user' in r]:
                # 尝试在父元素中查找配对
                siblings = parent.find_all(class_=re.compile(r'message|msg|chat', re.I))
                if len(siblings) >= 2:
                    # 假设前两个是用户和AI
                    user_elem = siblings[0]
                    ai_elem = siblings[1] if len(siblings) > 1 else None
                    
                    if ai_elem:
                        rounds.append({
                            'user': {
                                'content': self._extract_content(user_elem),
                                'timestamp': self._extract_timestamp(user_elem),
                                'raw_html': str(user_elem)
                            },
                            'ai': {
                                'content': self._extract_content(ai_elem),
                                'timestamp': self._extract_timestamp(ai_elem),
                                'raw_html': str(ai_elem)
                            }
                        })
        
        return {'rounds': rounds}
    
    def _clean_parsed_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """清理解析后的数据"""
        if 'rounds' not in parsed_data:
            parsed_data['rounds'] = []
        
        # 过滤无效轮次
        valid_rounds = []
        for round_data in parsed_data['rounds']:
            if self._is_valid_round(round_data):
                # 清理内容
                round_data['user']['content'] = self._clean_content(round_data['user']['content'])
                round_data['ai']['content'] = self._clean_content(round_data['ai']['content'])
                valid_rounds.append(round_data)
            else:
                self.logger.debug(f"过滤无效轮次: {round_data.get('user', {}).get('content', '')[:50]}...")
        
        parsed_data['rounds'] = valid_rounds
        return parsed_data
    
    def _is_valid_round(self, round_data: Dict[str, Any]) -> bool:
        """判断轮次是否有效"""
        if 'user' not in round_data or 'ai' not in round_data:
            return False
        
        user_content = round_data['user'].get('content', '')
        ai_content = round_data['ai'].get('content', '')
        
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
    
    def _clean_content(self, content: str) -> str:
        """清理内容"""
        if not content:
            return ""
        
        # 移除多余的空行
        lines = [line.rstrip() for line in content.split('\n')]
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            if line.strip() or (i > 0 and lines[i-1].strip()):
                cleaned_lines.append(line)
        
        # 合并连续空行
        result_lines = []
        for line in cleaned_lines:
            if line.strip() or (not result_lines or result_lines[-1].strip()):
                result_lines.append(line)
        
        return '\n'.join(result_lines).strip()
    
    def _count_valid_rounds(self, rounds: List[Dict[str, Any]]) -> int:
        """计算有效轮次数量"""
        return sum(1 for round_data in rounds if self._is_valid_round(round_data))