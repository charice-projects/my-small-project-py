# -*- coding: utf-8 -*-
"""
解析器公共基类与工具 (v5.0)
提供：
    - BasePDFParser: 稳健的PDF加载、文本提取、表格提取
    - CoordinateEngine: 基于DBSCAN的坐标解析引擎（列边界、行分组、网格分配）
    - 文本回退工具
    - 日期、分类等通用函数
"""

import re
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Iterator
from pathlib import Path
from datetime import datetime

# 核心依赖
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

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

from .helpers import clean_text, safe_float


class BasePDFParser:
    """
    所有解析器的公共基类（非抽象，提供通用工具方法）
    核心能力：
        - 逐页隔离读取，多引擎降级
        - 跨页文本拼接（_pending_line）
        - 进度条集成（tqdm）
        - 表格提取、行分割、表头识别、列映射
    子类需要实现 run() 方法，并调用基类工具。
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.account_info: Dict[str, str] = {}
        self.transactions: List[Dict] = []
        self.raw_text: str = ""
        self._plugin_name: str = self.__class__.__name__.replace("Parser", "")
        self._pending_line: Optional[str] = None

    def log(self, msg: str) -> None:
        if self.verbose:
            # 使用 tqdm.write 避免干扰进度条
            if TQDM_OK:
                tqdm.write(f"[{self._plugin_name}] {msg}")
            else:
                print(f"[{self._plugin_name}] {msg}")

    # ------------------------ PDF 读取层 ------------------------
    def load_pdf(self, pdf_path: str, progress_desc: str = "读取页面") -> bool:
        """稳健加载PDF，返回是否成功提取到文本"""
        file_path = Path(pdf_path)
        if not file_path.exists():
            self.log(f"文件不存在: {pdf_path}")
            return False

        full_text = ""
        failed_pages = []
        total_pages = 0
        self._pending_line = None

        if pdfplumber:
            try:
                with pdfplumber.open(file_path) as pdf:
                    total_pages = len(pdf.pages)
                    pages_iter = tqdm(pdf.pages, desc=f"[{self._plugin_name}] {progress_desc}", unit="页") if TQDM_OK else pdf.pages
                    for idx, page in enumerate(pages_iter, 1):
                        try:
                            text = page.extract_text()
                            if text:
                                if self._pending_line:
                                    text = self._pending_line + " " + text.lstrip()
                                    self._pending_line = None
                                full_text += text + "\n"
                            else:
                                # 尝试用 extract_words 重建
                                words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
                                if words:
                                    line_text = self._reconstruct_text_from_words(words)
                                    if self._pending_line:
                                        line_text = self._pending_line + " " + line_text.lstrip()
                                        self._pending_line = None
                                    full_text += line_text + "\n"
                                else:
                                    chars = page.chars
                                    if chars:
                                        line_text = self._reconstruct_text_from_chars(chars)
                                        if self._pending_line:
                                            line_text = self._pending_line + " " + line_text.lstrip()
                                            self._pending_line = None
                                        full_text += line_text + "\n"
                                    else:
                                        self.log(f"第 {idx} 页无文本元素，已跳过")
                        except Exception as e:
                            failed_pages.append(idx)
                            fallback_text = self._read_page_with_pypdf(file_path, idx)
                            if fallback_text:
                                if self._pending_line:
                                    fallback_text = self._pending_line + " " + fallback_text.lstrip()
                                    self._pending_line = None
                                full_text += fallback_text + "\n"
                            else:
                                if self.verbose:
                                    self.log(f"第 {idx} 页所有引擎均失败，已跳过")
            except Exception as e:
                self.log(f"pdfplumber 整体打开失败: {e}，尝试 pypdf 降级...")
                full_text = self._load_with_pypdf(file_path)
                if not full_text:
                    self.log("所有 PDF 引擎均失败")
                    return False
        else:
            self.log("pdfplumber 不可用，尝试 pypdf 降级...")
            full_text = self._load_with_pypdf(file_path)
            if not full_text:
                self.log("pypdf 读取失败")
                return False

        self.raw_text = clean_text(full_text)
        if not self.raw_text:
            self.log("警告：未提取到任何文本内容")
            return False
        return True

    def _reconstruct_text_from_words(self, words: List[Dict]) -> str:
        """从 extract_words 重建文本"""
        if not words:
            return ""
        lines = {}
        for w in words:
            y_key = round(w['y0'], 1)
            lines.setdefault(y_key, []).append(w)
        result_lines = []
        for y in sorted(lines.keys()):
            sorted_words = sorted(lines[y], key=lambda w: w['x0'])
            line_text = ' '.join([w['text'] for w in sorted_words])
            result_lines.append(line_text)
        return '\n'.join(result_lines)

    def _reconstruct_text_from_chars(self, chars: List[Dict]) -> str:
        """从 page.chars 重建文本行"""
        if not chars:
            return ""
        lines = {}
        for c in chars:
            y_key = round(c['y0'], 1)
            lines.setdefault(y_key, []).append(c)
        result_lines = []
        for y in sorted(lines.keys()):
            sorted_chars = sorted(lines[y], key=lambda c: c['x0'])
            line_text = ''.join([c['text'] for c in sorted_chars])
            result_lines.append(line_text)
        return '\n'.join(result_lines)

    def _read_page_with_pypdf(self, pdf_path: str, page_num: int) -> str:
        """使用 pypdf 读取指定页面"""
        if not PdfReader:
            return ""
        try:
            reader = PdfReader(pdf_path)
            if page_num <= len(reader.pages):
                page = reader.pages[page_num - 1]
                text = page.extract_text()
                return text if text else ""
        except Exception:
            pass
        return ""

    def _load_with_pypdf(self, pdf_path: str) -> str:
        """pypdf 全量读取（降级）"""
        if not PdfReader:
            return ""
        full_text = ""
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            pages_iter = tqdm(range(total_pages), desc=f"[{self._plugin_name}] 降级读取(pypdf)", unit="页") if TQDM_OK else range(total_pages)
            for i in pages_iter:
                try:
                    text = reader.pages[i].extract_text()
                    if text:
                        full_text += text + "\n"
                except Exception:
                    continue
        except Exception as e:
            self.log(f"pypdf 降级也失败: {e}")
        return full_text

    # ------------------------ 表格提取 ------------------------
    def extract_tables(self, pdf_path: str, progress_desc: str = "提取表格") -> List[List[List[str]]]:
        """提取 PDF 中所有表格，返回三维列表: [表索引][行][列]"""
        if not pdfplumber:
            return []
        all_tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_iter = tqdm(pdf.pages, desc=f"[{self._plugin_name}] {progress_desc}", unit="页") if TQDM_OK else pdf.pages
                for page in pages_iter:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            cleaned_rows = []
                            for row in table:
                                cleaned_row = [clean_text(str(cell)) if cell else '' for cell in row]
                                if any(cleaned_row):
                                    cleaned_rows.append(cleaned_row)
                            if cleaned_rows:
                                all_tables.append(cleaned_rows)
        except Exception as e:
            self.log(f"表格提取异常：{e}")
        return all_tables

    # ------------------------ 文本行解析辅助 ------------------------
    def parse_lines_from_text(self) -> List[List[str]]:
        """从原始文本中按行拆分，尝试重建表格行（用于回退）"""
        if not self.raw_text:
            return []
        lines = self.raw_text.splitlines()
        parsed_rows = []
        skip_keywords = ['户名', '账号', '起止日期', '电子流水号', '第', '页', '交易明细清单',
                         '中国农业银行', '招商银行', '建设银行', '支付宝', '微信支付']
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(kw in line for kw in skip_keywords):
                continue
            parts = re.split(r'\s{2,}', line)
            if len(parts) <= 1:
                parts = line.split()
            if len(parts) >= 3:
                parsed_rows.append(parts)
        return parsed_rows

    def iterate_rows_with_progress(self, rows: List[Any], desc: str = "解析交易行") -> Iterator:
        """为列表元素提供带进度条的迭代器"""
        if TQDM_OK:
            return tqdm(rows, desc=f"[{self._plugin_name}] {desc}", unit="行")
        else:
            return iter(rows)

    # ------------------------ 表头识别与列映射 ------------------------
    def find_header_row(self, rows: List[List[str]], keywords: List[str]) -> int:
        """在二维行列表中查找包含所有关键字的行索引（表头行）"""
        for i, row in enumerate(rows):
            row_text = ' '.join(row)
            if all(kw in row_text for kw in keywords):
                return i
        return -1

    def map_columns_by_keywords(self, header_row: List[str], column_aliases: Dict[str, List[str]]) -> Dict[str, int]:
        """根据表头行和列别名映射，返回 列名 -> 列索引 的字典"""
        mapping = {}
        for idx, cell in enumerate(header_row):
            cell_clean = cell.strip()
            if not cell_clean:
                continue
            for col_name, aliases in column_aliases.items():
                if any(alias in cell_clean for alias in aliases):
                    if col_name not in mapping:
                        mapping[col_name] = idx
                    break
        return mapping

    # ------------------------ 日期与分类工具 ------------------------
    def parse_date(self, date_str: str) -> Tuple[str, str]:
        """统一日期解析，返回 (YYYY-MM-DD, 星期英文)"""
        if not date_str or not date_str.strip():
            return "", ""
        date_str = date_str.strip()
        if ' ' in date_str:
            parts = date_str.split()
            if len(parts) >= 1:
                date_str = parts[0]
        formats = [
            '%Y-%m-%d', '%Y%m%d', '%Y/%m/%d', '%Y.%m.%d',
            '%y-%m-%d', '%y%m%d', '%y/%m/%d'
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d'), dt.strftime('%A')
            except ValueError:
                continue
        if date_str.isdigit() and len(date_str) == 8:
            try:
                y, m, d = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
                dt = datetime(y, m, d)
                return dt.strftime('%Y-%m-%d'), dt.strftime('%A')
            except:
                pass
        return date_str, ""

    def classify_transaction(self, summary: str, counterparty: str, amount: float) -> str:
        """基于关键词和金额对交易进行简单分类（通用版）"""
        combined = (summary + ' ' + counterparty).lower()
        if "转账" in combined or "汇款" in combined or "代付" in combined:
            return "转账"
        if "消费" in combined or "支付" in combined or "快捷支付" in combined:
            return "消费"
        if "退款" in combined or "退货" in combined:
            return "退款"
        if "利息" in combined or "结息" in combined:
            return "利息"
        if "手续费" in combined or "管理费" in combined or "工本费" in combined:
            return "手续费"
        if "工资" in combined or "薪金" in combined:
            return "工资"
        if "提现" in combined or "充值" in combined:
            return "存取现"
        if abs(amount) >= 50000 and counterparty:
            return "大额转账"
        return "其他"

    def get_cell_safe(self, row: List[str], col_index: int, default: str = "") -> str:
        """安全获取行中的列值，避免索引越界"""
        if 0 <= col_index < len(row):
            return row[col_index]
        return default


# =================================================================
#  CoordinateEngine: 基于坐标的解析引擎（新增）
# =================================================================

class CoordinateEngine:
    """
    坐标解析引擎：基于 DBSCAN 聚类，从 PDF 页面单词中提取列边界、行分组和网格数据。
    适用于无表格线、但列位置固定的文本型 PDF（如农业银行流水）。
    所有方法均为静态方法，方便各插件调用。
    """

    @staticmethod
    def detect_columns(words: List[Dict], eps: float = 8, min_samples: int = 1) -> List[Tuple[float, float]]:
        """
        通过聚类单词的 x 坐标，确定列边界。
        返回 [(left, right), ...] 按从左到右排序。
        如果聚类失败或列数不足，返回空列表。
        """
        if not words or not SKLEARN_OK:
            return []
        x_coords = [w.get('x0') for w in words if w.get('x0') is not None]
        if len(x_coords) < 3:
            return []

        x_arr = np.array(x_coords).reshape(-1, 1)
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(x_arr)
        labels = clustering.labels_
        clusters = {}
        for x, label in zip(x_coords, labels):
            if label == -1:
                continue
            clusters.setdefault(label, []).append(x)
        if not clusters:
            return []

        centers = sorted([np.mean(clusters[label]) for label in clusters])
        if len(centers) < 2:
            return []

        # 生成边界：左边界=当前中心与上一中心中点，右边界=当前中心与下一中心中点
        max_x1 = max([w.get('x1', 0) for w in words]) + 5
        bounds = []
        for i, cx in enumerate(centers):
            left = 0 if i == 0 else (centers[i-1] + cx) / 2
            right = max_x1 if i == len(centers)-1 else (cx + centers[i+1]) / 2
            # 适当外扩 3 像素，避免边界过紧
            left = max(0, left - 3)
            right = min(max_x1, right + 3)
            bounds.append((left, right))
        return bounds

    @staticmethod
    def detect_rows(words: List[Dict], eps_ratio: float = 0.6) -> List[List[Dict]]:
        """
        通过聚类单词的 y 坐标，将单词分组为行。
        返回按 y 排序的行列表，每行内按 x 排序。
        eps 根据当前页面单词 y 间距中位数动态计算（eps = median_gap * eps_ratio），
        限定在 [3, 15] 之间。
        """
        if not words or not SKLEARN_OK:
            return []

        # 提取 y 坐标（兼容多种键名）
        y_vals = []
        for w in words:
            y = w.get('y0') or w.get('top') or w.get('y1') or w.get('bottom')
            if y is not None:
                y_vals.append(y)
        if not y_vals:
            # 如果完全无 y 坐标，每个单词单独成行
            return [[w] for w in words]

        sorted_y = sorted(y_vals)
        gaps = [sorted_y[i+1] - sorted_y[i] for i in range(len(sorted_y)-1) if sorted_y[i+1] > sorted_y[i]]
        if gaps:
            median_gap = np.median(gaps)
            eps = max(3, min(15, median_gap * eps_ratio))
        else:
            eps = 8

        y_arr = np.array(y_vals).reshape(-1, 1)
        clustering = DBSCAN(eps=eps, min_samples=1).fit(y_arr)
        labels = clustering.labels_
        lines_dict = {}
        for w, label in zip(words, labels):
            if label == -1:
                # 噪点单独成行
                label = max(labels) + 1
            lines_dict.setdefault(label, []).append(w)
        # 按平均 y 排序
        sorted_lines = sorted(lines_dict.values(), key=lambda line: np.mean([w.get('y0', w.get('top', 0)) for w in line if w.get('y0') is not None]))
        for line in sorted_lines:
            line.sort(key=lambda w: w.get('x0', 0))
        return sorted_lines

    @staticmethod
    def assign_words_to_grid(words: List[Dict], col_bounds: List[Tuple[float, float]]) -> List[List[str]]:
        """
        将单词分配到列网格中，返回二维列表: rows x cols，每个单元格为合并后的文本。
        列边界必须已确定。
        """
        if not words or not col_bounds:
            return []
        # 先进行行分组
        row_groups = CoordinateEngine.detect_rows(words)
        grid = []
        for row_words in row_groups:
            # 为每列准备文本列表
            col_texts = {i: [] for i in range(len(col_bounds))}
            for w in row_words:
                x_center = (w.get('x0', 0) + w.get('x1', 0)) / 2
                # 查找该单词属于哪一列
                for idx, (left, right) in enumerate(col_bounds):
                    if left <= x_center <= right:
                        col_texts[idx].append(w.get('text', ''))
                        break
            # 合并每列文本
            row_cells = [' '.join(col_texts[i]).strip() for i in range(len(col_bounds))]
            if any(row_cells):
                grid.append(row_cells)
        return grid

    @staticmethod
    def find_header_row(grid: List[List[str]], keywords: List[str], min_score: int = 4) -> int:
        """
        在网格中查找包含最多关键词的行作为表头。
        返回行索引，若未找到返回 -1。
        """
        if not grid:
            return -1
        best_idx = -1
        best_score = 0
        for i, row in enumerate(grid):
            row_text = ''.join(row)  # 去掉空格直接拼接
            score = sum(1 for kw in keywords if kw in row_text)
            if score > best_score:
                best_score = score
                best_idx = i
        if best_score >= min_score:
            return best_idx
        return -1

    @staticmethod
    def map_columns_by_header(header_row: List[str], column_aliases: Dict[str, List[str]]) -> Dict[str, int]:
        """根据表头行和列别名映射，返回 列名->列索引"""
        mapping = {}
        for idx, cell in enumerate(header_row):
            cell_clean = cell.strip()
            if not cell_clean:
                continue
            for col_name, aliases in column_aliases.items():
                if any(alias in cell_clean for alias in aliases):
                    if col_name not in mapping:
                        mapping[col_name] = idx
                    break
        return mapping