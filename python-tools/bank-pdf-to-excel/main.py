#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
银行/支付流水 PDF 智能解析工具 - 主程序 (v2.7)

v2.7 修复（2026-11）：
    - 账户信息 Sheet：删除重复表头、修复末尾行未框线、去掉多余冻结
    - 解析失败时自动重试手动选插件（自动检测误命中场景）

v2.6 改进（2026-11）：
    - Excel 输出样式化：边框、冻结首行、筛选、列宽、千分位数字、分区表头
    - 账户信息 Sheet 合并交易汇总（原"统计分析"内容并入）
    - 新增期初/期末余额、汇总时间范围、分节浅黄底
    - 兼容 nongye.py 的非标字段（交易摘要/本次余额/无交易方向）
"""

import sys
import os
import time
import gc
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List

import pandas as pd
from openpyxl.styles import Font, Border, Side, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from utils.helpers import normalize_path
from plugins import PLUGINS, get_plugin_by_identifier


# ============ Excel 样式配置 ============
_HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
_HEADER_FONT = Font(name="微软雅黑", size=11, bold=True, color="1F4E78")
_BODY_FONT = Font(name="微软雅黑", size=10)
_SECTION_FONT = Font(name="微软雅黑", size=11, bold=True, color="1F4E78")
_SECTION_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
_THIN_SIDE = Side(style="thin", color="B0B0B0")
_BORDER = Border(left=_THIN_SIDE, right=_THIN_SIDE, top=_THIN_SIDE, bottom=_THIN_SIDE)
_CENTER = Alignment(horizontal="center", vertical="center")
_LEFT = Alignment(horizontal="left", vertical="center")
_NUMBER_FMT = "#,##0.00"

# 列宽映射（按字段名）
_COL_WIDTH = {
    "交易日期": 12, "星期": 10, "摘要": 22, "交易方向": 10,
    "交易金额": 14, "账户余额": 14, "对手信息": 42, "交易分类": 10,
    "交易时间": 11, "交易摘要": 22, "本次余额": 14,
    "日志号": 16, "交易渠道": 12, "交易附言": 22,
    "交易名称": 18, "对方账号": 25, "对方行名": 20,
    "交易地点": 12, "卡号": 25, "流水号": 22,
    "交易单号": 25, "交易类型": 12, "交易方式": 12, "商户单号": 25,
    "商品说明": 22, "付款方式": 12, "交易订单号": 25, "商家订单号": 25,
    "附言": 20, "收单机构": 22, "序号": 8,
}
_DEFAULT_WIDTH = 15


def list_plugins() -> None:
    print("\n可用的解析插件：")
    for i, p in enumerate(PLUGINS, 1):
        print(f"  {i}. {p.name} ({p.identifier})")


def manual_select() -> str:
    list_plugins()
    while True:
        choice = input("\n请输入插件序号或标识符：").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(PLUGINS):
                return PLUGINS[idx].identifier
        else:
            plugin = get_plugin_by_identifier(choice)
            if plugin:
                return plugin.identifier
        print("无效选择，请重新输入")


def generate_report(output_path: str, transactions: List[Dict]) -> None:
    from collections import Counter

    report_path = output_path.replace('.xlsx', '_report.txt')

    lines = []
    lines.append("=" * 60)
    lines.append(f"📋 解析可信度报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)

    if not transactions:
        lines.append("❌ 无交易数据，报告终止")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return

    df = pd.DataFrame(transactions)
    total = len(df)
    lines.append(f"📊 总交易笔数：{total}")
    lines.append("")

    empty_date = df['交易日期'].isna().sum() if '交易日期' in df.columns else total
    empty_amount = df['交易金额'].isna().sum() if '交易金额' in df.columns else total
    empty_date_rate = empty_date / total
    empty_amount_rate = empty_amount / total

    lines.append("【字段空值检查】")
    lines.append(f"  日期缺失：{empty_date} 笔（{empty_date_rate:.1%}）{' ⚠️ 异常' if empty_date_rate > 0.05 else ' ✅ 正常'}")
    lines.append(f"  金额缺失：{empty_amount} 笔（{empty_amount_rate:.1%}）{' ⚠️ 异常' if empty_amount_rate > 0.05 else ' ✅ 正常'}")
    lines.append("")

    if '交易日期' in df.columns:
        try:
            dates = pd.to_datetime(df['交易日期'], errors='coerce')
            if not dates.isna().all():
                valid_dates = dates.dropna()
                lines.append("【日期范围与密度】")
                lines.append(f"  起始日期：{valid_dates.min().strftime('%Y-%m-%d')}")
                lines.append(f"  结束日期：{valid_dates.max().strftime('%Y-%m-%d')}")
                lines.append(f"  总天数：{(valid_dates.max() - valid_dates.min()).days + 1} 天")

                day_counts = Counter(valid_dates.dt.strftime('%Y-%m-%d'))
                avg_daily = sum(day_counts.values()) / max(len(day_counts), 1)
                abnormal_days = [(d, c) for d, c in day_counts.items() if c > avg_daily * 3 and c > 50]
                if abnormal_days:
                    lines.append(f"  ⚠️ 发现异常密集交易日期（日均 {avg_daily:.1f} 笔）：")
                    for d, c in abnormal_days[:5]:
                        lines.append(f"      {d} : {c} 笔")
                else:
                    lines.append("  ✅ 每日交易量分布正常")
                lines.append("")
        except Exception:
            pass

    if '交易金额' in df.columns and len(df) > 3:
        amounts = df['交易金额'].dropna()
        if len(amounts) > 3:
            mean = amounts.mean()
            std = amounts.std()
            if std > 0:
                extreme = amounts[(amounts > mean + 3 * std) | (amounts < mean - 3 * std)]
                lines.append("【金额异常检测（均值±3倍标准差）】")
                if not extreme.empty:
                    lines.append(f"  ⚠️ 发现 {len(extreme)} 笔极端金额：")
                    for val in extreme.head(5).tolist():
                        lines.append(f"      {val:.2f}")
                else:
                    lines.append("  ✅ 未发现极端金额异常")
                lines.append("")

    has_warning = any("⚠️" in line for line in lines)
    lines.append("=" * 60)
    if has_warning:
        lines.append("📌 结论：发现上述可疑项，建议打开 Excel 后重点复核。")
    else:
        lines.append("✅ 结论：基础数据校验全部通过，数据可信度良好。")
    lines.append("=" * 60)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"📋 可信度报告已生成：{report_path}")


# ============ Excel 样式工具 ============

def _style_header_row(ws, n_cols, row=1):
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = _CENTER
        cell.border = _BORDER


def _style_body(ws, n_rows, n_cols, start_row=2, numeric_cols=None):
    numeric_cols = numeric_cols or set()
    for r in range(start_row, start_row + n_rows):
        for c in range(1, n_cols + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = _BODY_FONT
            cell.border = _BORDER
            cell.alignment = _LEFT
            if c in numeric_cols:
                cell.number_format = _NUMBER_FMT


def _classify_amounts(df):
    if "交易方向" in df.columns:
        inc = df[df["交易方向"] == "收入"]
        exp = df[df["交易方向"] == "支出"]
        oth = df[df["交易方向"] == "其他"] if "其他" in df["交易方向"].unique() else pd.DataFrame()
    else:
        inc = df[df["交易金额"] >= 0]
        exp = df[df["交易金额"] < 0]
        oth = pd.DataFrame()
    return inc, exp, oth


def _write_account_sheet(writer, bank_name, account_info, transactions):
    """
    账户信息 Sheet：账户信息 + 交易汇总
    v2.7 修复：
      - 删除 rows 里的重复 ["项目","内容"]（pandas 会自己写表头）
      - n_rows = len(rows)，不再减 1（修复末尾行未框线）
      - 去掉 freeze_panes（账户信息少行，冻结无意义）
    """
    # v2.7：rows 不再包含表头，pandas 写 columns 时会自动生成
    rows = []

    # ---- 分节 1：账户信息 ----
    rows.append(["【账户信息】", ""])
    rows.append(["银行/平台", bank_name])
    for k, v in account_info.items():
        if k == "银行/平台":
            continue
        rows.append([k, v])

    # ---- 分节 2：交易汇总 ----
    if transactions:
        df = pd.DataFrame(transactions)
        inc, exp, oth = _classify_amounts(df)
        net_flow = inc["交易金额"].sum() + exp["交易金额"].sum()

        date_range_str = ""
        if "交易日期" in df.columns:
            dates = pd.to_datetime(df["交易日期"], errors="coerce").dropna()
            if not dates.empty:
                date_range_str = f"（{dates.min().strftime('%Y-%m-%d')} 至 {dates.max().strftime('%Y-%m-%d')}）"

        rows.append(["【交易汇总】", date_range_str])
        rows.append(["总交易笔数", len(df)])
        rows.append(["收入笔数", len(inc)])
        rows.append(["收入合计（元）", round(inc["交易金额"].sum(), 2) if not inc.empty else 0.0])
        rows.append(["支出笔数", len(exp)])
        rows.append(["支出合计（元）", round(exp["交易金额"].sum(), 2) if not exp.empty else 0.0])
        if not oth.empty:
            rows.append(["其他笔数", len(oth)])
            rows.append(["其他合计（元）", round(oth["交易金额"].sum(), 2)])
        rows.append(["净流入（元）", round(net_flow, 2)])

        balance_col = None
        for col in ("账户余额", "本次余额"):
            if col in df.columns:
                balance_col = col
                break

        if balance_col is not None and "交易金额" in df.columns:
            valid = df.dropna(subset=[balance_col, "交易金额"])
            if not valid.empty:
                first_bal = float(valid[balance_col].iloc[0])
                first_amt = float(valid["交易金额"].iloc[0])
                last_bal = float(valid[balance_col].iloc[-1])
                rows.append(["期初余额（元）", round(first_bal - first_amt, 2)])
                rows.append(["期末余额（元）", round(last_bal, 2)])

    # ---- 写出 ----
    df_out = pd.DataFrame(rows, columns=["项目", "内容"])
    df_out.to_excel(writer, sheet_name="账户信息", index=False)

    ws = writer.sheets["账户信息"]
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 42

    _style_header_row(ws, 2, row=1)

    # v2.7：n_rows = len(rows)，不用减 1（rows 不含表头，pandas 单独写 1 行表头）
    n_rows = len(rows)
    _style_body(ws, n_rows, 2, start_row=2)

    # 分节标题（浅黄底 + 加粗）
    # Excel 行号 = 数据行号 + 1（因表头占第 1 行）
    for i, row_data in enumerate(rows):
        if isinstance(row_data[0], str) and row_data[0].startswith("【"):
            excel_row = i + 2
            ws.cell(row=excel_row, column=1).font = _SECTION_FONT
            ws.cell(row=excel_row, column=2).font = _SECTION_FONT
            for c in (1, 2):
                ws.cell(row=excel_row, column=c).fill = _SECTION_FILL

    # 内容列左对齐 + 数字千分位（覆盖全部数据行）
    for i in range(len(rows)):
        excel_row = i + 2
        b_cell = ws.cell(row=excel_row, column=2)
        b_cell.alignment = _LEFT
        if isinstance(b_cell.value, (int, float)):
            b_cell.number_format = _NUMBER_FMT

    # v2.7：去掉 freeze_panes，账户信息不用冻结


def _write_detail_sheet(writer, transactions):
    if not transactions:
        return

    df = pd.DataFrame(transactions)
    df.to_excel(writer, sheet_name="交易明细", index=False)

    ws = writer.sheets["交易明细"]
    n_rows, n_cols = df.shape[0], df.shape[1]

    for idx, col_name in enumerate(df.columns, start=1):
        width = _COL_WIDTH.get(str(col_name), _DEFAULT_WIDTH)
        ws.column_dimensions[get_column_letter(idx)].width = width

    numeric_cols = set()
    for idx, col_name in enumerate(df.columns, start=1):
        if str(col_name) in ("交易金额", "账户余额", "本次余额"):
            numeric_cols.add(idx)

    _style_header_row(ws, n_cols, row=1)
    _style_body(ws, n_rows, n_cols, start_row=2, numeric_cols=numeric_cols)

    # 交易明细冻结 + 筛选（这个保留，几百上千行有用）
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _write_log_sheet(writer, bank_name, transactions):
    log = {
        "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "银行/平台": bank_name,
        "交易笔数": len(transactions),
    }
    pd.DataFrame([log]).to_excel(writer, sheet_name="日志", index=False)

    ws = writer.sheets["日志"]
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 12
    _style_header_row(ws, 3, row=1)
    _style_body(ws, 1, 3, start_row=2)


def export_excel(output_path: str, bank_name: str, account_info: Dict, transactions: List[Dict]) -> None:
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 创建输出目录：{output_dir}")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        _write_account_sheet(writer, bank_name, account_info, transactions)
        _write_detail_sheet(writer, transactions)
        _write_log_sheet(writer, bank_name, transactions)

    gc.collect()

    try:
        subprocess.run(
            ['powershell', '-command', f'Unblock-File -Path "{output_path}"'],
            capture_output=True,
            check=False
        )
    except Exception:
        pass


def _try_parse(plugin, path: str, verbose: bool):
    """尝试解析，返回 (account_info, transactions)；异常时返回 ({}, [])"""
    try:
        return plugin.parse(str(path), verbose)
    except Exception as e:
        print(f"\n❌ 解析过程异常：{e}")
        import traceback
        traceback.print_exc()
        return {}, []


def main() -> None:
    print("=" * 60)
    print("银行/支付流水 PDF 智能解析工具 v2.7 - 插件化架构")
    print("=" * 60)

    # 1. 获取 PDF 路径
    while True:
        raw = input("\n📂 请输入 PDF 文件路径（支持拖拽）：")
        path = normalize_path(raw)
        if not path.exists():
            print("❌ 文件不存在，请重新输入")
            continue
        break

    # 2. 选择解析模式
    print("\n请选择解析方式：")
    print("  1. 自动检测（推荐）")
    print("  2. 手动指定格式")
    mode = input("请输入选项 (1/2，默认1)：").strip() or "1"

    selected_plugin = None
    if mode == "2":
        identifier = manual_select()
        selected_plugin = get_plugin_by_identifier(identifier)
        if not selected_plugin:
            print("❌ 插件加载失败")
            return
    else:
        print("\n🔍 正在自动检测格式...")
        for plugin in PLUGINS:
            print(f"  尝试 {plugin.name}...", end=" ")
            try:
                matched = plugin.detect(str(path))
            except Exception as e:
                print(f"⚠️ 检测异常已跳过：{e}")
                continue
            if matched:
                print("✅ 匹配")
                selected_plugin = plugin
                break
            else:
                print("❌")
        if not selected_plugin:
            print("\n❌ 自动检测失败，请手动指定格式")
            identifier = manual_select()
            selected_plugin = get_plugin_by_identifier(identifier)

    if not selected_plugin:
        print("❌ 无法确定解析器")
        return

    print(f"\n✅ 使用解析器：{selected_plugin.name}")

    # 3. 输出路径
    default_out = str(path.with_suffix('.xlsx'))
    print(f"\n💾 默认输出路径：{default_out}")
    print("   （您也可以输入完整路径，如 C:\\Output\\report.xlsx，目录将自动创建）")
    out = input("   请输入输出路径（直接回车使用默认）：").strip()
    if not out:
        out = default_out
    if not out.lower().endswith(('.xlsx', '.xls')):
        out += '.xlsx'

    if os.path.exists(out):
        overwrite = input(f"⚠️ {os.path.basename(out)} 已存在，按 Enter 覆盖，输入 c 取消：").strip().lower()
        if overwrite == 'c':
            print("已取消操作")
            return

    verbose = input("🔊 显示详细信息？(y/n，默认 y)：").strip().lower() != 'n'

    # 4. 解析
    start_time = time.time()
    print("\n⏳ 正在解析 PDF（进度条在下方显示，请耐心等待）...\n")

    account_info, transactions = _try_parse(selected_plugin, path, verbose)

    # v2.7：解析失败时，自动重试手动选择
    if not transactions:
        print(f"\n⚠️ 【{selected_plugin.name}】未解析到任何交易记录。")
        print("   可能是自动检测误命中（如赣州 PDF 含'支付宝'字样被 AliPayPlugin 抢）。")
        retry = input("\n是否手动重新选择插件重试？(Y/n，默认 Y)：").strip().lower()
        if retry == 'n':
            print("已放弃。")
            return

        identifier = manual_select()
        retry_plugin = get_plugin_by_identifier(identifier)
        if not retry_plugin:
            print("❌ 插件加载失败")
            return
        print(f"\n✅ 重试用解析器：{retry_plugin.name}")
        print("\n⏳ 重新解析中...\n")
        account_info, transactions = _try_parse(retry_plugin, path, verbose)
        selected_plugin = retry_plugin

        if not transactions:
            print(f"\n❌ 重试仍然失败（{retry_plugin.name}）。请检查 PDF 格式或插件实现。")
            return

    parse_elapsed = time.time() - start_time
    print(f"✅ 成功解析 {len(transactions)} 笔交易")

    # 5. 导出
    print("📊 正在生成 Excel 报表...")
    export_start = time.time()
    export_excel(out, selected_plugin.name, account_info, transactions)
    export_elapsed = time.time() - export_start

    generate_report(out, transactions)

    total_elapsed = time.time() - start_time
    if total_elapsed < 60:
        time_str = f"{total_elapsed:.2f} 秒"
    else:
        minutes = int(total_elapsed // 60)
        seconds = total_elapsed % 60
        time_str = f"{minutes} 分 {seconds:.2f} 秒"

    print("\n" + "─" * 50)
    print("🎉 处理完成！")
    print(f"📁 输出文件：{out}")
    print(f"📊 交易笔数：{len(transactions)}")
    if '起止日期' in account_info:
        print(f"📅 交易期间：{account_info['起止日期']}")
    elif '交易时间段' in account_info:
        print(f"📅 交易期间：{account_info['交易时间段']}")
    print(f"⏱️  解析耗时：{parse_elapsed:.2f} 秒")
    print(f"⏱️  导出耗时：{export_elapsed:.2f} 秒")
    print(f"⏱️  总用时：{time_str}")
    print("─" * 50)

    input("\n按 Enter 键退出...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n❌ 程序异常：{e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 键退出...")