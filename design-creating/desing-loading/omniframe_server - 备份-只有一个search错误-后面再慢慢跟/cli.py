"""
Omniframe CLI - 命令行工具
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import aiohttp
from tabulate import tabulate

from config.settings import settings
from utils.logger import logger, setup_logging


class OmniframeCLI:
    """命令行客户端"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"http://{settings.host}:{settings.port}"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def execute_command(self, command: str, quiet: bool = False) -> Dict[str, Any]:
        """执行命令"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/commands/execute",
                json={"command": command, "auto_index": True}
            ) as response:
                data = await response.json()
                
                if response.status != 200:
                    print(f"错误: {data.get('detail', '未知错误')}")
                    return {"success": False}
                
                return data
        
        except aiohttp.ClientError as e:
            print(f"连接错误: {e}")
            return {"success": False}
    
    async def list_files(self, path: Optional[str] = None, recursive: bool = False):
        """列出文件"""
        try:
            params = {"recursive": str(recursive).lower()}
            if path:
                params["path"] = path
            
            async with self.session.get(
                f"{self.base_url}/api/files/list",
                params=params
            ) as response:
                data = await response.json()
                
                if response.status != 200:
                    print(f"错误: {data.get('detail', '未知错误')}")
                    return
                
                if data["success"]:
                    self._print_file_list(data["items"])
                else:
                    print(f"失败: {data.get('message', '未知错误')}")
        
        except aiohttp.ClientError as e:
            print(f"连接错误: {e}")
    
    async def search_files(self, query: str, path: Optional[str] = None):
        """搜索文件"""
        try:
            params = {"query": query, "search_type": "both"}
            if path:
                params["path"] = path
            
            async with self.session.get(
                f"{self.base_url}/api/files/search",
                params=params
            ) as response:
                data = await response.json()
                
                if response.status != 200:
                    print(f"错误: {data.get('detail', '未知错误')}")
                    return
                
                if data["success"]:
                    print(f"找到 {data['total']} 个结果:")
                    self._print_file_list(data["results"])
                else:
                    print(f"搜索失败: {data.get('message', '未知错误')}")
        
        except aiohttp.ClientError as e:
            print(f"连接错误: {e}")
    
    async def get_system_info(self):
        """获取系统信息"""
        try:
            async with self.session.get(f"{self.base_url}/system/info") as response:
                data = await response.json()
                
                if response.status != 200:
                    print(f"错误: {data.get('detail', '未知错误')}")
                    return
                
                print("\n=== 系统信息 ===")
                print(f"平台: {data['system']['platform']}")
                print(f"Python: {data['system']['python_version']}")
                print(f"主机名: {data['system']['hostname']}")
                
                print("\n=== 资源使用 ===")
                print(f"CPU: {data['resources']['cpu_percent']}%")
                print(f"内存: {data['resources']['memory_percent']}%")
                
                disk = data['resources']['disk_usage']
                print(f"磁盘: {disk['percent']}% (已用: {self._humanize_size(disk['used'])}, "
                      f"可用: {self._humanize_size(disk['free'])})")
                
                print("\n=== 服务状态 ===")
                print(f"工作空间: {data['service']['root_path']}")
                print(f"安全模式: {data['service']['safe_mode']}")
                print(f"宪法规则: {data['service']['constitution_enabled']}")
        
        except aiohttp.ClientError as e:
            print(f"连接错误: {e}")
    
    async def generate_index(self, force: bool = False):
        """生成索引"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/commands/index/generate",
                json={"force": force, "incremental": not force}
            ) as response:
                data = await response.json()
                
                if response.status != 200:
                    print(f"错误: {data.get('detail', '未知错误')}")
                    return
                
                if data["success"]:
                    result = data["result"]
                    print(f"✓ 索引生成完成")
                    print(f"  文件数: {result.get('total_files', 0)}")
                    print(f"  目录数: {result.get('total_dirs', 0)}")
                    print(f"  耗时: {result.get('execution_time', 0):.2f}秒")
                else:
                    print(f"失败: {data.get('message', '未知错误')}")
        
        except aiohttp.ClientError as e:
            print(f"连接错误: {e}")
    
    async def get_status(self):
        """获取状态"""
        try:
            # 系统状态
            async with self.session.get(f"{self.base_url}/system/info") as sys_response:
                sys_data = await sys_response.json()
            
            # 索引状态
            async with self.session.get(f"{self.base_url}/api/commands/index/status") as idx_response:
                idx_data = await idx_response.json()
            
            # 上下文状态
            async with self.session.get(f"{self.base_url}/api/context/status") as ctx_response:
                ctx_data = await ctx_response.json()
            
            print("\n" + "="*50)
            print("Omniframe Server 状态")
            print("="*50)
            
            if sys_response.status == 200:
                print(f"服务状态: 运行正常")
                print(f"工作空间: {sys_data['service']['root_path']}")
                print(f"运行时间: {ctx_data.get('session_duration', '未知')}")
            else:
                print(f"服务状态: 异常")
            
            if idx_response.status == 200 and idx_data["success"]:
                status = idx_data["status"]
                print(f"\n索引状态: {status.get('has_index', False) and '已创建' or '无索引'}")
                print(f"索引文件: {status.get('total_files', 0)} 个")
                print(f"最后更新: {status.get('last_updated', '从未')}")
            
            if ctx_response.status == 200 and ctx_data["success"]:
                stats = ctx_data["statistics"]
                print(f"\n上下文状态:")
                print(f"命令历史: {stats.get('total_commands', 0)} 条")
                print(f"文件访问: {stats.get('total_file_access', 0)} 次")
                print(f"书签: {stats.get('total_bookmarks', 0)} 个")
            
            print("="*50)
        
        except aiohttp.ClientError as e:
            print(f"连接错误: {e}")
    
    def _print_file_list(self, items):
        """打印文件列表"""
        if not items:
            print("没有文件")
            return
        
        table_data = []
        for item in items:
            icon = "📁" if item.get("is_dir") else "📄"
            name = item["name"]
            size = self._humanize_size(item.get("size", 0))
            modified = item.get("modified_iso", "")[:19].replace("T", " ")
            
            table_data.append([icon, name, size, modified])
        
        print(tabulate(table_data, 
                      headers=["类型", "名称", "大小", "修改时间"],
                      tablefmt="simple"))
    
    def _humanize_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        size = float(size_bytes)
        
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        
        return f"{size:.1f} {units[i]}"
    
    async def interactive_mode(self):
        """交互式模式"""
        print("\n" + "="*50)
        print("Omniframe CLI - 交互模式")
        print("输入 'help' 查看命令，'exit' 退出")
        print("="*50)
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if command.lower() in ['exit', 'quit', 'q']:
                    print("再见！")
                    break
                
                elif command.lower() in ['help', '?']:
                    self._print_help()
                
                elif command.lower().startswith('list'):
                    # 解析参数
                    parts = command.split()
                    path = parts[1] if len(parts) > 1 else None
                    recursive = '-r' in parts or '--recursive' in parts
                    await self.list_files(path, recursive)
                
                elif command.lower().startswith('search'):
                    parts = command.split()
                    if len(parts) < 2:
                        print("用法: search <查询词> [路径]")
                    else:
                        query = parts[1]
                        path = parts[2] if len(parts) > 2 else None
                        await self.search_files(query, path)
                
                elif command.lower() in ['status', 'info']:
                    await self.get_status()
                
                elif command.lower() in ['index', 'reindex']:
                    force = 'force' in command.lower()
                    await self.generate_index(force)
                
                elif command.lower() == 'system':
                    await self.get_system_info()
                
                elif command:
                    # 作为自然语言命令执行
                    result = await self.execute_command(command)
                    
                    if result.get("success"):
                        if result.get("requires_confirmation"):
                            print("⚠️  需要确认的操作:")
                            for conf in result.get("confirmations", []):
                                print(f"  - {conf.get('message')}")
                            print("请在Web界面中确认")
                        else:
                            self._print_command_result(result)
                    else:
                        print(f"命令执行失败: {result.get('message', '未知错误')}")
            
            except KeyboardInterrupt:
                print("\n\n中断")
                break
            except EOFError:
                print("\n\n再见！")
                break
            except Exception as e:
                print(f"错误: {e}")
    
    def _print_command_result(self, result):
        """打印命令结果"""
        if result.get("data"):
            items = result["data"]
            if isinstance(items, list) and len(items) > 0:
                if "path" in items[0] and "name" in items[0]:
                    self._print_file_list(items)
                else:
                    print(json.dumps(items, indent=2, ensure_ascii=False))
        
        if result.get("message"):
            print(f"✓ {result['message']}")
        
        if result.get("execution_time"):
            print(f"耗时: {result['execution_time']:.2f}秒")
    
    def _print_help(self):
        """打印帮助信息"""
        help_text = """
可用命令:
  help                    显示此帮助信息
  exit, quit, q          退出程序
  
  list [路径] [-r]       列出文件，-r 递归列出
  search <查询词> [路径] 搜索文件
  status                 显示服务器状态
  system                 显示系统信息
  index [force]          生成索引，force 强制重新生成
  
自然语言命令:
  任何其他输入都将作为自然语言命令执行
  例如: "查找所有图片", "列出最近修改的文件", "打包下载所有PDF"
  
示例:
  > list /path/to/dir -r
  > search report.txt
  > 初始化索引
  > 找出所有上周修改的文件
        """
        print(help_text)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Omniframe 命令行工具")
    parser.add_argument("command", nargs="?", help="要执行的命令")
    parser.add_argument("-p", "--path", help="文件路径")
    parser.add_argument("-r", "--recursive", action="store_true", help="递归操作")
    parser.add_argument("-q", "--query", help="搜索查询")
    parser.add_argument("-s", "--server", help="服务器地址", 
                       default=f"http://{settings.host}:{settings.port}")
    parser.add_argument("--force", action="store_true", help="强制操作")
    parser.add_argument("-i", "--interactive", action="store_true", 
                       help="进入交互模式")
    
    args = parser.parse_args()
    
    async def run():
        async with OmniframeCLI(args.server) as cli:
            if args.interactive:
                await cli.interactive_mode()
            elif args.command:
                if args.command == "list":
                    await cli.list_files(args.path, args.recursive)
                elif args.command == "search":
                    if not args.query:
                        print("错误: 需要查询词")
                        return
                    await cli.search_files(args.query, args.path)
                elif args.command == "status":
                    await cli.get_status()
                elif args.command == "system":
                    await cli.get_system_info()
                elif args.command == "index":
                    await cli.generate_index(args.force)
                else:
                    # 作为自然语言命令执行
                    result = await cli.execute_command(args.command)
                    if result.get("success"):
                        cli._print_command_result(result)
                    else:
                        print(f"失败: {result.get('message', '未知错误')}")
            else:
                parser.print_help()
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n操作被用户中断")
    except Exception as e:
        logger.error(f"CLI运行失败: {e}")
        print(f"错误: {e}")


if __name__ == "__main__":
    main()