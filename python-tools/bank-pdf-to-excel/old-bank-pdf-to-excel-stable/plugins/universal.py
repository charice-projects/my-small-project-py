# -*- coding: utf-8 -*-
"""
通用后备解析器 (v2.0)
解析策略：坐标解析优先（使用 CoordinateEngine），若失败则回退到列嗅探。
进度条：读取页面、坐标解析、解析交易行三个阶段。
"""
import re
from typing import Dict, List, Tuple, Optional

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


class UniversalPlugin(StatementPlugin):
    """通用后备解析器（当所有专用插件都失败时使用）"""

    @property
    def name(self) -> str:
        return "通用后备解析器"

    @property
    def identifier(self) -> str:
        return "universal"

    def detect(self, pdf_path: str) -> bool:
        # 通用解析器永远不自主动检测，仅当用户手动选择或自动检测失败时使用
        return False

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        parser = _UniversalParser(pdf_path, verbose)
        return parser.parse()


class _UniversalParser:
    """通用解析器"""

    def __init__(self, pdf_path: str, verbose: bool = False):
        self.pdf_path = pdf_path
        self.verbose = verbose
        self.account_info: Dict[str, str] = {}
        self.transactions: List[Dict] = []

    def parse(self) -> Tuple[Dict[str, str], List[Dict]]:
        # 1. 尝试坐标解析
        self._parse_by_coordinates()

        # 2. 若坐标解析结果不足，回退到列嗅探
        if len(self.transactions) < 5:
            self._parse_by_sniffing()

        # 3. 去重
        self._deduplicate()

        return self.account_info, self.transactions

    # ---------- 坐标解析 ----------
    def _parse_by_coordinates(self):
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # 进度条：读取页面
                pages_iter = tqdm(pdf.pages, desc="[通用] 坐标解析", unit="页") if TQDM_OK else pdf.pages
                for page_num, page in enumerate(pages_iter, 1):
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    if not words:
                        continue

                    # 检测列
                    col_bounds = CoordinateEngine.detect_columns(words, eps=12)
                    if not col_bounds or len(col_bounds) < 3:
                        continue

                    # 获取网格
                    grid = CoordinateEngine.assign_words_to_grid(words, col_bounds)
                    if not grid:
                        continue

                    # 尝试自动识别表头：寻找包含"日期"或"金额"的行
                    header_idx = self._find_header_row_auto(grid)
                    if header_idx == -1:
                        continue

                    # 建立列映射
                    col_mapping = self._build_col_mapping_auto(grid[header_idx])
                    if not col_mapping:
                        continue

                    # 解析交易行（带进度条，但此处为了简洁，直接用列表迭代）
                    # 由于解析行数可能很多，我们用 tqdm 包裹
                    data_rows = grid[header_idx+1:]
                    if not data_rows:
                        continue

                    # 过滤空行
                    data_rows = [row for row in data_rows if any(row)]

                    iter_rows = tqdm(data_rows, desc="[通用] 解析交易行", unit="行") if TQDM_OK else data_rows
                    for row in iter_rows:
                        tx = self._parse_row(row, col_mapping)
                        if tx:
                            self.transactions.append(tx)

        except Exception:
            pass

    # ---------- 列嗅探回退 ----------
    def _parse_by_sniffing(self):
        """基于内容特征的列嗅探（原方案）"""
        full_text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception:
            return
        lines = full_text.splitlines()
        lines = [line.strip() for line in lines if line.strip()]
        # 按连续空格分割
        rows = []
        for line in lines:
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 3:
                rows.append(parts)
        if not rows:
            return

        # 嗅探日期列和金额列
        max_cols = max(len(row) for row in rows)
        date_score = [0] * max_cols
        amount_score = [0] * max_cols

        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$|^\d{8}$|^\d{4}/\d{2}/\d{2}$')
        amount_pattern = re.compile(r'^[-+]?\d+\.\d{2}$|^[-+]?\d+$')

        for row in rows:
            for idx, cell in enumerate(row):
                if idx >= max_cols:
                    break
                cell_clean = cell.strip()
                if not cell_clean:
                    continue
                if date_pattern.match(cell_clean) or re.match(r'^\d{4}-\d{2}-\d{2}', cell_clean):
                    date_score[idx] += 1
                if amount_pattern.match(cell_clean):
                    try:
                        val = float(cell_clean.replace(',', ''))
                        if -1e9 < val < 1e9:
                            amount_score[idx] += 1
                    except:
                        pass

        date_col = -1
        amount_col = -1
        if max(date_score) > len(rows) * 0.1:
            date_col = date_score.index(max(date_score))
        if max(amount_score) > len(rows) * 0.1:
            amount_col = amount_score.index(max(amount_score))

        if date_col == -1 or amount_col == -1:
            return

        # 解析
        for row in rows:
            if len(row) <= max(date_col, amount_col):
                continue
            date_str = row[date_col].strip() if date_col < len(row) else ""
            amount_str = row[amount_col].strip() if amount_col < len(row) else ""
            if not date_str or not amount_str:
                continue
            amount = safe_float(amount_str)
            if amount is None:
                continue
            f_date, weekday = self._parse_date(date_str)
            summary = ' '.join([row[i] for i in range(len(row)) if i not in [date_col, amount_col]])
            direction = "收入" if amount >= 0 else "支出"
            tx = {
                '交易日期': f_date,
                '星期': weekday,
                '摘要': summary,
                '交易方向': direction,
                '交易金额': amount,
                '账户余额': None,
                '对手信息': '',
                '交易分类': self._classify(summary, '', amount),
                '备注': '⚠️ 通用嗅探解析（可能存在错位，请人工复核）'
            }
            self.transactions.append(tx)

    # ---------- 辅助方法 ----------
    def _find_header_row_auto(self, grid: List[List[str]]) -> int:
        """自动查找表头行（包含日期和金额关键词）"""
        keywords = ["日期", "金额", "摘要", "余额"]
        best_idx = -1
        best_score = 0
        for i, row in enumerate(grid):
            row_text = ''.join(row)
            score = sum(1 for kw in keywords if kw in row_text)
            if score > best_score:
                best_score = score
                best_idx = i
        if best_score >= 2:
            return best_idx
        return -1

    def _build_col_mapping_auto(self, header_row: List[str]) -> Dict[str, int]:
        """根据表头建立列映射"""
        mapping = {}
        aliases = {
            "交易日期": ["日期", "Date", "日"],
            "摘要": ["摘要", "描述", "说明", "交易摘要"],
            "交易金额": ["金额", "Amount", "交易金额"],
            "账户余额": ["余额", "Balance"],
            "对手信息": ["对手", "对方", "户名", "对方账号"]
        }
        for col_name, alias_list in aliases.items():
            for idx, cell in enumerate(header_row):
                if any(alias in cell for alias in alias_list):
                    mapping[col_name] = idx
                    break
        # 如果关键列缺失，按位置补全
        if "交易日期" not in mapping:
            mapping["交易日期"] = 0
        if "交易金额" not in mapping:
            # 尝试找第二列或第三列
            if len(header_row) >= 3:
                mapping["交易金额"] = 2
            else:
                mapping["交易金额"] = 1
        return mapping

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
        summary = get("摘要")
        counterparty = get("对手信息")
        balance_str = get("账户余额")
        balance = safe_float(balance_str) if balance_str else None

        direction = "收入" if amount >= 0 else "支出"
        cat = self._classify(summary, counterparty, amount)

        return {
            '交易日期': f_date,
            '星期': weekday,
            '摘要': summary,
            '交易方向': direction,
            '交易金额': amount,
            '账户余额': balance,
            '对手信息': counterparty,
            '交易分类': cat,
            '备注': '通用解析'
        }

    def _parse_date(self, date_str: str) -> Tuple[str, str]:
        if not date_str:
            return "", ""
        date_str = date_str.strip().split()[0]
        for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d'), dt.strftime('%A')
            except:
                continue
        return date_str, ""

    def _classify(self, summary: str, counterparty: str, amount: float) -> str:
        combined = (summary + ' ' + counterparty).lower()
        if "转账" in combined or "汇款" in combined:
            return "转账"
        if "消费" in combined or "支付" in combined:
            return "消费"
        if "退款" in combined:
            return "退款"
        if "利息" in combined:
            return "利息"
        if "手续费" in combined:
            return "手续费"
        if "工资" in combined:
            return "工资"
        if abs(amount) >= 50000 and counterparty:
            return "大额转账"
        return "其他"

    def _deduplicate(self):
        seen = set()
        unique = []
        for tx in self.transactions:
            key = (tx['交易日期'], tx['摘要'], tx['交易金额'])
            if key not in seen:
                seen.add(key)
                unique.append(tx)
        self.transactions = unique