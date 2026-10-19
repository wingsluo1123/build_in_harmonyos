# E429-draft-PG82：提取型 vendor 源码的 CPU 特性配置与函数闭包核验

状态：路径 B 候选草稿，正式编号与入库由主编确认。适用范围是发布源码包含冻结能力配置、架构分支和源代码提取过程的 C/C++ 库；不专属于 pglast 或 Python。

## 现象与输入

输入：官方 release/sdist、目标编译器/最低 ISA、真实失败日志、被引用的 capability header 和被保留的函数实现。输出：可说明理由的分支选择、可重现构建参数和真实功能回归证据。

案例：pglast 8.2 随包 libpg_query 在 OHOS AArch64 clang15 编译 src_port_pg_popcount_aarch64.c 时，arm_sve.h 报 `SVE support not enabled`。这是受控本地构建失败，不是虚构的远端 CI 构建编号。

## 根因定位

1. pg_config.h 定义 USE_SVE_POPCNT_WITH_RUNTIME_CHECK。
2. port/pg_bitutils.h 根据 __aarch64__ 与 __ARM_NEON 定义 POPCNT_AARCH64。
3. 提取后的 pg_popcount_aarch64.c 包含 SVE/NEON 分支的声明和调用，却未保留未使用的 helper 完整函数体；不能只补 `-march=...+sve` 就认定源码闭包正确。
4. pg_bitutils.c 仍保留 !POPCNT_AARCH64 的完整通用算法。

关键增量是同时核验「冻结特性声明—编译器架构宏—提取后的实现闭包」，区分 ISA 未启用与分支代码已被提取掉；不是仅凭报错补一个 SIMD 开关。

## 诊断与修复步骤

1. 核验官方源包哈希，保留失败命令和原始日志；定位报错 include。
2. 追溯条件宏的产生位置，检查是否来自当前目标 configure，或来自 release 中的冻结配置。
3. 对选中分支检查声明、调用、定义是否完整，并检查 fallback 的真实实现，排除 stub。
4. 优先在可重生成完整 vendor 源码的场景重新检测能力。对于现有提取型源包，只有完整通用实现已证实存在时，才在 build 私有 CFLAGS 使用 `-U__ARM_NEON` 让本案例选择通用路径。
5. 不编辑生成的 pg_config.h、不注入 __OHOS__，不通过全局提高 ISA 掩盖源代码提取缺口。
6. 检查最终 ELF 与功能回归：干净 Conan build、原版 SQL/PLpgSQL/AST/扫描/指纹/格式化测试、安装包消费以及载荷负向测试。

## 实测证据

- 官方 pglast 8.2 sdist SHA256：e5d64c29281ecd9d001b5521b807be0e66375f356cbefda19c337c2253765496。
- 本地负例：首次无兼容参数构建报 SVE support not enabled；构建失败不会标为成功。
- 本地修复后：reports/validation-summary.md、native-validation-summary.json（完整图与JUnit本地保全）（原始日志保留本地，摘要列 SHA256），2405 passed / 14 ty skips / 1 上游 xfail / 0 failed；Windows typehints 28/28 作为可选工具替代证据，不冒充目标端成功。
- 安装包消费者 8/8；重定位 8/8；移走载荷 import 失败，恢复 8/8。诊断重复运行不重复计算用例数。
- reports/cpu-branch-red-green.json 保留原目标无回退参数的 SVE 编译失败及 portable 编译/链接/执行成功；cpu_fallback_probe.c 对 32/64 位 popcount 分别检查 6 组独立字面量（零、单bit、最高bit、全1、交替位、混合hex），12 个检查均通过。这是诊断实验，未加到上游测试计数。
- 配套 CPU 分支诊断见本库 conanfile.py/notes.md；无修改生成源码/配置/上游测试。

## 查重与差异

检索范围：knowledge/graph、knowledge/doc、knowledge/drafts，以及全局知识库。关键词：SVE support not enabled、USE_SVE_POPCNT_WITH_RUNTIME_CHECK、POPCNT_AARCH64、pg_popcount_aarch64、ARM_NEON。

工具 draft-review 的最高相似项为 E016（reconfigure-no-asm），分数 0.23，建议 create；E016 处理实际汇编指令不受支持或 configure 误识架构，未覆盖冻结 feature header 与提取后函数定义缺失的联合核验。该自动结论只作辅助，最终由主编确认。

相近草稿 DRAFT-11327-upstream-dist-drops-referenced-header-non-x86-path 处理 rnnoise 的非 x86 分支引用缺失头文件，修复为补回头文件；其通用路径同样依赖缺失头文件，因此不能应用本案的「已确认完整 portable fallback」方案。本案既有头均存在，问题来自冻结能力配置与函数提取闭包。相近 SIMD/平台分支知识仍应交主编人工确认，不将文字检索无精确匹配当作官方已批准独创。

最新 main e44a437b752d912829371f62967ab03766dbdbb3 另有 DRAFT-psimd-0.0-simd-backend-activation-evidence：它要求证明 SIMD 后端实际激活，本案要求证明被冻结配置误选的分支不完整、且完整 portable fallback 可用，方向和输入条件不同。本案不宣称 SIMD 已激活或性能等价；popcount 诊断将测试与实现分开编译且未用 LTO，避免编译器对跨单元调用做常量替换。

## 局限与反例

- __ARM_NEON 是编译器内建能力宏。一般完整项目不应随意取消；本命令只适用于已经核验 portable 分支与函数闭包的案例，不能自动推广为所有 ARM 适配的默认参数。
- 通用分支也缺代码、依赖硬件 intrinsics 或没有等价算法时不能使用此方案，应修复生成/提取流程或补完整源码。
- 完整 PostgreSQL 构建应优先运行其能力检测；不要照搬提取库的处理。
- 这不证明性能与 SIMD 分支等价，仅验证功能回归；性能敏感场景另行比较。
- ty/SQLite/mypy 的测试环境问题与 CPU 分支修复分开报告，不作为额外独立积分申报。

## 申报

申请路径 A+B 的知识库扩展，贡献创新 10 分候选；类别资格、新知识通用性、正式定号、入库与积分以官方审核为准。草稿必须随 pglast 原子 PR 提交，不能修改正式图谱或自行晋升。

## 2026-10-17 当前输入复验

当前main ad0c1a73eaeeb0807aebf150606a75a9ee950bd0再次查重，E016=0.23、E1761=0.18、E601=0.17，工具create仅辅助。E1761处理测试注入的同名OpenSSL符号，E601处理发行包缺失头文件，仍不覆盖本候选的冻结能力配置与提取函数闭包。官方Verifier本轮0；原版2405通过/14跳过/1预期失败、消费者8/8、独立HarmonyOS签名机制1/1，源与原文哈希见本库reports/native-validation-summary.json。该平台测试为交付验证，不另申报创新；本轮正式W3/远端门禁另核验，旧回执不继承。
