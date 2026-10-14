# `DRAFT-meson-recipe-project-options-vs-upstream-option-set`：Meson 配方选项集与上游版本不一致导致配置失败

> Contributor: Quas | Status: DRAFT | Created: 2026-09-30
> 与同 stem 的 .kv 配对；来源：orc 0.4.42 → 0.4.41 版本迁移实测（本机 G2 门禁真实失败后修复）

## 现象

`meson setup` 阶段直接失败，报错形如：

`
../meson.build:1:0: ERROR: Unknown option: "hotdoc".
ConanException: Error 1 while executing meson.configure()
`

三个容易误判的特征：

1. 报错位置指向 `meson.build` 第 1 行（选项校验发生在读构建脚本之前），而不是任何编译错误；
2. 同一份配方用在较新的上游版本上完全正常，换一个版本就失败（本例：orc 0.4.42 的配方用在 0.4.41 源码上）；
3. 静态检查（G1 配方完整性）不会发现，只有真正跑一次 configure 才暴露。

## 根因

1. **meson 对未知选项是致命错误，不是警告**：传一个上游没声明的 `-D<opt>=...` 会直接中止配置。
2. **选项集合定义在上游源码里，且随版本演进**：旧版是 `meson_options.txt`，新版是 `meson.options`（部分版本两者并存，另有 E258 覆盖并存场景）；选项的增删发生在上游各版本之间，配方不能假定它稳定。
3. **骨架复用不会自动跟随**：以既有档案为骨架做版本迁移时，配方里的 `project_options` 原样保留。本仓库
   `archives/**/conanfile.py` 中 `project_options[` 命中 **319 处**，说明「按名写死选项」是主流写法，这个风险是系统性的。
4. **暴露点晚**：只有真实 configure（G2）才发现，所以“配方看起来没问题”与“真的能配置”之间隔着一整轮构建。

## 修复步骤（可操作）

1. **先取目标版本的真实选项集**（不要凭记忆）：
   - `curl -sL <source.tar.xz> | tar tJf - | grep -E 'meson_options\.txt|meson\.options'`
   - `grep -oE "^option\('[^']+'" <src>/meson_options.txt`（新版文件名 `meson.options`）
2. **与配方选项表做差集**：`grep -n 'project_options\[' archives/<letter>/<pkg>/<version>/conanfile.py`，
   找出“配方传了但上游没有”的项（本例即 `hotdoc`）。
3. **按目标版本裁剪或改名**：删除上游已移除的选项；命名变更的改成新名；不要盲目保留骨架配方的整份选项表。
   - 本例修复：删掉 orc 0.4.41 配方里的 `tc.project_options["hotdoc"] = "disabled"`（0.4.41 没有 hotdoc 选项）
4. **删除前确认它真的不存在**（见「反例与边界」）：必要时换成目标版本中的等价选项。
5. **重跑 G2 门禁**：`ohc conan-verify <pkg> <version>`，必须看到 G2 PASS；配置通过不等于后续成功。

## 验证方式

- 上游选项集与配方选项表的差集为空（或差异都被显式处理）；
- `ohc conan-verify <pkg> <version>` 的 G2 门禁 PASS（meson setup 成功进入编译阶段）；
- 交付记录里保留「目标版本选项集」与「配方选项表」的对照结论（哪些删、哪些改名、依据是什么）。

## 适用范围

- 所有使用 `MesonToolchain` 或 Meson 且设置 `project_options` 的 Conan 配方；
- 特别是「以既有档案为骨架迁移到另一上游版本」的场景——两个方向都适用：新版配方配旧版源码（本例），以及旧版配方配新版源码（上游删除了选项）。

## 反例与边界

- **反例一**：用 `try/except` 吞掉 `meson.configure()` 的失败，或把 `Unknown option` 当作可忽略告警。
  这等于用错误的选项集继续构建，产物与声明的配置不一致。
- **反例二**：只把报错的选项删掉就收工。**删掉一个选项会改变构建行为**：原本由配方显式关闭的文档、测试、后端等子项会回到上游默认值
  （本例 hotdoc 属于文档子项，风险较低；若是测试或后端开关，风险就高）。所以删除前必须核对目标版本是否真的没有该项，
  有等价项就改用等价项。
- **边界**：本条只解决「选项名在上游不存在」这一类失败。若报错不同（依赖缺失、编译器不认识参数、`meson.options` 与
  `meson_options.txt` 并存导致拒绝配置），属于别的条目范围（后者见 E258）。
