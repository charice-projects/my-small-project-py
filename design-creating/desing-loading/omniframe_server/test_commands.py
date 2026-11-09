# [file name]: enhanced_test_commands.py
[file content begin]
"""
增强版测试命令 - 支持交互式测试
"""
import requests
import json
import time
import uuid


class CommandTester:
    """命令测试器"""
    
    def __init__(self, base_url="http://192.168.2.181:8080"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/commands/execute"
        self.session_id = None
    
    def create_session(self):
        """创建测试会话"""
        self.session_id = str(uuid.uuid4())
        return self.session_id
    
    def test_command(self, command_text, expected_action=None, expected_success=None, is_interactive=False):
        """测试单个命令"""
        headers = {"Content-Type": "application/json"}
        data = {
            "command": command_text,
            "session_id": self.session_id
        }
        
        try:
            start_time = time.time()
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response_time = time.time() - start_time
            
            result = response.json()
            
            print(f"\n{'='*60}")
            print(f"命令: {command_text}")
            print(f"会话ID: {self.session_id}")
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {response_time:.2f}s")
            print(f"成功: {result.get('success', 'unknown')}")
            print(f"Action: {result.get('action', 'unknown')}")
            print(f"消息: {result.get('message', 'No message')}")
            
            # 检查交互式标记
            if result.get('interactive'):
                print(f"🔵 交互式: 需要后续输入")
                print(f"建议: {result.get('suggestions', [])}")
            
            # 显示详细参数
            if 'parameters' in result:
                print(f"参数: {json.dumps(result['parameters'], ensure_ascii=False, indent=2)}")
            
            # 评估测试结果
            test_passed = True
            reasons = []
            
            if expected_action and result.get('action') != expected_action:
                test_passed = False
                reasons.append(f"Action不匹配: 期望 {expected_action}, 实际 {result.get('action')}")
            
            if expected_success is not None and result.get('success') != expected_success:
                test_passed = False
                reasons.append(f"Success不匹配: 期望 {expected_success}, 实际 {result.get('success')}")
            
            if is_interactive and not result.get('interactive'):
                test_passed = False
                reasons.append("期望交互式响应但未收到")
            
            if test_passed:
                print(f"✅ 测试通过")
            else:
                print(f"❌ 测试失败: {', '.join(reasons)}")
            
            return {
                "result": result,
                "passed": test_passed,
                "reasons": reasons,
                "response_time": response_time
            }
            
        except requests.exceptions.Timeout:
            print(f"\n{'='*60}")
            print(f"命令: {command_text}")
            print("❌ 请求超时")
            return None
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"命令: {command_text}")
            print(f"❌ 请求异常: {e}")
            return None
    
    def test_interactive_flow(self):
        """测试交互式流程"""
        print("\n" + "="*60)
        print("测试交互式搜索流程")
        print("="*60)
        
        # 步骤1: 输入 search（无关键词）
        print("\n步骤1: 输入 'search'（无关键词）")
        step1 = self.test_command("search", expected_action="search_prompt", expected_success=True, is_interactive=True)
        
        if step1 and step1["passed"] and step1["result"].get("requires_followup"):
            # 步骤2: 输入关键词
            print("\n步骤2: 输入关键词 'test'")
            step2 = self.test_command("test", expected_action="search", expected_success=True)
            
            return step1["passed"] and step2["passed"]
        
        return False
    
    def test_all(self):
        """测试所有命令"""
        # 创建测试会话
        self.create_session()
        
        test_cases = [
            # 系统状态命令（期望成功）
            ("show status", "system_info", True, False),
            ("status", "system_info", True, False),
            ("system info", "system_info", True, False),
            ("system status", "system_info", True, False),
            ("health", "system_info", True, False),
            ("显示系统状态", "system_info", True, False),
            ("系统状态", "system_info", True, False),
            
            # 列表命令（期望成功）
            ("show files", "list", True, False),
            ("list files", "list", True, False),
            ("ls", "list", True, False),
            ("list", "list", True, False),
            ("显示文件", "list", True, False),
            ("列出文件", "list", True, False),
            ("列出文档", "list", True, False),
            
            # 搜索命令
            ("search test", "search", True, False),  # 有关键词，期望成功
            ("find file", "search", True, False),    # 有关键词，期望成功
            ("搜索文档", "search", True, False),      # 中文搜索，期望成功
            ("查找图片", "search", True, False),      # 中文搜索，期望成功
            ("search", "search_prompt", True, True), # 无关键词，期望交互式提示
            
            # 索引命令（期望成功）
            ("index", "index", True, False),
            ("生成索引", "index", True, False),
            ("初始化索引", "index", True, False),
            ("更新索引", "index", True, False),
            
            # 其他命令（期望成功）
            ("查看最近文件", "recent", True, False),
            ("历史记录", "history", True, False),
            ("目录树", "tree", True, False),
        ]
        
        print("开始测试命令解析系统...")
        print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"会话ID: {self.session_id}")
        print(f"{'='*60}")
        
        results = []
        for command, expected_action, expected_success, is_interactive in test_cases:
            print(f"\n测试: {command}")
            print(f"预期: Action={expected_action}, Success={expected_success}, Interactive={is_interactive}")
            result = self.test_command(command, expected_action, expected_success, is_interactive)
            results.append((command, expected_action, expected_success, is_interactive, result))
        
        # 测试交互式流程
        print(f"\n{'='*60}")
        print("测试交互式搜索流程")
        interactive_result = self.test_interactive_flow()
        results.append(("interactive_flow", "mixed", True, True, interactive_result))
        
        # 汇总结果
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results):
        """打印汇总结果"""
        print(f"\n{'='*60}")
        print("测试结果汇总:")
        print(f"{'='*60}")
        
        successful = 0
        failed = 0
        total = len(results)
        
        for command, expected_action, expected_success, is_interactive, result in results:
            if command == "interactive_flow":
                if result:
                    status = "✅ 成功"
                    successful += 1
                else:
                    status = "❌ 失败"
                    failed += 1
                print(f"{status}: {command}")
            elif result and result.get("passed", False):
                status = "✅ 成功"
                successful += 1
            else:
                status = "❌ 失败"
                failed += 1
            
            if command != "interactive_flow":
                print(f"{status}: {command} - 期望: Action={expected_action}, Success={expected_success}")
        
        print(f"\n{'='*60}")
        print(f"总计: {total} 个测试")
        print(f"成功: {successful}")
        print(f"失败: {failed}")
        success_rate = (successful/total)*100 if total > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
        
        # 显示失败详情
        if failed > 0:
            print(f"\n{'='*60}")
            print("失败详情:")
            for command, expected_action, expected_success, is_interactive, result in results:
                if command == "interactive_flow":
                    if not result:
                        print(f"\n命令: {command}")
                        print(f"交互式流程测试失败")
                elif result and not result.get("passed", False):
                    print(f"\n命令: {command}")
                    print(f"预期: Action={expected_action}, Success={expected_success}")
                    if "result" in result:
                        print(f"实际Action: {result['result'].get('action', 'unknown')}")
                        print(f"实际Success: {result['result'].get('success', 'unknown')}")
                        print(f"错误信息: {result['result'].get('message', 'No message')}")
                    print(f"失败原因: {', '.join(result.get('reasons', []))}")


if __name__ == "__main__":
    tester = CommandTester()
    tester.test_all()
[file content end]