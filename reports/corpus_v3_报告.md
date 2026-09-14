# corpus v3 构建报告（八项收尾落实；可进入模型）

2026-09-08。构建目录：`sep6/new_pipeline/out_corpus/corpus-v3-2026-09-08/`（构建器 **build_corpus-2026-09-08.v8**；unit_map v16；提取规则 extract-2026-09-08.13 不变）。v1、v2 原样保留。**模型没有跑。**

## 1. 结果与验收

| 项目 | v2 | **v3** |
|---|---|---|
| 主语料：版本 / 作品 | 582 / 518 | **582 / 518**（不变） |
| `texts/` 全语言 | 582 文档，47.24M 字符 | **582 文档，47.27M 字符** |
| `texts_analysis_en/` | 580 | **580** |
| `texts_no_prologue_epilogue/` | 580 | **580** |
| 节点去向（总 1,055,990） | 保留 959,307 / 排除 89,962 / 留待 6,721 | **保留 959,342 / 已核实排除 89,920 / 待审 0 / 留待 0 / 补充 6,728** |
| 补充材料 `supplementary/` | — | **7 个文档，6,728 节点，280,566 字符**（不计入 582/518） |
| 反读对账 | 1,742 文件 0 不符 | **1,749 文件 0 不符**（含 7 个补充文档；我另外独立重算 hash 一致） |
| 回归测试 | 40/40 | **51/51**（新增 supplementary、翻译关系、序幕显式归属、语言覆盖 11 项） |

与 ChatGPT 的差分预期（保留 959,342 / 排除 89,920 / 补充 6,728）完全一致。v2→v3 逐节点差异 6,763 个 = 6,721 个原留待节点 + 42 个印本英译，全部落在八项之内；主语料文本发生变化的版本只有 5 个：Norwich（126）、Arches of Triumph（489）、Byron Conspiracy（647）、Honor and Industry（791）、Britannia's Honor（913）。

## 2. 八项的落实方式

决定记录在新表 `policy_decisions.csv`（8 行；decided_by 写的是"Grace 2026-09-08 转发 ChatGPT 的八项方案要求落实"，没有另写批准日期）。"补充"= 单独输出有出处的 TXT 和清单，标明本版分析边界，**不是**认定材料非戏剧或功能已定。

| # | 材料 | v3 去向 | 实现 |
|---|---|---|---|
| 1 | Heywood 序尾声 620 节点 | 补充 `A03241.23__unit.txt`（prologue 230 / epilogue 170 / 讲辞 220） | 单元 inclusion_status = supplementary |
| 2 | 印本英译 42 节点 | **11 个演说译文进主语料**（language=en，text_role=speech，relation=translation，`translation_of` 指向同一文件里的拉丁/法/西语原文节点；A02732 Dutchmen 讲辞记"无印本原文"，A01506 Limbert 告别演说记 `not_delivered_according_to_source`）；31 个诗译文进补充 | 节点决定（hash 逐条核对）；`kept_nodes.csv` 新增 relation / translation_of 列，`corpus_manifest.csv` 新增 relations 列 |
| 3 | Lyndsay 4,608 节点 | 补充 `A72573.1__unit.txt`，语言 **sco**（TCP 把整个文件标成 eng，属错误；`unit_language.csv` 新列 overrides_xml_lang=yes 覆盖，来源记为"unit_language.csv (overrides xml:lang)"） | 单元 supplementary，relation = outside_deep_scope，不造 DEEP id |
| 4 | Phillis Funerall 1,198 节点（十二个 day 分区） | 补充 `A01227.2__part_day.txt` | 容器决定 supplementary |
| 5 | Bushell 柱内诗 24 行 | 补充 `A17342__sonnet.txt` | 容器决定 supplementary |
| 6 | Edinburgh：EPIGRAMME 组 12 行 + Walter Forbes 的 panegyric 178 行（说明已改正，不再写 Drummond / "两首 epigram"） | 补充两个文档 | 容器决定 supplementary |
| 7 | Norwich 拉丁诗 57 节点 + 英译 31 节点 | 一个补充文档 `A01506__Norwich_1578_Latin_poems…txt`（la 57 / en 31，按原文顺序） | 节点决定 supplementary，同一 supplementary_group |
| 8 | Byron 合用序幕 24 行 | **进 Conspiracy（ed 647）一次**，角色 prologue；对照视图仍去掉；不复制到 Tragedy | `frames_decisions.csv` 新列 target_unit_id = A18404.1（构建器要求目标单元已构建且同源，否则硬失败） |

## 3. 构建器 v8 的变化（都有回归测试）

- 新去向 **supplementary**：单元 / 容器 / 节点决定都可用；写入 `supplementary/`，配 `supplementary_manifest.csv`（文件、单元、组、决定层级、tcp、源文件 hash、所属版本/作品（若有）、依据、节点数、字符数、语言、角色、sha256）和 `supplementary_nodes.csv`；参加反读对账；`release_checklist.md` 新增 F 节；不进三个主视图，不计入排除或留待。
- 节点决定可带 relation / translation_of。
- frames_decisions 可带 target_unit_id（显式编辑归属）。
- unit_language.csv 可带 overrides_xml_lang。
- 留待（deferred）机制保留，本版为 0。

## 4. 文件

- 构建：`out_corpus/corpus-v3-2026-09-08/`（三个视图 + `supplementary/`；`corpus_manifest.csv`、`supplementary_manifest.csv`、`kept_nodes.csv`、`supplementary_nodes.csv`、`node_fates.csv`、`corpus_reconciliation.csv`、`release_checklist.md`、`FREEZE_REPORT.md`、全部 `inputs_*` 含 `inputs_policy_decisions.csv`）。
- 脚本：`apply_v3_decisions.py`（改表；每条节点对 lines.csv 核对单元、XPath、文本 hash）；改表前备份 `out_versions/tables_before_v3_2026-09-08/`；快照 `out_versions/unit_map-2026-09-08.v16/`。
- 表：`policy_decisions.csv` 8；`manual_overrides.csv` 101（2 行改 supplementary）；`unit_language.csv` 3；`container_audits.csv` 606（4 行 deferred→supplementary）；`body_node_decisions.csv` 5,802（纳入 3,822 / 排除 1,892 / 补充 88）；`frames_decisions.csv` 20（Byron 行改 include + target）。

## 5. 下一步

按 ChatGPT 的完成标准，v3 已通过回归、coverage 绑定和反读对账，增量与归属核对无误，可以进入模型。建模输入：`texts_analysis_en/`（580 个英文文档）为主分析视图；`texts_no_prologue_epilogue/` 为对照；`texts/` 为全语言存档；`supplementary/` 不进模型。更深入的表演史/归属问题留给以后的语料版本。
