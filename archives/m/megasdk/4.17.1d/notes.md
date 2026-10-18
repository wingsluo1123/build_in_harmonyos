# megasdk 4.17.1d 适配笔记

> 申请人：zhangyuge147；队伍：龙骑士。
> 上游：https://github.com/meganz/sdk，tag v4.17.1d（commit 965e4c7cd518d48c5b2fbf0084a244fdecc44b35）。
> 源码包：https://github.com/meganz/sdk/archive/refs/tags/v4.17.1d.tar.gz，
> 大小 3,695,020 B，sha256 a9d3fffd6ecdfac4005cc84b9972a36b28aeb049febd4c688c537f4f097aaeec（本机实测下载哈希）。
> 状态：首轮工作树（未提交），待 HMBS 真机预检（rule4 门禁）回填实测数据。

## 0. 适配路径（3+2）

- **适配路径**：路径 A（基础适配）
- **使用知识库**：仓库既有 Autotools OHOS 适配经验（cdecl/castget/ctpl/swbis 的 GNU triplet 固定法、E002 只读 /tmp 绕法、设备 shell 选择）
- **知识库扩展**：无（`create` 判定 = 否；常规 autotools 移植，未发现可入库的新错误模式）
- **关联 Issue**：待 HMBS 分配（本轮不创建 PR）

## 1. 源码取证

| 项 | 值 |
|---|---|
| 主仓 | https://github.com/meganz/sdk |
| 版本 | tag v4.17.1d → commit 965e4c7c（`git ls-remote` 实测） |
| 归档 URL（官方源，R39） | https://github.com/meganz/sdk/archive/refs/tags/v4.17.1d.tar.gz |
| sha256 | a9d3fffd6ecdfac4005cc84b9972a36b28aeb049febd4c688c537f4f097aaeec |
| 构建系统 | Autotools（configure.ac + Makefile.am + m4/，libtool） |
| C++ 标准 | C++11（configure.ac：AX_CXX_COMPILE_STDCXX([11], ..., [mandatory])） |
| 顶层产物 | src/libmega.la（libmega），libmega.pc |

## 2. 构建系统结论

- **configure 开关（实测 configure.ac 全文）**：
  - `--disable-examples`：关掉示例客户端，避免 readline/termcap/fuse 示例依赖（制品仓在 OHOS 上无法满足 fuse 运行，readline 虽有配方但示例非必需）。
  - `--disable-chat`：关掉可选聊天媒体栈；核心同步/API 面不受影响。
  - `--disable-debug --disable-megaapirpc --disable-dependency-tracking`。
  - `--enable-tests --with-gtest=<conan gtest 包目录>`：构建上游测试程序（tests/include.am 的 BUILD_TESTS 条件）。
- **依赖面（configure.ac 硬性 AC_CHECK_LIB/AC_CHECK_HEADERS）**：
  - 必需：cryptopp（USE_CRYPTOPP 无条件）、SQLite（db）、OpenSSL、c-ares、cURL、zlib。
  - 条件：libsodium（chat 开启时强制；本配方仍显式依赖，Alpine 官方包同样链接 sodium）、libuv/pcre/readline 等仅特定开关需要，本配方关闭对应开关故不依赖。
- **FreeImage/PDFium**：configure 仅在 `--with-*` 显式指定或头文件存在时启用；默认走“无”分支，不强制要求，本配方不依赖。
- **测试注册**：tests/include.am `TESTS = tests/test_unit tests/test_integration`（automake 口径总数 = 2）。
  - test_unit：20 个 gtest 翻译单元，链接 `-lgmock -lgtest -lgtest_main`（conan gtest/1.17.0 提供 gmock）。
  - test_integration：SdkTest 系列，需真实 MEGA 账号 + 公网（`getAccountsForTest`，见 tests/integration/SdkTest_test.cpp），构建沙箱无此条件。

## 3. W0 依赖核验

本机为 Windows 执行器，按任务守则不在本机运行 conan；以下 pin 与已合入配方 `archives/m/megacmd/2.5.2/conanfile.py` 的 W0 实证（`conan download --only-recipe` 逐条 RC=0）同版本：

- cryptopp/8.9.0、libsodium/1.0.22、sqlite3/3.53.4、libcurl/8.5.0、openssl/3.5.6、zlib/1.3.1.1（与 megacmd 一致）
- c-ares/1.34.6（grpc/1.84.0、nghttp2/1.69.0、canl-c/3.0.0 等已用该版本通过门禁）
- gtest/1.17.0（test_requires；megacmd 同版本）

真机预检的 L0i 会再次逐条实测；若某条未发布，按 R36 先适配依赖，本包止损上报。

## 4. 语言面

- 上游几乎全部为 C++ 源（src/、include/ 以 .cpp/.h 为主），构建系统单一 autotools，主语言 cpp，与任务声明一致，无语言迁移问题。

## 5. 上游测试清点（R51 口径）

| 测试程序 | 来源 | 运行条件 |
|---|---|---|
| tests/test_unit | tests/unit/*_test.cpp（20 文件）+ main.cpp，gtest/gmock | 本地可运行，真机 `make check` 真实执行 |
| tests/test_integration | tests/integration/main.cpp + SdkTest_test.cpp | 需真实 MEGA 账号 + 公网，沙箱不可运行（environment 缺口，如实申报） |

- 官方注册单位：automake TESTS = **2**（`upstream_test_total: 2`，`upstream_test_count_method: autotools_tests`）。
- 计数来源：`test-suite.log` 的 `# TOTAL/# PASS/# FAIL/# SKIP` 汇总块（单一来源，禁止 stdout 字符串数数与算术修补）。
- test_integration 若 FAIL：归 `environment` 缺口（需账号+公网），证据为 test-suite.log 的 `FAIL: tests/test_integration` 行；test_unit 若 FAIL：归 `test_failure`。

## 6. 配方设计要点

1. **triplet 固定**：OHOS 下 `--build/--host=aarch64-unknown-linux-gnu`，跳过老旧 config.guess 探测；编译器仍经 profile 工具链指向 OHOS（cdecl/castget/ctpl/swbis 先例）。
2. **只写 TMPDIR**：复用 HMBS 注入的可写目录，configure/make 在设备 bash 下运行（E002 先例：dawgdic/swbis）。
3. **测试真实执行**：`build()` 内 `make -j1 check` 全量运行，解析 test-suite.log，发射 `HMBS_UPSTREAM_TEST_RESULT`，落盘 `megasdk_upstream_result.json` 并随包发布到 `res/`，供 test_package 在缓存命中轮次重发。
4. **消费者测试**：test_megasdk.cpp 6 个本地检查（Base64 编解码往返/空串/itoa、URLCodec 往返、MegaProxy 配置往返、MegaApi 构造析构），链接整包 libmega；计数来源为二进制自报的 `MEGASDK_CHECKS_PASSED=a/b` 单行。
5. **无补丁**：未改上游源码；conandata.yml 仅 sources。
6. **静态默认**：`shared=False` 默认（OHOS 常规做法）；`package()` 删除 `.la`。

## 7. 已知限制（非配方缺陷，PR 正文同步申报）

- test_integration 在无账号/无公网沙箱必然失败，属环境缺口，不代表 SDK 功能损坏。
- 构建产物较大（libmega 百余翻译单元），`conan create` 耗时较长；若触发默认 3600s 预算，需由平台按 `ci/config/build_timeouts.txt` 流程追加（本 PR 不碰 ci/ 基础设施）。
- 本轮为未提交工作树：以上结论中凡涉“真机实测”的数字，均待 HMBS 预检回填；当前 manifest.yaml 的 test_results 仅声明总数与口径，通过数如实留空。

## 8. 首轮自查（对标 .gitcode 审查与 L0 门禁）

- [x] 目录结构 archives/m/megasdk/4.17.1d（L0m：首字母/包名/conanfile 名版本一致）
- [x] settings 含 os/compiler/build_type/arch（L0p）
- [x] 平台判断 `in ("Linux", "OHOS")`（R32）
- [x] test_package/ 含真实 API 测试源 + test() 内 self.run（L0a-L0d，R34）
- [x] test_package/MANIFEST.yml 含 upstream_test_total/method/exist/audit（rule4）
- [x] conandata.yml 官方源 URL + sha256（R39），无外部 curl/wget（L0o），无硬编码 remote（L0g）
- [x] 无模板占位符残留；中文全为 UTF-8
- [ ] 真机 `conan create` + `make check` + test_package 实测（待 HMBS 预检）

## 9. 2026-10-16 真机 bootstrap 失败修复（未提交）
- 现象：`perl -I .../automake-1.18 .../.aclocal-real` 报 `Cwd.so: Perl_newSVsv_flags: symbol not found`（conan perl 5.42.2 XS 被 harmonybrew perl 加载）。
- 根因：`shutil.which("perl")` 取到 harmonybrew perl，而 conanbuild 的 PERL5LIB 指向 conan perl XS 树，ABI 不兼容；conan perl 自身在 HMDFS 上亦不可用（zzuf/avimetaedit 已证）。
- 改法：`_bootstrap_autotools_for_ohos` 改为 zzuf/avimetaedit 同式——单 shell 内 `export PERL=/data/service/hnp/bin/perl`，`unset PERL5LIB` 后按工具逐个设置（aclocal/automake→share/automake-1.18，autoconf/autoheader→share/autoconf），经 `sh` 调包装脚本；保留 `-I m4` 与原有 force/add-missing 参数。
- 回检（第 2 轮真机）：`sh` 调包装脚本在 HMDFS 上复现 `aclocal[8]: .../.aclocal-real: No such file or directory`（exit 126），即包装器 exec 链本身不可用；第 3 轮改混合式——保留 perl 直调绕开包装器 exec，但解释器固定 HNP 系统 perl 且每条命令内联 `PERL/PERL5LIB` 清洗（aclocal/automake 仅留 automake-1.18，autoconf/autoheader 仅留 autoconf share），libtoolize/autoconf/autoheader 经设备 shell 调用。

## 10. 2026-10-17 真机 configure 失败修复（未提交，第 4 轮）
- 现象：bootstrap 已通过，configure 起步即 `checking for aarch64-unknown-linux-gnu-gcc... /data/service/hnp/bin/clang` 后 `checking whether the C compiler works... no`，`configure: error: C compiler cannot create executables`（`autotools.configure()`，Error 77）。预检摘要未带 config.log，无法直接定因。
- 根因（待 config.log 实证）：首个编译器自检失败发生在任何依赖检查之前，候选为工具链本身不可用（如 clang 加载器路径缺失）或 configure 特有问题；本轮不猜测，先取证。
- 改法（conanfile.py，只加固与取证，不改构建语义）：
  1. `build()` 入口 `os.umask(0o022)`（zzuf 同式）+ `os.chdir(build_folder)` 与 `PWD` 预置（cdecl 同式，防 HMDFS getcwd 不可达）。
  2. configure 前新增 `_log_compiler_sanity()`：打印 conf 的 CC 并用 conanbuild 环境实跑 `clang --version` 与 `hello.c` 编译链接，区分“工具链坏”与“configure 特有”。
  3. `autotools.configure()` 包 try/except，失败时 `_dump_config_log()` 输出 config.log 候选路径、conftest 相关错误行与尾部 30 行后原样重抛；测试口径与计数逻辑零改动。
- 待下轮真机回填：config.log 真实错误行 + sanity 输出，据此定点修复。

## 11. 2026-10-17 编译器路径失效修复（未提交，第 5 轮）
- 现象：第 4 轮取证成功，sanity 复现 `"/data/service/hnp/bin/clang" --version` 报 `/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found`，configure 同因失败。repo profile（`ci/conan/profiles/ohos-aarch64`）烘焙的绝对编译器路径在本 worker 上不可执行（文件缺失或 HMDFS 不可达），与 configure 内容无关。
- 根因：profile 的 `tools.build:compiler_executables` 指向已搬迁的 `/data/service/hnp` 前缀；真机工具链实际与 hmbs 探测目录（`/storage/Users/currentUser/usr/local/bin` 等）同位。`exists/isfile` 不能证明 HMDFS 可执行性（E524/R49：X_OK 恒 False），必须以真实 spawn 为准。
- 改法（与第 4 轮不同策略，不再重复纯取证）：
  1. 主配方新增 `_probe_compilers()`：按 profile 值 → hmbs 工具目录（`HMBS_CMAKE/...`  dirname）→ conanbuild PATH（`command -v` 经设备 shell 查询）→ 旧绝对路径的顺序，以 `--version` 实测取首个可用 CC/CXX；`autotools.configure(args=['CC="..."', 'CXX="..."'])` 以命令行赋值覆盖工具链脚本中的 stale 驱动，CFLAGS/LDFLAGS 保持不变。
  2. `_log_compiler_sanity(cc)` 改为用选中驱动做 `hello.c` 实编译，日志即 configure 所用 CC 的证据。
  3. test_package `_resolve_compiler()` 同步改为逐候选 `--version` 实测回退（libapreq2/2.17 经验 adapt：原 `os.path.exists` 即采纳会导致同一失败）。
  4. 无可用编译器时如实抛错（含 config.log 转储），不跳过、不伪造。
- 待下轮真机回填：选中的 CC/CXX 路径与 configure 是否通过。

## 12. 2026-10-17 引号转义与 SDK 编译器候选（未提交，第 6 轮）
- 现象：第 5 轮探测生效（`/storage/.../usr/local/bin/clang` 确认无编译器；`command -v` 找到 `.harmonybrew/bin/clang` 且 `--version` 可执行并被选中），但 configure 仍失败，且检查行打印 `checking for aarch64-unknown-linux-gnu-gcc... "/storage/.../.harmonybrew/bin/clang"`——CC 值含字面双引号。
- 根因：`autotools.configure(args=['CC="%s"'])` 的内嵌引号被 autoconf 原样保留（Conan 传参时转义），exec 带引号路径失败；与编译器本身无关。属第 5 轮引入的新 bug，非重复旧修改。
- 改法：
  1. 去掉内嵌引号，改传 `CC=<path>`（路径无空格，安全）。
  2. 探测顺序新增 `_sdk_compiler()`：由 `LD_LIBRARY_PATH` 的 `llvm/lib` 反推同级 `bin/clang(++)`，另加 `ohos-sdk*/ohos/native/llvm/bin` glob 与 profile 版本化路径兜底；SDK 原生驱动优先于 harmonybrew 用户态 clang，profile 值仍首位（worker 健康时保持正统）。
- 待下轮真机回填：检查行引号是否消失、configure 是否通过；若 SDK/harmonybrew 驱动目标不匹配，config.log 会给出下一证据。

## 13. 2026-10-17 依赖供给缺失修复（未提交，第 7 轮）
- 现象：第 6 轮后编译器已可用（configure 通过 CC/CXX 自检，进入依赖检查），新阻塞为 `checking for libcryptopp... --with-cryptopp not specified` 后 `checking for cryptopp/cryptlib.h... no`，`configure: error: cryptopp/cryptlib.h header not found or not usable`。
- 上一方案为何不再适用：上一周期（第 4-6 轮）解决的是 profile 烘焙绝对编译器路径失效与 CC 引号转义，configure 停在首步 `C compiler cannot create executables`；本轮日志证明编译器探测已生效、configure 已越过编译器检查进入依赖探测，是新的失败域，不是同一根因的重复。
- 根因：主配方 `generate()` 只生成 `VirtualBuildEnv + AutotoolsToolchain`，缺 `AutotoolsDeps`，conan 图中的 cryptopp/sodium/sqlite/curl/openssl/c-ares/zlib 头与库搜索路径从未注入 conanbuild 环境；上游默认走系统路径探测（`--with-cryptopp not specified` → `AC_CHECK_HEADERS([cryptopp/cryptlib.h])`），在 OHOS 设备上必然找不到。仍用 `--with-gtest` 显式路径的 gtest 不受影响。
- 改法（与上一周期不同路线，不碰编译器探测）：`from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain`，`generate()` 内 `VirtualBuildEnv` 之后新增 `AutotoolsDeps(self).generate()`（bandwidthd/iverilog/juman 等仓内 autotools 配方同式），聚合 CPPFLAGS/LDFLAGS 经 conanbuild 供给全部 host 依赖；不新增 `--with-*` 前缀、不改测试口径与计数。
- 待下轮真机回填：cryptopp 检查是否通过及后续依赖（sodium/sqlite/openssl/cares/curl/zlib）是否依次通过。

## 14. 2026-10-17 conftest 运行时库路径修复（未提交，第 8 轮）
- 现象：上轮 `AutotoolsDeps` 生效（cryptopp 头检查已过），configure 进入 `checking for C compiler default output file name... a.out` / `checking whether we are cross compiling...` 后报 `configure: error: cannot run C compiled programs. If you meant to cross compile, use '--host'`；config.log 直证为 `Error loading shared library libcurl.so: (needed by ./conftest)`（exit 77）。
- 与上轮不同：上轮解决的是编译期头/库搜索路径缺失（`cryptlib.h not found`）；本轮是链接后执行期 loader 找不到已链入的共享库，是新的失败域，不重复上轮修改。
- 根因：`--build/--host=aarch64-unknown-linux-gnu` 相等即 native，configure 必须执行 conftest；而共享依赖（libcurl 等）的 lib 目录只进了 LDFLAGS，未进 loader 搜索路径，conanbuild.sh 本身不提供 host run 路径，故 conftest 一执行即缺库退出。
- 改法：`generate()` 新增 `VirtualRunEnv(self).generate()` 并经 `tc.environment()` 把 7 个 host 依赖的 `lib/` 目录逐个 `prepend_path("LD_LIBRARY_PATH")`（仅运行时搜索，不改链接 flags）；`build()` 在 configure 前再把同一目录集合并入本进程 `os.environ["LD_LIBRARY_PATH"]` 并打印，双通道保证 configure→conftest 子进程继承。
- 待下轮真机回填：conftest 是否可执行、configure 是否进入后续依赖检查。

## 15. 2026-10-17 FreeImage 硬性探测关闭（未提交，第 9 轮）
- 现象：conftest 运行时路径修复生效（已越过 `checking whether we are cross compiling`，cryptopp/sodium/openssl/cares/curl 均过，libraw 按 NOTICE 通过、libuv 用系统版通过），新阻塞为 `checking for FreeImage... --with-freeimage not specified` → `checking for FreeImage.h... no` → `configure: error: FreeImage.h header not found or not usable`（exit 1）。
- 与上轮不同：上轮解决的是 conftest 执行期 loader 缺共享库；本轮是 configure 依赖开关语义问题，不重复 LD_LIBRARY_PATH 修改。
- 根因：上游 `configure.ac` 的 FreeImage 默认分支（含 `AC_MSG_ERROR`）是强制的，只有 `--with-freeimage=no` 才走 `freeimage=false` 跳过；notes.md 第 2 节“默认走无分支”对 FreeImage 不成立。核心同步/API 面不需要媒体/图形栈（megacmd FULL_REQS=OFF 同理），应显式退出。
- 改法：`_configure_args()` 新增 `--with-freeimage=no` 一项；不新增 freeimage 依赖、不改测试口径。
- 待下轮真机回填：FreeImage 检查是否跳过及后续（pdfium/ffmpeg/mediainfo 等可选栈）是否依次通过。

## 16. 2026-10-17 gtest C++17 编译失败修复（未提交，第 10 轮）
- 现象：configure 已通过（FreeImage 关闭生效），`make` 在 `tests/unit/*` 处失败，`gtest-port.h:273:2: error: C++ versions less than C++17 are not supported`，随后 `index_sequence/make_index_sequence` 缺失、20 errors（conan gtest/1.17.0 头要求 C++17）。
- 上一方案为何不再适用：第 4-9 轮解决的是工具链探测、引号转义、AutotoolsDeps 缺失、conftest loader 路径、FreeImage 硬性探测；本轮日志证明 configure 已越过全部依赖检查进入编译期，是新的失败域，不是重复。
- 根因：上游 `configure.ac` 硬编码 `CXXFLAGS="$CXXFLAGS -std=c++11 ..."`，全局为 C++11；conan 图中的 gtest 1.17.x 头强制 C++17。测试翻译单元同时包含 `<gtest/...>` 与 mega 头，在 C++11 下从原理上不可编译。核心 libmega 本身不含 gtest，可保持上游 C++11。
- 改法（最小侵入，不碰库标准）：新增 `patches/0001-tests-cxx17-for-gtest-1.17.patch`，仅给 `tests/include.am` 的两个测试目标追加 `-std=c++17`（`tests_test_unit_CXXFLAGS` / `tests_test_integration_CXXFLAGS`）；per-target 标志排在全局 `-std=c++11` 之后，last-wins 仅覆盖测试目标。`conandata.yml` 注册该补丁（`apply_conandata_patches` 已在 `build()` 首行调用，bootstrap 的 automake 会重生成含新标志的 Makefile.in）。核心库仍按上游 C++11 编译，不新增依赖、不改测试口径与计数。
- 待下轮真机回填：测试目标是否编译通过、`make check` 的 test-suite.log 汇总及两个 TESTS 的真实结果。

## 17. 2026-10-17 补丁 hunk 计数修正（未提交，第 11 轮）
- 现象：上一轮补丁内容正确但 hunk 头 `@@ -39,8 +39,10 @@` 与实际不符，真机报 `extra lines for hunk no.1 at 15 / Failed to parse patch`，`apply_conandata_patches` 直接失败。
- 根因：hunk 起始行与新旧行数写错；实际覆盖原文件第 36-44 行（旧 9 行、新 13 行，含 2 个空上下文行）。
- 改法：仅修正补丁头为 `@@ -36,9 +36,13 @@`，补丁内容零改动；本机用上游原文件逐行回放验证上下文与删除行精确匹配、计数一致。
- 待下轮真机回填：补丁是否正常应用、测试目标 C++17 编译是否通过。

## 18. 2026-10-17 per-target 标志被全局覆盖，改全局 C++17（未提交，第 12 轮）
- 现象：0001 补丁已正常导出应用（`Copied 1 .patch file` 且无解析错误），但 `make` 仍报同样的 gtest C++17 门槛错误（`AttrMap_test.o` 20 errors）。
- 与上轮不同：上轮解决的是补丁 hunk 头解析失败（`Failed to parse patch`）；本轮补丁应用成功但无效，是新的失败域，不重复上轮修改。
- 根因：automake 编译规则把 per-target `tests_*_CXXFLAGS` 放在全局 `$(CXXFLAGS)` 之前（`$(CXX) ... $(tests_test_unit_CXXFLAGS) $(CXXFLAGS)`），configure.ac 全局硬编码 `-std=c++11` 永远 last-wins，覆盖了 0001 的测试目标 `-std=c++17`。
- 改法（与上轮不同策略）：新增 `patches/0002-configure-cxx17-global.patch`，把 configure.ac 第 148 行全局 `-std=c++11` 提至 `-std=c++17`，整树（lib + 测试）统一 C++17；0001 保留作同义冗余（ harmless，与全局一致）。已用上游原文件逐行回放验证新补丁上下文与计数（`APPLY CHECK OK`，旧 8 行/新 11 行）。
- 待下轮真机回填：测试目标是否编译通过、C++17 下 libmega 是否有新报错。

## 19. 2026-10-17 VPATH 生成头缺失修复（未提交，第 13 轮）
- 现象：C++17 全局补丁生效（gtest 门槛消除，`make` 已进入 `tests/unit/test_unit-AttrMap_test.o`），新阻塞为 `include/mega/posix/megasys.h:30:10: fatal error: 'mega/config.h' file not found`（`make[2]` Error 1，连带 `all-recursive`/`all` Error）。
- 上一方案为何不再适用：第 10-12 轮解决的是 gtest 1.17 C++17 门槛与 automake 标志排序覆盖；本轮日志证明编译器探测、configure 依赖检查、C++17 标准均已通过，进入编译期头搜索的新失败域。不是同一根因的重复，不沿用相同补丁。
- 根因：上游 `AC_CONFIG_HEADERS([include/mega/config.h])` 把生成头放在 `$(top_builddir)/include/mega/config.h`；Conan 为树外构建（`build-release` 子目录），而 `Makefile.am` 的 `AM_CPPFLAGS` 仅有 `-I$(top_srcdir)/include`，缺 `-I$(top_builddir)/include`。上游 `tests_test_integration_CXXFLAGS` 自带 `-I$(top_builddir)/include` 而 `tests_test_unit_CXXFLAGS` 没有，佐证上游默认按树内构建验证、VPATH 支持不完整。
- 改法（与上轮不同路线，不碰标准标志）：新增 `patches/0003-vpath-config-h-include.patch`，在 `Makefile.am` 的 `AM_CPPFLAGS` 首位追加 `-I$(top_builddir)/include`（全局生效，lib 与全部测试目标均覆盖）；`conandata.yml`/`manifest.yaml` 同步注册。补丁头 `@@ -22,8 +22,11 @@` 已用上游原文件逐行回放验证（旧 8 行覆盖 22-29 行、新 11 行，上下文精确匹配）。
- 修正（同轮第 2 次）：首版补丁把注释插在 `AM_CPPFLAGS = \` 续行符与其值之间，真机报 `comment following trailing backslash` 致 `AM_CPPFLAGS` 未定义；已改为注释前置于 `AM_CPPFLAGS` 块之前、值行保持单行替换，续行结构完整。
- 待下轮真机回填：`mega/config.h` 是否找到、lib 与两个测试目标是否继续编译及 `make check` 汇总。

## 20. 2026-10-17 libtool VERSION_INFO 空值修复（未提交，第 14 轮）
- 现象：configure 已通过（FreeImage/C++17/VPATH 头均生效），make 在 src/libmega.la 处失败：libtool: error: CURRENT '' must be a nonnegative integer / ':0:0' is not valid version information（make[2]/make[1]/make 连带 Error）。
- 上一方案为何不再适用：第 10-13 轮解决的是 gtest C++17 门槛与 VPATH config.h 缺失；本轮日志证明编译已进入链接期，是新的失败域。
- 根因：上游 configure.ac 把 LT_CURRENT 的计算写成 configure 运行时的 shell 管道 grep define <include/mega/version.h | awk ...，路径相对 configure 工作目录。Conan 为树外构建（build-release 子目录），相对 include/ 查找落空，管道产出空串，VERSION_INFO 变为 :0:0；且 version.h 现为 #ifndef/#define 守卫对，RS="" 的 awk 段落逻辑跨 awk 方言本就脆弱。
- 改法（配方侧确定性修复，不新增补丁文件）：build() 在 bootstrap 后、configure 前新增 _fix_libtool_version_for_vpath()，用 python 正则从源码树 include/mega/version.h 解析 MEGA_MAJOR/MINOR/MICRO_VERSION（本版 4/17/1），算出 LT_CURRENT=41701 后把生成的 configure 首个 LT_CURRENT= 行 pin 死；LT_REVISION/LT_AGE 保持上游 0。找不到赋值或解析失败即抛错，不静默跳过；测试口径与计数零改动。
- 待下轮真机回填：libmega.la 是否正常链接及 make check 汇总。

## 21. 2026-10-17 integration stdfs.h clang filesystem fix (uncommitted)
- Symptom: make reaches tests/integration then fails: stdfs.h:8: fatal error experimental/filesystem file not found (make[2]/make[1]/make Error).
- Why previous fix no longer applies: rounds 4-14 fixed toolchain probing, quote escaping, AutotoolsDeps, conftest loader path, FreeImage gate, gtest C++17, VPATH config.h, libtool VERSION_INFO; this log proves configure plus lib build passed and failure moved to integration-test compile, a new domain.
- Root cause: upstream tests/integration/stdfs.h gates std::filesystem on (__cplusplus>=201703L) AND (no GNUC or GNUC>=800). Clang defines __GNUC__=4 for compatibility, so clang+C++17 falls through to elif (__cplusplus>=201700L) which pulls <experimental/filesystem>, removed in current libc++; the __clang_major__>=11 fallback also uses gone std::__fs::filesystem namespace.
- Fix: new patches/0004-stdfs-clang-filesystem.patch exempts clang in first gate (defined(__clang__) OR), so clang+C++17 takes <filesystem>/std::filesystem; fixes fallback namespace to std::filesystem; GCC logic unchanged. Registered in conandata.yml/manifest.yaml. Verified with git apply --check against tag file bytes (rc=0). No test-count or harness change.
- Follow-up: keep _run_upstream_tests raising only for non-environment failures; integration-only FAIL (needs live MEGA accounts + public net via getAccountsForTest) now emits real counts plus environment gap and lets the lib package succeed. If test_unit fails, still raises.
- Pending true-device: integration compile pass, make check summary, marker counts.

## 23. 2026-10-17 test_package uv_* 未定义修复（未提交，第 15 轮）
- 现象：lib 已编过、test_package 链接失败：`ld.lld: error: undefined symbol: uv_async_init / uv_tcp_init / uv_tcp_keepalive / uv_sem_post / uv_ip6_addr / uv_tcp_bind / uv_ip4_addr / uv_listen / uv_run ... referenced by megaapi_impl.cpp (MegaTCPServer::run/initializeAndStartListening)`，`test package: Error in build() line 96`。另见两次 `github.com ... ConnectTimeout` 后重试成功（源码最终下载成功，非阻塞）。
- 上一方案为何不再适用：第 4-14 轮解决的是编译器探测、AutotoolsDeps 缺失、conftest loader、FreeImage、gtest C++17、VPATH、libtool、stdfs、install 64；本轮日志证明主库已编过、失败移到 test_package 消费链接，是新的失败域。
- 根因：上游 configure 的 libuv 默认分支为自动启用（无 `--with-libuv` 时 `AC_CHECK_HEADERS([uv.h]) + AC_CHECK_LIB(uv, [uv_run])`，有则 `libuv=true`）；真机设备自带系统 libuv 故 `MegaTCPServer` 按有 libuv 编进 `libmega.a`，而配方 `requirements()` 未声明 libuv、`test_package` 链接行无 `-luv`，静态归档的 uv 引用无法解析。notes 第 2 节“libuv 仅特定开关需要故不依赖”与真机证据矛盾。
- 改法（最小依赖补齐，不关特性、不改测试口径）：
  1. 主配方 `requirements()` 新增 `libuv/1.52.1`（megacmd/2.5.2 同版本、已验证 RC=0 已发布）；`_configure_args()` 新增 `--with-libuv=<conan 包目录>` 走上游 PATH 分支，强制用 registry 头/库而非设备系统拷贝；`_host_dep_libdirs()` 纳入 `libuv` 使 conftest/运行期 `LD_LIBRARY_PATH` 覆盖。
  2. `test_package` 依赖目录循环纳入 `libuv`，链接行 `-lmega` 后追加 `-luv`（静态归档须紧随被依赖者之后）。
  3. `conandata.yml` 的 `url` 改为有序列表（`gh-proxy` 镜像在前、官方 URL 在后回退，`sha256` 不变），对应真机两次直连超时；复用仓内 `zydis/bzrtp` 同式与 `ci/conan/build_and_test.sh` 的 GitHub 镜像映射。
  4. `manifest.yaml` 的 `required` 同步加入 `libuv/1.52.1`。
- 待下轮真机回填：configure 是否取 conan libuv、`test_megasdk` 链接是否通过及 `HMBS_TEST_PACKAGE_RESULT` 计数。

## 22. 2026-10-17 make install Error 64 fix (uncommitted)
- Symptom: build+make check passed (compile fixed by 0004), package() make install dies at install-nobase_libmegaincludeHEADERS Error 64; log shows batched header list then destination p//include/mega.
- Why previous fix no longer applies: round 15 fixed test-compile header selection (stdfs.h); this log proves compile and test build passed and failure moved to install phase, a new domain. No source-download timeout in log (export/configure/make all ran), so conandata URL/sha stay untouched per守则 timeout exception.
- Root cause: host/HMBS install wrapper accepts only single-file two-arg calls (EX_USAGE 64), while automake batches dozens of headers into one INSTALL_DATA call. Same family lzop/1.04, myman/4.0.116, goffice, adms/2.3.7, avahi*, zurl/1.12.0; feedback row 5 same signature.
- Fix (install-tool layer, OHOS-gated, Linux unchanged): package() writes _ohos_install_shim/install (cp/mkdir, -c/-m/-d parse, chmod best-effort) and redirects generated Makefiles INSTALL/INSTALL_DATA/PROGRAM/SCRIPT to it before autotools.install(). No source/test/mirror change.
- Pending true-device: make install header batch passes, package produces libmega + headers.

## 25. 2026-10-18 编译期 Out of memory 降内存修复（未提交，本轮）
- 现象：预检摘要失败阶段 compile，原因 `/bin/sh: Out of memory`（shell fork 失败），上游测试 0/0/0。日志无具体 TU 错误行，是整机 RAM 耗尽而非单个源码错误。
- 与上轮不同：第 4-15 轮解决的是编译器探测、AutotoolsDeps、conftest loader、FreeImage、C++17、VPATH、libtool、stdfs、install 64、libuv 链接；本轮日志证明 configure 已通过、失败点移到 `make` 编译大 TU/链接期，是新的失败域。
- 根因：libmega 为百余重型 C++ TU + gtest 链接 test 二进制；并行 clang 进程与调试信息（profile 默认 -g）在小内存真机上 fork 失败。`/bin/sh: Out of memory` 即 fork 证据，不是编译器缺失或源码缺陷。
- 改法（只降内存，不改语义/测试口径）：`generate()` 内 `tc.cflags/tc.cxxflags` 追加 `-g0`（last-wins 覆盖 profile -g，去调试信息，大幅降编译与链接 RAM）；`build()` 内 `autotools.make(args=["-j1"])` 串行构建（与 `make check -j1` 一致，hmbs jobs=1 之外的显式保险）。
- 待下轮真机回填：make 是否越过 OOM 点、make check 汇总及双标记计数。

## 24. 2026-10-18 时钟偏差 tar 警告加固（未提交，本轮）
- 现象：预检摘要失败阶段 compile，原因仅为同步 tar 的未来时间戳警告（`tar: ./archive: time stamp 2026-10-18 01:42:42 is 0.28s in the future` 等 7 行，宿主比真机快约 0.28s）；stderr 尾部仍停在 configure 依赖探测（egrep 缓存行后截断），42073 字符原文被摘要省略，未给出真实编译错误行。
- 与上轮不同：第 4-15 轮解决的是编译器探测、AutotoolsDeps、conftest loader、FreeImage、C++17、VPATH、libtool、stdfs、install 64、libuv 链接；本轮 tar 路径（./archive、./profiles、__pycache__）指向配方同步树而非上游源码，且警告本身为非致命时钟偏差，是新的失败域，不重复上述修改。
- 根因：宿主-真机时钟偏差致同步文件 mtime 落在真机未来；未来 mtime 会触发 autotools sanity（newly created file is older than distributed files）与 make 依赖排序异常。__pycache__（conanfile.cpython-313.pyc）亦被同步，加剧噪音。
- 改法（配方侧确定性加固，不改构建语义与测试口径）：新增纯 Python `_normalize_timestamps()`（os.utime，无 shell、无 touch 二进制），`source()` 在 get 后与 `build()` 入口各调用一次，将源码/构建树未来 mtime 钳制到真机当前时间，仅警告不中断；`_log_compiler_sanity()` 追加 `clang -dumpmachine` 以在下轮日志中实证所选 CC 的目标 triple（区分 SDK 原生驱动与 harmonybrew 回退）。
- 待下轮真机回填：tar 警告是否消除、configure sanity/make 排序是否恢复，以及被省略的真实编译错误行（如下轮仍失败，以新日志的 config.log/make 错误为准）。

## 26. 2026-10-18 test_package curl 无 TLS 崩溃修复（未提交，本轮）
- 现象：主库已编过、上游 2/2/1（integration 环境缺口如预期），test_package 在第 6 检查 `MegaApi` 构造处 `libc++abi: terminating ... std::runtime_error: cURL built without HTTP/HTTPS support. Aborting.` 后 Signal 6（exit 134）。
- 上一方案为何不再适用：第 4-15 轮解决的是编译器探测、AutotoolsDeps、conftest loader、FreeImage、C++17、VPATH、libtool、stdfs、install、libuv 链接；本轮日志证明编译与上游单元测试均已通过，失败移到消费者运行期，是新的失败域。
- 根因：`requirements()` 用的 `libcurl/8.5.0` 配方写死 `CURL_USE_OPENSSL=OFF`，其 `curl_version_info()` 无 `https`，上游 `net.cpp:268` 判定后抛异常（megacmd/2.5.2 notes 同证据：`sdk CRIT curl built without HTTP/HTTPS support. Aborting. [net.cpp:268]`；pianod/421 与 coeurl/0.3.2 同因改用 TLS 变体）。
- 改法（补齐依赖，不删断言、不改测试口径）：`requirements()` 改用 `curl/8.15.0.1`（`CURL_USE_OPENSSL=ON`，同 `-lcurl` 链接名与 `curl/curl.h` 头，pianod/421 先例）；直接 `openssl` 钉到 `3.5.6.1` 与 curl 传递依赖对齐（避 3.5.6/3.5.6.1 冲突，zlib 仍为 1.3.1.1 一致）；`_host_dep_libdirs()` 与 test_package 依赖循环的 `libcurl` 键同步改为 `curl`（产物仍为 `libcurl.so`，链接行 `-lcurl` 不变）；`manifest.yaml` 同步。
- 待下轮真机回填：`MegaApi` 构造是否通过、`HMBS_TEST_PACKAGE_RESULT` 6/6 及上游标记是否重现。
