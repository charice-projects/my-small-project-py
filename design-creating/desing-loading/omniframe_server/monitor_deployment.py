# [file name]: monitor_deployment.py
[file content begin]
"""
部署监控脚本 - 监控增强功能部署状态
"""
import requests
import time
import json
from datetime import datetime
import threading


class DeploymentMonitor:
    """部署监控器"""
    
    def __init__(self, base_url="http://192.168.2.181:8080", check_interval=10):
        self.base_url = base_url
        self.check_interval = check_interval
        self.running = False
        self.metrics = {
            "checks": 0,
            "successful": 0,
            "failed": 0,
            "response_times": []
        }
    
    def check_health(self):
        """检查服务健康状态"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=5)
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            self.metrics["checks"] += 1
            self.metrics["response_times"].append(response_time)
            
            if response.status_code == 200:
                self.metrics["successful"] += 1
                return True, f"正常 (响应时间: {response_time:.2f}ms)"
            else:
                self.metrics["failed"] += 1
                return False, f"异常 (状态码: {response.status_code})"
        
        except Exception as e:
            self.metrics["checks"] += 1
            self.metrics["failed"] += 1
            return False, f"连接失败: {str(e)}"
    
    def check_enhanced_features(self):
        """检查增强功能"""
        tests = [
            ("search", "search_prompt", True),
            ("search test", "search", True),
            ("show status", "system_info", True)
        ]
        
        results = []
        
        for command, expected_action, expected_success in tests:
            try:
                response = requests.post(
                    f"{self.base_url}/api/commands/execute",
                    json={"command": command},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    passed = (
                        result.get("action") == expected_action and
                        result.get("success") == expected_success
                    )
                    
                    results.append({
                        "command": command,
                        "passed": passed,
                        "action": result.get("action"),
                        "success": result.get("success"),
                        "interactive": result.get("interactive", False)
                    })
                else:
                    results.append({
                        "command": command,
                        "passed": False,
                        "error": f"状态码: {response.status_code}"
                    })
            
            except Exception as e:
                results.append({
                    "command": command,
                    "passed": False,
                    "error": str(e)
                })
        
        return results
    
    def monitor_loop(self):
        """监控循环"""
        print(f"开始监控服务: {self.base_url}")
        print(f"检查间隔: {self.check_interval}秒")
        print("-" * 60)
        
        self.running = True
        
        while self.running:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 检查健康状态
            health_ok, health_msg = self.check_health()
            health_status = "✅" if health_ok else "❌"
            
            print(f"[{timestamp}] 健康检查: {health_status} {health_msg}")
            
            # 每5次检查执行一次增强功能测试
            if self.metrics["checks"] % 5 == 0:
                print(f"[{timestamp}] 执行增强功能测试...")
                feature_results = self.check_enhanced_features()
                
                for result in feature_results:
                    status = "✅" if result["passed"] else "❌"
                    interactive = "🔵" if result.get("interactive") else ""
                    print(f"  {status}{interactive} {result['command']}: "
                          f"action={result.get('action')}, success={result.get('success')}")
                
                # 打印统计信息
                avg_response_time = sum(self.metrics["response_times"][-10:]) / min(10, len(self.metrics["response_times"])) if self.metrics["response_times"] else 0
                success_rate = (self.metrics["successful"] / self.metrics["checks"] * 100) if self.metrics["checks"] > 0 else 0
                
                print(f"[{timestamp}] 统计: 检查={self.metrics['checks']}, "
                      f"成功率={success_rate:.1f}%, "
                      f"平均响应={avg_response_time:.2f}ms")
                print("-" * 60)
            
            time.sleep(self.check_interval)
    
    def start(self):
        """启动监控"""
        thread = threading.Thread(target=self.monitor_loop)
        thread.daemon = True
        thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n停止监控...")
            self.running = False
    
    def get_report(self):
        """获取监控报告"""
        if not self.metrics["response_times"]:
            avg_response_time = 0
        else:
            avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
        
        success_rate = (self.metrics["successful"] / self.metrics["checks"] * 100) if self.metrics["checks"] > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_checks": self.metrics["checks"],
            "successful_checks": self.metrics["successful"],
            "failed_checks": self.metrics["failed"],
            "success_rate": success_rate,
            "avg_response_time_ms": avg_response_time,
            "status": "healthy" if success_rate > 95 else "degraded"
        }


if __name__ == "__main__":
    monitor = DeploymentMonitor()
    monitor.start()
[file content end]