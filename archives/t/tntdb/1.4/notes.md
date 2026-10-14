# tntdb 1.4 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, libtool)
- 编译日期: 2026-09-27
- 编译器: clang/clang++
- 状态: built（待真机 rule4 门禁验证后由 HMBS 提交）

## 上游信息
- 上游仓库: https://github.com/maekitalo/tntdb
- 上游版本: V1.4 标签（2019-10-08, commit b66cd63）
- 源码包: V1.4.tar.gz（147261 字节，
  sha256 `20f5d10817c0ad74f7728a0ca393337c0c73336dbc2b3273dcde22e5cc7cd76d`；
  codeload 与 archive 两种端点字节一致，已实测）
- 许可证: LGPL-2.1-or-later
- 依赖: cxxtools（强制，头文件 + `-lcxxtools`，测试另需 `-lcxxtools-unit`）、
  sqlite3（sqlite 驱动）、mysql/postgresql 客户端（本适配禁用）

## 编译步骤

1. `autoreconf -fi`（tag 归档不带生成的 configure，需 automake/1.18 + libtool/2.5.4.1）。
2. `configure --with-sqlite=yes --with-replicate=yes --with-mysql=no
   --with-postgresql=no --with-oracle=no --with-driverdir='${libdir}'
   --disable-dependency-tracking
   --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
  （`SHELL=/bin/sh`、`CONFIG_SHELL=/bin/sh`，TMPDIR 指向真机可写目录）。
3. `make -j1`，`make -j1 check`（仅构建出 `test/tntdb-test`，上游未定义 TESTS）。
4. 用真机 python3 标准库 sqlite3 模块把 `test/sqlite-test.sql` 灌成
   `test.db`，`TNTDBURL=sqlite:<tmp>/test.db` 运行 `test/tntdb-test -s`。
5. `make install`（INSTALL 重定向到 mkdir -p 兼容垫片，删除 `*.la`）。

## 上游测试盘点

`test/Makefile.am` 把 8 个套件编译进单个 `test/tntdb-test` 二进制
（cxxtools-unit `testmain.h`：`-s` 打印 `success/errors/skipped`，
退出码即 `app.errors()`）：

| 套件文件 | 方法数（registerMethod 源码审计） | 是否需 DB |
|---|---|---|
| base-test.cpp | 15 | 是（TNTDBURL，默认 sqlite:test.db） |
| colname-test.cpp | 1 | 是 |
| decimal-test.cpp | 6 | 否 |
| sqlbuilder-test.cpp | 4 | 否 |
| statement-test.cpp | 3 | 否（mock IStatement） |
| timespan-test.cpp | 1 | 否 |
| types-test.cpp | 26 | 部分是 |
| value-test.cpp | 2 | 否 |
| **合计** | **58** | fixture 覆盖全部 DB 需求 |

`test/test.cpp`、`test/tntdb-locktest.cpp` 未列入 SOURCES，属手工工具，
不计入总数。计数口径 `auto`（单一 cxxtools-unit 聚合）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 归档无 configure | git 归档不含 autotools 生成文件 | `autoreconf -fi`（与同作者 cxxtools 3.0.0 配方同模式） |
| 2 | `make check` 不执行测试 | 上游未定义 automake TESTS | 配方显式运行 `test/tntdb-test -s` 并解析汇总 |
| 3 | mysql/postgresql 驱动无法构建 | 真机无客户端库与服务器 | `--with-mysql=no --with-postgresql=no`，保留 sqlite + replicate |
| 4 | 驱动 .so 对消费者不可见 | 上游默认装到 `lib/tntdb/` 子目录，不在 loader 搜索路径；且构建期绝对 DRIVERDIR 对可重定位包会过期 | `--with-driverdir='${libdir}'`，驱动与主库同目录 |
| 5 | 静态主库时驱动符号解析风险 | 驱动 dlopen 需从主库解析 core 符号 | 默认 `shared=True`（插件架构要求，见 conanfile 文档串） |
| 6 | 本机 Windows 无法完整检出上游 main | 上游同时存在 `archives/l/libXext` 与 `archives/l/libxext`（Linux 大小写敏感）及带 `\r` 的补丁文件名 | 与本任务无关；HMBS 在 Linux 真机同步完整代码树，本机仅维护 tntdb 目录 |
| 7 | 真机 `autoreconf -fi` 在 `aclocal` 阶段 exit 126：`bin/aclocal: .aclocal-real: No such file` | 远端 ohpcd automake/1.18 二进制包半残（DRAFT-6051：包装器在、点文件缺失；同包 `autom3efab95d532f9`，xraylib/4.2.1 同症）；tntdb tag 无自带 configure，无法像 libee 那样跳过自举。2026-09-29 预检证明仅靠存在性预检不够：预检仍走了 `autoreconf` 并在运行时失败 | 配方分层自举：完好时仍走 `autoreconf -fi`，但用 try/except 包裹，运行时 exit 126 即自动转分步手动自举（2026-09-29 预检已验证该兜底生效）；缺失时直接分步手动自举（dcap 2.47.14 模式：libtoolize → aclocal → autoheader → automake --add-missing → autoconf，conan payload 优先、`--version` 实测过的系统工具兜底），并补幂等 E007 config.guess/sub HarmonyOS 补丁（此前缺失，vanilla 2024 脚本不认 `linux-ohos` 三元组） |
| 8 | 真机 `configure[139]: /data/service/hnp/bin/bash: inaccessible`（Error 127，中断于 `autotools.configure()`） | 镜像/profile 烤进 conanbuild 脚本的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 在本 worker 不存在；`generate()` 的 hmbs_shell 覆盖输给 conanbuildenv  sourcing 顺序（libmrss 先例），`os.environ` 同样被覆盖 | `build()` 在 configure 前新增 `_sanitize_stale_hnp_shell()`：把 build/generators 目录下 `.sh` 及新生成 `configure` 中的该坏路径替换为 `/bin/sh`，并重 pin `SHELL/CONFIG_SHELL`；仅改 shell 路径，不碰测试逻辑 |
| 9 | 真机 `configure: C compiler cannot create executables`（2026-09-30 预检：`checking for aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang` 后 `checking whether the C compiler works... no`；同轮 `libtoolize: /data/service/hnp/bin/grep: inaccessible`） | profile `[conf] tools.build:compiler_executables` 仍指向 `/data/service/hnp/bin/clang/clang++`，而真机 clang 已迁移到 `~/usr/local/bin`（zydis/4.1.1 已实证同迁移；本 worker `HMBS_BUILD_TOOLS` 亦只列 `/storage/Users/currentUser/usr/local/bin` 工具），旧路径缺失致 conftest 链接失败；自举本身已成功（fallback 生效），与 automake 半残无关 | `generate()+build()` 新增 `_resolve_compiler/_pin_real_compilers`（zydis 模式：旧路径存在则沿用 CI，缺失则按 PATH→`~/usr/local/bin`→`/storage/.../usr/local/bin` 解析并 `--version` 实测）：重写生成的 `.sh/.cmake` 中的旧编译器绝对路径、经 `hmbs_compiler` build-scope 导出 CC/CXX，`build()` 复核并在 configure 失败时转储 `config.log` 尾部 + `HMBS_DIAG_CONFIGURE_FAILED` 单行诊断；仅换编译器路径，不改测试口径 |
| 10 | 真机 `make: libtool: error: '//lib/libcxxtools.la' is not a valid libtool archive`（2026-09-30 第二轮预检：configure 已过，`src/libtntdb.la` 链接时 `library .../libcxxtools.la was moved` 后 `grep/sed: //lib/libcxxtools.la: No such file`；同行 `-DDRIVERDIR=\"//lib\" -rpath //lib`） | 双因：① 依赖 cxxtools 包自带 `.la` 其 `libdir='//lib'`（构建时 prefix=/ 残留，adplay/zile/libgee 同款），libtool 按该残留路径重定位即 ENOENT；② 本配方 `tc.configure_args` 的 `--with-driverdir=${libdir}` 缺单引号，与 notes 记录的 quoted 形式不一致，`/bin/sh` 命令行会先展开 `${libdir}`，driverdir 先天易 stale | ① `build()` configure 前删依赖 `lib/*.la` 中含 `//lib` 残留者（zile/2.6.4 模式：libtool 回落直链 `.so`，仅删缓存 `.la`，不碰测试）；② driverdir 改回 `--with-driverdir='${libdir}'` 单引号字面量，让 configure（非 shell）展开；③ configure 成功后打 `prefix/libdir/driverdir` 三行 `HMBS diag makevar` 供下轮验证 |
| 11 | 真机上游测试启动即 `Error relocating libtntdb.so.5: __divtf3/__addtf3等: symbol not found`（exit 127，`-s` 汇总缺失；2026-10-08 第三轮预检：编译链接已过，configure/`.la` 修复生效） | OHOS clang 包装器给 libtool 共享库链接注入 `-nostdlib`，丢掉隐式 builtins；aarch64 long double 为 fp128（decimal.cpp），软浮点符号滞留未定义，链接期不报错，延迟到测试二进制 dlopen 时爆发（libzimg/3.0.6 + DRAFT-13534 同指纹） | `generate()` 仅 OHOS 时 `tc.extra_ldflags.append("-lclang_rt.builtins")`（回退 `tc.ldflags`）；前两轮修复保留 |
| 12 | 真机上游测试 49/58（9 失败；2026-10-08 第四轮预检：编译链接已过，`test/tntdb-test -s` 实测 `types::testLimits/testUnsignedLong/testUint64: EXCEPTION can't convert "1.8446744073709552e+19" to unsigned long`、`types::testDecimal: ASSERTION at types-test.cpp:279` 等） | 非 OHOS 特有，为上游 sqlite 驱动固有精度限制：`src/sqlite/statement.cpp` 中 `setUnsignedLong` 超 `LONG_MAX`、`setUnsigned` 超 `INT_MAX` 即 `log_warn("possible loss of precision")` 后转 `setDouble`，`setDecimal` 经 `getDouble()` 存 double，`setUnsigned64` 强转 `int64_t`；double 往返无法精确表示 ULONG_MAX/UINT64_MAX（打印为 `1.8446744073709552e+19`）与精确 Decimal，`Value::get(unsigned long)` 解析科学计数法即抛，Decimal 相等即断言。上游 `make check` 从不执行该 runner（未定义 TESTS），故该失败在上游即存在；此前配方把测试失败 `raise RuntimeError` 冒充成编译失败，致预检停在 compile 阶段 | `_run_upstream_tests` 改为测试失败不抛：计数仍以 `-s` 汇总为唯一来源，逐行解析 `suite::method: STATUS` 仅作 gaps 明细（`len==failed` 时逐条 `count:1/test_failure`，否则聚合一条 `count:failed`，`skipped` 另计，保证 `sum(gaps.count)==failed+skipped`），随 marker 输出 `gaps` 并落盘 `hmbs_upstream.json`，构建继续走 `package/test_package`；仅 `-s` 汇总缺失（harness 未跑）才抛。不删断言、不跳过测试 |
| 13 | 真机 `package()` 安装失败 `libtool: cannot install 'tntdb5-replicate.la' to a directory not ending in //lib`（2026-10-08 第五轮：gaps 放行后首次进入安装阶段，`mkdir -p '.../p'//lib''` 杂引号为证） | 前轮 `--with-driverdir='${libdir}'` 单引号经 AutotoolsToolchain 自有引号层后原样漏进 Makefile（`driverdir = '//lib'` 杂引号 + `//lib` 残留），`$(DESTDIR)$(driverdir)` 展开即 `'.../p'//lib''`，libtool 纯字符串后缀校验即不匹配；属新阶段暴露的本配方引号 bug，非上游源码问题 | ① `generate()` 改传 `--with-driverdir=\${libdir}`：无内嵌单引号，shell 透传字面 `${libdir}` 给 configure/make 展开；② 新增 `_normalize_dslash_paths()`（build configure 后 + package install 前双调用）：Makefile/`.la` 中 `(?<!:)//lib`→`/lib`（避开 `://`），并去 `driverdir =`/`libdir =` 行杂单引号，仅整路径文本，不碰测试 |
| 14 | 真机 `test_package` CMake 配置失败 `CMAKE_CXX_COMPILER: /data/service/hnp/bin/clang++` 不存在（2026-10-08 第六轮：主包安装已过，上游 49/58 gaps 已落盘，卡在消费者测试配置） | 共享 profile 的 `tools.build:compiler_executables` 仍指向已迁移旧路径（主包 2026-09-30 同因，`HMBS_BUILD_TOOLS` 只列 `/storage/.../usr/local/bin` 工具）；`test_package` 用 CMakeToolchain，直取 profile 值，无主包 `_pin_real_compilers` 纠偏 | `test_package/conanfile.py generate()` 新增纠偏：旧路径存在沿用、缺失则按 PATH→`~/usr/local/bin`→`/storage/.../usr/local/bin` 解析并写入 `CMAKE_C/CXX_COMPILER` 缓存，经 build-scope 导出 CC/CXX，重写 generators 中残留旧绝对路径；仅换编译器路径，不改测试口径 |
| 15 | rule4 incomplete：新增测试 0/10 无 gaps（2026-10-09 预检：ctest 1/1 Failed，仅见 3 行 CHECK PASS 即中断，test_package 标记硬编码 passed=0 无明细） | 双因：① test_tntdb.cpp 全流程单 try 包裹，任一用例抛异常即 abort，后续 CHECK 永不打印，旧标记仅按退出码猜 passed=0（禁用模式：无确定性计数源、无 gaps）；② statement-bind 用 setDouble、transaction 用显式 rollback()，与上游 base-test proven 路径（泛型 set(name,value)、析构回滚）不一致 | ① test_tntdb.cpp 改为 10 用例逐项 guarded（guardedCtx/guardedPlain，异常转 DIAG+FAIL 不 abort；set→泛型 set("limit",9.0)，事务改析构回滚；stdout 无缓冲；setup 失败时 DB 用例逐项 FAIL+offline 用例照跑）；② test_package/conanfile.py 改 subprocess 捕获 ctest 合并输出，以 CHECK PASS/FAIL 行为唯一计数源（TNTEST_RESULT 仅作证据），ordered 期望集仅用于命名缺失项，失败/缺失逐项 gaps(count:1/test_failure)+DIAG 证据，和恒 sum==failed，不做 rc 猜测修正；ctest 经 HMBS_CMAKE 同目录回退定位 |

## 依赖版本

- cxxtools/3.0.0（archives 已有，需制品仓已发布；真机预检复核）
- sqlite/3.53.3（archives 已有，需制品仓已发布；真机预检复核）
- automake/1.18、libtool/2.5.4.1（tool_requires，仅构建期）

## 验证结果

待 HMBS 真机预检返回后填写：

```bash
# 预检 conan create 日志摘录（真机实测，非估算）
# HMBS_UPSTREAM_TEST_RESULT={...}  # test/tntdb-test -s，58 方法
# HMBS_TEST_PACKAGE_RESULT={...}   # test_tntdb，10 CHECK
```

退出码为 0 不等于测试真跑了的证伪项：
`test.db` 由 schema 实测生成（非空校验在配方内：文件不存在或 0 字节即抛错），
fixture 缺失时 base/types 等 DB 套件必然报错，`-s` 汇总与退出码双重校验。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/t/tntdb/1.4/conanfile.py | 主配方（autotools） |
| archives/t/tntdb/1.4/conandata.yml | 源码 URL + sha256（codeload + 官方归档双端点，CI 自动追加镜像回退） |
| archives/t/tntdb/1.4/manifest.yaml | 版本级 manifest |
| archives/t/tntdb/manifest.yaml | 软件级 manifest |
| archives/t/tntdb/1.4/test_package/ | test_tntdb.cpp + CMakeLists + conanfile + MANIFEST.yml |
| archives/t/tntdb/1.4/notes.md | 本文件 |

## 注意事项

- 本轮未执行 `git commit/push`、未创建 PR、未调用 GitCode 写接口；
  工作树保持未提交，等待 HMBS 真机验证。
- PR 正文测试数字留待真机 evidence 轮填写，不猜测。
| 16 | CI #83076 conan create 失败：test_package 9/10（仅 `decimal-scale` FAIL），上游仍 49/58（2026-10-10 CI 实测；真机预检同为 49/58，口径一致） | 双因：① 本配方消费者测试 bug：`t_decimalScale` 断言 `Decimal("19.95").exponent() == -2`，而上游 `Decimal::Parser::finish` 为 `_exponent += _eoff`（小数点前位数）、`toStringFix` 在 exponent 处插点，故 "19.95" 实为 mantissa "1995"+exponent 2，全平台必 FAIL（CI 日志仅此一项 CHECK FAIL，且无 DIAG 异常，即纯断言错误）；② 上游 9 项为 sqlite 驱动固有限制、非 OHOS 特有：`src/sqlite/statement.cpp` 中超 `LONG_MAX/INT_MAX` 的无符号量转 `setDouble`、Decimal 经 `getDouble()` 存 double、`setUnsigned64` 强转 int64，double 往返无法精确表示 ULONG/UINT64_MAX（回读为 `1.8446744073709552e+19`，`Value::get(unsigned long)` 抛）、Decimal 精度丢失、NaN 经 `sqlite3_column_bytes/blob` 文本回读为 null（`isNotNull` 断言）、float-max 游标全等、`Decimal(double::max)` 的 nearBy 与 `Utf8Codec::encode` 的 ustring 回读亦在该驱动路径内；上游 `make check` 从不执行该 runner（无 TESTS），故上游即如此。按 HMBS 纪律不跳过不断言：消费者 bug 修断言，上游 9 项保留真实 gaps（test_failure + 逐条日志证据） | ① `test_tntdb.cpp::t_decimalScale` 改为 `d.exponent() == 2 && d.toString() == "19.95"` 并注释语义来源（Parser::finish + toStringFix），10 CHECK 不变；② 上游 runner 与 gaps 逻辑不动（`_run_upstream_tests` 仍以 `-s` 汇总为唯一计数源，`hmbs_upstream.json` 落盘原样重发），MANIFEST 口径不变；notes 记档，待真机预检复核 10/10 + 49/58 口径 |
| 17 | CI #85029 conan create 仍失败：test_package ctest exit=0 Passed 却被判 0/10（consumer 上轮修复已生效，上游仍 49/58） | 本配方解析路径 bug：test()用 ctest --output-on-failure 并以 CHECK 行为唯一计数源；该标志在成功时抑制测试 stdout，全通过时输出无 CHECK 行，解析器见 0 CHECK 即报 passedCount=0 并 raise；上轮 9/10 反而可解析是因失败时 ctest 打印全部输出。二进制本身 10/10 通过（ctest Passed） | test_package/conanfile.py 切到 ctest -V -R test_tntdb（成败均打印测试输出），CHECK 解析不变仍为唯一计数源；marker command 同步更新。待真机预检复核 10/10 + 上游 49/58 |
| 18 | CI #85611 test_package consumer 仍 FAIL（line 403 raise；同 head 真机预检 passed），Buildbot API 502 无法拉取完整日志定位具体 CHECK | 差异定位：同一 HEAD 真机 10/10 而 CI-037 失败，唯一环境差异是 TMPDIR 隔离性——HMBS 真机注入任务独立 TMPDIR，CI worker 多构建共享同一 TMPDIR；消费者使用固定文件名 tntdb_consumer.db，并发构建会互删/互写导致 setup 或 DB CHECK 随机失败（table exists/missing/busy）。此为本配方测试代码的真实隍防缺陷，与上游无关 | test_tntdb.cpp改用随 PID 唯一的 DB 文件名（getpid 后缀），setup 加 drop table if exists kv 冪等，启动时 DIAG 打印 db 路径+pid 供下轮定位；10 CHECK 口径不变、不跳过任何用例。待真机预检+CI 复核 |
| 19 | CI #89106 test_package consumer 仍 FAIL（line 403 raise）：-V 输出中 10 个 CHECK 全 PASS、TNTEST_RESULT 10/10、ctest Passed，但 marker 读出 passedCount=0 | 真因为 ctest -V 给每行测试输出加数字前缀（1: CHECK PASS: ...），而解析器正则要求行首即 CHECK，10 行全部错过；--output-on-failure 失败时打印原始 stdout 无前缀，故上轮反考解析成功。二进制本身在 CI-034 上 10/10 通过，PID 隔离与共享文件冲突推测不成立 | test_package/conanfile.py 新增 _norm 函数消除可选的数字冒号前缀，CHECK/DIAG/TNTEST_RESULT 三处解析均走 _norm；计数仍唯来自 CHECK 行，口径不变。待真机预检+CI 复核 |
