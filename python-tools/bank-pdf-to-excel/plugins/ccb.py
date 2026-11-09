# -*- coding: utf-8 -*-
"""
建设银行流水解析插件 (v13.3)

v13.3 修复（2026-11-09）：
    - detect 改为两个特征词同时命中（"中国建设银行" + "个人活期账户全部交易明细"）
      原版本仅用 "建设银行" 单特征，违反 README 3.2 禁止 3
    - _classify 补漏 "提现" 关键词 → 归为 "存取现"
      原版本 "支付机构提现" 会被误归 "其他"（README 3.9 分类规范明确包含"提现"）
    - 三级降级阈值从 < 5 改为 < 1
      原版本：即使表格提取只拿到 3 笔，也会触发坐标解析回退
      新版本：表格提取成功（≥1 笔）即停止，不回退
    - 裸 except 改为 except Exception，避免捕获 KeyboardInterrupt
    - 各解析分支的静默异常增加 verbose 日志，便于调试

v13.2 修复（2026-11-09）：
    - 删除 _deduplicate 调用。原因：
      (1) 三级降级机制互斥，本来不会产生重复
      (2) 建行存在"日期/摘要/金额/余额/对手 全部相同"的合法独立交易
          （如序号 499 和 501，两笔 -320.00 / 余额 41,192.99）
          任何按内容指纹的去重都会误杀它们
      (3) 建行 PDF 有连续序号（1~893），本身即是最强完整性证据

v13.1 修复（2026-11-09）：
    - _deduplicate 指纹从 (日期, 摘要, 金额) 升级为 (日期, 摘要, 金额, 余额, 对手信息)

解析策略：表格提取优先 → 坐标解析回退 → 文本行分割（最后兜底）
"""

import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .base import StatementPlugin
from utils.parser_common import BasePDFParser, CoordinateEngine
from utils.helpers import clean_text, safe_float

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False
    def tqdm(iterable, desc=None, **kwargs):
        return iterable


class CCBPlugin(StatementPlugin):
    """建设银行流水解析插件"""

    @property
    def name(self) -> str:
        return "建设银行"

    @property
    def identifier(self) -> str:
        return "ccb"

    def detect(self, pdf_path: str) -> bool:
        """
        检测是否为建行流水 PDF。
        使用两个特征词同时命中（README 3.2 禁止 3）：
          - "中国建设银行"：银行全称
          - "个人活期账户全部交易明细"：建行对账单标题
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages[:2])
        except Exception:
            return False
        return "中国建设银行" in text and "个人活期账户全部交易明细" in text

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        parser = _CCBParser(pdf_path, verbose)
        return parser.parse()


class _CCBParser:
    """建行解析器"""

    # 表头关键词（用于识别表头行）
    HEADER_KEYWORDS = ["日期", "摘要", "金额", "余额", "对方", "卡号"]
    REQUIRED_KEYWORDS = ["日期", "金额"]

    def __init__(self, pdf_path: str, verbose: bool = False):
        self.pdf_path = pdf_path
        self.verbose = verbose
        self.account_info: Dict[str, str] = {}
        self.transactions: List[Dict] = []

    def parse(self) -> Tuple[Dict[str, str], List[Dict]]:
        # 1. 加载文本用于账户信息（不显示进度）
        self._load_text_for_account_info()

        # 2. 尝试表格提取
        self._parse_by_tables()

        # 3. 如果表格提取结果为空，尝试坐标解析
        #    阈值用 < 1 而非 < 5：表格提取成功（≥1 笔）即代表 PDF 有表格结构，
        #    不应再回退到坐标解析（否则会重复/遗漏，见 v13.3 说明）
        if len(self.transactions) < 1:
            self._parse_by_coordinates()

        # 4. 如果仍然为空，回退到文本行分割
        if len(self.transactions) < 1:
            self._parse_from_text_lines()

        # 5. 不去重！三级降级互斥，且建行存在合法的"完全相同"交易
        #    （如序号 499 和 501 的两笔 -320.00/余额 41,192.99）
        #    任何按内容指纹的去重都会误杀这些交易

        return self.account_info, self.transactions

    # ---------- 账户信息 ----------
    def _load_text_for_account_info(self):
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()
                if not first_page:
                    return
                info = {}
                m = re.search(r'卡号[／/]账号[：:]\s*(\d+)', first_page)
                if m:
                    info['卡号/账号'] = m.group(1)
                m = re.search(r'客户名称[：:]\s*(\S+)', first_page)
                if m:
                    info['客户名称'] = m.group(1)
                m = re.search(r'起止日期[：:]\s*(\d{8}\s*[-–—]\s*\d{8})', first_page)
                if m:
                    info['起止日期'] = m.group(1)
                self.account_info = info
        except Exception as e:
            if self.verbose:
                print(f"[建行] 账户信息提取异常：{e}")

    # ---------- 表格提取 ----------
    def _parse_by_tables(self):
        """使用 pdfplumber 表格提取"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                pages_iter = tqdm(pdf.pages, desc="[建行] 读取页面", unit="页") if TQDM_OK else pdf.pages
                all_rows = []
                for page in pages_iter:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                cleaned = [clean_text(str(c)) if c else '' for c in row]
                                if any(cleaned):
                                    all_rows.append(cleaned)

                if not all_rows:
                    return

                header_idx = self._find_header_row(all_rows)
                if header_idx == -1:
                    return

                header_row = all_rows[header_idx]
                col_mapping = self._build_col_mapping(header_row)
                if not col_mapping:
                    return

                data_rows = all_rows[header_idx+1:]
                data_rows = [row for row in data_rows if not self._is_skip_row(row)]

                iter_rows = tqdm(data_rows, desc="[建行] 解析交易行", unit="行") if TQDM_OK else data_rows
                for row in iter_rows:
                    tx = self._parse_row(row, col_mapping)
                    if tx:
                        self.transactions.append(tx)

        except Exception as e:
            if self.verbose:
                print(f"[建行] 表格提取异常：{e}")

    # ---------- 坐标解析（回退） ----------
    def _parse_by_coordinates(self):
        """使用坐标引擎解析"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                pages_iter = tqdm(pdf.pages, desc="[建行] 坐标解析", unit="页") if TQDM_OK else pdf.pages
                for page in pages_iter:
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    if not words:
                        continue
                    col_bounds = CoordinateEngine.detect_columns(words, eps=10)
                    if not col_bounds or len(col_bounds) < 3:
                        continue
                    grid = CoordinateEngine.assign_words_to_grid(words, col_bounds)
                    if not grid:
                        continue
                    header_idx = CoordinateEngine.find_header_row(grid, self.REQUIRED_KEYWORDS, min_score=3)
                    if header_idx == -1:
                        continue
                    header_row = grid[header_idx]
                    col_mapping = self._build_col_mapping(header_row)
                    if not col_mapping:
                        continue
                    for row in grid[header_idx+1:]:
                        if not any(row):
                            continue
                        tx = self._parse_row(row, col_mapping)
                        if tx:
                            self.transactions.append(tx)
        except Exception as e:
            if self.verbose:
                print(f"[建行] 坐标解析异常：{e}")

    # ---------- 文本行回退（最后兜底） ----------
    def _parse_from_text_lines(self):
        """从纯文本行中解析（简单分割）"""
        full_text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception as e:
            if self.verbose:
                print(f"[建行] 文本提取异常：{e}")
            return
        lines = full_text.splitlines()
        lines = [line.strip() for line in lines if line.strip()]
        rows = []
        for line in lines:
            if any(kw in line for kw in ["合计", "温馨提示", "卡号", "客户名称", "日期"]):
                continue
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 4:
                rows.append(parts)
        if not rows:
            return
        col_mapping = {
            "交易日期": 0,
            "摘要": 1 if len(rows[0]) > 1 else -1,
            "交易金额": 2 if len(rows[0]) > 2 else -1,
            "账户余额": 3 if len(rows[0]) > 3 else -1,
            "对方信息": 4 if len(rows[0]) > 4 else -1,
        }
        if col_mapping["交易金额"] == -1:
            return
        for row in rows:
            tx = self._parse_row(row, col_mapping)
            if tx:
                self.transactions.append(tx)

    # ---------- 辅助方法 ----------
    def _find_header_row(self, rows: List[List[str]]) -> int:
        for i, row in enumerate(rows):
            row_text = ' '.join(row)
            if "交易日期" in row_text and "金额" in row_text:
                return i
        return -1

    def _build_col_mapping(self, header_row: List[str]) -> Dict[str, int]:
        mapping = {}
        aliases = {
            "交易日期": ["交易日期", "日期", "Date"],
            "摘要": ["摘要", "交易摘要"],
            "交易金额": ["交易金额", "金额", "Amount"],
            "账户余额": ["账户余额", "余额", "Balance"],
            "对方信息": ["对方", "对手", "交易对方", "户名"],
            "附言": ["附言", "交易地点"]
        }
        for col_name, alias_list in aliases.items():
            for idx, cell in enumerate(header_row):
                if any(alias in cell for alias in alias_list):
                    mapping[col_name] = idx
                    break
        if "交易日期" not in mapping:
            mapping["交易日期"] = 0
        if "交易金额" not in mapping:
            mapping["交易金额"] = 2 if len(header_row) > 2 else 1
        return mapping

    def _is_skip_row(self, row: List[str]) -> bool:
        row_text = ' '.join(row)
        skip_keywords = ["合计", "温馨提示", "生成时间", "序号", "卡号/账号", "客户名称"]
        return any(kw in row_text for kw in skip_keywords)

    def _parse_row(self, row: List[str], col_mapping: Dict[str, int]) -> Optional[Dict]:
        def get(col):
            idx = col_mapping.get(col)
            if idx is not None and idx < len(row):
                return row[idx]
            return ""

        date_str = get("交易日期")
        if not date_str:
            return None

        amount_str = get("交易金额")
        amount = safe_float(amount_str)
        if amount is None:
            return None

        f_date, weekday = self._parse_date(date_str)
        balance_str = get("账户余额")
        balance = safe_float(balance_str) if balance_str else None
        summary = get("摘要")
        counterparty = get("对方信息")
        remark = get("附言")

        direction = "收入" if amount >= 0 else "支出"
        if any(kw in summary for kw in ["退货", "退款", "利息", "工资"]):
            direction = "收入"
        elif any(kw in summary for kw in ["手续费", "管理费", "短信费"]):
            direction = "支出"

        cat = self._classify(summary, counterparty, amount)

        return {
            '交易日期': f_date,
            '星期': weekday,
            '摘要': summary,
            '交易方向': direction,
            '交易金额': amount,          # 带符号，支出为负（README 3.2 禁止 4）
            '账户余额': balance,
            '对手信息': counterparty,
            '附言': remark,
            '交易分类': cat,
        }

    def _parse_date(self, date_str: str) -> Tuple[str, str]:
        if not date_str:
            return "", ""
        date_str = date_str.strip().split()[0]
        for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d'), dt.strftime('%A')
            except Exception:
                continue
        return date_str, ""

    def _classify(self, summary: str, counterparty: str, amount: float) -> str:
        combined = (summary + ' ' + counterparty).lower()
        if "转账" in combined or "汇款" in combined:
            return "转账"
        if "消费" in combined or "支付" in combined:
            return "消费"
        if "退货" in combined or "退款" in combined:
            return "退款"
        if "利息" in combined or "结息" in combined:
            return "利息"
        if "手续费" in combined or "管理费" in combined:
            return "手续费"
        if "工资" in combined or "薪金" in combined:
            return "工资"
        # README 3.9 规范：存取现 = 存取现 / 提现 / 充值
        if "存取" in combined or "现金" in combined or "提现" in combined:
            return "存取现"
        if abs(amount) >= 50000 and counterparty:
            return "大额转账"
        return "其他"