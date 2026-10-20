# qmf 5.0-git20250326.d27f464 adaptation notes

- 上游：https://github.com/qt-labs/messagingframework，提交 d27f4646df066a6f5a8cc4b8761b710c26ea797c（Debian 快照 2025-03-26 所取的上游修订，提交时间 2025-03-03）。
- 源码包：`https://github.com/qt-labs/messagingframework/archive/d27f4646df066a6f5a8cc4b8761b710c26ea797c.tar.gz`，sha256 `f6508161a1dd19362dc19797ccfcc51f6d561c94416866aa88d8dbf7ce318db5`（本机实测下载 1388326 字节并校验）。
- 版本含义：`5.0` 为 Debian/Ubuntu 二进制包时代版本号，`git20250326` 为快照日期，`d27f464` 为上游短哈希；与 Debian `qmf_5.0~git20250326.d27f464.orig.tar.xz` 同源（内容为同一上游提交，Debian 仅做 `~` 转义与 debian/ 目录增补）。
- 适配路径：路径 A（基础适配）。

## 构建系统与依赖

- 构建系统：CMake（`cmake_minimum_required 3.16`，`project(... VERSION 4.0.4)`，`include(CTest)`，无 `BUILD_TESTING` 开关，`add_subdirectory(tests benchmarks examples)` 常开）。
- 关键 CMake 依赖：`Qt6 Core Xml DBus Sql Network Test Core5Compat`（REQUIRED），`LinguistTools` 可选，`pkg_check_modules(ICU icu-i18n)` 可选，`ZLIB` 可选，`ECM` 可选（缺失仅不生成 pkgconfig 文件）。
- 本配方依赖（均已在制品仓有目录，W0 由真机 `conan download --only-recipe` 复核）：
  - `qtbase-sql-dbus/6.11.1`（提供 Sql/DBus/Xml/Network/Core/Test；plain `qtbase/6.11.1` 的 `FEATURE_sql=OFF/FEATURE_dbus=OFF` 配不出 QMF，已按 E439 教训选用 sql-dbus 变体）
  - `qtcore5compat/6.11.1`（提供 `Qt6::Core5Compat`；E437：源码包名为 qt5compat，产物为 libQt6Core5Compat）
  - `icu/76.1`（启用 `HAVE_LIBICU` 字符集探测；缺失仅降级，不致命）
  - `zlib/1.3.1.1`（启用 IMAP COMPRESS；缺失仅告警，不致命）
- 配置：`BUILD_WIDGETS=OFF`（此时 `examples/` 为空，`src/libraries/qmfwidgets` 跳过），`USE_HTML_PARSER=OFF`（免除 `Qt6::Gui`），`CMAKE_PREFIX_PATH` 指向上述四个包，`Qt6_DIR`/`Qt6Core5Compat_DIR`/`CMAKE_MODULE_PATH` 显式指向包内 cmake 目录（qca/qtkeychain 同款）。
- 平台判断一律 `in ("Linux", "OHOS")`（R32）；`self.run` 内无 `${CC}` 裸变量（R33）；补丁为空（R8 无平台宏问题）。

## 上游测试盘点（与官方一致口径 ctest_entries）

- 来源：`tests/CMakeLists.txt`（该提交快照实测，共 29 行 `add_subdirectory(tst_*)` + 1 个条件 `tst_crypto`）。
- 官方总数：30（29 无条件 + 1 条件）。`upstream_test_total: 30`，`upstream_test_count_method: ctest_entries`。
- OHOS 可运行子集：29（`tst_crypto` 需 `gpgme-config`，OHOS 无 GPGME，不注册；属条件缺失，非跳过）。
- 无条件 29 项：tst_locks, tst_longstream, tst_longstring, tst_python_email, tst_qlogsystem, tst_qmail_listmodels, tst_qmail_sortkeys, tst_qmailaccountconfiguration, tst_qmailaddress, tst_qmailcodec, tst_qmaildisconnected, tst_qmaillog, tst_qmailmessage, tst_qmailmessagebody, tst_qmailmessageheader, tst_qmailmessagepart, tst_qmailmessageset, tst_qmailnamespace, tst_qmailserviceaction, tst_qmailstorageaction, tst_qmailstore, tst_qmailstorekeys, tst_qmailthread, tst_qmflist, tst_qprivateimplementation, tst_smtp, tst_pop, tst_imap, tst_storagemanager。
- 运行方式：`build()` 内 `ctest -N` 取 discovered（`Test #N:` 行数），`ctest --output-on-failure --timeout 300` 全量运行并逐行解析 `Test #N ... Passed/Failed/Timeout`；`QMF_DATA` 指向构建目录隔离 mailstore（上游 README 要求），`QT_QPA_PLATFORM=offscreen`，`HOME/XDG_*` 隔离。
- 标记：`HMBS_UPSTREAM_TEST_RESULT` 双通道输出并落盘 `build/hmbs_upstream.json`，`package()` 复制到 `res/hmbs_upstream.json` 供缓存命中轮重发（zydis 模式）。

## test_package（消费者视角）

- `test_qmf.cpp` 真实调用 `QmfClient` 公共 API：CHECK 1 构造 `QMailAddress("QMF Test", "qmf-test@example.com")` 并断言 `address()/isEmailAddress()`，CHECK 2 断言 `toString()` 回环携带邮箱；输出 `RESULT: 2 passed, 0 failed`，`test()` 正则解析该行后输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=2/passedCount=2）。
- `CMakeLists.txt` 用 `find_package(Qt6 Core)` + `find_package(qmf)`（CMakeDeps 生成 `qmf::qmf`），链接 `Qt6::Core qmf::qmf`；R34 合规（链接并调用被测库，非空壳）。
- 缓存命中轮重发包内 `res/hmbs_upstream.json`，保证每轮皆有上游证据。

## 真机预检期待（首轮未验证，待 HMBS 回填）

- `conan create archives/q/qmf/5.0-git20250326.d27f464 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` 应依次通过 L0（结构/依赖）、编译、`ctest 29/29`、`test_qmf 2/2`。
- 已知风险：DBus 会话总线缺失可能影响 `tst_qmailserviceaction/tst_qmailstorageaction`（需看真机日志；若失败则按 `test_failure` 记 gaps，不包装成 environment 豁免）；`tst_imap/tst_pop/tst_smtp` 为本地协议自测，无需外网。
- 本轮未执行 `git commit/push`，未调用 GitCode 写接口，未写 `.hmbs/pr.json`；工作树保持未提交，等待 HMBS 真机预检。

## 2026-10-18 QT_NO_SSL setter 去守卫补丁

- 真机现象：`src/plugins/messageservices/imap/imapprotocol.cpp:592` 报
  `no member named 'setMailAuthentication' in 'ImapConfigurationEditor'`，
  此时 QmfClient/QmfMessageServer 已编过（约 24%），说明 ICU/INTERFACE 旁路有效。
- 根因：OHOS 的 qtbase-sql-dbus/6.11.1 为无 SSL 变体（定义 `QT_NO_SSL`），
  而上游 imap/pop/smtp 的 `*configuration.h/.cpp` 把纯键值存取
  （`setMailEncryption/setMailAuthentication/setAcceptUntrustedCertificates`、
  smtp 的 `smtpUsername/smtpPassword` 存取与 `Auth_LOGIN/Auth_PLAIN` 枚举）
  包在 `#ifndef QT_NO_SSL` 内，调用方却无条件使用，被守卫掉后即编译失败。
- 修复：配方 `build()` 新增 `_patch_qt_no_ssl_config()`，对上述 6 个纯配置
  文件做锚定字符串去守卫（只删 `QT_NO_SSL` 的 `#ifndef/#endif` 行，
  遇 `#else` 或失衡直接抛错；含 `QSsl` 则拒绝），传输层 SSL 守卫保持不动。
- 与前轮区别：前轮修的是 ICU 导入目标类型（UNKNOWN→INTERFACE，已生效）；
  本轮是新失败域（IMAP 插件），不沿用 ICU 路径排序/影子 `.pc` 手段。

## 2026-10-18 小内存 OOM 缓解（tar Cannot fork）

- 真机现象：编译期 `tar (child): child process: Cannot fork: Out of memory`，上游测试 0/0/0。QMF 源码包仅约 1.4MB，解包自身不可能耗尽内存；指纹与 kyua 第二十六轮、kanzi-cpp 注释的整机 RAM 耗尽同族（Qt 重型 TU 在高优化+调试信息+多并发下峰值 RSS 占满内存，tar fork 成为最先倒下的旁观者）。
- 修复（仅本库配方，测试口径不动）：`generate()` 按构建类型封顶追加优化/调试标志（Release -O1 -g0、RelWithDebInfo -O1 -g1、MinSizeRel -Os -g0、Debug -O0 -g1，libpuzzle 前例；靠后追加覆盖 profile 的 -O2/-O3/-g，不改 NDEBUG）；构建域环境追加 CFLAGS/CXXFLAGS 并定义 MAKEFLAGS=-j1；`build()` 内对生成的 conan_toolchain.cmake 做幂等尾部追加（kanzi-cpp 前例，防编译器修复重写丢失标志）；OHOS 下 `cmake.build/install` 显式 `--parallel 1` / `-j1`（显式封顶，不依赖 profile 的 jobs 注入）。
- 证伪分支：① 日志出现 `HMBS diag OOM flags` 且越过编译进入 ctest → 本次生效，看 29 用例实测数；② 同一 tar fork OOM 复现 → 耗内存的另有其人（多半为整机环境问题），下轮如实上报环境故障停留；③ 日志无该行 → 本次未同步，查 HMBS 同步版本。

## 2026-10-18 tst_smtp Encrypt_SSL 编译修复

- 真机现象：tests/tst_smtp/tst_smtp.cpp:114 报 no member named Encrypt_SSL in QMailTransport（87%% 处，前序库/插件已编过）。同文件另有 setSmtpAuthentication(PlainMechanism) 可编（QMail 枚举未守卫、setter 已去守卫），故唯一定位到 qmailtransport.h 的 EncryptType 枚举守卫。
- 根因：OHOS 的 qtbase-sql-dbus/6.11.1 为无 SSL 变体（QT_NO_SSL），qmailtransport.h 把纯整数 Encrypt_SSL/TLS 包在 ifndef QT_NO_SSL 内；tst_imap/tst_pop/tst_smtp 三个测试无条件引用 QMailTransport::Encrypt_SSL。
- 修复：配方新增 _patch_transport_encrypt_enum，仅对该枚举块做锚定去守卫（Encrypt_SSL=1/TLS=2 常驻；QSsl 头、前置声明、switchToEncrypted、sslErrorOccured、encryption 成员等其余 7 处守卫原样保留，补丁内校验计数非零）。安全依据：qmailtransport.cpp 在 QT_NO_SSL 下已对任意 EncryptType 做 Q_UNUSED/mailEncryption()->NONE/明文 connectToHost 降级，客户端 TLS 分支仍被各自守卫编译掉，测试断言零改动。
- 与前轮区别：前轮去守卫的是 6 个纯配置存取文件；本轮是传输层枚举新失败域，不碰测试语义、不跳过用例。

## 2026-10-18 benchmark M_MMAP_MAX 编译修复

- 真机现象：前轮 Encrypt_SSL 修复生效（构建由 87%% 推进到 98%%），新失败在 benchmarks/tst_messageserver/testmalloc.cpp:180 报 use of undeclared identifier M_MMAP_MAX，上游测试仍 0/0/0。
- 根因：testmalloc.cpp 无条件调用 mallopt(M_MMAP_MAX, 0)（glibc <malloc.h> 常量），OHOS libc 头缺该常量；该调优仅关闭 mmap 使基准堆块开销固定，缺失时跳过不影响基准可编可跑。与前轮不同域（前轮是 Qt SSL 变体枚举），故采用新策略：常量级 ifdef 守卫而非枚举去守卫。
- 修复：配方新增 _patch_benchmark_glibc_mallopt，对该调用做锚定 #ifdef M_MMAP_MAX 守卫（glibc 行为不变；TEST_TESTMALLOC 块未启用未动；operator delete 警告仅警告不致命）。benchmark 非 ctest 计数口径（upstream_test_total=30 仅 tests/），不改测试口径。

## 2026-10-18 benchmark __libc_* 链接修复（禁用 benchmarks on OHOS）

- 真机现象：M_MMAP_MAX 守卫生效后构建推进到 99%，新失败在 benchmarks/tst_messageserver 链接期：`ld.lld: error: undefined symbol: __libc_malloc/__libc_free/__libc_calloc/__libc_realloc/__libc_memalign`（testmalloc.cpp.o 引用），`clang-15: link failed`，上游测试仍 0/0/0。
- 根因：benchmarks/tst_messageserver/testmalloc.cpp 本质 glibc-only：`extern "C" __libc_malloc/calloc/realloc/memalign/free` 私有符号 + mallinfo/mallopt/malloc_usable_size + 全局 malloc/free/new/delete 重载做堆测量；OHOS libc 无这些 __libc_* 符号，无法链接。与前轮 M_MMAP_MAX 常量缺失同文件不同层（前轮是单个常量，本轮是整套分配器拦截架构），ifdef 无法挽救。
- 修复：配方新增 `_patch_disable_benchmarks_on_ohos()`，对顶层 CMakeLists 的 `add_subdirectory(benchmarks)` 做锚定替换为 `if(NOT CMAKE_SYSTEM_NAME STREQUAL "OHOS")` 守卫；Linux 行为不变。benchmarks/ 仅含 tst_messageserver（已实证 benchmarks/CMakeLists.txt 仅此一项），tests/（ctest 29/30 口径）与 examples/（BUILD_WIDGETS=OFF 时为空）不动，上游测试口径不变。前轮 mallopt 守卫保留（Linux 基准仍可用）。
- 证伪：若下轮日志出现 `benchmark_fix: benchmarks skipped on OHOS` 且越过 99% 进入 ctest → 生效；若仍链接 tst_messageserver → 补丁未同步，查 HMBS 同步版本。

## 2026-10-18 benchmark 禁用策略切换（配方侧硬删除）

- 真机现象：上一轮 CMake-time 守卫（`if(NOT CMAKE_SYSTEM_NAME STREQUAL "OHOS")`）已推送但预检仍在 99% 链接 tst_messageserver（`__libc_malloc` 等 5 符号未定义），说明守卫条件在真机工具链下恒为真（CMAKE_SYSTEM_NAME 实际值非 OHOS，conan/OHOS-SDK 工具链行为），属于同指纹第 2 次修复，必须换策略。
- 新策略：配方侧按 `self.settings.os == "OHOS"` 在 source 时直接删除 `add_subdirectory(benchmarks)`（替换为注释行），Linux 原样保留；不再依赖 CMAKE_SYSTEM_NAME 取值。幂等标记为 `benchmarks disabled on OHOS`，并兼容替换上一轮旧守卫块。tests/ 口径（30/29）与 examples/ 均不动。
- 证伪：下轮日志应出现 `benchmark_fix: benchmarks removed for OS=OHOS` 且构建不再进入 `benchmarks/tst_messageserver` 目录；若仍进入则为同步问题，如实上报。

## 2026-10-18 ctest ***Failed 解析修复（executed 0/30）

- 真机现象：benchmark 硬删除生效后构建越过 99% 进入 ctest，但标记为 discovered=30、executed=0、passed=0、failed=0、skipped=30，detail 为空（"see ctest_upstream.log"），直接抛 ConanException。
- 根因：配方 `build()` 的 ctest 日志正则 `\\.*\\s+(Passed|Failed|Timeout)` 要求状态词前为空白，而 CTest 失败行实际渲染为 `Test #N: name ...***Failed`（星号紧贴 Failed，无空白），通过行才是 `   Passed`。30 个用例若含失败则一个都计不上，executed 恒为 0，failed_names 为空，恒等式 passed+failed==executed 空转。这是纯 harness 解析缺陷，非上游测试语义问题。
- 修复：解析改为 `re.search(r"Test\\s+#\\d+:\\s+(\\S+).*?\\b(Passed|Failed|Timeout)\\b")`，以词边界匹配状态词，同时兼容 `   Passed` 与 `***Failed`/`***Timeout`；汇总行 `N tests passed` 为小写且无 `Test #`，不会误命中。数据源仍唯一（build/ctest_upstream.log 的 Test #N 行），恒等式与 gaps 口径不动。本轮未改任何测试断言与跳过逻辑。
- 证伪：下轮日志应出现 `executed>0` 且 failed_names 非空（或全通过）；若仍 executed=0 则为同步问题或日志格式另有变体，需拉取 ctest_upstream.log 尾部再定位。

## 2026-10-18 源码下载超时镜像回退

- 真机现象：`source()` 在下载 `https://github.com/qt-labs/messagingframework/archive/d27f464...tar.gz` 时两次超时（ReadTimeout/ConnectTimeout，重试 5 秒后仍失败），conan create 在 Export 后直接 ERROR，无编译输出。
- 根因：GitHub 直连在真机网络下不可达，非配方逻辑问题；`conandata.yml` 仅有单一直连 URL，无镜像回退。
- 修复：`conandata.yml` 的 `url` 改为有序列表，首项为 `ci/conan/build_and_test.sh` 维护的 GitHub 镜像映射 `https://gh-proxy.com/https://github.com/...`，末项保留官方原始 URL 回退；`sha256` 不变（镜像提供完全相同归档，继续用原值校验）。`source()` 的 `get(self, **self.conan_data["sources"])` 原生支持 URL 列表逐个尝试，无需改配方。

## 2026-10-18 ctest 零执行诊断加固（executed 0/30）

- 真机现象：benchmark 硬删除后构建越过 99% 进入 ctest，但本轮仍为 discovered=30、executed=0、failed=0、skipped=30，detail 为空（见 ctest_upstream.log）。此时已有 ***Failed 词边界解析修复，仍零匹配，说明不是旧正则问题，而是日志无 Test #N 行（ctest 未找到、日志为空、或输出为 Not Run/Skipped 变体）。
- 根因：harness 只有单一数据源（ctest_upstream.log 的 Test #N 行），无日志存在性校验、无头尾转储、无第二数据源；ctest 用裸 PATH 调用，若真机 PATH 未含 ctest 或重定向未落盘，则静默产出 executed=0。
- 修复（只改 harness，不改测试语义）：ctest 改为绝对路径解析（HMBS_CMAKE 同目录 sibling 优先，shutil.which 回退，并打印 HMBS diag ctest exe）；运行后校验日志大小并打印头 20 行/尾 60 行；空日志时列出 Testing/Temporary 目录；解析扩展 Not Run/Skipped/Disabled（计入 notreun，属 skipped，不伪造 passed）；executed 仍为 0 时回退解析 Testing/Temporary/LastTest.log（确定性第二源，非字符串数数）；gaps detail/evidence 改为真实尾部摘录与搜索路径，不再用空泛 see log。恒等式与口径不变。
- 证伪：下轮日志应出现 HMBS diag ctest exe、ctest log size、ctest head/tail 行；若 size=-1 则为落盘失败，若有 Not Run 行则为用例未跑而非解析漏，若 LastTest.log 恢复计数则为重定向问题。

## 2026-10-18 No tests were found 根因修复（换策略第2次）

- 真机现象：上轮诊断加固生效，日志首次吐出真相：ctest_upstream.log 仅 142 字节，内容为 Test project .../b/build/Release + No tests were found!!!。discovered=30 来自配方对 tests/CMakeLists.txt 的 add_subdirectory 字符串计数回退，并非真实注册数；真实注册数为 0。
- 根因（与上轮解析假设不同域）：一是 CTest 仅在 BUILD_TESTING=ON 时 enable_testing，配方未显式打开，套件可能根本未注册；二是 ctest 固定跑在 self.build_folder（build/Release 配置子目录），而顶层 CTestTestfile.cmake 可能位于 base build 目录，目录假设错误即 No tests found。上轮只修了解析，本轮换策略修注册与目录。
- 修复：generate() 新增 tc.variables[BUILD_TESTING]=ON（官方开关，不改测试语义）；build() 新增 CTest 工作目录探测（build_folder、父目录、子目录 walk 找 CTestTestfile.cmake，选 subdirs 最多的为顶层并打印 head）；ctest -N 与 ctest 运行均改到该目录，日志镜像回 build_folder；删除 add_subdirectory 字符串计数回退（虚假 discovered），零注册时如实报 discovered=0 并附搜索目录；LastTest.log 回退与 Testing 列表同步改到该目录。
- 证伪：下轮日志应出现 HMBS diag ctest dir、CTestTestfile head、ctest -N head；若 discovered 回到 29（tst_crypto 缺 GPGME 未注册）并进入执行，则本策略生效；若仍为 0，则看 CTestTestfile head 与候选列表定位配置原因。

## 2026-10-18 上游零add_test根因修复（换策略第3次）

- 真机现象：上轮 BUILD_TESTING=ON 与目录探测均生效，但 ctest 仍 No tests were found（discovered=0），而 stderr 明确显示 tst_qmailstorageaction 等测试目标已编译。注册与目录假设双双证伪。
- 根因（新域）：抽查上游 tests/tst_qmailaddress、tst_qmailstore、tst_python_email、tst_storagemanager 的 CMakeLists.txt，全部只有 add_executable+install，没有任何 add_test() 调用。上游 include(CTest) 只是引入模块，从未注册用例，ctest 章程性零注册；29 个二进制就是全部上游测试交付物。
- 修复（只加 harness，不改断言）：配方新增 _patch_register_qmf_tests()，从 tests/CMakeLists.txt 动态解析 29 个无条件 tst_* 名（排除条件性的 tst_crypto），逐项校验子目录确有同名 add_executable 后，在顶层追加 add_test(NAME/COMMAND/WORKING_DIRECTORY=tests/<名> 源码目录，照顾 tst_python_email 的 testdata 就近读取；HOME/QMF_DATA 隔离不变）。幂等标记，缺失目标直接抛错不静默。gaps 新增条件性 tst_crypto 的 environment 缺口（gpgme-config 缺席，与无 GPGME 的上游行为一致），使 gaps 合计恒等于 30-通过数。
- 证伪：下轮应出现 qmf_testreg: registered 29 tests 且 ctest -N 发现 29；若仍为 0 则看配置错误行；各用例真实 QtTest 结果以 ctest_upstream.log 与 LastTest.log 为准。

## 2026-10-18 loader 路径与失败摘录（第 3 次换策略：加载域）

- 真机现象：插件暂存后仍 17/29、12 失败（sortkeys/store 系列 + smtp/pop/imap +
  storagemanager SEGV），且预检摘要未见 `qmf_plugin_stage` 行。
- 新策略（与前两轮不同域）：① 暂存匹配放宽到大小写不敏感、含/不含 lib 前缀、
  版本化 `.so.*`（防漏检）；② 新增 loader 路径闭环——`_stage` 同步收集插件
  源目录与 `libQmfClient/MessageServer` 所在目录到 `self._qmf_extra_ld`，
  `_runtime_env` 自动前置到 `LD_LIBRARY_PATH`（插件 `dlopen` 解析符号需要，
  仅 `QT_PLUGIN_PATH` 不够）；③ 测试 harness 只增证据不改口径——从
  `ctest_upstream.log` 确定性摘录 `FAIL!/Compared values/QVERIFY` 等行到
  `HMBS diag qtest failures`，供下轮定位 sortkeys/store 真实断言。
- 证伪：下轮应见 `qmf_plugin_stage: staged` + `ld dirs=` + `HMBS diag qtest failures`
  行；若插件仍 0，则为构建产物命名另有变体，需看 stage 警告。

## 2026-10-18 QMF 插件暂存修复（第 2 次换策略：发现域）

- 真机现象：locks QMutex 分支生效后（不再 SIGSYS），仍 17/29 通过、12 失败，
  含 tst_storagemanager 在 test_init SIGSEGV（地址 0），日志伴随
  `Unable to create content manager for scheme: ""`。
- 根因（与前轮 IPC/ locks 域不同）：`QMailPluginManager("contentmanagers")`
  只扫描 `QCoreApplication::libraryPaths()/messagingframework/<subdir>/*.so*`
  （见 `support/qmailpluginmanager.cpp`）。`conan create` 在 build 树跑 ctest
 （install 之前），`libqmfstoragemanager/libimap/libpop/libsmtp` 尚在散装
  build 目录，无 `messagingframework/<subdir>` 布局，故 `contentPlugins()` 为空、
  `defaultScheme()==""`、`create("")` 返回空指针，`test_init` 解引用崩溃；
  其余 QMailStore-content 用例同因失败。前轮只修了锁，未修发现路径。
- 修复（只改 harness，不改测试语义）：`build()` 在 `cmake.build` 后、`ctest` 前
  新增 `_stage_qmf_plugins()`——遍历 build（含父目录）搜上述 4 个 MODULE 产物，
  拷贝到 `build/qmf-test-plugins/messagingframework/contentmanagers|messageservices/`，
  `_runtime_env()` 自动前置该根到 `QT_PLUGIN_PATH`；另加 best-effort
  `_ensure_dbus_session()`（有 dbus-daemon 则起私会话总线，无则警告继续，
  不致命，因 store/content 不依赖它）。
- 与聚合经验 #1 的区别：该经验处理“自动探测的可选编码依赖”（补依赖+工具路径），
  本轮是“构建树插件布局不可见”（补 QT_PLUGIN_PATH 暂存），不沿用其路线。
- 证伪：下轮应出现 `qmf_plugin_stage: staged ... files` 且
  `tst_storagemanager` 不再 SIGSEGV；若仍空插件则看 `qmf_plugin_stage: no ... found`
  与 ctest 日志的 `No content manager plugins found` 行。剩余 smtp/pop/imap
  `test_connection` 若仍失败，属外部服务器+SSL-less（QT_NO_SSL）环境限制，
  下轮单独归因，不在本轮改断言。

## 2026-10-18 QSystemSemaphore SIGSYS 根因修复（换策略第4次：IPC 域）

- 真机现象：注册补丁生效后 discovered=29、14 通过，15 个用例全部以 `SIGSYS***Exception` 崩溃（0.15~0.17 秒，initTestCase 内，伴随 D-Bus 连接失败告警）。同时 harness 计数自相矛盾：ctest 汇总 `48% tests passed, 15 tests failed out of 29`，标记却报 executed=14/failed=0/skipped=15。
- 根因（新域，前三轮的注册/目录/解析假设之外）：`src/libraries/qmfclient/locks.cpp` 的 ProcessMutex（每个 QMailStore DB 操作经 qmailstore_p.cpp 的 MutexGuard 加锁）实现为 `QSystemSemaphore`，即 SysV `semget/semop`（经 ftok 键）。HongMeng 内核无 SysV IPC 系统调用，直接以 SIGSYS（signal 31，E051：不可捕获）杀进程。证据链：① 崩溃的 15 个恰为全部触及 QMailStore 的用例（store/account/message/service/smtp/pop/imap/storagemanager），通过的 14 个恰为纯值/编解码/日志用例（address/codec/messagebody/header/part/namespace/qmflist/locks 本身只测 AccountKey）；② D-Bus 告警只是 QCRITICAL 继续执行，非崩溃点；③ 前轮 ICU/SSL/benchmark 修的是编译期不同域。
- 修复（换实现路线，不碰测试语义）：配方新增 `_patch_locks_qmutex_on_ohos()`，OHOS 下把 locks.cpp 的 QSystemSemaphore 分支整体包进 `#else`，新增 `#ifdef QMF_USE_QMUTEX_LOCKS` 分支——按 key 共享的进程内 QMutex 注册表（调用方每次构造全新 ProcessMutex 故必须按 key 共享，永不销毁，与上游"no-one will close"语义对齐；SQLite 自身文件锁仍在底层保 DB 完整；ctest 串行故单进程测试被完全串行化）。`generate()` 仅当 `settings.os == OHOS` 时定义该中性特征宏（Linux 保持上游 SysV 原路径）；源码中无 `__OHOS__` 平台宏（PF5 合规，平台判断只在配方 Python 侧）。附带 harness 诚实化：ctest 解析与 LastTest.log 回退同时识别 `Exception/Abort/Crash` 为失败（此前 SIGSYS 行无 Failed 字样被静默丢弃，导致 executed=14/failed=0 的矛盾计数）。
- 与聚合经验 #1 的区别：该经验处理的是"自动探测的可选编码依赖"（补依赖+工具路径），本轮是"内核直接缺失的 IPC 系统调用"，补依赖无法解决（semget 不是缺包，是内核拒绝），故不沿用其路线。
- 证伪：下轮日志应出现 `locks_fix: locks.cpp QMutex-registry branch added` 与 `qmf_locks_fix: QMF_USE_QMUTEX_LOCKS defined for OHOS`，且 15 个原 SIGSYS 用例进入真实 QtTest 断言（通过或给出断言级失败行，而非 signal 行）；若仍全 SIGSYS 则为补丁未同步或另有第二崩溃点，需看 ctest tail 与 LastTest.log 定位。已知后续风险：tst_smtp/tst_imap/tst_pop 的 test_connection 需真实外网服务器（smtp.free.fr/imap.free.fr），隔离真机上可能转为断言失败，届时按 environment 逐项举证，不伪造通过。

## 2026-10-18 插件暂存路径纠偏（裸 PLUGIN_KEY）

- 真机现象：前两轮暂存+loader闭环后仍 17/29、12 失败（store/content 系列 updateMessage FALSE + storagemanager SEGV），且路径假设从未被证伪。
- 根因（新域，非IPC/发现域复述）：qmailcontentmanager.cpp 的 PLUGIN_KEY 为裸串 contentmanagers（messageservices 同理），QMailPluginManager 只扫描 libraryPaths/<PLUGIN_KEY>/*.so*；配方却暂存到 messagingframework/<subdir>/，正确目录始终为空，故 contentPlugins() 为空、defaultScheme() 为空串、updateMessage FALSE、storagemanager 空指针崩溃。证据：qmailcontentmanager.cpp PLUGIN_KEY 定义；install 目的地亦为 qt5/plugins/contentmanagers。
- 修复：_stage 改为双布局——主写 <root>/<subdir>（裸键正确路径）并镜像到 legacy <root>/messagingframework/<subdir>；_runtime_env 改判裸键目录存在即前置 QT_PLUGIN_PATH；build() 新增 HMBS diag plugin tree 转储供下轮验证。测试断言零改动。
- 证伪：下轮应见 qmf_plugin_stage 行 + plugin tree 含 contentmanagers/qmfstoragemanager 与 messageservices/imap|pop|smtp，且 Unable to create content manager 行消失；若仍空则看 stage 警告与 tree。

## 2026-10-18 messageserver拉起与网络分组（第2指纹新策略）

- 真机现象：裸键双布局生效后 24/29，仅剩 5 失败：storageaction init断言isMessageServerRunning FALSE、qmailstore updateMessages QCOMPARE mismatch、smtp completed.wait FALSE、pop/imap updateStatus 2 vs 3。
- 与上轮区别：上轮修插件发现路径（布局域），本轮换到服务生命周期+外部网络域，不再改暂存逻辑。
- 修复：新增_best-effort _ensure_messageserver（构建树搜daemon并后台拉起供isMessageServerRunning）；新增_probe_mail_network对free.fr三端口DNS/TCP短超时探测供gaps证据；qtest摘录补Loc行精确定位qmailstore；gaps拆分smtp/pop/imap为environment、其余为test_failure，总和仍=30-通过数。测试断言零改动。
- 证伪：下轮应见messageserver started/plugin tree/net probe行；storageaction若仍FALSE则看daemon二进制名或D-Bus注册；qmailstore看Loc行；网络三项看probe的dns/tcp结果。

## 2026-10-18 messageserver候选放宽与qmailstore精确定位（第3指纹新策略诊断精度）

- 真机现象：上轮分组生效（2 test_failure+3 environment+1 crypto=6=30-24），但storageaction仍isMessageServerRunning FALSE、qmailstore updateMessages仍QCOMPARE mismatch且Loc被摘要截断；上轮后台拉起与分组未改变二者，属同指纹第3次，必须换诊断精度策略而非重复拉起命令。
- 与前次区别：前次是拉起+分组；本轮不改布局与分组，仅放宽daemon候选（message+server子串+ELF判定替代精确名+可执行位），去poll门控改日志增长报告，并新增qmailstore updateMessages FAIL后9行专用摘录。
- 证伪：下轮应见messageserver candidates/started/poll/logsize行与qmailstore context行；若候选为none则二进制名另有变体，若context给出Actual/Expected则下轮可定点修body比对。

## 2026-10-19 messageserver误选.so根因修复与三态门禁（第4指纹新策略）

- 真机现象：上轮放宽后仍24/29，storageaction仍isMessageServerRunning FALSE，qmailstore仍QCOMPARE mismatch。
- 根因（代码审查新域）：_ensure_messageserver的候选条件含`or _fl.endswith((".exe", ""))`，空后缀恒为True，故所有含message+server的文件（含libQmfMessageServer.so等共享库与CMake中间文件）全部入选；再按路径最短排序，选中的是.so而非真正的daemon可执行文件，后台拉起的实际是共享库，messageserver从未真正运行。本轮改为精确策略：basename必须含messageserver且不以lib开头，排除.so/.a/.o/.cmake等产物后缀与.so.版本符号，保留ELF/可执行判定；排序优先精确名messageserver，再按路径长度。
- 三态门禁（lcm/zerolang先例）：仅真实test_failure阻断打包；纯环境失败（smtp/pop/imap需直连smtp/pop/imap.free.fr外网，预检worker不可达）转为status incomplete带gaps放行，不再抛错；含真实失败时仍按failed抛错。测试断言零改动。
- 证伪：下轮应见`qmf_messageserver: candidate ... (from N)`且N为小数字（1-3），`poll=... logsize=... after 5s`且logsize>0；若storageaction仍FALSE则看messageserver.log head是否给出D-Bus注册失败；若仅剩3网络失败则状态应为incomplete且打包继续。

## 2026-10-19 messageserver5真名与D-Bus会话修复（第5指纹新策略：命名+IPC域）

- 真机现象：上轮窄化候选后仍24/29，storageaction仍isMessageServerRunning FALSE，qmailstore仍updateMessages QCOMPARE mismatch；且每轮ctest初始化均报Failed to connect D-Bus。
- 根因（新域，前轮只修候选宽窄未修真名与总线）：① 上游CMake真名是messageserver5（src/tools/messageserver/CMakeLists.txt add_executable(messageserver5)），裸messageserver从不存在，排序键把messageserver5当非精确名，若有杂项候选即可能误选；② QMail::isMessageServerRunning()=sessionBus.isConnected && isServiceRegistered(org.qt.messageserver)，MessageServer::init()内registerObject+registerService失败即return false，而预检无会话总线（dbus-daemon不在PATH），daemon起后即退出，测试侧恒FALSE。qmailstore的Actual/Expected被摘要截断，需加宽摘录下轮定位。
- 修复：build_requirements新增tool_requires dbus/1.14.10.3（published，可提供dbus-daemon）；_ensure_dbus_session除PATH外再扫conan dbus包bin/dbus-daemon；排序键把messageserver5(.exe)视为精确名；启动后校验日志含Registered messageserver to D-Bus/Failed to register/Failed to initialize并分别打diag；摘录单行400→600并纳入Actual/Expected行，qmailstore上下文9→15行。测试断言零改动。
- 证伪：下轮应见qmf_dbus: found daemon/session bus started、qmf_messageserver: candidate ...messageserver5...、D-Bus registration confirmed、qtest failures含Actual/Expected；若仍FALSE则看messageserver.log head与dbus地址是否透传到ctest env。

## 2026-10-19 可写TMPDIR透传与证据内嵌（第2指纹新策略：文件系统域+证据域）

- 真机现象：上轮供给dbus/1.14.10.3后仍24/29、5失败不变，每轮仍Failed to connect D-Bus；同指纹第2次，必须换策略，不得原样重复供给daemon。
- 与前次区别：前次是供给会话总线（依赖域）；本轮换到文件系统域+证据域——① ctest运行环境此前丢弃可写TMPDIR，回落到可能只读的/tmp，QMailStore消息体文件重写（updateMessages改10个subject+body）最先受影响；② 前轮加宽的日志摘录被聚焦摘要截断，Actual/Expected与dbus/ms状态无法回传，改把关键证据内嵌进 gaps.evidence 与最终异常信息（摘要必保留）。
- 修复：_runtime_env新增可写TMPDIR探测透传（TMPDIR/TMP/TEMP/GOTMPDIR）并定义XDG_RUNTIME_DIR；_ensure_dbus/_ensure_messageserver/qmailstore上下文改记self._qmf_*状态；gaps.test_failure的evidence携带exe/dir/dbus/ms/TMPDIR/store/fails首行，最终ConanException同步携带dbus/ms/store。测试断言零改动，保留dbus依赖不断链。
- 证伪：下轮原因行应含dbus=/ms=/store=字段；若TMPDIR行显示qmf_tmp: ctest TMPDIR=某可写目录且qmailstore仍失败，则看store=内Actual/Expected定点；若dbus仍no-daemon/fork-fail，则证明OHOS worker上会话总线不可用，需下轮单独归因storageaction的D-Bus依赖。

## 2026-10-19 fork-OOM 第三轮新策略（pipe+分阶段，非 flag 封顶复述）

- 真机现象：-O0 -g0 + --parallel 1 + 工具链尾部追加已生效，仍在编译期报 `/bin/sh: Out of memory`（上游测试 0/0/0）。同指纹第 2 次修复，不得复述 -O/-g/-j 封顶，必须换轴。
- 根因判断：存量手段只压了“优化器峰值”与“并发数”，而 fork 失败（非 cc1plus 内部 OOM）指向整机内存耗尽的旁观者崩溃；-j1 下仍倒，说明单 TU 的编译期管道与链接页缓存叠加即超限，需削“单作业常驻内存”而非继续降 -O（已到底）。
- 修复（仅本库配方，测试口径不动）：① generate() 在 -O0 -g0 后追加 -no-pipe（编译阶段间走磁盘临时文件而非内存管道，TMPDIR 已是验证过的可写目录；行为中性）；工具链尾部追加与 CFLAGS/CXXFLAGS 构建域同步；② generate() 新增 CMAKE_UNITY_BUILD=OFF + CMAKE_DISABLE_PRECOMPILE_HEADERS=ON，禁 TU 归并/PCH 膨胀（QMF 全局 CMAKE_AUTOMOC=ON，mocs_compilation.cpp 为疑似峰值源）；③ build() OHOS 下改分阶段串行：先逐 target 编 QmfClient → QmfMessageServer → messageserver5（已对上游 CMakeLists 核对真名），再全量收尾补插件与 29 测试；单 target 失败只告警并由全量构建如实报错，不静默放行。
- 与经验区别：经验 1/2 均为 -O/-g 封顶+单作业（前轮已用尽，adapt 保留不回归）；聚合 #1 为编码依赖探测（ICU/pkgconf 已闭环，reject）；DRAFT 两条（test 产物污染 / tarball 子模块）与 fork-OOM 无关，不适用。
- 证伪：下轮日志应出现 `HMBS diag OOM flags: -O0 -g0 -no-pipe` 与分阶段构建行；若仍同错则为整机内存环境问题，需如实上报停留。


## 2026-10-19 package() absolute install path redirect
- Symptom: build 100% ok, ctest 26/29, then package() fails:
  cmake_install.cmake file INSTALL "cannot create directory: /opt/tests/qmf"
  (tests/tst_locks install, needs admin privilege).
- Root cause: upstream tests/*/CMakeLists use absolute
  DESTINATION /opt/tests/qmf, which bypasses CMAKE_INSTALL_PREFIX, so
  conan cmake.install() (prefix=package folder) still tries /opt.
- Fix: new _patch_test_install_destinations() in build(), called after
  _patch_register_qmf_tests(): rewrites /opt/tests/qmf -> tests/qmf and
  /opt/tests -> tests (package-relative) in tests/**/CMakeLists.txt.
  Idempotent; warns if no absolute destination found. Library/plugin
  destinations untouched; ctest runs from build tree, execution unchanged.
- Verify: python -m py_compile conanfile.py OK; awaiting HMBS preflight
  (cmake.install should proceed past tests/tst_locks).

## 2026-10-19 test_package compiler check redirect (stale profile path)
- Symptom: main package builds 100%, ctest 26/29 incomplete(environment-only),
  package() now succeeds ("Package built"), but test_package dies in
  cmake.configure() at project(): "The CMAKE_CXX_COMPILER:
  /data/service/hnp/bin/clang++ ... is not able to compile a simple test
  program" (with the "System is unknown to cmake / Platform/HarmonyOS" warning).
- Comparison with previous round: last round fixed package() absolute
  DESTINATION /opt/tests/qmf -> verified effective this round (package built).
  This failure is a new stage/domain (test_package toolchain), not a repeat,
  so a different route is required instead of re-editing install destinations.
- Root cause: ohos-aarch64 profile pins tools.build:compiler_executables to
  /data/service/hnp/bin/clang(++), missing on this preflight worker, while
  CMakeToolchain bakes the stale path into test_package's conan_toolchain.cmake.
  Evidence: main build log prints "HMBS diag fixed generated toolchain
  conan_toolchain.cmake" (the main recipe's _resolve_compiler/_fix_generated_
  toolchain_compiler rewrote the stale path, which is why the main build
  passed); test_package had no such workaround. Same fingerprint as
  bzrtp/5.3.105 notes (profile path missing on some workers).
- Fix (test_package only, no test semantics change): mirror the bzrtp
  convention -- generate() resolves conf -> PATH via _compiler_executable()
  and forces CMAKE_C/CXX_COMPILER cache variables on OHOS, plus a
  post-generate toolchain rewrite of the stale /data/service/hnp/bin paths.
  Linux behavior untouched. R33 compliant (conf/shutil.which, no bare env).
- DRAFT knowledge checked and rejected: [1] EAGAIN try-compile needs
  "Resource temporarily unavailable"+cmTC+Error 127 signature, absent here;
  failure is deterministic stale-path (same /data/service/hnp path + main
  build rewrite evidence). [2] conandata single-element mirror-skip: our
  conandata.yml is already a 2-entry list (gh-proxy first, official fallback)
  and source() downloaded fine -- not applicable.
- Verify: python -m py_compile on both conanfiles OK; awaiting HMBS preflight
  (test_package configure should pass compiler check and run ./test_qmf).

## 2026-10-19 test_package find_dependency(qtbase-sql-dbus) redirect
- Symptom: compiler check now passes (previous round's fix verified), but
  test_package cmake.configure() dies at CMakeLists.txt:9 find_package(qmf):
  qmf-config.cmake runs find_dependency(qtbase-sql-dbus) and CMake reports
  'By not providing Findqtbase-sql-dbus.cmake ... but CMake did not find one'.
- Comparison with previous round: last round fixed the stale profile compiler
  path in test_package (verified effective: project()/pthread checks now pass).
  This failure is the NEXT stage in the same configure (dependency resolution),
  not a repeat, so a different route is required.
- Root cause: qmf requires qtbase-sql-dbus/qtcore5compat publicly, so CMakeDeps
  emits find_dependency(<ref-name>) in qmf-config.cmake; but BOTH Qt providers
  set cmake_find_mode=none (Qt ships its own Qt6/Qt6Core5Compat configs, same
  reason as qtbase's own test_package comment), so no such config file is ever
  generated. Evidence: icu/ZLIB find_dependency lines succeeded in the same log
  (their files are generated); only the find_mode=none Qt edges are dangling.
  Upstream QMF installs no *Config.cmake (verified top CMakeLists from GitHub:
  no install(EXPORT)), so qtkeychain's find_mode=none+upstream-config pattern
  is not applicable here; generated qmf::qmf must stay.
- Fix (test_package only, maeparser consumer-side precedent, no test/prod
  semantic change): generate() sets cmake_file_name Qt6/Qt6Core5Compat on the
  two dep cpp_infos before CMakeDeps runs, adds Qt6Core5Compat_DIR cache var
  (mirrors main recipe), and CMakeLists finds Qt6 + Qt6Core5Compat BEFORE qmf
  so the redirected find_dependency calls are no-op re-finds.
- DRAFT knowledge rejected: [1] EAGAIN try-compile needs Resource temporarily
  unavailable/cmTC/Error 127 signature -- absent (compiler check passed);
  [2] conan-init single-element mirror-skip -- our conandata.yml is already a
  2-entry list and source() downloaded fine.
- Verify: python -m py_compile on both conanfiles OK; awaiting HMBS preflight
  (configure should pass find_package(qmf) and build ./test_qmf).
