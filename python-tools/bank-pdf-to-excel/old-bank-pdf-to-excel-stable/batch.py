#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
银行流水 PDF 批量解析工具 (v1.0)

用法：
    python batch.py <输入目录或PDF文件>                 # 默认输出到输入目录
    python batch.py <输入> -o <输出目录>                # 指定输出目录
    python batch.py <输入> -p "农业*"                   # 文件名通配符筛选
    python batch.py <输入> -v                           # 显示详细信息

特点：
    - 自动检测每个 PDF 的银行类型（复用 PLUGINS）
    - 一 PDF → 一 Excel（同名冲突时自动加时间戳）
    - 单个失败不影响后续，最后输出汇总 CSV
"""

import sys
import os
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
from tqdm import tqdm

from utils.helpers import normalize_path
from plugins import PLUGINS, get_plugin_by_identifier
from main import export_excel, generate_report


def find_pdf_files(input_path: Path, pattern: Optional[str] = None) -> List[Path]:
    """查找 PDF 文件"""
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() == '.pdf' else []

    if input_path.is_dir():
        pdfs = list(input_path.glob('*.pdf')) + list(input_path.glob('*.PDF'))
        pdfs = sorted(set(pdfs))
        if pattern:
            import fnmatch
            pdfs = [p for p in pdfs if fnmatch.fnmatch(p.name, pattern)]
        return pdfs

    return []


def detect_plugin(pdf_path: Path):
    """自动检测插件（跳过通用后备，兜底单独处理）"""
    for plugin in PLUGINS:
        if plugin.identifier == 'universal':
            continue
        try:
            if plugin.detect(str(pdf_path)):
                return plugin
        except Exception:
            continue
    return None


def process_one(pdf_path: Path, output_dir: Path, verbose: bool = False) -> Dict:
    """处理单个 PDF，返回结果统计"""
    result = {
        'file': pdf_path.name,
        'path': str(pdf_path),
        'status': 'unknown',
        'plugin': None,
        'count': 0,
        'output': None,
        'error': None,
        'elapsed': 0.0,
    }
    t0 = time.time()

    # 1. 检测插件
    plugin = detect_plugin(pdf_path)
    if plugin is None:
        plugin = get_plugin_by_identifier('universal')
        if plugin is None:
            result['status'] = 'no_plugin'
            result['error'] = '无法识别格式且无通用兜底'
            return result
        result['plugin'] = f"{plugin.name}(兜底)"
    else:
        result['plugin'] = plugin.name

    # 2. 解析
    try:
        account_info, transactions = plugin.parse(str(pdf_path), verbose=verbose)
    except Exception as e:
        result['status'] = 'parse_error'
        result['error'] = str(e)[:200]
        result['elapsed'] = time.time() - t0
        return result

    if not transactions:
        result['status'] = 'empty'
        result['error'] = '未提取到交易记录'
        result['elapsed'] = time.time() - t0
        return result

    result['count'] = len(transactions)

    # 3. 导出（同名冲突自动加时间戳）
    output_path = output_dir / f"{pdf_path.stem}.xlsx"
    if output_path.exists():
        ts = datetime.now().strftime('%H%M%S')
        output_path = output_dir / f"{pdf_path.stem}_{ts}.xlsx"

    try:
        export_excel(str(output_path), plugin.name, account_info, transactions)
        generate_report(str(output_path), transactions)
        result['output'] = str(output_path)
        result['status'] = 'success'
    except Exception as e:
        result['status'] = 'export_error'
        result['error'] = str(e)[:200]

    result['elapsed'] = time.time() - t0
    return result


def main():
    parser = argparse.ArgumentParser(description='银行流水 PDF 批量解析工具')
    parser.add_argument('input', help='输入目录或 PDF 文件路径')
    parser.add_argument('-o', '--output', help='输出目录（默认为输入目录）')
    parser.add_argument('-p', '--pattern', help='文件名通配符（如 "农业*"）')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    args = parser.parse_args()

    input_path = normalize_path(args.input)
    if not input_path.exists():
        print(f"❌ 路径不存在：{input_path}")
        sys.exit(1)

    output_dir = normalize_path(args.output) if args.output else (
        input_path if input_path.is_dir() else input_path.parent
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = find_pdf_files(input_path, args.pattern)
    if not pdfs:
        print(f"❌ 未找到任何 PDF 文件")
        sys.exit(1)

    print("=" * 60)
    print(f"📦 批量解析：共 {len(pdfs)} 个 PDF")
    print(f"📁 输出目录：{output_dir}")
    print("=" * 60)

    results: List[Dict] = []
    pbar = tqdm(pdfs, desc="总体进度", unit="个", ncols=100)
    for pdf in pbar:
        pbar.set_postfix_str(pdf.name[:35])
        r = process_one(pdf, output_dir, args.verbose)
        results.append(r)
        ok = sum(1 for x in results if x['status'] == 'success')
        pbar.set_postfix_str(f"✓{ok} / 共{len(results)} | {pdf.name[:25]}")

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print("📊 批量处理汇总")
    print("=" * 60)

    success = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']

    print(f"✅ 成功：{len(success)} / {len(results)}")
    print(f"❌ 失败：{len(failed)} / {len(results)}\n")

    if success:
        print("【成功列表】")
        for r in success:
            print(f"  ✓ {r['file'][:45]:45} {r['plugin']:12} {r['count']:>5} 笔  {r['elapsed']:.1f}s")
        print()

    if failed:
        print("【失败列表】")
        for r in failed:
            print(f"  ✗ {r['file'][:45]:45} [{r['status']}] {r['error'] or ''}")
        print()

    # 汇总 CSV
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_csv = output_dir / f"_batch_summary_{ts}.csv"
    pd.DataFrame(results).to_csv(summary_csv, index=False, encoding='utf-8-sig')
    print(f"📋 汇总报表：{summary_csv}")

    total_count = sum(r['count'] for r in success)
    total_time = sum(r['elapsed'] for r in success)
    print(f"\n🎉 共处理 {total_count} 笔交易，成功文件总耗时 {total_time:.1f}s")

    input("\n按 Enter 键退出...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)