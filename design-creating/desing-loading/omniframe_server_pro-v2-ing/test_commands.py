# enhanced_test_commands.py
import requests
import json
import time

def test_command(command_text):
    """测试单个命令"""
    url = "http://192.168.2.181:8080/api/commands/execute"
    headers = {"Content-Type": "application/json"}
    data = {"command": command_text}
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response_time = time.time() - start_time
        
        result = response.json()
        
        print(f"\n{'='*60}")
        print(f"命令: {command_text}")
        print(f"状态码: {response.status_code}")
        print(f"响应时间: {response_time:.2f}s")
        print(f"成功: {result.get('success', 'unknown')}")
        print(f"Action: {result.get('action', 'unknown')}")
        print(f"消息: {result.get('message', 'No message')}")
        
        # 显示详细参数
        if 'parameters' in result:
            print(f"参数: {json.dumps(result['parameters'], ensure_ascii=False, indent=2)}")
        
        if not result.get('success', False):
            print(f"❌ 错误: {result.get('message', 'Unknown error')}")
            if 'supported_actions' in result:
                print(f"支持的Actions: {result['supported_actions']}")
        else:
            print(f"✅ 成功")
            if 'data' in result:
                print(f"数据数量: {len(result['data'])}")
        
        return result
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

def test_all():
    """测试所有命令"""
    test_cases = [
        # 系统状态命令
        ("show status", "应该返回system_info"),
        ("status", "应该返回system_info"),
        ("system info", "应该返回system_info"),
        ("system status", "应该返回system_info"),
        ("health", "应该返回system_info"),
        ("显示系统状态", "应该返回system_info"),
        ("系统状态", "应该返回system_info"),
        
        # 列表命令
        ("show files", "应该返回list"),
        ("list files", "应该返回list"),
        ("ls", "应该返回list"),
        ("list", "应该返回list"),
        ("显示文件", "应该返回list"),
        ("列出文件", "应该返回list"),
        ("列出文档", "应该返回list"),
        
        # 搜索命令
        ("search test", "应该返回search并搜索test"),
        ("find file", "应该返回search并搜索file"),
        ("搜索文档", "应该返回search并搜索文档"),
        ("查找图片", "应该返回search并搜索图片"),
        ("search", "应该失败，缺少关键词"),
        
        # 索引命令
        ("index", "应该返回index"),
        ("生成索引", "应该返回index"),
        ("初始化索引", "应该返回index"),
        ("更新索引", "应该返回index"),
        
        # 其他命令
        ("查看最近文件", "应该返回recent"),
        ("历史记录", "应该返回history"),
        ("目录树", "应该返回tree"),
    ]
    
    print("开始测试命令解析系统...")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    results = []
    for command, expected in test_cases:
        print(f"\n测试: {command}")
        print(f"预期: {expected}")
        result = test_command(command)
        results.append((command, expected, result))
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总:")
    print(f"{'='*60}")
    
    successful = 0
    failed = 0
    total = len(results)
    
    for command, expected, result in results:
        if result and result.get('success', False):
            status = "✅ 成功"
            successful += 1
        else:
            status = "❌ 失败"
            failed += 1
        
        print(f"{status}: {command} - {expected}")
    
    print(f"\n{'='*60}")
    print(f"总计: {total} 个命令")
    print(f"成功: {successful}")
    print(f"失败: {failed}")
    print(f"成功率: {(successful/total)*100:.1f}%")
    
    # 显示失败详情
    if failed > 0:
        print(f"\n{'='*60}")
        print("失败详情:")
        for command, expected, result in results:
            if not result or not result.get('success', False):
                print(f"\n命令: {command}")
                print(f"预期: {expected}")
                if result:
                    print(f"实际Action: {result.get('action', 'unknown')}")
                    print(f"错误信息: {result.get('message', 'No message')}")

if __name__ == "__main__":
    test_all()