# -*- coding: utf-8 -*-
"""
支付宝流水解析插件 (v1.1)

改动：
    1. 增加文本行回退策略（当表格提取失败时）
    2. 解析循环使用基类的带进度条迭代器
"""

import re
from typing import Dict, List, Tuple

from .base import StatementPlugin
from utils.parser_common import BasePDFParser
from utils.helpers import clean_text, safe_float


class AliPayPlugin(StatementPlugin):
    @property
    def name(self) -> str:
        return "支付宝"

    @property
    def identifier(self) -> str:
        return "alipay"

    def detect(self, pdf_path: str) -> bool:
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages[:3]:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
        except:
            pass
        text = clean_text(text)
        return "支付宝支付科技有限公司 交易流水证明" in text or "支付宝" in text

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        parser = _AliPayParser(verbose)
        success = parser.run(pdf_path)
        if not success:
            return {}, []
        return parser.account_info, parser.transactions


class _AliPayParser(BasePDFParser):
    def run(self, pdf_path: str) -> bool:
        self._plugin_name = "支付宝"
        if not self.load_pdf(pdf_path):
            return False
        self._extract_account_info()
        self._parse_transactions(pdf_path)
        return len(self.transactions) > 0

    def _extract_account_info(self) -> None:
        info = {"银行/平台": "支付宝"}
        text = self.raw_text[:3000]

        m = re.search(r'兹证明[：:]\s*([^（(]+?)(?:\s*（|$)', text)
        if m:
            info['姓名'] = m.group(1).strip()
        m = re.search(r'证件号码[：:]\s*(\d{15,18})', text)
        if m:
            info['身份证'] = m.group(1)
        m = re.search(r'支付宝账号[：:]\s*(\S+)', text)
        if m:
            info['支付宝账号'] = m.group(1)
        m = re.search(r'交易时间[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*至\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
        if m:
            info['交易时间段'] = f"{m.group(1)} 至 {m.group(2)}"

        self.account_info = info

    def _parse_transactions(self, pdf_path: str) -> None:
        tables = self.extract_tables(pdf_path)
        all_rows = []
        for table in tables:
            all_rows.extend(table)

        if not all_rows:
            self.log("表格提取无数据，尝试文本行回退...")
            all_rows = self.parse_lines_from_text()

        if not all_rows:
            self.log("未提取到任何数据行")
            return

        header_keywords = ['交易时间', '交易对方', '金额']
        header_idx = self.find_header_row(all_rows, header_keywords)
        if header_idx == -1:
            header_keywords = ['交易时间', '对方', '金额']
            header_idx = self.find_header_row(all_rows, header_keywords)
            if header_idx == -1:
                self.log("表头识别失败")
                return

        header_row = all_rows[header_idx]
        col_map = self.map_columns_by_keywords(header_row, {
            'time': ['交易时间', '时间'],
            'direction': ['收/支', '收支', '类型'],
            'counterparty': ['交易对方', '对方'],
            'goods': ['商品说明', '商品'],
            'payment_method': ['收/付款方式', '方式'],
            'amount': ['金额', '交易金额'],
            'order_id': ['交易订单号', '订单号'],
            'merchant_order': ['商家订单号', '商家单号']
        })

        if len(col_map) < 4:
            self.log("列映射不完整，使用默认列序（支付宝标准格式）")
            col_map = {
                'time': 0,
                'direction': 1,
                'counterparty': 2,
                'goods': 3,
                'payment_method': 4,
                'amount': 5,
                'order_id': 6,
                'merchant_order': 7
            }

        for row in self.iterate_rows_with_progress(all_rows[header_idx+1:], desc="解析交易行"):
            if not any(row):
                continue

            time_str = self.get_cell_safe(row, col_map.get('time', 0))
            amount_str = self.get_cell_safe(row, col_map.get('amount', 5))

            if not time_str or not amount_str:
                continue

            amount = safe_float(amount_str)
            if amount is None:
                continue

            direction_raw = self.get_cell_safe(row, col_map.get('direction', 1))
            if '收入' in direction_raw:
                direction = "收入"
            elif '支出' in direction_raw:
                direction = "支出"
            elif '不计' in direction_raw:
                direction = "其他"
            else:
                direction = "收入" if amount >= 0 else "支出"

            f_date, weekday = self.parse_date(time_str)

            counterparty = self.get_cell_safe(row, col_map.get('counterparty', 2))
            goods = self.get_cell_safe(row, col_map.get('goods', 3))
            payment_method = self.get_cell_safe(row, col_map.get('payment_method', 4))
            order_id = self.get_cell_safe(row, col_map.get('order_id', 6))
            merchant_order = self.get_cell_safe(row, col_map.get('merchant_order', 7))

            summary = f"{goods} {payment_method}".strip()

            tx = {
                '交易日期': f_date,
                '星期': weekday,
                '交易方向': direction,
                '交易金额': amount,
                '交易对方': counterparty,
                '商品说明': goods,
                '付款方式': payment_method,
                '交易订单号': order_id,
                '商家订单号': merchant_order,
                '摘要': summary,
                '交易分类': self.classify_transaction(summary, counterparty, amount) if direction != "其他" else "不计收支",
            }
            self.transactions.append(tx)

        self.log(f"解析完成，共 {len(self.transactions)} 笔交易")