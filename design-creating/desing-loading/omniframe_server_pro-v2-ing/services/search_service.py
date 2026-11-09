# services/search_service_v2.py
"""
搜索服务 V2 - 高性能搜索服务
"""
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from functools import lru_cache
import asyncio

from utils.logger import logger
from services.file_service_v2 import AsyncFileService


class SearchEngine:
    """搜索引擎"""
    
    def __init__(self, file_service: AsyncFileService):
        self.file_service = file_service
        self.search_history = []
        self.max_history = 100
        
    async def search(self, 
                    query: str,
                    search_path: Optional[str] = None,
                    search_type: str = "name",
                    limit: int = 100) -> Dict[str, Any]:
        """执行搜索"""
        start_time = datetime.now()
        
        try:
            # 解析搜索查询
            parsed_query = self._parse_query(query)
            
            # 执行搜索
            if search_type == "index":
                # 使用索引快速搜索
                results = await self.file_service.fast_search(
                    parsed_query["keywords"], limit
                )
            else:
                # 常规搜索
                results = await self.file_service.search_files(
                    parsed_query["keywords"],
                    search_path,
                    search_type,
                    parsed_query["case_sensitive"],
                    limit
                )
            
            # 增强结果
            enhanced_results = self._enhance_results(results, parsed_query)
            
            # 记录搜索历史
            self._record_search(query, len(enhanced_results))
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "query": query,
                "results": enhanced_results,
                "count": len(enhanced_results),
                "execution_time": execution_time,
                "search_type": search_type
            }
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "results": []
            }
    
    def _parse_query(self, query: str) -> Dict[str, Any]:
        """解析搜索查询"""
        parsed = {
            "original": query,
            "keywords": query,
            "case_sensitive": False,
            "exact_match": False,
            "file_types": []
        }
        
        # 检测是否区分大小写
        if any(c.isupper() for c in query):
            parsed["case_sensitive"] = True
        
        # 检测是否精确匹配
        if query.startswith('"') and query.endswith('"'):
            parsed["exact_match"] = True
            parsed["keywords"] = query[1:-1]
        
        # 提取文件类型限制
        file_type_patterns = [
            (r'type:(pdf|doc|docx|txt)', 'document'),
            (r'type:(jpg|jpeg|png|gif|bmp)', 'image'),
            (r'type:(mp3|wav|flac)', 'audio'),
            (r'type:(mp4|avi|mov|mkv)', 'video'),
            (r'type:(py|js|java|cpp|html|css)', 'code'),
        ]
        
        for pattern, file_type in file_type_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                parsed["file_types"].append(file_type)
                # 从查询中移除类型限制
                parsed["keywords"] = re.sub(pattern, '', parsed["keywords"]).strip()
        
        return parsed
    
    def _enhance_results(self, 
                        results: List[Dict[str, Any]],
                        parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """增强搜索结果"""
        enhanced = []
        
        for result in results:
            enhanced_result = result.copy()
            
            # 计算相关性分数
            relevance = self._calculate_relevance(result, parsed_query)
            enhanced_result["relevance"] = relevance
            
            # 添加预览信息
            if result.get("size", 0) < 1024 * 1024:  # 小于1MB的文件
                enhanced_result["preview_available"] = True
            else:
                enhanced_result["preview_available"] = False
            
            enhanced.append(enhanced_result)
        
        # 按相关性排序
        enhanced.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        return enhanced
    
    def _calculate_relevance(self, 
                           result: Dict[str, Any],
                           parsed_query: Dict[str, Any]) -> float:
        """计算相关性分数"""
        score = 0.0
        query_keywords = parsed_query["keywords"].lower()
        file_name = result.get("name", "").lower()
        
        # 名称匹配
        if parsed_query["exact_match"]:
            if query_keywords == file_name:
                score += 100
        else:
            # 部分匹配
            for keyword in query_keywords.split():
                if keyword in file_name:
                    score += 10
            
            # 开头匹配权重更高
            if file_name.startswith(query_keywords):
                score += 50
        
        # 文件类型权重
        if parsed_query["file_types"]:
            file_extension = result.get("name", "").split('.')[-1].lower()
            if any(file_type in file_extension for file_type in parsed_query["file_types"]):
                score += 30
        
        # 最近修改的文件权重更高
        modified = result.get("modified", 0)
        if modified:
            days_ago = (datetime.now().timestamp() - modified) / (24 * 3600)
            if days_ago < 7:  # 一周内修改的
                score += 20
            elif days_ago < 30:  # 一个月内修改的
                score += 10
        
        return score
    
    def _record_search(self, query: str, result_count: int):
        """记录搜索历史"""
        search_record = {
            "query": query,
            "result_count": result_count,
            "timestamp": datetime.now().isoformat()
        }
        
        self.search_history.append(search_record)
        
        # 限制历史记录数量
        if len(self.search_history) > self.max_history:
            self.search_history.pop(0)
    
    async def get_search_suggestions(self, partial_query: str) -> List[str]:
        """获取搜索建议"""
        suggestions = []
        
        # 从历史记录中获取建议
        for record in self.search_history[-10:]:
            if record["query"].startswith(partial_query):
                suggestions.append(record["query"])
        
        # 添加常见搜索
        common_searches = [
            "document",
            "image",
            "pdf",
            "code",
            "recent"
        ]
        
        for search in common_searches:
            if partial_query in search:
                suggestions.append(f"search {search}")
        
        return list(set(suggestions))[:5]  # 去重并限制数量
    
    @lru_cache(maxsize=128)
    def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门搜索"""
        from collections import Counter
        
        if not self.search_history:
            return []
        
        # 统计搜索频率
        search_counts = Counter([record["query"] for record in self.search_history])
        
        popular = []
        for query, count in search_counts.most_common(limit):
            # 查找最近一次搜索时间
            last_searched = max(
                [record["timestamp"] for record in self.search_history 
                 if record["query"] == query]
            )
            
            popular.append({
                "query": query,
                "count": count,
                "last_searched": last_searched
            })
        
        return popular


class SearchServiceV2:
    """搜索服务V2"""
    
    def __init__(self, file_service: AsyncFileService):
        self.search_engine = SearchEngine(file_service)
    
    async def search_by_name(self, 
                           query: str,
                           search_path: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """按名称搜索"""
        result = await self.search_engine.search(
            query, search_path, "name", limit
        )
        
        if result["success"]:
            return result["results"]
        else:
            logger.error(f"按名称搜索失败: {result.get('error')}")
            return []
    
    async def search_by_content(self,
                              query: str,
                              search_path: Optional[str] = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """按内容搜索"""
        result = await self.search_engine.search(
            query, search_path, "content", limit
        )
        
        if result["success"]:
            return result["results"]
        else:
            logger.error(f"按内容搜索失败: {result.get('error')}")
            return []
    
    async def search_by_index(self,
                            query: str,
                            limit: int = 100) -> List[Dict[str, Any]]:
        """使用索引搜索"""
        result = await self.search_engine.search(
            query, None, "index", limit
        )
        
        if result["success"]:
            return result["results"]
        else:
            logger.error(f"索引搜索失败: {result.get('error')}")
            return []
    
    async def get_suggestions(self, partial_query: str) -> List[str]:
        """获取搜索建议"""
        return await self.search_engine.get_search_suggestions(partial_query)
    
    def get_search_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        return self.search_engine.search_history[-limit:]
    
    def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门搜索"""
        return self.search_engine.get_popular_searches(limit)