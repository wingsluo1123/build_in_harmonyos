# liblscp 1.0.1 适配笔记

- 任务号 15090（活动=开源鸿蒙PC专项积分赛-依赖），主理 QDR-1009-E05，分支 `feat/liblscp-1.0.1`
- worktree `~/qzy/QDR-1009-E05-liblscp-1.0.1`，基线 upstream/main 实读 `2909ad9eadff18a8008d47be0f593b4e61d3aa69`
- 目标平台 OpenHarmony / HarmonyOS PC aarch64，clang 15.0.4（`Target: aarch64-unknown-linux-ohos` 实测）

## 上游

- 官方源码：https://download.linuxsampler.org/packages/liblscp-1.0.1.tar.gz
- SHA256 `db54a33c0e5e98c44a11022e92183baf7b977e70721293641a109ea4dbb4f6c7`，98261 字节
  （2026-10-12 设备侧与 Windows 侧各一次 HTTP 200 独立取证，逐字相同；1.0.2/1.1.0/1.2.0 同路径 404 ⇒ 1.0.1 是当前最新发行版）
- 许可证 LGPL-2.1-or-later（`LICENSE` = LGPL v2.1 正文，各头文件 "either version 2.1 of the License, or (at your option) any later version"）
- 语言/构建系统：纯 C（`*.c`=10、`*.h`=8、`*.cpp`=0）+ CMake ≥3.13；无 configure/autotools

## 上游构建系统逐行读数（决定配方写法）

| 位置 | 上游事实 | 配方处置 |
|---|---|---|
| `CMakeLists.txt:3-7` | `project(liblscp VERSION 1.0.1 … LANGUAGES C)` | 版本串与归档目录/分支一致，不归一化 |
| `CMakeLists.txt:12-33` | `execute_process(git describe …)` 成功即覆盖 `PROJECT_VERSION` | 真机源码目录非 git 仓 ⇒ 预期 inert；由消费者测试断言 `LSCP_VERSION=="1.0.1"` 实测坐实，不打补丁 |
| `CMakeLists.txt:36-41,75-81` | 两次 `include(GNUInstallDirs)`，`CONFIG_LIBDIR/INCLUDEDIR = "${CMAKE_INSTALL_PREFIX}/<探测值>"` 绝对形态并被当安装目标 | `tc.variables["CMAKE_INSTALL_LIBDIR"]="lib"`、`CMAKE_INSTALL_INCLUDEDIR="include"` 钉死，避免 generator 猜 lib64 |
| `CMakeLists.txt:61-64` | `SHARED_VERSION_INFO 6.0.6` / SOVERSION 6 | **实测优先于推断**：真机产物为 `lib/liblscp.so` 单一文件，`llvm-readelf -d` 只有 `NEEDED libc.so`、**无 SONAME 条目**（该读数属修复前 tip `e13eadc29`，已被 2026-10-15 19:10 那次真机 conan create 推翻，见文末「P1-1 DT_SONAME 真机验证」节） ⇒ 消费者 `DT_NEEDED` 直接是 `liblscp.so`（test_package 与 examples 均按此链接运行成功）。`cpp_info.libs=["lscp"]` 不受影响 |
| `CMakeLists.txt:96-111` | `if (UNIX AND NOT APPLE)` 下 `check_include_files(stdlib.h;…;sys/socket.h;unistd.h)` 与 12 个 `check_function_exists` 任一缺失即 `FATAL_ERROR` | musl/OHOS sysroot 均具备；configure 阶段实测读数记录在本节末 |
| `src/CMakeLists.txt:12-15` | `configure_file(${CMAKE_SOURCE_DIR}/lscp/version.h.cmake ${CMAKE_SOURCE_DIR}/lscp/version.h)` **回写源码目录** | conan `cmake_layout` 的 source 目录可写，无需补丁；不把它当幻影文件提交 |
| `src/CMakeLists.txt:23-30,65-68` | PUBLIC_HEADERS = `lscp/{client,device,event,socket,thread,version}.h`，装入 `${CONFIG_INCLUDEDIR}/lscp` | `includedirs=["include"]`，消费者按 `<lscp/client.h>` 引用 |
| `src/CMakeLists.txt:45-48` | `add_library(${PROJECT_NAME} SHARED …)` **硬编码 SHARED** | `default_options shared=True`；`shared=False` 由 `validate()` 抛 `ConanInvalidConfiguration`（不做假旋钮，不为此打补丁） |
| `src/CMakeLists.txt:50` | `target_link_libraries(liblscp PUBLIC pthread)` | `cpp_info.system_libs=["pthread"]` |
| `src/CMakeLists.txt:58-63` | `PREFIX "lib"` + `OUTPUT_NAME "lscp"` | `cpp_info.libs=["lscp"]`（以产物为准，不猜） |
| `doc/CMakeLists.txt` | `find_package(Doxygen)`，未找到则不建 target、不 FATAL_ERROR | 不装 doxygen 依赖，文档段自然跳过 |
| `examples/CMakeLists.txt:7-20` | 上游自带 `example_server`/`example_client` 两个链接本库的可执行文件，无 install 规则 | 随默认构建编译（额外链接期证据），不进包、不触发 R38 `commands.json` |

## 上游测试分析（五维账本，口径见 AGENTS §10.1）

| 维度 | 读数 | 依据 |
|---|---|---|
| `N_static` 上游静态声明 | **0** | tarball 全树 `add_test\|enable_testing\|ctest\|BUILD_TESTING\|make check` 命中 0（2026-10-12 实读） |
| `N_registered` | 0 | 无任何测试 target |
| `N_executed` | 0 | 无可执行对象 |
| 未执行/跳过分类 | 0 | 不存在条件跳过项 |
| `N_consumer` | **1** 个消费者程序 / **76** 条断言（被审 tip `09a123cac` 真机实测 76 执行 / 76 通过 / 0 失败） | `test_package/test_liblscp.c`，编译+链接 `liblscp.so` 并调用公开 API，退出码由断言决定；读数取自 `reports/conan-create.log` 第 269/270 行 `liblscp consumer test: 76 assertions, 0 failures` + `RESULT: PASS`（2026-10-13 19:27 现场）。修复前 tip `e13eadc29` 的同程序读数为 **65** 断言 / 0 失败（`reports/w3-local-ci.log` 第 339/340 行，2026-10-12 22:28），差值 11 条＝P1-1 新增的第 5 组反悬置断言 |

上游无自动化测试 ⇒ 本包的行为证据完全由 test_package 承担（AGENTS §10「上游无测试时如实写 0，再设计真实 API/行为测试」）。消费者测试五组断言：
1. `configure_file` 生成的 `LSCP_PACKAGE/LSCP_VERSION/LSCP_BUILD` == `liblscp/1.0.1/1.0.1`（顺带坐实 `git describe` 覆盖分支未生效）；
2. `src/event.c` 的 17 项事件枚举 ↔ 文本互转，含 `strcasecmp` 大小写路径、`to_text(NONE)==NULL`、`from_text(NULL/未知)==LSCP_EVENT_NONE`；
3. 客户端 API 的 NULL 句柄契约（`get_errno/get_result/get_timeout/get_events/query/destroy`）；
4. 对本进程内 loopback 假 LSCP 服务端发起**真实事务**：`lscp_client_set_timeout(5000)` → `GET MASTER_VOLUME` 收 `OK[0.85]` 解析为 result="0.85"/errno=0 → 纯 `OK` 累积路径 → `ERR:400:bogus command` 转 `LSCP_ERROR`/errno=500/result="bogus command"（逐条对应 `src/common.c:116-256` 解析器实测语义）。
5. **E513 反悬置断言（P1-1 整改新增，3 条真实可达路径 + 时间上界）**：5a 公开线程 API——`lscp_thread_create(worker_never_returns, detach=0)` 起一个永不返回的 joinable worker，`lscp_thread_cancel()` 必须返回 `LSCP_OK` 且紧随的 `lscp_thread_join()` 必须在 `TEARDOWN_BUDGET_MS=5000` 内返回 `LSCP_OK`；5b 自然退出路径——worker 立即返回后 `lscp_thread_destroy()` 同样在上界内完成（并断言 `g_worker_ran==1` 证明线程体确实跑过）；5c 库自身路径——`lscp_socket_agent_start()` 起活 worker 后 `lscp_socket_agent_free()`（`lscp_client_destroy()` 实际调用的那一条）必须在上界内返回 `LSCP_OK`。撤回的空桩形态下 5a/5c 必然阻塞到超时，故这三组读数即是"不悬置"的行为证明。

## OHOS pthread cancellation 平台缺口与 0001 补丁（改前/改后同口径读数）

**上游用了什么**：`src/thread.c` 的 `lscp_thread_cancel()` 只有两个分支——`#if defined(WIN32)`（不终止线程，注释 "Should we TerminateThread(pThread->hThread, 0) ?"，直接 `ret = LSCP_OK`）与 `#else`（`pthread_cancel(pThread->pthread) == 0` ⇒ 置 `pthread = 0` ⇒ `LSCP_OK`）。全 tarball 的 cancellation 家族调用点实测**仅此 1 处**（`grep -rE "pthread_cancel|pthread_testcancel|pthread_setcancelstate|pthread_setcanceltype"` 于 src/、lscp/、examples/、CMakeLists.txt ⇒ `src/thread.c:150` 一条命中）。`lscp_thread_destroy() = lscp_thread_cancel() + lscp_thread_join()`，二者构成公开 API 契约。

**OHOS 缺什么**（2026-10-12 真机 llvm-nm 实测，SDK 26.0.0.18_3 / clang 15.0.4）：

| 符号 | 静态 `libc.a`（--defined-only） | 共享 `libc.so`（-D --defined-only） |
|---|---|---|
| `pthread_cancel` | 1（有定义） | **0** |
| `pthread_setcanceltype` | 1 | **0** |
| `pthread_testcancel` | 0 | 0 |
| `pthread_setcancelstate` | 0 | 0 |
| `pthread_create` / `pthread_join` | 0 | 1（正常可用） |

sysroot `usr/include/pthread.h` 亦不声明该家族（clang 报 `call to undeclared function 'pthread_cancel'`，create #1 日志 140 行）。关键结论：**取消符号只存在于静态归档、不在可执行文件实际链接的共享 libc 里** ⇒ 库本体 `liblscp.so` 能带着未定义符号完成链接（`[53%] Built target liblscp`），失败推迟到**任何**消费它的可执行文件链接期，由 `ld.lld: error: undefined reference due to --no-allow-shlib-undefined: pthread_cancel / referenced by ../src/liblscp.so` 报出（create #1 日志 152/158 行，`examples/example_client`、`example_server` 两处）。这也是"库绿、消费者全红"这种症状形态的根因。

**处置（两版，如实记录被审结论）**：

- **初版（tip `e13eadc29`，`patches/0001-ohos-thread-cancel-cooperative-join.patch`，872 B）**：在 `#if defined(WIN32)` 与 `#else` 之间插入 `#elif defined(__OHOS__)`，采取与上游 WIN32 分支同一套协作式语义——`if (pThread->pthread) ret = LSCP_OK;`，随后交给 `lscp_thread_join()` 等线程自然返回。**该形态已被独立 W4 判为 P1**：`knowledge/doc/E513.md` 的「根因分析」段原文禁止的正是这种"no-op stub or simply returning an error changes the lifecycle of a joinable worker: callers still wait in pthread_join() and cannot reclaim the thread"——空桩既不请求取消也不清句柄，`lscp_thread_destroy()`（`= cancel() + join()`）会停在 join 上无限等待一个仍在运行的 worker。初版随本轮整改**已删除**，其申报依据（"grep 除 thread.c 自身外无 in-tree 调用方"）经复核为假，见下条更正。
- **现版（tip `09a123cac`，`patches/0001-ohos-thread-cancel-guarded-signal-exit.patch`，4024 B，sha256 `bbcf6b83ff92dc968566595940dcdd4a3a9ac998fc299d8a1c4c99769f5398f8`）**：按 `E513.md`「推荐方案」原文 **方法=guarded-signal-thread-exit** 实现——`lscp_thread_create()` 在 `pthread_create()` **之前**用 `sigaction()` 安装一个窄范围的 async-signal-safe 退出处理器（处理器体只调 `pthread_exit(NULL)`，`sa_flags=0` 不设 `SA_RESTART` 因为处理器永不返回；安装失败则 `free(pThread)` 并返回 NULL，不留下半初始化线程），`lscp_thread_cancel()` 的 `__OHOS__` 分支改为 `pthread_kill(pThread->pthread, SIGUSR1) == 0` ⇒ 定向唤醒后**保留句柄**，由 `lscp_thread_destroy()` 的 `lscp_thread_join()` 正常回收并 `free()`。保留信号取 `SIGUSR1`（与 `E513.md` 验证段 `pthread_kill(thread, SIGUSR1)` 一致）；本补丁不改动任何调用方的信号掩码，故 `E513.md`「确保应用侧信号掩码不阻塞该保留信号」这一条件在本包内成立的前提已如实披露：库自身不存在任何 `pthread_sigmask`/`sigprocmask` 调用（全 tarball grep 命中 0），若下游应用在创建 client 之前屏蔽 `SIGUSR1`，取消会退化为不生效而由 join 继续等待——这是该替代机制的应用侧使用边界，写在此处而非藏进代码。Linux/其它平台分支逐字未变。clang 对 OHOS 目标预定义 `__OHOS__ 1`（`clang -dM -E` 实测），无需额外宏注入。

**明确不采用的三条路（附理由，避免审计误判为规避）**：
- 不采用"OHOS 分支诚实失败（返回 `LSCP_ERROR`）并让 `lscp_thread_destroy()` 不进 join"这条替代方案（独立 W4 给出的选项 b）——`E513.md` 根因分析把"simply returning an error"与 no-op stub 并列禁止：它同样丢弃了 targeted exit，调用方（`lscp_socket_agent_free()` → `lscp_client_destroy()`）只能得到一个泄漏的活线程；且 join 分支若按平台跳过，就与公开 API 契约分叉。故选 rec=guarded-signal-thread-exit（CIB 选项 a）。
- 不自定义 `pthread_cancel/pthread_testcancel` 等符号做 shim —— 那是往库里塞假实现掩盖缺口，且本仓库既有草稿（`knowledge/drafts/DRAFT-E680-ohos-no-pthread-cancellation.kv`）的 shim 方案返回 ESRCH 会让 `lscp_thread_destroy()` 停在 `LSCP_FAILED`、既不 join 也不 free；
- 不删除/关闭 `examples` 子目录 —— 上游 `CMakeLists.txt:118-120` 无条件 `add_subdirectory`，保留它们等于保留第二个独立链接期验证面（消费者可执行文件），删掉只会隐藏症状、不改分母也不增证据。

**改前/改后对照（同一 llvm-nm 口径，同一 sysroot）**：

| 读数 | 改前（create #1，12:53） | 改后（create #2，13:32） |
|---|---|---|
| `liblscp.so` 未定义 `pthread_cancel` 计数 | **1** | **0** |
| 链接 liblscp.so 的可执行文件 | `ld.lld` 报 undefined reference ×2，`CREATE_RC=2` | `examples/example_client`、`example_server`、`test_liblscp` 全部链接成功，`CREATE_RC=0` |
| 消费者测试执行 | 未生成（`TEST_EXE_NOT_FOUND`） | 65 断言 / 0 失败，`RESULT: PASS`（13:32，初版补丁）；现版补丁下同程序 **76 断言 / 0 失败 / `RESULT: PASS`**（2026-10-13 19:27，`reports/conan-create.log:269`） |
| 包内容 | 不可用 | `include/lscp/{client,device,event,socket,thread,version}.h`、`lib/liblscp.so`、`lib/pkgconfig/lscp.pc`、`licenses/` |

## 真机 create 读数（两次绿跑分别绑定各自载体）

### 初版（tip `e13eadc29`，2026-10-12 13:32，`CREATE_RC=0`）

- 命令：`conan create archives/l/liblscp/1.0.1 -pr:h=<任务私有 shadow profile> -pr:b=<同>`（**未加 `--build=missing`**；本包 conanfile 无任何 `requires`，依赖面为空）
- `gate.sh 8000` → `GATE_OK`；本窗 build-slot 快照 → `SLOT_DONE:ok MemAvailable=10576MB`；`tools.build:jobs=2`（`-j2` 实测于日志）
- recipe revision `80368bea615ed043d863c1f1560f3827`（初版 conandata/补丁下的读数，随 P1-1 整改已作废，见下）
- 日志：设备 `~/tmp/uc2/QDR-1009-E05/liblscp-create2-20261012-133207.log`；Windows 侧回读 `.temp/QDR-1009-E05/logs/liblscp-create2-run-1352.log`（非空，2588 B）

### 现版（被审 tip `09a123cac`，2026-10-13 19:27 官方 conan-verify 内 G2 的 create）

- 发起命令：`python3 scripts/ohc-run.py conan-verify liblscp 1.0.1 --profile ohos-aarch64-15461B`（脚本载体 `.temp/QDR-1009-E05/probe/liblscp_step20_rerun.sh`；create 日志本身不回显外层命令行，只回显 profiles 段）
- 前置门槛实测：`sh ~/tmp/uc2/gate.sh 8000` → `GATE_RC=0`（`GATE_PASS:probe=clang MemAvailable=12015MB MemFree=747MB Cached=15268MB swap余=49031MB load=20.000 20.060 20.091 PSI_full=avg10=52.89 编译器进程=0`）；共享槽位锁 `build-slot.QDR-1009-E05.sh --wait 3600 --mem 8000`，`tools.build:jobs=2`，独立 `CONAN_HOME=~/tmp/ch/home-QDR-1009-E05-liblscp`
- **同一条门禁本轮跑过两次，第一次是红的且红因是本窗自己的声明错位**：19:2x 首跑 `VERIFY_RC=2`、G0/G1 PASS、**G2 FAIL**，原因是补丁改名后 `conandata.yml:19` 仍声明旧文件名 `patches/0001-ohos-thread-cancel-cooperative-join.patch` ⇒ 构建死在补丁应用步、**根本没编译到新代码**；`sed` 校正声明路径为 `0001-ohos-thread-cancel-guarded-signal-exit.patch` 后重跑 1 次 ⇒ `VERIFY_RC=0`。该失败不得隐去，也不构成"仅启动一次"的表述
- 读数：`liblscp/1.0.1@ohpcd/stable#54de32d79014a9df05bbcf1b00910746`（2026-10-13 11:26:47 UTC 导出）【**本节 revision/package-revision 已被文末 22:45–22:46 绑定构建节现值取代：recipe revision `073c332775dc48c720da23061c76705b`、package revision `dda9f48fcded6d023abe8a4fa79c3f94`**】、package id `01d92cf349a0dd98ff915f4bd99a04430171517f`（**与初版逐字相同 ⇒ 本次整改未动 settings/options，故 package_id 不变**）、created package revision `679e7da89941b2d2cf7007416d951687`；settings 实测 `os=OHOS / os.version=6.0 / arch=armv8 / compiler=clang / compiler.version=15 / compiler.libcxx=libc++ / compiler.cppstd=17 / build_type=Release`（`libcxx=c++17` 是此前的误写，conan 无该取值），options `shared=True`
- 关键输出：`liblscp consumer test: 76 assertions, 0 failures`（第 269 行）、`RESULT: PASS`（第 270 行），三条反悬置读数 `thread cancel+join (live worker): ret=0/0 elapsed_ms=0`／`thread destroy (natural exit): ret=0 elapsed_ms=0`／`socket agent free (live worker): ret=0 elapsed_ms=0`（第 266/267/268 行，预算 5000ms ⇒ 实际 0ms 返回）
- 该绿跑 create 日志现场**无真实错误行**（`grep -nE "Error|error:|Not found|FAIL"` 命中 0）；`version: package=liblscp version=1.0.1 build=1.0.1` 坐实 `git describe` 覆盖分支未生效；`lscp_client_create: cmd: connect: Connection refused` 是断言组 4a 的**预期**负向路径（对已关闭 loopback 端口建链应返回 NULL），非错误
- CMake 对 OHOS 的提示 `System is unknown to cmake, create: Platform/HarmonyOS …` 为 CMake 4.4.3 未知平台名的常规告警，不影响 configure 完成（`Configuring done (3.8s)`）

## 内存与资源评估

- `memcap-run.py --probe` 对消费者程序真机实测 **peak=4MB rc=0**（`PROBE_RC=0`）；`test_package/MANIFEST.yml` 的 `max_rss_mb` 据此记预算 **8**（实测 2 倍余量），不再用起草时的 64 估值。
- 消费者测试仅用 loopback socket 与小缓冲，无 GB 级输入；构建走全队的 `gate.sh 8000` + 本窗 build-slot 快照 + 独立 `CONAN_HOME=~/tmp/ch/home-QDR-1009-E05-liblscp`。

## 构建 profile 输入身份（本任务私有，不改框架只读件）

框架只读件 `ci/conan/profiles/ohos-aarch64`（被审 tip 上 2101 B，sha256 `7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793`，mtime 2026-10-12 12:33）把 `tools.build:compiler_executables` 写死 `/data/service/hnp/bin/clang(++)`、`[buildenv] CONFIG_SHELL/SHELL` 写死 `/data/service/hnp/bin/bash`、`PATH`/`LD_LIBRARY_PATH` 也含 hnp 路径；本设备实测这三条二进制**不存在**（同队 adns 1.7.0 因此连吃 exit 127 / exit 77，见 `.temp/QDR-1009-E05/STATE.md` R43 链）。**本窗未改任何框架文件**（AGENTS §9），差异属框架侧可移植性，另由 PR #15461 承载。

本任务名下实际存在**两份**私有 profile，必须分开指认（此前把二者混为一谈＝独立 W4 判定的 P1 项，现更正）：

| 载体 | 绝对路径 | 字节 | sha256 | 与绿读数的关系 |
|---|---|---|---|---|
| **通过输入（唯一）** `ohos-aarch64-15461B` | `~/tmp/ch/home-QDR-1009-E05-liblscp/profiles/ohos-aarch64-15461B` | **2757** | `67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e` | `reports/w3-local-ci.log:7/10/17` 记录 `Profile ohos-aarch64-15461B` / `profile: ohos-aarch64-15461B`；`reports/conan-verify-report.md:34` 记录 `**Profile**: ohos-aarch64-15461B`。**两份绿载体用的是同一输入** |
| 早期尝试件 `ohos-aarch64-e05` | `~/tmp/ch/home-QDR-1009-E05-liblscp/profiles/ohos-aarch64-e05`（同内容另存 `~/tmp/QDR-1009-E05-liblscp-shadow/ci/conan/profiles/ohos-aarch64`） | 630 | `70ccfc78b783094d1f243c7c47b8615297611445e2a3d93c2635f33752bdf372` | **不是**任何绿读数的输入。此前 `manifest.yaml:67` 与 notes 的 `CONAN_PROFILE` 段把它申报成 W3 通过输入，属身份误绑，本轮已改 |

`15461B` 件的内容即框架修复 **PR #15461 的候选 profile**：文件头 8 行 Jinja（`{% set use_hnp = os.path.isfile("/data/service/hnp/bin/clang") ... %}` 探测后回落 `~/.harmonybrew/bin` 与 `~/usr/local/bin`），其余为 `#` 注释与 `os=OHOS / os.version=6.0 / arch=armv8 / compiler=clang / compiler.version=15 / compiler.libcxx=libc++ / compiler.cppstd=17 / build_type=Release`。同源关系本窗实测：与本窗被审 tip 上的仓库只读件逐字节 `diff` 只差 Jinja 头与 `[conf]/[buildenv]` 的工具路径行，而 **`[settings]` 段 `diff` rc=0（`SETTINGS_DIFF_RC=0`，脚本 `.temp/QDR-1009-E05/probe/liblscp_step22_facts.sh` G 段）** ⇒ settings 未变，故 `package_id 01d92cf349a0dd98ff915f4bd99a04430171517f` 不受该输入差异影响（且初版与现版两次 create 的 package id 实测逐字相同，独立坐实同一结论）。同一 sha256 `67404bc1…` 在本机另分布于 `~/tmp/uc2/QDR-1009-E03/fw-15461-verify/profiles/ohos-aarch64.B`、`~/tmp/uc2/QDR-1009-E07/profiles/ohos-aarch64.B`、`~/tmp/uc2/QDR-1009-E01/profiles/ohos-aarch64-15461B`、`~/tmp/uc2/QDR-1010-PR01/f15461/ohos-aarch64`、`~/tmp/root-audit-framework-20261012/ohos-aarch64.candidate`（本窗 `sha256sum` 逐个实测一致），与 `ohos-aarch64.A`/`f15461/ohos-aarch64.base`（2101 B / `7ebd43d2…`＝仓库件）构成 #15461 的 base/candidate 对。**#15461 的线上 head SHA 本窗未独立核验**（仅有统筹巡检记录 `15461@1f9ac702` 与 CIB 审计的 g2_attribution 段），故此处只以内容 sha256 与逐字 diff 为据，不据此声称框架修复已合入。

**措辞硬约束（照 CIB 审计 `wording_constraint`）**：本包全部"绿"只能表述为「**私有影子 profile `ohos-aarch64-15461B`（2757 B / `67404bc1…`）输入下官方工具绿**」，**禁止表述为官方默认管线绿**。默认仓库 profile 输入在本包上的现存终态仍是红：历史载体 `reports/conan-verify-report.md`（tip `e13eadc29` 上 1425 B）记 `Verdict FAIL / Profile ohos-aarch64 / G0/G1 PASS / G2 FAIL`，官方 `finish` 自报 `RC=1` 且失败步骤 `step3, step5b, step8`；该差项归因于框架只读 profile 的 hnp 硬编码与未合入的 #15461（外部基建依赖），不判本配方缺陷，也不为此重复构建。**注意**：被审 tip `09a123cac` 上 `reports/conan-verify-report.md` 已被 2026-10-13 19:27 的影子 profile 绿跑覆盖为 1237 B / `7da24d35…`（`Verdict: PASS`），因此"默认输入仍红"在这一格**没有本 tip 上的现场载体**，只有上面标注的历史读数与 `.temp/QDR-1009-E05/logs/liblscp-step17-p1facts-1910.log` 的现场快照——不得把二者混写成"当前默认管线绿"。

## 状态声明（不得越界引用）

本笔记写于配方起草落盘时点；真机 `conan create` 的退出码、第一条真实错误、test_package 实际断言执行数与通过率，一律以本目录 `manifest.yaml` 与 `.temp/QDR-1009-E05/logs/` 内日志回读为准。未完成 create 前不得称"已构建通过"，未过 W4 独立审计前不得提审。
## 2026-10-12 14:4x 官方门禁读数与披露（QDR-1009-E05 / 任务 15090）

- Step5 W3 本地 CI（官方 `ohc-run.py finish liblscp 1.0.1 built`，私有 build-slot 快照 + `gate.sh 8000` GATE_PASS/MemAvailable 11431MB）：
  `conan create passed`；`L0=pass`、`L1=pass`（test_package 真实执行）、`L2=skip`（无 bin/，库包）、`L4=pass`（补丁无危险函数）、
  `L1e=pass`（破坏性负测：lib/ 与 include/ 移走后测试即失败 ⇒ 测试真实依赖本库）；Build Summary `Success 1/1 / Pass rate 100.0%`。
  官方产物（按 tip `09a123cac` 现场重绑，2026-10-13 20:2x `sha256sum` 实测）：`reports/w3-local-ci.log` **21141 B**，sha256 `267f5ec6a6ddd7e55bf12a9a371d6818a9d8b8117a7da4a2e37851e0e3e30ede`，mtime 2026-10-12 22:28 ⇒ **该载体属修复前 tip `e13eadc29`，不覆盖 P1-1 的代码改动**（其内 65 断言读数即修复前证据）。此前申报的 21602 B / `ed5a9d61…` 与现场不符，作废。
  `.ci-result.json`：**2026-10-13 22:41 设备现场回读 = 存在**，路径在**版本目录根** `archives/l/liblscp/1.0.1/.ci-result.json`（**不在 `reports/` 下**）：364 B，sha256 `5e032b0954618f6ac149e1bf4c2ff3fcfaa99f2a13abe0f8c3b9d8558fc5a886`，其 `log_sha256` 指回 `reports/w3-local-ci.log` 的 `267f5ec6…` ⇒ Step5 的官方两件载体**互绑成立**。但该次 W3 运行发生在 2026-10-12 22:26（当时检出 tip `60d373ba8`），**对当前文本 tip 仍是滞后载体**。
  上一轮申报的"被审 tip 现场不存在（`ls` → No such file）⇒ 撤回绑定"是**本窗路径核查错误**（只在 `reports/` 目录里找），该作废声明于此更正；更早申报的 364 B / `94f5724f…`（14:43 那次）维持作废。
- 首错定位（14:30 那次 finish Step5 的真实首错，非本配方缺陷）：`junk_check.sh` 在 full 模式（整仓扫描）下 JC5 报 8 个**他人归档**的
  未登记工作流标记（cloog/.build-closed、kics、libbfio、libdazzle、oscpack、reflex、thc 的 .staging-verified）⇒ `JC_RESULT=fail`
  ⇒ L0 fail、L1/L2/L4/L5 skip。处置按 AGENTS §9 既定本地规避：在 worktree 根写**仅本地不入库**的 `pr.diff`（`+++ b/` 清单取自
  `git show --name-only HEAD`），使 junk_check 进入 `prdiff` 模式——与真实 buildbot 的 checkout-pr + git apply 行为同源。
- 编译器路径（**本段 14:4x 原申报已作废，按现场载体更正**）：仓库只读框架 profile `ci/conan/profiles/ohos-aarch64` 把 CC/CXX 与 SHELL 写死为
  `/data/service/hnp/bin/clang`、`/data/service/hnp/bin/bash`；本设备实测该路径不存在（`/data/service/hnp/bin/clang: No such file or directory`）。
  本窗**未改任何框架文件**（§9），该 sha 现场仍为 `7ebd43d2…`（2101 B，见上节 profile 身份表）。
  14:4x 曾把 W3 通过归因于 `CONAN_PROFILE` 按名称回退到私有 `profiles/ohos-aarch64-e05`（630 B / `70ccfc78…`）。
  **该归因在被审 tip 上没有任何在-site 载体**：`reports/` 现场唯一的 W3 绿跑日志是 `w3-local-ci.log`（21141 B / `267f5ec6…`，mtime 2026-10-12 22:28），
  其第 **7/10/17** 行记录的 profile 名是 **`ohos-aarch64-15461B`**（2757 B / `67404bc1…`），不是 `ohos-aarch64-e05`。
  ⇒ 现行口径：**通过输入只有 `ohos-aarch64-15461B`**；630 B 的 `ohos-aarch64-e05` 是更早期的尝试件，不得再申报为 W3/绿跑输入（详见上节）。
- 仍存红的官方门禁（基建类，需统筹定夺）：`ohc-run.py conan-verify liblscp 1.0.1` **不带** `--profile` 时 G2 仍 FAIL（VERIFY_RC=1/2，两次同签名）。
  该红的**首错原文**属修复前 tip `e13eadc29`：当时 `reports/conan-create.log` 为 7389 B / `076fa622…`，末行
  `liblscp/1.0.1@ohpcd/stable: ERROR: Error in build() method, line 69`。**被审 tip `09a123cac` 上该文件已被 19:27 的绿跑覆盖**
  （现场 18520 B / `e5d91396…`，`grep` 真实错误行命中 0，末行 `RESULT: PASS`）⇒ 默认输入的终态红在本 tip **无在-site 载体**，只能引用上述历史签名，
  不得把二者混写。`conan-verify` 把 `-pr:h/-pr:b` **显式指向仓库框架 profile 路径**、不受 `CONAN_PROFILE` 影响，故命中与 14:30 相同的
  `/data/service/hnp/bin/clang` 缺失。知识图谱在此误命中 E540（该条目面向 ohos-test-runner 的 PATH 注入场景）；**本轮未重读 E540 原文，
  故不再引用其字段名**，只保留既有定性：这不是 liblscp 兼容性失败，而是框架 profile 的工具路径可移植性问题。
  可选出路（不在本窗权限内）：框架侧 profile 可移植性单独 PR（即 #15461 的方向），或整仓影子工程覆盖 `ci/conan/profiles`。
- 已知限制（W4 需知）·L5 双载体冲突，**不得概称 L5 PASS**：`w3-local-ci.log` 第 **350** 行 `[fail] L5a: liblscp.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址`、
  第 **365** 行 `L5_RESULT=fail: soname_gate_failed`；而 `reports/conan-verify-report.md`（1237 B / `7da24d35…`，19:27）把 **L2/L4/L5 三节都渲染成 `✅ PASS`**，
  但其节内正文逐字是 `⏭️ 跳过（无 cache 路径）`。⇒ 两份官方载体对 L5 的判决相反，本窗只并列呈现、不替独立审计裁定。
  事实面（不受判决影响）：上游 CMakeLists 未设 `SOVERSION/VERSION`，打包实测产物为单个 `lib/liblscp.so`、`readelf -d` 仅 NEEDED libc.so。
  本窗不改上游命名契约（改名/加 SOVERSION 属上游行为变更），如实记录。
- 补丁形态披露（对照 E513·本轮已按 E513.md 原文整改，**以下三段替换 14:4x 的旧披露**）：
  - **旧披露的两处不实，逐条更正**：①"沿用上游 WIN32 语义——`lscp_thread_cancel()` 直接 `ret = LSCP_OK`" 描述的是**已删除的初版 872 B 空桩**，
    现版 `patches/0001-ohos-thread-cancel-guarded-signal-exit.patch`（4024 B / `bbcf6b83…`）已改为 create 期 `sigaction()` 安装 SIGUSR1 退出处理器 +
    `pthread_kill()` 定向退出（见「OHOS pthread cancellation 平台缺口」节的处置段）；②"实测缓解依据：`grep -rn "lscp_thread_" src/ include/` 除
    `src/thread.c` 内自身定义/声明外**无 in-tree 调用方**"**经复核为假**——真实调用面：`src/socket.c:216`、`:248`（`lscp_socket_agent_free`）、
    `src/client.c:602`、`:603`（`lscp_client_destroy` 内）、`src/client.c:921`、`src/common.c:100`、`:101`，且 `src/client.c:231` →
    `src/socket.c:219 lscp_thread_create()` 构成公开 API 可达链（`lscp/socket.h:72` 持 `pThread`，socket.h/thread.h 均在 PUBLIC_HEADERS 内）
    ⇒ 取消-再-join 路径是**公开且活跃的**，这正是初版必须重做的理由。Linux 分支逐字节未变（现版 diff 只在 `__OHOS__` 分支与 create 路径新增）。
  - **E513 引用改为原文可核部分**：`knowledge/doc/E513.md`「根因分析」禁止 "a no-op stub or simply returning an error changes the lifecycle of a
    joinable worker: callers still wait in `pthread_join()` and cannot reclaim the thread"；「推荐方案」的**方法=guarded-signal-thread-exit**，
    「验证」段以 `pthread_kill(thread, SIGUSR1)` 后 `pthread_join` 收束。**该文档内没有 `forbid_1`/`fallback` 字段，14:4x 与本轮此前的字段名引用系误引，一并作废。**
  - **反悬置的真实读数（替代"缓解依据"式推断）**：被审 tip 绿跑 `reports/conan-create.log` 第 **266–268** 行
    `thread cancel+join (live worker): ret=0/0 elapsed_ms=0` / `thread destroy (natural exit): ret=0 elapsed_ms=0` /
    `socket agent free (live worker): ret=0 elapsed_ms=0`，第 **269** 行 `76 assertions, 0 failures`、第 **270** 行 `RESULT: PASS`
    ⇒ 三条可达路径（含 `lscp_socket_agent_free()` 这条 `lscp_client_destroy()` 实际走的路径）在 `TEARDOWN_BUDGET_MS=5000` 预算内即时返回；
    撤回的初版空桩形态下 5a/5c 会阻塞到超时。此点仍交独立 W4 判定，本窗不自审。
- 五维账本（同源，MANIFEST.yml/notes.md/正文候选/create 日志一致）：`N_static=0`（上游 1.0.1 tarball 无自动化测试注册入口：
  CMake 无 `add_test`/`enable_testing`，无 `make check` 目标）、`N_registered=0`、`N_executed=0`、未执行/跳过 0、
  `N_consumer=1` 程序（`test_package/test_liblscp.c`）——被审 tip `09a123cac` 实测 **76** 断言 0 失败（`reports/conan-create.log:269/270`，19:27）；
  修复前 tip `e13eadc29` 为 65 断言（`reports/w3-local-ci.log:339/340`，22:28 载体）。上游静态全量为 0 ⇒ 配方 `build()` 不调用 `cmake.test()`
  （§10 "无自动化测试时如实写 0"），消费者测试真实编译+链接+运行并由退出码判定。
## 2026-10-13 20:3x P1-2/P1-3 文本与证据重绑（零构建、零 push）

独立 W4 终局件 `.temp/QDR-1009-CIB/w4-lscp/audit-result-liblscp-e13eadc29.json`（verdict=fail，P0=0/P1=3/P2=4/P3=4）中 P1-1 已在 19:3x 完成代码整改
（tip `09a123cac`），本节只做 P1-2/P1-3 的**申报↔现场绑定更正**，不新增任何构建读数。被审 tip 取本轮实时 `git rev-parse HEAD`
= `09a123cace3ee01bd6cdf339624ce64295915612`（分支 `feat/liblscp-1.0.1`，worktree 干净）。

绑定台账（左=本 notes 旧申报，右=被审 tip 上 `sha256sum`/`wc -c`/`sed -n` 实测；探测脚本 `.temp/QDR-1009-E05/probe/liblscp_step22_facts.sh`
→ 日志 `.temp/QDR-1009-E05/logs/liblscp-step22-facts-2020.log`，追加探测 `liblscp_step24_pkgid.sh`）：

| 载体 | 旧申报（作废） | 被审 tip 现场实测 | 处置 |
|---|---|---|---|
| `reports/w3-local-ci.log` | 21602 B / `ed5a9d61…` | **21141 B / `267f5ec6a6ddd7e55bf12a9a371d6818a9d8b8117a7da4a2e37851e0e3e30ede`**，mtime 2026-10-12 22:28 | 改绑现场值，并标注**属修复前 tip `e13eadc29`**，不覆盖 P1-1 |
| `.ci-result.json`（**版本目录根，不在 `reports/` 下**） | `reports/.ci-result.json` 364 B / `94f5724f…`；随后又申报"现场不存在、撤回绑定" | **存在**：364 B / `5e032b0954618f6ac149e1bf4c2ff3fcfaa99f2a13abe0f8c3b9d8558fc5a886`（2026-10-13 22:41 现场 `sha256sum`），`log_sha256` ↔ `w3-local-ci.log` `267f5ec6…` | 恢复绑定，但绑定对象 = 2026-10-12 22:26 那次 W3 运行（检出 tip `60d373ba8`）⇒ **对当前文本 tip 滞后**；"不存在/撤回"系本窗路径核查错误，于此更正；`94f5724f…`（14:43）维持作废 |
| `reports/conan-create.log` | 7389 B / `076fa622…`，末行 `Error in build() method, line 69` | **18520 B / `e5d91396819cab22500fe664d908f1fe04ee283b8a4beed4b6b8be57ea3ce79b`**，mtime 2026-10-13 19:27，`:269` = `76 assertions, 0 failures`、`:270` = `RESULT: PASS`，真实错误行 grep 命中 0 | 绿跑改绑现场值；旧的 7389 B/`line 69` 首错降级为**修复前 tip 的历史签名**，本 tip 无在-site 载体 |
| `reports/conan-verify-report.md` | 未单独申报 | **1237 B / `7da24d35b39582030460ebbcd6b7227b5cedd343fb5f5c552ba8f7e770f1ac2b`**，19:27，`:3` `**Verdict**: PASS`、`:5` `**Profile**: ohos-aarch64-15461B` | 新增绑定；其 L2/L4/L5 渲染 `✅ PASS` 而正文 `⏭️ 跳过（无 cache 路径）` 的矛盾与 `L5_RESULT=fail` 并列上报，不自裁 |
| 通过输入 profile | 630 B / `70ccfc78…`（`ohos-aarch64-e05`） | **2757 B / `67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e`（`ohos-aarch64-15461B`）**，被两份绿载体共同引用 | P1-3 主更正：`manifest.yaml` 与 notes 的输入身份统一到该副本 |
| 仓库只读框架 profile | 2101 B / `7ebd43d2…` | 现场逐字相同（本窗未改，合规 §9） | 保持不变，作为默认输入红的根因 |
| recipe revision / package_id | `80368bea…` / `01d92cf3…` | 绿跑 `:导出行` `#54de32d79014a9df05bbcf1b00910746`（2026-10-13 11:26:47 UTC）、package id **仍** `01d92cf349a0dd98ff915f4bd99a04430171517f`、package revision `679e7da89941b2d2cf7007416d951687` | revision 改绑现版；package_id 未变这一点单独说明 `[settings]` 等价性（`diff` rc=0，仅工具路径/buildenv 差异） |
| 消费者断言数 | 65 | 被审 tip **76**（`conan-create.log:269`）；65 保留为修复前 `w3-local-ci.log:339` 读数 | notes/manifest/MANIFEST.yml 三处同源统一到 76（并各自标注载体） |

未闭环项（如实申报，不冒称完成）：①`result.json` 未在现 tip 重生成【已闭合：10-13 22:4x 首次重导 `9e98e320…`，2026-10-15 13:2x 按本轮实测读数再次官方重导 → `5693abbf…`，见文末；均官方生成器，无手改】——与本轮 `conandata.yml` 的措辞更正（见下段）**同批**按新 tip 用官方生成器重生成，不做手改、不造 SHA；
②本窗 build-slot 快照与仓库版脚本存在差异未同步（`SLOT_SNAPSHOT_IN_SYNC=no`）【已闭合：2026-10-15 13:1x 现场实测两侧剥离 CR 后**逐字相同** 8894 B / `9771c729…`、`diff` rc=0 / 0 行 ⇒ 现值 `SLOT_SNAPSHOT_IN_SYNC=yes`，见文末 10-15 节；此前"417 行差异"系 CRLF 假象】；③#15461 的线上 head SHA 本窗未独立核验（仅有统筹记录 `15461@1f9ac702`）；
④P2/P3 其余项（result.json 的 autotools 签名误引改为本轮实测、`conanfile.py:28` 空 url、PR 正文载体）不在本派单范围内。

## 2026-10-13 21:2x conandata 措辞更正与 recipe revision 滞后声明（零构建）

本轮把 `conandata.yml` 中与补丁正文不一致的两处旧措辞（`:15-17` 注释"按上游已有的 WIN32 分支语义给 `__OHOS__` 增加协作式路径（不硬取消，由
`lscp_thread_join` 等待线程自然退出）"、`:20` `patch_description` "改走上游 WIN32 的协作式语义（不硬取消，交给 `lscp_thread_join`）"）改为与现版补丁正文
一致的实测语义：create 期 `sigaction()` 安装只调 `pthread_exit(NULL)` 的 SIGUSR1 处理器、`lscp_thread_cancel()` 改 `pthread_kill()` 定向退出、由
`lscp_thread_destroy()` 的 `lscp_thread_join()` 正常回收。**该文件的 `sources.url` / `sources.sha256` / `patch_file` / `patch_type` / `strip` 逐字未动**
（官方 URL 仍为标量形态 `https://download.linuxsampler.org/packages/liblscp-1.0.1.tar.gz`，sha256 仍 `db54a33c…`；无 `file://`、无镜像、无 `.ghfast-bak`）。

**必须随本提交生效的滞后声明（不得隐去）**【本段已于 2026-10-13 22:45–22:46 的恰 1 次绑定构建**部分闭合**，见文末同名节；保留原文以便复核，不再作为现值引用】：`conandata.yml` 属 conan 导出面 ⇒ 本提交后 **recipe revision 不再是 `54de32d79014a9df05bbcf1b00910746`**。
本 notes 与 `manifest.yaml` 里申报的 `54de32d7…`（连同 `package_id 01d92cf3…`、package revision `679e7da8…`、76 断言读数）**一律只绑定 tip `09a123cac` 的那次绿跑**，
不得当作新 tip 的证据。新 tip 的 recipe revision 与 W3/G2 绿读数**尚不存在**，须由下一轮**恰 1 次**绑定构建（`gate.sh 8000` + 本窗 build-slot 快照 + `jobs=2`，
`--profile ohos-aarch64-15461B`）重导后再绑定；`[settings]` 段与仓库 profile 等价（`SETTINGS_DIFF_RC=0`）⇒ `package_id` 预期不变，但这是**预期、不是读数**。
同理 `reports/w3-local-ci.log`（21141 B / `267f5ec6…`）与 `reports/conan-create.log`（18520 B / `e5d91396…`）在新 tip 上均属**滞后载体**，
`.ci-result.json`（版本目录根，364 B / `5e032b09…`，`log_sha256`↔`267f5ec6…`）同样滞后于新 tip——上一轮把它写成"现场不存在、撤回绑定"是本窗**路径核查错误**（只在 `reports/` 找），此处更正。L5 双载体冲突（`w3-local-ci.log:350/365` fail vs `conan-verify-report.md` 渲染 `✅ PASS` 而正文 `⏭️ 跳过（无 cache 路径）`）
按上一条目所述**并列保留、不删不改判**，交独立 W4 裁定。

---

## 2026-10-13 22:4x 载体存在性更正（22:00 派单构建之前，纯文本）

22:41 设备侧只读回读（载体 `.temp/QDR-1009-E05/logs/liblscp-step38-precheck-2245.log`）推翻了上一节里本窗自己写下的"`.ci-result.json` 现场不存在"：

- **实际路径是版本目录根** `archives/l/liblscp/1.0.1/.ci-result.json`（364 B / `5e032b0954618f6ac149e1bf4c2ff3fcfaa99f2a13abe0f8c3b9d8558fc5a886`）。上一轮只在 `reports/` 目录内 `ls`，因此误报"不存在"。
  ⇒ **本窗"撤回该绑定"的结论作废并更正**：`5e032b09…` 与 `reports/w3-local-ci.log`（`267f5ec6…`）的 `log_sha256` 互绑**成立**；
  更早申报的 14:43 那次 `94f5724f…` 维持作废。该 W3 运行发生于 2026-10-12 22:26（当时检出 tip `60d373ba8`），
  对本次文本 tip 仍是**滞后载体**——更正的是"存在性与互绑"，不是把它升格成本 tip 的证据。
- 同轮回读的其余现场基线：`reports/conan-create.log` 18520 B / `e5d91396…`、`reports/conan-verify-report.md` 1237 B / `7da24d35…`、
  `reports/w3-local-ci.log` 21141 B / `267f5ec6…`；`conandata.yml` 1870 B / `c809b959…`；
  仓库只读 profile 2101 B / `7ebd43d2…`（**未改**）、影子 profile `ohos-aarch64-15461B` 2757 B / `67404bc1…`；
  `CONAN_HOME/global.conf` 第 6 行 `tools.build:jobs=2`；worktree HEAD `82f125d8c…`（父 `09a123cac…`）、脏项 5 件均为大小写幻影或本地不入库件。
- **为什么把这条更正放在构建之前提交**：22:00 派单要把一次真实端到端读数绑到文本 tip 上；若带着一条已被本窗现场证伪的陈述去绑，
  绑定本身就不可信。因此本 notes 的唯一改动就是上面的存在性更正，随构建前的**一笔纯文本提交**落盘；
  **构建与该笔提交（而非 `82f125d8c`）绑定**，两 tip 之间只有本 notes 的文本差异（该差异是否计入 conan 导出面，以本次构建实测出的 recipe revision 为准，不预先断言）。
- 措辞闸门不变：绿只能写"私有影子 profile `ohos-aarch64-15461B`（2757 B / `67404bc1…`）输入下官方工具绿"，**不得**写"官方默认管线绿"；
  L5 双载体冲突（`w3-local-ci.log:350/365` fail vs `conan-verify-report.md` 渲染 `✅ PASS` 而正文 `⏭️ 跳过（无 cache 路径）`）并列保留、不删不改判，交独立 W4。

---

## 2026-10-13 22:45–22:46 恰 1 次绑定构建（tip `4327f6e14`，端到端绿）

> **载体存续声明（2026-10-15 13:1x 追加）**：本节申报的两个绿载体已被 10-15 13:17 那一次运行**原地覆盖**（`conan-create.log` 18597 B / `a3200ed5…` → 8614 B / `d86beb00…`；verify-report `9d6ec2e3…` → `0d65222f…`）。本节的 **from-source 库编译结论仍成立**（编译行的可读摘录保留在本窗 Windows 侧日志 `liblscp-step42-buildread-2247.log` / `liblscp-step43-buildproof-2300.log`），但"设备 `reports/` 里现存的 create.log 能证明库本体重编"这一条**已不再成立**——现存载体是缓存复用那次的输出。W4 若需现场复核库本体编译，须允许再一次 from-source 构建（本窗未做，见下一节）。

22:00 派单的唯一阶段＝把文本 tip 与一次真实端到端读数绑死。构建前落一笔纯文本提交 `4327f6e144d9cc3fe64eea56b7c29c57aff29faa`（父 `82f125d8c…`，1 file `notes.md`，24+/3−，内容仅上一节的载体存在性更正），**构建与该 tip 绑定**。

### 前置门槛与槽位（全部现场实测；载体 `.temp/QDR-1009-E05/logs/liblscp-step42-buildread-2247.log`、`liblscp-step44-result-2305.log`）
- `sh ~/tmp/uc2/gate.sh 8000` → `GATE_RC=0`，`GATE_PASS:probe=clang MemAvailable=11659MB MemFree=868MB Cached=15095MB swap余=48853MB load=20.03 PSI_full=avg10=53.5 编译器进程=0`。
- 槽位：`SLOT_OK 22:45:30 cmd=python3 scripts/ohc-run.py conan-verify liblscp 1.0.1 --profile ohos-aarch64-15461B` → `SLOT_DONE:ok MemAvailable=11699MB`。`CONAN_HOME=~/tmp/ch/home-QDR-1009-E05-liblscp`，`global.conf` 第 6 行 `tools.build:jobs=2`。本小时全队重构建只有 2 槽（统筹 22:08:35 判定扩容阈值 2×8000=16GB 未达）⇒ 未越锁、锁路径未改。
- 构建前设备 STATE 已写"构建中 + 日志绝对路径 + 预计时长"：`~/tmp/uc2/QDR-1009-E05/STATE-device.md`（written_at 22:45:27，bind_tip `4327f6e14…`，log `$D/h-build.out` / `$D/h-build.err`）。

### 命令与判决
- 官方入口恰 1 次：`python3 scripts/ohc-run.py conan-verify liblscp 1.0.1 --profile ohos-aarch64-15461B` → **`VERIFY_RC=0`**（22:45:30→22:46:16）。
- `conan-verify-report.md`：`Verdict: PASS`、`Profile: ohos-aarch64-15461B`、`Date: 2026-10-13T22:46:15.918291`；G0/G1/G2/G3 渲染 PASS；**G4 渲染 PASS 而正文含 `⚠️ 无法找到程序包 ID`**；L2/L4/L5 渲染 `✅ PASS` 而正文 `⏭️ 跳过（无 cache 路径）` ⇒ **不得概称 L5 PASS**（沿用既有并列口径，交 W4）。
- 实际 conan 命令行（`h-build.err` 回显）：`conan create <…>/archives/l/liblscp/1.0.1 -pr:h=ohos-aarch64-15461B -pr:b=ohos-aarch64-15461B --build=missing --user=ohpcd --channel=stable`。
- Error 77 同签名检查：**`ERR77_HITS=0`**、err 内"第一条真实错误"为空 ⇒ 硬门未触发，未起第 2 次构建。

### 真实端到端（非缓存复用）证据
`reports/conan-create.log`：`:91 Building from source` → `:133-148` CMake 实编译 6 个 C 目标（`client.c/common.c/device.c/event.c/socket.c/thread.c`）→ `:149 Linking C shared library liblscp.so` → `:155-156` examples 可执行链接 → `:160 Package '01d92cf3…' built` → `:182 created` → `:186 Launching test_package` → `:202 Removing previously existing 'test_package' build folder` 之后重建并运行。

### revision / package_id / 消费者读数（现值，覆盖此前申报）
- `:183` Full package reference ⇒ recipe revision **`073c332775dc48c720da23061c76705b`**、package_id **`01d92cf349a0dd98ff915f4bd99a04430171517f`**（与历次逐字相同）、package revision **`dda9f48fcded6d023abe8a4fa79c3f94`**。
- 此前申报的 `54de32d79014a9df05bbcf1b00910746` 与 package revision `679e7da89941b2d2cf7007416d951687` 属 tip `09a123cac` 那次绿跑，**自本起作废**，改绑上面的现读数。
- 消费者测试：`:266-268` 三条反悬置读数 `ret=0` / `elapsed_ms=0`（预算 `TEARDOWN_BUDGET_MS=5000`）、`:269 liblscp consumer test: 76 assertions, 0 failures`、`:270 RESULT: PASS`。
- 载体身份（构建后现场）：`reports/conan-create.log` **18597 B / `a3200ed5633895a48a10ff7bde0fad99083b6c7da8af64948ac602201ab23019`**（mtime 2026-10-13 22:46）、`reports/conan-verify-report.md` **1237 B / `9d6ec2e3aa79212013f2fffa39242defcd9a7916e74c8d1682bce3df2b885bed`**（22:46）；`reports/w3-local-ci.log`（21141 B / `267f5ec6…`）与 `.ci-result.json`（版本目录根，364 B / `5e032b09…`）mtime **仍为 2026-10-12 22:28** ⇒ 对当前 tip **仍是滞后载体**，本窗不升格、不重跑 finish 去凑。
- **为什么本轮不跑 finish**：`scripts/ohc/finish.py:186-192` 构造 `ConanVerifier` 时不传 profile、`conan_verify.py` 无环境变量读取 ⇒ 内部 step3 一律用默认名 `ohos-aarch64`，本机红，且会**覆盖**上面两个绿载体（2026-10-12 22:2x 实证过该覆盖损失）。恰 1 次限额内选择只跑 conan-verify。

### 官方 result.json 重导（未手改 JSON）
`python3 scripts/ohc-run.py result liblscp 1.0.1 --status partial --commit-hash 4327f6e14… --branch feat/liblscp-1.0.1 --agent QDR-1009-E05 --out ~/tmp/uc2/QDR-1009-E05/result-4327f6e14.json` → `RESULT_RC=0`，**1594 B / sha256 `9e98e320e2ccf99b6f651a8d659904e76d7f3274abac57d9e579c7c4b3389f69`**，`draft:false`、`feedback_pending:true`；`error_detail` 记 finish step3/5b/8 与"W4 未做"。result.json 不落提交面，也不自引用包含它自身的提交。

### 本窗自撞的两条操作错误（必须披露，不影响构建结论）
1. 上传脚本前的一条远程命令用了**双引号** ⇒ `$HOME` 在 Windows 本地展开成 `/c/Users/Admin/tmp/…`，`mv` 报 `No such file or directory`，导致 runner 内 canonical↔快照对账拿不到文件（`SLOT_DIFF_RC=2 / DIFF_LINES=0 / CANON_SHA= 空`），本次构建实际跑在既有私有快照 `9771c729…` 上。**未在建中覆盖快照**（那正是 2026-09-21"副本被原地重写⇒在途构建被打断"的机制）。构建结束后重做对账：两侧剥离行尾 CR 后 sha256 **逐字相同**（`9771c729…`）、`diff` rc=0 / 0 行 ⇒ 与 canonical（9101 B / `70a8f3cdefd489f0de4899657a5f7b6003cdb773c76ad3c2fb54b79991520754`）差异**仅为 CRLF 行尾**；所用快照内 `:80 D="$HOME/tmp/uc2/.build-slots"`、`SLOTS=2`、`MAX_SLOTS=3`（超限时夹回）⇒ 锁路径与槽数口径未被副本脱钩。
2. 一次 `tail -25 $D/h-build.err 2200` 把多余 token 当第二个文件参数 ⇒ 远端报 `tail: 2200: No such file or directory`；不影响构建，只影响那次回读渲染。

### 上一节遗留的"是否计入导出面"——本轮实测答复
`conanfile.py:36-37` 实读：`def export_sources(self): export_conandata_patches(self)` ⇒ 导出面只带补丁，`notes.md`/`manifest.yaml`/`test_package/MANIFEST.yml` 不在其中；本次构建前后 `conandata.yml`（1870 B / `c809b959…`）与 `conanfile.py` 未变。因此严格表述为：**读数的绑定对象是 tip `4327f6e14`；本次之后的纯文本提交不改 conan 读取的配方/补丁文件，故同一读数对新 tip 仍适用（这是内容层实证，不是官方 revision 计算器的输出，后续若再变仍以下一次实测为准）**。

### 新事实与统筹裁决入文本
- **QDR-1009-E06 裁 A 成立**：平台 CI worker 侧 `/data/service/hnp/bin/*` 存在且可用（16 条已合入 autotools PR 中 15 条最新有效判决为「## CI 校验通过」，正向签名覆盖 8+ worker；载体 `.temp/QDR-1009-E06/WORKER-HNP-PROBE-20261013-2100.md`）⇒ 15090 的阻塞**不得**再写成"必须等 #15461 合入"。但判决↔revision 的 SHA 绑定**未成立**（平台 `ci?id` ≠ buildbot `buildid`，旧结论作废），设备侧 Error 77 仍是本机事实——两头不得互推。
- **措辞闸门不变**：绿只能写"私有影子 profile `ohos-aarch64-15461B`（2757 B / `67404bc1…`）输入下官方工具绿"，**不得**写"官方默认管线已绿"。
- **notes.md:95 与 :112-116 的描述性文本**含 `/data/service/hnp`、`~/.harmonybrew/bin`：统筹 22:00 裁决**本轮不改**；提交面 `conandata.yml/conanfile.py/manifest.yaml/test_package/*` 实测 0 处此类路径。若将来改，只改文本、零构建。
- **上一轮列为待办的 `conandata.yml` 补丁描述错位已闭合**：现值 `patch_description` = guarded-signal-thread-exit 语义（与正文一致）；`sources.url/sha256/patch_file/patch_type/strip` 逐字未动（官方 URL 仍标量 `https://download.linuxsampler.org/packages/liblscp-1.0.1.tar.gz`，sha256 `db54a33c…`，无 `file://`/镜像/`.ghfast-bak`）。补丁现场 4024 B / `bbcf6b83…`、107 行、只改 `src/thread.c`。

### 五维账本同源（数字未变，四处统一到现读数）
`N_static=0`（tarball 内 `add_test`/`enable_testing`/`ctest`/`BUILD_TESTING` 命中 0 ⇒ `build()` 不调 `cmake.test()`，不为凑数造分母）/ `N_registered=0` / `N_executed=0` / 未执行或跳过 0 / `N_consumer=1` 程序 **76** 断言 **0** 失败。分母未缩；0/0 不作"通过"申报；消费者通过**不冒充**上游全量。`notes.md` / `manifest.yaml` / `test_package/MANIFEST.yml` / `result.json` 四处本轮同步到 76/0 与 recipe revision `073c3327…`。

### 边界与下一步唯一动作
本窗零 push / 零建 PR / 零提审 / 零框架写 / **不自审**。下一步唯一动作＝统筹排独立 CI 角色对最终 tip 做 W4，须裁定：①`L5a liblscp.so` 缺 `DT_SONAME`（上游 CMake 未设 SOVERSION，本窗不改上游命名契约）；②补丁形态（E513 推荐方案实现，反悬置组 5a/5b/5c 走库自身可达路径）；③`G4 无法找到程序包 ID` 与 L2/L4/L5 `跳过（无 cache 路径）` 的渲染语义；④finish 内部 step3 的默认 profile 红（本机事实，不代表平台 worker）。

---

## 2026-10-15 13:17 恰 1 次绑定构建（tip `4327f6e14`；配方真导出 + `test_package` 真跑，**库二进制包缓存复用**）

12:5x 派单：用户 10-13 暂停结束了本窗接单资格，root 12:4x 只恢复**接单资格**（原 job/失败计数/stale_wakes/CI 预算全保留，不构成任何门禁通过）。唯一阶段＝恰 1 次绑定构建，把 tip `4327f6e144d9cc3fe64eea56b7c29c57aff29faa` 与一次真实读数绑死，随后停在 W4 交接点。

### 前置门槛（逐项现场实测，不跳过；载体 `.temp/QDR-1009-E05/logs/liblscp-step48-precheck-1255.log`）
- 真实 HEAD/分支从本窗现场读：`4327f6e14…` / `feat/liblscp-1.0.1`；本包 0 处未提交改动，全树脏项仅 `libXext` 两条大小写假改动 + `.build-cache/`、`feedback/SKILL_FEEDBACK_5cfd5c10.md`、`pr.diff` 三个幻影/本地件（§5.1，原样不动）。
- `sh ~/tmp/uc2/gate.sh 8000` → `GATE_RC=0`，`GATE_PASS:probe=clang MemAvailable=9915MB MemFree=793MB Cached=11955MB swap余=48387MB load=20.33 PSI_full=avg10=63.13 编译器进程=0`；`/proc/meminfo` `MemAvailable=10115072 kB`。
- 在途核对：我 10-13 那个 pid 50109 runner **已死**（`RUNNER_ALIVE=0`、无残留构建进程 `BUILD_PROC_COUNT=0`）；槽位标记 `slot=FREE ×3`；他人的 `slot1.owner`（mtime 10-15 13:11）只登记不删。
- 影子 profile 先回读身份：`ohos-aarch64-15461B` **2757 B / `67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e`**（与申报逐字相同）；仓库只读 `ci/conan/profiles/ohos-aarch64` 2101 B / `7ebd43d2…` **一字节未动**。`global.conf:6 tools.build:jobs=2`。
- `memcap-run.py --probe` 消费者程序：`MEMCAP[probe] peak=4MB budget=0MB rc=0 用时0.6s`（这是对**既有已构建** `test_liblscp` 的重跑评估，**不是**本轮绑定构建的读数，不得混作端到端证据）。
- **槽位快照对账闭合**：root 已把权威 `经验文档/tools/build-slot.sh` 改为 LF ⇒ 权威版与本窗私有快照 `build-slot.QDR-1009-E05.sh` **逐字相同**（8894 B / `9771c7291ecabfc3e460368cae60ae1c1e5ea153845bb41b5b7fa7ad8dc904c6`，`diff` rc=0 / 0 行）⇒ `SLOT_SNAPSHOT_IN_SYNC=yes`（此前 `no` 与"417 行差异"是 CRLF 假象）。本轮**未同步覆盖**任何副本（两侧已相同，无动作可做），锁路径仍 `$HOME/tmp/uc2/.build-slots`，`SLOTS=2` / `MAX_SLOTS=3`。

### 命令与判决（恰 1 次，未起第 2 次）
- 构建前设备 STATE 写"构建中 + 日志绝对路径 + 预计时长"：`~/tmp/uc2/QDR-1009-E05/STATE-device.md`（written_at 13:17:18，bind_tip `4327f6e14…`）。
- 官方入口恰 1 次：`python3 scripts/ohc-run.py conan-verify liblscp 1.0.1 --profile ohos-aarch64-15461B` → **`VERIFY_RC=0`**（13:17:20→13:17:33；`SLOT_OK 13:17:20 cmd=…` + `SLOT_DONE:ok MemAvailable=9572MB`）。底层命令回显：`conan create <…>/archives/l/liblscp/1.0.1 -pr:h=ohos-aarch64-15461B -pr:b=ohos-aarch64-15461B --build=missing --user=ohpcd --channel=stable`。
- `reports/conan-verify-report.md`：`Verdict: PASS`、`Profile: ohos-aarch64-15461B`、`Date: 2026-10-15T13:17:33.676075`；G0/G1/G2/G3 PASS；**G4 渲染 PASS 而正文 `⚠️ 无法找到程序包 ID`**；L2/L4/L5 渲染 `✅ PASS` 而正文 `⏭️ 跳过（无 cache 路径）` ⇒ **不得概称 L5 PASS**，与 `w3-local-ci.log:350/365` 的 fail 并列保留、不改判，交独立 W4。
- **Error 77 同签名真命中 = 0**（对 `reports/conan-create.log` 与 `i-build.err` 各自直接 `grep -cE "C compiler cannot create executables|Error 77"` 均返回 0）⇒ 硬门未触发。**必须披露**：runner 里打印的 `ERR77_HITS=1` 是本窗自测脚本缺陷——把 `grep -c` 的结果写文件后又用 `wc -l` 数该文件行数（数的是行数不是匹配数）。真实计数见 `.temp/QDR-1009-E05/logs/liblscp-step52-loginspect-1325.log`。

### 关键限定：本轮**不是** from-source 库重编（缓存复用）
`reports/conan-create.log`（8614 B）现场行：`:10 Exported: liblscp/1.0.1@ohpcd/stable#073c332775dc48c720da23061c76705b (2026-10-15 05:17:24 UTC)`（配方真实重新导出），而 `:58/:62/:73/:77` 显示 recipe 与二进制包 `01d92cf349a0dd98ff915f4bd99a04430171517f#dda9f48fcded6d023abe8a4fa79c3f94` 均为 **`- Cache`** ⇒ **库本体未重编**，运行时间仅 13 s。本轮真实重做的部分：`test_package`——`:83 Removing previously existing 'test_package' build folder` → `:137 Building C object CMakeFiles/test_liblscp.dir/test_liblscp.c.obj` → `:138 Linking C executable test_liblscp` → `:144 RUN: ./test_liblscp` → `:150 liblscp consumer test: 76 assertions, 0 failures` → `:151 RESULT: PASS`。上游测试注册/执行痕迹 **0**（`UPSTREAM_TEST_HITS=0`）。
⇒ 本轮读数的准确表述是：**私有影子 profile 输入下，配方导出 + 消费者端到端绿；库本体的 from-source 编译证据仍属 10-13 22:46 那次（其设备载体已被本轮覆盖，见上一节的载体存续声明）**。不得把本轮写成"端到端重编译绿"。

### 读数与载体身份（现值）
- recipe revision **`073c332775dc48c720da23061c76705b`**（与 10-13 现值逐字相同）、package_id **`01d92cf349a0dd98ff915f4bd99a04430171517f`**、package revision **`dda9f48fcded6d023abe8a4fa79c3f94`**。
- 构建输入四件与 10-13 22:46 那次**逐字相同**（`conandata.yml` 1870 B / `c809b959…`、`conanfile.py` `6efb9e19…`、`test_package/test_liblscp.c` `082dd54f…`、`patches/0001-…patch` 4024 B / `bbcf6b83…`）⇒ revision 一致是实测复现，非推断。
- 绿载体：`reports/conan-create.log` **8614 B / `d86beb00b9c623dfe3fafd38f2977257c8c6acc574a3860618862c1c2a7a0f08`**、`reports/conan-verify-report.md` **1237 B / `0d65222f9db24388cdff2a25a346d3b384dc7c7a558c288142c4d715ab26c827`**（均 mtime 2026-10-15 13:17）；`reports/w3-local-ci.log`（21141 B / `267f5ec6…`）与 `.ci-result.json`（版本目录根，364 B / `5e032b09…`）mtime **仍 2026-10-12 22:28** ⇒ 对当前 tip **仍是滞后载体**，本窗不升格、不重跑 finish 去凑。
- 消费者读数分列：76 断言 / **执行 76、通过 76、跳过 0、失败 0**（`test_liblscp` 1 个程序；三条反悬置读数 `ret=0`、`elapsed_ms=0`，预算 `TEARDOWN_BUDGET_MS=5000`）。

### 官方 result.json 重导（未手改 JSON、未绕过校验）
`python3 scripts/ohc-run.py result liblscp 1.0.1 --status partial --commit-hash 4327f6e14… --branch feat/liblscp-1.0.1 --agent QDR-1009-E05 --out ~/tmp/uc2/QDR-1009-E05/result-4327f6e14-1015.json` → **`RESULT_RC=0`，1743 B / `5693abbf19ad5b2f6a302016adb9c19b363eaf46e11e920793bba0c5e4fb2c27`**，`draft:false`、`feedback_pending:true`；`error_detail` 如实写未达终态缺项（W4 未做 / finish step3 默认 profile 红且会覆盖绿载体 / 本轮二进制包缓存复用且覆盖 from-source 载体）。
两次调用曾被官方校验拦下：`checkpoints[0].message 长度 > 200` → `RESULT_RC=2`、`EXIT_REASON: result_invalid`、**未落盘**；缩短该字段后通过。`reports/result.json` 与 `reports/conan-verify-result.json` 现场 **ABSENT** ⇒ result 载体只在本窗命名空间，不在提交面，也不自引用包含它自身的提交。

### 五向同源（本轮统一到 13:17 现值）
`notes.md`（本节）/ `manifest.yaml` / `test_package/MANIFEST.yml` / `result.json`（`5693abbf…`）/ PR 正文预备：recipe revision `073c3327…`、package_id `01d92cf3…`、package revision `dda9f48f…`、消费者 76/76/0 跳过/0 失败、上游 0，载体 `8614 B / d86beb00…` + `1237 B / 0d65222f…`，并**都带"库二进制包缓存复用"限定**。
五维账本未变：`N_static=0`（tarball 内 `add_test`/`enable_testing`/`ctest`/`BUILD_TESTING` 命中 0 ⇒ `build()` 不调 `cmake.test()`，不为凑数造分母）/ `N_registered=0` / `N_executed=0` / 未执行或跳过 0 / `N_consumer=1` 程序 76 断言；分母未缩，0/0 不作"通过"申报，消费者通过**不冒充**上游全量。

### 边界与下一步唯一动作
本窗零 push / 零建 PR / 零提审 / 零框架写 / **不自审**；`pre_pr_audit.py generate` 本轮**未重跑**（不作 W4 替代）；adns 15060 未碰；proxycheck 15066 不代他人做。措辞闸门：绿只能写"私有影子 profile `ohos-aarch64-15461B`（2757 B / `67404bc1…`）输入下官方工具绿"。
下一步唯一动作＝**交独立 W4**（CIA/CIB 由统筹排），除上一节四项外须一并裁定本轮新增面：⑤本小时证据的作用域仅为"导出面 + 消费者测试"，库本体编译需否再开一次 from-source 由 W4 判定；⑥`ERR77_HITS=1` 的计数缺陷与真实 0 命中的披露是否足以支撑"硬门未触发"结论；⑦from-source 绿载体被覆盖后的证据链完整性（现存编译摘录仅为本窗日志）。


---

## 2026-10-15（回合 28）P1-1 DT_SONAME 真机验证 + P1-2/P2/P3 读数重绑

派单：恰一次合法单槽真机验证 + 文本重绑。执行窗 `QDR-1009-E05`，工作树起点 tip `94712c5ffd05c74a6771ea7438d364e21a074b6b`（DT_SONAME 配方注入即提交在该 tip 上，本轮未再改配方文件），分支 `feat/liblscp-1.0.1`。统筹此前的「加 SOVERSION」字面处方已由本窗一手反证并作废，本轮不再执行该无效动作。

### 一次性构建动作序（全部现场回读）

1. `sh ~/tmp/uc2/gate.sh 8000` → `GATE_PASS:probe=clang MemAvailable=11365MB MemFree=1013MB Cached=14543MB swap余=48801MB 编译器进程=0 RSS=0MB`，`GATE_RC=0`。
2. 槽位快照 `~/tmp/uc2/QDR-1009-E05/build-slot.QDR-1009-E05.sh`（8894 B）与本窗从仓库 canonical scp 上去的 `build-slot.repo-20261015.sh` `diff` 结果 **IDENTICAL**（规则未变更，快照无需刷新）；锁路径仍 `$HOME/tmp/uc2/.build-slots`（第 80 行）。占 1 槽：`SLOT_OK 19:10:32` → `SLOT_DONE:ok MemAvailable=11446MB`。
3. 内存封顶：先 `memcap-run.py --probe`（对本消费者程序，见下节实测值），构建体本身以 `memcap-run.py --mb 6000` 包裹 → `MEMCAP[run] peak=261MB budget=6000MB rc=0 用时27.9s`。
4. **恰 1 次 conan create**（官方入口 + 私有影子 profile，`--build=missing` 由工具自带）：
   `python3 scripts/ohc-run.py conan-verify liblscp 1.0.1 --profile ohos-aarch64-15461B` → `BUILD_RC=0`，报告 `Verdict: PASS / Profile: ohos-aarch64-15461B / Date: 2026-10-15T19:11:00.763341`。
   本轮**未**跑 `finish`（其内部 step3/step35 会再触发一次 conan create，超出「恰一次」边界），也**未**起第二次构建、零在途 PID。

### P1-1 判据：`readelf -d` 的 DT_SONAME 改前/改后一手对照

| 项 | 改前（修复前 tip 的库本体，设备在盘原件） | 改后（本轮 tip `94712c5ff` 真建产物） |
|---|---|---|
| 路径 | `p/b/libls6bc27c8dec250/p/lib/liblscp.so` | `p/b/libls31b1bb95a6ef6/p/lib/liblscp.so` |
| 体积 / sha256 / mtime | 84288 B / `20eab61966906c1cfec7e612d4841fb16debe5958d49104e1c83bdae8a4c6f9b` / 2026-10-12 13:32 | 88384 B / `4fc43378512cd0c145e747d91671bf0cbae90522e3153f7d1fe08c13325c4f3a` / 2026-10-15 19:10 |
| `readelf -d` dynamic | 仅 `0x0000000000000001 (NEEDED) Shared library: [libc.so]`，**SONAME 命中 0** | `0x0000000000000001 (NEEDED) Shared library: [libc.so]` + **`0x000000000000000e (SONAME) Library soname: [liblscp.so]`，SONAME 命中 1** |
| 包内 lib 目录 | 单一 `liblscp.so` | `FILE_COUNT=1 / SYMLINK_COUNT=0`（扁平单文件、无版本化符号链接，包布局与 `cpp_info.libs=["lscp"]` 均未变） |
| 链接命令 `link.txt` | `grep -c soname` = **0** | `grep -c soname` = **1**，实文为 `clang -fPIC -O3 -DNDEBUG -shared -Xlinker --dependency-file=… -Wl,-soname,liblscp.so -o liblscp.so … -lpthread` |

配方注入变量确实到达 CMake：`generators/conan_toolchain.cmake:197-198` 两行 `set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname," CACHE STRING …)` / `set(CMAKE_PLATFORM_NO_VERSIONED_SONAME "ON" CACHE STRING …)`；`CMakeCache.txt:156` `CMAKE_PLATFORM_NO_VERSIONED_SONAME:STRING=ON`、`:200` `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG:STRING=-Wl,-soname,`。

消费者侧一手读数：`test_package/build/clang-15-armv8-17-release/test_liblscp`（35264 B / sha256 `40193e24859b451827e3f024804eafa6d2d731cee318e1627ce729def5dd99c4`，mtime 2026-10-15 19:10）`readelf -d` 记 `NEEDED [liblscp.so]` + `NEEDED [libc.so]` ⇒ 下游按 **SONAME 名**（非路径形）寻址成立。本机无 `ldd`（`ldd: inaccessible or not found`），故动态寻址以 `readelf -d` + 真实运行退出码为判据；消费者在 `LD_LIBRARY_PATH` 指向包 lib 目录时真实运行通过（下节）。

**P1-1 结论：成立**（判据＝产物 `readelf -d` 出现 DT_SONAME，本轮已一手取得）。根因与本窗采用的改法见上一节；`CMake 不认识 HarmonyOS` 这一事实也在本轮载体 `conan-create.log:245-246` 由 CMake 自己打印出来（`System is unknown to cmake, create: Platform/HarmonyOS to use this system …`）。

### P1-2 证据载体可复核性（冻结新断言行，不 `git add -f reports/`）

载体身份：`archives/l/liblscp/1.0.1/reports/conan-create.log` **18597 B / 271 行**，sha256 `743a46df09615def61141549f6a20bdabafe75f741722562e3ff5f666523811f`，mtime 2026-10-15 19:10，采集时间 2026-10-15 19:10:36→19:11:00（`Exported …#3475dd5e…` 行内 UTC 时间戳 2026-10-15 11:10:36）。

**声明：该日志是 `.gitignore` 覆盖的本地件、不随 PR 提交；以下逐字冻结的读数绑定 tip `94712c5ff`（recipe revision `3475dd5e700939ef50e940dd8ee9df6b`），复核者若在自己工作副本看不到该文件属正常，应按本节行号 + sha256 与自身重跑读数比对。**

```text
264:version: package=liblscp version=1.0.1 build=1.0.1
265:lscp_client_create: cmd: connect: Connection refused
266:thread cancel+join (live worker): ret=0/0 elapsed_ms=0
267:thread destroy (natural exit): ret=0 elapsed_ms=0
268:socket agent free (live worker): ret=0 elapsed_ms=0
269:liblscp consumer test: 76 assertions, 0 failures
270:RESULT: PASS
```

同一载体内的 from-source 与打包证据行号：`:10` 导出 rrev；`:62` 主二进制包缺失判定；`:83` `…:01d92cf3… - Build`（**本体真重编**，非缓存命中）；`:104` `Calling build()`；`:133-148` 六个 C 目标逐个编译；`:149` `Linking C shared library liblscp.so`；`:151-157` examples 编译与链接；`:164` `Calling package()`；`:196` test_package 消费引用（该处 `- Cache` 指包本体已在缓存，消费者随后仍真实重编译）；`:218` 消费者 `Calling build()`；`:256/257` 消费者重编译与链接；`:181` `Created package revision be46b0180663ef16c1aac628663a835c`；`:182/:183` 包 ID 与完整引用。全载体 `grep -cE "Error|error:"` = **0**。

`test_package/MANIFEST.yml` 的 `assertion_count: 76` 与 `manifest.yaml` 的 `total/passed/failed = 76/76/0` 均引同一载体同一行号（三处同源，另加本 notes 与 result.json 共五处）。

### 读数现值（revision 三元组，全部一手取自新载体）

- recipe revision **`3475dd5e700939ef50e940dd8ee9df6b`**（旧 `073c332775dc48c720da23061c76705b` **作废**）
- package_id **`01d92cf349a0dd98ff915f4bd99a04430171517f`**（历次逐字相同：`[settings]` 与仓库 profile 等价、package_id 由 settings/options 派生，属实测而非预期）
- package revision **`be46b0180663ef16c1aac628663a835c`**（旧 `dda9f48fcded6d023abe8a4fa79c3f94` **作废**）
- 输入件 sha：`conanfile.py` `6f5516428756877f12f20886155b56c80fd6bc1de3825712e312ec547fc88a65`（含 `:75-76` 两行注入，提交于起点 tip，本轮**未改**）、`conandata.yml` `c809b959f785bb928ae5da7e5abb60400c24bb3b080f1ec38fc26e149e92fb5e`（未动）、`patches/0001-ohos-thread-cancel-guarded-signal-exit.patch` `bbcf6b83ff92dc968566595940dcdd4a3a9ac998fc299d8a1c4c99769f5398f8`（未动）
- 影子 profile 输入身份：`~/tmp/ch/home-QDR-1009-E05-liblscp/profiles/ohos-aarch64-15461B` 2757 B / `67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e`；仓库只读框架 profile `ci/conan/profiles/ohos-aarch64` 2101 B / `7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793`（**逐字未改**）

### P2 措辞同步（照审计结论，不留旧写法）

- **G4 语义**：`reports/conan-verify-report.md`（现值 1237 B / sha256 `8494f384932de700b355f0d535bd4a42763bcabef8ddcc14c74a3107bdd609d5`，2026-10-15 19:11）第 38-39 行渲染 `## G4: ✅ PASS` 而正文 `⚠️ 无法找到程序包 ID`。**这是框架侧缺陷**：`scripts/ohc/conan_verify.py:725→737` 用带 `@ohpcd/stable` 的 ref 取包信息触发 KeyError 后回落该文案，与本包产物无关；包 ID/revision 由载体 `:10/:181/:182/:183` 独立取证。框架修复走**单独 PR**，不并入本配方 PR。
- **L2/L4/L5**：该报告把 L2/L4/L5 三节渲染为 `✅ PASS` 而正文均为 `⏭️ 跳过（无 cache 路径）`。本包**禁止**出现「L2/L4/L5 通过」写法；唯一允许表述：**conan-verify 因无 cache 路径跳过 L2/L4/L5，产物门禁以 `build_and_test.sh` 的 L5 读数为准**。
- **影子 profile 绿的作用域**：本轮全部「绿」只能表述为「**私有影子 profile `ohos-aarch64-15461B`（2757 B / `67404bc1…`）输入下官方工具绿 ≠ 官方默认管线绿**」。仓库默认 profile 输入在本包上的历史终态仍是红（`/data/service/hnp/bin/clang` 硬编码、未合入的 #15461），与 E06 的定档 A 并列不互推。
- **上游 0 注册测试维持**：tarball 内 `add_test` / `enable_testing` / `ctest` / `BUILD_TESTING` 命中 0 ⇒ `N_static=0 / N_registered=0 / N_executed=0`，`build()` 不调 `cmake.test()`（不为凑数造分母）；上游测试表与适配后表**都写 0/0**，不得写 100%。消费者 76 断言单列，不冒充上游全量。

### P3 卫生项本轮处置

- `max_rss_mb`：`memcap-run.py --probe` 对消费者程序 `test_liblscp` 实测 **`MEMCAP[probe] peak=4MB budget=0MB rc=0 用时0.6s`**（`PROBE_RC=0`）；`test_package/MANIFEST.yml:46 max_rss_mb: 8` 为该实测峰值的 2 倍预算（非起草估值 64）。构建体本身以 `--mb 6000` 预算包裹，实测峰值 261 MB。
- **`conanfile.py:28 url = ""` 本轮未填**——不是遗漏：`url` 属配方导出面，任何改动都会再次轮换 recipe revision，使本窗刚取得的 DT_SONAME 一手读数与提交 tip 脱绑。该项须与下一个「带授权构建的配方改动阶段」一并做；在此之前保持原样并在 result.json 的缺项中如实列明。

### 旧 W3 载体存续声明（不得升格、不得删）

- `reports/w3-local-ci.log` 21141 B / sha256 `267f5ec6a6ddd7e55bf12a9a371d6818a9d8b8117a7da4a2e37851e0e3e30ede`（mtime 2026-10-12 22:28）：其内含**已被移除的旧补丁名** `cooperative-join` 与修复前 65 断言读数，属修复前 tip `e13eadc29` 的历史件；本轮可复核的新载体是上一节的 `conan-create.log`（`743a46df…`，76 断言行号 269/270）。旧件按 §9「不删他人/历史件」保留在盘，仅作历史签名引用。
- `.ci-result.json`（版本目录根，364 B / `5e032b0954618f6ac149e1bf4c2ff3fcfaa99f2a13abe0f8c3b9d8558fc5a886`，`log_sha256` 指回上面那个历史件）与 `reports/ci-metadata.json`（792 B，`2026-10-12T14:28:22Z`，记 `L5: fail soname_gate_failed`）在**当前 tip 上仍是滞后载体**：本轮按「恰一次 conan create」边界未重跑 `finish`/`build_and_test.sh`。因此**官方 W3/L5 绑定当前 tip 的载体尚不存在**，P1-1 的成立判据取自产物 `readelf -d` 一手读数与 `link.txt` 对照；如需官方 W3 L5 绿读数绑定当前 tip，须由统筹另派一个含 `finish` 的授权阶段（会再触发一次构建）。`ci-metadata.json` 的 `L5 fail` 记录的是改前事实，不改写、不伪造。

### 本轮边界执行与下一步唯一动作

零 push / 零建 PR / 零提审 / 零平台写 / 零 claim-lease-import / 未改框架文件 / 未动他人 worktree 与产物 / 未读未打印令牌 / 未新建 Cron-Goal-Agent。外层命令未用 `2>&1`。`pre_pr_audit.py report` 子命令**不由本窗执行**（照 root 口径「report 只读取独立结论，本窗不得自审」），本窗只跑 `generate` 与 `check` 并如实回报读数。
**下一步唯一动作**＝请统筹派 CIA 或 CIB 在本轮新 tip 上做**新一轮独立 W4（只读、零槽）**；W4 通过后由统筹裁定是否另派含 `finish` 的 W3 载体绑定阶段。
## 2026-10-15（回合 29）仓根 `.ci-result.json` 与 `conanfile.py` url 空值清项（恰一次合法单槽真机构建）

派单＝统筹 20:00 的唯一阶段。执行窗 `QDR-1009-E05`，起点 tip `151a1dcc7a92fcb2e45bde5d834dcc03e3ac8454`（上一回合提交面），分支 `feat/liblscp-1.0.1`。本轮**不重复 DT_SONAME 取证**（上一回合已一手证实），只清两个缺项并把三处文本载体按新读数重绑。

### 改动面（逐文件核对）
1. `conanfile.py:28` `url = ""` → `url = "https://download.linuxsampler.org/packages/liblscp-1.0.1.tar.gz"`，逐字取自 `conandata.yml:7` 的官方 https 标量。文件 sha256 `6f5516428756877f12f20886155b56c80fd6bc1de3825712e312ec547fc88a65` → `e743c22366d48bbfe7436ec53629319fe07a4841701c98321aa34686ac43c79c`，`git diff` 恰 1 增 1 删；禁用形态 grep（`file://`/`ghfast`/`.orig`/`mirror`）命中 **0**；`ast.parse` OK；`conandata.yml` 一字节未动（`git status` 不含它）。
   仓内先例核对（只读）：`archives/a/audioflux/0.1.9` 与 `archives/l/ladspa-sdk/1.17` 的 recipe 里 `url` 也是空串（前者带 `# CI fills this` 注释），⇒ 空串并非违规写法，但正文要求"上游版本/上游 URL"可机读，本轮按派单填官方标量。
2. `preflight_check.sh liblscp/1.0.1` 实测 **RC=0 但只跑依赖预检**（原文 `未找到依赖声明…` + `[OK] 预检通过（无依赖需要检查）`），**不校验 recipe url / SHA / R37**。⇒ URL 与 SHA 的复核改由本窗四件一手动作承担：与 `conandata.yml:7/:8` 逐字比对、`git diff` 核面对象、禁用形态 grep、以及构建期 conan 对 tarball sha256 的强制校验（`:163 Sources correctly downloaded from …` + `:164 Uncompressing 963d07ec_liblscp-1.0.1.tar.gz`）。
3. `notes.md` 的 finish 收尾块由官方工具自行搬动（旧的 `编译结束 2026-10-12 22:26 / 最终状态 built` 段被删，新的 `编译结束 2026-10-15 20:25 / 最终状态 built` 追加在文末），本窗未手编该块；本节由本窗追加在其前。

### 门禁与资源（恰一次构建，零排队空耗）
- `sh ~/tmp/uc2/gate.sh 8000` → `GATE_RC=0`，原文 `GATE_PASS:probe=clang MemAvailable=11155MB MemFree=1040MB Cached=14745MB swap余=48755MB inode余=? load=20.850 21.190 21.037 PSI_full=avg10=53.62 编译器进程=1 RSS=133MB`。
- 槽位快照 `~/tmp/uc2/QDR-1009-E05/build-slot.QDR-1009-E05.sh`（8894 B / `9771c7291ecabfc3e460368cae60ae1c1e5ea153845bb41b5b7fa7ad8dc904c6`）与本窗 19:08 从仓库 canonical 取来的 `build-slot.repo-20261015.sh` `diff` 结果 **IDENTICAL**（规则未变更，快照无需刷新），锁路径仍 `$HOME/tmp/uc2/.build-slots`。`--wait 1800 --mem 8000` 立即 `SLOT_OK 20:24:57`，只占 1 槽；起建前 `MemAvailable=11427840 kB`（≈11.4 GB）< 2×`--mem`（16 GB）⇒ **未请求第 3 槽扩容**（与派单实测一致）。
- 硬预算包裹 `memcap-run.py --mb 2000` → 末行 `MEMCAP[run] peak=110MB budget=2000MB rc=1 用时163.7s`（`rc=1` 是被包裹的 finish 自身退出码，见披露）。
- 命令：`python3 scripts/ohc-run.py finish liblscp 1.0.1 built`，环境 `CONAN_HOME=~/tmp/ch/home-QDR-1009-E05-liblscp`、`CONAN_PROFILE=ohos-aarch64-15461B`（影子 profile 起建前回读 2757 B / `67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e`；仓库 profile 2101 B / `7ebd43d2…` 一字节未动）、`MAKEFLAGS=-j2`、`TMPDIR=~/tmp/uc2/QDR-1009-E05/tmp`。仓内 `ci/`、`scripts/`、`templates/`、`knowledge/` **零写**。
- 起建前把将被覆盖的载体 `cp -p` 存副本到 `~/tmp/uc2/QDR-1009-E05/r29-pre/`，回读 sha256 与在-site 原件逐字相同：`conan-create.log` 18597 B / `743a46df…`、`conan-verify-report.md` 1237 B / `8494f384…`、`w3-local-ci.log` 21141 B / `267f5ec6…`、版本目录 `.ci-result.json` 364 B / `5e032b09…`、`ci-metadata.json` 792 B / `2384ebfc…`。

### 官方 W3/L5 载体（本轮新增，两个缺项之一已清）
`reports/w3-local-ci.log` **21525 B / 377 行 / sha256 `a53c19a8e35b67cff6aeafc7b1d522de10dede2dfb5c6625734370efab99053e`**，mtime 2026-10-15 20:27：
- `:1 $ setup.sh (RC=0)`、`:14 $ build_and_test.sh archives/l/liblscp/1.0.1 (RC=0)`
- `:7/:10/:17` 记录 `Profile ohos-aarch64-15461B`（同一输入）；`:92-95` Pre-download 把 conandata 临时换成 `file://` 本地缓存、`:377` 结束时还原为官方 URL ⇒ 现场复核 `conandata.yml:7` 仍是官方 https 标量、`:8` sha256 未变、`git status` 不含 `conandata.yml`
- `:106 Exported: liblscp/1.0.1#0cb035c666cf01a1730c4a3e166b2f41 (2026-10-15 12:25:52 UTC)` ⇒ 该值是**运行态** rrev（本轮 r30 更正：上一轮把它写成"本轮要绑的新 rrev"不完整）。r30 只读重算实测：`:106` 那次导出的 conandata 是 Pre-download 临时注入后的 **1926 B / `8fb39be4ba6a4d920ab9e40c2b4337eeb688fe5d52cd250c646211886f498cb4`**（`:7` 为 `file://`，https 命中 0），索引目录 `p/liblsc91c31145bc33`、reference `liblscp/1.0.1`（无 user/channel），packages 表对其**有行**（`01d92cf3…` / `339399f7…` / `b/libls008a56c021d75`）；而**交付面**（`conandata.yml` 1870 B / `c809b959f785bb928ae5da7e5abb60400c24bb3b080f1ec38fc26e149e92fb5e`，`:7` 官方 https + 同一 `conanfile.py` `e743c223…`）的 rrev 是 **`b1944ed936b9c777954acb4c85a9125f`**（reference `liblscp/1.0.1@ohpcd/stable`、目录 `p/libls421116f79ad15`），packages 表对其**零行 ⇒ 交付 rrev 自身未构建，不得写成该 rrev 已构建并通过**。两次导出相差 **31.01 s**（交付面 epoch `1792067121.94` / 运行态 `1792067152.96`，后者折 UTC 正是 `:106` 行内时间）。因此归因更正：`0cb035c6…` 的真因是**注入改变了导出 conandata 的字节**，而不是"填 `url` 使 rrev 由 `3475dd5e…` 轮换"——`3475dd5e…` 侧的 conanfile 是填 url 前那版（`4729 B / 6f551642…`）。两值并列申报、不合并。构建输入等价是**申报的论证**而非交付侧实测：官方 URL 与注入 URI 对应同一源码 tarball `db54a33c…`（98261 B）、同一 `conanfile.py` `e743c223…`（4792 B）与同一补丁字节；`liblscp.so 88384 B / 4fc43378…`（`DT_SONAME=liblscp.so`）**只指运行态实测产物**，交付 rrev 未构建、无该侧产物可作二进制比较，不得写成"两侧逐字相同"⇒ 本轮纯文本改证据标识、**零重建**。重算载体：`.temp/QDR-1009-E05/liblscp-r30/r30_stepA_verify.out`（10213 B / sha256 `3a92df0533b5792398d4093e2e473f7444f116774c6d574c747d479f4c744a57`，`cache.sqlite3` 28672 B / `ad60935e…` 的 `cp -p` 副本经离线 `mode=ro` SQL 读取，零构建零占槽零清理）。
- `:157 Forced build from source`、`:159 … 01d92cf349a0dd98ff915f4bd99a04430171517f - Build`、`:209-224` 编译 6 个 C 目标（`client/common/device/event/socket/thread.c`）、`:225 Linking C shared library liblscp.so`、`:240 Calling package()`、`:253 Packaged 1 '.so' file: liblscp.so`、`:257 Created package revision 339399f757bd0746705e89fa602ce12c`、`:259 Full package reference liblscp/1.0.1#0cb035c6…:01d92cf3…#339399f7…`、`:260` 包目录 `p/b/libls008a56c021d75/p`
- 消费者：`:278 Removing previously existing 'test_package' build folder` → `:332` 编译 `test_liblscp.c` → `:333` 链接 → `:339 RUN: ./test_liblscp` → **`:345 liblscp consumer test: 76 assertions, 0 failures`** → **`:346 RESULT: PASS`**
- 官方逐条判决：`:22 G0_RESULT=pass`、`:62 KC_RESULT=pass`、`:89 JC_RESULT=pass`、`:363 L0_RESULT=pass: all checks passed`、`:364 L1_RESULT=pass: test_package executed`、`:351 L1b pass`、`:352 L1c No upstream make check/ctest in log`（与 `upstream_total=0` 同源）、`:356-359 L1e 破坏性反向验证 pass`（把 `lib/` 与 `include/` 移走后消费者测试即失败 ⇒ 测试实质依赖被测包，非假测试）、`:365 L2_RESULT=skip: no bin/ dir`、`:366 L4_RESULT=pass: patches clean`、**`:355 [ok] L5: lib/ has content (library package)` + `:367 L5_RESULT=pass: lib/ has content`**
- `:371-375 Build Summary Total 1 / Success 1 / Failed 0 / Pass rate 100.0% (1/1)`
- **`L5a` / `缺少 DT_SONAME` / `soname_gate_failed` 在本日志 grep 命中 0** ⇒ 上一回合起长期挂着的"L5 双载体冲突"（旧 `267f5ec6…` 载体的 `:350/:365` fail vs verify-report 渲染 PASS）在本 tip 上已由**同一份官方 W3 日志自身**消解：不存在 fail 行，也不需要拿 verify-report 的渲染去反推。历史 fail 行仅作为修复前 tip `e13eadc29` 的历史签名保留引用。

`.ci-result.json`（版本目录根，由官方 `finish.py:236 _write_ci_result(passed=True)` 在 W3 pass 分支写出）：**364 B / sha256 `61df0c25984fac61758b5b6668c379eb2bec04d27ca63f8b378e3552d505e542`**，逐字内容 `exit_code: 0`、`step: W3_local_ci`、`timestamp: 2026-10-15T20:27:23.137080`、`integrity_hash: 5b4281c248ee825e`、`log_sha256: a53c19a8…` ⇔ 上面那份 W3 日志互绑成立。

**仓根缺项的闭合方式（派单 ④ 授权的唯一手段）**：框架侧路径不一致——写方 `scripts/ohc/finish.py:270` 是 `self.archive_dir / ".ci-result.json"`（版本目录），读方 `scripts/pre_pr_audit.py:307` 是 `repo_dir / ".ci-result.json"`（仓根）。本窗按授权用 `cp -p` **逐字转存**一份到仓根，两份实测 `wc -c` 均 **364**、`sha256sum` 均为 **`61df0c25…`**（逐字节相同）；未手编内容、未改框架、未用 `--force` 绕 check。`.ci-result.json`（仓根与版本目录）与 `ci-metadata.json` 都被 `.gitignore` 覆盖（`:269` 与 `:244`）⇒ 属本地现场载体，不进 PR 面。

### 新 rrev 下 DT_SONAME 仍逐字成立（派单 ⑦ 的核验，不是重复取证）
`readelf -d` 于本轮包目录 `~/tmp/ch/home-QDR-1009-E05-liblscp/p/b/libls008a56c021d75/p/lib/liblscp.so`（**88384 B / `4fc43378512cd0c145e747d91671bf0cbae90522e3153f7d1fe08c13325c4f3a`**）：`0x000000000000000e (SONAME) Library soname: [liblscp.so]`、`0x0000000000000001 (NEEDED) Shared library: [libc.so]`；`lib/` 下仅此一个 `.so` 加 `pkgconfig/`（无版本化符号链接，与配方注入的 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` 一致）。该产物与上一回合 rrev `3475dd5e…` 下的产物 **字节逐字相同**（同 88384 B、同 sha256）⇒ 本轮填 `url` 只改配方元数据、不改编译输出；官方 L5a 门（`build_and_test.sh:1542-1603`，判据为 `readelf -d` 有 DT_SONAME 且非绝对路径）在 `readelf` 实测可用（`~/usr/local/bin/readelf`）的前提下判 pass。改前对照仍是 `p/b/libls6bc27c8dec250/p/lib/liblscp.so`（84288 B / `20eab619…`，SONAME 命中 0）。

### 上一回合遗留的两处文本缺陷（本窗自证自修）
1. `manifest.yaml` 的 `conan:` 注释块末尾 `# [settings] 与仓库 profile 等价…` 被上一回合重绑脚本**重复写入一次**（锚点范围差一行）⇒ 本轮删重，现场 grep 该行计数须为 1。
2. 同块键值 `recipe_revision: 073c3327…` / `package_revision: dda9f48f…` 与注释里"旧值作废"自相矛盾（上一回合只重绑注释、没改键）⇒ 上一回合按实测把键改为 `0cb035c6…` / `339399f7…`；`package_id: 01d92cf3…` 不变（由 settings/options 派生，历次逐字相同是实测而非预期）。**r30 再更正（消费独立 W4 的 P1）**：把键写成 `0cb035c6…` 仍是证据身份误绑——该值是运行态（注入面）rrev，交付面真值是 `b1944ed9…` 且其自身未构建，故本轮 `manifest.yaml` 键改为 `recipe_revision: b1944ed936b9c777954acb4c85a9125f`，并新增 `recipe_revision_runstate: 0cb035c666cf01a1730c4a3e166b2f41` 与 `recipe_revision_runstate_cause`（成因、两侧 conandata 字节数与 sha、epoch 差、packages 零行）两条披露键；`test_package/MANIFEST.yml` 与本节同步为双值。零重建，无任何构建动作。

### 披露（不升格、不自裁）
- `FINISH_RC=2`（memcap 记被包裹命令 `rc=1`）：官方 `finish.run()` 的 step3（`finish.py:187-190` 构造 `ConanVerifier` **不传 profile** ⇒ `conan_verify.py:77` 默认 `ohos-aarch64`；`conan_verify.py:166-183/555-559` 因仓库 profile 文件存在而用其**绝对路径**）走仓库默认 profile，该 profile 硬编码 `/data/service/hnp/bin/clang` 在本机不存在 ⇒ step3 必红，`all(self.steps.values())` 为假 ⇒ finish 返回非 0。**这是本机事实、不代表平台 worker**；W3（step35）与 L5 均为官方绿，`.ci-result.json` 正是官方工具在 W3 pass 分支写出的。本窗未为凑 finish rc=0 重跑任何一次构建。
- step3 那次红色 conan-verify **原地覆盖**了 `reports/conan-create.log`（现 7794 B / `9a25e123…`）与 `reports/conan-verify-report.md`（1450 B）；上一回合的绿色 create.log 载体（18597 B / `743a46df…`，rrev `3475dd5e…`）已按 root 口径在起建前存好逐字副本（`~/tmp/uc2/QDR-1009-E05/r29-pre/`），历史证据链未断。⇒ 本轮之后"库本体重编 + 消费者 76/0 + SONAME"三件的**在-site 官方载体是 `w3-local-ci.log`（`a53c19a8…`）**，不再引用被覆盖后的红 create.log。
- `ci-metadata.json`（790 B / `3d25d72b…`，gitignore）`test_report` 本轮为 `L0/L1/L4/L5 = pass`、`L2 = skip(no bin/ dir)`，无 L5 fail 项；但其 `source_trace.url` 仍是 Pre-download 期间的 `file://…/.build-cache/predl_cache/963d07ec_liblscp-1.0.1.tar.gz` 形态（`sha256` 仍是官方 `db54a33c…`）⇒ 该文件不入库，是否接受为 W3 侧现场载体交独立 W4 裁定。
- 措辞闸门继续适用：绿只能写成"私有影子 profile `ohos-aarch64-15461B`（2757 B / `67404bc1…`）输入下官方工具绿 ≠ 官方默认管线绿"。
- 本窗零 push / 零建 PR / 零提审 / 零 `/rebuild` / 零平台写 / 零 claim-lease-import / 未改框架文件 / 未动他人 worktree 与产物 / 未读未打印令牌 / 未新建 Cron-Goal-Agent / **不自审**（`pre_pr_audit.py report` 不由本窗执行；本轮只依官方生成器产出 `result.json`）。外层命令未用 `2>&1`。
- **下一步唯一动作**＝本窗一次精确提交使提交面稳定（此后本窗不再改面），交统筹排 CIA 或 CIB 在新 tip 上做**独立 W4（只读、零槽）**。W4 需一并裁定：①`ci-metadata.json` 的 `file://` `source_trace` 形态可否作为 W3 侧载体；②step3 默认 profile 红与 `FINISH_RC=2` 是否影响"官方 W3 载体有效"的判定；③E513 反悬置组三条可达路径与 `TEARDOWN_BUDGET_MS=5000` 上界的语义充分性（本轮未改代码）；④`L1c No upstream make check/ctest in log` 与 `upstream_total=0` 的同源性。

---

**编译结束**: 2026-10-15 20:25
**最终状态**: built
