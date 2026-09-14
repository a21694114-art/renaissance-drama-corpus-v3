# corpus v2 构建报告 + 最终待决清单

2026-09-08。构建目录：`sep6/new_pipeline/out_corpus/corpus-v2-2026-09-08/`（构建器 build_corpus-2026-09-07.v7 不变；unit_map v15；提取规则 extract-2026-09-08.13）。v1（`corpus-v1-2026-09-07/`）原样保留为历史版本。**模型没有跑。**

## 1. 构建结果（重新计数，不沿用 577/515）

| 项目 | v1 | **v2** |
|---|---|---|
| 纳入的版本 / 作品 | 577 / 515 | **582 / 518** |
| 全语言视图 `texts/` | 577 个文档，46.48M 字符 | **582 个文档，47.24M 字符** |
| 英文分析视图 `texts_analysis_en/` | 575 | **580**（缺 Philotus = sco、Pedantius = la） |
| 对照视图 `texts_no_prologue_epilogue/` | 575 | **580** |
| 候选节点去向（总数 1,055,990 不变） | 保留 953,711 / 排除 87,748 / 留给你 14,531 | **保留 959,307 / 已核实排除 89,962 / 待审 0 / 留给你 6,721** |
| 反读对账 | 1,727 个文件 0 不符 | **1,742 个文件 0 不符**（构建器对账 + 我独立重算 sha256 一致） |
| 回归测试 `test_build_corpus.py` | 40/40 | **40/40** |
| coverage_check | 1,055,990，缺 0，重复 0 | **同** |
| 年份 / 类型 | 1520–1641 | 1520–1641；Adult Prof 246、Occasional 112、Boys Prof 78、Interlude 37、Closet 29、Univ 28、Translation 27、其他 25 |

新增的 5 个版本：Middleton 5078.09（ed 836）、5078.10（ed 837）；Gascoigne Montague Masque 5007.01（ed 110）；Alexander Croesus 5060.01（ed 491）、Darius 5060.02（ed 446）。新增 3 个作品（Croesus/Darius 的 1637 版本 v1 已在）。

**v1 → v2 逐节点差异只有这 10 组，全部落在本轮五项修正之内，其他 105 万节点去向一字未变：**

| 单元 | v1 | v2 | 节点数 |
|---|---|---|---|
| A07502.2.4.1 Jones's Easter | 保留 speech | 排除（演出指示） | 2 |
| A01514.1.1 Montague Masque | 留待 | 保留 dramatic_body 346 + speech 30 | 376 |
| A01514.1.0 Posies 其余诗 | 留待 | 已核实排除（非戏剧诗集） | 2,832 |
| A16527.1 Croesus | 留待 | 保留（dramatic_body 2,558 / chorus 390） | 2,948 |
| A16527.2 Darius | 留待 | 保留（dramatic_body 1,796 / chorus 430） | 2,226 |
| A17342 Bushell "Sonnet sung" | 留待 | 保留 song | 48 |
| A03241.23 Heywood 序尾声 | "非戏剧"排除 | 留给你决定 | 620 |

## 2. 五项修正的落实

1. **Middleton A07502.2.4 拆成三个单元**（`extract_units.py` 新增 `EXPLICIT_SPLITS` 显式拆分表，按容器 `/*/*[2]/*[2]/*[2]/*[9]` 的子元素区间 1–8 / 9–13 / 14–30；XML 与 XPath 不动，每个候选节点只归一个单元）。→ 5078.08 Jones's Easter（ed 835）保留 14 节点（2 首歌 + 12 行 Hyacinth/Adonis 台词；旧 seq 16–17 "Then fals into the former speech of Flora…" 按 ChatGPT 建议排除为演出指示）；5078.09 Sheriff Allen（ed 836）56 节点；5078.10 Sheriff Ducie（ed 837）70 节点。与 ChatGPT 预期 14/56/70 完全一致。原有 7 条节点决定迁移到新单元号（键不变，文本 hash 复核）。
2. **Alexander 接回官方记录**：按 `official_reconnections.json`（DEEP 官方导出 item_data.json，sha256 10005117…），A16527.1 → Croesus 5060.01 / work 209 / ed 491 / 1604，A16527.2 → Darius 5060.02 / work 196 / ed 446 / 1604。做法：`deep_additions.csv` 新增两行（键 A16527.5/.6，注明来源），`manual_overrides.csv` 改为 confirmed/primary/proposed，`date_resolutions.csv` 新增两行记录"剧本印刷 1604 vs 合集重发 5061/1607"两个层级；没有发明 5061.xx。两部的 `<sp>` 外诗行（合唱与人物的分节独白，7 条 div 链）逐组读首末行后按 A16527.3/.4 同样规则签核纳入。
3. **Montague Masque 拆出**：A01514.1 → A01514.1.1（DEEP 5007.01）+ 残余 A01514.1.0。**与 ChatGPT 的 346 节点有一处不同**：我把 div 35 之后的 36–38 也划进去（30 行），因为它们的标题写明是演出中的口头部分——"After the maske was done, the Actor tooke maister Tho. Bro. by the hand … with these words"、"he torned to the Bridegroomes and Brides, saying thus"、"the Actor did make an ende thus"，按"看功能"原则属表演语言，角色标 speech。若你或 ChatGPT 不同意，删掉 `container_audits.csv` 里 A01514.1.1 的 *[36]/*[37]/*[38] 三行并把拆分区间改回 35–35 即可。残余的 43 首诗（标题逐一看过：Anatomy of a Lover、Lullaby、Deprofundis、Dan Bartholmew……）按已定政策作为非戏剧诗集排除，不是"留待"。
4. **Bushell A17342**：原来整单元的 `sonnet` 留待行只保留到 `/*/*[2]/*[2]/*[3]`（"A Sonnet within the pillar of the Table"，24 行，仍留给你）；`/*/*[2]/*[2]/*[5]`"A Sonnet sung to the KING and QVEENE at Mr Bushells Rock" 48 行按 ChatGPT 的 48 条节点决定纳入为 song（hash 逐条核对；语言不写死，由 xml:lang 解析）。该文档现 166 节点（v1 118）。
5. **Heywood A03241.23**：撤回 `non_dramatic` 和不实的"已由 frames 表处理"说明。现在的记录：620 个正文候选 = 序 230 / 尾声 170 / 呈献者讲辞 220，是为宫廷、私宅和剧场演出写的表演语言，但单独印行、不能按"作品 + 版本/场次"归到任何 DEEP 版本文本；A03241 的 7 条 frames 行只覆盖前后附件。状态改为 **deferred_to_grace**（第 3 节第 1 项），不算"已核实非戏剧"，也不并入其他版本。

其余按 ChatGPT 复核维持：Jonson 三组代表文本不变；未重启全库审核（本轮只碰上述单元）。

## 3. 最终待决清单（都在 v2 之外、可逆；共 6,721 节点）

**A. 政策问题（先定原则）**

1. **Heywood 未归属的序尾声（A03241.23，620 节点）**——我的建议：作为"补充材料"单独存放（有独立 TXT 和清单），不进主语料；不因剧名相同就贴到其他版本上。你同意即照此结项；若你想让其中可确认剧目/场次的几篇（如 Red Bull 的 Richard III、Cockpit 的 Queen Elizabeth、Cupid and Psyche）进入对应版本，需要你逐篇确认归属，我再做 frames 归属表。
2. **英译本政策（约 40 节点，5 万字符，目前排除）**：已演出的拉丁/法/西/意语讲辞的印本英译（Norwich 市长演说等、Arches of Triumph、Honor and Industry、Britannia's Honor）。ChatGPT 建议：英译进英文分析视图，language=en，并记 translation 关系；原文仍留全语言视图。请定：（a）维持排除；（b）采纳 ChatGPT 建议。
3. **Lyndsay, Ane Satyre of the Thrie Estaitis 1602（A72573.1，4,608 节点，sco）**：无 DEEP 记录。是否作为 DEEP 范围之外的苏格兰语补充文本纳入全语言语料（同 Philotus 的处理：标 sco，不进英文视图）？涉及语料边界的定义。

**B. 具体材料（按功能判断）**

4. **Fraunce, Phillis Funerall（A01227.2，1,198 节点）**：Amyntas 十一天的哀歌，有叙事框架；DEEP 把它算作该作品第二部分。牧人独白（纳入）还是叙事诗（排除）？
5. **Bushell 柱内十四行（A17342，24 行）**：致国王王后，但标题说置于宴会桌的柱内——演唱/朗诵还是陈列铭文？（同单元另一首"sung"的 48 行已纳入。）
6. **Edinburgh 1633（A18463）**：两首致国王的 Epigram（12 行）与 Drummond 的 Panegyric（178 行），随入城记印出，有无朗诵？
7. **Norwich 1578 两首拉丁诗 Ad Solem / Ad Civitatem（A01506，57 节点，la）**：表演功能未核实；不影响英文视图。
8. **Byron 1608 合用序（A18404，24 行）**：一篇序服务两部剧——归 Conspiracy、两部都给，还是都不给？

你只需要对 1–8 各答一句，我改表换版本号重建即可（每次重建都重做 40 项回归、coverage 绑定和反读对账）。

## 4. 文件与快照

- 构建：`out_corpus/corpus-v2-2026-09-08/`（`corpus_manifest.csv` 只用 `*_effective` 列；`kept_nodes.csv`、`node_fates.csv`、`corpus_reconciliation.csv`、`release_checklist.md` A/B/C/E/D 分节、`FREEZE_REPORT.md`、全部 `inputs_*` 与 hash）。
- 本轮修改脚本：`apply_v1_review_fixes.py`（改五张表，每条节点行对 `out/lines.csv` 核对单元、XPath、文本 hash；不静默覆盖）；改表前的五张表备份在 `out_versions/tables_before_v2_fixes_2026-09-08/`。
- 快照：`out_versions/unit_map-2026-09-08.v15/`（全部输入表、脚本、`lines.csv`、`unit_map.csv`）；提取规则 .12 的脚本备份 `out_versions/extract_units_rule12_backup.py`。
- 表的现状：`manual_overrides.csv` 101 行；`container_audits.csv` 606 行（纳入 480 / 排除 122 / 留待 4）；`body_node_decisions.csv` 5,765 行（纳入 3,811 / 排除 1,897 / 留待 57）；`date_resolutions.csv` 9 行；`deep_additions.csv` 3 行；`frames_decisions.csv` 20 行不变。
