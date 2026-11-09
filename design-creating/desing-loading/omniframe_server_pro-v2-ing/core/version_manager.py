# core/version_manager.py
"""
版本管理器 - 支持新旧版本切换
"""
from typing import Optional, Dict, Any
import importlib

from config.settings import settings


class VersionManager:
    """版本管理器"""
    
    def __init__(self):
        self.current_version = getattr(settings, 'PARSER_VERSION', 'v1')
        
    def get_intent_parser(self):
        """获取意图解析器实例"""
        if self.current_version == 'v2':
            from core.intent_parser_v2 import IntentParserV2
            return IntentParserV2()
        else:
            from core.intent_parser import IntentParser
            return IntentParser()
    
    async def get_task_dispatcher(self):
        """获取任务分发器实例"""
        if self.current_version == 'v2':
            from core.task_dispatcher_v2 import get_task_dispatcher_v2
            return await get_task_dispatcher_v2()
        else:
            from core.task_dispatcher import get_task_dispatcher
            return await get_task_dispatcher()
    
    def switch_version(self, version: str):
        """切换版本"""
        if version in ['v1', 'v2']:
            self.current_version = version
            return True
        return False
    
    def compare_performance(self, command: str, iterations: int = 100):
        """对比性能"""
        results = {}
        
        for version in ['v1', 'v2']:
            self.switch_version(version)
            parser = self.get_intent_parser()
            
            import time
            times = []
            
            for _ in range(iterations):
                start = time.perf_counter()
                parser.parse(command)
                end = time.perf_counter()
                times.append(end - start)
            
            results[version] = {
                'avg_time': sum(times) / len(times),
                'max_time': max(times),
                'min_time': min(times)
            }
        
        return results