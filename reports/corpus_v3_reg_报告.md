# corpus v3 拼写规范化视图（EarlyPrint）构建报告 — r3

2026-09-14。输出目录：**`out_corpus/corpus-v3-reg-2026-09-14-r3/`**（脚本 `build_reg_view.py`，版本 reg-view-2026-09-14.4）。前两版 `corpus-v3-reg-2026-09-14/`（.2）和 `corpus-v3-reg-2026-09-14-r2/`（.3）已作废，目录内各有 `SUPERSEDED.txt`，可删除。输入：`corpus-v3-2026-09-08/` 的 `kept_nodes.csv` 与 `corpus_manifest.csv`（hash 记在 `inputs_manifest.json`）、`tcp_drama/` 源 XML、`earlyprint_download/data/xml/` 的 466 份 EarlyPrint XML（commit 与 sha256 逐文件记在 `reg_manifest.csv`）。**v3 的三个视图一字未动；模型没有跑。**

## 1. 与 r2 的区别（ChatGPT 2026-09-14 第二次复核提出）

r2 的词位跨度按单个 EarlyPrint 词位定位，而 EarlyPrint 把缩略词拆成用 `join` 相连的两个词位（`I`+`le`、`'T`+`is`、`wee`+`le`），跨度起点或终点落在中间时就截掉了一半：Ile → 'll、'Tis → is、weele → we，全库检索两类合计 12,133 行。r3 先把 `join` 相连的词位组成不可分割的词组，匹配和裁切都以词组为单位，跨度不会落在词组内部；同时增加首尾保留检查：源节点的第一个词或最后一个词在 EarlyPrint 里定位不到，整个节点不从 EarlyPrint 取，回退 v3 原文（`span_fallback` 原因 `edge_word_unmatched`），不再靠"至少 75% 的词匹配"默许丢掉首尾词。另外补了源文与 EarlyPrint 一对多、多对一的词配对（a nother / another、some body / somebody、T + is / Tis）和比较键里的 VV→W，否则这条检查会误伤很多正常行。代价是回退略多（跨度回退 951 → 1,788），配对覆盖 99.60% → 99.53%。

回归：复核给出的三个缩略词案例（A12157 第 53、121 行；A11152 第 1594 行）现为 `I'll leave a Servant to wait upon her.`、`'Tis so, you have done my passion justice Sir`、`Go drag 'em hence; this day we'll`；上一轮 8 个重复/说话者案例和 4 个补全案例保持正确；全库检索"v3 以 Ile/'Tis 开头而输出以 'll/is 开头"及句尾 weele/that's/let's 一类截断：0 行。

## 1a. 与 .2 版的区别（ChatGPT 2026-09-14 第一次复核提出）

.2 版把对齐上的 EarlyPrint 整行替换进来。EarlyPrint 有时把 TCP 的两行（或"台词 + 说话者 + 下一句"）合成一个 `<l>`，整行替换就把邻行的话重复了一遍，还把 v3 已排除的说话者标签（Pan.、1、2）带了回来；复核确认 6 篇文档 8 处。.3 版改为**词位跨度**：块级对齐之后，再把本节点自己的词逐个对到 EarlyPrint 的词，只输出这些词所在的跨度；跨度内多出的 EarlyPrint 词有限度接受（拆词、改正、补字），跨度两端多出的词只有在本节点该端本来就有整词 `<gap>`、且这些词不属于相邻节点时才接受。对不上的节点（覆盖不足 75% 或插入过多）回退 v3 原文。复核的 8 处全部消失，Othello / Monopolies 等补全保留；对全部 580 篇做"相邻两行 ≥5 词连续包含"扫描，reg 视图里新出现的 18 处全是原文本身的回声句（v3 里因拼写不同没被扫到），没有新的重复。

同时更正：词对统计改为分视图、每处理完一个源文件就落盘（.2 版的表只含最后一段进程的计数）；缺字指标改名为"配对节点内的源缺字标记数"，不再称"已补全"；字符数两边都按文件实际字符数。

## 2. 结果

| 项目 | texts_analysis_en_reg | texts_no_prologue_epilogue_reg |
|---|---:|---:|
| 文档 / 保留节点 | 580 / 955,792 | 580 / 948,986 |
| 精确 / 模糊 / 缺字补全 / 合并行 对齐 | 907,779 / 42,659 / 813 / 17 | 901,425 / 42,294 / 811 / 17 |
| 跨度定位失败回退 / 未对齐回退 | 1,788 / 2,736 | 1,773 / 2,666 |
| **配对覆盖（节点 / 字符）** | **99.53% / 99.51%** | 99.53% / 99.52% |
| 词位 / 有 reg / 已套用 | 8,685,320 / 1,663,458 / **1,653,784（19.0%）** | 8,620,247 / 1,650,750 / 1,641,121 |
| 拒绝：垃圾 reg / 专名小写化 | 132 / 9,542 | 132 / 9,497 |
| 配对节点内的源缺字标记：字母级 / 整词级 | 39,421 / 4,934（EarlyPrint 残留 gap 58） | 39,078 / 4,890 |
| 文件字符数 v3 → reg | 46,498,315 → 45,835,479 | 46,137,940 → 45,480,704 |
| 替换词对 / 出现次数 | **82,909 / 1,653,696**（`reg_pairs_texts_analysis_en.csv`） | 82,445 / 1,641,033 |
| then→than | 11,918 | 11,830（两视图不能相加） |

99.53% 是**配对覆盖率**，不是逐处核对过的正确率。每篇文档行数与 v3 相同（1,160 篇逐一核对），kept_nodes 逐节点 hash 0 不符。

覆盖低于 99% 的 47 篇、低于 90% 的 11 篇，原因不变：EarlyPrint 未收录 Jonson 1616 Works 末尾的假面（A04632，v3 版本 460、559、632、635、638、661、773、785、787）和 A04637 的 Althorp 娱乐（版本 462），整篇回退 v3 原文；其余散在 A12954、A14715、A10730 等。全部回退节点（含定位失败的原因和最近候选）在 `unaligned_nodes.jsonl`。

## 3. 规则（写方法说明用）

按 Grace 2026-09-13 的决定，目标是让文本更适应 embedding、允许误差，`reg` 不做语境审核，只有三条机械保护：`reg` 无字母、内部大小写错乱、等于词性标签的扔掉；专名（pos nn*/np*）只在 `reg` 保留首字母大写时接受；`join` 拆开的子词合并。已知照收的 EarlyPrint 误改：then→than 里有一部分是时间副词（三部试验剧里约五分之一，不是全库错误率）、Cipres→Cypress 等。**规范化对 embedding / 主题模型的影响尚未验证**，要靠与原拼写视图的对照实验来评估。

## 4. 文件

- `texts_analysis_en_reg/`、`texts_no_prologue_epilogue_reg/`：与 v3 同名文档，逐行对应。
- `reg_manifest.csv`：每篇的对齐类型计数、跨度回退、缺字标记数、v3 与 reg 的 sha256 与文件字符数、EarlyPrint commit 与 sha256。
- `unaligned_nodes.jsonl`、`reg_pairs_texts_analysis_en.csv`、`reg_pairs_texts_no_prologue_epilogue.csv`、`inputs_manifest.json`、`build.log`、`_state/summary.json`。
- 字符覆盖率的分子、分母都不含换行（manifest 的 `char_cov_pct`、`_state/summary.json` 与本报告一致）。
- 可删除：本目录 `_nodes/`（中间文件）、`out_corpus/corpus-v3-reg-2026-09-14/` 与 `-r2/`（作废）、`out_corpus/_reg_test_*`（试跑）。
- 试验与复核记录：`corpus_audit/earlyprint_pilot_2026-09-11/`、`corpus_audit/earlyprint_reg_review_2026-09-14/`、`corpus_audit/earlyprint_reg_r2_review_2026-09-14/`（ChatGPT 两次复核）。

## 5. 下一步

建模对照：两套文本用**同一份由 v3 节点定义的分块映射**（按节点序号切块，不按各自词数重切），同一模型、同一 random_state；`texts_analysis_en_reg/` 对 `texts_analysis_en/`，`texts_no_prologue_epilogue_reg/` 为去序尾声对照。
