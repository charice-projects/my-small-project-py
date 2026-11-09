# -*- coding: utf-8 -*-
"""
微信支付流水解析插件 (v2.1)

改动：在表格解析和文本回退的循环中增加 tqdm 进度条，解决大文件静默问题。
"""

import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    print("❌ 缺少 pdfplumber 库")
    sys.exit(1)

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False
    print("⚠️ 未安装 tqdm，进度条将不显示（建议安装：pip install tqdm）")

from .base import StatementPlugin

TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if OCR_SUPPORT:
    try:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    except:
        pass


class WeChatPlugin(StatementPlugin):
    @property
    def name(self) -> str:
        return "微信支付"
    
    @property
    def identifier(self) -> str:
        return "wechat"
    
    def detect(self, pdf_path: str) -> bool:
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages[:3]:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
        except:
            pass
        text = self._clean_text(text)
        return "微信支付交易明细证明" in text
    
    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        parser = _WeChatParser(verbose)
        success = parser.run(pdf_path)
        if not success:
            return {}, []
        return parser.account_info, parser.transactions

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        text = text.replace('\u3000', ' ').replace('\t', ' ')
        return text.strip()


class _WeChatParser:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.account_info: Dict[str, str] = {}
        self.transactions: List[Dict] = []
        self.raw_text = ""

    def log(self, msg: str):
        if self.verbose:
            print(f"[微信] {msg}")

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        text = text.replace('\u3000', ' ').replace('\t', ' ')
        return text.strip()

    @staticmethod
    def _safe_float(value, default=0.0):
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            v = value.strip().replace(',', '').replace(' ', '')
            if not v or v == '-':
                return default
            if v.startswith('(') and v.endswith(')'):
                v = '-' + v[1:-1]
            if v.upper().endswith('CR'):
                v = '-' + v[:-2]
            match = re.search(r'[-+]?\d*\.?\d+', v)
            if match:
                try:
                    return float(match.group())
                except:
                    pass
        return default

    def load_pdf(self, pdf_path: str) -> bool:
        full_text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_iter = tqdm(pdf.pages, desc="[微信] 读取页面", unit="页") if TQDM_OK else pdf.pages
                for page in pages_iter:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception as e:
            self.log(f"pdfplumber 读取失败: {e}")

        full_text = self._clean_text(full_text)

        if len(full_text) < 100 and OCR_SUPPORT:
            self.log("文字层不足，尝试 OCR 识别...")
            ocr_text = self._ocr_pdf(pdf_path)
            if ocr_text:
                full_text = ocr_text

        self.raw_text = full_text
        return len(self.raw_text) > 0

    def _ocr_pdf(self, pdf_path: str) -> str:
        try:
            images = convert_from_path(pdf_path, dpi=200)
        except Exception as e:
            self.log(f"PDF 转图片失败: {e}")
            return ""
        ocr_text = ""
        img_iter = tqdm(images, desc="[微信] OCR 识别", unit="页") if TQDM_OK else images
        for img in img_iter:
            try:
                text = pytesseract.image_to_string(img, lang='chi_sim+eng')
                ocr_text += text + "\n"
            except Exception as e:
                self.log(f"OCR 失败: {e}")
        return self._clean_text(ocr_text)

    def extract_account_info(self):
        info = {"银行/平台": "微信支付"}
        text = self.raw_text[:2000]
        m = re.search(r'兹证明[：:]\s*([^（(]+)', text)
        if m:
            info['姓名'] = m.group(1).strip()
        m = re.search(r'居民身份证[：:]\s*(\d{15,18})', text)
        if m:
            info['身份证'] = m.group(1)
        m = re.search(r'微信号[：:]\s*(\S+)', text)
        if m:
            info['微信号'] = m.group(1)
        m = re.search(r'交易明细对应时间段\s*(.+?至.+?)(?:\s|$)', text)
        if m:
            info['交易时间段'] = m.group(1).strip()
        self.account_info = info

    def parse_transactions(self, pdf_path: str):
        all_rows = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_iter = tqdm(pdf.pages, desc="[微信] 提取表格", unit="页") if TQDM_OK else pdf.pages
                for page in pages_iter:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            cleaned = [self._clean_text(str(cell)) if cell else '' for cell in row]
                            if any(cleaned):
                                all_rows.append(cleaned)
        except Exception as e:
            self.log(f"表格提取失败: {e}")

        if all_rows:
            self.log(f"表格提取到 {len(all_rows)} 行")
            self._parse_from_table(all_rows)
            return

        self.log("表格提取失败，回退到文本行合并")
        self._parse_from_text_fallback()

    def _parse_from_table(self, rows: List[List[str]]):
        header_idx = -1
        for i, row in enumerate(rows):
            row_str = ' '.join(row)
            if '交易单号' in row_str and ('交易时间' in row_str or '交易类型' in row_str):
                header_idx = i
                break
        if header_idx == -1:
            self.log("未找到表头")
            return

        col_idx = {
            'trans_id': 0,
            'time': 1,
            'type': 2,
            'direction': 3,
            'method': 4,
            'amount': 5,
            'counterparty': 6,
            'merchant': 7
        }

        fail_count = 0
        # 使用 tqdm 包裹循环
        iter_range = tqdm(range(header_idx + 1, len(rows)), desc="[微信] 解析交易行", unit="行") if TQDM_OK else range(header_idx + 1, len(rows))
        for i in iter_range:
            row = rows[i]
            if not any(row):
                continue
            first_cell = row[0] if row else ''
            if '编号：' in first_cell or '说明：' in first_cell:
                continue
            if len(row) < 7:
                continue

            tx = self._extract_from_cells(row, col_idx)
            if tx:
                self.transactions.append(tx)
            else:
                fail_count += 1
                if self.verbose and fail_count <= 3:
                    self.log(f"表格行解析失败: {' | '.join(row[:5])}...")

        self.log(f"表格解析成功 {len(self.transactions)} 笔，失败 {fail_count} 行")

    def _extract_from_cells(self, cells: List[str], col_idx: Dict) -> Optional[Dict]:
        try:
            trans_id = cells[col_idx['trans_id']].strip()
            time_str = cells[col_idx['time']].strip()
            trans_type = cells[col_idx['type']].strip()
            direction_raw = cells[col_idx['direction']].strip()
            method = cells[col_idx['method']].strip()
            amount_str = cells[col_idx['amount']].strip()
            counterparty_raw = cells[col_idx['counterparty']].strip()
            merchant_order = cells[col_idx['merchant']].strip() if len(cells) > col_idx['merchant'] else ''
        except IndexError:
            return None

        if not trans_id or not time_str:
            return None

        try:
            date_part = time_str.split()[0]
            date_obj = datetime.strptime(date_part, '%Y-%m-%d')
            f_date = date_obj.strftime('%Y-%m-%d')
            weekday = date_obj.strftime('%A')
        except:
            f_date = time_str[:10]
            weekday = ""

        amount = self._safe_float(amount_str)
        direction = "支出"
        if '收入' in direction_raw:
            direction = "收入"
        elif '支出' in direction_raw:
            direction = "支出"
        elif '其他' in direction_raw:
            direction = "其他"

        return {
            '交易日期': f_date,
            '星期': weekday,
            '交易单号': trans_id,
            '交易类型': trans_type,
            '交易方式': method,
            '交易金额': amount,
            '交易方向': direction,
            '对方': counterparty_raw,
            '商户单号': merchant_order,
        }

    def _parse_from_text_fallback(self):
        lines = self.raw_text.splitlines()
        header_idx = -1
        for i, line in enumerate(lines):
            if '交易单号' in line and ('交易时间' in line or '交易类型' in line):
                header_idx = i
                break
        if header_idx == -1:
            self.log("未找到表头")
            return

        merged = []
        buffer = ""
        for i in range(header_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            if any(skip in line for skip in ['编号：', '说明：', '财付通']):
                continue
            if re.match(r'\d{20,}', line):
                if buffer:
                    merged.append(buffer)
                buffer = line
            else:
                buffer += " " + line
        if buffer:
            merged.append(buffer)

        self.log(f"文本合并记录数: {len(merged)}")
        fail_count = 0
        iter_merged = tqdm(merged, desc="[微信] 解析文本行", unit="条") if TQDM_OK else merged
        for rec in iter_merged:
            tx = self._extract_wechat(rec)
            if tx:
                self.transactions.append(tx)
            else:
                fail_count += 1
        self.log(f"文本解析成功 {len(self.transactions)} 笔，失败 {fail_count} 条")

    def _extract_wechat(self, text: str) -> Optional[Dict]:
        m_id = re.search(r'(\d{20,}?)(?=\D|$)', text)
        if not m_id:
            return None
        trans_id = m_id.group(1)
        remaining = text[m_id.end():].strip()

        time_pats = [r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})']
        time_str = None
        for pat in time_pats:
            m = re.search(pat, remaining)
            if m:
                time_str = m.group(1)
                remaining = remaining[:m.start()] + ' ' + remaining[m.end():]
                break
        if not time_str:
            return None

        m_amt = re.search(r'([\d,]+\.\d{2})', remaining)
        if not m_amt:
            return None
        amount_str = m_amt.group(1)
        prefix = remaining[:m_amt.start()].strip()
        suffix = remaining[m_amt.end():].strip()

        parts = prefix.split()
        if len(parts) >= 3:
            trans_type = parts[-3]
            direction_raw = parts[-2]
            method = parts[-1]
        elif len(parts) == 2:
            trans_type = parts[0]
            direction_raw = parts[1]
            method = ""
        else:
            trans_type = parts[0] if parts else ""
            direction_raw = ""
            method = ""

        suffix_parts = suffix.split()
        merchant_order = suffix_parts[-1] if suffix_parts else ""
        counterparty_raw = ' '.join(suffix_parts[:-1]) if len(suffix_parts) > 1 else ""

        try:
            date_part = time_str.split()[0]
            date_obj = datetime.strptime(date_part, '%Y-%m-%d')
            f_date = date_obj.strftime('%Y-%m-%d')
            weekday = date_obj.strftime('%A')
        except:
            f_date = time_str[:10]
            weekday = ""

        amount = self._safe_float(amount_str)
        direction = "支出"
        if '收入' in direction_raw:
            direction = "收入"
        elif '支出' in direction_raw:
            direction = "支出"
        elif '其他' in direction_raw:
            direction = "其他"

        return {
            '交易日期': f_date,
            '星期': weekday,
            '交易单号': trans_id,
            '交易类型': trans_type,
            '交易方式': method,
            '交易金额': amount,
            '交易方向': direction,
            '对方': counterparty_raw,
            '商户单号': merchant_order,
        }

    def run(self, pdf_path: str) -> bool:
        if not self.load_pdf(pdf_path):
            return False
        self.extract_account_info()
        self.parse_transactions(pdf_path)
        return len(self.transactions) > 0