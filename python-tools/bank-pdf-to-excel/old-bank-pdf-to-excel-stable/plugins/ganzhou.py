# -*- coding: utf-8 -*-
"""
赣州银行历史交易流水解析插件 (v1.0)

PDF 特征：
    - 无表格边框（extract_tables 返回空）
    - 有文字层，列位置固定
    - 表头：交易日期|币种|交易金额|余额|交易摘要|对手信息|收单机构|收支类型
    - 每页重复表头，收支类型被拆成"收支类"+"型"
    - 一笔交易可能跨多行（对手信息、余额会被换行拆分）

解析策略：坐标聚类（锚点法）
    1. extract_words 提取词坐标
    2. 从表头词的 x0 确定 8 列边界
    3. 以交易日期（YYYY-MM-DD）的词为交易锚点
    4. 每个词按"最近锚点"归属（距离相等时优先上方）
    5. 每列内按 y 排序拼接（余额列直接拼、其他列中文相邻拼）
"""

import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime

from .base import StatementPlugin
from utils.helpers import safe_float

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


class GanZhouPlugin(StatementPlugin):
    @property
    def name(self) -> str:
        return "赣州银行"

    @property
    def identifier(self) -> str:
        return "ganzhou"

    def detect(self, pdf_path: str) -> bool:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()
                if first_page and "赣州银行" in first_page:
                    return True
        except Exception:
            pass
        return False

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        parser = _GanZhouParser(pdf_path, verbose)
        return parser.parse()


class _GanZhouParser:
    """赣州银行解析器（坐标聚类 + 锚点法）"""

    HEADER_KEYWORDS = ["交易日期", "币种", "交易金额", "余额", "交易摘要", "对手信息", "收单机构"]
    HEADER_TEXTS = set(HEADER_KEYWORDS) | {"收支类", "型", "收支类型"}

    COLUMN_ALIASES = {
        "交易日期": ["交易日期"],
        "币种": ["币种"],
        "交易金额": ["交易金额"],
        "余额": ["余额"],
        "交易摘要": ["交易摘要"],
        "对手信息": ["对手信息"],
        "收单机构": ["收单机构"],
        "收支类型": ["收支类", "收支类型"],
    }

    def __init__(self, pdf_path: str, verbose: bool = False):
        self.pdf_path = Path(pdf_path)
        self.verbose = verbose
        self.account_info: Dict[str, str] = {}
        self.transactions: List[Dict] = []

    def log(self, msg: str):
        if self.verbose:
            if TQDM_OK:
                tqdm.write(f"[赣州] {msg}")
            else:
                print(f"[赣州] {msg}")

    def parse(self) -> Tuple[Dict[str, str], List[Dict]]:
        if not self.pdf_path.exists():
            self.log(f"文件不存在: {self.pdf_path}")
            return {}, []
        self._extract_account_info()
        self._parse_by_coordinates()
        self._deduplicate()
        self.log(f"解析完成，共 {len(self.transactions)} 笔交易")
        return self.account_info, self.transactions

    # ---------------- 账户信息 ----------------
    def _extract_account_info(self):
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()
                if not first_page:
                    return
                info = {"银行/平台": "赣州银行"}
                m = re.search(r'户名[：:]\s*(\S+)', first_page)
                if m:
                    info['户名'] = m.group(1).strip()
                m = re.search(r'账号[：:]\s*(\d+)', first_page)
                if m:
                    info['账号'] = m.group(1)
                m = re.search(r'流水日期[：:]\s*(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})', first_page)
                if m:
                    info['起止日期'] = f"{m.group(1)} 至 {m.group(2)}"
                m = re.search(r'开户行[：:]\s*(\S+)', first_page)
                if m:
                    info['开户行'] = m.group(1)
                m = re.search(r'申请时间[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', first_page)
                if m:
                    info['申请时间'] = m.group(1)
                self.account_info = info
        except Exception as e:
            self.log(f"账户信息提取异常: {e}")

    # ---------------- 主解析流程 ----------------
    def _parse_by_coordinates(self):
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                pbar = tqdm(pdf.pages, desc="📐 坐标解析", unit="页") if TQDM_OK else pdf.pages
                for page in pbar:
                    self._parse_page(page)
        except Exception as e:
            self.log(f"坐标解析异常: {e}")
            import traceback
            traceback.print_exc()

    def _parse_page(self, page):
        words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)
        if not words:
            return

        col_bounds, col_names = self._detect_columns(words)
        if not col_bounds or "交易日期" not in col_names:
            self.log("未检测到表头/列边界，跳过本页")
            return

        date_col_idx = col_names.index("交易日期")
        anchors = self._find_date_anchors(words, col_bounds, date_col_idx)
        if not anchors:
            self.log("未找到日期锚点，跳过本页")
            return

        # 过滤有效数据词（排除页眉、账户信息、页脚、表头词）
        first_y = min(a['y'] for a in anchors)
        last_y = max(a['y'] for a in anchors)
        y_min = first_y - 15
        y_max = last_y + 15

        valid_words = []
        for w in words:
            text = (w.get('text') or '').strip()
            if not text:
                continue
            if text in self.HEADER_TEXTS:
                continue
            if self._is_noise(text):
                continue
            y = w.get('top', w.get('y0', 0))
            if y_min <= y <= y_max:
                valid_words.append(w)

        txs = self._group_by_anchor(valid_words, anchors, col_bounds, col_names)
        self.transactions.extend(txs)

    def _is_noise(self, text: str) -> bool:
        if '页' in text and ('共' in text or '/' in text):
            return True
        if text.startswith('第') and '页' in text:
            return True
        return False

    # ---------------- 表头检测 ----------------
    def _detect_columns(self, words) -> Tuple[List[Tuple[float, float]], List[str]]:
        keyword_words = []
        for w in words:
            text = (w.get('text') or '').strip()
            if not text:
                continue
            for kw in list(self.HEADER_KEYWORDS) + ["收支类"]:
                if kw == text or (len(kw) >= 2 and kw in text):
                    keyword_words.append((kw, w))
                    break

        if len(keyword_words) < 5:
            return [], []

        keyword_words.sort(key=lambda x: x[1].get('x0', 0))

        cols: List[Tuple[str, float]] = []
        for kw, w in keyword_words:
            x0 = w.get('x0', 0)
            col_name = None
            for name, aliases in self.COLUMN_ALIASES.items():
                if any(a in kw for a in aliases):
                    col_name = name
                    break
            if col_name and not any(c[0] == col_name for c in cols):
                cols.append((col_name, x0))

        if len(cols) < 5:
            return [], []

        cols.sort(key=lambda x: x[1])
        col_names = [c[0] for c in cols]
        col_x0 = [c[1] for c in cols]

        max_x1 = max(w.get('x1', 0) for w in words) + 5
        col_bounds = []
        for i, cx in enumerate(col_x0):
            left = 0 if i == 0 else (col_x0[i - 1] + cx) / 2
            right = max_x1 if i == len(col_x0) - 1 else (cx + col_x0[i + 1]) / 2
            left = max(0, left - 2)
            right = min(max_x1, right + 2)
            col_bounds.append((left, right))

        return col_bounds, col_names

    # ---------------- 日期锚点 ----------------
    def _find_date_anchors(self, words, col_bounds, date_col_idx):
        left, right = col_bounds[date_col_idx]
        anchors = []
        for w in words:
            text = (w.get('text') or '').strip()
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
                continue
            x_center = (w.get('x0', 0) + w.get('x1', 0)) / 2
            if left <= x_center <= right:
                anchors.append({
                    'y': w.get('top', w.get('y0', 0)),
                    'date': text,
                })
        anchors.sort(key=lambda a: a['y'])
        return anchors

    # ---------------- 分组与拼接 ----------------
    def _group_by_anchor(self, words, anchors, col_bounds, col_names):
        if not anchors:
            return []

        buckets = [{'anchor': a, 'cols': {name: [] for name in col_names}} for a in anchors]

        for w in words:
            text = (w.get('text') or '').strip()
            if not text:
                continue
            x_center = (w.get('x0', 0) + w.get('x1', 0)) / 2
            col_idx = -1
            for i, (left, right) in enumerate(col_bounds):
                if left <= x_center <= right:
                    col_idx = i
                    break
            if col_idx == -1:
                continue
            col_name = col_names[col_idx]
            y = w.get('top', w.get('y0', 0))

            # 找最近锚点（距离相等时保持更上方的，因为 anchors 已按 y 升序）
            best_idx = 0
            best_dist = float('inf')
            for i, a in enumerate(anchors):
                dist = abs(a['y'] - y)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
                # dist == best_dist 时保持已有（更上方）

            buckets[best_idx]['cols'][col_name].append({
                'text': text,
                'y': y,
                'x0': w.get('x0', 0),
            })

        txs = []
        for bucket in buckets:
            tx = self._parse_bucket(bucket, col_names)
            if tx:
                txs.append(tx)
        return txs

    def _parse_bucket(self, bucket, col_names):
        anchor = bucket['anchor']
        cols = bucket['cols']

        def join_col(name):
            items = cols.get(name, [])
            if not items:
                return ""
            items.sort(key=lambda x: (x['y'], x['x0']))

            if name == "余额":
                # 余额列：直接拼接（处理 "8321.3" + "8" → "8321.38"）
                return ''.join(it['text'] for it in items)

            result = items[0]['text']
            for prev, cur in zip(items[:-1], items[1:]):
                prev_last = prev['text'][-1] if prev['text'] else ''
                cur_first = cur['text'][0] if cur['text'] else ''
                # 中文/全角字符相邻不加空格（"南昌大学第二附" + "属医院"）
                if self._is_wide_char(prev_last) and self._is_wide_char(cur_first):
                    result += cur['text']
                else:
                    result += ' ' + cur['text']
            return result.strip()

        date_str = join_col("交易日期") or anchor['date']
        amount_str = join_col("交易金额")
        balance_str = join_col("余额")
        summary = join_col("交易摘要")
        counterparty = join_col("对手信息")
        acquire_org = join_col("收单机构")
        direction_hint = join_col("收支类型")

        amount = safe_float(amount_str) if amount_str else None
        if amount is None:
            return None

        balance = safe_float(balance_str) if balance_str else None

        f_date, weekday = self._parse_date(date_str)

        if direction_hint:
            if "收" in direction_hint:
                direction = "收入"
            elif "支" in direction_hint:
                direction = "支出"
            else:
                direction = "收入" if amount >= 0 else "支出"
        else:
            direction = "收入" if amount >= 0 else "支出"

        if counterparty == "-":
            counterparty = ""
        if acquire_org == "-":
            acquire_org = ""

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
            '收单机构': acquire_org,
        }

    @staticmethod
    def _is_wide_char(ch: str) -> bool:
        return bool(ch) and ord(ch) > 127

    def _parse_date(self, date_str: str) -> Tuple[str, str]:
        if not date_str:
            return "", ""
        date_str = date_str.strip().split()[0]
        for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d'), dt.strftime('%A')
            except ValueError:
                continue
        return date_str, ""

    def _classify(self, summary: str, counterparty: str, amount: float) -> str:
        combined = (summary + ' ' + counterparty).lower()

        # 赣州特有规则
        if "短信费" in combined:
            return "手续费"
        if "利息结息" in combined or "结息入账" in combined:
            return "利息"
        if "收单清算资金" in combined or "清算资金" in combined:
            return "转账"
        if "信贷" in combined or "还款" in combined:
            return "其他"

        # 通用规则
        if "转账" in combined or "汇款" in combined or "代付" in combined or "跨行" in combined:
            return "转账"
        if "消费" in combined or "支付" in combined:
            return "消费"
        if "退款" in combined or "冲正" in combined:
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