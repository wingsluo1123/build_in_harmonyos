## PR 信息

- **三方库名称**：hdf5
- **上游版本**：2.2.0（官方发布包；本次为 native OHOS static parallel C/HL/tools 配置）
- **上游仓库地址**：https://github.com/HDFGroup/hdf5
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（高难度挑战候选）
- **使用知识库**：E2026100906-draft-HDF2（CMake 原测试驱动的 argv 类型域、函数作用域及字面环境值保全）；私有溢出流和原生 MPI/临时文件证据。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
| --- | ---: | --- |
| 单元测试 | 0 | 不另拆统计；使用上游原 CTest 注册清单统一逐名核对 |
| 集成测试 | 3216 | 原 C/HL/tools/examples/MPI CTest 清单，含实际 Bash 注册的四组 H5SHELL 与文件内容 oracle |
| 其他测试 | 0 | C++ 与 Fortran API 明确未构建，不冒充其覆盖；无另列测试组 |
| **合计** | **3216** | 清单与 JUnit 精确名称相同、全部 run/pass、failed/not_run/disabled 均 0 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
| --- | ---: | --- | --- |
| 单元测试 | 0 | 不变 | 统一按原 CTest 注册清单核对 |
| 集成测试 | 3217 | +1 | 原 3216 全量，加实际两 rank MPI HDF5 消费者 create/write/read |
| 鸿蒙特有测试 | 1 | 新增 | 已安装生产 h5tools 溢出流：真实 HarmonyOS、owned TMPDIR、4096 字节以上写读、立即 unlink、close 与无泄漏 |
| **合计** | **3218** | **+2** | 原用例未删减、未跳过、未按 TAP ok 推断通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（说明如下）

1. `config/cmake/runExecute.cmake`：宏改为函数作用域中的 `PARSE_ARGV`，保留真实 argv、MPI launcher 与字面环境变量，避免二次插值；原退出码和错误断言保留。
2. `tools/test/h5dump/CMakeTests.cmake`：恢复原 long-double 精度用例；使用真实 `-L %.35Lg` 与原数值子串，要求实际 RC0、无 stderr，取消原 SKIP_TEST，不减少清单。`tools/test/h5ls/CMakeTests.cmake`、`tools/test/h5repack/CMakeTests.cmake`：恢复原用例注册和缺失 companion references，保留内容比较；不是跳过失败或泛化 stdout。
3. `tools/test/h5ls/expected/tqmarkfile.ls`、`tstarfile.ls`：补齐原测试需要的缺失参考文件，依据官方 fixture 结构与独立工具生成/核对，保存精确比较语义。
4. `tools/test/h5repack/expected/h5copy_extlinks_src-base.h5copy_extlinks_src.h5.ddl`、`textlinkfar-merge.textlinkfar.h5.tst`、`textlinkfar-mergeprune.textlinkfar.h5.ddl`、`textlinksrc-merge.textlinksrc.h5.tst`、`textlinksrc-mergeprune.textlinksrc.h5.ddl`、`textlinktar-merge.textlinktar.h5.tst`、`textlinktar-mergeprune.textlinktar.h5.ddl`：依据实际解析的循环/外链和独立对象标签验证更新受影响预期，不以新生成输出无条件覆盖失败 oracle。原失败和修复记录全部保留。

5. `test/test_use_cases.sh.in` 和 `bin/output_filter.sh`：原 `/tmp` 写入点改为正确加引号的 `${TMPDIR:-/tmp}`，保留原数据和过滤断言，不禁用 Bash 入口。旧 r033 的 3215/3216 失败原样保留。

十九个补丁均由官方 `refresh-patch --auto` 生成并严格重放，最终正式补丁在 fresh native Conan 中完整执行。不存在手工假 patch、禁用测试或减少分母。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

已有完整上游测试，额外增加 installed-package 消费者和独立鸿蒙测试，不替代上游清单。新增文件：`test_package/main.c`（真实两 rank MPI 数据文件）；`test_package/overflow_stream.c`（调用安装生产工具库并验证鸿蒙私有流生命周期）。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：3216/3216（100%）
- 新增测试用例通过率：2/2（100%）

当前 fresh run `hdf5-official-objcopy-review-220-20261011-r760` 从原 finish W3 与 native `conan create` 实际 RC0 完成，自动生成原 `.ci-result.json`；原3216/3216零失败/跳过/disabled，MPI 消费者1/1、鸿蒙1/1。被验证 HEAD 为 `348acecc259c9bd56410f1aef982e694ef1412ad`，候选 tree 为 `5b09dcbf222a9b74fab271797eff95b2270c6040`；验证后的增量仅报告和配对知识。JUnit SHA-256 `bbbaa4d1589df07fc3d0f977f2e63a0d6599c936eae753f9ab504f83a494c113`；完整日志 `e7ef324ce9711f785b6a8131fbff0267889759a21503843a09ee82dfcdaf0497`；独立 observed `f83385995f1ced4af4f9b32cc664505d0d8e40594d4ef93b1e7decf937038197`。逐项原名称/JUnit核对、唯一launch、完整WAL/receipt、release/postrelease和进程0均已独立验证。旧r605/r038是历史结果，不能认证本次新配方；旧3212范围不含四组shell，不能替代3216。

完整实际代码检视193189036指出消费者 generate() 忽略已配置的 objcopy，仅要求 PATH 查找。现优先消费 tools.build:compiler_executables 的 objcopy，缺省才按原 PATH 寻找；溢出流注释纠正为4096字节，原断言不变。Conan默认构建环境的质疑已由官方2.29.1源码与真实契约澄清，未据此重复修改 build()。

本次针对当前 HEAD 平台 build96239 的真实 `H5SHELL-test_flush_refresh` 超时修复：只在 OHOS 将原 POSIX shell 测试入口绑定到真实 `/system/bin/sh`；其他 OS 保留原 Bash。源码、3216项清单、原 IPC/文件比较断言及超时均不修改。CMakeCache真实回读 `SH_PROGRAM=/system/bin/sh`，同一HMDFS worker型路径中全部原测试通过且没有 getcwd/chdir 错误。原Bash失败保留，尚不能确定其精确内核/加载器根因；不将可执行的shell选择修复宣称为系统服务修复。新提交仍须其完整HEAD的平台Review和CI，不将本地通过冒充平台PASS。

针对当前 HEAD 的 AI 检视 192997664：生产 `h5tools_task_tmpfile` 移除仅围住函数体的 `__OHOS__` 条件，统一使用原 POSIX `mkstemp`、立即 `unlink` 和 `fdopen`。未设置或空 TMPDIR 保留原 `tmpfile` fallback；非法相对路径及不可创建的绝对路径保持失败闭锁，不退回未知目录。官方补丁19/19实际重放，宿主四项定向控制与上述同一新真机全量均通过；不点击 resolve 代替修复，也不沿用 r036 来认证新代码。新提交后仍须回读其完整 HEAD 的最新检视和平台 CI。

r035 原3216项均通过，但鸿蒙临时文件的真实 `st_uid==getuid()` 断言失败，整个事务保留为 FAIL。此次只修 `test_package/conanfile.py` 的任务私有临时目录选择：验证无符号链接、真实进程归属及访问权限，在 POSIX 根独占创建0700子目录，保留原 C 的 UID、4096字节、unlink/nlink、完整读回与 EOF 断言；不修改系统账户或权限。平台旧请求104577/build91281是实际 flush-refresh 超时失败，其精确根因未证明；r036本地通过不能替代修复提交后完整当前 HEAD 的平台 CI。

## 补充说明

- 关联 Issue：#3880
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/hdf5-2.2.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 高难候选：HD4（依赖链庞大、全量测试校验成本极高）。技术壁垒是 Conan MPI 使用要求、实际两进程原测试、工具私有溢出流和循环外链独立 oracle 的联合可复现校验，不仅测试数量多。HD1/HD2/HD3 未匹配，逐项证据另行保留。
- 知识为可跨 CMake 测试驱动复用的参数类型域和二次展开机制，不是软件介绍；同 stem KV/MD 已提交候选，包含真实反例、修复、验证、适用/不适用与安全边界。现有 PostgreSQL make/shell 引号条目明确不适用 CMake；本次增量是函数 PARSE_ARGV、多值 PROGRAM/ARGS/EMULATOR 以及显式父作用域结果回传，不重复申报保留脚本 stem 碰撞根因。
- 严格范围：static parallel C/HL/tools；C++/Fortran APIs 不构建。依赖为已发布 mpich/5.0.1.2、zlib/1.3.2.1、libaec/1.1.7，不涉及 HDF5 上游没有要求的 BLAS/LAPACK。不宣称 FEniCS 整栈或高难候选已获委员会批准。
- 合并后需要走正式 `/release` 发布流程；PR 校验不上传，不自动合并。
- 最新完整实际检视193205665所指元数据已修正：十九项补丁注释、r038/r605历史范围及被断开的原MPI消费者句子。配方 AST 与原运行行为不变，补丁和测试源原字节不改；原3216/3216证据不重写，新完整HEAD的平台CI仍独立验收。Windows建议超出本配方明确限定的Linux/OHOS范围，不声称已做Windows适配或将建议当平台批准。


新正式事务 `hdf5-official-private-build-220-20261014-standard-marker-r193` 使用真实进程UID所有、规范非链接0700私有POSIX目录承载CMake构建与generators，最终安装仍为实际Conan包根。原ctest并行度保持1；同轮原3216个唯一测试、全部四组原Shell测试零失败/跳过，真实双rank MPI消费者1项与原生产溢出场景1项通过。鸿蒙C源SHA-256保持72f434731a9a28dd7ff10953ee636656059b6f354bbc75fd42d8f9666c9e80a5，只移入现行harmony_tests结构并在原测试成功后输出标准成功标记。正式Finish自动生成W3回执，唯一launch、完整回执链、进程归零及release/postrelease独立核验。测试输入tree `e99b8ceab3094c99933182b33f65853cf34b5f24`，日志SHA-256 `ec3d1a3aa59a5f38dd9ee6c58f7d43bef6cea044282f7738b43ec55c31c35f23`。保留此前超时、L0结构失败与L1成功标记缺失的真实失败；此结果不代表新HEAD平台CI、提审或制品发布已完成。
