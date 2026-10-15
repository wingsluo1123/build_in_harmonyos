# iceoryx 2.0.8 — OHOS（鸿蒙 PC / aarch64）适配笔记

上游：<https://github.com/eclipse-iceoryx/iceoryx>（tarball `v2.0.8.tar.gz`，
sha256 `375b8e63…59bd9`，`tar tf | wc -l` = 1655）。

## 1. 交付形态（6 个库 + 头 + 上游 CMake 配置）

| 路径 | 说明 |
|---|---|
| `lib/libiceoryx_platform.so` | 平台抽象层（hoofs 的下层） |
| `lib/libiceoryx_hoofs.so` | POSIX 封装 + cxx 容器/工具（`DT_NEEDED` → platform） |
| `lib/libiceoryx_posh.so` | 共享内存传输（pub/sub、chunk 管理） |
| `lib/libiceoryx_posh_roudi.so` | RouDi 运行时库 |
| `lib/libiceoryx_posh_gateway.so` | gateway 库 |
| `lib/libiceoryx_binding_c.so` | C 语言绑定 |
| `include/iceoryx/v2.0.8/**` | 公共头（hoofs / posh / binding_c 三套） |
| `lib/cmake/iceoryx_{hoofs,posh,binding_c}/**` | 上游安装的 CMake 包配置（非 conan 消费者可用；conan 侧另有 `iceoryx::*` 生成目标） |
| `licenses/LICENSE`、`licenses/NOTICE.md` | Apache-2.0 原文 + 上游 NOTICE |

刻意**不**交付：上游在 `BUILD_TEST=ON` 时安装的 `libiceoryx_hoofs_testing.a`、
`libiceoryx_posh_testing.a`、`bin/iox-bm-optional-and-expected`（都是测试产物；
`package()` 里显式删除并在自检 C9 里做负向断言）。

## 2. ⚠ 重大能力裁剪：没有 `iox-roudi`（因为 cpptoml 不在制品仓）

上游 `iceoryx_posh/CMakeLists.txt` 里 `iceoryx_posh_config`（TOML 动态配置）与
**`iox-roudi` 可执行文件**都位于同一个 `if(TOML_CONFIG)` 块内：

```cmake
if(TOML_CONFIG)
    add_library(iceoryx_posh_config ...)      # 依赖 cpptoml
    ...
    add_executable(iox-roudi ...)
    set(ROUDI_EXPORT iceoryx_posh_config iox-roudi)
endif()
```

`TOML_CONFIG` 需要 cpptoml。**实测**：制品仓里 `cpptoml` 只有 `archives/c/cpptoml/`
下的 `manifest.yaml` 占位，没有真正的 recipe/package ——
`conan list -r ohpc 'cpptoml/*'` 零命中（`libmnl`/`libnftnl`/`gtest` 等都能查到，
唯独它查不到）。PF4 明确禁止在本 PR 里捎带依赖，因此：

* 本包以 **`TOML_CONFIG=OFF` + `DOWNLOAD_TOML_LIB=OFF`** 构建；
* 交付 **6 个库**，但**不交付 `iox-roudi` 与 `iceoryx_posh_config`**；
* 运行时需要消费者用交付的 `iceoryx_posh_roudi` 库自行写 RouDi 主程序（上游自己的
  测试环境 `roudi_env` 正是基于该库）。

**建议**：调度侧补一个 `cpptoml` 任务；之后本包只需把
`with_toml_config` 默认值改为 True 并去掉 patch 0002/0003，即可补回 `iox-roudi`。

## 3. 四个补丁（三个 test-harness + 一个 OHOS 平台层）

1. `0001-tests-use-conan-googletest.patch` — 上游 `iceoryx_meta/tests.cmake` 在
   `BUILD_TEST=ON` 时**无条件** `add_subdirectory(cmake/googletest)`，那份 CMakeLists
   会在 configure 期用 ExternalProject **下载并编译 googletest**（worker 无网络 ⇒
   必挂）。补丁把这**一行**换成 `find_package(GTest CONFIG REQUIRED)`，即用声明好的
   conan 依赖 `gtest/1.17.0.1`。
2. `0002-tests-tolerate-toml-config-off.patch` — `TOML_CONFIG=OFF` 时上游不创建
   `iceoryx_posh_config` 目标，而 `iceoryx_posh/test`、`iceoryx_binding_c/test` 无条件
   链接 `iceoryx_posh::iceoryx_posh_config` ⇒ 配置期报 “target was not found”。
   补丁加一个空 `INTERFACE` 替身；安装/导出集合不变（`ROUDI_EXPORT` 为空）。
3. `0003-tests-skip-toml-gateway-test.patch` — 两个 TOML 单元测试
   （`test_popo_toml_gateway_config_parser.cpp`、`test_roudi_config_toml_file_provider.cpp`）
   会 `#include <cpptoml.h>` ⇒ 从 GLOB 结果里剔除。**测试源文件本身一行未改**。
4. `0004-ohos-mqueue-stubs.patch`（**portability，无平台宏**）— 有些 C 库的
   `<mqueue.h>` 只有消息队列**类型**（`mqd_t`、`struct mq_attr`），**不声明任何
   `mq_*` 函数**、也没有消息队列运行时；OHOS 走的 `platform/unix/` 通用 POSIX 层
   直接调用这些函数 ⇒ 编译期失败（CI 原文见下）。补丁做两件事：
   (a) `iceoryx_meta/CMakeLists.txt` 增加一个**配置期探针**：用
   `check_cxx_source_compiles`（`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`，
   **只编译不链接** —— 这类库「没声明」也「没实现」，链接探针会把两种情况混为一谈）
   编译一个调用 `mq_open` 的翻译单元；失败时 `add_compile_definitions(IOX_NO_POSIX_MQ=1)`
   并打印一行 `STATUS`；
   (b) `platform/unix/` 的 `mqueue.hpp` / `mqueue.cpp` 在该宏下提供
   `mq_open/mq_close/mq_unlink/mq_getattr/mq_setattr/mq_notify/mq_send/mq_receive/
   mq_timedsend/mq_timedreceive` 与 `iox_mq_open2/iox_mq_open4` 的 `static inline`
   ENOSYS 桩（上游 mac/win 平台层同款做法），并补 `<sys/types.h>`（无 mq_* 声明的
   `mqueue.h` 也不带 `mode_t`）。
   **没有任何平台名被硬编码**（不写 `__OHOS__`，符合仓库 R8/`PF5` 口径）：判定依据是
   「这套 libc 到底有没有 POSIX 消息队列」这个能力探针本身，任何有 mqueue 的 libc 上
   补丁都是 no-op。

   CI 实证（PR !15129 build #79880，失败日志原文）：

   ```
   iceoryx_hoofs/platform/unix/include/iceoryx_hoofs/platform/mqueue.hpp:23:49: error: unknown type name 'mode_t'; did you mean 'mqd_t'?
   mqueue.cpp:22:12: error: use of undeclared identifier 'mq_open'
   .../sysroot/usr/include/mqueue.h:16:13: note: 'mqd_t' declared here
   ```

## 4. OHOS 硬坑

- **POSIX 消息队列（OHOS 没有 → 由能力探针兜底）**：OHOS 的 `<mqueue.h>` 只定义
  `mqd_t` / `struct mq_attr`，**一个 `mq_*` 函数都不声明**，也没有 mqueue 运行时
  （`/dev/mqueue` 不存在）。iceoryx 的 `platform/unix/` 层（OHOS 走这一层）与
  `posix_wrapper/message_queue.cpp` 直接调用 `mq_open/mq_send/...` ⇒
  编译期 `use of undeclared identifier 'mq_open'`。修法见 §3 补丁 4（能力探针 +
  ENOSYS 桩；本仓知识库 `DRAFT-ohos-mqueue-stub` 的推荐做法，先例 systemd/261）。
  ⇒ **能力声明**：没有 mqueue 运行时的目标上，`iox::posix::MessageQueue`（以及依赖
  它的 iceperf/`-t mq` 路径）**不可用**，构造/收发一律返回 `ENOSYS`；共享内存
  （`/dev/shm`）与 unix domain socket 两条 IPC 通道不受影响，`build()` 的 I3 判据
  也据此判定套件不可执行。
- **F（SONAME）**：OHOS 不在 CMake 平台表里 ⇒ CMake 不会给 `.so` 写 SONAME。
  配方强制 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,`，实测 6 个库均有
  `DT_SONAME`（自检 C3 逐库断言 `DT_SONAME == 文件名`）。
- **F（RPATH）**：unset `CMAKE_INSTALL_RPATH`（`CMAKE_SKIP_INSTALL_RPATH=ON`），并
  自检 C4 扫描交付库字节里不得出现 `/home/`、`/storage/`、`.conan2` 等构建机路径。
  另：`iceoryx_meta` 在 `BUILD_SHARED_LIBS` 时会自己设
  `CMAKE_INSTALL_RPATH=${CMAKE_INSTALL_PREFIX}/lib`（= conan 包目录），必须压掉。
- **F（构建树测试）**：OHOS 上 CMake 不写可执行文件 RUNPATH ⇒ 测试二进制找不到同树的
  `libiceoryx_*.so`。`build()` 执行 gtest 二进制时显式注入
  `LD_LIBRARY_PATH=<build 树里所有含 libiceoryx_*.so 的目录>`。
- **UNIX 变量**：CMake 对未知 `CMAKE_SYSTEM_NAME=HarmonyOS` **不置 `UNIX`**，而
  iceoryx 用 `if(UNIX)`/`if(LINUX)` 选择 POSIX 实现 ⇒ 显式 `-DUNIX=TRUE`
  （本仓先例：allegro4/5、cling、i2pd、libfltk、log4cplus、osslsigncode）。
  注意 `if(LINUX)` 为假还带来一个副作用：`iceoryx_hoofs` 不会链接 `acl`/`atomic`
  （上游只在 `if(LINUX)` 里链），所以 OHOS 侧不需要 libacl —— 本机 x86_64 构建时
  `DT_NEEDED` 里出现的 `libacl.so.1` 是**宿主**链接结果，与 OHOS 交付无关。
- **C++ 标准**：`ICEORYX_CXX_STANDARD` 只在 `CMAKE_SYSTEM_NAME` 匹配 Linux/QNX 时取
  14，其余（含 HarmonyOS）取 **17**。因此 OHOS 侧用 gtest 1.17（要求 C++17）没问题，
  而本机 Linux 复现需要把 gtest 换成 1.14（本地 profile 的 `[replace_requires]`）。
- **签名**：交付的 6 个 `.so` 逐个签名（`llvm-objcopy --remove-section .codesign` +
  `binary-sign-tool sign -selfSign 1 -inFile X -outFile X.signed` + `os.replace` +
  `chmod 0755`，判据是重新读回 `.codesign` 段）。

## 5. 上游测试：入口、口径与结果

上游**不使用 ctest**：`iceoryx_meta/tests.cmake` 注册的是 custom target
（`module_tests` / `integration_tests` / `all_tests`），直接执行
`./<cmp>/test/<cmp>_moduletests --gtest_filter=-*.TimingTest_*`。

`build()` 的做法：
1. 先用 `--gtest_list_tests` **枚举**每个测试二进制里的 gtest 用例数（清单口径，
   不执行）→ 5 个二进制、**4974 个用例**；
2. 探测 POSIX 共享内存（`/dev/shm` 可写）、POSIX 消息队列（`/dev/mqueue` 可写）、
   unix domain socket；
3. 探测通过则**真跑** 5 个二进制（`--gtest_filter=-*.TimingTest_*`，与上游
   `module_tests` 目标一致），逐二进制打印 `OK/FAILED/SKIPPED/executed/DISABLED`；
   任何 FAILED、rc≠0、或缺少 gtest 汇总（= 二进制没跑起来）都判失败；
4. 探测不通过则逐二进制打印「已枚举 N 个用例但**未执行**」及具体原因，**不假装通过**。

本机实测（/dev/shm 可用）：

```
[upstream] inventory: 5 test binary(ies), 4974 gtest case(s)
[upstream]   iceoryx_hoofs  module tests:      2937 case(s)
[upstream]   iceoryx_hoofs  integration tests:   25 case(s)
[upstream]   iceoryx_posh   module tests:      1649 case(s)
[upstream]   iceoryx_posh   integration tests:   83 case(s)
[upstream]   iceoryx_binding_c module tests:    280 case(s)
[upstream] iceoryx_hoofs  module tests:      rc=0 OK=2885 FAILED=0 SKIPPED=0
[upstream] iceoryx_hoofs  integration tests: rc=0 OK=0    FAILED=0 SKIPPED=0   (= 25 个用例全被上游加 DISABLED_ 前缀)
[upstream] iceoryx_posh   module tests:      rc=0 OK=1603 FAILED=0 SKIPPED=0
[upstream] iceoryx_posh   integration tests: rc=0 OK=78   FAILED=0 SKIPPED=0
[upstream] iceoryx_binding_c module tests:   rc=0 OK=260  FAILED=0 SKIPPED=0
[upstream] total OK=4826 SKIPPED=0 failures=0
```

`iceoryx_posh` 模块/集成测试包含真实的 pub/sub、chunk、`roudi_env` 端到端 IPC 断言，
是本包最强的运行期证据。

## 6. 消费者用例（`test_package/test_package.cpp`，13 项）

真链接交付的 `iceoryx_posh` / `iceoryx_binding_c` / `iceoryx_hoofs`：

- `cxx::string<32>` 拼接、`TruncateToCapacity` 截断到 8、`unsafe_append` 拒绝超长；
- `cxx::vector<int,4>` 恰好放 4 个、第 5 个返回 false；`optional`/`expected` 语义；
- `iceoryx_binding_c` 的 C API（`iox_runtime_init`）可链接；
- **POSIX 共享内存往返**：用 `iox::posix::SharedMemoryBuilder` 建
  `/dev/shm/iox_conan_consumer_probe`（4096 B），经 iceoryx 句柄 `mmap` 写入
  payload，然后由**独立的 POSIX 读者**（`open`+`pread`，完全不经过 iceoryx）
  读回并逐字节核对，再核对 `stat` 的报告大小，最后验证对象析构后确实从
  `/dev/shm` 消失、`unlinkIfExist` 报告「本来就不存在」。

## 7. 本地验证

```bash
CONFIG_SHELL=/bin/bash conan create archives/i/iceoryx/2.0.8 \
    -pr:h=le-local -pr:b=le-local --build=missing -r conancenter
# [upstream] total OK=4826 SKIPPED=0 failures=0
# consumer use case: 13 checks, 0 failure(s)
# 交付形态自检：15 项通过 / 0 项失败 / 1 项跳过（.codesign，仅 OHOS）
```

`le-local` 仅用于本机（x86_64）复现：OHPC 制品仓的 `zlib` 配方把 shell 默认成
`/data/service/hnp/bin/bash` 且强制 `CC=clang`（本机无 clang），gtest 1.17 要求
C++17 而本机 Linux 走 C++14 —— 因此本地用 `CONFIG_SHELL=/bin/bash`、
`tools.build:compiler_executables=gcc`、`[replace_requires] zlib/gtest` 过渡。
**这些都与交付配方无关**：OHOS 侧由 CI 用制品仓原生依赖构建。

### 7.1 补丁 4（mqueue 能力探针 + ENOSYS 桩）的独立复现（2026-10-10）

本机没有 OHOS SDK，因此按 CI 日志复刻一个**假的 `<mqueue.h>`**（只有
`typedef int mqd_t;` + `struct mq_attr`，一个 `mq_*` 都不声明），用它模拟 SDK
26.0.0.18 的头文件形态，逐层验证：

```bash
# ① 补丁前：复现 CI 的同一条错误（假 mqueue.h 放在 -I 最前）
g++ -std=c++14 -I fakeinclude -I <…>/platform/unix/include     <…>/platform/unix/source/mqueue.cpp
#   mqueue.hpp:23:49: error: 'mode_t' has not been declared; did you mean 'mqd_t'?
#   mqueue.cpp:27:12: error: 'mq_open' was not declared in this scope

# ② 补丁后（宏由下面的 CMake 探针给出）：platform/unix 的 7 个 TU 全部编译通过
for f in platform/unix/source/*.cpp; do g++ -std=c++14 -c -DIOX_NO_POSIX_MQ=1 \
    -I fakeinclude -I <…>/platform/unix/include "$f" -o /dev/null; done
#   file/fnctl/grp/mman/mqueue/socket/unistd.cpp 全绿

# ③ 桩的语义：22 项断言全部 OK（每个 mq_* 返回 -1 且 errno==ENOSYS）
#   OHOS-like mqueue shim: all checks OK

# ④ 真正消费这些桩的 TU 也能编过（含 mode_t / mq_unlink / mq_send /
#    mq_receive / mq_timedreceive / mq_timedsend / iox_mq_open4 全部调用点）
g++ -std=c++14 -fsyntax-only -DIOX_NO_POSIX_MQ=1 -I fakeinclude \
    -I <…>/platform/unix/include -I <…>/hoofs/include \
    <…>/hoofs/source/posix_wrapper/message_queue.cpp
#   rc=0

# ⑤ CMake 探针本身：同一份源码、两种头文件形态，configure 结果相反
cmake -S iceoryx_meta -B cfg-native   …（真 mqueue.h）
#   -- Performing Test IOX_HAS_POSIX_MQ_OPEN - Success      ⇒ 不定义宏，走上游原路径
cmake -S iceoryx_meta -B cfg-like -DCMAKE_CXX_FLAGS=-I…/fakeinclude
#   -- Performing Test IOX_HAS_POSIX_MQ_OPEN - Failed
#   -- iceoryx: <mqueue.h> declares no mq_open -> POSIX message queue stubs enabled
#   ⇒ 定义 IOX_NO_POSIX_MQ=1，编译 ENOSYS 桩

# ⑥ 非探针分支未受影响：本机 glibc 下两个 iox_mq_open* 仍走真实 mq_open
#   iox_mq_open4 rc=-1 errno=22 (EINVAL) / iox_mq_open2 rc=-1 errno=2 (ENOENT)
```

桩不会与系统声明撞车的判据（查过源码与日志原文，不是猜测）：

- OHOS 的 clang 在 **C++ 模式预定义 `_GNU_SOURCE`**（`OHOSTargetInfo::getOSDefines`，
  `OpenHarmony/third_party_llvm-project` 的 `clang/lib/Basic/Targets/OSTargets.h` 第 1053
  行）⇒ 失败那轮编译**已经带着 `_GNU_SOURCE`**，SDK 26.0.0.18 的 `<mqueue.h>` 依旧不声明
  `mq_open`（日志原文）⇒ 桩不会与系统声明冲突，而且**宏由探针按能力给出**，SDK 以后
  真带上声明时探针会翻成 Success、补丁自动 no-op。
- 桩的签名逐个对照过 OpenHarmony musl 自己那份 `include/mqueue.h`（AtomGit
  `openharmony/third_party_musl`，`mq_open/mq_close/mq_getattr/mq_notify/mq_receive/
  mq_send/mq_setattr/mq_timedreceive/mq_timedsend/mq_unlink` 九个函数的原型），
  与 `posix_wrapper/message_queue.cpp` 的调用点一致（④ 已实测）。

## R7（2026-10-12 CI #85699）— `time_mock` 的 `noexcept` 与 OHOS libc 声明不匹配

**CI 原文（类别=编译失败，失败步骤跑到 `cleanup ✅` ⇒ 真失败）**：
```
iceoryx_hoofs/testing/include/iceoryx_hoofs/testing/mocks/time_mock.hpp:44:5:
  error: exception specification in declaration does not match previous declaration
（同 45 / 46）
iceoryx_hoofs/testing/mocks/time_mock.cpp:30:5 / :40:5 / :50:5: 同类错误（共 6 errors）
make[2]: *** [hoofs/CMakeFiles/iceoryx_hoofs_testing.dir/testing/mocks/time_mock.cpp.o] Error 1
```
**根因（读上游源码定位）**：该测试 mock 在 `#if defined(__linux__)` 分支里把
`clock_getres/clock_gettime/clock_settime` **重新声明为 `noexcept`**（`.hpp` 44–46 行、`.cpp` 三处实现）。
`noexcept` 在 C++17 已是函数类型的一部分，只有当 libc 的**系统声明本身就带该规格**
（glibc 用 `__THROW` 声明这三个函数，C++ 下即 `noexcept`）时才匹配。OHOS 的 libc 头（musl 系）声明这三个
函数时**不带**该规格 ⇒ 重声明立刻非法。glibc 上之所以一直没问题，正是因为 glibc 带了它。

**修法（`patches/0005-time-mock-noexcept-libc-match.patch`，6 处 guard，语义等价、零测试删减）**：
`#if defined(__linux__)` → `#if defined(__linux__) && defined(__GLIBC__)`（`.hpp` 1 处 + `.cpp` 3 处）。
判据正是「系统声明是否带 `noexcept`」的真实条件：glibc 定义 `__GLIBC__` ⇒ 走 `noexcept` 分支（与改动前**完全一致**）；
musl/OHOS 不定义 ⇒ 走既有的 `#else`（无 `noexcept`）分支。**不硬编码任何平台名**（不用 `__OHOS__`，PF5/R8 会拦），
且在 glibc 上是逐字节 no-op。上游测试未被删除或改写，只修这一处类型规格。

**本地校验**：对上游 tag `v2.0.8` 的原始两个文件 `patch -p1 --dry-run` **clean**（输出两行 `checking file …` 无报错）；
改动仅 4 行 guard，`clock_*` 的 mock 行为与断言数不变。

---

## 7. 修 OHOS CI #91284 失败：SoFi 压力测试的 `pthread_setaffinity_np`

**CI 实证（buildid 104864 / 构建 #91284 / PR #15129，2026-10-14 15:06）**：

```
iceoryx_hoofs/test/stresstests/test_stress_sofi.cpp:64:23:
  error: use of undeclared identifier 'pthread_setaffinity_np'; did you mean 'sched_setaffinity'?
          auto retVal = pthread_setaffinity_np(nativeHandle, sizeof(cpu_set_t), &cpuset);
```

**根因**：`pthread_setaffinity_np()` 是 **glibc 的 GNU 扩展**（OHOS sysroot 的 `sched.h` 只声明
`sched_setaffinity()`）。上游该文件用 `#ifdef __linux__` 保护这个调用，而 musl 系目标（OHOS）**定义
`__linux__` 但没有该函数** ⇒ 声明缺失、编译中断。与 0005（time_mock 的 `noexcept` 规格）是**同一类**错误：
「`__linux__` 被当成 glibc 的同义词」。

**修法（`patches/0006-stress-test-affinity-glibc-guard.patch`，1 处 guard，语义等价、零测试删减）**：
第 59 行 `#ifdef __linux__` → `#if defined(__linux__) && defined(__GLIBC__)`。musl/OHOS 上走该文件**自带**的
`#else` 分支（`static_cast<void>(cpu); static_cast<void>(nativeHandle); … return true;`），即上游对非 Linux
平台本来就采用的「不设亲和性」路径；glibc 上逐字节 no-op。**不硬编码平台名**（不用 `__OHOS__`，PF5/R8 会拦）。
**测试用例、断言、fixture、期望值一行未改**，压力测试仍然构建、仍然执行。

**上游全量核实**：`grep -rn pthread_setaffinity_np` 在整个 v2.0.8 源码树中**只有这一处调用**（另一处是同文件
第 67 行的报错字符串），因此该错误一次修净，不存在遗漏调用点。

**本地校验**：对上游 tag `v2.0.8` 的原始 `test_stress_sofi.cpp` `patch -p1` 应用 clean（`checking file` 无报错），
应用后第 59 行确为 `#if defined(__linux__) && defined(__GLIBC__)`；`diff` 仅 1 行。
