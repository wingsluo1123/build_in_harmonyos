# 主编知识草稿审核工作流（Editor Review Workflow）

> 版本：v1.1（2026-10-16，v1.0 随批次 1 PR 建立，v1.1 工具固化至 scripts/kb_editor.py 并更新 SKILL §0.5）
> 适用角色：主编（`OHC_ROLE=editor`）
> 目标：将协作者提交的知识草稿（`knowledge/drafts/`）按可追溯、可复现的流程审核入库，产出正式条目（`knowledge/graph/E*.kv` + `knowledge/doc/E*.md` + `index.tsv`）。

## 核心原则

1. **来源可追溯**：每条草稿必须能定位到来源 PR（合入 main 的 merge commit）。PR 归属反查**前置**到审核之前，作为审核的上下文输入。
2. **未合入即暂缓**：草稿的添加 commit 若只存在于未合入 main 的 feature 分支（PR open / 被拒 / 未建 PR），该草稿**暂缓**——不接纳、不拒绝，留在草稿池等 PR 落地后自然进入后续批次。理由：PR 可能被拒或内容修改，提前入库会产生孤儿知识与回撤成本。
3. **批次按 PR 编号升序**：批次内草稿按来源 PR 编号从小到大排序处理（孤儿草稿垫底），同一 PR 的草稿聚集审核，互为上下文。
4. **每批 100 条**：100 条草稿 = 一个分支 = 一个 PR = 一份报告。
5. **四维审核**：事实 / 质量 / 有效性 / 重复性（详见 P2）。

## 五阶段流程

### P0 准备

```bash
git checkout main && git pull origin main          # 同步
# 构建/更新「草稿→来源PR映射表」（python3 scripts/kb_editor.py pr-map --batch-file <批次文件>）
# 映射字段：draft, pr(!N), title, author, email, merged(bool), branch
```

反查算法（已验证可靠）：
- 草稿文件的**最早添加 commit**：`git log --all --diff-filter=A --format=%H -- <draft.kv> | tail -1`（倒序取最后 = 最早；文件可能被多个分支携带，最早添加者才是源头）
- feat commit 的标题即来源 PR 标题；作者/邮箱取 `git log -1 --format='%an <%ae>' <hash>`
- **GitCode 单 PR API 校正**（已合入时必做）：commit subject 可能是评论命令（`/rebuild` 被 commit 到分支，!13563 实例）或 `Merge` 文本——已知 !N 后拉 `GET /api/v5/repos/.../pulls/{N}`（匿名可用），用 PR 真实标题+登录名覆盖；失败静默回退 commit 值。作者口径统一为 GitCode 登录名（与积分赛事报告一致）
- **PR 编号**：`git log --ancestry-path --merges --oneline <hash>..origin/main | tail -1` 取最早 merge（格式 `!N merge feat/xxx into main`）
- 无 merge 结果 → 分支未合入 → 标记 `merged=false`
- ⚠️ 草稿名里的数字段**不可信**（实例：DRAFT-10035-wmcdplay 实际来自 !13252，!10035 是 liblastlog2）

### P1 批次构建

- 全部草稿按 `(PR 编号升序, 无PR垫底按名称)` 排序，每 100 条一批
- 按 PR 聚类生成审核视图：同 PR 草稿连续展示（合并机会/一致性互查）
- 标记：`merged=false` 的草稿 → **暂缓清单**（本批跳过）；无 git 记录的孤儿草稿 → REVIEW 级单独人工判断

### P2 审核（四维度）

| 维度 | 检查项 | 数据来源 |
|------|--------|---------|
| 事实 | 来源 PR 存在且已合入；按 PR 抽样 1 个软件验证归档目录与 git 历史 | P0 映射表 + archives/ |
| 质量 | 核心三字段（error_signature / root_cause / rec_approach）非空、非占位符、长度≥8 | 逐条解析 kv |
| 有效性 | kv↔md 配对；severity/category 词表合规 | 文件系统 |
| 重复性 | draft-review 工具相似度 + 自查 jaccard（vs 正式库 & 批内）双通道 | 全量预审 JSON |

**决策规则**：
- 三字段任一缺失/占位 → **拒绝**（空壳）
- 无 md 配对 → **拒绝**
- 工具判 merge-into 且 score≥0.7 → **拒绝**（重复）；score<0.7 → 人工比对内容后裁定（误判率实测存在，批次 1 曾推翻 3 条）
- 批内 jaccard≥0.8 → 保留信息量最大者，其余**拒绝**（批内重复）
- 通过 → **接纳**
- 同 PR 多条草稿内容高度关联 → 评估合并为单条（promote 合并检测会自动吸收相似草稿）

### P3 执行

1. 接纳草稿逐条 `ohc-run.py graph promote <draft_id>`（自动分配 E 编号/复用空洞，自动生成 doc 与 index 行）
2. **promote 后置修复**（已知框架缺陷，修复工具：python3 scripts/kb_editor.py fix）：
   - 补 16 必填字段（doc_file / trigger_tool / phase / affected_scope / verification_cmd / rec_description / rec_priority / rec_auto_fix / rec_impl）
   - severity 数字化：`P0→3, P1→2, P2/P3→1`（kv 与 index.tsv 均为数字口径，`parse_index_tsv` 要求数字）
   - 非标字段清理（草稿私有字段如 approach/keywords/solution 等，可映射项改名：keywords→match_keywords）
   - relations（similar_to 等）值含自由文本/DRAFT 引用 → 清空（多行块连删）
   - principles 自由文本 → P 编号映射（no-platform-macros-in-patches→P005 等）
3. 拒绝草稿删除 kv+md；暂缓草稿原样保留
4. `graph validate --fix` 直至 0 error（kv=md=index 三向对齐）

### P4 验证与发布

1. `git checkout -b editor/kb-promote-batch-<N>` → `git add knowledge/` → commit（**不得包含 archives/ 等无关变更**）
2. `git push -u origin <branch>`
3. 生成审核报告（python3 scripts/kb_editor.py report）→ 桌面 `知识库审核报告-批次N-日期.md`
4. 回复管理员：分支名 + 报告文件路径（报告即 PR 描述来源，原始 PR 编号/标题/作者/邮箱已自动填充）
5. 管理员网页创建 PR 并合入 → 通知主编进入下一批

## 报告规范

- 接纳清单：草稿原名称 / 接纳后编号 / 正式 PR 编号（留空待 PR 创建）/ 原始 PR 编号及标题（带 GitCode MR 链接）/ 作者 / 邮箱 / 状态
- 拒绝清单：草稿名 / 原始 PR / 拒绝原因（中文规范化）
- 暂缓清单：草稿名 / 所在 feature 分支 / 暂缓原因（PR 未合入）
- 附：批外自动合并吸收清单、审查方法、质量披露、校验结果（`批次草稿 N→0 ｜ 图谱 X→Y（kv=md=index，0 error）`）

## 工具链

统一入口 `scripts/kb_editor.py`（v12.23 起随仓库交付，子命令即流程步骤）：

```bash
python3 scripts/kb_editor.py batch --size 100            # P1 批次构建（时间序 + DEFER 预过滤）
python3 scripts/kb_editor.py pr-map --batch-file <F>     # P0 批次内来源 PR 精查（增量缓存 .ohc/kb-editor/）
python3 scripts/kb_editor.py audit --batch-file <F>      # P2 四维审核 → 决策表 TSV（含 DEFER 过滤）
#   前置: python3 scripts/ohc-run.py draft-review --json > .ohc/kb-editor/draft-review-full.json
#   人工环节: REVIEW 条目逐条比对内容裁定（误判实测存在）
python3 scripts/kb_editor.py promote --decisions <F>     # P3 批量 promote ACCEPT（日志 .ohc/kb-editor/promote.log）
python3 scripts/kb_editor.py fix                         # P3 后置字段修复（git status 新增 E 条目）
python3 scripts/ohc-run.py graph validate --fix          # P4 校验直至 0 error
python3 scripts/kb_editor.py report --decisions <F> --batch N --date D --out <报告路径>
python3 scripts/kb_editor.py publish --branch editor/kb-promote-batch-N --push
python3 scripts/kb_editor.py pr-info <PR号...> [--fix-map]   # 辅助: 按PR号核对标题/作者/状态, 可回写校正缓存
```

**性能注记**：ancestry 单次查询 0.5s（IO 正常）但 HMDFS 抖动时可拖长，故 ①单次 20s 超时+标记重试；②全量 3593 条不一次性查询，按批次 100 条精查（`--batch-file`）；③未合入分支定位用 `git log --all --source` 的 ref 标注（消除 `branch --contains` 12s/次）。

### 与 ohc-run.py 的关系

`kb_editor.py` 是主编专用独立脚本（不依赖技能运行时路径）；`graph promote`/`graph validate`/`draft-review` 仍由 `scripts/ohc-run.py` 提供，kb_editor 以子进程调用。

## 已知框架问题（待框架 PR 修复）

1. `_kv_to_tsv_row` 写 severity 为 `P1` 文本，`parse_index_tsv` 期望数字 → 新条目 index 行被解析器丢弃（C2 假阴性）
2. promote 合并检测把被吸收草稿的字段**内联拼接**进宿主字段值（E608 实例：verification_cmd 拼进 affected_scope）
3. promote 不写 doc_file 等必填字段、不清理非标字段（靠 kb_editor.py fix 兜底）
4. 草稿名数字段与 PR 编号无对应关系（不可作为反查依据）
