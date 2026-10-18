# ECOS 2.0.10 适配记录

状态：built

验证进度：本地功能验证和完整 W3 已通过；完整 finish 第二次仅因主仓 W5 多行字段误报返回 1，未发布、未提交 PR、未获得积分。任务 14559，领取人 A1038，分支 feat/ecos-2.0.10。以真实设备、官方流水线及评审结果作为正式验收依据。

## 来源和依赖

上游 embotech/ecos v2.0.10，源码 SHA256 为 1aa24b5782b84fa33df2987510fb8f60f5f999cc2d3a5c73cfc3eb5e5f3b46af。AMD、LDL 和 SuiteSparse_config 在源码内置，无独立 Conan 依赖。包内保留 ECOS COPYING、AMD/LDL README 许可说明及 SuiteSparse_config 许可头。

## 上游测试清点

test/ 共 49 个文件。原始 CMake 未注册测试；Makefile 的 test 目标仅构建两个测试程序。ecostester 正常启用 28 项（含 EXPCONE 的 5 项），bb_test 有 10 个测试函数。上游原本注释掉的 unboundedMaxSqrt 仍未启用，不能把它计为已运行。以上是正常启用套件的 38 项，不代表源码中所有潜在测试入口均已运行。

完整文件清点：8 个 .c、33 个 .h、5 个 .m、1 个 .py、2 个 .md。逐文件哈希和分类另附 upstream-test-census.json。额外入口及未执行的具体原因：

| 入口 | 状态和技术原因 |
|---|---|
| matlab/test_box_volume.m | 未运行。调用 cvx_begin gp、cvx_solver ecos，比对另一 CVX 求解器；需要 MATLAB/CVX 与 ECOS MEX 接口，本 C 库配方不构建 MATLAB MEX，现有目标验证流程未配置 MATLAB/CVX/MEX 对照组合，不据此断言平台永久不支持它。 |
| matlab/test_inv_pos.m | 未运行。调用 CVX inv_pos 建模、ECOS MEX 和默认 CVX 求解器作对照；同上，不是已编译 C 测试的独立可执行入口。 |
| matlab/test_portfolio.m | 未运行。调用 CVX、ECOS MEX 与默认求解器比较投资组合模型；同上。 |
| matlab/RUN_ALL_TESTS.m | 未运行。是前三个 test_*.m 的 MATLAB 驱动，调用 cvx_clear、eval 与 assert，不另计独立用例。 |
| matlab/lp_netlib_lp_tests.m | 未运行。循环 10 个 UFget 数据集，需要 UFget MATLAB 数据访问函数与 ecos MEX。C 套件自带 10 个 Netlib 头文件并已运行，但不冒充这个脚本已运行，数据集重叠也不重复计分。 |
| qcml/simple_tests.py | 生成脚本未运行。使用 Python2 print/map 语法、依赖外部 QCML，作用是为 5 个模型生成 C 代码，求解调用在上游已注释。对应已生成 C 模型在 ecostester 的 5 个用例中实际执行。 |
| unboundedMaxSqrt | 未运行。上游 ecostester.c 原本注释调用，本适配保持该状态；未验证它为何被上游禁用。 |
| infeasibleProblems/infeasible2.h / test_infeasible2 | 未运行。上游 ecostester.c 未 include 此头文件，也未注册该函数；本适配未新增启用，不能计入38项通过。未验证上游不注册它的原因。 |

因此通过率仅指正常启用 C 套件 38/38，不称“全部上游语言入口 100% 通过”。辅助入口的可接受范围需由赛事评审确认。

## 修改意图

1. CMakeLists.txt：修正 project 版本 2.0.8 为源码真实版本 2.0.10；在使用安装目录变量前加载 GNUInstallDirs；修正安装 target 的头文件路径；支持静态/动态库；注册并运行上游两套测试。
2. include/ecos_bb.h、ecos_bb/ecos_bb.c、ecos_bb/ecos_bb_preproc.c：Boolean 节点状态使用 signed char，避免 ARM 的普通 char 默认为 unsigned 时 -1 哨兵提升为 255。指针和分配对象大小不变；公开结构字段的指针类型变化，使用内部字段的源代码需重新编译并核对类型。
3. test/bb_test.c：basic 模型要求第二变量 Boolean 且 >=0.5，正确最优解为 [0,1]，原预期 [0,0] 不可行。保留其他解向量断言，增加求解状态和 setup 检查，将任意测试失败传递为非零退出码。
4. test/exponential/log_ax_x.h：保留坐标误差 <1e-11 和 OPTIMAL 断言；仅将该测试的 feastol 从 1e-12 收紧为 1e-14，并输出真实误差、残差和对偶间隙。不改求解器默认容差。Windows 误差由约 8.4e-11 降至 3.7e-13。
5. Conan test_package：20 个公共 API 检查，涵盖版本、索引 ABI、LP、数据更新、不可行/无界、SOCP 与 Boolean BB。

补丁仅通过未修改的官方 ohc-run.py refresh-patch --auto 在 POSIX guest 生成；6 个补丁均通过 dry-run。Windows 官方脚本路径分隔符问题的失败记录保留，未修改官方基础设施。

## 已有直接证据与限制

Windows MinGW GCC 6.3 / 32bit x86：强制 -funsigned-char，静态 USE_LONG，38 项正常启用的上游用例通过；安装后 find_package 的消费者 20/20 通过。

OHOS 7.0.0.32 AArch64 QEMU：原始 BB5/6/7 失败，原始代码只加 -fsigned-char 后恢复；修复源码强制 -funsigned-char 后两套 CTest 通过。它不是 OHOS6 PC 真机。私有 CMake/SDK 工具有历史环境兼容改动，不能把该结果称为远端 clean CI 成功。

Conan 配方的实际 create 和消费者结果以随附原始日志为准。完整 W3 已由原样官方 finish 实际运行通过，.ci-result.json 由官方工具生成，日志与完整性哈希可核对。W3 使用实际 OHOS7 私有 profile，不是 OHOS6 运行时或远端 CI 证据。完整 finish 第一次实际退出码为 1：ConanVerifier 默认官方 OHOS6 元数据 profile 缺 Make，W5 把主仓 E219/E253/E305 的已有多行内容误报为空。随后本地改用 Ninja 已完成库构建；消费者生成配置在首次 configure 丢失 include 属性，手动重配置后 20/20 通过，已通过私有 CMake 包装入口恢复既有库搜索路径、记录目录并 sync，官方 ConanVerifier 原样命令退出码 0；默认 profile 是 OHOS6 元数据，实际运行时仍为 OHOS7。独立框架修复不混入本软件 PR。W4、远端 CI、上传、PR、评审合入和积分尚未完成。制品仓匿名 download 的 policy 错误不能证明同版本不存在，正式提交前必须完成可用制品仓访问核查。
---

**编译结束**: 2026-10-02 01:39
**构建状态**: built（完整 finish 仍未通过，不等于远端验收通过）
---

**编译结束**: 2026-10-02 02:14
**最终状态**: built


## 最终本地工作流复核

第二次原样 finish 的质量验证和完整 W3 都通过，实际退出码 1，唯一失败步骤 step5b 是主仓 W5 对 E219/E253/E305 已有多行字段的误报。未修改检查器、未删除知识条目、未手写 CI 回执。未经修改的原生 graph validate 返回 0（542 对条目，170 条既有警告）；独立框架修复草案通过 8 项回归和全量字段检查，单独保存，不混入 ECOS PR。

ConanVerifier 汇总为 PASS，但其 G4 未发现 package ID，L2/L4/L5 因无 cache 路径跳过，不能称这些子项已独立验明。实际包文件/ELF/消费者证据由原始构建日志与制品清单另提供。旧式 G0 clean-verify 固定调用 ./configure，而 ECOS 为 CMake 工程、没有 configure；其警告保留，干净应用 6 补丁与实际 CMake 构建证据见 Conan/W3 原始日志，不添加伪造 configure 或 G0 marker。

软件级 README 要求与 PF9 路径门禁冲突：新增 archives/e/ecos/README.md 被 PF9 拦截。说明置于本版本 README.md，保持 PR 全部文件在单一版本目录；该结构警告不冒充已消除。W4 结论保存为独立运行时 reports/audit-result.json，不将报告或 CI marker 放入源代码提交。

未完成的外部阶段：本人作者身份确认、Conan 鉴权访问、提交 PR、平台“去提审”关联任务14559、官方 CI、评审合入与积分入账。已确认活动配置5火种/任务，不代表已获积分。
