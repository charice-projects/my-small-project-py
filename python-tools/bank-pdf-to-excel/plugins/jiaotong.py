# -*- coding: utf-8 -*-
"""
交通银行对账单解析插件 (v1.0)

格式特征：
    - 16 列固定表格：序号|会计日期|交易日期|交易名称|凭证种类|凭证号码|
                    借方发生额|贷方发生额|余额|卡号|交易地点|
                    对方账号|对方户名|对方行名|摘要|流水号
    - pdfplumber.extract_tables() 完美支持（空列保留，列数稳定 16）
    - 每页均有表头（多页时需跳过）

方向判断：
    - 借方发生额非空 → 支出（金额取负）
    - 贷方发生额非空 → 收入（金额取正）
"""

import re
from typing import Dict, List, Tuple, Optional

from .base import StatementPlugin
from utils.parser_common import BasePDFParser
from utils.helpers import clean_text, safe_float


class JiaoTongPlugin(StatementPlugin):
    @property
    def name(self) -> str:
        return "交通银行"

    @property
    def identifier(self) -> str:
        return "jiaotong"

    def detect(self, pdf_path: str) -> bool:
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages[:2]:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
        except Exception:
            pass
        text = clean_text(text)
        return "交通银行" in text and "明细对账单" in text

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        parser = _JiaoTongParser(verbose)
        success = parser.run(pdf_path)
        if not success:
            return {}, []
        return parser.account_info, parser.transactions


class _JiaoTongParser(BasePDFParser):
    """交通银行解析器"""

    # 16 列固定索引
    COL = {
        'seq': 0,             # 序号
        'account_date': 1,    # 会计日期
        'trans_date': 2,      # 交易日期
        'trans_name': 3,      # 交易名称
        'voucher_type': 4,    # 凭证种类
        'voucher_no': 5,      # 凭证号码
        'debit': 6,           # 借方发生额（支出）
        'credit': 7,          # 贷方发生额（收入）
        'balance': 8,         # 余额
        'card_no': 9,         # 卡号
        'location': 10,       # 交易地点/渠道
        'cp_account': 11,     # 对方账号
        'cp_name': 12,        # 对方户名
        'cp_bank': 13,        # 对方行名
        'summary': 14,        # 摘要
        'serial': 15,         # 流水号
    }

    HEADER_KEYWORDS = ['序号', '会计日期', '借方发生额', '贷方发生额', '余额']

    def run(self, pdf_path: str) -> bool:
        self._plugin_name = "交通银行"
        if not self.load_pdf(pdf_path):
            return False
        self._extract_account_info()
        self._parse_transactions(pdf_path)
        return len(self.transactions) > 0

    # ---------- 账户信息 ----------
    def _extract_account_info(self) -> None:
        info = {"银行/平台": "交通银行"}
        text = self.raw_text[:2000]

        m = re.search(r'开户机构[：:]\s*(\S+)', text)
        if m:
            info['开户机构'] = m.group(1)
        m = re.search(r'账号[：:]\s*(\d+)', text)
        if m:
            info['账号'] = m.group(1)
        m = re.search(r'户名[：:]\s*(\S+)', text)
        if m:
            info['户名'] = m.group(1)

        year_m = re.search(r'年份[：:]\s*(\d+)', text)
        month_m = re.search(r'月份[：:]\s*(\d+)', text)
        if year_m and month_m:
            info['账单年月'] = f"{year_m.group(1)}年{month_m.group(1)}月"

        m = re.search(r'出单截至日期[：:]\s*(\d{4}-\d{2}-\d{2})', text)
        if m:
            info['出单日期'] = m.group(1)

        self.account_info = info

    # ---------- 交易解析 ----------
    def _parse_transactions(self, pdf_path: str) -> None:
        tables = self.extract_tables(pdf_path)
        if not tables:
            self.log("未提取到任何表格")
            return

        all_rows: List[List[str]] = []
        for table in tables:
            all_rows.extend(table)

        if not all_rows:
            return

        # 定位第一个表头
        header_idx = -1
        for i, row in enumerate(all_rows):
            row_text = ' '.join(str(c) for c in row if c)
            if all(kw in row_text for kw in self.HEADER_KEYWORDS):
                header_idx = i
                break

        if header_idx == -1:
            self.log("表头识别失败")
            return

        self.log(f"表头定位成功（第 {header_idx + 1} 行）")

        for row in self.iterate_rows_with_progress(all_rows[header_idx + 1:], desc="解析交易行"):
            tx = self._parse_row(row)
            if tx:
                self.transactions.append(tx)

        self.log(f"共解析 {len(self.transactions)} 笔交易")

    def _parse_row(self, row: List[str]) -> Optional[Dict]:
        if not row or len(row) < 9:
            return None

        def get(key: str) -> str:
            idx = self.COL.get(key)
            if idx is None or idx >= len(row):
                return ""
            val = row[idx]
            if val is None:
                return ""
            # 单元格内换行合并为空格
            return re.sub(r'\s+', ' ', str(val)).strip()

        # 序号必须是纯数字（自动跳过重复表头和说明行）
        seq_str = get('seq')
        if not seq_str or not seq_str.isdigit():
            return None

        # 日期优先用"交易日期"，回退"会计日期"
        date_str = get('trans_date') or get('account_date')
        if not date_str:
            return None

        # 借贷金额 → 方向判定
        debit_str = get('debit')
        credit_str = get('credit')
        debit = safe_float(debit_str) if debit_str else None
        credit = safe_float(credit_str) if credit_str else None

        if debit and debit > 0:
            direction = "支出"
            amount = -abs(debit)
        elif credit and credit > 0:
            direction = "收入"
            amount = abs(credit)
        else:
            # 借贷都空，无法判断（跳过）
            return None

        balance = safe_float(get('balance')) if get('balance') else None

        f_date, weekday = self.parse_date(date_str)

        trans_name = get('trans_name')
        summary = get('summary')
        cp_name = get('cp_name')
        cp_account = get('cp_account')
        cp_bank = get('cp_bank')
        location = get('location')
        card_no = get('card_no')
        serial = get('serial')

        # 交易分类（合并交易名称 + 摘要作为关键词来源）
        cat = self.classify_transaction(
            trans_name + ' ' + summary,
            cp_name,
            amount
        )

        return {
            '交易日期': f_date,
            '星期': weekday,
            '交易名称': trans_name,
            '交易方向': direction,
            '交易金额': amount,
            '账户余额': balance,
            '摘要': summary,
            '对手信息': cp_name,
            '对方账号': cp_account,
            '对方行名': cp_bank,
            '交易地点': location,
            '卡号': card_no,
            '流水号': serial,
            '交易分类': cat,
        }