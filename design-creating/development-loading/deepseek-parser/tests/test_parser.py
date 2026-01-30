"""
tests/test_parser.py
测试解析器功能
"""
import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from core.deepseek_parser import DeepSeekParser


class TestDeepSeekParser(unittest.TestCase):
    """测试DeepSeek解析器"""
    
    def setUp(self):
        """测试前准备"""
        self.parser = DeepSeekParser()
        
        # 测试数据目录
        self.test_data_dir = Path(__file__).parent.parent / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
    
    def test_parse_simple_html(self):
        """测试解析简单HTML"""
        # 创建一个简单的测试HTML
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>DeepSeek Conversation</title>
        </head>
        <body>
            <div class="message-user">
                <div class="content">如何用Python实现快速排序？</div>
                <time datetime="2024-01-24T10:00:00">10:00</time>
            </div>
            <div class="message-assistant">
                <div class="content">快速排序是一种高效的排序算法...</div>
                <pre><code class="python">def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)</code></pre>
                <time datetime="2024-01-24T10:01:00">10:01</time>
            </div>
        </body>
        </html>
        """
        
        # 解析HTML
        result = self.parser.parse_html(html_content)
        
        # 验证结果
        self.assertIn('metadata', result)
        self.assertIn('rounds', result)
        self.assertGreater(len(result['rounds']), 0)
        
        # 验证对话轮次
        round_data = result['rounds'][0]
        self.assertIn('user', round_data)
        self.assertIn('ai', round_data)
        
        # 验证用户内容
        user_content = round_data['user']['content']
        self.assertIn('如何用Python实现快速排序', user_content)
        
        # 验证AI内容
        ai_content = round_data['ai']['content']
        self.assertIn('快速排序', ai_content)
        self.assertIn('```python', ai_content)
    
    def test_parse_empty_html(self):
        """测试解析空HTML"""
        html_content = ""
        
        with self.assertRaises(Exception):
            self.parser.parse_html(html_content)
    
    def test_parse_invalid_html(self):
        """测试解析无效HTML"""
        html_content = "<invalid>html</content>"
        
        result = self.parser.parse_html(html_content)
        
        # 应该返回空结果
        self.assertEqual(len(result.get('rounds', [])), 0)
    
    def test_is_technical_conversation(self):
        """测试技术对话判断"""
        # 技术对话
        user_tech = "如何配置Docker容器？"
        ai_tech = "配置Docker容器需要以下步骤..."
        self.assertTrue(self.parser._is_technical_conversation(user_tech, ai_tech))
        
        # 非技术对话
        user_nontech = "你好"
        ai_nontech = "你好！"
        self.assertFalse(self.parser._is_technical_conversation(user_nontech, ai_nontech))
        
        # 包含代码的对话
        user_code = "请帮我写一个Python函数"
        ai_code = "```python\ndef hello():\n    return 'Hello World'\n```"
        self.assertTrue(self.parser._is_technical_conversation(user_code, ai_code))
    
    def test_extract_content(self):
        """测试内容提取"""
        # 创建测试元素
        from bs4 import BeautifulSoup
        
        html = '<div class="test">这是一个<b>测试</b>内容</div>'
        soup = BeautifulSoup(html, 'lxml')
        element = soup.find('div')
        
        content = self.parser._extract_content(element)
        
        self.assertIn('测试', content)
        self.assertNotIn('<b>', content)
    
    def test_extract_timestamp(self):
        """测试时间戳提取"""
        from bs4 import BeautifulSoup
        
        # 测试包含time元素的情况
        html = '<div><time datetime="2024-01-24T10:00:00">10:00</time></div>'
        soup = BeautifulSoup(html, 'lxml')
        element = soup.find('div')
        
        timestamp = self.parser._extract_timestamp(element)
        self.assertEqual(timestamp, "2024-01-24T10:00:00")
        
        # 测试data-time属性
        html = '<div data-time="2024-01-24T11:00:00">内容</div>'
        soup = BeautifulSoup(html, 'lxml')
        element = soup.find('div')
        
        timestamp = self.parser._extract_timestamp(element)
        self.assertEqual(timestamp, "2024-01-24T11:00:00")
    
    def tearDown(self):
        """测试后清理"""
        pass


if __name__ == '__main__':
    unittest.main()