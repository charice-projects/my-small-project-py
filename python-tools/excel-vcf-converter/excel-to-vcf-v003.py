#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 转 vCard 转换器 v3.1
====================================
[模块信息]
    模块名称: ExcelToVCFConverter
    版本号: 3.1.0
    发布日期: 2026-04-09
    维护者: 西施先生

[依赖库]
    pip install pandas openpyxl

[功能概述]
    将 Excel 文件中的联系人数据转换为标准 vCard 3.0 格式（.vcf），
    支持智能字段映射、多值拆分（如一个单元格内多个电话/邮箱）、
    路径自动清洗（移除不可见字符）、可选分批输出等高级功能。
    解决因 Excel 中多号码/多邮箱导致手机导入失败的问题。

[核心特性]
    ✅ 智能识别中英文列名（姓名、手机、公司、邮箱、地址等）
    ✅ 单元格内多值自动拆分（支持逗号、分号、空格、换行等分隔符）
    ✅ 彻底清洗输入路径（移除零宽字符、方向格式符 U+202A 等）
    ✅ 可选分批输出（例如每 200 条一个 .vcf 文件）
    ✅ 支持命令行模式与交互模式
    ✅ 兼容 vCard 3.0，每条记录间空行分隔，提升导入稳定性

[使用场景]
    - 将企业/个人 Excel 通讯录批量导入手机
    - 从 CRM 系统导出联系人后转换为手机可读格式
    - 处理包含多个电话/邮箱的复杂表格

[安全说明]
    - 本工具完全离线运行，不会上传任何数据
    - 输出文件保存在本地，请妥善保管

[更新日志]
    v3.1.0 (2026-04-09) - 修复方向格式符导致路径识别失败的问题
    v3.0.0 (2026-04-09) - 重构路径清洗、增加命令行参数、日志系统
    v2.0.0 (2026-03-24) - 支持多值拆分、分批输出
    v1.0.0 (2026-01-26) - 初始版本
"""

# 代码正文...
import os
import re
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ExcelToVCFConverter:
    """Excel转VCF转换器，支持智能字段映射、多值拆分、输入清洗"""

    def __init__(self):
        # 字段映射配置（支持中英文多种列名）
        self.field_mapping = {
            'name': ['姓名', '名字', '名称', 'name', '联系人', '全名', 'fullname', 'nickname'],
            'mobile': ['手机', '号码', '移动电话', '手机号', 'mobile', '电话', '联系电话', '手机号码', '电话1', 'cell', 'cellular'],
            'tel_work': ['工作电话', '办公电话', '公司电话', 'work phone', '电话2', 'work', 'business'],
            'tel_home': ['家庭电话', '住宅电话', 'home phone', '电话3', 'home', 'landline'],
            'company': ['公司', '单位', 'company', '组织', '机构', 'organization', 'org'],
            'title': ['职位', '职务', 'title', 'position', '职称', 'job title'],
            'note': ['备注', '说明', 'note', '注释', '描述', 'remark', 'memo'],
            'email': ['邮箱', '电子邮件', 'email', '电子邮箱', 'mail', 'e-mail'],
            'address': ['地址', '住址', 'address', '家庭住址', '公司地址', 'street']
        }

        # 多值字段分隔符（正则表达式）
        self.value_separator = r'[,;、\n\r\t\s]+'

        # 输出分批大小（0表示不分批）
        self.batch_size = 0

        # 是否开启调试模式（显示不可见字符）
        self.debug = False

    # ----------------------------------------------------------------------
    # 输入清洗与路径规范化（增强版）
    # ----------------------------------------------------------------------
    @staticmethod
    def clean_input_path(raw_path: str, debug: bool = False) -> str:
        """
        彻底清洗用户输入的路径字符串，去除：
        - 所有 Unicode 控制字符（包括方向格式字符 U+202A~U+202E）
        - 零宽字符、BOM、不换行空格
        - ASCII 控制字符
        - 各种引号
        - 并将反斜杠统一为正斜杠
        """
        if not isinstance(raw_path, str):
            raw_path = str(raw_path)

        original = raw_path

        # 1. 移除所有 Unicode 控制字符（类别 Cc, Cf, Cn, Co, Cs）
        #    特别包括：方向格式字符（LRE, RLE, LRO, RLO, PDF, LRI, RLI, FSI, PDI）
        #    U+202A (LRE), U+202B (RLE), U+202C (PDF), U+202D (LRO), U+202E (RLO)
        #    U+2066 (LRI), U+2067 (RLI), U+2068 (FSI), U+2069 (PDI)
        #    使用正则 \p{C} 需要 regex 库，这里用明确范围 + 常见字符
        control_chars = (
            '\u200b\u200c\u200d\u200e\u200f'   # 零宽字符
            '\u202a\u202b\u202c\u202d\u202e'   # 方向格式
            '\u2066\u2067\u2068\u2069'         # 额外的方向隔离符
            '\ufeff\u00a0'                     # BOM、不换行空格
        )
        # 先移除这些特定字符
        cleaned = re.sub(f'[{control_chars}]', '', raw_path)

        # 2. 移除所有 ASCII 控制字符（0x00-0x1F, 0x7F）
        cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned)

        # 3. 移除所有其他 Unicode 控制字符（一般类别 Cc 和 Cf）
        #    使用 Unicode 属性需要 regex 库，这里用范围 \u0000-\u001F 已覆盖，补充 \u0080-\u009F
        cleaned = re.sub(r'[\u0080-\u009f]', '', cleaned)

        # 4. 首尾空白
        cleaned = cleaned.strip()

        # 5. 去除成对的常见引号（单、双、弯引号）
        quote_pairs = [('"', '"'), ("'", "'"), ('“', '”'), ('‘', '’')]
        for left, right in quote_pairs:
            if cleaned.startswith(left) and cleaned.endswith(right):
                cleaned = cleaned[1:-1]
                break

        # 6. 将反斜杠统一为正斜杠
        cleaned = cleaned.replace('\\', '/')

        # 7. 移除末尾多余的斜杠
        cleaned = cleaned.rstrip('/')

        # 8. 处理可能残留的 Windows 盘符冒号后的斜杠问题（C:/ 已经是正确的）
        #    不需要额外处理

        if debug and cleaned != original:
            logger.debug(f"路径清洗: {repr(original)} -> {repr(cleaned)}")
        return cleaned

    @staticmethod
    def validate_path(path_str: str) -> Optional[Path]:
        """验证路径是否存在，返回 Path 对象或 None"""
        try:
            p = Path(path_str)
            if p.exists():
                return p.resolve()
            else:
                logger.error(f"文件不存在: {p}")
                return None
        except Exception as e:
            logger.error(f"无效路径: {path_str} - {e}")
            return None

    # ----------------------------------------------------------------------
    # 文本清理
    # ----------------------------------------------------------------------
    @staticmethod
    def clean_text(text) -> str:
        if pd.isna(text) or text == '':
            return ""
        text_str = str(text).strip()
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text_str)
        cleaned = re.sub(r'[\n\r]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    @staticmethod
    def clean_phone(phone) -> str:
        if pd.isna(phone) or phone == '':
            return ""
        phone_str = str(phone).strip()
        cleaned = re.sub(r'[^\d\+\s\(\)\-\.]', '', phone_str)
        return cleaned.strip()

    def split_values(self, value: str) -> List[str]:
        if pd.isna(value) or str(value).strip() == '':
            return []
        parts = re.split(self.value_separator, str(value))
        return [p.strip() for p in parts if p.strip()]

    # ----------------------------------------------------------------------
    # 列映射检测
    # ----------------------------------------------------------------------
    def detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        column_mapping = {}
        logger.info("开始字段映射检测...")
        for col in df.columns:
            col_str = str(col).strip()
            col_lower = col_str.lower()
            matched = False
            for field, keywords in self.field_mapping.items():
                for keyword in keywords:
                    if keyword.lower() in col_lower:
                        column_mapping[col] = field
                        logger.info(f"  ✓ 映射: '{col}' -> {field}")
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                column_mapping[col] = col
                logger.info(f"  ? 未识别: '{col}'，将保留原值（不用于输出）")
        return column_mapping

    # ----------------------------------------------------------------------
    # vCard 生成
    # ----------------------------------------------------------------------
    def create_vcard(self, row: pd.Series, column_mapping: Dict[str, str]) -> str:
        vcard_lines = ["BEGIN:VCARD", "VERSION:3.0"]

        # 姓名
        name = ""
        for col, field in column_mapping.items():
            if field == 'name' and pd.notna(row[col]) and str(row[col]).strip():
                name = self.clean_text(row[col])
                break
        if not name:
            for col in row.index:
                if pd.notna(row[col]) and str(row[col]).strip():
                    name = self.clean_text(row[col])
                    break
        if not name:
            name = "未知联系人"

        vcard_lines.append(f"N:{name}")
        vcard_lines.append(f"FN:{name}")

        # 电话
        phones_by_type = {'mobile': [], 'tel_work': [], 'tel_home': []}
        for col, field in column_mapping.items():
            if field in phones_by_type and pd.notna(row[col]) and str(row[col]).strip():
                raw = str(row[col]).strip()
                numbers = self.split_values(raw)
                for num in numbers:
                    cleaned = self.clean_phone(num)
                    if cleaned:
                        phones_by_type[field].append(cleaned)

        for tel_type, numbers in phones_by_type.items():
            for num in numbers:
                if tel_type == 'mobile':
                    vcard_lines.append(f"TEL;CELL:{num}")
                elif tel_type == 'tel_work':
                    vcard_lines.append(f"TEL;WORK:{num}")
                elif tel_type == 'tel_home':
                    vcard_lines.append(f"TEL;HOME:{num}")

        if not phones_by_type['mobile'] and any(phones_by_type.values()):
            first_phone = next((p for p in phones_by_type['tel_work'] + phones_by_type['tel_home'] if p), None)
            if first_phone:
                vcard_lines.append(f"TEL;CELL:{first_phone}")

        # 公司
        company = ""
        for col, field in column_mapping.items():
            if field == 'company' and pd.notna(row[col]) and str(row[col]).strip():
                company = self.clean_text(row[col])
                break
        if company:
            vcard_lines.append(f"ORG:{company}")

        # 职位
        title = ""
        for col, field in column_mapping.items():
            if field == 'title' and pd.notna(row[col]) and str(row[col]).strip():
                title = self.clean_text(row[col])
                break
        if title:
            vcard_lines.append(f"TITLE:{title}")

        # 备注
        note = ""
        for col, field in column_mapping.items():
            if field == 'note' and pd.notna(row[col]) and str(row[col]).strip():
                note = self.clean_text(row[col])
                break
        if note:
            vcard_lines.append(f"NOTE:{note}")

        # 邮箱
        emails = []
        for col, field in column_mapping.items():
            if field == 'email' and pd.notna(row[col]) and str(row[col]).strip():
                raw = str(row[col]).strip()
                parts = self.split_values(raw)
                for e in parts:
                    if '@' in e:
                        emails.append(e.strip())
        for email in emails:
            vcard_lines.append(f"EMAIL:{email}")

        # 地址
        address = ""
        for col, field in column_mapping.items():
            if field == 'address' and pd.notna(row[col]) and str(row[col]).strip():
                address = self.clean_text(row[col])
                break
        if address:
            vcard_lines.append(f"ADR:;;{address};;;;")

        vcard_lines.append("END:VCARD")
        return '\n'.join(vcard_lines)

    # ----------------------------------------------------------------------
    # 核心转换
    # ----------------------------------------------------------------------
    def convert_excel_to_vcf(self, excel_file: Union[str, Path], vcf_file: Union[str, Path] = None,
                             sheet_name: Union[str, int] = 0) -> Tuple[Optional[str], int]:
        excel_path = self.validate_path(str(excel_file))
        if excel_path is None:
            return None, 0

        logger.info(f"正在读取Excel文件: {excel_path}")
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name, dtype=str)
            df = df.fillna('')
        except Exception as e:
            logger.error(f"读取Excel失败: {e}")
            return None, 0

        total_rows = len(df)
        logger.info(f"成功读取，共 {total_rows} 条记录")
        logger.debug(f"列名: {list(df.columns)}")

        column_mapping = self.detect_columns(df)

        if vcf_file is None:
            base_name = excel_path.stem
            vcf_file = excel_path.parent / f"{base_name}_通讯录.vcf"
        else:
            vcf_path = Path(vcf_file)
            if vcf_path.parent == Path('.'):
                vcf_path = excel_path.parent / vcf_path
            if vcf_path.suffix.lower() != '.vcf':
                vcf_path = vcf_path.with_suffix('.vcf')
            vcf_file = vcf_path

        vcf_file.parent.mkdir(parents=True, exist_ok=True)

        if self.batch_size > 0:
            base_stem = vcf_file.stem
            parent = vcf_file.parent
            ext = vcf_file.suffix
            batch_files = []
            total_success = 0
            for start_idx in range(0, total_rows, self.batch_size):
                end_idx = min(start_idx + self.batch_size, total_rows)
                batch_df = df.iloc[start_idx:end_idx]
                batch_file = parent / f"{base_stem}_part{start_idx // self.batch_size + 1}{ext}"
                success = self._write_vcf_file(batch_df, column_mapping, batch_file, start_idx + 1)
                total_success += success
                batch_files.append(batch_file)
            logger.info(f"✅ 分批转换完成，共生成 {len(batch_files)} 个文件，成功 {total_success}/{total_rows} 条记录")
            for f in batch_files:
                logger.info(f"  - {f}")
            return str(vcf_file), total_success
        else:
            success = self._write_vcf_file(df, column_mapping, vcf_file)
            return str(vcf_file), success

    def _write_vcf_file(self, df: pd.DataFrame, column_mapping: Dict[str, str],
                        output_file: Path, start_index: int = 1) -> int:
        vcards = []
        success_count = 0
        logger.info(f"正在处理 {output_file} ...")
        for idx, row in df.iterrows():
            try:
                vcard = self.create_vcard(row, column_mapping)
                vcards.append(vcard)
                success_count += 1
                if success_count % 50 == 0:
                    logger.info(f"  已处理 {success_count} 条记录...")
            except Exception as e:
                logger.warning(f"第 {idx + start_index} 行处理失败: {e}")
                continue

        if vcards:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(vcards) + '\n')
            logger.info(f"  ✓ 成功写入 {len(vcards)} 条记录到 {output_file}")
            logger.info(f"    文件大小: {output_file.stat().st_size} 字节")
        else:
            logger.warning("没有有效记录，未生成文件")
        return success_count


# ----------------------------------------------------------------------
# 命令行与交互
# ----------------------------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(description='Excel转vCard通讯录转换器 v3.1')
    parser.add_argument('-i', '--input', help='输入Excel文件路径')
    parser.add_argument('-o', '--output', help='输出vcf文件路径')
    parser.add_argument('-s', '--sheet', default=0, help='工作表名或索引')
    parser.add_argument('-b', '--batch', type=int, default=0, help='每批记录数')
    parser.add_argument('-d', '--debug', action='store_true', help='开启调试模式')
    return parser.parse_args()


def interactive_mode(converter: ExcelToVCFConverter):
    print("\n" + "=" * 60)
    print("Excel转vCard通讯录转换器 v3.1".center(60))
    print("=" * 60)
    print("提示：可直接拖拽Excel文件到本窗口，然后按回车")
    raw_input_path = input("请输入Excel文件路径: ").strip()
    excel_file = converter.clean_input_path(raw_input_path, debug=converter.debug)

    excel_path = converter.validate_path(excel_file)
    if excel_path is None:
        logger.error("文件不存在，请检查路径中的不可见字符或转义问题")
        if converter.debug:
            logger.debug(f"原始输入: {repr(raw_input_path)}")
            logger.debug(f"清洗后: {repr(excel_file)}")
        return

    # 工作表选择
    try:
        xl = pd.ExcelFile(excel_path)
        sheet_names = xl.sheet_names
        xl.close()
        if len(sheet_names) > 1:
            print(f"发现多个工作表: {sheet_names}")
            sheet_input = input("请输入要使用的工作表名 (直接回车使用第一个): ").strip()
            if sheet_input in sheet_names:
                sheet_name = sheet_input
            else:
                sheet_name = sheet_names[0]
                print(f"使用默认工作表: {sheet_name}")
        else:
            sheet_name = sheet_names[0]
    except Exception as e:
        logger.warning(f"无法获取工作表信息，使用索引0: {e}")
        sheet_name = 0

    # 输出文件
    default_vcf = excel_path.parent / f"{excel_path.stem}_通讯录.vcf"
    output_input = input(f"请输入输出vcf文件路径 (直接回车使用: {default_vcf}): ").strip()
    if not output_input:
        vcf_file = default_vcf
    else:
        vcf_file = converter.clean_input_path(output_input, debug=converter.debug)
        vcf_path = Path(vcf_file)
        if vcf_path.suffix.lower() != '.vcf':
            vcf_path = vcf_path.with_suffix('.vcf')
        vcf_file = vcf_path

    # 分批
    batch_input = input("是否需要分批输出？(y/n, 默认n): ").strip().lower()
    if batch_input in ('y', 'yes'):
        try:
            batch_size = int(input("请输入每批记录数 (如 200): ").strip())
            if batch_size > 0:
                converter.batch_size = batch_size
                logger.info(f"将按每批 {batch_size} 条记录拆分输出")
        except:
            logger.warning("输入无效，将不分批")

    logger.info("\n开始转换...")
    result_file, success = converter.convert_excel_to_vcf(excel_path, vcf_file, sheet_name)

    if result_file:
        print("\n📱 导入到手机的方法:")
        print("1. 将vcf文件发送到手机 (通过邮件、微信、QQ等)")
        print("2. 在手机上使用『文件管理』应用找到vcf文件")
        print("3. 点击vcf文件，选择『联系人』或『通讯录』应用打开")
        print("4. 确认导入所有联系人")
        print(f"\n💡 提示: 输出文件位于 {result_file}")
        if success == 0:
            print("⚠️ 警告: 没有成功转换任何记录，请检查Excel格式或列名映射。")

        try:
            open_dir = input("\n是否打开文件所在目录？(y/n, 默认n): ").strip().lower()
            if open_dir in ('y', 'yes'):
                output_path = Path(result_file)
                if sys.platform == 'win32':
                    os.startfile(output_path.parent)
                elif sys.platform == 'darwin':
                    os.system(f'open "{output_path.parent}"')
                else:
                    os.system(f'xdg-open "{output_path.parent}"')
        except:
            pass


def quick_convert(excel_file: str, vcf_file: str = None, sheet_name=0,
                  batch_size: int = 0, debug: bool = False) -> Tuple[Optional[str], int]:
    converter = ExcelToVCFConverter()
    converter.batch_size = batch_size
    converter.debug = debug
    if debug:
        logger.setLevel(logging.DEBUG)
    return converter.convert_excel_to_vcf(excel_file, vcf_file, sheet_name)


def main():
    args = parse_arguments()
    converter = ExcelToVCFConverter()
    converter.debug = args.debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.input:
        excel_file = converter.clean_input_path(args.input, debug=args.debug)
        excel_path = converter.validate_path(excel_file)
        if excel_path is None:
            logger.error("无效的输入文件")
            sys.exit(1)
        output = args.output
        if output:
            output = converter.clean_input_path(output, debug=args.debug)
        converter.batch_size = args.batch
        result_file, success = converter.convert_excel_to_vcf(excel_path, output, args.sheet)
        if result_file:
            logger.info(f"转换完成，成功 {success} 条记录，输出文件: {result_file}")
        else:
            logger.error("转换失败")
            sys.exit(1)
    else:
        interactive_mode(converter)


if __name__ == "__main__":
    main()