"""
宪法规则引擎 - 确保所有操作符合宪法规则
"""
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import yaml

from config.settings import settings
from utils.logger import logger
from utils.path_utils import PathUtils
import logging  # 添加这一行

class ConstitutionEngine:
    """宪法规则引擎"""
    
    def __init__(self, constitution_path: Optional[str] = None):
        self.constitution_path = constitution_path or settings.constitution_path
        self.rules = []
        self.principles = []
        self.protected_directories = []
        self.security_exceptions = []
        self.last_updated = None
        
        self.load_constitution()
    
    def load_constitution(self) -> bool:
        """加载宪法规则"""
        try:
            constitution_file = PathUtils.normalize_path(self.constitution_path)
            if not constitution_file.exists():
                logger.warning(f"宪法文件不存在: {constitution_file}")
                self._load_default_rules()
                return False
            
            with open(constitution_file, 'r', encoding='utf-8') as f:
                constitution_data = yaml.safe_load(f)
            
            if not constitution_data:
                logger.warning("宪法文件为空")
                self._load_default_rules()
                return False
            
            # 加载规则
            self.principles = constitution_data.get('principles', [])
            self.rules = constitution_data.get('rules', [])
            self.protected_directories = constitution_data.get('protected_directories', [])
            self.security_exceptions = constitution_data.get('security_exceptions', [])
            self.last_updated = constitution_data.get('last_updated')
            
            logger.info(f"宪法规则已加载: {len(self.rules)} 条规则, {len(self.principles)} 条原则")
            return True
            
        except Exception as e:
            logger.error(f"加载宪法规则失败: {e}")
            self._load_default_rules()
            return False
    
    def _load_default_rules(self):
        """加载默认规则"""
        self.principles = [
            {
                "name": "安全第一",
                "description": "所有操作必须以安全为首要考虑",
                "enforcement": "required"
            }
        ]
        
        self.rules = [
            {
                "id": "DEFAULT-001",
                "name": "禁止删除系统文件",
                "description": "禁止删除系统关键文件",
                "condition": "operation.target_path.contains('system')",
                "action": "block",
                "priority": "critical"
            }
        ]
        
        self.protected_directories = ["/system", "/windows", "/program files"]
        logger.info("已加载默认宪法规则")
    
    def evaluate_operation(self, 
                          operation: Dict[str, Any], 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """评估操作是否符合宪法规则"""
        if not settings.constitution_enabled:
            return {"allowed": True, "reason": "宪法检查已禁用"}
        
        logger.info(f"评估操作: {operation.get('action', 'unknown')}")
        
        evaluation = {
            "allowed": True,
            "requires_confirmation": False,
            "blocked": False,
            "violations": [],
            "warnings": [],
            "confirmations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查基本原则
        self._check_principles(operation, evaluation, context)
        
        # 检查具体规则
        for rule in self.rules:
            self._check_rule(rule, operation, evaluation, context)
        
        # 检查受保护目录
        self._check_protected_directories(operation, evaluation)
        
        # 检查安全例外
        self._check_security_exceptions(operation, evaluation)
        
        # 确定最终状态
        if evaluation["blocked"]:
            evaluation["allowed"] = False
            evaluation["requires_confirmation"] = False
        
        logger.info(f"操作评估结果: 允许={evaluation['allowed']}, 需要确认={evaluation['requires_confirmation']}")
        return evaluation
    
    def _check_principles(self, 
                         operation: Dict[str, Any], 
                         evaluation: Dict[str, Any],
                         context: Optional[Dict[str, Any]] = None):
        """检查基本原则"""
        for principle in self.principles:
            principle_name = principle.get("name", "")
            enforcement = principle.get("enforcement", "recommended")
            
            if enforcement == "required":
                # 这里可以添加对特定原则的检查逻辑
                pass
    
    def _check_rule(self, 
                   rule: Dict[str, Any], 
                   operation: Dict[str, Any], 
                   evaluation: Dict[str, Any],
                   context: Optional[Dict[str, Any]] = None):
        """检查单个规则"""
        try:
            rule_id = rule.get("id", "unknown")
            rule_name = rule.get("name", "")
            condition = rule.get("condition", "")
            action = rule.get("action", "")
            priority = rule.get("priority", "medium")
            
            # 评估条件
            condition_met = self._evaluate_condition(condition, operation, context)
            if not condition_met:
                return
            
            # 根据动作类型处理
            if action == "block":
                evaluation["blocked"] = True
                evaluation["violations"].append({
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "priority": priority,
                    "message": rule.get("parameters", {}).get("message", "违反规则")
                })
                logger.warning(f"操作被规则阻止: {rule_id} - {rule_name}")
            
            elif action == "require_confirmation":
                evaluation["requires_confirmation"] = True
                confirmation_message = rule.get("parameters", {}).get(
                    "message", 
                    f"需要确认: {rule_name}"
                )
                evaluation["confirmations"].append({
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "message": confirmation_message,
                    "priority": priority
                })
                logger.info(f"操作需要确认: {rule_id} - {rule_name}")
            
            elif action == "log_operation":
                log_level = rule.get("parameters", {}).get("log_level", "INFO")
                logger.log(
                    getattr(logging, log_level.upper()),
                    f"规则触发的日志: {rule_name} - 操作: {operation.get('action')}"
                )
            
            elif action == "notify":
                evaluation["warnings"].append({
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "message": rule.get("parameters", {}).get("message", "规则警告"),
                    "priority": priority
                })
        
        except Exception as e:
            logger.error(f"检查规则时出错: {e}")
    
    def _evaluate_condition(self, 
                           condition: str, 
                           operation: Dict[str, Any], 
                           context: Optional[Dict[str, Any]] = None) -> bool:
        """评估条件表达式"""
        if not condition or condition == "always":
            return True
        
        try:
            # 简单的条件表达式解析
            # 支持: operation.field == value, operation.field.contains(value), etc.
            
            # 替换变量
            condition = self._replace_variables(condition, operation, context)
            
            # 简单的条件检查
            if "==" in condition:
                left, right = condition.split("==", 1)
                left = left.strip()
                right = right.strip().strip('"').strip("'")
                
                # 获取操作字段的值
                field_value = self._get_field_value(left, operation, context)
                return str(field_value) == right
            
            elif "!=" in condition:
                left, right = condition.split("!=", 1)
                left = left.strip()
                right = right.strip().strip('"').strip("'")
                
                field_value = self._get_field_value(left, operation, context)
                return str(field_value) != right
            
            elif "contains" in condition:
                left, right = condition.split("contains", 1)
                left = left.strip()
                right = right.strip().strip('"').strip("'")
                
                field_value = self._get_field_value(left, operation, context)
                return right in str(field_value)
            
            elif "startswith" in condition:
                left, right = condition.split("startswith", 1)
                left = left.strip()
                right = right.strip().strip('"').strip("'")
                
                field_value = self._get_field_value(left, operation, context)
                return str(field_value).startswith(right)
            
            elif "endswith" in condition:
                left, right = condition.split("endswith", 1)
                left = left.strip()
                right = right.strip().strip('"').strip("'")
                
                field_value = self._get_field_value(left, operation, context)
                return str(field_value).endswith(right)
            
            else:
                # 尝试作为Python表达式评估（安全限制）
                return False
        
        except Exception as e:
            logger.error(f"评估条件时出错: {condition} - {e}")
            return False
    
    def _replace_variables(self, 
                          condition: str, 
                          operation: Dict[str, Any], 
                          context: Optional[Dict[str, Any]] = None) -> str:
        """替换条件中的变量"""
        # 替换操作字段
        for key, value in operation.items():
            if isinstance(value, (str, int, float, bool)):
                placeholder = f"operation.{key}"
                if placeholder in condition:
                    condition = condition.replace(placeholder, str(value))
        
        # 替换配置变量
        config_vars = {
            "config.root_path": settings.root_path,
            "config.safe_mode": str(settings.safe_mode),
        }
        
        for var, value in config_vars.items():
            if var in condition:
                condition = condition.replace(var, str(value))
        
        return condition
    
    def _get_field_value(self, 
                        field_path: str, 
                        operation: Dict[str, Any], 
                        context: Optional[Dict[str, Any]] = None) -> Any:
        """获取字段值"""
        if field_path.startswith("operation."):
            field_name = field_path[10:]  # 移除 "operation."
            return operation.get(field_name)
        
        elif field_path.startswith("context.") and context:
            field_name = field_path[8:]  # 移除 "context."
            return context.get(field_name)
        
        elif field_path.startswith("config."):
            field_name = field_path[7:]  # 移除 "config."
            return getattr(settings, field_name, None)
        
        return None
    
    def _check_protected_directories(self, 
                                    operation: Dict[str, Any], 
                                    evaluation: Dict[str, Any]):
        """检查受保护目录"""
        target_path = operation.get("target_path", "")
        if not target_path:
            return
        
        root_path = PathUtils.normalize_path(settings.root_path)
        
        for protected in self.protected_directories:
            protected_path = root_path / protected.lstrip("/")
            
            try:
                target_abs = PathUtils.normalize_path(target_path)
                if target_abs == protected_path or target_abs.is_relative_to(protected_path):
                    evaluation["blocked"] = True
                    evaluation["violations"].append({
                        "rule_id": "PROTECTED-DIR",
                        "rule_name": "受保护目录访问",
                        "priority": "high",
                        "message": f"禁止访问受保护目录: {protected}"
                    })
                    break
            except Exception:
                continue
    
    def _check_security_exceptions(self, 
                                  operation: Dict[str, Any], 
                                  evaluation: Dict[str, Any]):
        """检查安全例外"""
        action = operation.get("action", "")
        
        for exception in self.security_exceptions:
            if exception.get("operation") == action:
                requires = exception.get("requires", "")
                
                if requires == "admin_approval":
                    evaluation["requires_confirmation"] = True
                    evaluation["confirmations"].append({
                        "rule_id": "SECURITY-EXCEPTION",
                        "rule_name": "安全例外操作",
                        "message": "此操作需要管理员批准",
                        "priority": "critical"
                    })
                
                elif requires == "multiple_confirmations":
                    evaluation["requires_confirmation"] = True
                    evaluation["confirmations"].append({
                        "rule_id": "SECURITY-EXCEPTION",
                        "rule_name": "多重确认操作",
                        "message": "此操作需要多重确认",
                        "priority": "critical"
                    })
    
    def get_rule_summary(self) -> Dict[str, Any]:
        """获取规则摘要"""
        return {
            "total_rules": len(self.rules),
            "total_principles": len(self.principles),
            "protected_directories": self.protected_directories,
            "last_updated": self.last_updated,
            "enabled": settings.constitution_enabled
        }
    
    def add_rule(self, rule: Dict[str, Any]) -> bool:
        """添加新规则"""
        try:
            # 验证规则
            required_fields = ["id", "name", "condition", "action"]
            for field in required_fields:
                if field not in rule:
                    logger.error(f"规则缺少必要字段: {field}")
                    return False
            
            # 检查ID是否重复
            rule_id = rule["id"]
            for existing_rule in self.rules:
                if existing_rule.get("id") == rule_id:
                    logger.error(f"规则ID已存在: {rule_id}")
                    return False
            
            self.rules.append(rule)
            logger.info(f"新规则已添加: {rule_id}")
            return True
        
        except Exception as e:
            logger.error(f"添加规则失败: {e}")
            return False
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除规则"""
        for i, rule in enumerate(self.rules):
            if rule.get("id") == rule_id:
                self.rules.pop(i)
                logger.info(f"规则已移除: {rule_id}")
                return True
        
        logger.warning(f"规则未找到: {rule_id}")
        return False
    
    def save_constitution(self) -> bool:
        """保存宪法规则到文件"""
        try:
            constitution_data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "principles": self.principles,
                "rules": self.rules,
                "protected_directories": self.protected_directories,
                "security_exceptions": self.security_exceptions
            }
            
            constitution_file = PathUtils.normalize_path(self.constitution_path)
            constitution_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(constitution_file, 'w', encoding='utf-8') as f:
                yaml.dump(constitution_data, f, allow_unicode=True, sort_keys=False)
            
            logger.info(f"宪法规则已保存: {constitution_file}")
            return True
        
        except Exception as e:
            logger.error(f"保存宪法规则失败: {e}")
            return False