# 银行/支付流水 PDF 智能解析工具

> 把 PDF 流水转成结构化 Excel 的插件化工具。当前 8 家银行，v2.7。

---

## 📏 文档维护契约（每次改 README 前必读，30 行）

### 给决策者（人）

这份 README 服务三类读者，**每类只读自己那段**：
- 🧑‍💼 使用者：只关心"是什么 / 怎么用"
- 🧑‍💻 开发者：追加"架构 / 怎么用 AI 开发"
- 🤖 AI：只要"决策 / 禁止 / 完成标准"

**改文档前先问自己 3 个问题**：
1. 我改的是哪一段？读者是谁？
2. 新增这条，是读者**需要**，还是我**觉得他们需要**？
3. 如果给 AI 加"更多解释" → 停下来。AI 不需要解释，需要**禁止**。

**最常犯的错**：以为"更多信息 = AI 更好工作"。**事实相反**——AI 段每多 100 行解释，AI 就多 100 行"跳读风险"。

### 给 AI 助手

如果你被要求"优化 README"或"补充文档"，遵守：

- ❌ **不要给 AI 段增加解释性文字**（AI 不需要"为什么"）
- ❌ **不要给用户段增加技术细节**（用户不需要"怎么实现"）
- ❌ **不要新增章节**，除非能一句话说清"解决哪个具体问题"
- ❌ **不要用"更完整"、"更专业"、"更清晰"作为理由扩充**
- ✅ **新增前必答**："这条会让 AI 更容易执行，还是更难？"
- ✅ **铁律只增不减**（除非有真实反例证明它不再适用）
- ✅ **行数上限 1500**，超了外挂到 docs/，不扩充 README

**如果用户明确要求扩充**：先提醒用户看这份契约，不要直接执行。

### 契约本身的更新规则

- 这份契约**极简**（不超过 30 行），**不要扩充它**
- 修改这份契约需要**明确的反例**（比如"某次 AI 因为缺少某条规则犯了错"）
- **不要因为"觉得契约不够完整"而修改**——那是它要防止的东西

---

## 📖 你是哪类读者？

| 你是谁 | 读哪一段 | 时间 |
|--------|---------|------|
| 🧑‍💼 **使用者**（只想跑工具） | [第一部分：怎么用](#第一部分用户怎么用) | 5 分钟 |
| 🧑‍💻 **开发者**（想加插件/改代码） | [第二部分：怎么开发和维护](#第二部分开发者怎么开发和维护) | 30 分钟 |
| 🤖 **AI 助手**（新对话要干活） | [第三部分：AI 执行入口](#第三部分ai-执行入口) | 30 秒定位 |

> 💡 **不读全文**：每段自包含，读者只读自己那段，不需要"通读"。

---

# 第一部分：用户怎么用

## 1.1 这是什么

**把银行/支付平台的 PDF 流水文件，转换为结构化、可分析、可归档的 Excel 表格。**

**输入**：一份 PDF 流水（从网银下载的月账单、对账单）

**输出**：一个 Excel，包含 3 个 Sheet：
- **账户信息**：户名、账号、起止日期 + 交易汇总（笔数/收支/净流入/期初/期末余额）
- **交易明细**：每笔交易的日期、金额、余额、对手、分类（含边框、冻结首行、筛选、千分位）
- **日志**：处理时间、银行名称、交易笔数

## 1.2 解决什么问题

**3 个真实场景**：

1. **月报核对**：每月下载 5~10 家银行的流水，人工录入 Excel 要 2 小时 → 用工具 10 分钟搞定
2. **对账**：把银行流水和公司账本对比 → 工具输出结构化数据后，Excel 里直接 VLOOKUP
3. **归档**：年度审计需要 1 年内所有流水 → 工具批量转换，自动按银行分类

## 1.3 支持哪些银行

| 银行/平台 | 支持状态 |
|-----------|---------|
| 农业银行 | ✅ 生产稳定 |
| 招商银行 | ✅ 生产稳定 |
| 交通银行 | ✅ 生产稳定 |
| 建设银行 | ✅ 生产稳定 |
| 赣州银行 | ✅ 生产稳定 |
| 微信支付 | ✅ 生产稳定 |
| 支付宝 | ✅ 生产稳定 |
| 其他银行 | ⚠️ 通用兜底（可能字段错位，需人工核对） |

**你的银行不在列表里？** 找开发者按 [第二部分](#第二部分开发者怎么开发和维护) 加插件，通常 1~2 小时能加一家。

## 1.4 环境和配置

**Python 3.8 ~ 3.11**（推荐 3.10 或 3.11）

```bash
# 安装依赖
pip install pdfplumber pandas openpyxl numpy scikit-learn tqdm pypdf

# 验证
python main.py
```

**可选依赖**（微信支付 OCR 降级用）：
```bash
pip install pytesseract pdf2image
# 并安装 Tesseract OCR 引擎：
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS:   brew install tesseract
# Linux:   sudo apt install tesseract-ocr
```

## 1.5 快速开始（单个文件）

```bash
python main.py
```

按提示操作：

```
📂 请输入 PDF 文件路径（支持拖拽）：D:\流水\农业银行.pdf
   → 从文件管理器拖到终端即可，路径支持 Git Bash 的 /e/... 格式

请选择解析方式：
  1. 自动检测（推荐）
  2. 手动指定格式

🔍 正在自动检测格式...
  尝试 微信支付... ❌
  尝试 支付宝... ❌
  尝试 交通银行... ❌
  尝试 建设银行... ✅ 匹配

✅ 使用解析器：建设银行
💾 输出路径：D:\流水\农业银行.xlsx

🎉 处理完成！
📊 交易笔数：893
📅 交易期间：2025-10-09 至 2026-09-16
```

**如果自动检测误命中**（例如某 PDF 含"支付宝"字样被支付宝插件抢），程序会提示"是否手动重新选择插件重试"，按 Enter 后手动选正确插件即可，**不用退出重跑**。

## 1.6 批量处理（重点）

**一个月几十份流水？用批量脚本。**

```bash
# 处理整个目录
python batch.py "D:/流水/2025-10"

# 指定输出目录
python batch.py "D:/流水/2025-10" -o "D:/流水/输出"

# 只处理文件名匹配的 PDF
python batch.py "D:/流水/2025-10" -p "建设*"

# 显示详细日志（调试用）
python batch.py "D:/流水/2025-10" -v
```

**推荐的文件组织**：

```
D:/流水/
├── 2025-10/                    ← 按月归档
│   ├── 农业银行_10月.pdf
│   ├── 招商银行_10月.pdf
│   ├── 建设银行_10月.pdf
│   └── ...
└── 2025-11/
    └── ...
```

**批量输出结构**：

```
输出目录/
├── 农业银行_10月.xlsx
├── 农业银行_10月_report.txt    ← 可信度报告
├── 招商银行_10月.xlsx
├── 招商银行_10月_report.txt
├── ...
└── _batch_summary_20251016_143022.csv   ← 汇总表（哪些成功/失败）
```

**批量处理 3 个检查点**：

1. **看成功/失败比**：全成功 → 直接用 Excel；有失败 → 打开汇总 CSV 看 `error` 字段
2. **看是否有"通用兜底"**：用 `通用后备(兜底)` 解析的 PDF → 可能是新格式，建议单独拿出来给开发者
3. **看笔数是否合理**：明显偏少或偏多 → 可能解析有问题，跑一次 `*_report.txt` 看可信度

## 1.7 常见问题（用户向）

**Q1：解析不准怎么办？**
- 看 `*_report.txt` 有没有 ⚠️ 标记
- 对比 PDF 首尾的"总笔数 / 总支出"与 Excel 的"账户信息" Sheet 的交易汇总
- 不对的话，把 PDF 发给开发者，可能需要为新格式加插件

**Q2：输出 Excel 里某列是空的？**
- 不同银行的字段不同（如农业银行有"交易渠道"，建行没有）
- **pandas 会自动按列并集对齐**，空列属正常现象
- 字段说明见 [6.3 特色字段](#63-特色字段各插件差异)

**Q3：同名输出文件冲突？**
- `batch.py` 检测到同名文件时会**自动加时间戳**（如 `农业银行_143022.xlsx`），不会覆盖

**Q4：批量处理中某个 PDF 失败，会影响其它吗？**
- **不会**。单个失败会记录到汇总 CSV 的 `error` 字段，其它文件继续处理

**Q5：能处理扫描件/图片 PDF 吗？**
- 微信支付插件支持 OCR 降级（需安装 Tesseract）
- 其他银行暂不支持，遇到扫描件请先用其他工具 OCR 成文字版

**更多问题**：见项目根目录 `docs/faq-archive.md`

---

# 第二部分：开发者怎么开发和维护

## 2.1 项目架构

### 目录结构

```
bank-pdf-to-excel/
├── main.py              # 单文件交互式入口
├── batch.py             # 批量处理入口
├── probe.py             # PDF 结构探测脚本（新增插件前必跑）
│
├── plugins/             # 插件目录（每家银行一个文件）
│   ├── __init__.py      # 插件注册中心
│   ├── base.py          # StatementPlugin 抽象基类
│   ├── nongye.py        # 农业银行
│   ├── zhaoshang.py     # 招商银行
│   ├── jiaotong.py      # 交通银行
│   ├── ccb.py           # 建设银行
│   ├── ganzhou.py       # 赣州银行
│   ├── wechat.py        # 微信支付
│   ├── alipay.py        # 支付宝
│   └── universal.py     # 通用兜底
│
├── utils/               # 公共工具
│   ├── helpers.py       # 文本清洗、数值转换、路径规范化
│   └── parser_common.py # BasePDFParser 基类 + CoordinateEngine
│
├── docs/
│   ├── plugins/         # 每银行一份档案（加同类时读）
│   └── templates/       # 5 个插件模板（可直接 cp）
│
└── CHANGELOG.md         # 版本历史
```

### 数据流

```
用户输入 PDF 路径
    ↓
main.py / batch.py 加载 PLUGINS 列表
    ↓
对每个 PDF：循环 PLUGINS 调 detect(pdf_path)，命中即停
    ↓
命中插件 → parse() → (account_info, transactions)
    ↓
pandas DataFrame → Excel 3 个 Sheet（含样式）
    ↓
可信度报告（txt）+ 批量汇总（csv，仅批量模式）
```

### 关键文件职责

| 文件 | 职责 | 何时修改 |
|------|------|---------|
| `main.py` | 单文件交互式入口 | 仅在改交互流程或 Excel 样式时 |
| `batch.py` | 批量处理入口 | 仅在改批量逻辑时 |
| `probe.py` | PDF 结构探测 | 仅在加探测规则时 |
| `plugins/__init__.py` | 插件注册与优先级 | **每次新增插件都要改** |
| `plugins/base.py` | 插件接口定义 | 只在改接口时（几乎不动） |
| `plugins/xxx.py` | 单银行解析逻辑 | **新增银行时新建** |
| `utils/parser_common.py` | 基类 + 坐标引擎 | 只在改基础能力时（很少动） |
| `utils/helpers.py` | 文本清洗、数值转换 | 只在改基础工具时（很少动） |
| `docs/plugins/xxx.md` | 单银行档案 | **新增银行时新建** |

## 2.2 核心接口

**所有插件必须继承 `StatementPlugin`，实现 4 个方法**：

```python
from .base import StatementPlugin

class XXXPlugin(StatementPlugin):
    @property
    def name(self) -> str:
        """返回插件显示名称（如"建设银行"）"""
        return "XXX银行"

    @property
    def identifier(self) -> str:
        """返回唯一标识符（如"ccb"），用于命令行选择"""
        return "xxx"

    def detect(self, pdf_path: str) -> bool:
        """自动检测 PDF 是否属于本插件支持格式（必须严格，见 AI 段禁止 3）"""
        ...

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict, List[Dict]]:
        """执行解析，返回 (account_info, transactions)"""
        ...
```

**基类 `BasePDFParser` 提供的通用工具**（继承后直接用）：

| 方法 | 用途 |
|------|------|
| `load_pdf(pdf_path)` | 加载 PDF，填充 `self.raw_text` |
| `extract_tables(pdf_path)` | 提取所有表格，返回三维列表 |
| `parse_date(date_str)` | 统一日期解析，返回 (YYYY-MM-DD, 星期英文) |
| `classify_transaction(summary, counterparty, amount)` | 标准交易分类 |
| `get_cell_safe(row, idx, default='')` | 安全取单元格 |

## 2.3 用 AI 加插件的 SOP（推荐）

**这是 AI 时代最重要的开发流程。**

### Step 1：跑 probe.py 摸清 PDF 结构（2 分钟）

```bash
python probe.py "你的银行.pdf"
```

输出 6 段报告：
- 【1】文本层检查（判断是否扫描件）
- 【2】`extract_tables()` 测试（判断是否表格）
- 【3】表头词及 x0 坐标（判断是否流式文本）
- 【4】数据区跨行检查（判断逐行 vs 锚点）
- 【5】完整 `extract_words`（需 `--full`，定位字段错位）
- 【6】原始文本（前 2 页）

**路径含空格时加引号**，Git Bash 拖拽的 `/d/...` 格式会自动规范化。

### Step 2：开 AI 对话（用这个开场白）

```
这是我的银行流水解析项目（附件：README.md、plugins/、utils/、probe.py）。
我要新增 [XX银行] 插件。以下是 probe.py 的探测输出：

【1】
（粘贴）
【2】
（粘贴）
【3】
（粘贴）
【4】
（粘贴）

请按 README 第三部分 AI 执行入口执行。
```

**注意**：不要因为"我知道 AI 很聪明"就省略 probe 输出。**没有 probe = 没有策略判断依据 = AI 会停下来要**。

### Step 3：验收 AI 的产出（5 分钟）

AI 完成后，逐项检查：

- [ ] `plugins/xxx.py` 存在，能 import 成功
- [ ] `docs/plugins/xxx.md` 存在，**内容不传播错误做法**（如"对金额取绝对值"）
- [ ] `CHANGELOG.md` 有新条目
- [ ] 用样例 PDF 跑一次，**笔数/总支出/净流入三项与 PDF 汇总一致**
- [ ] 余额连续性校验 **0 断点**
- [ ] **手动抽查 3 笔支出，`交易金额` 为负数**（不是 `abs` 后的正数）

**如果 AI 报告"未验证"**（这是好事）——你自己跑一次验证，不要催它"报完成"。

### Step 4：如果 AI 漏了步骤

**不要自己补，让 AI 补**——这是训练 AI 协作的过程。

## 2.4 手动加插件（不用 AI）

**如果你更习惯手动，按这个流程：**

### Step 1：判断策略（参考 probe 输出）

```
probe【1】文本 < 30 字符？
├─ 是 → OCR 模板
└─ 否 ↓
probe【2】extract_tables 有结果？
├─ 是 → 表格提取模板
│       ├─ 表头含"借方/贷方" → 借贷双列
│       └─ 表头含"金额"单列 → 单列带符号
└─ 否 ↓
probe【3】表头 ≥4 个稳定列？
├─ 否 → 行文本正则模板
└─ 是 ↓
probe【4】行间距稳定 10~25？
├─ 否 → 锚点模板
└─ 是 → 看【5】单笔 top 极差
        ├─ > 8 → 锚点模板
        └─ ≤ 8 → 逐行模板
```

### Step 2：复制模板

```bash
cp docs/templates/plugin-{策略}.py plugins/{拼音}.py
```

改 3 处：
1. `class XXXPlugin` → `class {拼音}Plugin`
2. `name` → `"{银行名}"`
3. `identifier` → `"{拼音}"`（参考已有惯例，如建行是 `ccb`）

### Step 3：改 detect 和 parse

参考 `docs/plugins/` 下同类插件的档案。

### Step 4：注册

```python
# plugins/__init__.py
from .{拼音} import {拼音}Plugin
PLUGINS = [..., {拼音}Plugin(), UniversalPlugin()]
```

## 2.5 调试与验证

### 单文件调试

```bash
python batch.py "你的.pdf" -v    # 加 -v 看详细日志
```

### 余额连续性校验

```python
import openpyxl
wb = openpyxl.load_workbook("xxx.xlsx", data_only=True)
rows = list(wb["交易明细"].iter_rows(min_row=2, values_only=True))
print(f"📊 读到 {len(rows)} 行")
prev = None
for r in rows:
    date, _, summary, _, amount, balance, *_ = r
    if balance is None or amount is None:
        prev = None; continue
    if prev is not None and abs(round(prev + float(amount) - float(balance), 2)) > 0.01:
        print(f"⚠️ {date} {summary} 断点")
    prev = float(balance)
```

**任何断点 = 有交易被丢或被错算。** 这是"总收入/总支出与 PDF 汇总不符"的最快定位方法。

### 3 个回归校验点

1. **笔数**：与 PDF 首尾的"总笔数"对比
2. **金额合计**：与 PDF 末尾的"累计借方/贷方发生额"对比
3. **余额连续性**：0 断点

## 2.6 扩展点在哪

| 想加什么 | 改哪里 |
|---------|--------|
| 新银行插件 | `plugins/` 新建 + `plugins/__init__.py` 注册 |
| 新字段 | `plugins/xxx.py` 的 `parse()` 返回字典里加 key（pandas 自动对齐） |
| 新交易分类 | `utils/parser_common.py` 的 `classify_transaction()` |
| 新输出 Sheet | `main.py` 的 `_write_xxx_sheet()` |
| 合并多 Excel | `batch.py` 加 `--merge` 参数（未来扩展） |
| 新探测规则 | `probe.py` 加新的判定段落 |

---

# 第三部分：AI 执行入口

> ⚠️ **阅读契约**：
> 1. 先读完 3.2 铁律再往下（不要跳）
> 2. 3.5 完成标准是收尾时必须逐项对照的（不是可选）
> 3. 如果上下文很长，重读 3.1 和 3.2

## 3.1 任务路由

| 用户说…… | 前置条件 | 读 | 做 |
|-----------|---------|-----|-----|
| "加 XX 银行插件" | **必须有实际 probe 输出（【1】~【4】段）** | 3.2 → 3.3 → 3.6 | 按 3.3 决策树 |
| "XX 插件坏了" | — | 3.2 → 3.4 | 按 3.4 决策树 |
| "XX 银行出现新格式" | **必须有实际 probe 输出** | 3.2 → 3.4 | 按 3.4 的"同银行多格式"分支 |
| "加个功能" | — | 3.2 → 3.4 | 按需求分析 |

> 🔴 **前置条件不满足时的行为**：
> - 如果用户没给 probe 输出 → **停在第一步，回复"需要 probe.py 输出，无法判断策略"**
> - 如果用户说"你直接写" → **拒绝，说明"无 probe = 无策略判断依据"**
> - 不要用 3.6 档案索引里的"probe 信号"作为决策依据（那是描述，不是事实）
> - 不要用"我知道 XX 银行是什么格式"作为依据（那是猜，不是事实）

## 3.2 🔴 铁律（违反 = 代码错误）

### 🔴 禁止 1：按内容指纹做任何"重复判断"（不只是去重）

**红线定义**：任何"按交易内容字段（日期/摘要/金额/余额/对手）判断是否重复"的代码，都禁止。**无论它叫 `_deduplicate` / `_filter_dups` / `_warn_same_key` / `_report_dups`，无论它是"合并"还是"只打印"，无论它是"主逻辑"还是"辅助诊断"**。

**为什么这么严**：
1. **银行流水天然存在多字段全同的合法独立交易**——这是常态，不是异常
2. **"只打印不合并"是变通的入口**——今天 `print`，明天有人改成 `--merge`，后天就是 7,920 事故
3. **"按内容指纹分组"本身就是错误模型**——因为正确的完整性判据是余额连续性，不是内容

**以下合理化借口全部禁止**：

- ❌ "这次 PDF 看起来有重复" → 不要判断，直接不写
- ❌ "我只打印，不合并，不改数据" → 打印重复提醒也是按内容指纹做判断
- ❌ "我不叫 `_deduplicate`，叫 `_warn_same_key`" → 换名字也不行
- ❌ "我是为了保险起见加一层诊断" → 保险做法是余额连续性校验，不是内容指纹
- ❌ "我只在开发/调试时用" → 调试辅助也是代码，也会被后续维护者"正式化"
- ❌ "我加个 `--dry-run` 参数，默认关闭" → 参数开关也是代码，开关会被打开
- ❌ "我加了但用户可以选择不用" → 提供了这个能力就是埋了雷
- ❌ "我读'后果'判断这次能不能例外" → 后果不是让你判断例外的依据

**正确的替代方案**：

| 你的目的 | ❌ 错误做法 | ✅ 正确做法 |
|---------|------------|------------|
| 防止重复解析 | 按内容指纹去重 | 三级降级**互斥执行**（`if len < 1` 分支天然不重复） |
| 防止多页重复表头 | 按内容指纹去重 | **序号列非数字跳过**（这是过滤，不是去重） |
| 发现漏读 | 按内容指纹"疑似重复提醒" | **余额连续性校验**（用余额判据，不用内容指纹） |
| 开发/调试期"看一眼同指纹" | 加代码到插件 | **独立脚本，不进入插件**（`tools/xxx.py`，代码与解析隔离） |

**后果（仅供了解，不是例外依据）**：建行 2026-11 差 7,920 元；农行 nongye.py 长期存在同日多笔"短信费 -2"被误杀。

**如果发现自己在写"看起来合理"的重复判断逻辑，先停手，问自己**：
1. 这段代码是否在**按内容字段判断"是否重复"**？
2. 如果删除它，功能是否仍然完整？（完整性用余额校验，不需要内容指纹）
3. 它的存在是不是"为了保险起见"？（保险不能靠内容指纹）

**任何一题答"是"，都不要写。**

### 禁止 2：金额必须 `round(2)`

- ❌ 不要在比较金额时用浮点数原值
- ✅ 比较前统一 `round(float(x), 2)`

### 禁止 3：`detect` 必须严格

- ❌ 不要写 `if "银行" in text`
- 🔴 **不要用 `or` 连一个宽泛条件**：

  ```python
  # ❌ 反模式：or 后面的宽泛条件让前面的严格条件形同虚设
  return "完整标题" in text or "银行名" in text
  # ✅ 正确：两个特征词 and 同时命中
  return "标题关键词1" in text and "标题关键词2" in text
  ```

- ✅ 写两个特征词同时命中（如 `"赣州银行" in text and "历史交易" in text`）
- ✅ 特征词必须从**实际 probe【6】前 2 行**里找，不能从文档描述里猜
- ✅ 上线前对**所有已有 PDF** 跑一遍，必须全部 False（除了自己）

**历史案例**：2026-11 `alipay.py` 用 `or "支付宝"` 导致赣州 PDF 被误命中；`nongye.py` 用 `or "农业银行"` 有同类隐患（已修复）。

### 禁止 4：字段名用标准名，且字段值语义不能错

- ✅ 字段名标准：`交易日期` / `星期` / `摘要` / `交易方向` / `交易金额` / `对手信息` / `交易分类` / `账户余额`
- ❌ 不要用 `交易摘要` / `本次余额`（这是 nongye.py 的历史遗留）
- ❌ 星期用**英文**（`Monday` / `Thursday`），不是中文
- 🔴 **`交易金额` 必须带符号**（正=收入，负=支出），**禁止 `abs()` / `abs(amount)` / `-abs(...)`**
- 不要用"`交易方向` 字段已经表达了正负"作为用 `abs()` 的理由——`交易方向` 是给用户看的辅助字段，`交易金额` 的符号是给 `main.py` 统计用的，**两者不能互相替代**
- 原因：`main.py` 的 Excel 输出按金额符号统计总支出/净流入，用 `abs` 会让统计全错（静默错误，看不出但实际错）

### 禁止 5：单笔跨行 = 必须锚点法

- ❌ 单笔字段跨行时不要用逐行解析
- ✅ **仅当【2】无表格（`extract_tables()` 返回空）时才适用本条**
- ✅ **【2】命中表格提取时，铁律 5 不适用**（`extract_tables()` 已自动处理单元格内换行）
- 判断：`probe.py --full` 看【5】段，单笔 top 极差 > 8 就是跨行
- 参考：`docs/plugins/ganzhou.md`

## 3.3 加插件决策树

> 🔴 **前置检查（在判断策略之前必须先做）**：
>
> 1. 回复里是否有"实际 probe 输出（【1】~【4】段）"？
>    - ✅ 有 → 进入 Step 1 决策树
>    - ❌ 没有 → **停止，明确回复"需要 probe.py 输出，无法判断策略"**
> 2. 不要用 3.6 档案索引里的"probe 信号"作为决策依据（那是描述，不是事实）
> 3. 不要用"这个银行我知道是什么格式"作为依据（那是猜，不是事实）
> 4. 如果用户说"你直接写" → 拒绝，说明"无 probe = 无策略判断依据"
>
> **前置检查不过 = 不许进入 Step 1。**

### Step 1：判断策略（按顺序，命中即停）

```
probe【1】文本 < 30 字符？
├─ 是 → 策略=OCR，模板=plugin-ocr.py
└─ 否 ↓
probe【2】extract_tables 有结果？
├─ 是 → 表格提取（铁律 5 不适用）
│       ├─ 表头含"借方/贷方" → 模板=plugin-table（借贷双列）
│       └─ 表头含"金额"单列 → 模板=plugin-table（单列带符号）
└─ 否 ↓
probe【3】表头 ≥4 个稳定列（x0 差 < 20）？
├─ 否 → 行文本正则，模板=plugin-text.py
└─ 是 ↓
probe【4】行间距稳定 10~25？
├─ 否 → 锚点法，模板=plugin-anchor.py
└─ 是 → 看【5】单笔 top 极差
        ├─ > 8 → 锚点法
        └─ ≤ 8 → 逐行，模板=plugin-coord.py
```

**判断完立刻在回复里写**：`策略 = X，模板 = Y`。不要沉默。

### Step 2：最小骨架（模板拿不到时用这段）

```python
# -*- coding: utf-8 -*-
import re
from datetime import datetime
from typing import Dict, List, Tuple

import pdfplumber

from .base import StatementPlugin
from utils.helpers import clean_text, safe_float


class XXXPlugin(StatementPlugin):
    @property
    def name(self) -> str:
        return "XXX银行"        # ← 改这里

    @property
    def identifier(self) -> str:
        return "xxx"            # ← 改这里（参考 __init__.py 已有惯例，见下表）

    def detect(self, pdf_path: str) -> bool:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages[:2])
        except Exception:
            return False
        # 两个特征词同时命中（见铁律 3）
        return "XXX银行" in text and "特征词" in text

    def parse(self, pdf_path: str, verbose: bool = False) -> Tuple[Dict[str, str], List[Dict]]:
        account_info = {}
        transactions = []
        # 核心解析逻辑
        return account_info, transactions
```

**⚠️ 关键**：
- 必须继承 `StatementPlugin`（不是 `BasePlugin`，这个类不存在）
- 必须实现 `parse()` 方法（不是 `_parse_transactions()`，后者只是自定义内部方法）
- `identifier` 参考下表，不要自己编

**identifier 命名约定**：

| 银行 | identifier |
|------|-----------|
| 农业银行 | `nongye` |
| 招商银行 | `zhaoshang` |
| 交通银行 | `jiaotong` |
| 建设银行 | `ccb` |
| 赣州银行 | `ganzhou` |
| 微信支付 | `wechat` |
| 支付宝 | `alipay` |

### Step 3：改 detect

特征词从**实际 probe【6】前 2 行**里找独特词，必须 2 个同时命中。

**⚠️ 如果没拿到 probe【6】** → 停下来要 probe，不要猜特征词。

### Step 4：改 `parse()`

按策略参考对应 `docs/plugins/xxx.md`。

### Step 5：注册

```python
# plugins/__init__.py
from .{拼音} import {拼音}Plugin
PLUGINS = [..., {拼音}Plugin(), UniversalPlugin()]
```

## 3.4 修 bug 决策树

```
用户症状是什么？
├─ 笔数不对 → 读 Q1（见 docs/faq-archive.md）
├─ 金额汇总不对 → 跑余额连续性校验（见 3.5）
├─ 对手信息为空 → 读 docs/plugins/xxx.md 的"已知坑"
├─ 字段错位 → probe --full 看【5】段
├─ 交易方向/分类列为空 → 检查 parse() 返回是否遗漏字段
└─ 程序报错 → 看 traceback，读 3.2 铁律
```

**同银行多格式分支**：README 描述特征与 probe 不符时：
1. 跑现有插件 → 能跑 = 修复；不能跑 = 新建 `xxx_v2.py`
2. v2 放 PLUGINS 里 v1 前面
3. `detect` 严格互斥

## 3.5 完成标准（漏一条 = 没做完）

**每次任务结束，逐项打勾：**

- [ ] `plugins/xxx.py` 存在，class/name/identifier 已改，**且继承 `StatementPlugin`、实现了 `parse()`**
- [ ] `docs/plugins/xxx.md` 存在，**且内容不传播错误做法**（如"对金额取绝对值"、"用 abs 处理符号"）
- [ ] `CHANGELOG.md` 有新条目（含原因/影响）
- [ ] 用样例 PDF 跑一次，笔数/总支出/净流入三项与 PDF 汇总一致
- [ ] 余额连续性校验 0 断点
- [ ] `交易金额` 字段带符号：**手动抽查 3 笔支出，金额为负数**（不是 `abs` 后的正数）

**6 项全 ✅ 才算完成。任一 ❌ 不要报告"完成"，先补。**

### 余额连续性校验脚本

```python
import openpyxl
wb = openpyxl.load_workbook("xxx.xlsx", data_only=True)
rows = list(wb["交易明细"].iter_rows(min_row=2, values_only=True))
print(f"📊 读到 {len(rows)} 行")
prev = None
for r in rows:
    date, _, summary, _, amount, balance, *_ = r
    if balance is None or amount is None:
        prev = None; continue
    if prev is not None and abs(round(prev + float(amount) - float(balance), 2)) > 0.01:
        print(f"⚠️ {date} {summary} 断点")
    prev = float(balance)
```

### 写代码前的强制自报（升级版）

写代码前，在回复里写：

```
本次任务自报：
【前置条件检查】
0. 我拿到了实际 probe 输出吗？：是/否（否 → 停止，要 probe）
   如果是，probe 的关键信号：
   - 【1】文本长度：___
   - 【2】extract_tables：有/无
   - 【4】行间距：___
   - 【5】单笔跨行：是/否

【任务执行】
1. 相关铁律：禁止 X、禁止 Y
2. 打算复制的模板：docs/templates/plugin-XXX.py（或"用 3.3 最小骨架"）
3. 要改的 3 处：class / name / identifier
4. 预期产出：plugins/xx.py、docs/plugins/xx.md、CHANGELOG.md
```

**自报第 0 项是"否" = 不许动手。**
**没自报 = 不许动手。**

## 3.6 插件档案索引

> ⚠️ **此处是"信号 → 档案"的匹配表，不是"某银行 → 某种格式"的事实表。**
>
> 只有**实际 probe 输出**命中"信号"列时，才去读对应档案。**不要因为"XX 银行有档案"就认为"XX 银行就是这种格式"**。

| **实际 probe 里的信号**（不是档案里的描述） | 读这份 | 用于 |
|-----------|--------|------|
| 【2】7 列表 + 表头"借方/贷方" | `docs/plugins/jiaotong.md` | 借贷双列模板 |
| 【2】7 列表 + 表头"金额"单列 | `docs/plugins/ccb.md` | 单列带符号模板 |
| 【2】空 + 【4】行间距稳定 + 不跨行 | `docs/plugins/nongye.md` | 逐行模板 |
| 【2】空 + 【4】行间距稳定 + 跨行 | `docs/plugins/ganzhou.md` | 锚点模板 |
| 【2】空 + 【3】列数 < 4 | `docs/plugins/zhaoshang.md` | 正则模板 |
| 【1】文本 < 30 字符 | `docs/plugins/wechat.md` | OCR 模板 |
| 用户提供 PDF 含"支付宝支付科技有限公司交易流水证明" | `docs/plugins/alipay.md` | 支付宝模板 |

## 3.7 已知坑

### 坑 1：建行去重事故（2026-11）

**看起来合理的错**：
```python
key = (date, summary, amount)  # "看起来安全"
```

**为什么错**：建行 499/501 两笔 -320，date/summary/amount/balance/counterparty **5 字段全同**，是合法独立交易。

**正确**：见 3.2 禁止 1。

### 坑 2：probe 行间距报 4.0

**看起来合理的错**：以为"要锚点法"。

**真相**：旧版 probe 把行内 0.3 像素差当行间距。**v1.1 修了**，报的是 20.0（真值）。

**正确**：看 probe v1.1 的输出，报 10~25 就是逐行。

### 坑 3：表头"收支类型"被拆两行

**看起来合理的错**：想办法拼接表头。

**正确**：只匹配主词"收支类"，残字"型"放进 `HEADER_TEXTS` 忽略。

### 坑 4：表格提取时仍被铁律 5 误导

**症状**：probe【2】有表格，但 AI 看到【5】单笔跨行，误判为"必须锚点法"。

**正确**：**【2】命中时铁律 5 不适用**（`extract_tables()` 已自动处理单元格内换行）。

### 坑 5：`identifier` 自己编

**症状**：AI 写了 `identifier = "jianshe"`，但项目惯例是 `ccb`。

**正确**：参考 3.3 的"identifier 命名约定表"，不要自己编。

### 坑 6：跳过 probe 直接写码（2026-11 R4 事故）

**症状**：AI 说"按 3.6 档案索引，建行应该是表格提取"，然后直接写代码，不跑 probe。

**为什么错**：
- 3.6 是"信号 → 档案"的匹配表，**不是"某银行 → 某种格式"的事实表**
- "XX 银行有档案" 不代表 "XX 银行就是这种格式"
- 没有实际 probe = 没有策略判断依据

**正确**：
- 3.1 / 3.3 已明确"前置条件：必须有实际 probe 输出"
- 自报第 0 项必须填"我拿到了实际 probe 输出吗？"
- 没有 probe → 停下来要，不写码

### 坑 7：`abs()` 破坏金额符号，且**被写进文档**（2026-11 R4 事故）

**看起来合理的错**：
```python
direction = "支出" if amt < 0 else "收入"
"交易金额": round(abs(amt), 2),  # "方向字段已经表达了，金额绝对值就行"
```

**为什么错**：`main.py` 的 Excel 输出按金额**符号**统计：
- `总支出` = 支出笔金额之和 → 用 `abs` 后变**正数**（应为负数）
- `净流入` = 收入 + 支出 → 支出是正数，净流入**严重虚高**

**更严重的传播**：AI 把错误做法写进了 `docs/plugins/ccb.md`：
> "字段映射：交易金额取 `round(abs(x), 2)`"
> "已知坑：先判断方向，再对金额取绝对值"

**这会让下一个 AI 读 ccb.md 时继续错。**

**正确**：
```python
direction = "支出" if amt < 0 else "收入"
"交易金额": round(amt, 2),  # 保留原始符号
```

**同时，docs/plugins/xxx.md 里写**："交易金额 = `round(float(x), 2)`，**保留原始符号（支出为负）**"

**如果发现自己在用 `abs()`，或在文档里写"对金额取绝对值"** → 立刻停手，这是 R4 事故的复发。

### 坑 8：`detect` 用 `or` 连宽泛条件（2026-11 alipay 事故）

**看起来合理的错**：
```python
return "支付宝支付科技有限公司 交易流水证明" in text or "支付宝" in text
#                                                    ↑↑↑↑↑↑↑↑↑↑
#                                    这个 or 让前面的严格条件形同虚设
```

**为什么错**：`or` 后面跟一个宽泛条件，会把 `or` 前面的严格性**完全抵消**。任何含"支付宝"字样的 PDF（比如赣州流水里的"支付宝信贷业务"）都会被误命中。

**正确**：
```python
# 两个特征词 and 同时命中
return "支付宝" in text and "交易流水证明" in text and "兹证明" in text
```

**历史案例**：2026-11 `alipay.py` 用 `or "支付宝"` 导致赣州 PDF 被误命中，最终解析失败；`nongye.py` 用 `or "农业银行"` 有同类隐患（已修复）。

**如果发现自己在写 `or` 连接两个检测条件** → 停下来，改成 `and`。

---

# 附录：速查表

## A. 使用速查

```bash
# 单文件
python main.py

# 批量
python batch.py "D:/流水/2025-10" -o "D:/流水/输出"
python batch.py "D:/流水/2025-10" -p "建设*" -v

# 探测 PDF 结构
python probe.py "D:/流水/新银行.pdf"
python probe.py "D:/流水/新银行.pdf" --full
```

## B. 输出字段速查

**必填**：`交易日期`、`星期`、`摘要`、`交易方向`、`交易金额`、`对手信息`、`交易分类`
**可选**：`账户余额`、`交易时间`
**特色**：由插件自定义（pandas 自动对齐）

## C. AI 协作速查

**最小启动包**：README.md + `plugins/`（全部）+ `utils/`（全部）+ `probe.py`
**新增插件额外**：`probe.py` 输出（【1】~【4】段完整，必要时加 `--full`）
**修 bug 额外**：出错 PDF 片段 + 期望/实际输出 + 报错信息 + `probe.py --full` 的【5】段 + 余额连续性校验结果

## D. 版本记录

当前版本：**v2.7**（详见 [CHANGELOG.md](CHANGELOG.md)）

---

## 许可证

本项目仅供个人学习和内部使用。使用时请遵守相关银行/支付平台的用户协议。

---

*最后更新：2026年11月*
*文档版本：v2.7*
*文档预算：≤ 1500 行（当前 ~950 行）*