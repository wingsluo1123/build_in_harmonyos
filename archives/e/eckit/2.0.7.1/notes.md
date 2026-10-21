# eckit 2.0.7.1 编译笔记（HarmonyOS PC / OHOS · Conan 2 + CMake + ecbuild）

## 定位
- 产出动态库 `libeckit.so`（ECMWF eckit 2.0.7），供 odc 等包作依赖与 dlopen 使用。
- 归档 `archives/e/eckit/2.0.7.1/`；分支 `fix/eckit-2.0.7.1`；平台任务 15313。
- 版本沿革：本目录是 2.0.7（任务 15039 / PR #15543 / 分支 `fix/eckit-2.0.7`）之上的 **fix 递增版**——平台 R37 版本碰撞闸（`ci/conan/build_and_test.sh` L0j）比对已发布配方的 conanfile.py+conandata.yml 归一化内容，同版本不允许第二个修订，故必须递增；上游源码仍是 2.0.7 tag tarball（`sha256 376aa865…`），**不存在 2.0.7.1 下载地址，也不虚构**。本文件下文 create#5–create#8 的全部读数属 **2.0.7 历史证据**（RREV `8057e2e84f…`/`af53dddb9…`/`0467f30b8a…`），不对本版本生效，保留仅为机制溯源与更正可追溯；本版本自己的真机读数见文末「回合37 · 2.0.7.1 create#9」段。
- 源：官方 tag tarball `https://github.com/ecmwf/eckit/archive/refs/tags/2.0.7.tar.gz`，
  sha256 `376aa865b317d9533c1c88e1a7d15ca248420cc8a048570f3fe216e123991b51`（`conandata.yml` 活文件实测，无镜像/`file://`/`.orig` 残留）。

## 关键适配（逐项：原文件 / 原因 / 内容 / 结果）

| 补丁 | 原文件 | 原因 | 内容 | 结果（一手载体） |
|---|---|---|---|---|
| `0001-musl-uid_t.patch` | `src/eckit/filesystem/PathName.h` | musl 不像 glibc 那样经其它头间接引入 `uid_t`/`gid_t`，补丁内注释所载报错 `unknown type name 'uid_t'; did you mean 'pid_t'?` | 显式 `#include <sys/types.h>` | 编译通过（create 段） |
| `0002-musl-strerror_r.patch` | `src/eckit/log/Log.cc` | 上游按 `_GNU_SOURCE` 选 `strerror_r` 重载，而 musl 只提供 XSI 版 ⇒ 交叉编译期重载选择错误 | 判据改为 `_GNU_SOURCE && __GLIBC__`，musl 走 XSI 分支（`Log.cc:62-69`） | 编译通过；`Log::syserr` 可用（XSI 分支实测见下 #57 归因） |
| `0003-ohos-no-pthread-cancel.patch` | `src/eckit/thread/ThreadControler.cc` | OHOS libc 不提供线程取消：`pthread_cancel`/`pthread_kill`/`pthread_setcanceltype` 在 sysroot `pthread.h` 中均不存在，试编全部失败 | `#if defined(__OHOS__)` 下 `kill()` 降级为 no-op（不做等价替换） | 编译链接通过。**功能限制（必须对外说明）**：依赖 `ThreadControler::kill()` 强杀线程的用法在鸿蒙上不生效，应改用协作式 `stop()` |
| `0004-ohos-systeminfo-linux.patch` | `src/eckit/system/SystemInfo.cc` | ecbuild 的 `OS_NAME` 取原始 `CMAKE_SYSTEM`（未归一化），`makeSystemInfo()` 的 Linux 分支不匹配 `OHOS` ⇒ 修前 `SystemInfo::instance()` 落 `SystemInfo.cc:68` NOTIMP（回合 16 实测） | Linux 分支同时接受 `OHOS`/`HarmonyOS` | **行为已在当前构建树上由上游用例坐实**：`tests/system/test_system_library.cc:78-83 CASE("test_eckit_system_info")` 调 `SystemInfo::instance().executablePath()` 并 `EXPECT(std::string(execPath).size())`，该可执行文件 = ctest **#131 `eckit_test_system_library` → Passed 0.08 sec**（`create-eckit-5.log:1926`）。消费者侧 `dynamicLibraryName()` 断言在当前 revision **未执行**（见"test_package 状态"） |
| `0005-geo-unzip-libzip-gate.patch` | `src/eckit/geo/CMakeLists.txt`（`strip: 1`） | `cache/Unzip.cc/.h` 与 `libzip` 依赖原被放在 `GEO_AREA_SHAPEFILE`（需 shapelib）块内；本配方 `ENABLE_SHAPELIB` 关闭时 `tests/geo` 的 `ZIP_FILE` 代码路径链接不到符号 | 把 `Unzip` 源与 `libzip` 依赖移到 `eckit_HAVE_ZIP` 块 | geo 族 **45 条用例全部 Passed，零 `undefined reference`**（`create-eckit-5.log`，含 `#211/212/213 eckit_test_geo_grid_fesom/icon/orca`） |

### 配方侧注入项（不改上游文件，故不进 patches 列表）
- **测试开关（§10 硬口径）**：门控变量是 ecbuild 的 `ENABLE_TESTS`（置 `eckit_HAVE_TESTS` ⇒ 顶层 `CMakeLists.txt:348 add_subdirectory(tests|regressions)`）。
  实测凭据：只设 CTest 的 `BUILD_TESTING` 时 cache 为 `ENABLE_TESTS:BOOL=OFF` + 日志 `Feature TESTS disabled` + `ctest -N` `Total Tests: 0`（回合 17 假绿取证）。
  现配方 `conanfile.py:65 tc.variables["ENABLE_TESTS"] = "ON"`，`build()` 末 `cmake.test()`（`:168`）真实执行上游套件。
  当前构建树 cache 复核（`create-eckit-5`）：`ENABLE_TESTS:BOOL=ON`（`:551`）、`BUILD_TESTING:STRING=ON`（`:114`）、`eckit_ENABLE_TESTS_defined_value:INTERNAL=ON`（`:1221`）。
- **libzip 目标命名空间钩子**：conan `CMakeDeps` 为 libzip 生成的目标是 `libzip::libzip`，而系统 libzip config 与上游 `src/eckit/geo/CMakeLists.txt:209`（含 0005）用 `libzip::zip` ⇒ 交叉 CONFIG 模式下报
  `Target "eckit_geo" links to: libzip::zip but the target was not found`（`diag-test-4.log:264-278`）。
  做法 = CMake 官方钩子 `CMAKE_PROJECT_eckit_INCLUDE` 指向 `eckit_adapt_libzip.cmake`（`find_package(libzip CONFIG REQUIRED)` + `add_library(libzip::zip ALIAS libzip::libzip)`），
  在 `project(eckit)` 之后、toolchain 使用之前生效；配方 `conanfile.py:106-114`、`:165`。
- 其余 feature 取值（`conanfile.py:62-75`）：`ENABLE_MPI=OFF`、`ENABLE_ECKIT_CMD=OFF`、`ENABLE_BUILD_TOOLS=OFF`、`ENABLE_EXTRA_TESTS=OFF`、
  `ENABLE_EIGEN/AEC/ZIP/BZIP2/LZ4=ON`、`ENABLE_RADOS/MKL/OMP/SNAPPY=OFF`。
- 产物签名（OHOS 强制）：`binary-sign-tool` + `llvm-objcopy` 定位链与 ELF64 节头表断言见 `conanfile.py` 签名段；实测
  `OHOS codesign: signer=…/usr/local/bin/binary-sign-tool objcopy=…/.harmonybrew/bin/llvm-objcopy targets=12`（`create-eckit-4.log:2327`），
  独立节头表遍历确认 `lib/libeckit.so`、`bin/eckit-version` 均 `HAS_CODESIGN`。

## 上游测试账本（§10.1 五维，数字全部来自一手载体，不由日志反填）

- `N_static = 138`：按 2.0.7 tag 源码逐个 CMakeLists 统计的真实注册入口 `ecbuild_add_test(`，分布在 **28 个 CMakeLists.txt**（下表 30 个目录条目中 `tests/experimental` 与 `tests/CMakeLists.txt` 两项声明点为 0 => 命中文件数 28，138 处注册点由下表逐目录相加）；可复现命令：`grep -ro 'ecbuild_add_test(' <src>/ --include=CMakeLists.txt | wc -l` = 138、`grep -rl 'ecbuild_add_test(' <src>/ --include=CMakeLists.txt | wc -l` = 28；松散形态 `ecbuild_add_test`（同行不带左括号）= 142，多出的 4 处全部集中在 `tests/geo/CMakeLists.txt`（该文件带括号 4 / 不带 8），故本包申报一律取带括号口径 138/28，不得再报第三个数；
  裸 `add_test(` = **0**、`eckit_add_etc_test(` = 0、`eckit_add_etc_shell_test(` = 0。逐目录（载体：create#5 源树 `…/eckitaead498222279/b`）：

  | 目录 | 声明点 | 目录 | 声明点 |
  |---|---|---|---|
  | tests/linalg | 28 | tests/maths | 5 |
  | tests/utils | 14 | tests/io | 5 |
  | tests/container | 10 | tests/runtime | 5 |
  | tests/filesystem | 10 | tests/value | 5 |
  | tests/types | 10 | tests/geo | 4 |
  | tests/log | 9 | tests/codec | 3 |
  | tests/mpi | 7 | tests/memory | 3 |
  | tests/parser | 4 | tests/config | 2 |
  | tests/serialisation | 2 | tests/option | 2 |
  | regressions | 1 | tests/exception | 1 |
  | tests/geometry | 1 | tests/large_file | 1 |
  | tests/spec | 1 | tests/sql | 1 |
  | tests/system | 1 | tests/testing | 1 |
  | tests/thread | 1 | tests/experimental | 0 |
  | tests/experimental/singleton | 1 | tests/CMakeLists.txt | 0 |
  | **合计** | **138** | | |

- `N_registered = 216`：一个 `ecbuild_add_test` 声明点可注册多条 ctest 用例（回归 `.sh` 族即由此展开），故注册条目 **>** 声明点数，两列分别记账、不互相顶替。
  载体：重新 configure 后 `ctest --test-dir …/build/Release -N` → `Total Tests: 216`（`ctest-N-1.txt`）。
- `N_executed = 216`（= 可执行分母，**未做任何删减**）：**权威执行 = create#6**（清树后全新重编）。
  汇总行 `98% tests passed, 5 tests failed out of 216`（`create-eckit-6.log:2109`），`Total Test time (real) = 91.07 sec`（`:2116`）。
  标签分账（`probe-170x-eckit6-failtests.txt:3-5`）：`eckit = 90.73 sec*proc (216 tests)`、`executable = 81.59 sec*proc (198 tests)`、`script = 9.14 sec*proc (18 tests)`。
  逐用例原文另以该树 `Testing/Temporary/LastTest.log`（787184B，mtime 16:47）为载体，5 条失败项的 `start time/time elapsed/Test Failed` 段已逐条摘出（`round23c.log` [E]）。
  历史对照（**同一次口径、更早一轮**）：create#5 `create-eckit-5.log:2098` 同为 `5 tests failed out of 216`，`Total Test time (real) = 93.01 sec`、`executable 84.07(198)/script 8.60(18)` —— 两次独立执行的**分母与失败集合逐条一致**，耗时/标签秒数按轮浮动，自本行起以 create#6 为准。
- `N_pass = 211`，`N_fail = 5`（逐条见下节，**保留 (Failed)/SIGSYS，不重分类、不删用例、不缩分母**）。
- `N_consumer = 1` 个消费者程序（`test_package/test.cpp`，5 个断言组）——**当前 blob 集上已真执行**（rc=0，独立编译/链接/运行载体，非 `conan test` 路径），见下"test_package 状态"。
- 内存：`max_rss_mb` 预算 **4000**（经 memcap 硬止损），create#6 实测 `MEMCAP[run] peak=460MB budget=4000MB rc=1 用时1625.5s`（create#5 为 `peak=442MB … 用时1697.7s`）；
  资源链 = `gate.sh 8000` → `build-slot.QDR-1009-E02.sh --wait … --mem 8000`（flock 真互斥）→ `memcap-run.py --mb 4000`，jobs=2/`MAKEFLAGS=-j2`。

### 因 feature 关闭而"未注册"的声明点（条件未执行分账，逐目录列明，不从分母删除）
- `tests/mpi` 7 处声明：`ENABLE_MPI=OFF`（cache `:530`）。216 条注册名单中含 `mpi` 名称的仅 **1** 条 ⇒ 其余未注册项属"条件未注册"，非"跑失败"。
- `tests/sql` 1 处：注册名单中含 `eckit_test_sql` 名称 **0** 条。
- `tests/experimental` 0 处 + `tests/experimental/singleton` 1 处：注册名单中含 `experimental` **0** 条（`ENABLE_EXTRA_TESTS=OFF`，cache `:1204`）。
- `ENABLE_ECKIT_CMD=OFF`（cache `:512`）：注册名单中含 `eckit_cmd` **0** 条。
- 其余声明点与 216 条注册条目的逐一对账（`eckit_add_test` 宏内部的展开关系）未在本轮逐条完成 ⇒ 记为**未逐项坐实**，不改分母口径。
  **通过率统一口径（回合 26 按 §10.1 锁定，正文三行 / 本 notes / `test_package/MANIFEST.yml` / result 四处同源）**：分母恒为注册 `N_registered = 216`；
  无豁免全量真跑档 = create#6 `216 执行 / 211 通过 = 211/216（97.7%）`（日志自报 `98%`）；
  逐项豁免后台内执行档 = create#7 `211 执行 / 211 通过 = 211/211（100%）`，同一注册分母下仍写作 `211/216（97.7%）`＋`本 run 执行项 211/211`。
  两档必须同句并列出现，不得单写 `100%` 而丢掉 216 分母，也不得把 create#7 的执行数写成 216。

## 5 条失败用例逐条归因（详证见 `.temp/QDR-1009-E02/eckit-draft/round20-attribution.md`）

1. **#3 `eckit_test_container_sharedmemarray` (SIGSYS)** — 首错原文（直跑，非聚合）：`Running case 0: test_eckit_sharedmemarray_construction … Signal 31 (core dumped)`、`RC3=159`。
   断点位 `tests/container/test_sharedmemarray.cc:40-43`。设备侧 ctypes fork-per-primitive 探针（**不含任何 eckit 代码**）：
   **调用点已坐实（回合 22，`probe-round22.log`）**：LD_PRELOAD shim 装 `sigaction(SIGSYS, SA_SIGINFO)` 后直跑该二进制，
   捕获 `SIGSYS_CAUGHT signo=31 si_code=1 si_syscall=190`，同帧回溯 `… <semget+0x4c> at /lib/ld-musl-aarch64.so.1` ←
   `<eckit::Semaphore::Semaphore(const eckit::PathName&, int)+0x8c> at libeckit.so` ← 该测试二进制。
   号→名由 SDK 头原文坐实：`sysroot/usr/include/asm-generic/unistd.h:261 #define __NR_semget 190`（aarch64 的 `asm/unistd.h` 只 `#include <asm-generic/unistd.h>`，自身 0 条 `__NR_` 定义）。
   源码路径：`src/eckit/container/SharedMemArray.h:69 Semaphore sem_;`（成员，进构造函数即构造）→ `src/eckit/os/Semaphore.cc:52 semget(key, count_, 0666 | IPC_CREAT)`；`SharedMemArray.cc:30 AutoLock<Semaphore> lock(sem_)`。
   **绑定 create#6 构建树的复现（回合 23，`round23b.log`/`round23c.log`）**：同一用例在 `…/p/b/eckita32a57605b7b5/b/build/Release/tests/container/` 上单用例直跑，
   `memcap-run.py --probe` 读数 `peak=2MB rc=-31`，持槽 + `--mb 4000` 执行读数 `MEMCAP[run] peak=6MB budget=4000MB rc=-31 用时0.3s`（`DIRECT3_RC=225`）；
   同树 LastTest.log 该用例段仅两行输出即到 `<end of output>` / `Test Failed.` ⇒ 与"构造函数体内第一条语句前就被信号杀死"一致。
   再以该树重编译 SIGSYS+backtrace 载体（`p3bt.so`，`P3BT_BUILD_RC=0`）LD_PRELOAD 直跑：`si_code=1(SYS_SECCOMP) si_syscall=190`，
   回溯帧逐字 `… <semget+0x4c> at /lib/ld-musl-aarch64.so.1` ← `<_ZN5eckit9SemaphoreC2ERKNS_8PathNameEi+0x8c> at …/eckita32a57605b7b5/b/build/Release/lib/libeckit.so` ← 该测试二进制。
   **被拒 syscall 集合（最小 C 探针坐实，`p3probe.c`，不含任何 eckit 代码；号码由 `__NR_*` 宏在设备头文件上解析后自印）**：
   `HDR semget=190 semctl=191 semop=193 shmget=194 shmctl=195 shmat=196 shmdt=197 statx=291 SIGSYS=31`；
   逐原语 fork 结果 = `semget(190)` **KILLED_BY_SIGNAL 31**、`shmget(194)` **KILLED**、`shmat(196)` **KILLED**、`semop(193)` **KILLED**；
   而 `shmctl(195)` 返 `-1/errno=14(EFAULT)`、`semctl(191)` 返 `-1/errno=22(EINVAL)`、`statx(291)` 返 `-1/errno=14` ⇒ **控制类与 statx 未被拦**；
   POSIX 侧 `shm_open fd=3 errno=0` / `ftruncate rc=0` / `shm_unlink rc=0`、`mmap(MAP_SHARED|MAP_ANONYMOUS) ptr=0x5a779bd000` 均 OK，`opendir("/dev/shm") FAIL`（**目录不可枚举，但 POSIX shm 命名对象实测可用**，两者不得混写）。
   ⇒ **限定结论**：本设备 seccomp（`Seccomp: 2 / Seccomp_filters: 1`）对 **SysV IPC 的创建/挂载类调用**（`semget`/`semop`/`shmget`/`shmat`/`shmdt`）返回 `SECCOMP_RET_TRAP`（`si_code=1`，可被用户态捕获）；
   本用例的真实死点是 **`semget`（信号量），不是共享内存调用**；POSIX shm 与匿名共享映射实测可用 ⇒ **不得写成泛指"OHOS 不支持 shm/共享内存"，也不得写成"statx 被拦"**。
   静态符号佐证：测试二进制 undefined 仅 `shm_open/shm_unlink/ftruncate/eckit::MMap::mmap`（**不含 SysV shm 家族**）；`libeckit.so` 另含 `shmget/shmat/shmdt`（`Shmget.cc:39`），本轮未在该用例路径上被触发。
   非本次适配引起（0001–0005 触及文件为 `PathName.h`/`Log.cc`/`ThreadControler.cc`/`SystemInfo.cc`/`geo/CMakeLists.txt`，无一在 `src/eckit/container/`、`src/eckit/os/` 或 `src/eckit/memory/`）。
   **取证口径更正（不得沿用旧读数）**：回合 20 的 ctypes 探针把裸号写成"195 shmget / 197 shmctl / 303 statx"，按 SDK 表与本轮宏自印实为 **194 shmget、195 shmctl、196 shmat、197 shmdt、291 statx**；
   该次探针"哪些裸号被拦"仍与本轮一致（196/197 被拦、195 返回错误码），但**号码标注作废**；本轮另坐实 190/193/194 亦被拦、191/291 未被拦，`statx` 早前的"被拦"暗示一并作废。本条以 `si_syscall` + 回溯帧 + 宏自印表 + fork-per-primitive 四处载体为准。
2. **#19 `eckit_test_filesystem_filemode` (Failed)** — 首错原文：`Condition failed: FileMode::fromPath(p) == m`，实测 `result = rw-,r--,--- oct=0640`（期望 0644）、`result = rwx,r-x,--x oct=0751`（期望 0755）。
   断点位 `tests/filesystem/test_filemode.cc:153`/`:196`/`:232`/`:209`/`:245`（前置 `AutoUmask mask(0)` + `chmod`）。
   native 对照（无 eckit 代码）：`umask(0)` 下建文件 0644→0660、0755→0770；文件 chmod 后→0660/0760；目录 chmod →一律 2771。与用例读数自洽。
   ⇒ **限定结论**：本设备 HMDFS 的默认文件模式与 `chmod` 语义与 POSIX 预期不同，仅影响**该用例断言的模式位读数**；**不得写成泛指"OHOS 不支持文件模式"**。
   非本次适配引起（同一二进制的纯位运算 case 0/1/2/4 全绿；native 探针不带 eckit 代码即复现）。
3. **#57 `eckit_test_log` (Failed)** — 首错原文：`unhandled eckit::Exception: Failed system call: unlink /tmp/edfpmjq3480hfnsribnzasdfibv (No error information)`、`FAILED: test_strerr`、`1 tests failed out of 11`。
   用例 `tests/log/test_log.cc:58-61`；上游容错 `LocalPathName.cc:392-400` 只把 `ENOENT` 当"本来就没有"。
   native 对照：`/tmp` 是**只读 0755 挂载**，`unlink` 不存在路径时 `/tmp` → **errno=30 EROFS**，HMDFS 路径 → **errno=2 ENOENT** ⇒ 落 throw 分支。
   "(No error information)" 定位在**上游代码自身**：`Exceptions.h:139` 第三参默认 0，`Exceptions.cc:107-108` `errno = err;` 把真实 errno 覆写成 0 ⇒ musl `strerror(0)` 文案。0002 只做重载选择，不改这一事实（glibc 上同样丢失）。
   ⇒ **限定结论**：仅"本用例对 `/tmp` 的 unlink 语义"这一具体 syscall 平台受限；**不得写成泛指"OHOS 不支持 /tmp 或删除"**。非本次适配引起。
4. **#69 `eckit_test_maths_floating_point_exceptions` (Failed)** — 读数原文：`4/5 Test #69 … ***Failed 0.06 sec` 而同块 `0 tests failed out of 4`；直跑同一二进制 **rc=0**。
   机制 = 上游自有的注册契约反转：`tests/maths/CMakeLists.txt:22-31` 在 `eckit_HAVE_FEENABLEEXCEPT` 未成立且非 x86/非 APPLE 时 `set_tests_properties(… WILL_FAIL TRUE)`；
   探测点 `src/eckit/CMakeLists.txt:40 check_symbol_exists(feenableexcept "fenv.h" …)`（musl/OHOS aarch64 无该符号），`eckit_config.h.in:41`、`FloatingPointExceptions.cc:124-125`。
   独立载体：`ctest --show-only=json-v1` → 该用例属性含 `{'name': 'WILL_FAIL', 'value': True}`。
   **不可安全修好**：改判为通过需撤销上游 `WILL_FAIL`（改测试意图/判据）。非本次适配引起（配方未设置/覆盖 `eckit_HAVE_FEENABLEEXCEPT`，未改 `tests/maths/CMakeLists.txt`）。保留 (Failed)。
5. **#154 `eckit_test_safe_casts` (Failed)** — 首错原文（`rerun-failed-1.log:151`）：`Test "No-op if used as signed to signed cast" failed with unhandled eckit::Exception: Bad cast: Value too large to cast to signed type @ `、`1 tests failed out of 6`。
   抛出文本逐字匹配 `src/eckit/utils/SafeCasts.h:53-60`（无符号→有符号越界分支）；`:67-70` 有符号→有符号是纯 no-op 不可能抛 ⇒ 抛出点只能是 `tests/utils/test_safe_casts.cc:91 static_cast<char>(-5)`。
   机制 = AArch64 AAPCS64 默认 `char` 为无符号（上游用例按 x86"char 有符号"书写）。编译参数取证
   `tests/utils/CMakeFiles/eckit_test_safe_casts.dir/flags.make`：`-stdlib=libc++ -pipe -Wall -Wextra -Wno-unused-parameter -Wno-unused-variable -Wno-sign-compare -O3 -DNDEBUG -std=c++17 -fPIE`
   —— **既无 `-fsigned-char` 也无 `-fno-signed-char`** ⇒ 取 ABI 默认，非配方注入。
   **不可安全修好**：加 `-fsigned-char` 会改变整库 `char` 语义与对外 ABI（与已发布包可能不一致），属削上游行为换绿灯。非本次适配引起。保留 (Failed)。
   **`char` 符号性对照已坐实（回合 22，`probe-round22.log` [6/9][7/9]，全部用 `flags.make` 原文参数）**：
   ① 默认 ABI：`static_assert(std::is_unsigned_v<char>)` **编译通过 RC=0**；`static_assert(std::is_signed_v<char>)` **失败 RC=1**
   （报错原文 `static assertion failed due to requirement 'std::is_signed_v<char>': PROBE_CHAR_SIGNED`）。
   ② 加 `-fsigned-char`：`is_signed_v<char>` **通过 RC=0** ⇒ 符号性确实只由该开关翻转，而本配方未给。
   ③ 运行读数（同一 `SafeCasts.h` 头 + `libeckit.so` 真链接）：`is_unsigned_v<char>=1`、`numeric_limits<char>::min()=0`、
   `static_cast<char>(-5) 按 unsigned char 读出=251`、`RESULT=THREW BadCast: Bad cast: Value too large to cast to signed type`
   —— 与用例失败文本逐字一致，抛出路径由此钉死在 `SafeCasts.h:53-60` 的无符号→有符号分支。
   ④ 汇编载体：`-S -O0` 输出 `bl _ZN5eckit11into_signedIcLi0EEE…`（`Ic` = 模板实参 `char`，非 `a`/`h`）⇒ 重载选择走 `make_signed<char>` 路径。
   ⇒ 仍**不可安全修好**（判语不变）：翻转需 `-fsigned-char`，改整库 `char` 语义与对外 ABI。保留 (Failed)，不删用例、不缩分母、不重分类。

> **取证口径纠正（必须保留）**：诊断轮 v1 的 216 条 `Not Run`（`Unable to find executable`）源于**复用未注册 tests 的旧 build 目录直接 `--target test`、跳过编译**（CMake 的 `test` 目标不依赖 `all`），
> 属测量手段缺陷，**不得记成产品失败**。另：`conan create --build=…` 的 rc=0 若日志含 `No tests were found!!!` 即为假绿，不作交付证据（回合 17）。

## test_package（消费者测试）状态
- 设计：`test_package/conanfile.py:9 requires(self.tested_reference_str)`；`:31` 用宿主编译器独立编译 `test.cpp`（非模板复制）生成 `test_probe`；`:43-51` shell 定位候选序后 `self.run("./test_probe", env="conanrun")`。
- `test.cpp` 5 个断言组：库版本（运行期 vs 编译期宏 vs `version_int()==20007`）、MD5 三组 RFC 1321 标准向量、Tokenizer 分词、AEC 往返（libaec 接入证据）、`SystemInfo::dynamicLibraryName()/executablePath()`（0004 工厂回归断言）。
- **blob 集上的执行状态（回合 22 记，回合 24 起该门已按逐项豁免改写，见「回合 24」节）**：`conan test` 路径当时不可达 —— create#5 及 create#6 都在 `build()` 末的 `cmake.test()`（原 `conanfile.py:168`）因上述 5 条失败返回 Error 2 而终止，不产出 package ⇒ 进不到 test_package 段。
  但同一 `test.cpp` 已在**当前构建树**上以独立载体真执行（`probe-round22.log` [8/9]）：用该树 `flags.make` 的原文 `CXX_FLAGS`/`CXX_INCLUDES` 编译 → 用 `tests/utils/.../link.txt` 原样链接 `libeckit.so` → `memcap-run.py --mb 800` 运行，
  读数 `CONSUMER_OBJ_RC=0 / CONSUMER_LINK_RC=0 / CONSUMER_RUN_RC=0`，5 个断言组逐条打印：版本三处一致（2.0.7 / 宏 2.0.7 / int 20007）、MD5 三组 RFC 1321 向量、Tokenizer `"a:bb:ccc"` 3 token、AEC 往返 4096→1804（44.0%）逐字节一致、
  **`SystemInfo OK: dynamicLibraryName(eckit)=libeckit.so, executablePath=…（OHOS 走 SystemInfoLinux）`** ⇒ 0004 的消费者侧回归断言在当前 blob 集上坐实。
  ⚠ 口径边界：这条是**同源的独立编译运行**，不冒充 `conan test`/`test_package` 流水线结果；后者仍需在 `cmake.test()` 门解决后才可达（交付口径待统筹定档，见「状态」节）。

## 状态（诚实口径）
- 编译/链接/安装/自签：已验证通过（create#2/#4 段与签名读数见上）。
- 上游测试：**已在 `build()` 内真实执行 216/216，211 通过 / 5 失败**（5 条均为平台机制/上游测试契约所致，逐条已给技术原因，不属"0 执行"）。
- `conan create` 端到端：create#5/#6 均为 **rc=2**（`build()` 末 `cmake.test()` 因上述 5 条失败终止、不产出包）。**统筹 18:30 已定档**（§10「个别用例平台受限逐项 `test_skipped` 附技术原因」）：配方改为对同一 `test` 目标注入锚定 `--exclude-regex` 逐条豁免这 5 项、其余 211 项继续真跑，实现与读数见「回合 24」节；create#7 的终态读数与是否产出包以本节之后的记录为准。
- **create#6（回合 22 起、回合 23 定案；终态读数来自统筹代证载体 `.temp/hw-coord/probe-170x-eckit6.txt`/`probe-170x-eckit6-failtests.txt` 与本窗 `round23*-win.txt`）**：
  先 `conan remove "eckit/2.0.7" -c` 清空缓存做**真正的全新重编**（配方三件套 blob 未变 ⇒ rrev 不变，本轮"新"在清树而非改配方），
  资源链 `gate.sh 8000`（本轮复跑 `GATE_PASS:probe=clang MemAvailable=11620MB … 编译器进程=0`，`GATE_RC=0`）→ `build-slot --wait 3600 --mem 8000`（**全程只占 1 槽**）→ `MAKEFLAGS=-j2` → `memcap-run.py --mb 4000`。
  **终态**：`CREATE_RC=2`、`ELAPSED_S=1645`、`MEMCAP[run] peak=460MB budget=4000MB rc=1 用时1625.5s`、
  `RREV=8057e2e84f8b16ee05e381d8f715da81 (2026-10-11 08:20:44 UTC)`，该 revision 在缓存里 **`No packages found`** ⇒ **无 PKID/prev 可报**；
  `Package 'ac5dbe63be94cf44531a6b18ac4b40fa5a84d380' build failed`（该 40 位串 = conan package_id，**不是 git 对象**，`git cat-file` 失败已证，禁止当提交引用）。
  **构建目录真名 = `…/p/b/eckita32a57605b7b5/b/build/Release`**（与 create#5 的 `eckitaead498222279` 不同）。
  ⇒ **目录名差异不得用来推 rrev 变化**：本轮以 `grep -o 'eckit/2.0.7#<32hex>'` 同法比对两侧日志，create#5 与 create#6 的 rrev **同为 `8057e2e84f…`**，
  且 create#6 日志内同时出现两个 `p/b/eckit*` 名（清树阶段列出旧树）⇒ 构建树按"每次构建请求"命名，与 rrev 无 1:1 关系；上轮留的"目录名之谜"以此闭合，"blob 未变 ⇒ rrev 不变"的推断**被实测证实**（非否定）。
- **时间戳口径更正（回合 22 自述的"18:0x 复核"不可能成立，现予作废）**：create#6 的真实时间线由三个独立载体互证 ——
  ①槽位 `slot1.owner since=2026-10-11 16:20:43`；②RREV 时间戳 `08:20:44 UTC` = `16:20:44 +08:00`（与①同秒）；③`ELAPSED_S=1645` ⇒ 终态 ≈`16:47:2x`，
  与 `create-eckit-6.log`/`.rc`/`.summary` 及该树 `LastTest.log` 的 mtime `16:46–16:47 CST` 一致。
  误因：当时采信 toybox `ps -ef` 的 `STIME` 列（出现"父 28795 STIME=17:39:07 而子 28851 owner since=16:20:43"的父子倒挂），**本机 `ps` 时间列不可作时间载体** —— 已入取证口径教训。
  本窗此后一切时点只写可核载体（`date`/文件 mtime/owner 文件/RREV UTC 戳），且**计划时点一律按统筹节拍表述，不写自造钟点**。
- 未做：W4 独立审计、PR 创建/推送、CI、AI Review、提审。本文件数字与 `test_package/MANIFEST.yml`、`manifest.yaml`、双侧 `STATE.md`、`round20-attribution.md` 同源。
  归档 `manifest.yaml` 不含测试数字，其 `status: built` 记录的是构建段（compile+link+install+签名）验证事实，未改动；端到端终态以本节为准。

## 回合 23 定案：create#6 终态下 5 个失败项逐项（根因 / 归属 / §10 处置）

交叉核对口径：07:07 的 `direct-eckit_test_*.txt` 四条逐字日志 vs create#6 同树 `LastTest.log` 用例段 —— **首错文本与失败集合逐条一致**（下表"两载体一致"列），`#3` 当时无 direct 日志，本窗已补单用例直跑 + 两个坐实载体。

| 用例 | 根因（已坐实） | 平台受限 or 本次适配 | §10 处置 | 两载体一致 |
|---|---|---|---|---|
| #3 `eckit_test_container_sharedmemarray` (SIGSYS) | `SharedMemArray.h:69 Semaphore sem_` 成员先构造 → `os/Semaphore.cc:52 semget()` → musl `semget` 触发 seccomp `RET_TRAP`（`si_syscall=190`、`si_code=1`） | **平台受限**（设备 seccomp 拦 SysV IPC 创建/挂载类调用；0001–0005 未触及 `container/`、`os/`、`memory/`） | **逐项 `test_skipped` 附本节技术原因**；不改配方、不删用例、不缩 216 分母、不重分类 | 直跑 `rc=-31`/`DIRECT3_RC=225` 与 LastTest.log `Test Failed.`（输出止于 case 0 首行）一致 |
| #19 `eckit_test_filesystem_filemode` (Failed) | HMDFS 默认文件模式与 `chmod` 语义偏离 POSIX（实测 0644→0660、0755→0770，目录 chmod 一律 2771；用例前置 `AutoUmask mask(0)`） | **平台受限**（同一二进制纯位运算 case 0/1/2/4 全绿；native 无 eckit 代码即复现） | **逐项 `test_skipped`**，说明"仅模式位读数受限"，不得写成泛指"OHOS 不支持文件模式" | direct 尾部 `5 tests failed out of 7` 与 LastTest.log case 3 起分岔一致 |
| #57 `eckit_test_log` (Failed) | 用例 `tests/log/test_log.cc:58-61` 对 `/tmp` 下随机名 `unlink`；本设备 `/tmp` 为**只读 0755 挂载**，unlink 不存在路径返 `errno=30 EROFS`，上游容错 `LocalPathName.cc:392-400` 只把 `ENOENT` 当"本来就没有" ⇒ 落 throw | **平台受限**（仅"该用例对 `/tmp` 的 unlink 语义"这一具体 syscall；"(No error information)" 源于上游 `Exceptions.cc:107-108` 把 errno 覆写为 0，非 0002 引入） | **逐项 `test_skipped`**，不得写成泛指"OHOS 不支持 /tmp 或删除" | direct 首错文本与 LastTest.log:67-68 逐字相同 |
| #69 `eckit_test_maths_floating_point_exceptions` (Failed) | 上游自有**注册契约反转**：`tests/maths/CMakeLists.txt:22-31` 在 `eckit_HAVE_FEENABLEEXCEPT` 未成立且非 x86/非 APPLE 时置 `WILL_FAIL TRUE`；musl/OHOS aarch64 无 `feenableexcept`（`src/eckit/CMakeLists.txt:40 check_symbol_exists`）⇒ 二进制 `0 tests failed out of 4`（rc=0）反被 ctest 判 Failed | **平台机制 + 上游测试契约**，非本次适配（配方未设置/覆盖该变量，未改 `tests/maths/CMakeLists.txt`） | **逐项 `test_skipped`** 并注明契约反转；**不可安全修好**：改判通过需撤销上游 `WILL_FAIL`（改测试判据） | 本轮独立载体 `ctest --show-only=json-v1` → 仅 #69 带 `{'name':'WILL_FAIL','value':True}`，#3/#154 无该属性 |
| #154 `eckit_test_safe_casts` (Failed) | AArch64 AAPCS64 默认 `char` 为无符号，上游用例按 x86"char 有符号"书写：`tests/utils/test_safe_casts.cc:91 static_cast<char>(-5)` → 走 `SafeCasts.h:53-60` 无符号→有符号越界分支抛 `BadCast` | **平台 ABI 差异 + 上游用例书写**，非本次适配（`flags.make` 逐字取证：既无 `-fsigned-char` 也无 `-fno-signed-char` ⇒ 取 ABI 默认，非配方注入） | **逐项 `test_skipped`**；**不可安全修好**：加 `-fsigned-char` 改整库 `char` 语义与对外 ABI | direct `1 tests failed out of 6` + 栈帧 `BackTrace::dump`←`Exception`←`BadCast` 与 LastTest.log case 5 文本逐字同形 |

**交付口径结论（本窗不自作主张）**：5 条均为"平台机制/上游测试契约"，§10 允许的唯一路径是**逐项 `test_skipped` 附技术原因**（不删用例、不改判据、不缩分母、不以消费者通过冒充上游全量）。
是否把 `test_skipped` 写进配方/正文并因此产生新 revision，**由统筹定档**；在此之前 create#6 的 `CREATE_RC=2` 与 `No packages found` 是端到端真实状态，**不得宣称适配完成或可提审**（CI 面尚未开始）。

## 一手载体（可复核路径）
- 设备 `~/tmp/uc2/QDR-1009-E02/`：`create-eckit-5.log`(+`.rc`)、`rerun-failed-1.log`(+`.rc`=8、`.xml`)、`probe-sigsys-1.log`、`direct-sharedmemarray.txt`、`showonly.json`、`ctest-N-1.txt`、`reconf-1.log`、`create-eckit-4.log`、`diag-test-1.log`、`probe-round20-2.log`(+`.rc`=2)。
- Windows `.temp/QDR-1009-E02/`：`STATE.md`（逐回合断点）、`eckit-draft/round20-attribution.md`（逐条详证）、`eckit-draft/run-create-eckit-5.sh`、`logs/`（本次提交与 HEAD 证明）。
- 回合 23 新增载体：设备 `~/tmp/uc2/QDR-1009-E02/{round23-probe.log,round23b.log,round23c.log,p3probe.c,p3probe,p3bt.c,p3bt.so,round23b-shim.{out,err}}`；
  Windows `.temp/QDR-1009-E02/logs/{round23-probe-win.txt,round23b-win.txt,round23c-win.txt,round23-rrev-compare.txt}`；统筹代证 `.temp/hw-coord/probe-170x-eckit6{,-failtests}.txt`。
- 回合 24 新增载体：设备 `~/tmp/uc2/QDR-1009-E02/{round24-args.log,round24-args2.log,probe-round24-args.sh,probe-round24-args2.sh}`；
  Windows `.temp/QDR-1009-E02/logs/{round24-args-win.txt,round24-args2-win.txt,round24-conan-render-win.txt}`、`eckit-draft/conanfile.py`（配方活文件副本）。

## 回合 24：逐项 `test_skipped` 落地（统筹 18:30 定档后的配方实现）

**定档**：统筹确认 §10 的"个别用例平台受限逐项 `test_skipped` 附技术原因"档成立（216 注册 / 211 真跑 / 5 逐项豁免），分母不缩、用例不删、不重分类。

**实现机制（取官方支持的最小注入点，非造假）**：本树生成器 = **Unix Makefiles（GNU Make 4.4.1 musl / ctest 4.4.3）**，`Makefile:91` 的 `test` 规则原文是 `ctest $(ARGS)` ⇒ 在配方 `build()` 内改为
`cmake.test(build_tool_args=['ARGS=--output-on-failure -E "^eckit_test_(container_sharedmemarray|filesystem_filemode|log|maths_floating_point_exceptions|safe_casts)$$"'])`，
即由 CMake/CTest 自己的 `--exclude-regex` 逐条排除那 5 个**逐字名**，其余 211 项在同一 `cmake.test()` 门内真实执行（`build()` 仍调用测试，不是整体跳过）。

**写法取证（踩坑留证，不隐藏）**：
- 单引号形态（`-E '^...$'`）在本设备**失败**：`/bin/sh: no closing quote`、`make: *** [Makefile:91: test] Error 1`（设备 `/bin/sh` 非 GNU bash 系，报错误文案即其特征）⇒ 作废。
- 采用 **双引号 + make 的 `$$` 字面转义**：conan 侧 `cmd_args_to_string` 渲染出的整条命令为
  `cmake --build . --target test -- 'ARGS=--show-only -E "^eckit_test_(...)$"'`，退出码 0。

**零执行预验读数（`--show-only`，不跑任何用例、不新建 create）**：
- 排除后 `Total Tests: 211`；逐项点名核对：`eckit_test_container_sharedmemarray`、`eckit_test_filesystem_filemode`、`eckit_test_log`、`eckit_test_maths_floating_point_exceptions`、`eckit_test_safe_casts` **均不在列表**；
  同族兄弟 **全部保留**（`eckit_test_log_channels/callback/threads/colour/json/tcp`、`eckit_test_maths_floating_point_exception_FE_INVALID/INEXACT/DIVBYZERO/OVERFLOW/UNDERFLOW`）⇒ 锚定有效。
- **反例坐实"必须锚定"**：正则去掉末尾 `$` 后 `Total Tests: 205`（连带误排 11 项）⇒ 若不加 `^...$` 就是缩分母，本配方不采用。

**判据不空转的反证**：同一建树内单跑 `ctest -R '^eckit_test_container_sharedmemarray$'` → `SIGSYS***Exception 0.27 sec`、`0% tests passed, 1 tests failed out of 1`、`SOLO_RC=8`、`MEMCAP peak=3MB` ⇒ 该项确会失败，豁免是"平台受限"而非"根本没跑"。

**测试账本口径（本回合起）**：注册 **216**；create#5/#6 **全量真跑 216**（211 通过 / 5 失败，两次独立读数 93.01s 与 91.07s）仍是"5 项为何失败"的一手证据、保留不删；create#7 起 `build()` 门内 **执行 211 / 通过 211 / 逐项豁免 5**（每条技术原因与签名见「回合 23 定案」表，配方注释同步内联）。
## create#7 终态读数（2026-10-11 设备 18:40:22 起槽 → 19:12:34 前结束，一手日志 `~/tmp/uc2/QDR-1009-E02/create-eckit-7.log`）

**端到端出包成功（本包第一次真产出 package）**：
- `CREATE_RC=0`、`ELAPSED_S=1725`、`MEMCAP[run] peak=518MB budget=4000MB rc=0 用时1721.9s`、`SLOT_DONE:ok MemAvailable=11857MB`（单槽持有，全机槽位实测见 `SLOT_OK 18:40:22` 行原文）。
- **RREV `af53dddb9db893da77840448aaacd542`**（`Exported: eckit/2.0.7#af53dddb9… (2026-10-11 10:40:23 UTC)` = 设备 18:40:23 CST）；
  **PKID `ac5dbe63be94cf44531a6b18ac4b40fa5a84d380`**；**prev `fdf860f04e9fbcbc0a77cff57c489aa7`**
  （全文引用 `eckit/2.0.7#af53dddb9…:ac5dbe63…#fdf860f0…`）。
- 构建/包目录 `p/b/eckit009e86d8d68b9`（`b/` 与 `p/` 同级）：**该目录名按 build request 生成、不等于 rrev 前缀**（延续回合 23 闭合结论）；
  待验证 HEAD = `20303bf4c8bab34f13c22410e5ff8b2420599a24`（逐项豁免门那次提交）。

**`build()` 门内 ctest 原文读数（同一次执行，不补跑）**：
- `100% tests passed out of 211`；`Total Test time (real) = 96.43 sec`；末项 `211/211 Test #211: ECKIT-166.sh ... Passed`。
- Label Time Summary：`eckit = 96.07 sec*proc (211 tests)` / `executable = 86.87 sec*proc (193 tests)` / `script = 9.21 sec*proc (18 tests)`。
  ⇒ **193 + 18 = 211 执行**；静态 `executable` 标签 198 减去本次逐项豁免的 5 项恰为 193（5 项全带 executable 标签），
  与"注册 216 = 198 executable + 18 script"完全对齐：**没有减用例、没有缩分母，只是逐项 `test_skipped`**。
- **被豁免的 5 项仍然被编译并链接**（一手行号：`958/959/960` sharedmemarray、`1006/1010/1011` filesystem_filemode、`1381/1385` safe_casts 等 `Built target` 原文）
  ⇒ 排除只作用在 ctest 执行点，不删目标、不改判据、不动 CMakeLists。

**test_package 消费者测试在同一次 create 内真实执行**：
- `3134:======== Testing the package: Building ========` → `clang++ -std=c++17 test.cpp -o test_probe … -DTARGET_SO='"…/libeckit.so"' -leckit`；
- `3139:======== Testing the package: Executing test ========` → `RUN: bash -c './test_probe'`；
- 断言输出（原文）：AEC 往返 `4096 -> 1804 字节（压至 44.0%）逐字节一致`、`SystemInfo OK: dynamicLibraryName(eckit)=libeckit.so …（OHOS 走 SystemInfoLinux）`、`eckit 2.0.7: 全部断言通过`。

**结论边界（不夸大）**：create#7 的 rc=0 只坐实 **W3 构建+上游测试门+消费者测试**这一档，
**不等于 published**（未 upload），也**不等于可提审**。
**W4 独立审计读数（第 3 轮，审计窗 `QDR-1009-CIB` 对 tip `6182ea63e`，全程只读）**：`P0=1 / P1=3 / P2=3 / P3=3`，**放行 = NO**；
唯一 P0 为仓库真闸 `scripts/ohc/preflight.py` 的 PF8「纯库包不应有 commands.json」（base=`cad4baeda` 与 `upstream/main` 双次 `rc=1` fail-closed），
本回合按审计窗给出的唯一合法修法在 `package_info()` 声明 `bindirs = ["bin"]`（实包确有 `bin/eckit-version` 35328B，与 `package_type=library` + 包级 `commands.json(binary:true)` 三者自洽）。
**该改动会产生新 rrev ⇒ 上述 create#7 的 `RREV af53dddb9db893da77840448aaacd542` / PKID / 211 读数 / peak 518MB 全部降级为"历史有效证据"，不再是当前 tip 的 W3 证据**；
按派单边界本回合**不起第 8 次 create**，重跑与证据重绑留待统筹下一派单。
`conan-verify`/`finish` 仍未推进（二者必然再走一次 `conan create`），亦未 push、未建 PR、未提审。

---

## create#8 终态读数（回合 27，本回合唯一一次真机 create；当前权威 W3 证据）

上一节"本回合不起第 8 次 create"是**回合 26 的边界**，已被统筹回合 27 派单取代：本回合恰好起 1 次 create，并把全部读数绑到该次新产生的 rrev。

**构建门顺序与实测（全在一手日志头部）**：`gate.sh 8000` → GATE_PASS（MemAvailable=11520MB；inode/容量本设备 `df -i/-h` 只打表头，故自核 `stat -f`：Inodes Total=48,455,677 / Free=40,869,112；编译器进程 1）→ 本窗私有快照 `build-slot.QDR-1009-E02.sh --wait 3600 --mem 8000` 于 12:27:56 `SLOT_OK`（共享锁路径 `$HOME/tmp/uc2/.build-slots` **未改**；基准 2 槽中另一槽由 QDR-1009-E07 的 c-ares 合法持有，本窗只取 1 槽、未起第 3 槽、未动他人进程/产物）。

**独立 CONAN_HOME 与 clean-room 前置**：`CONAN_HOME=~/tmp/ch/home-QDR-1009-E02-eckit`，只从已验证 home 复制 `global.conf`（含 `tools.build:jobs=2`）+ **根级 `remotes.json`** + profiles；先跑非构建预热 `conan install . --build=never -pr:h=ohos-aarch64 -pr:b=build-native` ⇒ `WARM_RC=0`，8 节点依赖二进制在 `ohpcd` 远端可得（不靠继承缓存，也不靠 `--build=missing`）。

**memcap 评估口径**：本包无独立可喂大输入的被测二进制可做单项 `--probe`（派单要求的峰值由整轮执行器实测承载）⇒ `memcap-run.py --mb 4000` 包裹 create，终态 `MEMCAP[run] peak=426MB budget=4000MB rc=0 用时 1766.7s`；峰值写入 `test_package/MANIFEST.yml` 的 `measured_peak_rss_mb: 426`（预算字段 `max_rss_mb: 4000` 不变）。历史对照 peak：#7=518 / #6=460 / #5=442 MB。

**终态与修订绑定**：`CREATE_RC=0`、`ELAPSED_S=1776`；
RREV `0467f30b8ac1050fbd32683f9ea7c8a9`（Exported 2026-10-12 04:27:58 UTC）/ PKID `ac5dbe63be94cf44531a6b18ac4b40fa5a84d380` / prev `d387e6767143aef1b53b849af3d5d520`；
Full package reference `eckit/2.0.7#0467f30b…:ac5dbe63…#d387e676…`（一手行 `3154`）；build+package 目录为新家 `p/b/eckite1a6be7ff5cfc`。
PKID 与 create#7 相同属预期（`package_id` 由 settings/options/requires 派生，不含 recipe rev），**rrev 才是修订判据**；本次 rrev 与配方输入最后一次改动的祖先提交 `4cf7ef21869ff7882a7dc7745ce4c93a665c4eff` 上 `conan export` 复算同值（回合 30 更正：此处原文写的是 `f2c5a9cdc`，那是回合 28 换线时被丢弃的旧线提交，`git merge-base --is-ancestor f2c5a9cdc HEAD` 实测返回 1 ⇒ NOT-ANCESTOR，不再作为绑定载体；`git diff --stat 4cf7ef218 HEAD -- archives/e/eckit/2.0.7/conanfile.py archives/e/eckit/2.0.7/conandata.yml archives/e/eckit/2.0.7/patches/` 为空，故该祖先即"输入未变"的证明点）。

**上游测试门（同次执行原文）**：`2148:100% tests passed out of 211`；`2155:Total Test time (real) = 100.94 sec`；Label Time Summary `executable=193 / script=18 / eckit=211` ⇒ 193+18=211 执行，静态 `executable` 198 减逐项豁免 5 = 193，与"注册 216 = 198+18"对齐：**未删用例、未缩分母**。

**零执行自证（同一 rrev 的构建树）**：`ctest --show-only` ⇒ `Total Tests: 216`；加锚定 `--exclude-regex "^eckit_test_(container_sharedmemarray|filesystem_filemode|log|maths_floating_point_exceptions|safe_casts)$"` ⇒ `Total Tests: 211`，11 个同族兄弟全部保留（`eckit_test_log_callback/channels/colour/json/tcp/threads` + `eckit_test_maths_floating_point_exception_FE_DIVBYZERO/INEXACT/INVALID/OVERFLOW/UNDERFLOW`）；去掉尾部锚定为 205 ⇒ 不采用。计数以 `Total Tests:` 行为准（`grep -c "Test #"` 得 117/112，不是 ctest 口径）。

**被豁免 5 项在本轮的真实结果（同一 rrev 建树逐个真跑，不是"声称跑过"）**：
`ctest -R "^(…5 个锚定名)$"` ⇒ `0% tests passed, 5 tests failed out of 5`，`Total Test time (real) = 0.51 sec`，
`3 eckit_test_container_sharedmemarray (SIGSYS)` / `19 eckit_test_filesystem_filemode (Failed)` / `57 eckit_test_log (Failed)` / `69 eckit_test_maths_floating_point_exceptions (Failed)` / `154 eckit_test_safe_casts (Failed)`；
#154 本轮一手失败内容为 `eckit::Exception: Bad cast: Value too large to cast to signed type`（runner 自报 `1 tests failed out of 6`）。
五项 root cause 与"平台受限 / 非本次适配导致"的逐条归因见「回合 23 定案」表（#3 seccomp RET_TRAP on `semget/190`、#19 HMDFS 默认文件模式 660、#57 `popen` 子进程、#69 musl `fenv` FE_* 契约、#154 上游断言与交叉编译数值强转契约），本轮复现的失败签名与该表一致 ⇒ **逐项 `test_skipped` 的技术原因在当前 rrev 上重新坐实**。
本轮 build 日志中 5 个目标各仍有 1 条 `Built target eckit_test_…` 原文 ⇒ 排除只作用在 ctest 执行点。

**包内容实测（PF8/P0-1 从论证变为事实）**：`bin/eckit-version` 35,328B 在位，以 `LD_LIBRARY_PATH=<pkg>/lib` 真跑输出 `2.0.7` rc=0（peak 2MB）；`lib/libeckit.so` 3,189,248B 等 5 个 `.so` 在位 ⇒ 与包级 `commands.json(binary:true)` + `package_info` 的 `bindirs=["bin"]` 申报在当前 rrev 上一致。

**test_package 在同一次 create 内真实执行**：`RUN: clang++ -std=c++17 test.cpp -o test_probe … -leckit -Wl,-rpath…` → `RUN: … bash -c ./test_probe`；五组断言原文逐条打印（版本 2.0.7/宏/int 20007、MD5 三个 RFC 1321 向量、`Tokenizer OK: "a:bb:ccc" -> 3 个 token`、AEC 往返 `4096 -> 1804 字节（压至 44.0%）`、`SystemInfo OK: dynamicLibraryName(eckit)=libeckit.so …（OHOS 走 SystemInfoLinux）`），末行 `eckit 2.0.7: 全部断言通过`。

**结论边界（不夸大）**：create#8 的 rc=0 只坐实 **W3 构建 + 上游测试门（豁免后 211/211，注册分母 216）+ 消费者测试**这一档，**不等于 published**（未 upload），也**不等于可提审**：W4 第 4 轮独立审计未做、`reports/audit-result.json` 须由审计窗出具、CI 未开始、未 push、未建 PR、未提审。一手日志 `round27-create-eckit-8.log`（281,714B，sha256 `43f99373ad34309e2ebf45542ce5f4984705e999267e8b12f98b2a24c72fbdbd`）已双侧同 sha256。

---

## 回合 28（2026-10-12）基线收敛：rebase 到最新 upstream/main + 官方 result.json 落盘

**为什么要做**：分支基点 `cad4baeda` 落后官方 `upstream/main` **344** 提交（不是此前自报的 32——32 是对本地 `origin/main` 的旧读数）。不 rebase 就建不了 PR，且两点 diff 面会把**他窗 `knowledge/drafts/*` 的删除**带进本 PR（实测面 1934 files / 192941 deletions，全属陈旧基线假象）。

**做法（无 force、不动他人）**：`git fetch upstream`（`upstream/main` = `01438b6e61889a90d2e9be3d7cff8476b078f7c7`，2026-10-12 12:34:52 +0800）→ `git checkout -b rebase/15039-tmp upstream/main` → `git cherry-pick cad4baeda..af0d32363`（本窗 9 个提交，**逐个 CP_RC=0、零冲突**）→ `git branch -f fix/eckit-2.0.7 rebase/15039-tmp` → 切回本名分支。分支名 `fix/eckit-2.0.7` **一字未改**（PF9/import-fix 口径接受 `fix/`，不得改名）；旧 tip `af0d32363` 在 `fix/eckit-2.0.7@{1}` reflog 可回捞；未 push、未建 PR。

**为什么不用 `git rebase --autostash`**：本 worktree 在 HMDFS 上**结构性无法**进入"干净树"——`archives/l/libXext/README.md` 与 `manifest.yaml` 因大小写叠写恒为 unstaged（§5.1 幻影）。实测 `rebase --autostash` 建出 autostash `3fde31ae5` 后仍报 `cannot rebase: You have unstaged changes` 并**原样回滚**，两文件 sha256 前后一致（`26bd9228…`/`f85a944d…`），`git stash list` 空 ⇒ 无残留、他人文件未被改动。改用"新分支 + cherry-pick"绕开该限制。

**rebase 后读数（回合 28 当刻快照，已被后续提交推进，保留不删以维持更正可追溯）**：当时 `behind = git rev-list --count HEAD..upstream/main` = **0**；`ours = upstream/main..HEAD` = **9**；三点 `upstream/main...HEAD` = **9**；PR 面 `git diff --stat upstream/main HEAD` = **10 files changed, 772 insertions(+), 21 deletions(-)**，只含 `archives/e/eckit/2.0.7/*` 与本窗 `knowledge/drafts/DRAFT-eckit-2.0.7-ctest-anchored-per-case-exclusion.{kv,md}`，**不再含任何他窗 drafts 删除**。当刻 tip = `d2fc2f237b5a169910b08e2965e60c9cbf584ab3`。

**回合 32 当刻读数（快照，取代上一行的"提交前当刻"口径；回合 32 实测，2026-10-13 12:07:24 设备本地，取代上一行的"提交前当刻"口径）**：命令与取值（本窗在设备 worktree `~/qzy/QDR-1009-E02-eckit-2.0.7` 直测，非转抄他人读数）——`git -C $R rev-parse HEAD` = **`df395a2f1c835a3bfcb853ab25660ea47757f26f`**（branch `fix/eckit-2.0.7`，即"W4 r3 pass 审计件入库 + `result.json` 官方重出"那一提交）；`git -C $R rev-list --count HEAD..upstream/main` = **0**；`git -C $R rev-list --count upstream/main..HEAD` = **15**；`git -C $R rev-list --count upstream/main...HEAD` = **15**；`git -C $R diff --stat upstream/main...HEAD` 末行 = **`13 files changed, 1085 insertions(+), 22 deletions(-)`**。13 个文件 = 上一行列出的 12 个 + 本窗新入库的 `archives/e/eckit/2.0.7/reports/audit-result.json`（93 行 / 15971 B / sha256 `a52df25e201dfc28e140e63a491800db7c946859f623881862b3f4e332de45e0`，QDR-1009-CIB 第三轮独立 W4 的 pass 判决件，逐字节原样入库、owner 未改一字、未自审）。**算术自洽**：`992 + 93 = 1085`；`result.json` 重出后在 diff 中仍计 **+35**（`wc -l`=34，末行无换行符 ⇒ 与回合 30 入库时的 +35 相同，对增删数无净影响）；deletions 仍 **22** 未变。双路核对：提交前先在暂存区预测 `git diff --cached --stat 01438b6e61889a90d2e9be3d7cff8476b078f7c7` 末行 = `13 files changed, 1085 insertions(+), 22 deletions(-)`，提交后在 `df395a2f1` 上实测逐字相同。上一行那组读数取自本回合第一次提交**之前**的 tip `0f66abcd1d4f50b1f8f2d699fdeaf346170283f7`（12:07:06 实测 behind=0 / ours=14 / 三点=14 / `12 files changed, 992 insertions(+), 22 deletions(-)`），保留不删以维持更正可追溯，不作当前 PR 面引用。本行所属的文本重绑提交只改本文件 2 行且 1:1 行数不变（`git diff --numstat` 应为 `2 2`，`wc -l` 恒 394），故 **13 files / 1085 insertions / 22 deletions 在该后续 tip 上仍逐字成立**；再往后任何新提交会使 ours 再 +1。tip 的最终绑定仍由 `result.json`（官方生成器 `--commit-hash`，现绑 `0f66abcd1…`）与 `manifest.yaml` 的 `evidence.tip_before_this_commit` 承载，本行不写"含本次提交后的 tip"以免自指。 **本行的 1085 / `df395a2f1` 组读数已由下一段「回合 34 重绑」在本窗实测中取代，保留不删仅作当刻快照与更正可追溯。**
**回合 34 重绑（本窗 2026-10-13 设备本地直测；**本行的 13 files / 1099 / 22 与 ours=19 / 对称差=301 组读数现定性为回合 34 当刻快照，已由文末「回合 35」段在同一交付面实测中取代，保留不删仅作当刻快照与更正可追溯**；命令与取法与上两段一致，非转抄他人读数）**：被审 tip = 本次重绑提交的前一个提交 = `931796d852b71b6b4b32c835a48d31dec7ee235a`（线上 PR #15543 head 与设备 `git rev-parse HEAD` 同值）；本窗重绑提交是分支最后一个提交，其 SHA 不能写进本文件（文件不含自身提交号，属自指），由 `result.json` 的 `commit_hash` 绑定与本段的 `--stat` 读数共同承载；本 PR 自身提交数 `git rev-list --count 01438b6e6188..<重绑提交>` = **19**；同一 tip 上对称差口径 `git rev-list --count upstream/main...HEAD` = **301**（= 19 + 被推进的上游侧 282），该对称差不代表 PR 提交数、不用于申报；`git diff --stat upstream/main...<重绑提交>` 末行 = **`13 files changed, 1099 insertions(+), 22 deletions(-)`**（提交前先在暂存区预测同一末行、提交后在同一 tip 上实测逐字相同；本提交只改 notes.md、`manifest.yaml`、`test_package/MANIFEST.yml`、`result.json` 四个早已在面内的文件，不新增/删除任何文件 => 文件数仍 13，与 `931796d852` 上的 13 files / 1101 / 22 同一集合）。**跟踪引用漂移必须如实记录**：本窗实测 `git rev-list --count HEAD..upstream/main` = **282**，成因是他窗 `git fetch upstream` 把共用的远端跟踪引用 `upstream/main` 推进到 `f6a25613daaf1aec7170321c249d6ccf3f329593`；`git merge-base upstream/main HEAD` 实测仍 = `01438b6e61889a90d2e9be3d7cff8476b078f7c7` => 三点 PR 面不受该引用推进影响，而两点 diff `git diff --stat upstream/main HEAD` 因此膨胀为 `2493 files changed, 5568 insertions(+), 829120 deletions(-)`（**该组两点读数取自落盘前 HEAD `931796d852…` 的当刻值；同一 tip 落盘后实测 insertions 为 5566**，差 2 = 该笔提交对 notes.md/manifest.yaml 的净增减），该形态**不是**本 PR 的变更面、一律不引用；两点数值随跟踪引用漂移而变，本窗起一律不复制具体数。本窗未做新的 rebase（回合 28 已把基线收敛到 `01438b6e6…`，再重基属历史形态改动且统筹本轮未要求）。

**证据是否需要重跑（结论：不需要，且不得再起第二次 create）**：rebase 未改配方输入——`conanfile.py` blob 仍是 `3ed03b33469093abde44b42db00f20d9efbdc262`、`conandata.yml` blob `9d2f051c5cfcc5979f6bac2c64b2c41a28de2647`、`patches/0004` blob `9bdef45b26143b47363eee1893875a484b86eb2e`（0001-0005 逐字未变）；官方 `exports` 只含 `conanfile.py + conandata.yml + 5 patches`。非构建复算实测 `conan export` ⇒ **`eckit/2.0.7#0467f30b8ac1050fbd32683f9ea7c8a9`（2026-10-12 06:16:36 UTC）与 create#8 同值**，PKID `ac5dbe63…` / prev `d387e676…` 不变 ⇒ 本文件的五维账本与 create#8 端到端读数在 rebase 后的当前修订上继续有效；构建门（gate/slot/memcap）因此**未被触发**，本回合真机零构建、零占槽。

**result.json 官方生成（回合 32 重出，取代上一行读数；两个旧哈希在此显式定性、仅作更正可追溯，不作当前证据引用）**：本窗按派单口径改用官方入口重出终态件，参数经设备侧脚本 `~/tmp/uc2/QDR-1009-E02/gen-result-32.sh`（md5 双侧 `299c475997c42c2dd62f96e997339549`）传递，命令原文 `python3 scripts/ohc-run.py result eckit 2.0.7 --status partial --branch fix/eckit-2.0.7 --commit-hash 0f66abcd1d4f50b1f8f2d699fdeaf346170283f7 --agent QDR-1009-E02 --no-ci-verify --force --out archives/e/eckit/2.0.7/result.json` 加 `--failed-reason`/`--summary`/`--checkpoint` 三条。首跑被**官方校验器**拒绝，原文 `❌ result.json 校验失败: summary 长度 > 500 / 未落盘`，`RES_RC=2` 且旧件 2139 B **未被破坏**（协议的"禁手写 JSON 绕过校验"真实生效）；把 summary 压到 418 字符后 `RES_RC=0`（2026-10-13 00:30:51 设备本地）。回合 32 当刻入库件快照（tip `df395a2f1`）实测 **2250 B / `wc -l`=34 / sha256 `8b2da088ac148d324e9a8917763f7c90ad3ba7156de0427651040680079c74b6` / blob `06276175ea524add3ab75411bfc9630a0d77e739`**，`status=partial`、`feedback_pending=true`、`agent=QDR-1009-E02`、`branch=fix/eckit-2.0.7`、`error_type=partial`，其 `commit_hash` 逐字等于生成当刻的 `git rev-parse HEAD`（`0f66abcd1d4f50b1f8f2d699fdeaf346170283f7`）——以上整组现定性为 `df395a2f1` 当刻快照，不作当前证据引用，`summary`(418 字符)/`error_detail`(214)/`checkpoints`(4 条) 已全部改写为发布交付轮口径 ⇒ 审计 **W4-R5(P3)** 的"新标识 + 旧叙述"消除、**W4-R8(P2)** 所指的本行陈旧断言由本次重绑闭合。旧读数定性：`d7d4dc45d865aa2453f314cc68428b5f506b0cf2d31d6761c8b57f6649633c9d`（2139 B）＝回合 28 落盘当刻读数、该版本**从未入库**；`198238308e8f3752a7b6ff06822dfd803a3231dbff4678bed60d4ef50e16d962`（2139 B，tracked blob `004eb51257d2fa6ca20bd88f7d0b2e8dadfc5876`）＝回合 30 重出并入库、在被审 tip `0f66abcd1` 上仍是 tracked 内容——W4-R8 的定档理由正是上一行只写了前者。**未手写、未手改 JSON**。入库口径（回合 30 坐实、本窗沿用）：`result.json` 位于版本目录根、不在 `.gitignore` 覆盖范围内（实测 `git check-ignore -v archives/e/eckit/2.0.7/result.json` 无输出），仓内已有 5 例把它入库；`reports/audit-result.json` 虽命中第 96 行 `reports/`，本窗按仓内先例 `git add -f` 入库——实测 `git ls-files` 中 `/reports/` 跟踪项 **2964** 个，其中 `reports/audit-result.json` 大量存在（抽样含 `archives/e/ee/3.2.2`、`archives/e/embedmq/1.0.1`、`archives/e/extra-cmake-modules/6.26.0`、`archives/e/extra-cmake-modules/6.28.0`），json-glib 15472 把 pass 件原样入库为同型先例。被 `reports/` 覆盖而未入库的是审计**输入**件 `reports/audit-input.json`（设备侧 157864 B 载体），两者不得混谈。 **回合 35 重绑后的当前入库件实测（在本次最终交付提交上取 `git show :<路径>` 的入库对象，与本窗暂存前工作区字节逐字相同）**：bytes = **2129 B**、`wc -l` = **28**（本文件一律采换行数口径：`git show HEAD:<路径> | wc -l`；本件末行无换行符，故逻辑行数 = 29 = wc -l + 1，回合 34 此处误写 27 即把逻辑行数当成了 wc -l，CIB r5 在本 tip 实测为 26；**本件的权威身份由下面的 sha256 + blob 承担，行数列仅作辅助并已注明口径**）、sha256 = **838552457b5bafc005cc9b4da664d94804130d794b4bf1e852082482ab0a5b49**、blob = **ef35d0568a731cd70ecff165f248f9c7f08e5f92**；文件内 `commit_hash` 字段 = `9b9d4e3d4602231815e7cefcd42b5bb3562e0fd8`（= 携带本件那个提交的前一个提交，即 CIB 第 5 轮的被审 tip），属仓内先例 `archives/l/libxmu/1.3.1/result.json` 的 `lag_commits=1` 形态——`commit_hash` 逐字等于携带它自身的提交在数学上不可达，本窗按统筹裁决采「绑最终内容提交 + 此后不再追加任何提交」，不把 result.json 移出 PR 面、也不造 SHA；**本件现含 `pr_number` = 15543 与 `pr_url`**（回合 34 重出时生成调用未传该两参 ⇒ 字段缺失；CIB r5 判为可闭合回归而非不可达限制，依据 = 官方生成器 `scripts/ohc/result_report.py` 的 `--pr-number`/`--pr-url` 在 :412-413 定义、:495-504 取值链、:594-597 仅在非空时写入）；`status=partial`、`agent=QDR-1009-E02`、`branch=fix/eckit-2.0.7`、`feedback_pending=true` 与本段上方一致，`summary`/`error_detail`/`checkpoints` 已改写为回合 35 口径（summary 478 字符、checkpoint 171 字符，官方校验器 `RES_RC=0` 真实落盘，未手写、未手改 JSON（AGENTS §9）。

**result.json 重生成义务**：本文件的 §10.1 口径句已含 `211/216（97.7%，全量真跑档 create#6）与本 run 211/211（100%，create#8）` 同句并列，故五维账本在 notes.md / `test_package/MANIFEST.yml`（`upstream_test_totals` + `upstream_test_totals_fullrun`）/ `result.json` summary / PR 正文候选四处同源；若后续任何一处被改且其改动进入 `exports`（conanfile.py/conandata.yml/patches）⇒ rrev 变 ⇒ `result.json` 与全部端到端读数过期，必须在同一次 create 上重取并重生成，本窗不手改 JSON。

**登记行（本窗自身动作）**：`registry-commit --task 15039 --package eckit/2.0.7` 仍 **RC=3** 被拒，逐字文案 `拒绝混入未点名任务：lbcd/3.5.2, libebml/1.4.5, liblscp/1.0.1, metabat/2.18, music/1.2.1, proxycheck/0.49a, vbindiff/3.0-beta5`（**列表里没有 eckit/2.0.7** ⇒ 拒因是共用 CSV 上他窗未提交行，非本窗行内容问题）。按派单"仍被拒就留现状"：未整表冒签、未 `git add -A`，本窗备注留在工作区待统筹收敛。

**边界复述**：零 push、零建 PR、零 trigger-ci、零提审；W4 第 4 轮独立审计不得自做，本回合产出即为"可交独立 W4"的状态：当前 tip + 未变的 rrev + 官方 result.json + 干净 PR 面。

## 回合 29（2026-10-12 16:06 派单）：统筹 16:04 实测两缺陷的处置

### 缺陷1 「eckit_adapt_libzip.cmake 未跟踪却被引用 ⇒ 按当前分支建 PR 后 worker 检出缺文件、configure 必挂」——判定：前提不成立，本窗不提交该件

一手证据链（不靠推断）：

1. 配方自己生成这个文件：conanfile.py:106-113 是 _zip_hook = os.path.join(self.source_folder, "eckit_adapt_libzip.cmake") 紧跟 save(self, _zip_hook, ...)，:114 把它塞进 tc.cache_variables["CMAKE_PROJECT_eckit_INCLUDE"]，:165 再显式传一次 -DCMAKE_PROJECT_eckit_INCLUDE=<source_folder>/...。也就是说该 .cmake 的权威来源是 generate() 的写入动作，不是仓库里的一个文件。
2. 已验证构建的工作目录在 conan 缓存内，与 checkout 无关：create#8 日志（281714 B，sha256 43f99373...）第 147 行 Calling source() in /storage/Users/currentUser/tmp/ch/home-QDR-1009-E02-eckit/p/eckita70d456f9de4e/s，第 160 行 Generators folder: .../p/b/eckite1a6be7ff5cfc/b/build/Release/generators，第 174 行 Calling build()。
3. 构建产物里该件确实在盘并被用：缓存实测 .../p/b/eckite1a6be7ff5cfc/b/eckit_adapt_libzip.cmake = 207 B、mtime 2026-10-12 12:28（起槽 12:27:56 之后、在本次 create 窗口内）、sha256 d12b59688086f0a23bcc56b194ffaf6b1ab3d01309963c19f14b33a7e489c559。
4. checkout 里那份 ?? 是预热副产物：同一日志第 48-53 行是那次非构建 conan install（Generators folder=~/tmp/uc2/QDR-1009-E02/warm27/build/Release/generators，此时 source_folder 就是 checkout 目录），第 53 行打印的 -DCMAKE_PROJECT_eckit_INCLUDE 才指向 archives/e/eckit/2.0.7/...；该副本 207 B、mtime 12:27、**sha256 与缓存那份逐字相同（d12b5968...）**。
5. 提交它既不解决问题、还扩大违规面：conanfile.py:21 的 exports_sources 只声明 patches/*，实测导出仅复制 1 个 .py + 1 个 .yml + 5 个 .patch ⇒ manifest.yaml/notes.md/这个 .cmake 都不进 recipe 缓存。把它 add 进版本目录，worker 侧的 conan create 依然靠 generate() 现写；而归档目录多出一个非配方文件反而给静态审查（junk/白名单）新增面。

处置（本轮唯一动作=消除 ?? 风险，不改动任何配方输入）：mv 到本窗私有证据目录 ~/tmp/uc2/QDR-1009-E02/hook-byproduct/eckit_adapt_libzip.cmake（MV_RC=0，移动前后 sha256 均为 d12b5968...，未删任何文件）。之后 archives/e/eckit/2.0.7/ 的 git status 只剩 result.json 这一个工作流标记未跟踪件（该件的入库口径已在回合 30 按 P2-2 更正为**提交**，见"回合 28"节的落盘口径更正段）。

派单第 1 步要求的判据结论：**成立 ⇒ 不需要第二次构建**——理由不是「提交后树内容与已构建内容一致」，而是更强的两条：(a) 已验证构建用的那份字节与仓库外的副产物 sha256 逐字相同；(b) 本轮提交只动 manifest.yaml 与 notes.md，两者都不在 conan exports 内 ⇒ 三件套 blob（conanfile.py 3ed03b33469093abde44b42db00f20d9efbdc262 / conandata.yml 9d2f051c5cfcc5979f6bac2c64b2c41a28de2647 / patches/0004 9bdef45b26143b47363eee1893875a484b86eb2e）不变 ⇒ rrev 仍 0467f30b8ac1050fbd32683f9ea7c8a9。本轮零构建、零槽位。

### 缺陷2 manifest.yaml 陈旧（244 B / mtime 10-11 01:28 / knowledge_gained 空数组）——已重绑

- 先纠一处读数：sha256 字段本来就不是陈旧项，实测 376aa865b317d9533c1c88e1a7d15ca248420cc8a048570f3fe216e123991b51 与本包 conandata.yml 的 sources.sha256 逐字相同；真正陈旧的是 status 之后缺 build/patches_applied/tests/evidence 各段、knowledge_gained 留空数组（scripts/ohc/finish.py:440-452 正是拿它判空、scripts/ohc/submission.py 的 _scan_knowledge_gained/_scan_knowledge_ref 直接读这两个键）。
- 重写按仓内既有形态对齐（参照 archives/4/4ti2/1.6.10/manifest.yaml 的字段集合），补齐：source.tar_format、build.{system,generator,jobs,cc,cxx,configure_options,dependencies（6 个直接依赖 ecbuild/libaec/libzip/bzip2/eigen/lz4，逐条取自 conanfile.py:35-40）}、patches_applied 5 条、knowledge_gained 5 条（首条即 B判定=create 的 DRAFT stem DRAFT-eckit-2.0.7-ctest-anchored-per-case-exclusion）、knowledge_ref 指 E011、tests 五维账本（138/216/211/211/0/5、label 193+18、消费者 1 程序 5 断言、100.94 s、create#6 无豁免对照）、evidence（rrev/PKID/prev/create 读数/日志 sha/该 hook 自生成证明）、memory.max_rss_mb 4000 与实测峰值 426。
- 自指问题按可核验方式处理：manifest 无法写「含自己这次提交的 tip」，故 evidence.tip_before_this_commit 记提交前 tip，重绑后的最终 tip 由 result.json（官方生成器在本件提交之后重出）承载，两者可互相闭环核对。
- YAML 合法性：scp 后用真实 yaml.safe_load 过一遍（仓内解析器是 crude 逐行式，双引号标量里不放裸反斜杠、值内不出现空格井号，避免静默截断）。

### 五维账本四向同源（本回合复算，口径不变）

N_static=138（28 个 CMakeLists 文件里 ecbuild_add_test( 注册点，裸 add_test( = 0）→ N_registered=216 → N_executed=211 → 通过 211 / 失败 0，另 5 项逐项 test_skipped → N_consumer=1 程序 / 5 组断言。分母 216 不删不缩：注册分母口径 211/216（97.7%）与本 run 执行项 211/211（100%）同句并列；无豁免全量真跑对照=create#6（216 执行 / 211 通过 / 5 失败，91.07 s）。四处载体 MANIFEST.yml / notes.md / manifest.yaml / result.json 与 PR 正文候选同源。

## 回合 30（2026-10-12 18:00 派单）：按 CIB 独立 W4 的 NO-GO 做 P1 整改 + 补审计输入件（非新审计、非重放、零构建）

起点 tip `6e13aef88e55bc6b5af907bbec019dced13f9b27`。CIB 判 P0=0 / P1=3 / P2=4，并正证基线 behind=0 / ahead=11、create#8 rc=0、五维四处同源、峰值 426MB 对 `max_rss_mb 4000` ⇒ 三项 P1 均属文本/补件性质。本窗逐项处置如下。

### P1-2 证据-提交错绑（已闭）

改前 → 改后行号（同一文件内实测 `grep -n`）：`test_package/MANIFEST.yml` 第 **4 → 5** 行（`create8_e2e` 首句）、第 **4 行内第二处 → 同行**（"与提交 … 后 conan export 复算同值"）、第 **54 → 55** 行（`upstream_test_totals.source_round`）、第 **82-83 → 84-86** 行（`notes` 段 `Current authoritative state`）；本文件第 **261** 行、第 **290 → 290/292** 行。
- 错绑内容：把 create#8 的端到端证据写成"绑当前 tip `f2c5a9cdc`"。实测 `git merge-base --is-ancestor f2c5a9cdc HEAD` **返回 1 ⇒ NOT-ANCESTOR**（回合 28 换线时被丢弃的旧线提交），该绑定在任何后续 tip 上都不可核验。
- 修法：证据改绑"配方输入最后一次改动的祖先提交" `4cf7ef21869ff7882a7dc7745ce4c93a665c4eff`，载体＝`git log -1 --format=%H HEAD -- archives/e/eckit/2.0.7/conanfile.py`（自指规避：不写 tip，因为本文件与 `MANIFEST.yml` 自身入库）；`git diff --stat 4cf7ef218 HEAD -- conanfile.py conandata.yml patches/` 为空 ⇒ 输入未变 ⇒ rrev `0467f30b8ac1050fbd32683f9ea7c8a9` 仍为当前修订。
- tip 类读数改由两处承载：`result.json`（官方生成器 `--commit-hash`）与 `manifest.yaml` 的 `evidence.tip_before_this_commit`；`MANIFEST.yml` 新增 `baseline_30` 段记录起点 tip 与本窗实测 PR 面 **11 files changed, 887 insertions(+), 22 deletions(-)**，并把回合 28 的 `d2fc2f237` / 10 files / 772 增明确标注为"rebase 当刻快照"（保留不删，更正可追溯）。

### P1-3 B 落盘闸门：取 (a)，不过 (b)——本窗实测与 CIB 读数不一致，留证不隐藏

`ohc-run.py draft-review DRAFT-eckit-2.0.7-ctest-anchored-per-case-exclusion -p <worktree> --top 5` 的**原文输出**见下面代码块。载体两份：`~/tmp/uc2/QDR-1009-E02/r30-draftreview.txt`（id 修正前）与 `~/tmp/uc2/QDR-1009-E02/r30-draftreview-after.txt`（P2-1 修正后同 stem 重跑），两份 **1612 B、sha256 同为 `b2e247eb3668191bf3df1494e2762e4efd7f7e33d518594f6557a1505a6d0d8f`、`diff` 无输出 ⇒ 逐字相同**（实测于 2026-10-12 20:14:36；这同时证明 `id` 字段不参与该工具的判决，与本文件下文"`_parse_simple_fields` 复算 ⇒ 29 键、漏读 0 键"那段一致）。两个草稿文件在**当前 HEAD `b592bd9c30…`** 上的实测（同回合命令 `git -C $R show HEAD:<路径> | sha256sum` 与 `wc -c`/`sha256sum` 各取一遍，工作区与 HEAD blob 同值）：`.kv` = **9266 B / sha256 `f8377a34e06c295f7c36d3d30dfaac11799d856b4ba046964a494f46a3c6e2d8`**；同 stem `.md` = **10448 B / sha256 `76496fc8bf602846638d86c907ec57d4bbafb3b7209c158958498d148fb580d4`**。本句原文此前写的"（`.kv` 与 HEAD 逐字相同，9264 B / sha256 `aa68b0b8acf63d2b53aa557159fb3a8e88559cfffe164ce5de2fdffc08e935dc`）"是 **P2-1（`id` 对齐文件 stem）修正之前**那个版本在**当刻**的真实读数，但 `21af4a1ba` 把修正后的 `.kv` 入库后，该值在本文件里就成了陈旧断言 ⇒ 由本行取代；旧值保留在此仅作更正可追溯，不作当前证据引用。工具原文输出：

```text
── 草稿 DRAFT-eckit-2.0.7-ctest-anchored-per-case-exclusion ──
  标题: 平台受限的上游 ctest 用例要在 conan cmake.test() 内逐项豁免——注入点是生成器相关的 Make
  质量预检: signature=✅  root_cause=✅  rec=✅

  相似正式条目 TOP5:
    E535  score=0.25  (sig=0.38 kw=0.06 cat=0.29)
        根因: >
路径 A（基础适配）常以"上游测试需 HDF5/MPI，不可用"为由直接将上游测试写成 0/N，
未实际启用上游 CTest 核验真实通过率。实测证明该假设
    E380  score=0.15  (sig=0.23 kw=0.0 cat=0.0)
        根因: A target can expose valid MemTotal data while CMake's platform-specific host-mem
    E332  score=0.14  (sig=0.23 kw=0.05 cat=0.0)
        根因: Some upstream projects provide a GTest-compatible native runner but leave it dis
    E294  score=0.14  (sig=0.23 kw=0.04 cat=0.0)
        根因: 部分 CMake 项目在 BUILD_SHARED_LIBS=ON 时只启用公共 API 测试，依赖内部符号的完整测试仅在静态构建中生成。直接把正式包改为静态会
    E328  score=0.12  (sig=0.23 kw=0.0 cat=0.0)
        根因: 单包 Conan 适配只拥有自己的可执行入口，但上游 monorepo 还包含控制面、
前端和基础设施测试簇。若 PR 只写"执行了一个 smoke-test"

  📌 预审建议: create
     疑似新知——无高相似条目，可考虑人工审核后纳入

  ⚠️ 以上建议仅为相似度计算参考；是否纳入正式知识库由人工审核决定
  人工纳入: python3 scripts/ohc-run.py graph promote eckit-2.0.7-ctest-anchored-per-case-exclusion
```

即：**质量预检 3/3 全绿、TOP5 含 E535 0.25、建议 `create`、退出码 0**。这与 CIB 报告的"0/3 / 不在 TOP3 / 转人工审核（低质量草稿）"**在同一 tip 上不可复现**。CIB 给出的机理（`scripts/ohc/draft_review.py::_parse_simple_fields` 只认 16/29 键，故质量三元组读空）本窗也做了独立复算：按该函数逐字实现（`re.match(r"^(\w+):\s*(.*)$", line)`，跳过空行/`#` 开头/缩进行，首见去重）解析同一份 `.kv` ⇒ **29 键、漏读 0 键**，`error_signature`/`root_cause`/`rec_approach`/`rec_command` 四个质量字段全部在解析面内。⇒ 结论取派单的 **(a)**：`.kv` 字段形态已在官方解析器的识别面内，不需要重写、**也没有可举证的解析器缺陷**，因此不触发 (b) 的框架单独 PR（AGENTS §9 的"框架缺陷另开 PR"前提是缺陷可复现，本窗无法复现即不得占用该通道）。差异归因留给审计方：CIB 的读数大概率出自 `.kv` 的**早期版本**（本窗回合 25 曾把该件从 `>-` 块标量改为整档纯标量，tip `999972f49 → 6182ea63e` 之间 blob 换过），引用时未绑定 `6e13aef88`。B 判定 `create` 本身不动，落盘闸门证据（成对草稿 + 本段原文读数）齐备。

### P2-1 `.kv` 的 `id` 与文件 stem 不一致（已闭）

`id: DRAFT-ECKIT-207-CTEST-ANCHORED-PER-CASE-EXCLUSION` → `id: DRAFT-eckit-2.0.7-ctest-anchored-per-case-exclusion`（与 stem 逐字一致，对齐仓内先例 `DRAFT-10103-reptyr-ptrace-capability-boundary.kv` 的 `id` 写法）；成对 `.md` 的两处旧 ID（第 3、9 行）同步改。只改标识字段，判据/签名/复现/对照表内容一字未动。

### P1-1 审计输入件（新授权，本窗自跑）

在本窗 worktree 跑官方 `scripts/pre_pr_audit.py generate --base-branch upstream/main`，产物 `archives/e/eckit/2.0.7/reports/audit-input.json`（`--output` 显式指向版本目录——默认值是 `~/tmp/audit-input-<branch>.json`，且设备 `/tmp` 只读）。**`reports/` 被 `.gitignore` 第 96 行覆盖**（`git check-ignore -v` 实测命中），仓内 HEAD 树中 `audit-input.json` 零存在 ⇒ 该件属"给审计方读的设备侧载体"，不入库、不进 PR 面，大小/sha256/N_CHANGED 由本窗汇报与 STATE 承载。**`audit-result.json` 不由本窗出**（须独立审计方在终态 tip 上出，本窗不自审）。

### P2-2 `result.json` 入库（已闭）/ P2-3 `test_package` 死参数（判定：本窗不改）

- P2-2：按 5 个先例把 `result.json` 精确提交（`.gitignore` 不覆盖它），`status` 仍为 `partial`、`feedback_pending: true`，由官方生成器重出并绑本轮文档提交，**未手改 JSON**。
- P2-3（`-DTARGET_SO=` 未被 `test.cpp` 使用 + `if False:` 死分支）：**不改**。理由＝改 `test_package/conanfile.py` 会使 create#8 里"test_package 在同一次 create 内真实编译并执行"的一手证据失效，而本轮派单明令不起第二次 create、真机零构建零占槽；该项属可读性整改，留给后续有构建配额的回合一并做，或按框架口径单独处理。此处如实记录，不冒充已修。

### 本轮构建与修订自证

起了构建＝**否**。零 `conan create`、零槽位、零 `gate.sh`；仅跑非构建的 `conan export` 复算（stdout/stderr 分文件，外层不用 `2>&1`）⇒ 文档提交后 rrev 仍 `0467f30b8ac1050fbd32683f9ea7c8a9`，与 create#8 同一修订（`exports` 实测仅 1 .py + 1 .yml + 5 .patch）。

### 边界（本轮执行口径）

零 push、零建 PR、零 bind、零提审、不自审；未碰 `scripts/`、`ci/`、`templates/`、`knowledge/graph/`、`refs/heads/backup/*` 与他人 worktree。`?? feedback/SKILL_FEEDBACK_3daeb6c6.md` 与 `archives/l/libXext/*` 两条大小写幻影按派单留作噪音，不入 PR 面、不清理。

### 收尾块生成自证（QDR-1009-CIA 接手 PR #15543，2026-10-13）

下节的收尾块由官方生成器在本 worktree 生成，非手写：命令 `python3 scripts/ohc-run.py close-archive eckit 2.0.7 built --skip-patch`（入口 `scripts/ohc/cli.py` 的 `close-archive` → `scripts/ohc/close_archive.py`，与 `finish` Step 2/10 `step2_close_archive` 同一函数）。生成器自带的编译时刻＝本次运行时刻，真实 W3 编译结束时刻以下列一手载体为准：`~/tmp/uc2/QDR-1009-E02/create-eckit-8.log`（281714 B，设备 mtime 2026-10-12 12:57）、`create-eckit-8.rc` 内容 `0`、`create-eckit-8.summary`（`CREATE_RC=0`、`ELAPSED_S=1776`、`MEMCAP[run] peak=426MB budget=4000MB rc=0`、rrev `0467f30b8ac1050fbd32683f9ea7c8a9`、PKID `ac5dbe63be94cf44531a6b18ac4b40fa5a84d380`、prev `d387e6767143aef1b53b849af3d5d520`）。状态取 `built`（W3 通过、未 upload ⇒ 不标 `published`），与 `manifest.yaml:4` 的 `status: built` 同值 ⇒ 生成器对 manifest 的重写为逐字 no-op；本次运行后排他副产物仅 `.build-closed`（`.gitignore` 已覆盖，不入 PR 面）。

本轮动作边界：零 `conan create`、零构建槽位、零 `gate.sh`；只改 `archives/e/eckit/2.0.7/notes.md` 一个受版本控制的文件。W4 独立审计件 `reports/audit-result.json` 的 `target_commit=0f66abcd1d4f50b1f8f2d699fdeaf346170283f7`；实测配方输入与 `test_package/`、`patches/` 树对象在 `0f66abcd1`→当前 tip 之间逐字相同（`conanfile.py`=`3ed03b33469093abde44b42db00f20d9efbdc262`、`conandata.yml`=`9d2f051c5cfcc5979f6bac2c64b2c41a28de2647`、`manifest.yaml`=`c42a16b5c95b17bfb1da960a0bd0c40daafaa988`、test_package tree=`8b160337d010dd24156e4a66b88285a3836c513c`、patches tree=`997986f98f1ec95c1d52f5a159d328e4e14e084e`），其间只增加文档/审计件/result.json 提交 ⇒ rrev 不变。最终 tip 的 W4 审计重绑由 CI 侧另排独立复审，本窗不自审、不冒充审计。
## 回合 34（2026-10-13 派单）：消费 CIB 第 4 轮独立 W4 的唯一 P1 —— 四载体一次重绑

被审对象 = 线上 `GET /pulls/15543` 实时 head `931796d852b71b6b4b32c835a48d31dec7ee235a`；CIB 终局件 `.temp/QDR-1009-CIB/w4-eckit-15543/audit-result-eckit-931796d852.json`（26267 B / 170 行 / sha256 `18f5fa1f4f40852a1ee512cfc8990529083bc48532ccf7068af8e3d522267c12`）判 **verdict=fail、P0=0 / P1=1 / P2=4 / P3=4、NO-GO 提审**。本窗只消费该结论，未自出、未改写任何 W4 verdict。唯一 P1（`tip-and-reading-binding-drift-across-carriers`）的四处闭合动作与落点：(a) 上方「回合 34 重绑」段给出最终交付提交上的 `--stat` 末行原值，`1085/df395a2f1` 标为当刻快照保留不删；(b) 上方 result.json 段的 bytes/`wc -l`/sha256/blob 四项改为最终 tip 实测值、旧组定性为快照；(c) `manifest.yaml` 的 `evidence.tip_before_this_commit` 刷新为 `931796d852b71b6b4b32c835a48d31dec7ee235a`；(d) 本件由官方入口 `scripts/ohc-run.py result ... --commit-hash 931796d852b71b6b4b32c835a48d31dec7ee235a --agent QDR-1009-E02 --no-ci-verify --force` 重出，与三处文本改动落在**同一次提交**（派单原文"必答四条（同一次提交内完成）"），该提交即 PR 最后一个提交。

同批处理的 P2/P3 文本项（零构建、不改 exports）：①原先把 CMakeLists 命中文件数写成 30 的三处一律改为 **28** 并附可复现 `grep` 命令——本文件内命中行号 = `36` + `330`（两处现均为 28，138 注册点与裸 `add_test( = 0` 不变；填后本文件内「旧值 30 配 CMakeLists 文件数」的表述命中数 = 0（本句已避开该字面形态，不复现该短语），第 36 行的「下表 30 个目录条目」是目录行数、另一口径，不冲突），另有 `test_package/MANIFEST.yml` 第 14 行同批改，线上 PR 正文的同一短语由本窗另行 PATCH（改正文不产生新 HEAD）；注册点 138 与裸 `add_test( = 0` 均与 CIB 独立复算一致，只有文件数 30 无法用任一形态复现，故采其读数；②`manifest.yaml` 的 `evidence.build_log` 追加限定句：同批一手载体 `~/tmp/uc2/QDR-1009-E02/create-eckit-8.summary`（3214 B / sha256 `78c68a176dbadf8bf456004492f98a96c176b9cf94fb9b0140849eba1508b8bc`）的 [7]-[9] 段是事后探针，其 `NO_BUILD_FOLDER` / `NO_PACKAGE_FOLDER` 读数出自探针脚本自身变量未设，不构成出包判定；包内容读数以该件 [6] 段与本文件 create#8 段的 `p/bin/eckit-version` 35328 B、`p/lib` 6 个 `.so` 在场为准（载体原文未删改）；③线上正文『已知限制』补 0003 能力缺失一行（`eckit::ThreadControler::kill()` 在 OHOS 降级为 no-op，应改用协作式 `stop()`）。

入库审计件的处置（CIB P2 `W4R4-shipped-audit-artifact-binds-older-tip`，取其"至少加一行指明"的替代方案）：`archives/e/eckit/2.0.7/reports/audit-result.json` 保持第 3 轮 pass 件 **逐字节原样**（15971 B / sha256 `a52df25e201dfc28e140e63a491800db7c946859f623881862b3f4e332de45e0`，本窗未改一字），其标称对象 = `0f66abcd1d4f50b1f8f2d699fdeaf346170283f7`，**第 4 轮复审结论由另件承载**（本段首行所列 sha256，路径在审计窗名下，不在 PR 面内），终局 pass 件须由 CIB 第 5 轮独立复审经单写者入库。不替换的理由是仓库官方门禁 `scripts/ohc/submission.py:1028` 的 Gate 3/4 直接读该路径并要 `verdict=pass` => 把 fail 件放进该路径会让本包自检报告自己变红，属工具语义污染而非证据改进。该件的 `ts` 分钟位是审计者生成器写出的字面形态（`2026-10-12T23:2x+08:00`），本窗不代改他人终局件字节（归属纪律），由 r5 件自然闭合。

构建与修订自证（本回合起构建 = **否**）：`git diff --stat 4cf7ef21869ff7882a7dc7745ce4c93a665c4eff HEAD -- archives/e/eckit/2.0.7/conanfile.py archives/e/eckit/2.0.7/conandata.yml archives/e/eckit/2.0.7/patches/` 为空，7 个 exports 输入 blob 与 CIB r4 逐字相同（`conanfile.py 3ed03b33469093abde44b42db00f20d9efbdc262`、`conandata.yml 9d2f051c5cfcc5979f6bac2c64b2c41a28de2647`、0001-0005 `d5f1e1a8da / fb29c6cca9 / 5183ebc987 / 9bdef45b26 / 62bdbdb93f`）=> rrev 仍 `0467f30b8ac1050fbd32683f9ea7c8a9`、PKID `ac5dbe63be94cf44531a6b18ac4b40fa5a84d380`、prev `d387e6767143aef1b53b849af3d5d520`，create#8 端到端读数继续有效；零槽位、零 `gate.sh`、未碰 `conanfile.py`/`conandata.yml`/`patches/`/`test_package/conanfile.py`/`test.cpp`；`test_package/conanfile.py` 的两处死代码（P2 `-DTARGET_SO=` 与 `if False:`）及 `conanfile.py:299` 的死 `or` 右侧按派单禁令**不改**（改它们会改 exports）；未触发 `/rebuild`、`/ai review`、resolve、`request-review`，未改 PR 标题（统筹裁决保留 `fix(eckit)` 类型位）。


## 回合 35（2026-10-13 22:00 派单）：消费 CIB 第 5 轮独立复审 GO 判决点名的文件级 P2/P3 文本项

被审对象 = 线上 `GET /api/v5/repos/OpenHarmonyPCDeveloper/build_in_harmonyos/pulls/15543` 实时 head 与本窗设备 `git rev-parse HEAD` 同值的 `9b9d4e3d4602231815e7cefcd42b5bb3562e0fd8`；CIB 第 5 轮判件（路径在审计窗名下、不在 PR 面内）verdict=pass、P0=0 / P1=0 / P2=7 / P3=3、GO 进入 CI/提审阶段。本窗只消费该结论，未自出、未改写任何 W4 verdict。

**当前权威 PR 面读数（本窗设备本地直测，取代上文「回合 34 重绑」段的当刻快照；命令与取法与该段一致，非转抄他人读数）**：本次文本闭合提交是分支最后一个提交，其 SHA 不能写进本文件（自指），由 `result.json` 的 `commit_hash` = `9b9d4e3d4602231815e7cefcd42b5bb3562e0fd8`（= 携带本件那个提交的前一个提交）与本段读数共同承载；`git rev-list --count 01438b6e6188..<本次提交>` = **20**；`git rev-list --count HEAD..upstream/main` 实测 = **282**（成因见上一段：他窗 `git fetch upstream` 把共用跟踪引用推进到 `f6a25613daaf1aec7170321c249d6ccf3f329593`；`git merge-base upstream/main HEAD` 实测仍 = `01438b6e61889a90d2e9be3d7cff8476b078f7c7`）；对称差 `git rev-list --count upstream/main...HEAD` = **302**（= 20 + behind），该对称差不代表 PR 提交数、不用于申报；`git diff --stat upstream/main...<本次提交>` 末行 = **`13 files changed, 1119 insertions(+), 22 deletions(-)`**（提交前先在暂存区预测同一末行、提交后在同一 tip 上实测逐字相同；本次提交只改 `notes.md`、`manifest.yaml`、`result.json` 三个早已在面内的文件，不新增/删除任何文件 ⇒ 文件数仍 13，与 `9b9d4e3d46` 上的 13 files / 1099 / 22 同一文件集合）。两点形态 diff 一律不引用具体数（见上一段的限定与教训）。

逐项闭合（全部文本级、零构建）：
- **P2-1**（`wc -l` 次级度量少 1）：上方 result.json 段已改为 `wc -l` = **28**（换行数口径）并写明末行无换行符 ⇒ 逻辑行数 29，同时声明本件身份由 sha256+blob 承担；回合 34 的 27 是把逻辑行数误当 `wc -l`，该句已就地改写、未删段。
- **P2-2**（同文件内 28/30 两个数并存 + 未填占位）：第 330 行改为 **28 个 CMakeLists 文件**（与第 36 行同口径，138 注册点、裸 `add_test( = 0` 均不变）；第 411 行的未填占位 `36 + []` 已填为实际命中行号 `36` + `330`，并把该句自带的旧值引述形态改掉，使本文件不再残留可被复算打回的第二个数。
- **P2-3**（`pr_number` / `pr_url` 缺失回归）：本件由官方入口带 `--pr-number 15543 --pr-url https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15543` 重出，两字段已在场（`git show :<路径>` 实测回读），未手写、未手改 JSON；滞后声明见上一段（`lag_commits=1`，绑父提交、此后不再追加提交）。
- **P3-1**（两点读数未限定）：已在「回合 34 重绑」段就地补「取自落盘前 HEAD `931796d852…`、同一 tip 落盘后实测 5566」，并按其替代方案规定本窗起两点形态一律不复制具体数。
- `manifest.yaml` 的 `evidence.tip_before_this_commit` 同步刷新为 `9b9d4e3d4602231815e7cefcd42b5bb3562e0fd8`（= 本提交的前一个提交），与 `result.json` 的 `commit_hash` 同源；不刷新就会重新制造 CIB r4 已闭合、r5 已确认闭合的「载体绑定漂移」，属本笔提交的必然后果，不是扩范围。

**本窗未动、如实留给下一写者/下一轮**：CIB r5 的 **P2-4 / P2-5**（线上正文两处 `931796d85` tip 滞后、`ours=18` 应为 19→本次再 +1、`f2c5a9cdc` 的「前身」系谱措辞与 notes.md 的 NOT-ANCESTOR 实测冲突）属平台正文写，派单明确该写权归接单后的 CI 角色，本窗不做平台写；**P2-6** 三处死代码（`conanfile.py:299` 的死 `or` 右侧、`test_package/conanfile.py` 的 `-DTARGET_SO=` 死宏与 `if False:` 死分支）在 exports 面内或会换 rrev，按派单禁令留给下一次真正起构建的那一轮一并清理并在同一次 create 上重取端到端读数；**P2-7** 官方默认 CI 管线的 profile 硬编码 `/data/service/hnp/*` 属框架侧 `ci/`（框架 PR #15461 未合入），本窗不碰框架文件，首次 CI 请求与判决解读归单写者 QDR-1009-CIB；**P3-2** 入库 `reports/audit-result.json` 保持第 3 轮 pass 件逐字节原样（15971 B / sha256 `a52df25e201dfc28e140e63a491800db7c946859f623881862b3f4e332de45e0`，本窗未改一字），r4/r5 结论由审计窗名下另件承载；**P3-3** 标题按统筹裁决保留 `【知识库扩展】fix(eckit): 2.0.7 适配 HarmonyOS PC` 未改。

构建与修订自证（本回合起构建 = **否**、零真机槽位）：`git diff --stat 4cf7ef21869ff7882a7dc7745ce4c93a665c4eff..<本次提交> -- archives/e/eckit/2.0.7/conanfile.py archives/e/eckit/2.0.7/conandata.yml archives/e/eckit/2.0.7/patches/` 为空 ⇒ 7 个 exports 输入 blob 与 CIB r5 逐字相同（`conanfile.py 3ed03b33469093abde44b42db00f20d9efbdc262`、`conandata.yml 9d2f051c5cfcc5979f6bac2c64b2c41a28de2647`、patches tree `997986f98f1ec95c1d52f5a159d328e4e14e084e`）⇒ rrev 仍 `0467f30b8ac1050fbd32683f9ea7c8a9`、PKID `ac5dbe63be94cf44531a6b18ac4b40fa5a84d380`、prev `d387e6767143aef1b53b849af3d5d520`，create#8 的端到端读数继续有效、不需要也不得起第二次 create；未碰 `conanfile.py`/`conandata.yml`/`patches/`/`test_package/conanfile.py`/`test.cpp`/`ci/`，未起 `gate.sh`、未取槽位锁，未发 `/rebuild`、`/ai review`、resolve、`request-review`，未创建/修改 PR 标题与正文。



---

**回合 38 · 2.0.7.1 端到端 create#9 一手读数落账（构建起于回合 37，本轮独立复核并补读数）**

构建判定（本窗从一手载体取值，不引用他人文本）：`CREATE_RC=0`、`ELAPSED_S=1717`、`MEMCAP[run] peak=435MB budget=4000MB`（MEMCAP 用时 1710.2s）、
`GATE_RC=0`、`SLOT_OK 17:39:33`（本窗私有快照、全机基准 2 槽、本窗只占 1 槽、未抢第 3 槽）、`jobs=2`、`CONAN_HOME=~/tmp/ch/home-QDR-1009-E02-eckit`。
命令：`conan create . --build="eckit/*" -pr:h=ohos-aarch64 -pr:b=build-native`（外层 `build-slot --wait 3600 --mem 8000` + `memcap-run.py --mb 4000`）。
一手载体：`~/tmp/uc2/QDR-1009-E02/create-eckit-9.log`（282885 B，sha256 `e4c28637ed869895d9805448540df0a3e288e14aa16413fbb230a8d9c5a3e6c5`）、`create-eckit-9.rc`（2 B，内容 `0`，sha256 `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`）、
`create-eckit-9.summary`（2507 B，sha256 `506c7c8c583855adc2581af8be3eacc76f91a8725f8f585ccaa9811b3d52638d`）。

修订三件（日志第 3155-3158 行原文，与本地缓存 `conan list` 对账一致）：
版本修订 `ec9c1763c4cb84752953546e4a58c8c7` / 包 ID `ac5dbe63be94cf44531a6b18ac4b40fa5a84d380` / 前序包修订 `878b12add91ab798519648358cb47f29`；
完整引用 `eckit/2.0.7.1#ec9c1763c4cb84752953546e4a58c8c7:ac5dbe63be94cf44531a6b18ac4b40fa5a84d380#878b12add91ab798519648358cb47f29`；
构建目录 `~/tmp/ch/home-QDR-1009-E02-eckit/p/b/eckitbeb08d077a043/b/build/Release`（日志 2161 行）、包目录 `~/tmp/ch/home-QDR-1009-E02-eckit/p/b/eckitbeb08d077a043/p`（日志 3158 行）。

上游测试五维账本（同一次 create 的 `build()` 门内，非事后补跑）：

| 维度 | 数值 | 一手来源 |
|---|---|---|
| N_static（注册入口） | 138 处 `ecbuild_add_test(`，分布 28 个 CMakeLists.txt（裸 `add_test(` = 0） | 上游 2.0.7 tag 源码静态计数；源码未变 ⇒ 沿用同 tag 口径，不是本 run 新数 |
| N_registered | **216** | `ctest --show-only`（零执行）在本 rrev 构建树实测：216 个 id、216 个唯一名 |
| N_executed | **211** | ctest 原文 `100% tests passed out of 211`（日志 2151 行） |
| 未执行 / 逐项豁免 | **5**（逐项 test_skipped，见下表） | 锚定 `--exclude-regex` 前后 216→211，差值恰 5 |
| N_consumer | 1 程序 / 5 断言组 | 同次 create 内 `RUN: clang++ ... -o test_probe` + `RUN: bash -c './test_probe'` |

Label Time Summary（日志 2153-2158 行原文）：`eckit = 94.09 sec*proc (211 tests)`、`executable = 84.89 sec*proc (193 tests)`、
`script = 9.20 sec*proc (18 tests)`、`Total Test time (real) = 94.45 sec`。
通过率口径：注册分母 216 下 211/216（97.7%），5 项逐项 test_skipped 附技术原因；本 run 执行项 211/211（100%）。

**计数口径纠正（本窗自证并披露）**：ctest 的行形态是 `Test` 后三个空格再 `#N:`，上一版探针用裸串 `Test #` 只数到 117/112；
本轮改用允许空白的匹配并只认 `Total Tests` 行，得 216/211。分母一律以 `Total Tests` 行为准，不用裸 grep 计数。

被豁免 5 项在**当前 rrev** 的逐一单跑复现（`ctest -R '^<名>$' --output-on-failure`，`memcap-run.py --mb 1500`，非构建、非 create）：

| 用例 id / 名 | 本轮结果 | 峰值 | 技术原因（非本次适配引入） |
|---|---|---|---|
| #3 eckit_test_container_sharedmemarray | `ONEOFF_RC=8`（SIGSYS） | 7MB | SysV IPC 被 seccomp 击杀：`si_code=1(SYS_SECCOMP)`、`si_syscall=190(semget)`；POSIX shm/mmap 可用而 semget/shmget/shmat/semop 被拦 |
| #19 eckit_test_filesystem_filemode | `ONEOFF_RC=8`（Failed） | 7MB | HMDFS 默认文件模式与 Unix 契约不同（知识库 E011）；断言点 test_filemode.cc:153/196/209/232/245 |
| #57 eckit_test_log | `ONEOFF_RC=8`（Failed） | 6MB | unlink 失败时 musl 不填 errno ⇒ 报错文本 `No error information` |
| #69 eckit_test_maths_floating_point_exceptions | `ONEOFF_RC=8`（Failed） | 5MB | 上游 `WILL_FAIL` 契约（216 项中仅此一项带 WILL_FAIL，期望失败未发生） |
| #154 eckit_test_safe_casts | `ONEOFF_RC=8`（Failed） | 7MB | 默认 ABI 的 char 签名差异（同树 `-fsigned-char` 对照 RC=0） |

五项峰值 5-7MB ⇒ 豁免不是为绕开内存；同族兄弟全部留存（`eckit_test_log_callback/channels/colour/json/tcp/threads`、
`eckit_test_maths_floating_point_exception_FE_DIVBYZERO/INEXACT/INVALID/OVERFLOW/UNDERFLOW`），去锚形态会多删 11 个（216→205），故不用。

包内容与产物验证（一手）：`Packaged 11 '.so' / 12 '.pc' / 5 '.cmake' / 7 '.yaml' / 1 file: eckit-version`（日志 3150-3154 行）；
`bin/eckit-version` 35328 B，以 `LD_LIBRARY_PATH=包/lib` 真跑 **rc=0**、stdout `2.0.7`、`MEMCAP peak=2MB budget=800MB`
（载体 `~/tmp/uc2/QDR-1009-E02/r38-eckit-version.out`，sha256 `b02ce8b805cd7c6b5c0d987ae938be8c052726c65595c4a66c2a433e6da50d39`）；`lib/libeckit.so` 3189248 B，
lib 目录内 11 个 `.so`、pkgconfig 12 个 `.pc`，与 `package_info` 的 `bindirs` 申报一致。
消费者断言原文（同次 create）：版本三处 `2.0.7` / 宏 / `int 20007`、MD5 三个 RFC 1321 向量、Tokenizer `a:bb:ccc`、
AEC 往返 `4096 -> 1804 字节`（压至 44.0%，libaec 已接入）、`SystemInfo dynamicLibraryName(eckit)=libeckit.so`（OHOS 走 SystemInfoLinux），
末行 `eckit 2.0.7: 全部断言通过`。输出里的 `2.0.7` 是上游版本字符串——源 tarball 就是 2.0.7 tag，本目录只是 fix 递增修订，不虚构 2.0.7.1 下载地址。

summary [8]/[9] 段的 `NO_BUILD_FOLDER` / `NO_PACKAGE_FOLDER` 定性更正：该 summary 的 [8]/[9] 段读数 NO_BUILD_FOLDER / NO_PACKAGE_FOLDER 经本窗复查是探针脚本自身的取值错误（不是构建结论）：脚本按 `Build folder: ` / `Package folder: `（带冒号）grep，而 conan 2.29.1 实际输出是 `eckit/2.0.7.1: Build folder <路径>`（无冒号），故变量为空、[8] 的被豁免项单跑与 [9] 的包内容检查被 [ -d ] 守卫跳过（oneoff-9.log / eckit-version-9.log 因此从未生成）。真实路径读数由本窗另行取证：Build folder=~/tmp/ch/home-QDR-1009-E02-eckit/p/b/eckitbeb08d077a043/b/build/Release（日志 2161 行原文）与 Package folder=~/tmp/ch/home-QDR-1009-E02-eckit/p/b/eckitbeb08d077a043/p（日志 3158 行原文），两目录均在场；包内容、bin/eckit-version 真跑与被豁免 5 项单跑读数见本地载体 r38-verify.out / r38-probe2.out / r38-probe3.out / r38-probe4.out；summary 原文未删改，保留作探针自证。
钩子自证在本轮构建树内复测：`~/tmp/ch/home-QDR-1009-E02-eckit/p/b/eckitbeb08d077a043/b/eckit_adapt_libzip.cmake` 207 B、mtime 2026-10-15 17:39、sha256 `d12b59688086f0a23bcc56b194ffaf6b1ab3d01309963c19f14b33a7e489c559`（与 2.0.7 轮次那份字节逐字相同）。
本轮 generate() 曾把这份钩子写回 checkout 的归档目录（`self.source_folder` 落点），已按 §9 移出至 `~/tmp/uc2/QDR-1009-E02/byproduct-2.0.7.1/eckit_adapt_libzip.cmake`（同 sha256，207 B），归档目录内不含它；同族先例＝HEAD 里 `archives/e/eckit/2.0.7/` 也只有 11 件、不含此 `.cmake`。`test_package/` 下 conan 生成的未忽略散件（`metadata`）同批移出，被 `.gitignore` 覆盖的 `conan*.sh`/`test_probe` 按先例留盘不入库。

本回合动作边界：只改本文与 `manifest.yaml` / `test_package/MANIFEST.yml` / 本地 `reports/test-report.md`（后者被 `.gitignore` 忽略、不进 PR），
`conanfile.py` / `conandata.yml` / `patches/` / `test.cpp` 一字未动 ⇒ exports 输入未变、rrev 不变，**不得也不需再起第 10 次 create**；
本回合零 `gate.sh`、零构建槽占用、零 `/rebuild`、零平台写、零推送。
---

**编译结束**: 2026-10-15 19:36
**最终状态**: built
