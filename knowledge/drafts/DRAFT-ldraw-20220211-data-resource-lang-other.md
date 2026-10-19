# 纯数据/资源库 lang-preflight 语言类别（`--lang other` 复检）

> 草稿（DRAFT-ldraw-20220211-data-resource-lang-other）——需人工/AI 审核后提升为正式条目。
> 来源：ldraw 20220211（LDraw.org 官方零件库）第一轮适配。

## 问题

`ohc-run.py lang-preflight`（R47，AI Worker 协议 v0.8 附录 D）对**无任何 C/C++ 源码的
纯数据/资源库**执行语言预检时：

- SKILL 语言计数扩展名表只识别 `.c/.cpp/.rs/.py/.go/.pl/.lua/.js/.java/.sh/.bash` 等；
  纯数据/资源库的文件（如 `.dat/.ldr/.png/.ttf/.db/.otf`）全部不计入 → 源码统计为 0。
- 判定结果 `detected_language = "other"`（协议 §4.6 枚举含 other）。
- 任务默认语言 `cpp`（`OHPCD_LANG` 未注入时）→ `detected != expected` → **自动写终态
  `env_unsupported`**（含 detected_language + language_evidence 三字段）。

实际案例：ldraw 20220211（LDraw 零件库，37,261 个文件全为 `.dat/.ldr/.png/.txt/.zip`）
首次预检即被误判为 `other → env_unsupported`，仿佛"语言不匹配"。

## 根因

这是**语言类别判定缺失**，不是语言不匹配的硬错误：纯数据/资源库本就没有 C/C++ 源码，
`other` 是它的正确类别。默认 cpp 假设 + 无源码统计 → 误报。

## 方案

1. 识别数据资源库（`source_stats` 为 0、无 manifest/构建系统，如仓库先例
   adobe-source-han-sans-*、libloc-database 均标注 `build_system: custom` 纯数据包）。
2. 以 `--lang other` 复检：`detected=other == expected=other` → exit 0，
   写 `lang_checked` 里程碑，确认数据资源库语言类别，进入 Conan 适配主流程。
3. 按数据资源包模式（E255 `resource-data-package-conan-recipe`、E241/E281/E305/E536
   家族）适配：`package_type=unknown`、`get()` 下载官方源、`package()` 复制数据、
   test_package 消费者视角验证。
4. 终态 result 以真实适配结果覆盖误判的 `env_unsupported` 草稿（`result` 命令 `--force`
   允许终态覆盖；校验器对语言字段仅要求 `detected_language` 枚举合法，不阻断数据包终态）。

```bash
# 复检（关键）
python3 scripts/ohc-run.py lang-preflight ldraw 20220211 --src <src> --lang other
# 适配（数据资源包模式，E255）
conan create archives/l/ldraw/20220211 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 验证

- ldraw 20220211：`--lang other` 复检 exit 0（expected=other, detected=other），
  conan create EXIT=0、test_package 消费侧 4/4 通过、W3 本地 CI EXIT=0、finish 通过。
- 与既有草稿家族（DRAFT-cl-unicode-lisp-lang-hold、DRAFT-bptree-lang-preflight-pyproject、
  DRAFT-E592-libyal-langpreflight-mixed）区分：那些是 manifest/统计误判（pyproject→mixed、
  lisp 源码不计），本候选是"纯数据/资源库无源码 → other 是正确类别，--lang other 复检
  后继续适配"。

## 适用边界 / 反例

- 适用：无任何 C/C++ 源码的纯数据/资源库（零件库、字体、数据文件、配置模板、固件资源）。
- 反例：含 `.c/.cpp`（哪怕占比低）的库仍按 c/cpp 判定，不适用本方案；`--lang other`
  只对 source_stats=0 的库正确。
- 依赖库标注 `【依赖项】` 不影响语言类别判定。

## 关系

- similar_to: DRAFT-cl-unicode-lisp-lang-hold-verification；DRAFT-bptree-lang-preflight-pyproject-tooling-false-positive
- caused_by: 无（SKILL 语言计数表不含数据扩展名）
- prerequisite_of: 数据资源包 Conan 适配（E255 家族）
- conflicts_with: 无
