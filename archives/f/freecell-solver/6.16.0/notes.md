# freecell-solver 6.16.0 鸿蒙 PC 适配笔记

上游: <https://fc-solve.shlomifish.org/>
版本: 6.16.0
目标: HarmonyOS PC（aarch64，ohos-sdk clang + libc++）

## 一、适配结论

产物（install 树）：

- `lib/libfreecell-solver.so`（170,368 B）——求解器核心 API：
  `fcs_user.h` / `fcs_move.h` / `fcs_enums.h` 等 10 个公共头（共 1,052 行），
  `lib/pkgconfig/libfreecell-solver.pc`（Version 6.16.0，
  `Libs: -L${libdir} -lfreecell-solver`，`Libs.private: -lm`）；
- `bin/` 12 个文件：
  - 7 个 ELF 工具：`fc-solve`、`freecell-solver-range-parallel-solve`、
    `freecell-solver-fc-pro-range-solve`、`freecell-solver-multi-thread-solve`、
    `dbm-fc-solver`、`depth-dbm-fc-solver`、
    `pi-make-microsoft-freecell-board`；
  - 5 个 Python 棋盘助手：`fc_solve_find_index_s2ints.py`、
    `find-freecell-deal-index.py`、`make_pysol_freecell_board.py`、
    `transpose-freecell-board.py`、`gen-multiple-pysol-layouts`；
- `share/man/man6/` 8 页 man、`share/doc/freecell-solver/` 文档、
  `share/freecell-solver/`（presetrc + presets/*.sh 预设库）；
- `licenses/COPYING.txt`（MIT）。

ELF 布局：`libfreecell-solver.so` 为单文件无版本 `.so`，`DT_SONAME` 为裸
基名 `libfreecell-solver.so`，`RUNPATH=$ORIGIN:$ORIGIN/../lib`；
可执行文件为 PIE（DYN AArch64）、带 `GNU_RELRO`、`GNU_STACK` 为 RW、
段对齐 4K。`fc-solve --version` 退出码 0；对标准 Microsoft deal #24 的
CLI 端到端求解输出 "This game is solveable. Total number of states checked
is 137."，退出码 0。

平台适配 **7 个补丁**（`patch_type: portability`，均为能力探测/去 CPAN
依赖/单目标文件级小改，不含平台条件编译宏，R8 合规）：

1. **0001** `CMakeLists.txt`：删除 `Moo` CPAN 硬检查（0003 已把该模块
   改成纯 Perl 类）；python3 模块（`six`/`pysol_cards`/`cffi`/
   `freecell_solver`）由 FATAL_ERROR 降为 WARNING（只影响可选 `boards`
   目标与 Perl 测试套件）；新增 `FCS_SKIP_PERL_TEST_HARNESS` 开关包住
   `perl_run_tests` 的 `ADD_TEST`。
2. **0002** `t/CMakeLists.txt`：cmocka 由 `pkg_check_modules(cmocka)`
   改为 `FIND_PACKAGE(cmocka CONFIG REQUIRED)` + `cmocka::cmocka`
   （OHOS 无 cmocka 的 pkg-config 条目）；新增
   `FCS_SKIP_PERL_GENERATED_TESTS` 包住三条 perl 生成 .t 脚本的
   `GEN_INDIVIDUAL_TESTS` 调用；把上游 5 个 C 单测程序逐条 `ADD_TEST`
   （上游原本只注册 Perl harness；测试代码零改动）。
3. **0003** `scripts/gen-c-lookup-files.pl`：`Moo` 类改为 blessed-hash
   纯 Perl 实现（只用到只读访问器与两个懒计算值），生成结果不变。
4. **0004** `scripts/gen-presets.pl`：去掉 Template Toolkit，固定模板块
   用直接正则替换（未知占位符仍按 STRICT 语义 die）。
5. **0005** `t/generate-card-tests.pl`：去掉 Template Toolkit，直接输出
   与 `card-test-render.c.tt` / `card-test-parse.c.tt` 相同的断言序列
   （.tt 模板保留供上游参考）。
6. **0006** `cmake/Shlomif_Common.cmake`：`FIND_LIBRARY(m)` 追加
   `HINTS ${CMAKE_C_IMPLICIT_LINK_DIRECTORIES}`（编译器 sysroot 不在
   CMake 默认搜索前缀；OHOS/musl 的 `libm.a` 为空归档、数学例程在
   `libc.so`，链接干净且保留上游 `-lm` 契约）。
7. **0007** `cmake/rinutils_bootstrap.cmake`：目录已存在时不再执行
   `git submodule update --init`（解包 tarball 不是 git 检出，该命令
   必败）；配方已把 rinutils 0.6.0 解到 `fc-solve/source/rinutils`。

## 二、源码与依赖

- 源码：SourceForge 官方发布包
  `freecell-solver-6.16.0.tar.xz`（443,572 B），SHA-256
  `71b8882e68f1be62529069018d0c732b75078669077c96348279575849f34313`。
- 发布 tarball 不含 rinutils 子模块头文件，CMake 的
  `rinutils_bootstrap.cmake` 期望 `<src>/rinutils/rinutils/include`；
  配方在 `source()` 里额外取 rinutils 0.6.0（16,053 B，SHA-256
  `81966e7f73a9a8e095dd06c159cfb8dd0da2b78942ba83b323d7ff59f74800cf`）
  解到 `fc-solve/source/rinutils`，构建期零网络。
- 依赖全部逐条对上游 CMakeLists 核实：
  - `gperf/3.3`（tool_requires）——`FIND_PROGRAM(_GPERF)` 缺失即
    `FATAL_ERROR`；
  - `libpath-tiny-perl/0.118`（tool_requires）——6 个 perl 生成器
    全部 `use Path::Tiny`，OHOS Perl 无 CPAN；`PERL5LIB` 指向
    `lib/perl5`；
  - `cmocka/2.0.2`（test_requires）——`t/` 下 5 个 C 单测。

## 三、构建配置

- 构建目录：`cmake.configure(build_script_folder="fc-solve/source")`，
  tarball 内工程根即仓库的 `fc-solve/source` 子目录。
- 平台：构建目录内 `Platform/HarmonyOS.cmake` 垫片
  （`include(Platform/Linux)`，E140/fluidsynth 先例），保留原生
  HarmonyOS 平台名而不是伪装 Linux 交叉构建。
- 共享库：`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（HMDFS 用户卷
  拒绝 `symlink()`，E330），单文件无版本 `.so` + 裸 DT_SONAME。
- RPATH：`DISABLE_APPLYING_RPATH=ON` 阻止上游把
  `CMAKE_INSTALL_FULL_LIBDIR` 烤进可执行文件；
  `CMAKE_INSTALL_RPATH=$ORIGIN:$ORIGIN/../lib` 让安装后的 CLI 就地
  找到库（L2 冒烟测试直接执行包内二进制）。
- 链接：`CMAKE_{EXE,SHARED}_LINKER_FLAGS_INIT=-Wl,-z,max-page-size=0x1000`
  （OHOS 加载器 4K 段布局）。
- 签名：`cmake install()` 重写 RUNPATH 会让 OHOS 构建期 `.codesign`
  失效（加载器报 Permission denied）；`package()` 对安装树内全部
  ELF 执行 `llvm-objcopy --remove-section .codesign` +
  `binary-sign-tool sign -selfSign 1`，本包共重签 **8 个** ELF
  （7 个 bin 工具 + 1 个共享库）。
- 环境：`TMPDIR=$HOME/tmp`（设备 `/tmp` 只读；`Path::Tiny->tempdir`
  与 pod2man 包装器按 TMPDIR 落盘）。

## 四、测试契约

上游在默认配置下只注册一条 CTest（Perl `run-tests.pl` harness），
其依赖的 CPAN 模块（`Task::FreecellSolver::Testing`、
`Test::Differences` 等）在 OHOS 上不可用。适配不修改任何测试代码，
而是把同一批上游 C 程序（cmocka）逐条注册为 CTest 用例（补丁 0002），
`conan create` 内实跑 `ctest --output-on-failure --no-tests=error`：

| CTest 用例 | 上游源文件 | 结果 |
| --- | --- | --- |
| `card-test-render` | `t/card-test-render.c.tt`（经 0005 生成） | Passed |
| `card-test-parse` | `t/card-test-parse.c.tt`（经 0005 生成） | Passed |
| `bit-reader-and-writer` | `t/bit-reader-and-writer-test.c` | Passed |
| `delta-states-debondt` | `t/debondt-delta-states-test.c` | Passed |
| `dbm-kaztree-compare-records` | `t/dbm-kaztree-compare-records-test.c` | Passed |

`FCS_ENABLE_DBM_SOLVER` 默认 ON 时 `DEBONDT_DELTA_STATES` 控制构建
`delta-states-debondt-test` 还是 `delta-states-test`（二选一）；配方
断言 `<build>/t` 下两个 delta 程序中恰有一个存在，避免注册随上游开关
漂移。

消费者测试（`test_package/`，CMakeDeps + VirtualRunEnv）：

- `test_freecell_solver` 13 项 `TEST PASS`（`TEST SUMMARY: 13/13
  passed`，失败退出码 1）：实例分配、库版本号、`freecell` 预设、
  未知预设返回 `FCS_PRESET_CODE_NOT_FOUND`、set_game 标准 Freecell
  参数、deal #24 求解（`FCS_STATE_WAS_SOLVED`）、迭代数 > 0、
  剩余步数 > 0、逐条重放步数与 `get_moves_left` 一致、无 NULL 步、
  `move_to_string` 非空、`get_next_move` 以 1 终止、完成态
  `Foundations: H-K C-K D-K S-K`；
- 安装契约 3/3：`include/freecell-solver/fcs_user.h`、
  `lib/pkgconfig/libfreecell-solver.pc`、以及 pc 文件中的
  `-lfreecell-solver` 链接行。

真机 `scripts/ohc-run.py conan-verify freecell-solver 6.16.0
--profile ohos-aarch64-full`：Verdict **PASS**（G0–G3 全 PASS；G4 报
「无法找到程序包 ID」、L2/L4/L5 因无 cache 路径跳过——conan 2.29.1
本地缓存 JSON 键与校验器解析路径不兼容，analitza 报告同款；等价项
已在真机手工取证）。`package_id=01d92cf349a0dd98ff915f4bd99a04430
171517f`。

## 五、问题与解法

1. **rinutils 子模块缺失**：发布 tarball 不含 `rinutils` 头文件，
   bootstrap 在目录存在时会跑 `git submodule update --init`，解包树
   不是 git 仓库 → 失败。解法：`source()` 预置 rinutils 0.6.0 到
   `fc-solve/source/rinutils`，补丁 0007 删除 submodule 分支。
2. **OHOS Perl 无 CPAN**：`Moo`（gen-c-lookup）、Template（gen-presets、
   generate-card-tests）、`Path::Tiny`（6 个生成器）——前两者改写为
   纯 Perl（0003/0004/0005），后者用 `libpath-tiny-perl/0.118` +
   `PERL5LIB` 提供；`t/` 的 Perl 测试脚本以 `FCS_SKIP_PERL_GENERATED_TESTS`
   关闭，改为直接注册 C 单测（0002）。
3. **cmocka 无 pkg-config 条目**：`pkg_check_modules(cmocka REQUIRED)`
   在 OHOS 上找不到 → `FIND_PACKAGE(cmocka CONFIG REQUIRED)` 消费
   CMakeDeps 导出的 `cmocka::cmocka`（0002）。
4. **libm 在编译器 sysroot**：`FIND_LIBRARY(m)` 失败 → 追加
   `HINTS ${CMAKE_C_IMPLICIT_LINK_DIRECTORIES}`（0006）。
5. **HMDFS 禁 symlink / 签名失效**：`CMAKE_PLATFORM_NO_VERSIONED_SONAME`
   + 安装后全树重签（E330/E077）。
6. **消费者完成态断言**：`freecell_solver_user_current_state_stringify`
   的显示模式（`parseable_output=0`）对上行做 16 列对齐并省略
   `Foundations:` 前缀；消费者断言完成态应传 `parseable_output=1`，
   得到规范形式 `Foundations: H-K C-K D-K S-K`。

## 六、已知限制

- `boards` 目标与上游 Perl 测试 harness 未启用（依赖 CPAN/PyPI 模块，
  OHOS 不可用）；覆盖由 5 个上游 C 单测 + 13 项消费者用例承担。
- 5 个 Python 棋盘助手随包安装，其运行期依赖（`pysol_cards` 等）不在
  包内，属上游可选工具，不影响库与 CLI 核心功能。
