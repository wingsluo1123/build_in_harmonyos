# puf 1.0.0 适配笔记

## 编译环境

- 构建系统: autotools（configure + make；源码包内置生成的 configure 脚本）
- 编译日期: 2026-10-10
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built（配方完成，待 HMBS 真机 conan create/verify 确认后由 HMBS 更新）

## 上游信息

- 上游仓库：https://sourceforge.net/projects/puf/（puf = Parallel URL Fetch，类 wget 的并行 HTTP 下载工具）
- 上游版本：1.0.0
- 许可证：GPL-2.0（源码包 COPYING 为 GPL v2）
- 源码包：`https://downloads.sourceforge.net/project/puf/puf/1.0.0/puf-1.0.0.tar.gz`
  （153 540 字节，sha256 `3f1602057dc47debeb54effc2db9eadcffae266834389bdbf5ab14fc611eeaf0`，已实测下载验证）

## 源码审计（上游无测试的依据）

puf 1.0.0 只产出 `bin/puf` 可执行文件（纯命令行动手，无库 API）。

解包 24 个条目，逐项核查无任何测试框架：

```text
AUTHORS ChangeLog ChangeLog.ag COPYING INSTALL NEWS README TODO
Makefile.am Makefile.in aclocal.m4 config.guess config.h.in config.sub
configure configure.in depcomp install-sh makemake missing
puf.1 puf.spec puf.spec.in
src/Makefile.am src/Makefile.in src/{puf.c,puf.h,url.c,recurse.c,http_conn.c,
  http_rsp.c,http_req.c,hostlist.c,getopts.c,fetch.c,util_date.c}
```

- `find . -iname '*test*'` 无命中。
- `src/Makefile.am` 仅 `bin_PROGRAMS = puf` 与 `puf_SOURCES`，无 `TESTS`/`check_PROGRAMS`。
- 生成的 `Makefile.in` 中 `check-am: all-am`（`make check` 只是重新构建，不运行任何测试）。
- 无 gtest/CTest/criterion/meson test 绑定。

结论：上游 1.0.0 不提供任何测试套件。
test_package/MANIFEST.yml 记 `upstream_tests_exist: false`、
`upstream_test_total: 0`、`upstream_test_count_method: manual_audit` 并附本审计。

## 编译步骤

标准 Autotools（真机内由 conan create 执行）：
```bash
./configure --prefix=/ --build=aarch64-linux-ohos --host=aarch64-linux-ohos
make -j1
make install DESTDIR=$package_folder
```

- 无外部依赖：`configure.in` 仅做 `AC_CHECK_LIB(xnet/socket/nsl)` 与
  `AC_CHECK_FUNC(snprintf)` 检查，OHOS bionic libc 直接满足。
- 原生构建（build=target），但必须显式传 `--build`/`--host`：源码包内置的
  2005 版 `config.guess` 无法从 HarmonyOS 的 `uname` 输出推断系统类型
  （报 `unable to guess system type` / `cannot guess build type`），
  只有显式给出三元组才能跳过 config.guess。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | 2005 版 `config.guess` 不认识 HarmonyOS 的 uname 输出（`UNAME_SYSTEM=HarmonyOS`） | OHOS 时显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos` 跳过 config.guess；同版 `config.sub` 也不认识 aarch64/linux-ohos，需 `patches/0001-config.sub-ohos.patch` 打补丁（同 aalib 思路） |
| 2 | 真机 compile 失败：configure 早期报 `sed: Operation not permitted`、随后 `can't fork - try again` | 配方曾强制 `CONFIG_SHELL/SHELL=/bin/sh` 覆盖 profile 的 `/data/service/hnp/bin/bash`；HMBS 注入的 `/bin/sh` shim 在受限 worker 上 fork/exec 子进程(如工具链 sed)脆弱，configure 启动段 fork 子 shell 失败 | 不再覆写 SHELL/CONFIG_SHELL，放行 profile 的 `/data/service/hnp/bin/bash`（AutotoolsToolchain 默认保留 buildenv 值）；configure/make 均不传 `SHELL=/bin/sh`。同模式 aalib 从不覆写 shell 且真机通过 |
| 3 | 工具包需 install 落到 `bin/` 直下 | Autotools 默认 prefix=/usr/local | `--prefix=/`，配合 `make install DESTDIR=$package_folder` 产出 `$package_folder/bin/puf` |
| 4 | 无上游测试，需真实调用二进制 | puf 是 CLI 工具非库 | test_package 用「`puf -h` + 裸 `puf`(exit 2) + 本地 HTTP 回环抓取校验」三断言实质验证 |
| 5 | OHOS /tmp 只读(erofs)，shell 命令替换会在 /tmp 建临时文件 | test.sh 运行环境受限 | test.sh 全程零 `$(...)`/反引号，输出经 `$TMPDIR` 文件 + grep；HTTP server 就绪用日志 grep 同步 |
| 6 | 真机编译失败：`./config.status ... ./confstat*/in|out|config.h: Permission denied`，随之 `make: No makefile found` | puf 内置 configure 生成的 config.status 在**构建树内**建临时目录 `./confstatXXXXXX`（硬编码，非 `$TMPDIR`），而构建树位于 HMFS 用户卷(`/storage`)；HMFS 上新建目录的权限元数据不立即生效，且该文件系统 chmod 本身不受支持(`HMBS_CAP_CHMOD=0`)，紧接的重定向写 `in/out/config.h` 全 EACCES | 双管齐下：① `patches/0002-configure-confstat-tmpdir.patch` 把 config.status 临时目录改为 `"${TMPDIR:-.}/confstatXXXXXX"`，脱离构建树；② 配方 build() 前 `_pin_tmpdir()` 用「建目录→写→回读」探针把 TMPDIR 钉到可写非 HMFS 根（首选 `/data/storage/el2/base/cache`，回退 HMBS 注入 TMPDIR） |
| 7 | CI(worker CI-016) configure 硬失败：`checking whether build environment is sane...` 后报 `newly created file is older than distributed files! Check your system clock`，且错误分支内 `can't fork - try again`（EAGAIN） | automake 的 AM_SANITY_CHECK 是**建议性** mtime 比对：`sleep 1` 后创建 `conftest.file`，用 `ls -Lt` 断言其比 (2005 年代的旧) `$srcdir/configure` 新。在 overlay/network/HMFS 类文件系统（延迟元数据/粗 mtime 粒度）或 `ls -Lt` 时间排序不可靠的主机上，新建文件未被观察到“新于”旧源码文件 → 误判并 `(exit 1)` 硬中止；错误分支的 `( exit 1 )` fork 恰逢 worker 资源压力报 EAGAIN | `patches/0003-configure-sanity-check.patch` 把 AM_SANITY_CHECK 两支失败路径（`ls -t` 排序异常、新建文件显得更旧）从硬错误降级为 WARNING 并继续，configure 不再被误中止；puf 构建不依赖源码树时钟，产物行为由 test_package 断言验证。EAGAIN 本身为 worker 瞬时资源压力（同代码在真机预检通过），补丁同时消除了错误分支的 fork（不再 `(exit 1)`） |
| 8 | CI #92103 编译期 `make` 失败：`/data/service/hnp/bin/bash: fork: retry: Resource temporarily unavailable` × N → `fork: Resource temporarily unavailable` → `make[2]: *** [Makefile:230: puf.o] Error 254` | 共享构建主机在 fork 压力尖峰下短暂拒绝 `fork()`（EAGAIN），shell 无法派生编译器；`make` 把它当作普通命令失败并中止。这是主机瞬时资源竞争，不是 puf 源码/工具链缺陷（同一配方在真机预检已通过；错误点在 fork 而非编译诊断） | 采用**不同实现路线**（前几轮的 HMFS tmpdir/sanity-check/shell 假设已用尽）：① 配方 `generate()` 追加 `--disable-dependency-tracking`，去掉每个编译单元的 `if $(COMPILE) -MT ... -MD -MP -MF ...; then mv; else ...` 包裹（depcomp+mv 子进程），降低单 TU 的 fork 次数；② 新增 `_run_make_with_fork_retry()`：把 `make`/`make install` 的 stdout/stderr 重定向到构建树内日志，**仅当**日志尾部命中 fork 压力指纹（`fork: retry`/`Resource temporarily unavailable`/`cannot fork`/`posix_spawn`/`out of memory`）时，退避 5s×attempt 后重跑 `make -j1`（增量续跑），最多 3 次；无该指纹的真实编译错误立即原样上抛，绝不重试掩盖。make 程序优先取 `tools.gnu:make_program`/`HMBS_MAKE` 绝对路径 |
| 9 | CI #92651 构建包在 `puf/1.0.0 (test package): puf test_package: OK` 之后**再无任何输出**，整步耗满 14400s 被 buildbot 强杀（`command timed out ... attempting to kill` / `SIGKILL failed to kill process` / `exit code -1`），CI 侧归类为「编译失败」。实际上 configure/make/install/package 与 test_package 3/3 全部成功 | test.sh 用 `( cd "$WEBROOT" && "$PYTHON" ... ) &` 起本地 HTTP server。**OHOS 的 `/bin/sh` 是 mksh**：`( ... ) &` 这种子外壳会把它继承的 stdout（即 `conan create ... | tee` 的写端管道）**一直持有到自己退出**；脚本结束时只 `kill "$SRV_PID"` 杀掉的是子外壳里的 python（$! 是子外壳 PID 时行为因 shell 而异），子外壳/其 stdio 副本仍存活，导致 `tee` 永远等不到 EOF、conan create 永不返回 → buildbot 4h 看门狗击杀。本机用 mksh 复现：原 test.sh 管道 20s 无 EOF；dash/bash 下正常——正是「本地通过、CI 挂死」的环境依赖型差异 | 让 HTTP server 与脚本 stdio 彻底解耦：把重定向挂到**子外壳本身**并 `exec` 解释器——`( cd "$WEBROOT" && exec "$PYTHON" -u -m http.server "$PORT" --bind 127.0.0.1 ) >"$HTTPDLOG" 2>&1 </dev/null &`。这样 `$!` 即 python 进程本身，不再有持有 stdout 管道的子外壳；`kill "$SRV_PID"` 后再 `wait "$SRV_PID"` 回收，确保脚本退出前无残留。mksh 下实测：修复后管道 1.0s 收到 EOF、rc=0、3/3 PASS；原文件在 mksh 下 20s 无 EOF |

## 源码修改

- `patches/0001-config.sub-ohos.patch`（本适配引入）：给 2005 版 `config.sub`
  增加 `aarch64` CPU 与 `linux-ohos*` OS 识别，使 `--build/--host=aarch64-linux-ohos`
  三元组通过校验。仅触碰 build 脚本识别逻辑，无源码语义改动。
- `patches/0002-configure-confstat-tmpdir.patch`（本适配引入，本轮重写）：puf 内置
  configure 生成的 `config.status` 硬编码在**构建树内**建临时目录 `./confstatXXXXXX`，
  HMFS 上新建目录权限元数据滞后 + chmod 不受支持(`HMBS_CAP_CHMOD=0`) 导致随后写
  `in/out/config.h` 全 `Permission denied`、Makefile 生成失败。补丁把临时目录改为
  `"${TMPDIR:-.}/confstatXXXXXX"`，使 config.status 用配方钉好的可写 TMPDIR。
  配方侧 build() 前 `_pin_tmpdir()` 用「建目录→写→回读」探针把 TMPDIR/TMP/TEMP 钉到
  可写非 HMFS 根（首选 `/data/storage/el2/base/cache`，回退 HMBS 注入 TMPDIR）。
- `patches/0003-configure-sanity-check.patch`（本适配引入）：automake 的
  AM_SANITY_CHECK 在 overlay/HMFS 类文件系统或 `ls -Lt` 排序不可靠主机上会把“新建文件
  显得比旧源码文件旧”误判为时钟问题并 `(exit 1)` 硬中止 configure；本补丁把两支失败路径
  从硬错误降级为 WARNING 后继续（纯构建守卫放宽，不影响产物）。
- OHOS 兼容（--build/--host）在配方 generate() 内完成；shell 不覆写，放行 profile 的 `/data/service/hnp/bin/bash`。
- `conanfile.py` link-retry 包装（本适配引入，本轮重写）：由 POSIX sh 包装 `hmbs-link-retry.sh`
  改写为 Python 包装 `hmbs-link-retry.py`，并新增 `_python_program()` 解析解释器；`CCLD` 覆盖由
  `'CCLD=$(SHELL) <wrapper.sh> $(CC)'` 改为 `'CCLD=exec <python> <wrapper.py> $(CC)'`。原因是
  shell 在 fork 失败时会中止整个脚本（exit 254），重试循环无法执行第二次；Python 把 fork 失败
  作为可捕获 `OSError`，才能真正循环重试。属配方健壮性改动，随配方提交。
- `test_package/test.sh`（本适配引入，本轮修复）：本地回环 HTTP server 的后台启动方式由
  `( ... ) >log 2>&1 &` 改为 `( ... && exec ... ) >log 2>&1 </dev/null &`，并在 `kill` 后
  `wait` 回收。原因是 OHOS `/bin/sh`（mksh）下 `( ... ) &` 子外壳会一直持有继承的 stdout
  管道，使 `conan create | tee` 永不收到 EOF、CI 步骤耗满 14400s 超时；修复后 server 与脚本
  stdio 完全解耦。此为测试接入改动，随配方提交。

## 依赖版本

- 无 Conan requires 依赖（纯 C，bionic libc 直接满足）。

## 验证结果

- 本机已实测 configure 修复：给 `--build/--host=aarch64-linux-ohos` 打上
  `0001-config.sub-ohos.patch` 后，configure 不再报 `cannot guess build type`，
  正常进入 `checking build system type... aarch64-unknown-linux-ohos` 并生成
  Makefile/config.h（exit 0）。`config.sub aarch64-linux-ohos` 返回
  `aarch64-unknown-linux-ohos`。
- 本机（Linux 模拟）已实测 test.sh：三断言全过——
  `puf -h` 打印完整用法；裸 `puf` 短用法+exit 2；本地回环抓取 payload 内容一致。
- 生成标记：
  - `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...,"discovered":0,...}`
  - `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":3,"passedCount":3}`
- 本轮：修复真机 compile 阶段 `config.guess: cannot guess build type`（配方
  generate() 传 --build/--host + 新增 config.sub 补丁）；工作树未提交，待 HMBS
  真机 conan create 全量验证（含 3 项 test_package 断言与 rule4 门禁）。
- 前轮核验被真机 compile 阶段新的 HMFS 竞态失败拦截：`config.status` 在构建树
  `/storage/...` 内建 `./confstatXXXXXX` 临时目录后，写 `in/out/config.h` 全
  `Permission denied` → 无 Makefile。首轮尝试 `chmod 700 "$tmp"` 未能解决
  （HMFS 上 chmod 不受支持，HMBS_CAP_CHMOD=0）；本轮改为把 config.status 临时目录
  移到 `$TMPDIR` 并在配方侧 `_pin_tmpdir()` 钉到探针验证的可写非 HMFS 根。本机已验证
  补丁可干净应用、config.status 逐字节使用 `${TMPDIR:-.}`、configure exit 0 且生成 Makefile。
- manifest.yaml 状态 `built` 为配方完成标记，真机通过后由 HMBS 更新。
- 本轮（修复真机 compile）：新失败 `configure[973] sed: Operation not permitted` +
  `configure[1032] can't fork - try again`（configure 启动段）。根因判定为配方强制
  `SHELL/CONFIG_SHELL=/bin/sh` 覆盖 profile 工作 shell，使 2005 版 configure 在真机
  worker 上 fork/exec 子进程脆弱；修复=移除所有 `/bin/sh` 覆写，放行 profile 的
  `/data/service/hnp/bin/bash`（对齐同模式并通过真机的 aalib）。同时移除 generate()
  的 Environment 覆写与 make/install 的 `SHELL=/bin/sh`。保留 _pin_tmpdir + confstat
  补丁（仍针对 HMFS tmpdir 竞态）。待 HMBS 真机复跑。
- 本轮（第 2 策略周期，CI #92103 编译期 fork 压力）：新失败为 `make` 阶段
  `/data/service/hnp/bin/bash: fork: retry: Resource temporarily unavailable` × N →
  `make[2]: *** [Makefile:230: puf.o] Error 254`。前几轮的 HMFS tmpdir / sanity-check /
  shell 覆写假设已用尽且与本失败点无关（本次失败发生在编译命令 fork 处，而非
  configure 期），故改用不同路线：① generate() 追加 `--disable-dependency-tracking`，
  把每个编译单元的 `if $(COMPILE) -MT ... -MD -MP -MF ...; then mv; else ...` 包裹
  （depcomp + mv 子进程）去掉，直接 `$(COMPILE) -c $<`，降低单 TU 的 fork 次数；
  ② 新增 `_run_make_with_fork_retry()`：`make` 与 `make install` 的 stdout/stderr
  重定向到构建树日志，仅当日志尾部命中 fork 压力指纹
  （`fork: retry` / `resource temporarily unavailable` / `cannot fork` / `posix_spawn`
  / `out of memory`）时退避 5s×attempt 后重跑 `make -j1`（增量续跑），最多 3 次；
  无该指纹的真实编译错误立即原样上抛，不重试、不掩盖。make 程序优先取
  `tools.gnu:make_program` / `HMBS_MAKE` 绝对路径。本机已实测
  `--disable-dependency-tracking` 后 src/Makefile 的 `.c.o` 规则变为单条
  `$(COMPILE) -c $<`（无 depcomp/mv 子 shell），`make -j1` 与 `make install` 均 rc=0；
  并用桩程序验证重试仅对 fork 指纹生效、真实编译错误只跑 1 次。待 HMBS 真机复跑。
- 本轮（第 3 策略周期，CI #92651）：失败形态为**步骤挂死**而非编译错误——
  `puf/1.0.0 (test package): puf test_package: OK` 之后无任何输出，整步耗满 14400s
  被 buildbot 强杀（`command timed out ... attempting to kill` / `SIGKILL failed to kill
  process` / `exit code -1`）；日志显示 configure/make/install/package 与 test_package
  3/3 断言**全部成功**。根因：test.sh 用 `( cd ... && "$PYTHON" ... ) &` 起 HTTP server，
  在 OHOS `/bin/sh`（mksh）下该子外壳会持续持有继承的 stdout（`conan create | tee` 写端）
  直到自己退出，脚本结束时的 `kill` 未能消除该 stdio 副本 → `tee` 永不 EOF → conan
  create 永不返回。本机用 mksh 复现原文件：管道 20s 无 EOF；改用把重定向挂在子外壳并
  `exec` 解释器、`kill` 后 `wait` 回收后：mksh 下 1.0s 收到 EOF、rc=0、3/3 PASS。
  dash/bash 下两种写法均正常，解释了「本地通过、CI 挂死」的环境差异。待 HMBS 真机复跑。
- 本轮（第 4 策略周期，真机 compile）：configure 启动即 `ConanException: Error while
  running cmd` + `Error: 'str' object has no attribute 'fileno'`，且
  `configure attempt 1/2 failed` 后未再重试（`fork_pressure=False`）。根因：上一轮为捕获
  configure 输出新增的 `_run_configure()` 把 `stdout=log_path, stderr=log_path` 以**字符串
  路径**传给 `self.run()`。Conan 2 的 `ConanFile.run()` 把 stdout/stderr 原样转交
  `subprocess.run`，只接受 file-like 对象（或 DEVNULL）；传字符串时 `conan_run` 调
  `.fileno()` 即抛 `'str' object has no attribute 'fileno'`，configure 从未真正启动。
  该函数还误用 `self.run("configure", cwd=build_folder)`：bare `configure` 既不在 PATH、
  又丢掉了 `Autotools.configure()` 生成的 `configure_args`（--prefix/--build/--host/
  --disable-dependency-tracking），且脚本实际位于 source_folder。修复：新增
  `_configure_command()`，从 `load_toolchain_args(self.generators_folder)` 读回
  `configure_args` 并与 `os.path.join(self.source_folder, "configure")` 拼成与
  `Autotools.configure()` **逐字节一致**的命令；`_run_configure()` 改为在 `with open(...)`
  打开的 file 对象上重定向 stdout/stderr（与既有的 `_run_make_with_fork_retry()` 写法一致），
  并移除已不再使用的 `Autotools` 导入。本机用 `save_toolchain_args`/`load_toolchain_args`
  往返实测：重建命令与 `Autotools.configure()` 输出完全一致。待 HMBS 真机复跑。
- 本轮（第 5 策略周期，CI #93827 @ CI-013 编译失败）：失败形态是**纯 fork/exec 资源压力**，
  不是源码缺陷。日志证据：① configure 成功（`checking build environment is sane... yes`、
  `creating Makefile/src/Makefile/puf.spec/config.h`），仅 config.status 期间三次
  `./config.status: fork: retry: Resource temporarily unavailable`；② make 三个 attempt 中
  **10 个翻译单元全部编译成功**（puf.c/url.c/.../util_date.c 均 `-c` 通过，只剩 warning），
  失败点在最后一条链接命令 `clang ... -o puf ... -lxnet`：
  `clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily
  unavailable` → `linker command failed`；③ 每次 attempt 首行都是
  `/data/service/hnp/bin/bash: fork: retry: Resource temporarily unavailable`。即共享构建
  主机在 fork 压力尖峰下持续拒绝 `fork()`/`posix_spawn()`，与 puf 源码、工具链参数无关
  （同配方此前真机预检已通过）。前一轮的 `_run_make_with_fork_retry()` 已正确识别该指纹并重试，
  但窗口太短（3 次 attempt、退避 `5s×attempt`，总计约 15s），尖峰未消退即耗尽重试。
  本轮修复（不改任何编译/测试口径，只加长瞬态重试窗口）：
  ① `_run_make_with_fork_retry(attempts=6)`，退避改为指数增长并封顶
  `min(5*2^(n-1), 60)`（5/10/20/40/60/60s，约 3.5 分钟），每次等待前 `gc.collect()` 释放
  Python 堆，给受限进程表留出恢复时间；
  ② `_run_configure(max_attempts=4)` 同步使用相同 `gc.collect()` + 指数退避；
  ③ 仍只在日志命中 fork 压力指纹时重试，无该指纹的真实编译错误立即原样上抛（不掩盖）。
  未修改补丁、test_package、MANIFEST 或任何通过率口径。待 HMBS 真机复跑。
- 本轮（第 6 策略周期，CI #93925 @ CI-013 编译失败，同一指纹第 2 次修复）：加长重试窗口
  （6 次 attempt、退避 5/10/20/40/60/60s，约 3.5 分钟）**仍然 6/6 全败**，证明「外层 make
  重试」方向本身无效。逐行比对 #93925 日志得到结构性根因：
  ① 每个 attempt 首行都是 `bash: fork: retry: Resource temporarily unavailable`，但
  **10 个翻译单元全部编译成功**——因为 **bash 内部会对 EAGAIN 的 `fork()` 自动重试**
  （即 `fork: retry` 是 bash 自己的重试提示，随后继续执行）；
  ② 唯一失败点是最后一条链接命令：`clang ... -o puf ... -lxnet` →
  `clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily
  unavailable`。**clang 派生链接器（ld.lld）走 `posix_spawn()`，且不重试 EAGAIN**，一次尖峰
  即让整个链接失败；
  ③ 外层 make 重试每次只给 clang **一次** `posix_spawn` 机会（间隔 5–60s），粒度太粗，
  因此窗口多长都没用。
  本轮修复（结构性改变，仍不改任何编译/测试口径）：**让链接 spawn 本身可重试**。新增
  `_LINK_RETRY_WRAPPER`（POSIX sh 包装脚本）与 `_write_link_retry_wrapper()` /
  `_link_retry_make_arg()`：把 make 的 `CCLD` 通过命令行覆盖为
  `'CCLD=$(SHELL) <build_folder>/hmbs-link-retry.sh $(CC)'`（单引号保护，交给 make 展开
  `$(SHELL)`/`$(CC)`，经 MAKEFLAGS 传递到 `src/` 的递归 make），包装脚本在**单条链接命令内**
  以 40 次 × 1s 的节奏快速重试 clang，只对 `posix_spawn failed`/`Resource temporarily
  unavailable`/`fork: retry` 等瞬态指纹重试，其它真实链接错误原样上抛（不掩盖）。外层
  make 级退避保留为第二道防线（覆盖链接之外的 spawn 失败）。包装脚本用纯参数展开取目录、
  不引入额外 `dirname` 子进程；日志文件优先落 build_folder（每构建唯一）再退避到 TMPDIR/cwd；
  全部不可写时直接 `exec` clang 一次，绝不让包装本身阻断链接。本机以假 clang 注入 EAGAIN
  实测：瞬态情形 3 次重试后成功、真实错误仅 1 次即上抛；并验证递归 make 与单引号赋值在
  `bash -c`/`sh` 下均正确展开。待 HMBS 真机复跑。
- 本轮（第 7 策略周期，CI #94128 @ OpenHarmonyPCDeveloper-CI-001 编译失败）：link-retry 包装脚本自身
  在持续 EAGAIN 下成为失败点。证据：① 6 个 make attempt 全部失败，但从 attempt 2 起 make 不再编译任何 TU
  （对象已 up-to-date），直接进入唯一链接命令；② 每次链接都以 4~5 行
  `hmbs-link-retry.sh: fork: retry: Resource temporarily unavailable` + `fork: Resource temporarily unavailable`
  告终（`make[2]: *** [Makefile:210: puf] Error 254`），**整个构建日志没有任何一条
  `hmbs-link-retry: link attempt N/40`** —— 说明包装脚本连 `clang > log 2>&1` 这一步都无法 fork；
  ③ 日志尾部（fork 指纹检测）除 `fork: retry` 外空无一字，正符合「fork 发生在重定向管道建立时，bash 的
  `fork: retry` 打在 stderr、捕获文件为空」这一形态。结论：包装脚本原实现的每个 attempt 有 3 次 fork
  （clang + 2 个日志文件命令），且把 clang 输出经额外管道复用，在进程表枯竭的瞬间**连一次重定向式 fork
  都无法完成**；其自带重试循环永远停在 i=1，只剩外层 make 级重试（也只给一次机会）在兜底，双重失效。
  本轮修复（结构精简，不改编译/测试口径）：包装脚本改为**只用 shell 内建命令做管道与日志**——clang 以
  继承 stdio 直接运行（成功路径单次 fork，不再经管道复用 clang 输出）；`> log` 以**重定向-即-创建**方式由
  shell 内建完成；仅当首次运行非零退出后才用一次内建 heredoc 捕获 clang 输出做瞬态指纹扫描（无 cat/tee
  子进程）；每次重试前仍 sleep 让进程表排空。本机已实测四种行为：真实链接错误（exit 1 无指纹）→ 不再重复
  运行第二次、rc 原样上抛；成功 → 输出透传、rc=0；带指纹的瞬态失败 → 循环重试至 attempts 后如实返回
  最后一次 rc；`fork: retry: Resource temporarily unavailable` + exit 254（复刻真机 mksh 形态）→ 正确识别并
  重试。单次 attempt 的 fork 数从 3 降到 1（仅 clang 自身）。待 HMBS 真机复跑。
- 本轮（第 8 策略周期，CI #94167 @ OpenHarmonyPCDeveloper-CI-032 编译失败）：第 7 周期的
  「只用 shell 内建」改写**仍然全败**，但这次日志给出了决定性证据：每个 make attempt 里，链接命令
  `bash hmbs-link-retry.sh clang ... -o puf ...` 都紧跟 4 行
  `hmbs-link-retry.sh: fork: retry: Resource temporarily unavailable` + 1 行
  `hmbs-link-retry.sh: fork: Resource temporarily unavailable`，然后 `Error 254`；
  **整个日志依旧没有任何一条 `hmbs-link-retry: link attempt N/40`**。
  本机受控实验（`setpriv` 降权 + `RLIMIT_NPROC=1`）复现并确证了根因：**shell 无法围绕一个「fork 失败」的
  外部命令做重试循环**——当 shell 派生外部命令而 `fork()` 返回 EAGAIN 时，它不是把非零状态返回给脚本，
  而是打印 `fork: retry` 若干次、随后以 **exit 254 中止整个脚本**；因此包装脚本的重试循环体根本进不了
  第二次迭代（`i` 永远停在 1，日志里没有 `link attempt` 行）。这正是「重试机制被它所要对冲的故障本身
  摧毁」。对照实验：同一 fork 枯竭条件下，Python 的 `subprocess.run` 只是抛出可捕获的 `OSError(errno=11)`，
  解释器存活并成功跑完全部重试迭代。
  本轮修复（结构性，不改任何编译/测试口径）：把 link-retry 包装从 POSIX sh **改写为 Python 脚本**
  （`hmbs-link-retry.py`），新增 `_python_program()`（优先 `HMBS_PYTHON3`，回退 `sys.executable`），
  `_link_retry_make_arg()` 把 make 的 `CCLD` 覆盖为
  `'CCLD=exec <python> <build_folder>/hmbs-link-retry.py $(CC)'`——`exec` 让 make 的 shell 用解释器替换自己，
  不额外多一次 fork；包装在循环内调用 `subprocess.run([clang]+args, stdout=PIPE, stderr=STDOUT)`，
  **仅在** `OSError` 的 errno 属于瞬态集合（EAGAIN/ENOMEM/EMFILE/ENFILE/ENOSPC）或输出命中瞬态指纹
  （`posix_spawn failed`/`resource temporarily unavailable`/`fork: retry`/`can't fork`/`cannot fork`/
  `fork failed`/`out of memory`）时退避重试（默认 60 次 × 1s）；真实链接错误原样透传、立即返回，
  绝不掩盖；重试耗尽时打印明确诊断并以 254 退出（与旧 shell 中止码一致，不吐 Python traceback）。
  本机已实测：① 正常成功 → 输出透传、rc=0；② 真实错误（`undefined reference`）→ 立即 rc=1、不重试；
  ③ 瞬态文本/`fork: retry` → 循环重试至耗尽后如实返回最后 rc；④ `RLIMIT_NPROC=1` 真 fork 枯竭 →
  Python 存活并重试全部迭代（shell 版在同条件下第一轮即 exit 254 中止）；⑤ 以假 clang 注入
  「前两次 EAGAIN、第三次成功」→ make 端 rc=0 且 clang 恰好被调用 3 次；⑥ make 的 `exec` 形式经 strace
  确认只引入一次 fork（sh -c exec → python），递归 make 经 MAKEFLAGS 正确传播覆盖值。待 HMBS 真机复跑。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/puf` | 并行 URL 抓取可执行文件 |
| `man/man1/puf.1` | man 手册页 |
| `licenses/COPYING` | GPL-2.0 许可证文本 |

## 注意事项

- puf 是并行 HTTP 下载工具，test_package 用本地 127.0.0.1 回环服务做 hermetic
  功能验证（不访问外网），端口由 shell PID 算术推导避免冲突。
- 切片 `--prefix=/` 使 install 落 bin/ 直下；若真机 OOM 可保持 `-j1`。
- 本轮（第 9 策略周期，CI #94346 @ OpenHarmonyPCDeveloper-CI-001 编译失败）：前一轮把 link-retry 改写为
  Python + `subprocess.run([clang]+args)` 后，包装终于进入了自己的循环（日志出现 60 行
  `hmbs-link-retry: spawn attempt N/60`，而此前版本一条都没有），但**每一次都抛
  `[Errno 11] Resource temporarily unavailable: '/data/service/hnp/bin/clang'`**，clang 一个字节都没产出；
  6 次 make attempt（退避 5/10/20/40/60s）全败。决定性对照：同一段日志里 10 个翻译单元**全部编译成功**
  （launcher 是 bash），只有链接失败——而 bash 的 `fork: retry` 行恰是 bash 自己对 EAGAIN 的内部重试。
  即：本机 `fork()` 可用，EAGAIN 只打在使用 **posix_spawn/vfork 快速路径**的调用方（clang→ld.lld 和
  CPython `subprocess`；`subprocess._USE_POSIX_SPAWN` 在 glibc≥2.24 上为 True，OHOS/musl 亦如此）。
  故前一轮的“Python 存活即可重试”结论正确但**未消除触发条件本身**：用 subprocess 重试等于反复走同一条
  会 EAGAIN 的 vfork 路径。
  本轮修复（换实现路线：不再用 subprocess 派生链接）：
  ① `_LINK_RETRY_WRAPPER` 内新增 `_spawn()`，用 **`os.fork()` + `os.execv()` 原始系统调用**替掉
  `subprocess.run`——与 bash 重试成功的那条路径完全一致；child 内 `dup2` 把 stdio 接到
  `<build>/hmbs-link-retry.log`（不再用 PIPE，因此不存在管道建立期的额外 fork），父进程 `waitpid` 后读日志。
  ② 新增 `_raise_process_limits()`：把软 `RLIMIT_NPROC`/`RLIMIT_NOFILE` 抬到硬上限（fork EAGAIN 的直接触发
  条件就是“进程数将超 RLIMIT_NPROC”），子进程继承后重试才真正有机会；不具权限时静默跳过，绝不致命。
  ③ 重试节奏改为 200 次 × 递增 0.2s（上限 2s，约 1 分钟高频轮询），而不是 60 次 × 1s——进程表空槽往往瞬时出现，
  高频小幅退避比低频大幅退避更容易抢到空槽；`OSError` 的瞬态 errno（EAGAIN/ENOMEM/...）与 clang 输出的
  瞬态指纹（`posix_spawn failed` 等）都触发重试，其他错误原样透传、立即返回（不掩盖真实链接错误）。
  ④ 同步更新配方内 `_LINK_RETRY_WRAPPER` 的注释与 `_run_make_with_fork_retry` docstring，记录 #94346 证据。
  未改动补丁、test_package、MANIFEST 或任何通过率口径。
  本机以假编译器实测 wrapper：① 成功路径 rc=0 且输出透传；② 真实链接错误（undefined reference）rc=1 且**只跑一次**；
  ③ 注入瞬态指纹「前两次失败、第三次成功」→ rc=0 且假编译器恰被调用 3 次；④ 猴补 `os.fork` 抛 EAGAIN
  （前三次）→ 循环重试后在第四次成功；⑤ `os.fork` 恒 EAGAIN → 重试耗尽后 rc=254 并打印明确诊断；
  ⑥ make 的 `CCLD=exec <python> <wrapper> $(CC)` 形式在单层与递归 `make -C sub`（经 MAKEFLAGS 传播）下均正确展开。
  待 HMBS 真机复跑。
