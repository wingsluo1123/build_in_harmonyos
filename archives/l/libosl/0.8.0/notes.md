# libosl 0.8.0 适配笔记

## 基本信息

- 软件：libosl（OpenShogiLib，将棋对局程序库）
- 版本：0.8.0
- 上游性质：C++（C++11）手写 GNU Makefile 项目（core/std/full 三个库 + 三套测试）
- 许可证：BSD-3-Clause
- 源码：Debian 官方池 `libosl_0.8.0.orig.tar.gz`（上游原站点已下线，这是 0.8.0 唯一权威来源；Ubuntu 池为逐字节相同的副本）
- sha256：`96c888da70a7031468cf20f7762b667a7dd39ee33de95a085b09d0cf3875c1c0`（Debian .dsc、PureOS、Ubuntu Launchpad 三方一致）

## 关键澄清：两个 libosl

`libosl` 有重名项目：德国马普所的对象存储层（object storage layer，最新仅 0.2.0，
依赖 lopsub）与本任务的 **OpenShogiLib**（将棋库，Debian `libosl 0.8.0-4`，
描述为 library for Shogi playing programs）。经 Debian copyright（Upstream-Name:
OpenShogiLib）与二进制依赖（libboost-*）确认，0.8.0 是后者。配方按 OpenShogiLib 编写。

## 编译环境

- 构建系统：makefile（`make -C core/osl`、`std/osl`、`full/osl` 产出三个静态库）
- 编译器：clang/clang++（HMBS 注入的 `tools.build:compiler_executables`）
- C++ 标准：`-std=c++14`（Boost 1.84 头文件要求至少 C++14；C++17 已移除上游
  `openingBook.h`/`kanjiMove.cc` 所用的 `std::unary_function/binary_function`，
  故取仍保留它们的最高标准；上游默认 C++11）
- 架构选项：`CPUOPTION=-march=armv8-a`（替代上游 `-march=native`，保证确定性）
- 状态：built（待真机验证）

## 编译步骤

```bash
export OSL_HOME=<源码根>
make -C core/osl CXX="<cxx> -std=c++14 -stdlib=libc++ -fPIC -DOSL_SMP -DOSL_NO_SSE -DBOOST_ALL_NO_LIB -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE -I<boost…>" \
  GXX="<同CXX>" INCLUDES="-I.. -I<boost…>" \
  CPUOPTION="-march=armv8-a" ARC="<ar> cru" RANLIB="<ranlib>" LDFLAGS="-L<boost…>" -j1
# std/osl、full/osl 同理；测试：
make -C core/test <同上变量> -j1   # 产出 testAll
# 运行：
(cd core/test && ./testAll --report_level=detailed --log_level=test_suite --catch_system_errors=yes)
```

> 说明：`GXX`/`INCLUDES` 覆盖 `makefile.conf` 的 `.deps/-MM` 依赖生成步骤，
> 否则该步骤沿用上游 `c++ -std=c++11 -I..`（无 Boost 头路径），每个 TU 都会报
> `boost/... file not found`（真机首轮日志）；`INCLUDES` 经命令行传入后，
> 各测试 Makefile 的 `INCLUDES += …` 仍会正常追加。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `quadInt.h`/`tripleInt.h` 在 `__clang__` 下无条件 `#include <emmintrin.h>`，aarch64 无此头文件；且即使头文件守卫生效，非 x86 仍可能因构建侧定义的 `OSL_USE_SSE` 走进 `__builtin_ia32_*` 分支（aarch64 clang 无此内建函数，`bits/tables.o` 报错） | 上游假设 clang == x86 clang，且 `OSL_USE_SSE` 可被构建侧强制打开 | 0001 补丁：include 限制在 `__i386__/__x86_64__`，quadInt.h 追加非 x86 架构门控 `#undef OSL_USE_SSE`；tripleInt.h 同款门控放在配方 `source()` 做（其 0.8.0 警告块与后世上游文本不同，补丁 hunk 在真机打不上）；配方另传 `-DOSL_NO_SSE`；均无 `__OHOS__` 宏 |
| 2 | 测试链接 `-lboost_unit_test_framework`，OHOS 无该编译库（b2 与 OHOS 不兼容 E068） | OHOS Boost 只发 headers | 0002/0003 (0002 rev2: BOOST_TEST_NO_MAIN + BOOST_TEST_ALTERNATIVE_INIT_API custom main + bool init hook，按 Boost 1.84 单头文档模式；旧 test_suite*(int,char**) 无宏写法与默认 runner 重载失配，启动即崩) 补丁：testAll.cc 改用 `<boost/test/included/unit_test.hpp>` 头文件入口，Makefile 去掉 `-l`（array-hash 0.7.2 先例；577 个用例源码零改动） |
| 3 | `oslfsck` 工具需要 lopsub（`lopsubgen` 生成器），制品仓无此包 | 依赖缺失 | 只打包三个静态库，不构建 `oslfsck`；库功能不受影响（notes 如实声明） |
| 4 | 上游站点下线，无法从官网取包 | 原站关停 | conandata 采用 Debian/Ubuntu 官方池镜像列表（同字节、同 sha256），官方原始 URL 概念对应 Debian 池 |
| 5 | 真机 `bits/boardTable.o` 编译失败：`basic_type.h:1355 reference to 'hash' is ambiguous`（候选 `std::hash`） | 上游在 `namespace std` 内先冗余前向声明 `template <typename T> struct hash;` 再特化；libc++ 已经由 `<functional>` 声明过主模板，模板名查找出现二义性（libstdc++ 容忍，libc++ 报错） | 0004 补丁：两处（`basic_type.h` 的 `osl::Move`、`hashKey.h` 的 `osl::HashKey/BoardKey`）补 `#include <functional>` 并删掉冗余前向声明，直接特化；无 `__OHOS__` 宏，纯标准库可移植修正 |
| 6 | 真机 `.deps/-MM` 步骤大量 `boost/... file not found`（`c++ -std=c++11 -I..`） | 配方只覆盖了 `CXX`，`makefile.conf` 的依赖生成用 `GXX`+`CXX_CPP_FLAGS(INCLUDES)`，仍走上游默认值（无 Boost 头路径） | 配方同步传入 `GXX="<同CXX>"` 与 `INCLUDES="-I.. -I<boost…>"`；测试 Makefile 的 `INCLUDES +=` 仍正常追加 |
| 7 | `openingBook.h`/`kanjiMove.cc` 使用 `std::unary_function/binary_function`（C++17 已移除） | 上游 C++11 时代代码；配方原用 `-std=c++17` 会在 core/std 模块编译失败 | 构建标准降为 `-std=c++14`（Boost 1.84 最低要求即 C++14，且仍保留这两个适配器；`sample/` 的 `random_shuffle` 不参与构建） |
| 8 | 真机 `bits/binaryIO.o` 编译失败：`boost/core/detail/sp_thread_sleep.hpp:73 use of undeclared identifier 'pthread_setcancelstate'`（经 `yield_k.hpp→yield_primitives.hpp` 链） | OHOS musl 无 POSIX 线程取消 API（E127，与 Android 同）；Boost 1.84 上游仅对 `__ANDROID__` 免除该调用，OHOS 仍走到 `pthread_setcancelstate` 分支 | 配方 `cxxflags` 加 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（boost/1.84.0 系列组件包同款能力宏，无平台宏），`-I` 顺序把已带 `0001-ohos-pthread-cancel-fix.patch` 的 serialization/iostreams/system/date_time 放前、未带补丁的 filesystem 放后；`package_info.defines` 与 test_package `preprocessor_definitions` 同步透出，保证消费者 TU 同样走 nanosleep 分支 |
| 9 | 真机 `bits/tables.o` 编译失败：`quadInt.h:96/104 use of undeclared identifier '__builtin_ia32_paddd128/psubd128'`（头文件已打印 `QuadInt without SSE` 警告，说明自带 arch 判断已走标量，但某处仍定义了 `OSL_USE_SSE` 使 `#if OSL_USE_SSE` 运算符分支取 SSE 路径）；随后补丁在真机报 `source file is different - full/osl/tripleInt.h` 打不上 | 构建侧（makefile/命令行）强制的 `OSL_USE_SSE` 覆盖了头文件按架构的自动判断；aarch64 clang 根本不提供 `__builtin_ia32_*` 内建函数；且 0.8.0 的 tripleInt.h 警告块与后世上游文本不同，按后世文本写的补丁 hunk 上下文失配 | 0001 补丁给 quadInt.h 加非 x86 架构门控 `#undef OSL_USE_SSE`（该 hunk 在真机可应用），tripleInt.h 同款门控改在配方 `source()` 以 `namespace osl` 为版本无关锚点幂等插入（替代打不上的补丁 hunk）；配方 `cxxflags` 追加 `-DOSL_NO_SSE`；纯架构探测，无平台宏；与上轮纯补丁策略不同 |
| 10 | 真机编译中途 `Connection to 47.122.125.180 closed by remote host`，无编译器错误行；`tar: time stamp ... is in the future` 仅为 0.1s 时钟偏移警告 | 受限真机峰值内存/时长不足：`makefile.conf` 默认 `RELEASE_CXX_OPTFLAGS=-O3 -DNDEBUG $(CPUOPTION) -g`，`-O3` 重度内联 + `-g` 使每个 clang TU 与三个 testAll 链接的峰值内存/产物翻倍，单并发仍在中途掉线 | 命令行覆盖 `RELEASE_CXX_OPTFLAGS="-O2 -DNDEBUG -march=armv8-a"`（去 `-g`、降一档优化；`-DNDEBUG`/`-march` 保留，不改测试口径）+ `build()` 起始低内存加固（任务私有 TMPDIR 确保存在；`MAKEFLAGS/XZ_OPT/GZIP/CMAKE_BUILD_PARALLEL_LEVEL` 仅 setdefault 单作业/单线程，不覆盖 HMBS 注入值；libdrpm/serf 先例的适配） |

| 11 | full/osl compile fail: game_playing/weightTracer.cc:200 boost::next missing (clang suggests std::next) | upstream used boost::next from boost/next_prior.hpp; Boost 1.84 headers no longer pull it transitively | recipe source() version-independent scan: boost::next->std::next, boost::prior->std::prev with <iterator> include; no __OHOS__ macro |

| 12 | core/test/testAll.cc compile fail: redefinition of main + init_unit_test bool() vs test_suite*(int,char**) mismatch under <boost/test/included/unit_test.hpp> (Boost 1.84) | included header predefines main and only accepts the new init signature; old DYN_LINK-era custom main/init no longer matches | rewrite 0002 patch: BOOST_TEST_MODULE + BOOST_TEST_NO_MAIN custom main, port init hook, filter --long in main before forwarding to unit_test_main; verified all 5 patches apply sequentially via git apply |

| 13 | core/test/move_generator/escapeMoves.t.cc compile fail: boost/progress.hpp + boost/timer.hpp hard #error deprecated in Boost 1.84 | upstream test TU includes <boost/progress.hpp>; Boost 1.84 deprecates it with #error unless BOOST_TIMER_ENABLE_DEPRECATED is defined | recipe cxxflags add -DBOOST_TIMER_ENABLE_DEPRECATED (upstream-sanctioned suppression named in the header message); no test source change, no scope change |
| 14 | core/test/testAll link fail: undefined BZ2_bzCompress/Decompress*(Init/End) from libboost_iostreams.a | boost1.84-iostreams component package compiles bzip2.cpp/zlib.cpp/gzip.cpp backends in (lzma/zstd excluded); raw-make test link only passed -lboost_* so codec symbols unresolved | recipe requires bzip2/1.0.8 + zlib/1.3.1 (both published), codec libdirs appended to LDFLAGS, `LDLIBS="-lbz2 -lz -lpthread"` fed to test Makefiles via their existing `LOADLIBES += ... $(LDLIBS)` line (after Boost libs; -lpthread 系补回被命令行覆盖的 makefile.conf `LDLIBS += -lpthread` 默认值，OSL_SMP/std::thread 与 Boost.Test 运行时依赖); .a builds unaffected; no test skipped |

| 15 | 真机 testAll[core/full] exit=139（SIGSEGV、无 Running 行）、testAll[std] exit=201（test_failure 却无 Running 行，解析矛盾） | 0002 旧写法只定义 BOOST_TEST_NO_MAIN、用废弃 test_suite*(int,char**) init 且无 BOOST_TEST_ALTERNATIVE_INIT_API，与 Boost 1.84 单头文档模式（要求双宏 + bool init）失配，默认 runner 重载错位导致启动即崩；另命令行 LDLIBS="-lbz2 -lz" 覆盖掉了 makefile.conf 的 -lpthread；解析器对 ANSI/格式变化脆弱且无输出尾证据 | 0002 rev2 改文档模式（双宏 + bool init + <unistd.h> for nice，--long 仍在 main 过滤）；LDLIBS 补 -lpthread；_run_upstream_tests 显式传 OSL_HOME、errors=replace、每套件打 output tail、解析先去 ANSI 且 Running 正则放宽到 `Running\s+N\s+test\s+cases?`、无 Running 时附 tail 样本以区分崩溃与格式失配；不改断言不跳过 |
| 16 | 本轮真机仍在库编译中途 `Connection closed by remote host`（-O2/-j1/去-g 已生效，日志仍见 `-O2 -DNDEBUG` 编译行后掉线；`tar: time stamp ... is N s in the future` 仅 0.4s 宿主-真机时钟偏移，非致命警告） | -O2 内联/向量化峰值仍超受限真机内存；tar 警告是 Windows 宿主 mtime 相对真机时钟超前，无需配方修复 | `RELEASE_CXX_OPTFLAGS="-O1 -DNDEBUG -march=armv8-a -g0"`（再降一档并用 -g0 钉死无调试信息；-DNDEBUG/-march 保留，不改测试口径）；低内存加固与单作业保持不变，不跳过任何测试 |
| 17 | 本轮真机 core/test/testAll.cc 编译失败：`redefinition of 'init_unit_test'`（前一定义在 boost/test/unit_test_suite.hpp:387）+ 连带 `expected '}'`（main 左括号未闭合假象） | 0002 rev2 同时定义了 `BOOST_TEST_MODULE`（经 config.hpp 隐含 `BOOST_TEST_MAIN`）与自定义 `bool init_unit_test()`；单头 `unit_test_suite.hpp` 在 `BOOST_TEST_MAIN` 下已默认定义 `bool init_unit_test(){return true;}`，与承载 OslConfig 初始化的自定义版本重定义冲突（Boost 源码 `BOOST_TEST_MAIN`/`BOOST_TEST_NO_MAIN`/`unit_test_main.ipp` 三处逻辑确认）；`expected '}'` 为重定义后的连锁误报 | 0002 rev3 去掉三处 `testAll.cc` 的 `#define BOOST_TEST_MODULE`（保留 `BOOST_TEST_NO_MAIN` 抑制自动 main + `BOOST_TEST_ALTERNATIVE_INIT_API` 声明 `bool(*)()` 新签名），自定义 init/main 成为唯一定义；577 用例源码、Makefile、测试口径均不动，不跳过任何测试 |

| 18 | 同一指纹第 3 次：去掉 MODULE 后真机仍报 `testAll.cc:42 expected '}'`（`31:1 to match '{'` 为 main 左括号，42 行恰为 for 循环的 `}`，说明 main 尾部缺失） | 前两轮只盯 `BOOST_TEST_MODULE` 重定义假设、沿用同一补丁体；实测补丁头 `@@ -1,28 +1,42 @@` 与正文不符——三处 hunk 实际新增 45 行（`python` 统计 add=45/del=28/ctx=0），头标 42 少 3 行，严格 patch 按头计数截断，把 `filtered_argc/return/}` 丢掉，main 恒未闭合；与 MODULE 有无无关，属手写补丁头计数事故（libdrpm/0.5.3 先例同类） | 换路线：删除 `patches/0002`（conandata/manifest 同步移除），改在配方 `source()` 用 `_fix_testall_entry()` 做精确字符串替换（幂等：已含 `BOOST_TEST_NO_MAIN` 则跳过；锚点缺失抛错不猜），保留 `BOOST_TEST_NO_MAIN + BOOST_TEST_ALTERNATIVE_INIT_API、无 MODULE、bool init + 过滤 --long 的 custom main` 的文档模式组合（Boost 1.84 单头 custom init + custom entry 两页确认）；三套件各保原 OslConfig 顺序，用例零改动；不跳过任何测试 |
| 19 | preflight std exit=201 discovered=0 + core/full exit=139 SIGSEGV, parser reports no Running line; std tail shows per-case pass/fail but no Running, full tail shows eval.bin/progress.txt load fail then Signal 11 | log_level=nothing suppresses Boost Running line (docs: nothing reports no info), so discovered stays 0; crash tail lacks Entering test name, catch_system_errors not enabled, data-file presence not logged, cannot tell missing dataset from aarch64 bug | test flags to --report_level=detailed --log_level=test_suite --catch_system_errors=yes (Running reappears, crash becomes per-test failure with Entering name), tail 4000->8000, log data/progress.txt eval.bin FILES presence, MANIFEST command sync; no assertion/test-source change, no dummy data |

| 20 | test_package test() 用裸 `subprocess.run(ctest)`、无 `self.run`，且 `passedCount` 靠 `findall("CHECK.*PASS")` 数 stdout 字符串 | PF3 预检要求 test() 含 `self.run` 真实执行逻辑；门禁明令禁止对 stdout 字符串数数做计数（catch2 教训：正则/减法拼出矛盾计数直接判 incomplete） | test() 改仓库通行范式（debugbreak/racon 先例）：`self.run(bash -c "ctest --output-on-failure", env="conanrun")`；`test_osl.cpp` 加 argv 过滤、CMake 注册 3 个独立 ctest 用例（move_api/initial_state/platform_config）；discovered 取 `ctest -N` 的 `Total Tests`，passed/failed 逐行解析 `Testing/Temporary/LastTest.log` 的 `Test #N ... Passed/Failed` 行，日志缺失如实报错不猜数 |
| 21 | test_package 用 C++17（generate + target_compile_features），而库本体因上游头文件用 C++17 已移除项只能按 C++14 构建 | 消费者若包含转递拉入相关公共头文件的 TU，会在真机遭遇与第 7 项同类硬错误；仅 `.cc` 的问题不影响消费者，但头文件侧无法逐一排除 | 消费者标准与库本体对齐为 C++14（Boost 1.84 下限即 C++14）；MANIFEST 同步更新命令与用例说明，不改任何断言 |

| 22 | 真机 core/full testAll exit=139（SIGSEGV、无汇总行，解析器报 unparsed 且 executed=0/skipped=0，恒等式破裂硬失败）；std 有 38 例 `check ifs/loaded has failed`；三处外部数据 `data/progress.txt、data/eval.bin、public-data/floodgate2010/FILES` 在 0.8.0 orig 包内缺失，full 尾部 `Failed to load NewProgress data ... Signal 11` | 0.8.0 orig 包本就不含 data/public-data 树（Debian 亦只构建不跑测试），缺数据与平台无关；-DNDEBUG 下 assert 被编出，setUp 失败后测试仍走进未初始化权重而崩溃；旧解析器崩溃时 returned executed=0（数字与框架输出脱节）且 summary 路径 failed>0 时 reason 为空会误判 passed | 解析器加崩溃回退（同次运行的 Entering/Leaving/error 行：executed=Leaving 数、failed=去重 error 用例、passed=executed-failed、skipped=discovered-executed；去掉钳制分支，不一致由恒等式如实报错；summary 路径 failed>0 必写 reason）；恒等式按门禁口径放宽为 executed+skipped<=discovered；非通过项经 `_classify_upstream_gaps` 以 environment gaps 上报（含缺文件清单与失败行证据，gaps 和=discovered-passed），状态 incomplete 只告警不抛错，无证据时仍抛错；用例零改动、不造假数据（catch2/odiff 先例的 incomplete+gaps 范式） |
| 23 | 真机 test_package 在 generate() 报 `ConanException: CMakeToolchain is declared in the generators attribute, but was instantiated in the generate() method too`（line 49 tc.generate()），主库已 built、test_package 未执行 | test_package/conanfile.py 同时在 `generators = "CMakeDeps", "CMakeToolchain"` 声明并在 `generate()` 内 `tc = CMakeToolchain(self); tc.generate()` 实例化，违反 Conan 2 门禁（同一生成器只能二选一）；前三周期只改主配方上游测试解析/日志开关，未触及 test_package 生成器，故换了失败域后旧方案无效 | `generators` 仅保留 `CMakeDeps`，保留 `generate()` 内自定义 `CMakeToolchain`（C++14/BOOST_SP_NO_PTHREAD_SETCANCELSTATE/OHOS→Linux 映射）；用例零改动、不跳过测试 |
| 24 | 真机 test_package build() 编译 `test_osl.cpp.o` 报 `osl/bits/construct.h:6:10: fatal error: 'boost/type_traits/has_trivial_destructor.hpp' file not found`（上轮 #23 已让 generate 通过、主库 built） | osl 公共头转递包含 Boost 头，但拆分的 boost1.84-* 组件包均声明 `cmake_file_name="Boost"`，CMakeDeps 无法经 `libosl::libosl` 可靠透出 Boost include，主配方 raw-make 靠手写 `-I` 不受影响、唯消费者 CMake 路径缺头；与 #23 的生成器双声明不同失败点 | test_package `generate()` 内经 `self.dependencies` 取各 boost1.84-* 的 `include` 并向 toolchain 注入 `-I`（各包头文件同源、任一可用即可）；CMakeLists/用例零改动、不跳过测试 |
| 25 | #24 修复在真机 `generate()` 报 `AttributeError: 'CMakeToolchain' object has no attribute 'cxxflags'`（line 64），generate 中断 | 前次凭记忆误用 `tc.cxxflags`；真机 Conan 2.30 的 CMakeToolchain 无此属性，仓库先例（zug/0.1.2、azure-storage-blobs-cpp/12.18.0 test_package）均为 `tc.extra_cxxflags`，且 zug 与本案同为“上游 CMake 不 find Boost 但公共头裸 include <boost/...>”须经 `extra_cxxflags` 注入 | 同一注入逻辑改用 `tc.extra_cxxflags.append(f"-I{inc}")`；其余（generators 仅 CMakeDeps、依赖枚举、isdir 守卫）不变，用例零改动 |
| 26 | 真机 test_package 编译报 `osl/move.h file not found`（generate 已通过、主库 built） | `test_osl.cpp` 引用了上游不存在的虚构头 `osl/move.h`；Move/Square 实际在 `osl/basic_type.h`（上游 move.t.cc 亦无 move.h）；前三周期只改主配方/生成器，未核对消费者 include 真实存在 | `test_osl.cpp` 改引真实头 `osl/basic_type.h`；用例零改动、不跳过测试 |
| 27 | 真机 test_package 编译 `test_osl.cpp:63 error: no member named 'player' in 'osl::Piece'`（#26 修头后新失败域，主库 built、generate 通过） | 消费者把 `Move::player()` 误用于 `Piece`；上游 `osl::Piece` 颜色接口为 `owner()`（`inline Player owner() const`，miniosl/osl 文档与 compactBoard.h 内 `p.owner()` 用法佐证），`player()` 仅存在于 `Move`；前序周期只核对头文件存在，未核对成员函数归属 | `test_osl.cpp` 仅改 `black_king.player()` 为 `black_king.owner()`（`pass.player()` 系 Move 方法，保留）；不断言、不跳过 |
| 28 | 真机 test_package `ctest 3/3 Passed` 却报 `HMBS_TEST_PACKAGE_RESULT passed=false passedCount=0`（#27 修 API 后编译已通，ctest 退出码 0） | `_parse_last_test_log` 用同行正则 `Test #\d+: .*Passed` 解析 `LastTest.log`；但 LastTest.log 为多行格式（`Test #N:` 与 `Test Passed.` 分处两行，同行正则恒得 0，mathic/1.4 同类事故），真机 `ctest --output-on-failure` stdout 的 `Test #1 ... Passed` 单行格式并不落盘到该文件；前次只修消费者源码，未触及计数器，故换失败域后旧方案无效 | 改用 silo-llnl/racon 先例：计 `Test Passed.`/`Test Failed.`+`Test Timeout.` 状态行（单源、无减法），取最新 LastTest.log 防 stale 并打 path+tail；执行仍走 `self.run(ctest)`，用例零改动 |

## 源码修改

- `test_package/test_osl.cpp`：虚构头 `osl/move.h` 改为真实头 `osl/basic_type.h`（#26；Move/Square 在 basic_type.h，上游 move.t.cc 佐证）；`Piece::player()` 改为 `Piece::owner()`（#27；颜色接口归属修正，`Move::player()` 保留）。
- `test_package/conanfile.py`：`generators` 仅保留 `CMakeDeps`（#23，Conan 2 双声明门禁修复）；`generate()` 经 `self.dependencies` 向 `tc.extra_cxxflags` 注入 Boost include（#24-25，消费者缺头修复；#24 误用不存在的 `tc.cxxflags` 在真机报 AttributeError，#25 改用仓库先例 `extra_cxxflags`）；`_parse_last_test_log` 改计 `Test Passed./Failed./Timeout.` 状态行并取最新日志（#28，同行正则在多行 LastTest.log 上恒得 0 的计数器修复，silo-llnl/racon 与 mathic/1.4 先例）。
- `patches/0001-emmintrin-x86-guard.patch`：两处 include 加 x86 架构守卫（可移植类）。
- `patches/0002-testall-boost-header-only.patch`：三处 testAll.cc 改用 Boost.Test 头文件入口（可移植类，测试框架适配；rev2 用 BOOST_TEST_NO_MAIN + BOOST_TEST_ALTERNATIVE_INIT_API + bool init 文档模式）。
- `patches/0003-test-makefile-drop-test-lib.patch`：三处测试 Makefile 去掉 `-lboost_unit_test_framework`（配套）。
- `patches/0004-libcxx-std-hash.patch`：`basic_type.h`/`hashKey.h` 补 `<functional>` 并去掉冗余的 `std::hash` 主模板前向声明（libc++ 可移植类）。
- `patches/0005-lightmutex-aarch64.patch`：`std/osl/misc/lightMutex.h` 的 LightMutex/LightMutexChar 自旋锁做 non-x86 可移植（x86 快路径不动，AArch64 用编译器原子 test-and-set/release + yield）。

## 依赖版本

- boost1.84-filesystem/1.84.0、boost1.84-serialization/1.84.0、boost1.84-iostreams/1.84.0（编译库）
- boost1.84-system/1.84.0、boost1.84-date_time/1.84.0（上游链接行所需；1.69 起主体为 header-only）
- bzip2/1.0.8、zlib/1.3.1（boost1.84-iostreams 内编入的 bzip2.cpp/zlib.cpp/gzip.cpp 后端所需；testAll 链接经 LDLIBS 传 -lbz2 -lz -lpthread，其中 -lpthread 系补回被命令行覆盖的 makefile.conf 默认值）
- 以上模块包在仓库中状态为 built/published；真机 `conan download -r=ohpcd` 做最终 W0 确认。

## 上游测试

- 框架：Boost.Test；入口 `core/std/full` 各一个 `testAll` 二进制。
- 总数：源码审计 150 个 `.t.cc` 文件、577 个 `BOOST_AUTO_TEST_CASE`（口径 auto）。
- 运行：`./testAll --report_level=detailed --log_level=test_suite --catch_system_errors=yes`；discovered 取框架
  `Running N test cases...` 行，passed/failed/skipped 取同次运行的详细报告汇总行；崩溃无汇总行时取同次运行的
  Entering/Leaving test case 及 `error: in ...` 行（executed=完成数、failed=去重失败用例、skipped=discovered-executed）。
  外部数据集缺失导致的非通过项以 environment gaps 上报（gaps 和=discovered-passed），状态 incomplete；用例零改动。
- test_package：`test_osl.cpp` 三组真实 API 检查（Move/Square 分类、CSA 初盘
  解析 + NumEffectState 一致性/王将位置、aarch64 `nosse` 平台配置），经 ctest 运行。

## 验证结果

```bash
# 待 HMBS 真机预检（conan create）回填：
# HMBS_UPSTREAM_TEST_RESULT=...
# HMBS_TEST_PACKAGE_RESULT=...
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 主配方（构建 + 上游测试 + 标记） |
| `conandata.yml` | 源码 URL 列表 + sha256 + 补丁声明 |
| `patches/000*.patch` | 4 个可移植补丁（0002 已退役转入 source()） |
| `test_package/` | 消费者测试（CMake + test_osl.cpp + MANIFEST.yml） |
| `manifest.yaml` | 版本元数据 |
| `notes.md` | 本文件 |

## 注意事项

- Windows 本地无法检出上游个别文件名（含回车符的 gama 补丁）与 `libXext/libxext`
  大小写冲突目录，工作树对这两处做了本地稀疏/中性处理，与本配方无关。
- `manifest.yaml` 中上游 577 例为源码快照审计数，PR 正文通过率以真机框架输出为准。
- 上游测试量较大（577 例将棋引擎单测），真机单并发（jobs=1）预计耗时较长，属正常现象。
