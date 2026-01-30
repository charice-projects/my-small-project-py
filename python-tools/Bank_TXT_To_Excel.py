"""
智能银行流水转换工具 v3.6 - 交互式版本
功能：智能识别多种银行流水格式，TXT转换为结构化Excel文件
支持银行：九江银行、工商银行、建设银行、农业银行、中国银行、招商银行等常见格式
作者：西施先生
日期：2026-01-13

修复问题：
1. 修复交易数据解析问题，正确解析九江银行流水
2. 基于简单版本改进，保持灵活性同时增强解析能力
3. 优化正则表达式匹配模式

-------------------------------------------------------------
【前期工作】
    -->配合PDF24 Creator 先将银行的PDF流水转换为TXT文档，
然后在使用本脚本。

【为什么不直接在线转换】
    -->因为在线存在数据泄露的风险
    -->因为在线转化后的Excel错误太多，没法用
"""





import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set, Any
from collections import defaultdict, Counter
import warnings
import unicodedata
import math
from dataclasses import dataclass
from enum import Enum

# 忽略警告
warnings.filterwarnings('ignore')

# ==================== 配置和常量 ====================

class BankType(Enum):
    """银行类型枚举"""
    UNKNOWN = "未知"
    JIUJIANG = "九江银行"
    ICBC = "工商银行"
    CCB = "建设银行"
    ABC = "农业银行"
    BOC = "中国银行"
    CMB = "招商银行"
    CITIC = "中信银行"
    CIB = "兴业银行"
    SPDB = "浦发银行"
    CGB = "广发银行"
    CEB = "光大银行"
    PINGAN = "平安银行"
    POST = "邮政储蓄"
    COMM = "交通银行"
    HXB = "华夏银行"

class TransactionType(Enum):
    """交易类型枚举"""
    TRANSFER = "转账"
    WITHDRAWAL = "取现"
    DEPOSIT = "存款"
    CONSUMPTION = "消费"
    SALARY = "工资"
    INTEREST = "利息"
    FEE = "手续费"
    REPAYMENT = "还款"
    LOAN = "贷款"
    OTHER = "其他"

@dataclass
class BankPattern:
    """银行模式配置"""
    bank_type: BankType
    name_patterns: List[str]  # 银行名称识别模式
    date_patterns: List[str]  # 日期格式模式
    amount_patterns: List[str]  # 金额格式模式
    transaction_start_markers: List[str]  # 交易开始标记
    account_info_markers: List[str]  # 账户信息标记
    column_mapping: Dict[str, str]  # 列名映射
    encoding_preference: str = "utf-8"  # 编码偏好

# 银行模式配置
BANK_PATTERNS = {
    BankType.JIUJIANG: BankPattern(
        bank_type=BankType.JIUJIANG,
        name_patterns=["九江银行", "Bank of JiuJiang", "JiuJiang Bank"],
        date_patterns=[r'\d{8}'],
        amount_patterns=[r'[+-]?\d{1,3}(?:,\d{3})*\.?\d*'],
        transaction_start_markers=["记账日期", "Date", "交易日期"],
        account_info_markers=["姓名:", "账号:", "Account No", "账户类型:"],
        column_mapping={
            "date": "日期",
            "currency": "货币",
            "amount": "交易金额",
            "balance": "余额",
            "type": "交易类型",
            "counterparty": "对方信息",
            "account": "对方账号"
        }
    ),
    BankType.ICBC: BankPattern(
        bank_type=BankType.ICBC,
        name_patterns=["工商银行", "ICBC", "Industrial and Commercial Bank"],
        date_patterns=[r'\d{4}-\d{2}-\d{2}', r'\d{8}'],
        amount_patterns=[r'[+-]?\d{1,3}(?:,\d{3})*\.?\d*'],
        transaction_start_markers=["交易日期", "记账日期"],
        account_info_markers=["户名:", "账号:", "客户编号:"],
        column_mapping={
            "date": "交易日期",
            "currency": "币种",
            "amount": "发生额",
            "balance": "余额",
            "type": "业务摘要",
            "counterparty": "对方户名",
            "account": "对方账号"
        }
    ),
    BankType.CCB: BankPattern(
        bank_type=BankType.CCB,
        name_patterns=["建设银行", "CCB", "China Construction Bank"],
        date_patterns=[r'\d{4}/\d{2}/\d{2}', r'\d{8}'],
        amount_patterns=[r'[+-]?\d{1,3}(?:,\d{3})*\.?\d*'],
        transaction_start_markers=["交易日期", "记账日期"],
        account_info_markers=["户名:", "账号:", "客户号:"],
        column_mapping={
            "date": "交易日期",
            "currency": "币种",
            "amount": "借方金额/贷方金额",
            "balance": "余额",
            "type": "摘要",
            "counterparty": "对方户名",
            "account": "对方账号"
        }
    ),
    BankType.CMB: BankPattern(
        bank_type=BankType.CMB,
        name_patterns=["招商银行", "CMB", "China Merchants Bank"],
        date_patterns=[r'\d{4}-\d{2}-\d{2}', r'\d{8}'],
        amount_patterns=[r'[+-]?\d{1,3}(?:,\d{3})*\.?\d*'],
        transaction_start_markers=["交易日期", "记账日期"],
        account_info_markers=["户名:", "卡号:", "账号:"],
        column_mapping={
            "date": "交易日期",
            "currency": "币种",
            "amount": "收入/支出",
            "balance": "余额",
            "type": "交易类型",
            "counterparty": "对方户名",
            "account": "对方账号"
        }
    )
}

# ==================== 工具函数 ====================

def clean_text(text: str) -> str:
    """清理文本：移除颜色代码、控制字符、乱码"""
    if not text:
        return ""
    
    # 移除ANSI颜色代码
    text = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)
    
    # 移除其他控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # 移除常见乱码字符
    text = re.sub(r'[���]', '', text)
    
    # 标准化空格
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def normalize_text(text: str) -> str:
    """标准化文本：移除多余空格、换行符等"""
    if not text:
        return ""
    
    text = clean_text(text)
    
    # 移除不可见字符，但保留常见标点
    text = ''.join(char for char in text if char.isprintable() or char in '，。！？；："\'').strip()
    
    return text.strip()

def detect_encoding(file_path: str) -> Tuple[str, float]:
    """智能检测文件编码和置信度"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'utf-16-le', 'utf-16-be', 'iso-8859-1', 'cp936', 'latin-1']
    
    best_encoding = 'utf-8'
    best_confidence = 0.0
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read(10000)
                
                # 检查是否有明显乱码
                garbage_chars = sum(1 for c in content if c in '���')
                total_chars = len(content)
                
                if total_chars == 0:
                    continue
                
                garbage_ratio = garbage_chars / total_chars
                
                # 检查中文字符比例
                chinese_chars = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
                chinese_ratio = chinese_chars / total_chars
                
                confidence = chinese_ratio * (1 - garbage_ratio)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_encoding = encoding
                    
        except Exception as e:
            continue
    
    return best_encoding, best_confidence

def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # 移除千位分隔符和货币符号
        value = value.strip()
        
        # 处理常见金额格式
        value = value.replace(',', '').replace(' ', '')
        
        # 处理负数
        if value.startswith('(') and value.endswith(')'):
            value = '-' + value[1:-1]
        elif value.startswith('-') or value.startswith('+'):
            pass  # 保留符号
        elif 'CR' in value or 'cr' in value:  # 贷方余额
            value = value.replace('CR', '').replace('cr', '')
            value = '-' + value
        
        try:
            return float(value)
        except:
            # 尝试提取数字
            match = re.search(r'[-+]?\d*\.?\d+', value)
            if match:
                try:
                    return float(match.group())
                except:
                    return default
    return default

def extract_date_ranges(text: str) -> List[Tuple[datetime, datetime]]:
    """从文本中智能提取日期范围"""
    date_ranges = []
    
    # 多种日期范围模式
    patterns = [
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*[至到\-~]\s*(\d{4})年(\d{1,2})月(\d{1,2})日', '%Y年%m月%d日'),
        (r'(\d{4})-(\d{1,2})-(\d{1,2})\s*[至到\-~]\s*(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
        (r'(\d{4})/(\d{1,2})/(\d{1,2})\s*[至到\-~]\s*(\d{4})/(\d{1,2})/(\d{1,2})', '%Y/%m/%d'),
        (r'(\d{4})(\d{2})(\d{2})\s*[至到\-~]\s*(\d{4})(\d{2})(\d{2})', '%Y%m%d'),
    ]
    
    for pattern, date_format in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                groups = match.groups()
                if len(groups) >= 6:
                    # 构建日期字符串
                    if date_format == '%Y%m%d':
                        start_str = f"{groups[0]}{groups[1]}{groups[2]}"
                        end_str = f"{groups[3]}{groups[4]}{groups[5]}"
                        start_date = datetime.strptime(start_str, '%Y%m%d')
                        end_date = datetime.strptime(end_str, '%Y%m%d')
                    elif date_format == '%Y-%m-%d':
                        start_str = f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                        end_str = f"{groups[3]}-{groups[4].zfill(2)}-{groups[5].zfill(2)}"
                        start_date = datetime.strptime(start_str, '%Y-%m-%d')
                        end_date = datetime.strptime(end_str, '%Y-%m-%d')
                    elif date_format == '%Y/%m/%d':
                        start_str = f"{groups[0]}/{groups[1].zfill(2)}/{groups[2].zfill(2)}"
                        end_str = f"{groups[3]}/{groups[4].zfill(2)}/{groups[5].zfill(2)}"
                        start_date = datetime.strptime(start_str, '%Y/%m/%d')
                        end_date = datetime.strptime(end_str, '%Y/%m/%d')
                    elif date_format == '%Y年%m月%d日':
                        start_str = f"{groups[0]}年{groups[1].zfill(2)}月{groups[2].zfill(2)}日"
                        end_str = f"{groups[3]}年{groups[4].zfill(2)}月{groups[5].zfill(2)}日"
                        start_date = datetime.strptime(start_str, '%Y年%m月%d日')
                        end_date = datetime.strptime(end_str, '%Y年%m月%d日')
                    
                    date_ranges.append((start_date, end_date))
            except:
                continue
    
    return date_ranges

def detect_bank_type(content: str) -> Tuple[BankType, float]:
    """检测银行类型和置信度"""
    content_lower = content.lower()
    
    # 常见银行关键词
    bank_keywords = {
        BankType.JIUJIANG: ["九江银行", "jiujiang"],
        BankType.ICBC: ["工商银行", "icbc", "industrial and commercial"],
        BankType.CCB: ["建设银行", "ccb", "construction bank"],
        BankType.ABC: ["农业银行", "abc", "agricultural bank"],
        BankType.BOC: ["中国银行", "boc", "bank of china"],
        BankType.CMB: ["招商银行", "cmb", "merchants bank"],
        BankType.COMM: ["交通银行", "bank of communications", "bcm"],
        BankType.CITIC: ["中信银行", "citic"],
        BankType.CIB: ["兴业银行", "cib", "industrial bank"],
        BankType.SPDB: ["浦发银行", "spdb", "pudong development"],
        BankType.POST: ["邮政储蓄", "postal savings"],
    }
    
    best_match = BankType.UNKNOWN
    best_score = 0.0
    
    for bank_type, keywords in bank_keywords.items():
        score = 0.0
        total_keywords = len(keywords)
        
        for keyword in keywords:
            if keyword.lower() in content_lower:
                score += 1.0
        
        if total_keywords > 0:
            final_score = score / total_keywords
            if final_score > best_score:
                best_score = final_score
                best_match = bank_type
    
    return best_match, best_score

def parse_counterparty_info(text: str) -> Tuple[str, Optional[str]]:
    """
    智能解析对方信息
    返回: (对方姓名/名称, 对方账号)
    """
    if not text:
        return "", None
    
    text = normalize_text(text)
    
    # 尝试分离姓名和账号
    # 情况1: 包含明显的账号（长数字）
    account_patterns = [
        r'\b\d{16,19}\b',  # 银行卡号
        r'\b\d{12,15}\b',  # 中等长度账号
        r'\b\d{8,11}\b',   # 短账号
    ]
    
    for pattern in account_patterns:
        matches = re.findall(pattern, text)
        if matches:
            account = matches[0]
            # 从文本中移除账号
            name_part = re.sub(pattern, '', text).strip()
            # 清理多余的分隔符
            name_part = re.sub(r'[\s\-_]+$', '', name_part)
            return name_part, account
    
    return text, None

# ==================== 交互式输入函数 ====================

def get_input_file_path() -> str:
    """获取输入文件路径"""
    while True:
        print("\n[提示] 请输入银行流水文件路径：")
        print("（支持拖拽文件到此处，或直接输入路径）")
        
        # 获取用户输入
        input_path = input("> ").strip()
        
        # 处理拖拽文件（可能包含引号）
        input_path = input_path.strip('"\'')
        
        # 检查文件是否存在
        if not input_path:
            print("[警告] 输入不能为空，请重新输入！")
            continue
            
        if not os.path.exists(input_path):
            print(f"[错误] 文件不存在: {input_path}")
            print("[提示] 请检查路径是否正确，或使用绝对路径。")
            
            # 提供建议
            current_dir = os.getcwd()
            print(f"[信息] 当前目录: {current_dir}")
            
            # 显示当前目录下的txt文件
            txt_files = [f for f in os.listdir(current_dir) if f.lower().endswith('.txt')]
            if txt_files:
                print("[信息] 当前目录下的txt文件:")
                for i, file in enumerate(txt_files[:10], 1):
                    print(f"  {i}. {file}")
                if len(txt_files) > 10:
                    print(f"  ... 还有 {len(txt_files) - 10} 个文件")
            continue
        
        # 检查文件是否为文本文件
        if not input_path.lower().endswith('.txt'):
            print("[警告] 文件扩展名不是.txt，但将继续尝试处理。")
            confirm = input("[询问] 是否继续？(y/n): ").strip().lower()
            if confirm != 'y':
                continue
        
        # 检查文件大小
        file_size = os.path.getsize(input_path)
        if file_size == 0:
            print("[错误] 文件为空！")
            continue
            
        if file_size > 100 * 1024 * 1024:  # 100MB
            print(f"[警告] 文件较大 ({file_size/1024/1024:.1f}MB)，处理可能需要一些时间。")
            confirm = input("[询问] 是否继续？(y/n): ").strip().lower()
            if confirm != 'y':
                continue
        
        return input_path

def get_output_file_path(input_path: str) -> str:
    """获取输出文件路径"""
    input_path_obj = Path(input_path)
    default_output = input_path_obj.with_suffix('.xlsx')
    
    print("\n[提示] 请输入输出Excel文件路径：")
    print(f"（直接回车将使用默认路径: {default_output}）")
    
    output_path = input("> ").strip()
    output_path = output_path.strip('"\'')
    
    # 如果用户直接回车，使用默认路径
    if not output_path:
        output_path = str(default_output)
        print(f"[信息] 使用默认输出路径: {output_path}")
    
    # 确保输出路径有正确的扩展名
    if not output_path.lower().endswith(('.xlsx', '.xls')):
        output_path = output_path + '.xlsx'
    
    # 检查输出目录是否存在
    output_dir = os.path.dirname(output_path) or os.getcwd()
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"[信息] 已创建输出目录: {output_dir}")
        except Exception as e:
            print(f"[错误] 无法创建输出目录: {e}")
            # 使用输入文件所在目录
            output_path = str(default_output)
            print(f"[提示] 将使用默认路径: {output_path}")
    
    # 检查文件是否已存在
    if os.path.exists(output_path):
        print("[警告] 输出文件已存在！")
        choice = input("[询问] 是否覆盖？(y=覆盖, n=重命名, c=取消): ").strip().lower()
        
        if choice == 'c':
            print("[提示] 操作已取消。")
            return get_output_file_path(input_path)
        elif choice == 'n':
            # 生成新文件名
            base_name = Path(output_path).stem
            counter = 1
            while True:
                new_name = f"{base_name}_{counter}.xlsx"
                new_path = str(Path(output_path).with_name(new_name))
                if not os.path.exists(new_path):
                    output_path = new_path
                    print(f"[信息] 使用新文件名: {output_path}")
                    break
                counter += 1
        # 如果选择'y'，直接覆盖
    
    return output_path

def get_processing_mode() -> Dict[str, bool]:
    """获取处理模式选项"""
    print("\n[提示] 请选择处理模式：")
    print("1. 完整模式 (推荐) - 生成详细分析报告")
    print("2. 简单模式 - 仅生成交易明细")
    print("3. 详细模式 - 显示详细处理信息")
    print("4. 全部启用 - 完整+详细模式")
    print("（直接回车默认选择1 - 完整模式）")
    
    while True:
        choice = input("\n[输入] 请输入选项 (1-4, 默认1): ").strip()
        
        if not choice:
            choice = '1'
            print("[信息] 使用默认选项: 完整模式")
        
        if choice == '1':
            return {'simple': False, 'verbose': False, 'all': False}
        elif choice == '2':
            return {'simple': True, 'verbose': False, 'all': False}
        elif choice == '3':
            return {'simple': False, 'verbose': True, 'all': False}
        elif choice == '4':
            return {'simple': False, 'verbose': True, 'all': True}
        else:
            print("[错误] 无效选项，请重新选择！")

# ==================== 银行流水解析器 ====================

class BankStatementParser:
    """银行流水解析器 - 基于简单版本重构"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.bank_type = BankType.UNKNOWN
        self.confidence = 0.0
        self.lines = []
        self.account_info = {}
        self.transactions = []
        self.date_ranges = []
        
    def print_debug(self, message: str):
        """打印调试信息"""
        if self.verbose:
            print(f"[调试] {message}")
    
    def load_file(self, file_path: str) -> bool:
        """加载文件 - 使用UTF-8编码"""
        try:
            # 直接使用UTF-8编码读取
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 清理内容
            content = clean_text(content)
            
            if content:
                self.lines = content.splitlines()
            
            if not self.lines:
                print("[错误] 无法读取文件内容")
                return False
            
            # 检测银行类型
            content_sample = ' '.join(self.lines[:50])
            self.bank_type, self.confidence = detect_bank_type(content_sample)
            
            self.print_debug(f"检测到银行类型: {self.bank_type.value} (置信度: {self.confidence:.2f})")
            
            return True
            
        except Exception as e:
            print(f"[错误] 加载文件失败: {e}")
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                    content = f.read()
                
                content = clean_text(content)
                self.lines = content.splitlines()
                
                if self.lines:
                    content_sample = ' '.join(self.lines[:50])
                    self.bank_type, self.confidence = detect_bank_type(content_sample)
                    return True
            except:
                pass
            
            return False
    
    def parse_account_info(self):
        """解析账户信息 - 改进版"""
        self.account_info = {
            "银行类型": self.bank_type.value,
            "检测置信度": f"{self.confidence:.2%}",
            "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 查找账户信息区域
        for i, line in enumerate(self.lines):
            if '姓名:' in line or 'Name' in line:
                # 解析账户信息部分
                for j in range(i, min(i+20, len(self.lines))):
                    info_line = self.lines[j].strip()
                    
                    if '姓名:' in info_line:
                        account_name = info_line.split('姓名:')[1].strip()
                        # 提取姓名部分（可能包含多余空格）
                        account_name = account_name.split()[0] if account_name.split() else account_name
                        self.account_info['姓名'] = account_name
                    
                    elif '账号:' in info_line:
                        account_num = info_line.split('账号:')[1].strip()
                        account_num = account_num.split()[0] if account_num.split() else account_num
                        self.account_info['账号'] = account_num
                    
                    elif '账户类型:' in info_line:
                        account_type = info_line.split('账户类型:')[1].strip()
                        account_type = account_type.split()[0] if account_type.split() else account_type
                        self.account_info['账户类型'] = account_type
                    
                    elif '开户行:' in info_line:
                        bank_name = info_line.split('开户行:')[1].strip()
                        self.account_info['开户行'] = bank_name
                    
                    elif '申请时间:' in info_line:
                        apply_time = info_line.split('申请时间:')[1].strip()
                        self.account_info['申请时间'] = apply_time
                
                break
        
        # 如果没有找到账户信息，尝试其他模式
        if not self.account_info.get('姓名'):
            # 尝试从文件开头查找
            for line in self.lines[:50]:
                line_clean = normalize_text(line)
                
                # 尝试匹配姓名
                name_match = re.search(r'姓名[:：]\s*([^\s:：]+)', line_clean)
                if name_match:
                    self.account_info['姓名'] = name_match.group(1)
                
                # 尝试匹配账号
                account_match = re.search(r'账号[:：]\s*([^\s:：]+)', line_clean)
                if account_match:
                    self.account_info['账号'] = account_match.group(1)
    
    def find_transaction_start(self) -> int:
        """查找交易数据开始位置 - 基于简单版本改进"""
        # 查找表头行
        header_patterns = ['记账日期', 'Date']
        
        for i, line in enumerate(self.lines):
            if any(pattern in line for pattern in header_patterns):
                # 检查是否是真正的表头行（包含多个表头字段）
                if '交易金额' in line or 'Transaction Amount' in line:
                    self.print_debug(f"找到表头行: {i}")
                    # 返回表头行的下一行作为数据开始
                    return i + 1
        
        # 如果没有找到表头，尝试查找第一个交易数据行
        for i, line in enumerate(self.lines):
            line_clean = normalize_text(line)
            # 检查是否以8位日期开头
            if re.match(r'^\s*\d{8}\s+', line_clean):
                # 检查是否包含金额
                if re.search(r'[\d,]+\.\d{2}', line_clean):
                    self.print_debug(f"找到交易数据行: {i}")
                    return i
        
        return 0
    
    def is_valid_transaction_line(self, line: str) -> bool:
        """判断是否为有效的交易数据行"""
        if not line or len(line.strip()) < 10:
            return False
        
        line_clean = normalize_text(line)
        
        # 跳过明显不是交易的行
        skip_keywords = [
            "合同ID号:", "版本:", "温馨提示", "合计统计", "合计收入", "合计支出",
            "九江银行APP", "可验证合同真伪", "=====", "-----", "*****",
            "记账日期", "Date", "Currency", "Transaction Amount"
        ]
        
        for keyword in skip_keywords:
            if keyword in line_clean:
                return False
        
        # 检查是否是页码行（如 "1 / 87"）
        if re.search(r'\d+\s*/\s*\d+', line_clean) and len(line_clean) < 20:
            return False
        
        # 检查是否以8位日期开头
        if not re.match(r'^\s*\d{8}\s+', line_clean):
            return False
        
        # 检查是否包含金额格式
        if not re.search(r'[\d,]+\.\d{2}', line_clean):
            return False
        
        return True
    
    def parse_transaction_line(self, line: str, prev_line_was_transaction: bool = False) -> Optional[Dict]:
        """解析单行交易数据 - 基于简单版本的正则表达式"""
        if not self.is_valid_transaction_line(line):
            return None
        
        line_clean = normalize_text(line)
        
        # 九江银行交易行的典型格式：20250113    CNY        300,000.00            304,294.31          转账                       廖灵娇 6214830373529923
        # 使用简单版本的正则表达式
        pattern = r'(\d{8})\s+(\w+)\s+([\d,.-]+)\s+([\d,.-]+)\s+(\S+)\s+(.+)'
        match = re.match(pattern, line_clean)
        
        if match:
            try:
                date_str, currency, amount_str, balance_str, trans_type, counterparty = match.groups()
                
                # 格式化日期
                try:
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    weekday = date_obj.strftime('%A')
                except:
                    formatted_date = date_str
                    weekday = ""
                
                # 清理金额（移除逗号）
                amount_clean = amount_str.replace(',', '')
                balance_clean = balance_str.replace(',', '')
                
                # 转换金额
                try:
                    amount_num = float(amount_clean)
                    balance_num = float(balance_clean)
                except:
                    return None
                
                # 判断交易方向（收入/支出）
                if amount_num >= 0:
                    direction = '收入'
                    direction_zh = '收入'
                else:
                    direction = '支出'
                    direction_zh = '支出'
                    amount_num = abs(amount_num)  # 转为正数
                
                # 提取对手方姓名和账号
                counterparty_parts = counterparty.strip().split()
                counterparty_name = ""
                counterparty_account = ""
                
                if len(counterparty_parts) >= 2:
                    # 检查最后一部分是否是账号（长数字）
                    last_part = counterparty_parts[-1]
                    if re.match(r'^\d{8,19}$', last_part):
                        counterparty_name = ' '.join(counterparty_parts[:-1])
                        counterparty_account = last_part
                    else:
                        counterparty_name = counterparty
                else:
                    counterparty_name = counterparty
                
                # 智能分类交易类型
                transaction_category = self.classify_transaction(trans_type, counterparty_name, amount_num)
                
                transaction = {
                    '日期': formatted_date,
                    '星期': weekday,
                    '记账日期': date_str,
                    '货币': currency,
                    '交易金额': amount_num,
                    '交易方向': direction,
                    '交易方向中文': direction_zh,
                    '联机余额': balance_num,
                    '交易类型': trans_type,
                    '交易分类': transaction_category,
                    '对方名称': counterparty_name,
                    '对方账号': counterparty_account,
                    '原始对手信息': counterparty
                }
                
                return transaction
                
            except Exception as e:
                self.print_debug(f"解析交易行失败: {e}")
                return None
        
        # 如果没有匹配成功，尝试更宽松的匹配
        return self.parse_transaction_line_lenient(line_clean)
    
    def parse_transaction_line_lenient(self, line_clean: str) -> Optional[Dict]:
        """宽松模式解析交易行"""
        # 尝试提取日期
        date_match = re.search(r'(\d{8})', line_clean)
        if not date_match:
            return None
        
        date_str = date_match.group(1)
        
        # 尝试格式化日期
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            formatted_date = date_obj.strftime('%Y-%m-%d')
            weekday = date_obj.strftime('%A')
        except:
            return None
        
        # 提取金额 - 使用更灵活的正则表达式
        amount_matches = re.findall(r'([+-]?\s*\d[\d,]*\.?\d*)', line_clean)
        
        if len(amount_matches) < 2:
            return None
        
        # 假设第一个金额是交易金额，第二个是余额
        try:
            amount_str = amount_matches[0].replace(',', '').replace(' ', '')
            balance_str = amount_matches[1].replace(',', '').replace(' ', '')
            
            amount_num = float(amount_str)
            balance_num = float(balance_str)
        except:
            return None
        
        # 判断交易方向
        if amount_num >= 0:
            direction = '收入'
            direction_zh = '收入'
        else:
            direction = '支出'
            direction_zh = '支出'
            amount_num = abs(amount_num)
        
        # 提取交易类型和对方信息
        # 移除日期和金额部分
        remaining = line_clean
        remaining = re.sub(r'\d{8}', '', remaining, 1)
        
        for amt in amount_matches[:2]:
            if amt in remaining:
                remaining = remaining.replace(amt, '', 1)
        
        remaining = remaining.strip()
        
        # 尝试提取交易类型（第一个词）
        parts = remaining.split()
        trans_type = "转账"
        if parts:
            trans_type = parts[0]
            counterparty = ' '.join(parts[1:]) if len(parts) > 1 else ""
        else:
            counterparty = ""
        
        # 解析对方信息
        counterparty_name, counterparty_account = parse_counterparty_info(counterparty)
        
        # 智能分类
        transaction_category = self.classify_transaction(trans_type, counterparty_name, amount_num)
        
        transaction = {
            '日期': formatted_date,
            '星期': weekday,
            '记账日期': date_str,
            '货币': 'CNY',
            '交易金额': amount_num,
            '交易方向': direction,
            '交易方向中文': direction_zh,
            '联机余额': balance_num,
            '交易类型': trans_type,
            '交易分类': transaction_category,
            '对方名称': counterparty_name,
            '对方账号': counterparty_account,
            '原始对手信息': counterparty
        }
        
        return transaction
    
    def classify_transaction(self, trans_type: str, counterparty: str, amount: float) -> str:
        """智能分类交易类型"""
        trans_type_lower = str(trans_type).lower()
        counterparty_lower = str(counterparty).lower()
        
        # 关键词分类
        categories = {
            TransactionType.TRANSFER: ["转账", "汇款", "转出", "转入", "transfer", "跨行", "手机转账", "汇款汇入"],
            TransactionType.WITHDRAWAL: ["取现", "atm", "取款", "withdrawal", "现金取款"],
            TransactionType.DEPOSIT: ["存款", "存入", "deposit", "现金存款"],
            TransactionType.CONSUMPTION: ["消费", "pos", "支付", "支付宝", "微信", "消费", "shopping", "美团", "滴滴", "京东"],
            TransactionType.SALARY: ["工资", "薪资", "薪金", "salary", "绩效", "奖金"],
            TransactionType.INTEREST: ["利息", "结息", "interest", "利息收入"],
            TransactionType.FEE: ["手续费", "管理费", "年费", "fee", "charge", "服务费", "工本费"],
            TransactionType.REPAYMENT: ["还款", "还贷", "repayment", "信用卡还款"],
            TransactionType.LOAN: ["贷款", "放款", "loan", "借款"],
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in trans_type_lower or keyword in counterparty_lower:
                    return category.value
        
        # 根据金额和对方信息推断
        if amount >= 50000 and counterparty:
            return "大额转账"
        elif "公司" in counterparty_lower or "有限" in counterparty_lower or "集团" in counterparty_lower or "科技" in counterparty_lower:
            return "对公交易"
        elif not counterparty or counterparty in ["", " "]:
            return "未知交易"
        
        return TransactionType.OTHER.value
    
    def parse_transactions(self):
        """解析所有交易数据 - 主要解析方法"""
        start_line = self.find_transaction_start()
        
        if start_line <= 0:
            self.print_debug("未找到交易开始位置，尝试其他方法...")
            # 尝试从头开始查找
            start_line = 0
        
        transactions = []
        parsed_count = 0
        line_count = 0
        
        # 处理续行的情况
        prev_line_was_transaction = False
        prev_transaction = None
        
        for i in range(start_line, len(self.lines)):
            line = self.lines[i]
            line_count += 1
            
            # 检查是否是续行（上一行是交易，当前行不以日期开头）
            if prev_line_was_transaction and prev_transaction:
                if not re.match(r'^\s*\d{8}\s+', line):
                    # 可能是上一行对手信息的续行
                    line_clean = normalize_text(line)
                    # 添加到上一个交易的对手信息中
                    if '原始对手信息' in prev_transaction:
                        prev_transaction['原始对手信息'] += ' ' + line_clean
                        prev_transaction['对方名称'] += ' ' + line_clean
                    continue
            
            # 解析当前行
            transaction = self.parse_transaction_line(line)
            
            if transaction:
                transactions.append(transaction)
                parsed_count += 1
                prev_line_was_transaction = True
                prev_transaction = transaction
                
                # 调试输出前几条交易
                if parsed_count <= 3:
                    self.print_debug(f"解析成功 {parsed_count}: {transaction['日期']} {transaction['交易方向中文']} {transaction['交易金额']:.2f}")
            else:
                prev_line_was_transaction = False
                prev_transaction = None
            
            # 进度提示
            if self.verbose and parsed_count % 100 == 0 and parsed_count > 0:
                print(f"[进度] 已解析 {parsed_count} 条交易...")
        
        self.transactions = transactions
        
        if transactions:
            self.print_debug(f"解析完成: 处理 {line_count} 行，成功解析 {parsed_count} 条交易")
        else:
            self.print_debug("未解析到任何交易记录")
            
            # 尝试备用方法
            self.parse_transactions_fallback()
    
    def parse_transactions_fallback(self):
        """备用解析方法 - 当主方法失败时使用"""
        self.print_debug("使用备用方法解析交易数据...")
        
        transactions = []
        
        # 直接使用正则表达式在全文中查找交易行
        transaction_pattern = r'(\d{8})\s+(\w+)\s+([\d,.-]+)\s+([\d,.-]+)\s+(\S+)\s+(.+)'
        
        for line in self.lines:
            line_clean = normalize_text(line)
            
            # 跳过明显不是交易的行
            skip_keywords = ["合同ID号:", "版本:", "温馨提示", "合计统计"]
            if any(keyword in line_clean for keyword in skip_keywords):
                continue
            
            match = re.match(transaction_pattern, line_clean)
            if match:
                try:
                    date_str, currency, amount_str, balance_str, trans_type, counterparty = match.groups()
                    
                    # 格式化日期
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    
                    # 清理金额
                    amount_num = float(amount_str.replace(',', ''))
                    balance_num = float(balance_str.replace(',', ''))
                    
                    # 交易方向
                    if amount_num >= 0:
                        direction = '收入'
                        direction_zh = '收入'
                    else:
                        direction = '支出'
                        direction_zh = '支出'
                        amount_num = abs(amount_num)
                    
                    # 对方信息
                    counterparty_parts = counterparty.strip().split()
                    counterparty_name = ""
                    counterparty_account = ""
                    
                    if len(counterparty_parts) >= 2:
                        last_part = counterparty_parts[-1]
                        if re.match(r'^\d{8,19}$', last_part):
                            counterparty_name = ' '.join(counterparty_parts[:-1])
                            counterparty_account = last_part
                        else:
                            counterparty_name = counterparty
                    else:
                        counterparty_name = counterparty
                    
                    # 智能分类
                    transaction_category = self.classify_transaction(trans_type, counterparty_name, amount_num)
                    
                    transaction = {
                        '日期': formatted_date,
                        '星期': date_obj.strftime('%A'),
                        '记账日期': date_str,
                        '货币': currency,
                        '交易金额': amount_num,
                        '交易方向': direction,
                        '交易方向中文': direction_zh,
                        '联机余额': balance_num,
                        '交易类型': trans_type,
                        '交易分类': transaction_category,
                        '对方名称': counterparty_name,
                        '对方账号': counterparty_account,
                        '原始对手信息': counterparty
                    }
                    
                    transactions.append(transaction)
                    
                except Exception as e:
                    self.print_debug(f"备用方法解析失败: {e}")
                    continue
        
        self.transactions = transactions
        self.print_debug(f"备用方法解析完成: 找到 {len(transactions)} 条交易")

# ==================== Excel报告生成器 ====================

class ExcelReportGenerator:
    """Excel报告生成器"""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
    
    def create_report(self, parser) -> bool:
        """创建完整报告"""
        try:
            # 创建Excel写入器
            writer = pd.ExcelWriter(self.output_path, engine='openpyxl')
            
            # 1. 账户信息表
            self.create_account_sheet(writer, parser.account_info)
            
            # 2. 交易明细表
            if parser.transactions:
                self.create_transaction_sheet(writer, parser.transactions)
            else:
                print("[警告] 没有交易数据可生成")
                writer.close()
                return False
            
            # 3. 基本统计表
            if parser.transactions:
                self.create_basic_stats_sheet(writer, parser.transactions)
            
            # 4. 处理日志表
            self.create_log_sheet(writer, parser)
            
            # 保存文件
            writer._save()
            writer.close()
            
            return True
            
        except Exception as e:
            print(f"[错误] 创建Excel报告失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_account_sheet(self, writer, account_info: Dict):
        """创建账户信息表"""
        df = pd.DataFrame(list(account_info.items()), columns=["项目", "内容"])
        df.to_excel(writer, sheet_name="账户信息", index=False)
        
        # 获取worksheet对象
        workbook = writer.book
        worksheet = workbook["账户信息"]
        
        # 设置列宽
        worksheet.column_dimensions['A'].width = 25
        worksheet.column_dimensions['B'].width = 40
    
    def create_transaction_sheet(self, writer, transactions: List[Dict]):
        """创建交易明细表"""
        df = pd.DataFrame(transactions)
        
        # 智能排序列顺序
        preferred_order = [
            "日期", "星期", "记账日期", "货币", "交易金额", "交易方向中文", 
            "联机余额", "交易类型", "交易分类", "对方名称", "对方账号", "原始对手信息"
        ]
        
        # 只保留存在的列
        columns = [col for col in preferred_order if col in df.columns]
        # 添加其他列
        other_columns = [col for col in df.columns if col not in preferred_order and col not in columns]
        columns.extend(other_columns)
        
        df = df[columns]
        df.to_excel(writer, sheet_name="交易明细", index=False)
        
        # 获取worksheet对象
        workbook = writer.book
        worksheet = workbook["交易明细"]
        
        # 设置列宽
        column_widths = {
            'A': 12,  # 日期
            'B': 10,  # 星期
            'C': 12,  # 记账日期
            'D': 8,   # 货币
            'E': 15,  # 金额
            'F': 10,  # 方向
            'G': 15,  # 余额
            'H': 15,  # 类型
            'I': 15,  # 分类
            'J': 25,  # 对方名称
            'K': 25,  # 对方账号
            'L': 40,  # 原始对手信息
        }
        
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
        
        # 设置数字格式
        for row in range(2, worksheet.max_row + 1):
            # 交易金额列 (E列)
            if worksheet[f'E{row}'].value is not None:
                worksheet[f'E{row}'].number_format = '#,##0.00'
            # 余额列 (G列)
            if worksheet[f'G{row}'].value is not None:
                worksheet[f'G{row}'].number_format = '#,##0.00'
    
    def create_basic_stats_sheet(self, writer, transactions: List[Dict]):
        """创建基本统计表"""
        df = pd.DataFrame(transactions)
        
        if len(df) == 0:
            return
        
        # 基本统计
        total_count = len(df)
        income_count = len(df[df["交易方向"] == "收入"])
        expense_count = len(df[df["交易方向"] == "支出"])
        total_income = df[df["交易方向"] == "收入"]["交易金额"].sum() if income_count > 0 else 0
        total_expense = df[df["交易方向"] == "支出"]["交易金额"].sum() if expense_count > 0 else 0
        net_flow = total_income - total_expense
        
        basic_stats = {
            "总交易笔数": total_count,
            "收入笔数": income_count,
            "支出笔数": expense_count,
            "总收入金额": round(total_income, 2),
            "总支出金额": round(total_expense, 2),
            "净现金流": round(net_flow, 2)
        }
        
        # 如果有日期信息，计算日期范围
        if "日期" in df.columns and len(df) > 0:
            try:
                dates = pd.to_datetime(df["日期"])
                date_range = f"{dates.min().strftime('%Y-%m-%d')} 至 {dates.max().strftime('%Y-%m-%d')}"
                days_count = (dates.max() - dates.min()).days + 1
                avg_daily_transactions = total_count / days_count if days_count > 0 else 0
                basic_stats["日期范围"] = date_range
                basic_stats["天数"] = days_count
                basic_stats["日均交易笔数"] = round(avg_daily_transactions, 2)
            except:
                pass
        
        df_stats = pd.DataFrame([basic_stats])
        df_stats.to_excel(writer, sheet_name="基本统计", index=False)
        
        # 获取worksheet对象
        workbook = writer.book
        worksheet = workbook["基本统计"]
        
        worksheet.column_dimensions['A'].width = 25
        for col in range(2, len(basic_stats) + 2):
            col_letter = chr(64 + col)  # A=65, B=66, ...
            worksheet.column_dimensions[col_letter].width = 20
    
    def create_log_sheet(self, writer, parser):
        """创建处理日志表"""
        log_data = {
            "处理时间": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "银行类型": [parser.bank_type.value],
            "检测置信度": [f"{parser.confidence:.2%}"],
            "交易记录数": [len(parser.transactions)],
            "处理状态": ["成功"]
        }
        
        df = pd.DataFrame(log_data)
        df.to_excel(writer, sheet_name="处理日志", index=False)

# ==================== 主程序 ====================

def print_banner():
    """打印程序横幅"""
    print("="*70)
    print("          智能银行流水转换工具 v3.6 - 交互式版本")
    print("="*70)
    print("功能: 智能识别多种银行流水格式，转换为结构化Excel文件")
    print("支持: 自动识别银行类型、智能解析交易、全面分析报告")
    print("="*70)
    print()

def main():
    """主函数"""
    print_banner()
    
    # 获取输入文件路径
    input_file = get_input_file_path()
    
    # 获取输出文件路径
    output_file = get_output_file_path(input_file)
    
    # 获取处理模式
    mode_settings = get_processing_mode()
    
    print("\n" + "="*60)
    print("配置完成，开始处理...")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print(f"处理模式: {'简单模式' if mode_settings['simple'] else '完整模式'}")
    print(f"详细输出: {'开启' if mode_settings['verbose'] else '关闭'}")
    print("="*60 + "\n")
    
    # 创建解析器
    bank_parser = BankStatementParser(verbose=mode_settings['verbose'] or mode_settings['all'])
    
    # 加载文件
    print("[1] 正在读取文件...")
    if not bank_parser.load_file(input_file):
        print("[错误] 无法加载文件")
        return
    
    print("[成功] 文件读取成功")
    print(f"[信息] 银行类型: {bank_parser.bank_type.value} (置信度: {bank_parser.confidence:.2%})")
    
    # 解析账户信息
    print("[2] 正在解析账户信息...")
    bank_parser.parse_account_info()
    print("[成功] 账户信息解析完成")
    
    # 解析交易数据
    print("[3] 正在解析交易数据...")
    bank_parser.parse_transactions()
    
    if not bank_parser.transactions:
        print("[错误] 未找到交易数据")
        print("[提示] 可能是以下原因导致:")
        print("  1. 文件格式不正确")
        print("  2. 文件编码不匹配")
        print("  3. 交易数据格式无法识别")
        print("  4. 文件内容为空或格式错误")
        
        # 显示更多调试信息
        print("\n[调试] 文件前30行内容:")
        for i, line in enumerate(bank_parser.lines[:30]):
            print(f"  行{i+1}: {line[:100]}")
        
        return
    
    print(f"[成功] 交易数据解析完成: {len(bank_parser.transactions)} 条记录")
    
    # 显示交易统计
    if bank_parser.transactions:
        df = pd.DataFrame(bank_parser.transactions)
        total_count = len(df)
        income_count = len(df[df["交易方向"] == "收入"])
        expense_count = len(df[df["交易方向"] == "支出"])
        
        print(f"[统计] 收入笔数: {income_count}, 支出笔数: {expense_count}")
        
        # 显示前几条交易示例
        print("\n[示例] 交易示例:")
        for i, trans in enumerate(bank_parser.transactions[:3]):
            amount = trans.get("交易金额", 0)
            direction = trans.get("交易方向中文", "")
            direction_symbol = "+" if direction == "收入" else "-"
            print(f"  {i+1}. {trans.get('日期', '')} {direction_symbol} {abs(amount):,.2f}元")
            print(f"     类型: {trans.get('交易类型', '')}, 对方: {trans.get('对方名称', '')[:20]}")
    
    # 生成报告
    print("[4] 正在生成Excel报告...")
    report_generator = ExcelReportGenerator(output_file)
    
    success = report_generator.create_report(bank_parser)
    
    if success:
        print(f"[成功] 转换完成! 文件已保存: {output_file}")
        
        # 显示基本统计信息
        if bank_parser.transactions:
            df = pd.DataFrame(bank_parser.transactions)
            total_count = len(df)
            income_count = len(df[df["交易方向"] == "收入"])
            expense_count = len(df[df["交易方向"] == "支出"])
            total_income = df[df["交易方向"] == "收入"]["交易金额"].sum() if income_count > 0 else 0
            total_expense = df[df["交易方向"] == "支出"]["交易金额"].sum() if expense_count > 0 else 0
            net_flow = total_income - total_expense
            
            print("\n[统计] 转换摘要:")
            print(f"  银行类型: {bank_parser.bank_type.value}")
            print(f"  总交易笔数: {total_count:,}")
            print(f"  收入笔数: {income_count:,}，支出笔数: {expense_count:,}")
            print(f"  总收入: {total_income:,.2f}元")
            print(f"  总支出: {total_expense:,.2f}元")
            print(f"  净现金流: {net_flow:,.2f}元")
        
        # 显示文件信息
        try:
            file_size = os.path.getsize(output_file)
            print(f"[信息] 文件大小: {file_size/1024:.1f} KB")
        except:
            pass
        
        print("\n" + "="*60)
        print("处理完成！您可以打开文件查看详细内容。")
        print("="*60)
    else:
        print("[错误] 转换失败")

if __name__ == "__main__":
    try:
        main()
        input("\n[提示] 按Enter键退出...")
    except KeyboardInterrupt:
        print("\n[提示] 用户中断操作")
    except Exception as e:
        print(f"\n[错误] 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        input("\n[提示] 按Enter键退出...")