# -*- coding: utf-8 -*-
"""
招商银行流水解析插件 (v5.5 - 最终修复版)

修复：
    - 对手信息缺失导致行错位（如"美团平台商户"）
    - 行重复解析（同一行被拆成支出+收入两条）
    - 增加非人名对手关键词匹配
"""

import re
import warnings
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

from .base import StatementPlugin
from utils.helpers import clean_text, safe_float

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    raise ImportError("pdfplumber is required.")

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False
    def tqdm(iterable, desc=None, unit=None, **kwargs):
        return iterable


class ZhaoShangPlugin(StatementPlugin):
    @property
    def name(self) -> str:
        return "招商银行"

    @property
    def identifier(self) -> str:
        return "zhaoshang"

    def detect(self, pdf_path: str) -> bool:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()
                if first_page and ("招商银行交易流水" in first_page or "Transaction Statement of China Merchant" in first_page):
                    return True
        except:
            pass
        return False

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        parser = _ZhaoShangParserV55(pdf_path, verbose)
        return parser.parse()


class _ZhaoShangParserV55:
    """招商银行解析器 v5.5 - 最终修复版"""

    TRANSACTION_TYPES = [
        "快捷支付", "银联快捷支付", "网联收款", "银联代付",
        "转账汇款", "汇入汇款", "行内转账转入", "行内转账转出",
        "本行个人转账", "柜台存现", "柜台取现", "转账手续费",
        "账户结息", "快捷退款", "银联无卡自助消费", "转账退款",
        "一网通支付鼓励金", "银联代付 续费", "转账退款", "转账手续费",
        "银联入账", "代付"
    ]

    # ---- 非人名对手关键词（如"美团平台商户"） ----
    COUNTERPARTY_KEYWORDS = [
        "美团平台商户", "拼多多平台商户", "淘宝平台商户", "抖音月付",
        "微信转账", "支付宝支付科技有限公司", "滴滴出行", "中铁网络",
        "中通快递", "申通快递", "京东白条", "五谷渔粉米线", "浙江古茗",
        "濂溪区糖糖饮品店", "零食很忙", "腾讯出行服务"
    ]

    SKIP_KEYWORDS = [
        "招商银行交易流水", "Transaction Statement", "户 名", "账号",
        "申请时间", "验证码", "电子回单专用章", "招商银行股份有限公司",
        "第", "页", "Date", "Currency", "记账日期", "货币",
        "交易金额", "联机余额", "交易摘要", "对手信息",
        "Counter Party", "Transaction Type", "Balance", "Amount",
        "招商银行"
    ]

    def __init__(self, pdf_path: str, verbose: bool = False):
        self.pdf_path = Path(pdf_path)
        self.verbose = verbose
        self.account_info: Dict[str, str] = {}
        self.transactions: List[Dict] = []
        self._pending_line = ""
        self._processed_fingerprints = set()  # 防重复

    def log(self, msg: str):
        if self.verbose:
            print(f"[招商] {msg}")

    def parse(self) -> Tuple[Dict[str, str], List[Dict]]:
        if not self.pdf_path.exists():
            self.log(f"文件不存在: {self.pdf_path}")
            return {}, []

        self._extract_account_info()
        self._parse_by_text_lines()
        self._deduplicate()
        self._post_process()
        self.log(f"解析完成，共 {len(self.transactions)} 笔交易")
        return self.account_info, self.transactions

    # ---------- 账户信息 ----------
    def _extract_account_info(self):
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()
                if not first_page:
                    return
                info = {}
                m = re.search(r'户\s*名[：:]\s*(\S+)', first_page)
                if m:
                    info['户名'] = m.group(1).strip()
                m = re.search(r'账号[：:]\s*(\d+)', first_page)
                if m:
                    info['账号'] = m.group(1)
                m = re.search(r'(\d{4}-\d{2}-\d{2})\s*[-–—]\s*(\d{4}-\d{2}-\d{2})', first_page)
                if m:
                    info['起止日期'] = f"{m.group(1)} 至 {m.group(2)}"
                self.account_info = info
        except Exception:
            pass

    # ---------- 行文本解析 ----------
    def _parse_by_text_lines(self):
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                pbar = tqdm(pdf.pages, desc="📄 逐页解析", unit="页") if TQDM_OK else pdf.pages
                for page in pbar:
                    text = page.extract_text()
                    if not text:
                        continue
                    lines = text.splitlines()
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if any(kw in line for kw in self.SKIP_KEYWORDS):
                            continue
                        if re.match(r'^[\d\s\-/]+$', line):
                            continue
                        self._process_line(line)
        except Exception as e:
            self.log(f"行文本解析异常: {e}")
            import traceback
            traceback.print_exc()

    def _process_line(self, line: str):
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
        if not date_match:
            if re.search(r'[\u4e00-\u9fa5]', line) and not re.search(r'^\d', line):
                self._pending_line = line
            return

        if self._pending_line:
            prev_line = self._pending_line
            self._pending_line = ""
            if re.search(r'[\u4e00-\u9fa5]', prev_line) or re.search(r'\d{10,20}', prev_line):
                full_line = line + " " + prev_line
                self._process_full_line(full_line)
                return

        self._process_full_line(line)

    def _process_full_line(self, line: str):
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
        if not date_match:
            return
        date_str = date_match.group(1)
        rest_after_date = line[date_match.end():].strip()
        if rest_after_date.startswith("--") or rest_after_date.startswith("-"):
            return

        amt_bal_pattern = re.compile(
            r'(?:CNY\s*)?([+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
        )
        m = amt_bal_pattern.search(rest_after_date)
        if not m:
            return

        amount_str = m.group(1).replace(',', '')
        balance_str = m.group(2).replace(',', '')
        amount = safe_float(amount_str)
        if amount is None:
            return
        balance = safe_float(balance_str)

        rest = rest_after_date[:m.start()] + rest_after_date[m.end():]
        rest = re.sub(r'\bCNY\b', '', rest).strip()
        if not rest:
            return

        # ---- 防重复：生成行指纹 ----
        fingerprint = f"{date_str}|{amount}|{balance}|{rest[:50]}"
        if fingerprint in self._processed_fingerprints:
            return
        self._processed_fingerprints.add(fingerprint)

        summary, counterparty = self._split_summary_counterparty(rest)
        if not summary:
            summary = rest

        f_date, weekday = self._parse_date(date_str)
        direction = "收入" if amount >= 0 else "支出"
        if "结息" in summary or "利息" in summary:
            direction = "收入" if amount > 0 else "支出"
        if "手续费" in summary or "管理费" in summary:
            direction = "支出"
        if "退款" in summary:
            direction = "收入" if amount > 0 else "支出"
        if "一网通支付鼓励金" in summary:
            direction = "收入"

        cat = self._classify(summary, counterparty, amount)
        self.transactions.append({
            '交易日期': f_date,
            '星期': weekday,
            '摘要': summary,
            '交易方向': direction,
            '交易金额': amount,
            '账户余额': balance,
            '对手信息': counterparty,
            '交易分类': cat,
        })

    # ---------- 分离摘要和对手信息（核心优化） ----------
    def _split_summary_counterparty(self, text: str) -> Tuple[str, str]:
        """
        从文本中分离摘要和对手信息。
        核心优化：支持"美团平台商户"等非人名对手关键词。
        """
        if not text:
            return "", ""

        original_text = text
        summary = ""
        counterparty = ""
        rest = text

        # 1. 提取交易类型（摘要）
        sorted_types = sorted(self.TRANSACTION_TYPES, key=len, reverse=True)
        for ttype in sorted_types:
            if rest.startswith(ttype):
                summary = ttype
                rest = rest[len(ttype):].strip()
                break

        if not summary:
            for ttype in sorted_types:
                if ttype in rest:
                    idx = rest.find(ttype)
                    if idx == 0 or (idx > 0 and rest[idx-1] == ' '):
                        summary = ttype
                        rest = rest[:idx] + rest[idx + len(ttype):]
                        rest = rest.strip()
                        break

        # 2. 从剩余文本提取对手信息
        if rest:
            # 2.1 优先匹配非人名关键词（"美团平台商户"等）
            matched_keyword = ""
            for kw in self.COUNTERPARTY_KEYWORDS:
                if kw in rest:
                    matched_keyword = kw
                    break
            if matched_keyword:
                # 提取关键词后面的账号（如果有）
                after_kw = rest[rest.find(matched_keyword) + len(matched_keyword):].strip()
                acc_match = re.search(r'^(\d{10,20})', after_kw)
                if acc_match:
                    counterparty = matched_keyword + " " + acc_match.group(1)
                    rest = rest[:rest.find(matched_keyword)] + rest[rest.find(matched_keyword) + len(matched_keyword) + len(acc_match.group(1)):].strip()
                else:
                    counterparty = matched_keyword
                    rest = rest.replace(matched_keyword, "").strip()

            # 2.2 尝试提取 URL
            if not counterparty:
                url_match = re.search(r'(https?://[^\s]+)', rest)
                if url_match:
                    counterparty = url_match.group(1)
                    rest = rest[:url_match.start()] + rest[url_match.end():]
                    rest = rest.strip()

            # 2.3 尝试提取完整的中文名（2~30字符）+ 账号
            if not counterparty:
                match = re.search(r'([\u4e00-\u9fa5]{2,30}[\u4e00-\u9fa5·]{0,6})\s+(\d{10,20})', rest)
                if match:
                    counterparty = match.group(1).strip() + " " + match.group(2).strip()
                    rest = rest[:match.start()] + rest[match.end():]
                    rest = rest.strip()

            # 2.4 尝试提取纯中文名（2~30字符）
            if not counterparty:
                match = re.search(r'([\u4e00-\u9fa5]{2,30})$', rest)
                if match:
                    name = match.group(1).strip()
                    if name not in self.TRANSACTION_TYPES and name not in ["支付", "转账", "退款"]:
                        counterparty = name
                        rest = rest[:match.start()].strip()

            # 2.5 尝试提取纯账号
            if not counterparty:
                match = re.search(r'(\d{10,20})$', rest)
                if match:
                    counterparty = match.group(1).strip()
                    rest = rest[:match.start()].strip()

            # 2.6 处理 "微信转账" 等特定模式
            if not counterparty and "微信转账" in rest:
                parts = rest.split("微信转账")
                if len(parts) >= 2:
                    counterparty = "微信转账 " + parts[1].strip()
                    rest = parts[0].strip()
                    if not rest:
                        rest = "微信转账"

            # 2.7 如果剩余部分是纯中文且长度合理，作为对手信息
            if not counterparty and rest:
                if re.match(r'^[\u4e00-\u9fa5\s·]{2,40}$', rest):
                    counterparty = rest
                    rest = ""

        # 3. 若摘要仍未提取，从原文推断
        if not summary and original_text:
            for ttype in sorted_types:
                if ttype in original_text:
                    summary = ttype
                    break
            if not summary:
                summary = original_text

        # 4. 清理空格
        summary = re.sub(r'\s+', ' ', summary).strip()
        counterparty = re.sub(r'\s+', ' ', counterparty).strip()

        if summary == counterparty:
            counterparty = ""

        return summary, counterparty

    # ---------- 辅助函数 ----------
    def _parse_date(self, date_str: str) -> Tuple[str, str]:
        if not date_str:
            return "", ""
        date_str = date_str.strip()
        date_str = re.sub(r'\s+', '', date_str)
        formats = ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d'), dt.strftime('%A')
            except:
                continue
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) >= 3:
                try:
                    y, m, d = parts[0][:4], parts[1][:2], parts[2][:2]
                    dt = datetime(int(y), int(m), int(d))
                    return dt.strftime('%Y-%m-%d'), dt.strftime('%A')
                except:
                    pass
        return date_str, ""

    def _classify(self, summary: str, counterparty: str, amount: float) -> str:
        combined = (summary + ' ' + counterparty).lower()
        if "转账汇款" in combined or "汇入汇款" in combined:
            return "转账"
        if "行内转账" in combined or "本行个人转账" in combined:
            return "转账"
        if "银联代付" in combined or "网联收款" in combined:
            return "转账"
        if "柜台存现" in combined:
            return "存取现"
        if "柜台取现" in combined:
            return "存取现"
        if "账户结息" in combined:
            return "利息"
        if "转账手续费" in combined or "续费" in combined:
            return "手续费"
        if "快捷退款" in combined:
            return "退款"
        if "一网通支付鼓励金" in combined:
            return "其他收入"
        if "转账" in combined or "汇款" in combined or "代付" in combined:
            return "转账"
        if "消费" in combined or "支付" in combined or "快捷支付" in combined:
            return "消费"
        if "退款" in combined or "退货" in combined:
            return "退款"
        if "利息" in combined or "结息" in combined:
            return "利息"
        if "手续费" in combined or "管理费" in combined:
            return "手续费"
        if "工资" in combined or "薪金" in combined:
            return "工资"
        if "提现" in combined or "充值" in combined:
            return "存取现"
        if abs(amount) >= 50000 and counterparty:
            return "大额转账"
        return "其他"

    def _deduplicate(self):
        seen = set()
        unique = []
        for tx in self.transactions:
            key = (tx['交易日期'], tx['摘要'], round(tx['交易金额'], 2), tx.get('对手信息', ''))
            if key not in seen:
                seen.add(key)
                unique.append(tx)
        self.transactions = unique

    def _post_process(self):
        for tx in self.transactions:
            if not tx.get('星期') and tx.get('交易日期'):
                try:
                    dt = datetime.strptime(tx['交易日期'], '%Y-%m-%d')
                    tx['星期'] = dt.strftime('%A')
                except:
                    pass
            if '摘要' not in tx:
                tx['摘要'] = ''
            if '对手信息' not in tx:
                tx['对手信息'] = ''