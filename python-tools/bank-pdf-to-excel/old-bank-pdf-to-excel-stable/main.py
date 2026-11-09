#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
银行/支付流水 PDF 智能解析工具 - 主程序 (v2.1)

增强功能：
    - 支持输出到任意目录（自动创建不存在的目录）
    - 生成 Excel 后自动解除 Windows 文件锁定（消除"来自 Internet"警告）
    - 强制垃圾回收释放文件句柄，避免资源管理器卡顿
    - 增加总耗时统计
    - 修正统计分析表中净流入的计算逻辑
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

from utils.helpers import normalize_path
from plugins import PLUGINS, get_plugin_by_identifier


def list_plugins() -> None:
    """打印所有可用的解析插件列表"""
    print("\n可用的解析插件：")
    for i, p in enumerate(PLUGINS, 1):
        print(f"  {i}. {p.name} ({p.identifier})")


def manual_select() -> str:
    """交互式手动选择插件，返回插件标识符 (identifier)"""
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
    """
    生成解析可信度报告（纯只读分析，不修改任何数据）
    目的：在不改动核心解析逻辑的前提下，给用户一个"数据是否有明显问题"的快速判断依据。
    """
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

    # 1. 关键字段空值检查
    empty_date = df['交易日期'].isna().sum() if '交易日期' in df.columns else total
    empty_amount = df['交易金额'].isna().sum() if '交易金额' in df.columns else total
    empty_date_rate = empty_date / total
    empty_amount_rate = empty_amount / total
    
    lines.append("【字段空值检查】")
    lines.append(f"  日期缺失：{empty_date} 笔（{empty_date_rate:.1%}）{' ⚠️ 异常' if empty_date_rate > 0.05 else ' ✅ 正常'}")
    lines.append(f"  金额缺失：{empty_amount} 笔（{empty_amount_rate:.1%}）{' ⚠️ 异常' if empty_amount_rate > 0.05 else ' ✅ 正常'}")
    lines.append("")

    # 2. 日期范围与异常日检测
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

    # 3. 金额极端值检测
    if '交易金额' in df.columns and len(df) > 3:
        amounts = df['交易金额'].dropna()
        if len(amounts) > 3:
            mean = amounts.mean()
            std = amounts.std()
            if std > 0:
                extreme = amounts[(amounts > mean + 3*std) | (amounts < mean - 3*std)]
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


def export_excel(output_path: str, bank_name: str, account_info: Dict, transactions: List[Dict]) -> None:
    """将解析结果导出为 Excel 文件（含四个 Sheet）"""
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 创建输出目录：{output_dir}")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        if account_info:
            df_info = pd.DataFrame(list(account_info.items()), columns=["项目", "内容"])
            df_info.to_excel(writer, sheet_name="账户信息", index=False)

        if transactions:
            df = pd.DataFrame(transactions)
            df.to_excel(writer, sheet_name="交易明细", index=False)

            # ---------- 统计分析（修正净流入计算） ----------
            if '交易方向' in df.columns:
                inc_df = df[df['交易方向'] == '收入']
                exp_df = df[df['交易方向'] == '支出']
                oth_df = df[df['交易方向'] == '其他'] if '其他' in df['交易方向'].unique() else pd.DataFrame()
                # 净流入 = 收入总额 + 支出总额（支出为负数）
                net_flow = inc_df['交易金额'].sum() + exp_df['交易金额'].sum()
                stats = {
                    "总笔数": len(df),
                    "收入笔数": len(inc_df),
                    "支出笔数": len(exp_df),
                    "其他笔数": len(oth_df),
                    "总收入": round(inc_df['交易金额'].sum(), 2) if not inc_df.empty else 0.0,
                    "总支出": round(exp_df['交易金额'].sum(), 2) if not exp_df.empty else 0.0,
                    "其他总额": round(oth_df['交易金额'].sum(), 2) if not oth_df.empty else 0.0,
                    "净流入": round(net_flow, 2),
                }
            else:
                # 如果没有交易方向，根据金额正负判断
                inc_df = df[df['交易金额'] >= 0]
                exp_df = df[df['交易金额'] < 0]
                net_flow = inc_df['交易金额'].sum() + exp_df['交易金额'].sum()  # exp_df 为负数
                stats = {
                    "总笔数": len(df),
                    "收入笔数": len(inc_df),
                    "支出笔数": len(exp_df),
                    "其他笔数": 0,
                    "总收入": round(inc_df['交易金额'].sum(), 2) if not inc_df.empty else 0.0,
                    "总支出": round(exp_df['交易金额'].sum(), 2) if not exp_df.empty else 0.0,
                    "其他总额": 0.0,
                    "净流入": round(net_flow, 2),
                }
            if '交易日期' in df.columns:
                dates = pd.to_datetime(df['交易日期'], errors='coerce')
                if not dates.isna().all():
                    stats['起始日期'] = dates.min().strftime('%Y-%m-%d')
                    stats['结束日期'] = dates.max().strftime('%Y-%m-%d')
            pd.DataFrame([stats]).to_excel(writer, sheet_name="统计分析", index=False)

        # 日志
        log = {
            "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "银行/平台": bank_name,
            "交易笔数": len(transactions),
        }
        pd.DataFrame([log]).to_excel(writer, sheet_name="日志", index=False)

    # 强制垃圾回收，释放文件句柄（防止资源管理器预览占用）
    gc.collect()

    # 尝试解除 Windows 文件锁定（消除"来自 Internet"的警告）
    try:
        subprocess.run(
            ['powershell', '-command', f'Unblock-File -Path "{output_path}"'],
            capture_output=True,
            check=False
        )
    except Exception:
        pass  # 如果 PowerShell 不可用或权限不足，忽略


def main() -> None:
    """主程序入口：解析 PDF 并导出 Excel"""
    print("=" * 60)
    print("银行/支付流水 PDF 智能解析工具 v2.1 - 插件化架构")
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
            if plugin.detect(str(path)):
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

    # 3. 确定输出路径（支持自定义目录）
    default_out = str(path.with_suffix('.xlsx'))
    print(f"\n💾 默认输出路径：{default_out}")
    print("   （您也可以输入完整路径，如 C:\\Output\\report.xlsx，目录将自动创建）")
    out = input("   请输入输出路径（直接回车使用默认）：").strip()
    if not out:
        out = default_out
    if not out.lower().endswith(('.xlsx', '.xls')):
        out += '.xlsx'

    # 4. 覆盖确认
    if os.path.exists(out):
        overwrite = input(f"⚠️ {os.path.basename(out)} 已存在，按 Enter 覆盖，输入 c 取消：").strip().lower()
        if overwrite == 'c':
            print("已取消操作")
            return

    # 5. verbose 默认改为 y
    verbose = input("🔊 显示详细信息？(y/n，默认 y)：").strip().lower() != 'n'

    # 6. 开始计时
    start_time = time.time()

    print("\n⏳ 正在解析 PDF（进度条在下方显示，请耐心等待）...\n")
    account_info, transactions = selected_plugin.parse(str(path), verbose)

    parse_elapsed = time.time() - start_time

    if not transactions:
        print("❌ 解析失败，未提取到任何交易记录。")
        return

    print(f"✅ 成功解析 {len(transactions)} 笔交易")

    # 7. 导出 Excel（单独计时）
    print("📊 正在生成 Excel 报表...")
    export_start = time.time()
    export_excel(out, selected_plugin.name, account_info, transactions)
    export_elapsed = time.time() - export_start

    # 8. 可信度报告
    generate_report(out, transactions)

    # 9. 总耗时统计
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