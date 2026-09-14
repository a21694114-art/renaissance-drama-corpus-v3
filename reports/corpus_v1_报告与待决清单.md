# corpus v1 正式构建报告 + 需要 Grace 决定的清单

2026-09-07。构建目录：`sep6/new_pipeline/out_corpus/corpus-v1-2026-09-07/`（构建器 build_corpus-2026-09-07.v7，unit_map v14，提取规则 extract-2026-09-07.12）。**模型没有跑。**

## 1. 构建结果

| 项目 | 数值 |
|---|---|
| 纳入的版本（edition）/ 作品（work） | **577 / 515** |
| 全语言视图 `texts/` | 577 个非空文档，46.48M 字符（含换行） |
| 英文分析视图 `texts_analysis_en/` | 575 个非空文档（缺 Philotus = sco、Pedantius = la） |
| 对照视图 `texts_no_prologue_epilogue/` | 575 个非空文档（英文，去掉 prologue/epilogue；induction 保留） |
| 候选节点去向 | 1,055,990 = 保留 953,711 + 已核实排除 87,748 + 待审 0 + **留给你决定 14,531** |
| 反读对账 | 1,727 个文件，0 不符 |
| 年份范围 / 类型 | 1520–1641；Adult Professional 246、Occasional 109、Boys Professional 78、Interlude 37、University/Inns 28、Translation 27、Closet 27、其他 25 |

文件名 `<edition_id>__<old_id>.txt`；元数据在 `corpus_manifest.csv`（只用 `*_effective` 列；`year_effective_raw` 保留 DEEP 原始日期区间；`languages`、`roles` 列记录每个文档的语言和角色构成）。`kept_nodes.csv` 是每个视图的输出顺序，`node_fates.csv` 是全部 1,055,990 个候选节点的去向，`release_checklist.md` 分列 A 纳入 / B 已核实排除 / C 已批准延期 / **E 留给你决定** / D 阻塞项（现为空）。所有输入表和 hash 都复制在 `inputs_*`。

"保留"的含义：`<sp>` 内的节点按结构规则保留；`<sp>` 外的节点只有经过容器签核或节点决定才保留。不是每个节点都经人工逐行核对。

## 2. 这一轮按既定政策自行落实的事（供你抽查）

**72 个 pending 单元**（`manual_overrides.csv` 新增 75 行，全部带证据）：
- 身份确认 47 个（标题页/首行/位置证据，如 Supposes、Jocasta、Cynthia's Revels、Sejanus、Catiline、Blackness/Beauty 1608、Folio 2H6/3H6/Troilus/Cymbeline、Randolph、Campion、Middleton 六篇 Honourable Entertainments……）。
- **更正一处自动匹配错误**：1590 年 Tamburlaine 两部被按顺序对调了；现按序幕"From jigging veins…"和"THE SECOND PART"标题改正。
- Gentleness and Nobility：抽取规则加入拉丁序数（Secunda pars），A10440 拆成 Part 1 / Part 2 / 哲人结语（结语作为 Part 2 的 component）。
- 非戏剧划分改为 excluded（Daniel 的 Delia/Rosamond/Civil Wars/Musophilus、Carew 诗集、Tatham 诗集、Gomersall 的 Elegy 和 Levite's Revenge、Jonson 1616 Epigrammes/Panegyre、1640 Underwood/Horace/Grammar/Discoveries、Heywood A03241.23、Gascoigne Posies 的 Peroratio/F.I.）。
- 4 个单元留给你（见第 3 节）。

**同版重复文本**（`edition_witness_selection.csv` 新增 3 对，按你 2026-09-07 确认的规则"完整转录中取不可辨识标记较少者"）：Bartholomew Fair、Staple of News、Devil Is an Ass 的 1631 印张（A04633）与 1640 卷二重印（A72473）。计数：BF 24 vs 58、Staple 32 vs 82、Devil 19 vs 90（A72473 更少），所以代表文本是 A72473.1.x，A04633.x 为备选。BF 的 Induction 在 A72473 里位于 front（已作为 induction frame 纳入）。行序列匹配率 0.83 / 0.93 / 0.88。状态写的是"按既定规则确认"，你可以推翻。

**日期**：A72473.1.3 Devil Is an Ass 按 .1.1/.1.2 的先例定为 1631（edition 973）。

**功能审核**（`container_audits.csv` 592 行：纳入 466 / 排除 122 / 留待 4，覆盖 365 个单元；`body_node_decisions.csv` 5,715 行：纳入 3,763 / 排除 1,895 / 留待 57；其中 ChatGPT 提供 4,053 个节点决定 + 8 行容器，我提供 1,662 个节点决定 + 584 行容器）。原则：按功能不按标签——角色的台词、独白、演说、歌、合唱、已核实的序尾声纳入；作者叙述、场景/服装/装置描写、舞蹈提示、题辞/铭文、演员名单、题解（argument）、哑剧描述、制作署名、印在正文里的献诗排除。Seneca/Alexander/Greville 等无 `<sp>` 的整部诗剧按 div 类型链整批纳入（样例核对过）；市长庆典和宫廷假面逐节点读过。

**Frames**（`frames_decisions.csv` 20 行）：Induction 纳入（Bartholomew Fair、Staple of News、Antonio and Mellida、Isle of Gulls、Rival Friends）；剧末歌纳入（Like Will to Like、Three Laws、Lancashire Witches、Roister Doister、Triumphs of Truth、Fatal Dowry）；Bale 的 Prolocutor 开场作 prologue；Poetaster 的 Apologetical Dialogue 作 epilogue（Jonson 说"只在台上说过一次"，编辑判断）；排除：Aglaura 另一版本的序尾声（随该版本一起在主语料外）、Lord Hay's Masque 卷末带乐谱重印的歌（正文已有）、Whore of Babylon 哑剧描述。

## 3. 需要你决定的清单（都已"留待"，不在 v1 里，可逆）

**A. 整部单元（4）**
1. **A72573.1 Lyndsay, Ane Satyre of the Thrie Estaitis (1602)**：没有 DEEP 记录，且是苏格兰语。是否纳入全语言语料（sco）？涉及 DEEP 范围界定。
2. **A16527.1 Croesus、A16527.2 Darius（Alexander 1607 Monarchicke Tragedies）**：本地 DEEP 表里 5061 集只有 Alexandraean Tragedy（两行，同一 edition 608）和 Julius Caesar，没有 Croesus/Darius 行，疑为元数据损坏。需要对 DEEP 官方导出核对（构建环境访问不到 deepplaybooks.org）。定了行号就能纳入。
3. **A01514.1 Gascoigne Posies 1575 "The Reporter" 诗组**：DEEP 的 Montague Masque (5007.01) 埋在这组诗里（`/*/*[2]/*[2]/*[1]/*[2]/*/*[35]`），要单独拆分才能建。

**B. 容器/节点（6 处，14,531 节点中的 1,483）**
4. **A01227.2 Fraunce, Phillis Funerall（68K 字符）**：Amyntas 十一天的哀歌（六音步），有叙事框架；DEEP 把它算作该作品第二部分。算牧人的独白（纳入）还是叙事诗（排除）？
5. **A17342 Bushell's Rock, "A Sonnet within the pillar of the Table at the Banquet"（72 行）**：向国王王后致意，但标题说放在宴会桌的柱子里——演唱还是陈列？
6. **A18463 Edinburgh 1633：两首致国王的 Epigram（12 行）和 Drummond 的 Panegyric（178 行）**：随入城记印出，有没有朗诵？
7. **A01506 Norwich 1578 两首拉丁诗 Ad Solem / Ad Civitatem（57 节点，la）**：表演功能未核实。不影响英文视图。
8. **A18404 Byron's Conspiracy and Tragedy 1608 的合用 prologue（24 行）**：一篇序服务两部剧——归 Conspiracy、两部都给，还是都不给？

**C. 政策问题：已演出的拉丁/法/西语讲辞的英译印本**
目前处理：演出用的原文保留在全语言视图（带语言标签，不进英文视图），**印出的英译一律排除**（Norwich 市长演说、两篇拉丁演说、告别演说和两首拉丁诗的英译；Arches of Triumph 意大利/荷兰拱门讲辞英译；Honor and Industry 法/西讲辞英译；Britannia's Honor 法语讲辞英译）。共约 40 个节点、5 万字符。另一种做法是让英译进英文分析视图。请定。

**D. 已知的不纯净处（已纳入，你可能想改）**
9. **A07502.2.4 Middleton, Sir Francis Jones's Easter**：这个单元后半印着 Lords of the Council 的两场娱乐（DEEP 5078.09/.10），现在随该单元一起进了语料；要分开需要新的拆分。
10. **A04633 vs A72473 代表文本**：按规则选了 1640 卷二重印（gap 更少）；如果你更愿意用 1631 原卷，改 `edition_witness_selection.csv` 的 role 即可。
11. 205,742 个保留节点的语言是"assumed en"（源 XML 无 xml:lang 或标 unk）；`edition_language_check.csv` 的功能词粗查没有发现其他整部非英文文本，但混合段落只在 Norwich、Theobalds、Hercules Furens、Magnificent Entertainment 等已审单元里逐节点处理过。

## 4. 下一步
- 你检查构建结果和上面 11 项；ChatGPT 可以对这一轮的容器/节点决定（`inputs_container_audits.csv`、`inputs_body_node_decisions.csv` 中 source 含 "Claude" 的行）做复核。
- 决定后改表、换新版本号重建即可（构建器拒绝覆盖已有目录；每次重建都重做反读对账）。
- 然后再跑模型。
