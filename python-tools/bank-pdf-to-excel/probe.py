# -*- coding: utf-8 -*-
"""
PDF 结构探测器 (v1.1)

用途：
    - 新增银行插件前，快速摸清 PDF 结构，判断该用哪种解析策略
    - 输出结构化摘要，可直接复制粘贴给 AI 对话

用法：
    python probe.py "path/to/流水.pdf"
    python probe.py "path/to/流水.pdf" --full    # 输出完整 extract_words

v1.1 改动：
    - 内嵌 normalize_path，兼容 Git Bash 拖拽的 /d/... 路径
    - 支持 Windows 原生路径、正斜杠、反斜杠混合
    - 多参数（路径含空格忘记加引号）时给出明确提示
"""

import sys
import re
import argparse
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("❌ 请先安装 pdfplumber: pip install pdfplumber")
    sys.exit(1)


def normalize_path(input_str: str) -> Path:
    """
    将各种来源的路径字符串规范化为 Path 对象。
    支持：
        - Git Bash 拖拽路径（如 "/d/流水/file.pdf" → "D:/流水/file.pdf"）
        - Windows 路径（"D:\\流水\\file.pdf" 或 "D:/流水/file.pdf"）
        - 被 shell 引号包裹的路径（首尾单/双引号自动去除）
        - 混合斜杠（统一转为正斜杠）
    """
    path_str = input_str.strip().strip('"\'')
    path_str = path_str.replace('\\', '/')

    # Git Bash 风格 /x/... → X:/...
    match = re.match(r'^/([a-zA-Z])/(.*)$', path_str)
    if match:
        drive = match.group(1).upper()
        rest = match.group(2)
        path_str = f"{drive}:/{rest}"
    # Windows 盘符无斜杠 C:Users → C:/Users
    elif len(path_str) > 1 and path_str[1] == ':' and not path_str[2:].startswith('/'):
        path_str = path_str[:2] + '/' + path_str[2:]

    return Path(path_str)


def probe(pdf_path: str, full: bool = False, sample_pages: int = 2):
    path = normalize_path(pdf_path)
    if not path.exists():
        print(f"❌ 文件不存在: {pdf_path}")
        print(f"   已尝试解析为: {path}")
        return

    print("=" * 70)
    print(f"📄 PDF 探测报告: {path.name}")
    print("=" * 70)

    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        print(f"📊 总页数: {total}\n")

        # ---------- 1. 文本层检查（判断是否扫描件） ----------
        print("-" * 70)
        print("【1】文本层检查")
        print("-" * 70)
        first_text = pdf.pages[0].extract_text() or ""
        if len(first_text.strip()) < 30:
            print(f"  ⚠️ 首页文本 < 30 字符，疑似扫描件")
            print(f"  → 策略建议：OCR（参考 wechat.py）")
        else:
            print(f"  ✅ 有文字层，首页文本 {len(first_text)} 字符")

        # ---------- 2. 表格提取测试 ----------
        print("\n" + "-" * 70)
        print("【2】extract_tables 测试（首页）")
        print("-" * 70)
        tables = pdf.pages[0].extract_tables()
        if not tables:
            print("  ❌ 无表格（extract_tables 返回空）")
            print("  → 策略建议：坐标聚类（参考 nongye.py / ganzhou.py）")
        else:
            col_counts = [len(r) for r in tables[0][:5]]
            print(f"  ✅ 提取到 {len(tables)} 个表，首表前 5 行列数: {col_counts}")
            print(f"  → 策略建议：表格提取（参考 jiaotong.py）")
            print(f"\n  首表前 3 行:")
            for r in tables[0][:3]:
                print(f"    {r}")

        # ---------- 3. 表头词 + 列边界 ----------
        print("\n" + "-" * 70)
        print("【3】表头词及 x 坐标（首页）")
        print("-" * 70)
        words = pdf.pages[0].extract_words(x_tolerance=3, y_tolerance=3)
        best_top = None
        if not words:
            print("  ❌ 无 extract_words 结果")
        else:
            header_candidates = {}
            for w in words:
                top = round(w.get('top', 0), 0)
                if 100 <= top <= 300:
                    header_candidates.setdefault(top, []).append(w)

            best_cnt = 0
            for top, ws in header_candidates.items():
                short = [w for w in ws if 2 <= len(w['text'].strip()) <= 8]
                if len(short) > best_cnt:
                    best_cnt = len(short)
                    best_top = top

            if best_top is not None and best_cnt >= 4:
                header_words = sorted(header_candidates[best_top], key=lambda w: w['x0'])
                print(f"  疑似表头行 (top≈{best_top}):")
                for w in header_words:
                    print(f"    x0={w['x0']:7.1f}  x1={w['x1']:7.1f}  text={w['text']!r}")
            else:
                print("  ⚠️ 未自动识别出表头行，请人工查看完整 extract_words（--full）")

        # ---------- 4. 数据区跨行检查 ----------
        print("\n" + "-" * 70)
        print("【4】数据区跨行检查（前 40 个词）")
        print("-" * 70)
        data_words = [w for w in words if w.get('top', 0) > (best_top or 200) + 10]
        data_words = sorted(data_words, key=lambda w: (w.get('top', 0), w.get('x0', 0)))

        if not data_words:
            print("  （未找到数据区词）")
        else:
            try:
                from sklearn.cluster import DBSCAN
                import numpy as np
                tops_arr = np.array([w['top'] for w in data_words]).reshape(-1, 1)
                labels = DBSCAN(eps=5, min_samples=1).fit(tops_arr).labels_
                row_centers = {}
                for w, lb in zip(data_words, labels):
                    row_centers.setdefault(lb, []).append(w['top'])
                centers = sorted([sum(v) / len(v) for v in row_centers.values()])
                gaps = [round(centers[i + 1] - centers[i], 1)
                        for i in range(len(centers) - 1)
                        if centers[i + 1] - centers[i] > 1]
                if gaps:
                    gaps.sort()
                    median_gap = gaps[len(gaps) // 2]
                    print(f"  识别到 {len(centers)} 个数据行，真实行间距中位数: {median_gap}")
                    print(f"  间距分布: {gaps[:5]}{'...' if len(gaps) > 5 else ''}")
                    if median_gap < 10:
                        print("  ⚠️ 行间距 < 10 → 数据混在一起，直接上锚点法")
                    elif median_gap <= 25:
                        print("  ✅ 行间距稳定 10~25 → 基础布局逐行")
                        print("     （再检查单笔是否跨行：需 probe.py --full 看【5】段）")
                    else:
                        print("  ⚠️ 行间距 > 25 → 可能有空行/跨页，人工确认")
                else:
                    print("  （无法计算行间距，可能只有 1 个数据行）")
            except Exception as e:
                print(f"  （行间距分析失败: {e}）")

            print(f"\n  前 20 个数据词（top, x0, text）:")
            for w in data_words[:20]:
                print(f"    top={w['top']:7.1f}  x0={w['x0']:7.1f}  text={w['text']!r}")

        # ---------- 5. 完整 extract_words ----------
        if full:
            print("\n" + "-" * 70)
            print("【5】完整 extract_words（首页全部）")
            print("-" * 70)
            for w in words:
                print(f"    top={w.get('top', 0):7.1f}  x0={w.get('x0', 0):7.1f}  "
                      f"x1={w.get('x1', 0):7.1f}  text={w['text']!r}")

        # ---------- 6. 原始文本 ----------
        print("\n" + "-" * 70)
        print(f"【6】extract_text 原始输出（前 {min(sample_pages, total)} 页）")
        print("-" * 70)
        for i, page in enumerate(pdf.pages[:sample_pages]):
            print(f"\n----- 第 {i + 1} 页 -----")
            print((page.extract_text() or "")[:3000])

    print("\n" + "=" * 70)
    print("📋 使用建议：")
    print("  - 把本报告【1】~【4】段完整复制给 AI，就能判断策略")
    print("  - 若需要精确到某笔交易的错位问题，加 --full 跑一次，贴【5】段")
    print("=" * 70)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="PDF 结构探测器 —— 新增银行插件前必跑",
        epilog="提示：路径含空格时请用引号包裹，例如：python probe.py \"D:/my proj/file.pdf\""
    )
    ap.add_argument("pdf", nargs="+", help="PDF 文件路径")
    ap.add_argument("--full", action="store_true", help="输出首页完整 extract_words")
    ap.add_argument("--pages", type=int, default=2, help="extract_text 展示页数（默认 2）")
    args = ap.parse_args()

    # 路径被空格拆成多个参数 → 提示用户加引号
    if len(args.pdf) > 1:
        joined = " ".join(args.pdf)
        print("⚠️ 检测到多个位置参数，路径很可能包含空格但未加引号。")
        print("   请按下面任一方式重试：")
        print(f'   方式 1（推荐）：python probe.py "{joined}"')
        print(f'   方式 2：把 PDF 挪到无空格目录后重试')
        sys.exit(1)

    probe(args.pdf[0], full=args.full, sample_pages=args.pages)