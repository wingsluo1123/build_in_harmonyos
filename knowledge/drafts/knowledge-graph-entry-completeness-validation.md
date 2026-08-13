# knowledge-graph-entry-completeness — 知识图谱条目完整性验证方法

> 关联知识草稿：`knowledge/graph/draft/knowledge-graph-entry-completeness-validation.kv`
> 关联库：linux-firmware-brcm 20260622（PR #3639 适配过程中发现）
> 状态：draft（draft: true），提交审核后由主编确定最终编号

本文档与同名 `.kv` 配套，说明知识图谱条目完整性问题的识别方法、真实根因、推荐处理方案、
验证命令、适用范围与限制，以及当前库如何通过隔离策略保持 PR 原子性。

---

## 1. 错误识别

**触发场景**：`graph validate` 或 `finish`（step5b 知识完整性检查）报告以下任一类问题：

| 错误类型 | 典型输出 | 说明 |
|----------|----------|------|
| 必填字段缺失 | `E219.kv: root_cause 为空`、`E305.kv: rec_approach 为空` | W4 `check_knowledge_completeness` 的 `_REQUIRED_KV_FIELDS = [error_signature, root_cause, rec_approach]` 判定 |
| 多行字段解析为空 | `E305.kv: root_cause 为空`（文件内实为 `root_cause: \|` 块标量且后有多行文本） | 校验器逐行正则 `^(\w+):\s*(.*)` 只读取首行，块标量首行内容为 `|`，命中 `val == "|"` 判定为空 |
| doc↔kv 配套缺失 | `E###.kv → 缺 E###.md` 或反之 | 条目文档与 kv 不同名 |
| graph validate 报告问题 | `E305: approach mismatch`、`unknown principle`、`non-standard fields` | 全库既有条目问题（severity/approach/字段规范） |

**关键判别**：先区分「条目真的缺内容」与「校验器对 `key: |` 多行块标量解析不兼容」。
用 `grep -A5 '^root_cause:' knowledge/graph/E219.kv` 查看条目文件：若 `|` 后存在缩进多行实际文本，
则该条目**内容完整**，报错来自解析兼容性问题；若字段后无任何内容，才是真正的字段缺失。

---

## 2. 真实根因

1. **已有知识条目字段不完整**：部分官方 E 条目（如 E219/E253/E305）的 `root_cause`/`rec_approach`
   使用 YAML 块标量 `|` 书写多行内容，而校验器用逐行正则解析，只取字段首行 → 读到 `"|"` → 判定为空；
2. **校验器与条目格式不兼容**：`workflow_checks.py` 的必填字段检查（`_REQUIRED_KV_FIELDS` 循环）
   不支持多行块标量读取，属校验逻辑与条目书写格式的兼容性缺口；
3. **全库既有问题**：`graph validate` 报的 8 errors/15 warnings（如 E305 approach mismatch）为
   知识库存量问题，与具体适配库无关，任何运行 finish 的流程都会命中。

> 实测证据（linux-firmware-brcm 20260622 实例）：E219/E253/E305 的 `root_cause` 均为 `|` 块标量，
> E305 的 `rec_approach` 也为 `|` 块标量；`rec_approach` 为单行值的 E219/E253 不被报空，
> 与 W4 输出（E219/E253/E305 root_cause 为空、E305 rec_approach 为空）完全吻合。

---

## 3. 推荐方案

1. **管理员独立维护**：由管理员通过独立知识库维护 PR 修复官方 E 条目——补全缺失字段，
   或将 `key: |` 块标量改为校验器可解析的格式（单行值或升级解析器支持多行块标量），
   同时校验 `doc/E###.md ↔ graph/E###.kv` 对应关系；
2. **当前库 PR 隔离**：当前库 PR **不直接修改旧 E 条目**，也不混入其修复；通过新增
   `firmware-resource-package-brcm-validation.kv/.md` 与
   `knowledge-graph-entry-completeness-validation.kv/.md` 两个草稿，将当前库验证问题
   与全局维护问题解耦，保持 PR 原子性；
3. **临时验证假设（可选）**：如需本地临时补全 E219/E253/E305 以验证解析假设，必须先记录
   逐文件 diff（`git diff > /tmp/e-fields.diff`），验证后**完整回滚**；临时改动不得进入当前 PR。

---

## 4. 验证命令

```bash
# 1) 复现知识图谱完整性检查（应报 E219/E253/E305 字段为空 + graph validate 问题）
python3 scripts/ohc-run.py graph validate
#    或直接运行 W4 检查
python3 -c "import sys; sys.path.insert(0,'scripts'); from ohc.workflow_checks import check_knowledge_completeness; print(check_knowledge_completeness(pdir='.'))"

# 2) 查看条目文件真实内容（确认 | 块标量后有多行文本）
grep -A5 '^root_cause:' knowledge/graph/E219.kv
grep -A5 '^rec_approach:' knowledge/graph/E305.kv

# 3) 运行 finish（如实记录退出码，禁止伪造通过）
python3 scripts/ohc-run.py finish linux-firmware-brcm 20260622 built

# 4) PR 原子性检查（应只含当前库 + 当前 draft）
git diff --name-only origin/main...HEAD
```

---

## 5. 适用范围

- 所有新增/维护的知识图谱 E 条目与知识库 draft；
- 所有运行 `finish`（step5b）/`graph validate`/`check-knowledge-completeness` 的适配流程；
- 管理员侧的知识库维护 PR 与校验器（graph validator）升级。

---

## 6. 限制

- 本 draft **只能记录和指导处理**，不能自动修复 E219/E253/E305（`rec_auto_fix: false`）；
- 不得修改、覆盖、重编号 E219/E253/E305 或其他官方 E 条目；
- 不得修改 graph validator（`graph.py` / `workflow_checks.py` 等校验逻辑）；
- 不得将 finish exit 1 伪造为通过（禁止手动改 `.ci-result.json` 或篡改日志哈希）；
- 本地临时补全 E 条目的改动验证后必须完整回滚，不得进入当前 PR。

---

## 7. 当前库复用（linux-firmware-brcm 20260622）

- 在 `finish` step5b 中发现全局知识图谱问题（E219/E253/E305 字段判定为空 + graph validate 存量问题）；
- 通过新增两个知识库草稿隔离当前适配与全局维护问题：
  1. `firmware-resource-package-brcm-validation.kv/.md` — 解决本库固件资源完整性、许可证、
     SHA256、目录结构、无 ELF、安装路径和 `package_info` 验证问题；
  2. `knowledge-graph-entry-completeness-validation.kv/.md` — 识别并指导隔离全局 E 条目
     完整性/解析兼容性问题；
- 当前 PR 不修改任何官方 E 条目，不混入其他库文件，保持 PR 原子性；
- `graph validate` / `finish` 的失败如实记录（退出码 1），不伪造通过，交由分析端与管理层决策。

---

## 关联与元数据

- kv 文件：`knowledge/graph/draft/knowledge-graph-entry-completeness-validation.kv`
- 关联实例：E219 / E253 / E305（root_cause/rec_approach 块标量解析判定为空）
- 原则引用：R11（失败先查归档）、R12（先匹配错误模式）、W2（PR 原子性）、W5（知识图谱完整性）
- similar_to：E219, E253, E305
- last_updated：2026-08-11
- contributor_id：probe
