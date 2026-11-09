# -*- coding: utf-8 -*-
"""
中国农业银行账户活期交易明细清单解析插件 (v18.2 - 最终生产版)
- 抑制 NumPy RuntimeWarning，保证进度条覆盖式刷新无干扰
- 无任何额外日志输出
- 坐标解析为主，静默文本回退为兜底
"""

import re
import warnings
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime

# 抑制 NumPy 运行时警告（如 Mean of empty slice）
warnings.filterwarnings("ignore", category=RuntimeWarning, module="numpy")

from .base import StatementPlugin
from utils.helpers import clean_text, safe_float

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    raise ImportError("pdfplumber is required.")

try:
    from sklearn.cluster import DBSCAN
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False
    def tqdm(iterable, desc=None, unit=None, **kwargs):
        return iterable


class NongYePlugin(StatementPlugin):
    @property
    def name(self) -> str:
        return "农业银行"

    @property
    def identifier(self) -> str:
        return "nongye"

    def detect(self, pdf_path: str) -> bool:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()
                if first_page and ("中国农业银行账户活期交易明细清单" in first_page or "农业银行" in first_page):
                    return True
        except:
            pass
        return False

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        parser = _NongYeParserV18(pdf_path)
        return parser.parse()


class _NongYeParserV18:
    """农业银行解析器 v18.2 - 最终生产版"""

    HEADER_KEYWORDS = [
        "交易日期", "交易时间", "摘要", "金额", "余额",
        "对手", "日志号", "渠道", "附言"
    ]
    REQUIRED_KEYWORDS = ["交易日期", "金额"]
    CHANNEL_KEYWORDS = [
        "微信", "支付宝", "掌上银行", "超级网银", "电子收款机",
        "自动柜员机", "银行柜面", "手机转账", "网上银行",
        "银联入账", "代付", "财付通", "抖音月付", "抖音电商",
        "个人活期结息", "短信费", "微信零钱提现"
    ]
    LOG_PREFIXES = ("NA", "UA", "WA", "YA", "NB", "UC", "NG", "NC", "NE")

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.account_info: Dict[str, str] = {}
        self.transactions: List[Dict] = []

    def parse(self) -> Tuple[Dict[str, str], List[Dict]]:
        if not self.pdf_path.exists():
            print(f"文件不存在: {self.pdf_path}")
            return {}, []

        self._extract_account_info()
        self._parse_by_coordinates()

        if len(self.transactions) < 10:
            self._parse_from_text_fallback()

        self._deduplicate()
        self._validate_integrity()
        return self.account_info, self.transactions

    # ---------- 账户信息 ----------
    def _extract_account_info(self):
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()
                if not first_page:
                    return
                info = {}
                m = re.search(r'户名[：:]\s*(\S+)', first_page)
                if m:
                    info['户名'] = m.group(1).strip()
                m = re.search(r'账号[：:]\s*(\d+\s*\d+)', first_page)
                if m:
                    info['账号'] = m.group(1).replace(' ', '')
                m = re.search(r'起止日期[：:]\s*(\d{8})\s*[-–—]\s*(\d{8})', first_page)
                if m:
                    info['起止日期'] = f"{m.group(1)} 至 {m.group(2)}"
                self.account_info = info
        except Exception:
            pass

    # ---------- 核心坐标解析 ----------
    def _parse_by_coordinates(self):
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                pbar = tqdm(pdf.pages, desc="📐 坐标解析", unit="页") if TQDM_OK else pdf.pages
                for page in pbar:
                    words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)
                    if not words:
                        continue

                    col_bounds, col_mapping = self._determine_columns(words)
                    if not col_bounds or len(col_bounds) < 3:
                        continue

                    lines = self._group_lines(words)
                    if not lines:
                        continue

                    for line in lines:
                        tx = self._parse_line(line, col_bounds, col_mapping)
                        if tx:
                            self.transactions.append(tx)
        except Exception:
            pass

    # ---------- 表头行识别 ----------
    def _find_header_line(self, words: List[Dict]) -> Optional[List[Dict]]:
        if not words:
            return None

        y_vals = [w.get('y0') or w.get('top') for w in words if w.get('y0') is not None]
        if not y_vals:
            return None
        sorted_words = sorted(words, key=lambda w: w.get('y0', w.get('top', 0)))
        lines = []
        if not sorted_words:
            return None
        cur_line = [sorted_words[0]]
        cur_y = sorted_words[0].get('y0', sorted_words[0].get('top', 0))
        for w in sorted_words[1:]:
            y = w.get('y0', w.get('top', 0))
            if abs(y - cur_y) < 10:
                cur_line.append(w)
            else:
                cur_line.sort(key=lambda w: w.get('x0', 0))
                lines.append(cur_line)
                cur_line = [w]
                cur_y = y
        if cur_line:
            cur_line.sort(key=lambda w: w.get('x0', 0))
            lines.append(cur_line)

        best_line = None
        best_score = 0
        for line in lines:
            full_text = ''.join(w.get('text', '') for w in line)
            required_ok = all(kw in full_text for kw in self.REQUIRED_KEYWORDS)
            if not required_ok:
                continue
            score = sum(1 for kw in self.HEADER_KEYWORDS if kw in full_text)
            if score > best_score:
                best_score = score
                best_line = line

        if best_line and best_score >= 4:
            return best_line
        return None

    # ---------- 列边界确定 ----------
    def _determine_columns(self, words: List[Dict]) -> Tuple[List[Tuple[float, float]], Dict[str, int]]:
        header = self._find_header_line(words)
        if header:
            kw_x = {}
            full = ''.join(w.get('text', '') for w in header)
            for kw in self.HEADER_KEYWORDS:
                if kw in full:
                    for w in header:
                        if kw in ''.join(w.get('text', '').split()):
                            kw_x[kw] = w.get('x0')
                            break
            if len(kw_x) >= 5:
                sorted_kws = sorted(kw_x.items(), key=lambda x: x[1])
                centers = [x for _, x in sorted_kws]
                if len(centers) < 9:
                    all_x = [w.get('x0') for w in words if w.get('x0') is not None]
                    if len(all_x) > 10:
                        x_arr = np.array(all_x).reshape(-1, 1)
                        clustering = DBSCAN(eps=8, min_samples=1).fit(x_arr)
                        labels = clustering.labels_
                        clusters = {}
                        for x, label in zip(all_x, labels):
                            clusters.setdefault(label, []).append(x)
                        all_centers = sorted([np.mean(clusters[l]) for l in clusters if l >= 0])
                        if len(all_centers) >= 9:
                            centers = all_centers
                max_x1 = max(w.get('x1', 0) for w in words) + 5
                bounds = []
                for i, cx in enumerate(centers):
                    left = 0 if i == 0 else (centers[i-1] + cx) / 2
                    right = max_x1 if i == len(centers)-1 else (cx + centers[i+1]) / 2
                    left = max(0, left - 3)
                    right = min(max_x1, right + 3)
                    bounds.append((left, right))
                mapping = {kw: idx for idx, (kw, _) in enumerate(sorted_kws) if kw in self.HEADER_KEYWORDS}
                return bounds, mapping

        # ---- 回退：全局聚类 + 强制映射 ----
        all_x = [w.get('x0') for w in words if w.get('x0') is not None]
        if len(all_x) < 5:
            return [], {}
        x_arr = np.array(all_x).reshape(-1, 1)
        for eps in [12, 10, 8]:
            clustering = DBSCAN(eps=eps, min_samples=1).fit(x_arr)
            labels = clustering.labels_
            clusters = {}
            for x, label in zip(all_x, labels):
                clusters.setdefault(label, []).append(x)
            centers = sorted([np.mean(clusters[l]) for l in clusters if l >= 0])
            if len(centers) >= 5:
                break
        if len(centers) < 3:
            return [], {}

        if len(centers) > 9:
            centers = centers[:9]
        while len(centers) < 9:
            last = centers[-1]
            gap = centers[-1] - centers[-2] if len(centers) >= 2 else 30
            centers.append(last + gap)

        max_x1 = max(w.get('x1', 0) for w in words) + 5
        bounds = []
        for i, cx in enumerate(centers):
            left = 0 if i == 0 else (centers[i-1] + cx) / 2
            right = max_x1 if i == len(centers)-1 else (cx + centers[i+1]) / 2
            left = max(0, left - 3)
            right = min(max_x1, right + 3)
            bounds.append((left, right))

        mapping = {}
        for i, kw in enumerate(self.HEADER_KEYWORDS[:len(bounds)]):
            mapping[kw] = i
        return bounds, mapping

    # ---------- 行分组 ----------
    def _group_lines(self, words: List[Dict]) -> List[List[Dict]]:
        if not words:
            return []
        y_vals = []
        for w in words:
            y = w.get('y0') or w.get('top') or w.get('y1') or w.get('bottom')
            if y is not None:
                y_vals.append(y)
        if not y_vals:
            return [[w] for w in words]

        sorted_y = sorted(y_vals)
        gaps = [sorted_y[i+1] - sorted_y[i] for i in range(len(sorted_y)-1) if sorted_y[i+1] > sorted_y[i]]
        eps = np.median(gaps) * 0.6 if gaps else 8
        eps = max(3, min(15, eps))

        if SKLEARN_OK:
            y_arr = np.array(y_vals).reshape(-1, 1)
            clustering = DBSCAN(eps=eps, min_samples=1).fit(y_arr)
            labels = clustering.labels_
            lines_dict = {}
            for w, label in zip(words, labels):
                lines_dict.setdefault(label, []).append(w)
            sorted_lines = sorted(lines_dict.values(), key=lambda line: np.mean([w.get('y0', w.get('top', 0)) for w in line if w.get('y0') is not None]))
            for line in sorted_lines:
                line.sort(key=lambda w: w.get('x0', 0))
            return sorted_lines
        else:
            sorted_words = sorted(words, key=lambda w: w.get('y0', w.get('top', 0)))
            lines = []
            cur_line = [sorted_words[0]]
            cur_y = sorted_words[0].get('y0', sorted_words[0].get('top', 0))
            for w in sorted_words[1:]:
                y = w.get('y0', w.get('top', 0))
                if abs(y - cur_y) < eps:
                    cur_line.append(w)
                else:
                    cur_line.sort(key=lambda w: w.get('x0', 0))
                    lines.append(cur_line)
                    cur_line = [w]
                    cur_y = y
            if cur_line:
                cur_line.sort(key=lambda w: w.get('x0', 0))
                lines.append(cur_line)
            return lines

    # ---------- 单行解析 ----------
    def _parse_line(self, line: List[Dict], col_bounds: List[Tuple[float, float]], col_mapping: Dict[str, int]) -> Optional[Dict]:
        if not line or len(col_bounds) < 3:
            return None

        col_texts = {i: [] for i in range(len(col_bounds))}
        for w in line:
            x_center = (w.get('x0', 0) + w.get('x1', 0)) / 2
            for idx, (left, right) in enumerate(col_bounds):
                if left <= x_center <= right:
                    col_texts[idx].append(w.get('text', ''))
                    break
        col_contents = {i: ' '.join(texts).strip() for i, texts in col_texts.items()}

        if col_mapping:
            date_idx = col_mapping.get("交易日期")
            time_idx = col_mapping.get("交易时间")
            summary_idx = col_mapping.get("摘要")
            amount_idx = col_mapping.get("金额")
            balance_idx = col_mapping.get("余额")
            counterparty_idx = col_mapping.get("对手")
            log_idx = col_mapping.get("日志号")
            channel_idx = col_mapping.get("渠道")
            memo_idx = col_mapping.get("附言")

            date_str = col_contents.get(date_idx, '') if date_idx is not None else ''
            time_str = col_contents.get(time_idx, '') if time_idx is not None else ''
            summary = col_contents.get(summary_idx, '') if summary_idx is not None else ''
            amount_str = col_contents.get(amount_idx, '') if amount_idx is not None else ''
            balance_str = col_contents.get(balance_idx, '') if balance_idx is not None else ''
            counterparty = col_contents.get(counterparty_idx, '') if counterparty_idx is not None else ''
            log_str = col_contents.get(log_idx, '') if log_idx is not None else ''
            channel_str = col_contents.get(channel_idx, '') if channel_idx is not None else ''
            memo = col_contents.get(memo_idx, '') if memo_idx is not None else ''

            if not summary and date_idx is not None and amount_idx is not None:
                for idx in range(date_idx+1, amount_idx):
                    summary += ' ' + col_contents.get(idx, '')
                summary = summary.strip()
            if not counterparty and amount_idx is not None:
                end_idx = log_idx if log_idx is not None else len(col_bounds)
                for idx in range(amount_idx+1, end_idx):
                    if idx == balance_idx or idx == log_idx or idx == channel_idx:
                        continue
                    counterparty += ' ' + col_contents.get(idx, '')
                counterparty = counterparty.strip()

            if not log_str and counterparty:
                candidates = re.findall(r'([A-Z]{0,2}\d{8,20})', counterparty)
                for cand in candidates:
                    if cand.startswith(self.LOG_PREFIXES):
                        log_str = cand
                        counterparty = counterparty.replace(cand, '').strip()
                        break

            if not channel_str and counterparty:
                for kw in self.CHANNEL_KEYWORDS:
                    if kw in counterparty and len(kw) <= 10:
                        channel_str = kw
                        counterparty = counterparty.replace(kw, '').strip()
                        break

            if log_str and len(log_str) > 20 and not log_str.startswith(self.LOG_PREFIXES):
                log_str = ''
            if channel_str and len(channel_str) > 10:
                channel_str = ''
                if counterparty:
                    for kw in self.CHANNEL_KEYWORDS:
                        if kw in counterparty and len(kw) <= 10:
                            channel_str = kw
                            counterparty = counterparty.replace(kw, '').strip()
                            break

            amount = safe_float(amount_str) if amount_str else None
            if amount is None:
                return None
            balance = safe_float(balance_str) if balance_str else None

            f_date, weekday = self._parse_date(date_str)

            if amount >= 0:
                direction = "收入"
            else:
                direction = "支出"
            if "短信费" in summary or "利息税" in summary:
                direction = "支出"
            elif "结息" in summary or "利息" in summary:
                direction = "收入"
            elif "冲正" in summary or "退款" in summary:
                direction = "收入"
                amount = abs(amount)

            cat = self._classify(summary, counterparty, amount)

            return {
                '交易日期': f_date,
                '交易时间': time_str,
                '交易摘要': summary,
                '交易金额': amount,
                '本次余额': balance,
                '对手信息': counterparty,
                '日志号': log_str,
                '交易渠道': channel_str,
                '交易附言': memo,
            }

        return None

    # ---------- 文本回退（静默） ----------
    def _parse_from_text_fallback(self):
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
        date_pattern = re.compile(r'^(\d{8})\s*(\d{6})?\s*(.*)')
        i = 0
        while i < len(lines):
            line = lines[i]
            m = date_pattern.match(line)
            if not m:
                i += 1
                continue
            date_str = m.group(1)
            time_str = m.group(2) if m.group(2) else ""
            rest = m.group(3).strip()
            j = i + 1
            while j < len(lines) and not re.match(r'^\d{8}\s', lines[j]):
                rest += ' ' + lines[j].strip()
                j += 1
            tx = self._parse_text_block(date_str, time_str, rest)
            if tx:
                self.transactions.append(tx)
            i = j

    def _parse_text_block(self, date_str: str, time_str: str, rest: str) -> Optional[Dict]:
        patterns = [
            re.compile(r'^([^+\-]{0,200}?)\s*([+\-]?\d+\.?\d*)\s*(\d+\.?\d*)\s*(.*)$'),
            re.compile(r'^([^+\-]{0,200}?)\s*(\d+\.?\d*)\s*(\d+\.?\d*)\s*(.*)$'),
            re.compile(r'^(.+?)\s*([+\-]?\d+\.?\d*)\s*(\d+\.?\d*)\s*(.*)$')
        ]
        for pat in patterns:
            m = pat.search(rest)
            if m:
                summary = m.group(1).strip()
                amount_str = m.group(2)
                balance_str = m.group(3)
                remaining = m.group(4).strip() if len(m.groups()) >= 4 else ""
                if not summary and remaining:
                    parts = remaining.split()
                    if parts and not re.search(r'[+\-]', parts[0]) and not re.match(r'^\d', parts[0]):
                        summary = parts[0]
                        remaining = ' '.join(parts[1:])
                amount = safe_float(amount_str)
                if amount is None:
                    continue
                balance = safe_float(balance_str)
                if balance is None or (balance <= 10 and '.' not in balance_str):
                    nums = re.findall(r'(?<![+\-])\d+\.\d{2}', remaining)
                    if nums:
                        cand = safe_float(nums[-1])
                        if cand is not None:
                            balance = cand
                            remaining = remaining.replace(nums[-1], '').strip()
                counterparty, log_id, channel = self._split_remaining(remaining, summary)
                direction = "收入" if amount >= 0 else "支出"
                if "短信费" in summary:
                    direction = "支出"
                elif "结息" in summary or "利息" in summary:
                    direction = "收入"
                elif "利息税" in summary:
                    direction = "支出"
                elif "冲正" in summary or "退款" in summary:
                    direction = "收入"
                    amount = abs(amount)
                f_date, weekday = self._parse_date(date_str)
                return {
                    '交易日期': f_date,
                    '交易时间': time_str,
                    '交易摘要': summary,
                    '交易金额': amount,
                    '本次余额': balance,
                    '对手信息': counterparty,
                    '日志号': log_id,
                    '交易渠道': channel,
                    '交易附言': "",
                }
        return None

    def _split_remaining(self, remaining: str, summary: str = "") -> Tuple[str, str, str]:
        counterparty = remaining
        log_id = ""
        channel = ""
        candidates = re.findall(r'([A-Z]{0,2}\d{8,20})', counterparty)
        for cand in candidates:
            if cand.startswith(self.LOG_PREFIXES):
                log_id = cand
                counterparty = counterparty.replace(cand, '').strip()
                break
        for kw in self.CHANNEL_KEYWORDS:
            if kw in counterparty:
                channel = kw
                counterparty = counterparty.replace(kw, '').strip()
                break
        counterparty = re.sub(r'\s+', ' ', counterparty).strip()
        return counterparty, log_id, channel

    # ---------- 辅助函数 ----------
    def _parse_date(self, date_str: str) -> Tuple[str, str]:
        if not date_str:
            return "", ""
        date_str = date_str.strip().split()[0]
        for fmt in ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d'), dt.strftime('%A')
            except:
                continue
        return date_str, ""

    def _classify(self, summary: str, counterparty: str, amount: float) -> str:
        combined = (summary + ' ' + counterparty).lower()
        if "贷款放款" in combined:
            return "贷款"
        if "贷款还款" in combined:
            return "贷款还款"
        if "信用卡还款" in combined or "信用卡还" in combined:
            return "信用卡还款"
        if "提现" in combined and ("微信" in combined or "财付通" in combined):
            return "存取现"
        if "转存" in combined or "转支" in combined or "转账" in combined or "代付" in combined:
            return "转账"
        if "消费" in combined or "微信支付" in combined or "支付宝" in combined or "财付通" in combined:
            return "消费"
        if "退款" in combined or "冲正" in combined:
            return "退款"
        if "结息" in combined or "利息" in combined:
            return "利息"
        if "手续费" in combined or "管理费" in combined:
            return "手续费"
        if "工资" in combined or "薪金" in combined:
            return "工资"
        if abs(amount) >= 50000 and counterparty:
            return "大额转账"
        return "其他"

    def _validate_integrity(self):
        # 静默校验
        pass

    def _deduplicate(self):
        seen = set()
        unique = []
        for tx in self.transactions:
            key = (tx['交易日期'], tx['交易摘要'], tx['交易金额'])
            if key not in seen:
                seen.add(key)
                unique.append(tx)
        self.transactions = unique