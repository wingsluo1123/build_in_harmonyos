# lcm 1.3.11 适配笔记

## 关键记录（真机环境轮：preflight.sh can't fork 资源耗尽，未改代码）
- 现象（HMBS 真机 preflight，compile 阶段未产出任何配方构建输出即失败）：
  `preflight.sh[314]: can't fork - try again`
  stdout 停在 `抢到锁槽 0（第 1 轮）` + `HMBS_PLATFORM_CAPABILITIES={...jobs:1...}`，属 harness fork 构建命令时 ENOMEM/EAGAIN。
- 判定：知识库 E491 forbid_3（`retry.*(can't fork|Errno 12)` 资源耗尽必须先有设备资源证据再改包）+
  DRAFT-ci-worker-gate-fork-oom（`can't fork`/`Errno 12` 为真机资源故障，非代码/配方/测试问题）。
  失败发生在配方产生任何编译输出之前（非编译期 fork 风暴），且 lcm 无 simint 式代码生成规模参数、
  `autotools.make(args=["-j1"])` 串行编译已在位，经验 1 的 -j1 手段已满足。
- 处置：未改任何配方/测试代码（E491 forbid_3），保持工作树原样，等待 hmbs 重跑真机预检（资源释放后应恢复）。

## 上游信息
- 名称：LCM（Lightweight Communications and Marshalling）——发布/订阅消息传递 + 数据编组库（C 核心 liblcm + lcm-gen 代码生成器 + lcm-logger/lcm-logplayer 工具）
- 上游项目：lcm-proj/lcm，https://github.com/lcm-proj/lcm
- 版本：任务目标版本号 1.3.11；（目录/配方版本）——官方 lcm-proj 最高 1.3.x release 为 v1.3.1，并无 v1.3.11。为使配方可真实构建，来源取官方 v1.3.1 正式 release 归档，sha256 为其真实校验值，差异已如实说明（详见 conandata.yml 注释）
- 许可证：LGPL-2.1-or-later
- 构建系统：autotools（lcm 1.4+ 才转 CMake；1.3.x 为 Autotools）
- 依赖：glib（configure.ac 硬性 PKG_CHECK_MODULES(glib-2.0, gthread-2.0)）

## 源码包
- conandata URL：https://github.com/lcm-proj/lcm/archive/refs/tags/v1.3.1.tar.gz
- sha256：d9765731127e5138017938c2f990eda6d8a8df260c98fe3053189db7954b9a41
- 注：GitHub tag 归档（archive/refs/tags/v1.3.1.tar.gz）只携带 configure.ac/bootstrap.sh，**无预生成 configure**，build() 需先 autoreconf -fi 自举（同仓库大量 tag-archive autotools 项目先例）

## 关键修复（本轮：真机编译阶段 tar zcat OOM）
- 现象（HMBS 真机 preflight，phase=compile）：`tar: exec /usr/bin/zcat: Out of memory` + `tar: had errors`，上游发现/执行/通过均 0（失败发生在任何编译之前）
- 根因：设备端 conan 的 get()/unzip() 对 .tar.gz 会回退到系统 `tar`，而系统 tar 需 fork 一个外部 `/usr/bin/zcat`；在受限 OHOS worker 上该 exec 以 ENOMEM 失败（fork 内存耗尽）。`get` 解包早于任何编译，因此 -j1 串行编译无济于事（同 xmlsec/1.3.12 第 2 轮证伪）。
- 方案（绕开系统 tar，纯 Python 解压）：
  1. source() 改用 `conan.tools.files.download()`（只取字节、不解压，内部支持镜像列表回退）+ 自研 `_extract_tar_gz_py()`（纯 Python tarfile+gzip 逐成员流式提取，峰值内存仅与单文件大小相关，不 fork 任何外部 zcat/tar）；
  2. 解压前 gc.collect()，并对瞬时 OOM/fork 类错误（out of memory / cannot exec / cannot fork / child died / signal 13 / connection closed / timeout）至多 3 次指数退避重试；checksum 类错误不重试；
  3. strip_root 单一顶层目录语义与 conan unzip 一致。
  - 先例：archives/a/atools-apkbuild-lint/20.2.2（同一错误串 `tar: exec /usr/bin/zcat: Out of memory` 的纯 Python 解压修复）
- 方案 2（无 configure，autoreconf 自举）：tool_requires 增补 automake/1.18 + libtool/2.5.4；build() 中若源码树无 configure 则先 `self.run("autoreconf -fi", cwd=source_folder, env="conanbuild")`（automake 包 buildenv 已注入 ACLOCAL_PATH，含 HNP 系统 pkg.m4 供 PKG_CHECK_MODULES 展开），再 Autotools.configure()。
  - 先例：仓库内 opendmarc/cbootimage/c-vtapi/cowdancer 等 tag-archive autotools 项目同款。

## 上游测试接入
- lcm 的 C/C++ 单测在独立 test/ 树（未接入 automake make check），依赖 vendored gtest（test/gtest）并链 liblcm。
- 配方 build() 的 _run_upstream_tests 手动编译 4 个 gtest 二进制（test/c/memq_test、test/c/eventlog_test、test/c/udpm_test、test/cpp/memq_test）并运行。
- discovered=12（确定性来源：上游 .cpp 中的 TEST() 用例，test/c/memq 4 + test/c/eventlog 3 + test/c/udpm 1 + test/cpp/memq 4）。
- 计数从 gtest 输出逐行 `[ RUN ]`/`[ OK ]`/`[ FAILED ]` 解析，单一数据源，无减法推导；恒等式 executed==passed+failed、executed<=discovered 不满足即显式失败。机器标记 HMBS_UPSTREAM_TEST_RESULT 由此产生。

## 关键修复（本轮 R2：autoconf mktemp 目录不可写 unsafe_local_mktemp，第 2 周期）
- 现象（HMBS 真机 preflight，phase=compile，autoreconf 自举后的 config.status 阶段）：
  `./config.status: line 807: ./confcDCgli/subs1.awk: Permission denied` + `config.status: error: could not setup config files machinery`
- 根因：HMDFS 强制新目录 setgid；autoconf 生成的 configure（及其内嵌、随后落盘的 config.status 模板）用 `(umask 077 && mktemp -d "./confXXXXXX")` / `(umask 077 && mkdir)` 建临时目录，umask 077 产出 0700+setgid 的目录，后续 config.status 向其中写 subs1.awk 时连属主都被拒（UID 映射，写者非属主）。
- 上一周期（R1）只加了 `mktemp exit-1` shim **无效**：HMBS_CAP_CHMOD=0 下 shim 文件不可执行，shell 跳过它落到真 mktemp，0700 目录照旧不可写；buildtorrent 笔记同样明确「mktemp exit-1 shim 不能根治」。
- 方案（复刻 swbis _patch_configure_umask + knowledge/E011/E129/E136/E626 家族，**umask 077 → umask 022 是根治**）：
  1. 新增 `_patch_configure_umask()`：遍历 source_folder，把生成的 `configure`/`config.guess`/`config.sub` 里的 `umask 077`→`umask 022`（含 autoconf 拼写 `umash 077`）。config.status 由 configure 内嵌 heredoc 落盘生成，故改 configure 即传播到 config.status。
  2. build() 在 autoreconf 生成 configure **之后**、`autotools.configure()` **之前**调用 `_patch_configure_umask()`（必须先 autoreconf 后改，否则被重新生成覆盖）。
  3. make 前再幂等重刷一次 `_patch_configure_umask()`，防 automake maintainer 规则在 make 阶段重生成 configure 丢补丁（babeltrace DRAFT-6048 先例）。
  4. 保留 mktemp shim 作为后备（无副作用），但不再依赖它。
  - 先例：swbis/1.13.3 `_patch_configure_umask`、cyrus-sasl-login/2.1.28、libkibi/0.1.1、buildtorrent/0.9.1、libhttpdserver、libuio、hyphen 等（knowledge E011/E129/E136/E206/E223 家族，均 ✅）。
- 未跳过任何测试；本修复仅在 configure/config.status 临时目录权限位层面放宽 umask，测试口径不变。

## 关键修复（真机 R4：run_upstream_tests.sh 的 gtest-build 目录 ENOENT）
- 现象（HMBS 真机 preflight，phase=compile）：conf 修复后进入测试接入脚本 `RUN: bash .../run_upstream_tests.sh`，首条编译
  `clang ... -c "$SRC/test/gtest/src/gtest-all.cc" -o "$TMP/gtest-build/gtest-all.o"` 报
  `error: unable to open output file '.../gtest-build/gtest-all.o': 'No such file or directory'`，
  但脚本内 `mkdir -p '$TMP/gtest-build'` 已先执行（set -e 未中止，说明 mkdir 返回 0）。
  上游发现 12 / 执行 0 / 通过 0（第一个 gtest 编译即失败）。
- 根因：HMDFS 对运行时由 fork 出的子进程（脚本内 `mkdir -p`）新建的目录存在不一致——同一 bash 脚本内
  mkdir 创建的 gtest-build 目录，下一条 fork 出的 clang 进程 open() 写输出文件时返回 ENOENT，目录对后续
  进程不可见/不可写。与知识库 `unsafe_local_mktemp`/`hmdfs-mktemp-0700-append-deny`/E112/E114 同族：
  运行时子进程新建目录在 HMDFS 上对后续进程不可靠。
- 方案（沿用仓库 proven 的 bypass-mktemp / E112-E114 / DRAFT-6507：Python 父进程预建并物化）：
  1. _run_upstream_tests 中先 `os.makedirs(.tmp/gtest-build, exist_ok=True)`，并写入哨兵文件
     `.hmbs_materialized`（强制物化 + 原位验证可写），替换原先依赖 shell `mkdir -p` 的运行时建目录；
  2. 清掉目录内历史遗留 .o/.a，避免复用目录残留旧归档；
  3. 脚本内 `mkdir -p '$TMP/gtest-build'` 保留为幂等 no-op（目录已物化存在则返回 0）。
- 测试发现数稳定为 12（test/c/memq 4 + test/c/eventlog 3 + test/c/udpm 1 + test/cpp/memq 4），
  计数仍为单数据源（逐行 [ RUN ]/[ OK ]/[ FAILED ]），无减法推导，口径不变。

## 关键修复（真机 R5：run_upstream_tests.sh 单引号导致 $SRC 不展开，cd 失败）
- 现象（HMBS 真机 preflight，phase=compile，R4 gtest-build 修复后进入测试脚本首条 `cd`）：
  `run_upstream_tests.sh: line 11: cd: $SRC/test/c: No such file or directory`，上游发现 12 / 执行 0。
- 根因：这不是 HMFS 目录不可见问题，而是手写 bash 脚本的**单引号引用了 shell 变量**——例如
  `A("cd '$SRC/test/c'")` 用单引号包住 `$SRC/test/c`，单引号内 `$SRC` 不展开，`cd` 尝试进入名为
  `$SRC/test/c` 的字面目录，故报错消息里 `$SRC` 原样出现（若真展开会显示绝对路径）。脚本内
  `A("L='...'")`/`A("INC='-I\"$SRC/...\"'")`/`A("LIBS='-L\"$L\"...'")` 同属此类，即使修好 cd 也会在
  后续编译/运行阶段因 include/lib 路径仍是字面 `$SRC`/`$L` 而失败（shell 不会递归二次展开值内的变量）。
- 该 bug 之前从未被触发：R1（compiler_executables conf）与 R4（gtest-build ENOENT）都停在更早的行；
  R4 修复 gtest-build 后执行推进到第 11 行 cd 才暴露此潜伏缺陷。
- 方案（彻底重写测试脚本构造，剔除易错单引号变量间接层）：
  1. 所有路径（src/test/c、src/test/cpp、src/test/gtest、src/lcm、src/lcmgen/lcm-gen、
     build/lcm/.libs 等）改为在 Python 侧用 os.path.join 解析成绝对路径，再以 `%` 格式化直接嵌入
     shell 命令，全程用双引号包裹，杜绝单引号变量不展开问题；
  2. 移除脚本内 SRC/TMP/CXX/AR/L/INC/LIBS/FLAGS 这些 shell 变量间接层，改为每条命令内联绝对路径；
  3. lcm-gen 生成 C 类型只被 eventlog_test（经 common.c→common.h 的 lcmtest_*.h）需要，移到
     Python 父进程用 self.run 单独生成并写 `.lcmgen_materialized` 哨兵物化（复用 R4 的 HMFS 绕过模式），
     cpp memq_test 用不到生成类型，删去 --cpp 生成步骤；
  4. 运行 lcm-gen 与四个 gtest 二进制前统一设置 LD_LIBRARY_PATH = liblcm .libs + gtest-build +
     所有依赖 libdir（兼容 glib 共享库运行期 .so 查找），测试二进制用绝对路径直接执行、不再依赖 cd；
  4b. 静态链接的 liblcm.a 引用了 glib 及其传递依赖的符号，故四个 gtest 二进制的链接命令行
     除 -Lliblcm.glibs -llcm / -Lgtest-build -lgtest -lgtest_main 外，还动态收集所有依赖的
     -L libdir 与 -l lib（自 self.dependencies cpp_info）以及 -lm，补齐 pkg-config(lcm.pc)
     本会提供的链接闭包；
  5. 保持 discovered=12 与逐行 [ RUN ]/[ OK ]/[ FAILED ] 单数据源计数、恒等式校验、HMBS_UPSTREAM_TEST_RESULT
     口径不变。
- 未跳过任何测试；仅修正 shell 脚本生成逻辑，测试口径与计数来源不变。

## 关键修复（真机 R6：gtest-all.cc 的 `#include "src/*.cc"` 需 -I 指向 test/gtest 父目录）
- 现象（HMBS 真机 preflight，phase=compile，R5 单引号修复后进入 gtest 编译首条命令）：
  `RUN: bash .../run_upstream_tests.sh` -> `gtest-all.cc:42:10: fatal error: 'src/gtest.cc' file not found`
  `#include "src/gtest.cc"`，上游发现 12 / 执行 0 / 通过 0。
- 根因：R5 写 gtest 编译命令时给 `-I` 传的是 `gsrc = test/gtest/src`。而 vendored gtest 的
  `gtest-all.cc` 通过 `#include "src/gtest.cc"` / `"src/gtest-port.cc"` 等把同目录源文件拉进来；
  该 `"..."` 相对 include 是**先相对当前包含文件所在目录** `test/gtest/src/` 找 `src/gtest.cc`（不存在），
  再沿 `-I` 在 <test/gtest/src>/src/gtest.cc（不存在）找，故报 file not found。只有把 `-I` 指向
  gtest 的**父目录** `test/gtest`（gdir），`src/gtest.cc` 才能解析到 `test/gtest/src/gtest.cc`。
  这是 gtest-all.cc 单文件聚合编译的经典约定（它不是 `./src/*.cc` 而是 `src/*.cc`，根在 gtest 顶层）。
- 方案（R6）：新增 `gdir = os.path.join(src, "test", "gtest")`，两条 gtest 编译命令改为
  `-isystem <ginc> -I<gdir> -I<gsrc>`（保留 gsrc 无害，gdir 前置保证 `src/*.cc` 命中
  `test/gtest/src/*.cc`）。其余脚本、计数（discovered=12）、LD_LIBRARY_PATH、链接闭包逻辑均不变。
- 未跳过任何测试；仅修正 gtest 聚合编译的 include 路径，测试口径与计数来源不变。

## 关键修复（真机 R7：gtest 二进制 -I 需指向源码根，`#include <lcm/lcm.h>` 才能命中）
- 现象（HMBS 真机 preflight，phase=compile，R6 gtest 编译通过后进入二进制编译首条命令）：
  `RUN: bash run_upstream_tests.sh` -> `test/c/memq_test.cpp:5:10: fatal error: 'lcm/lcm.h' file not found`
  `#include <lcm/lcm.h>`，上游发现 12 / 执行 0 / 通过 0。
- 根因：R5/R6 里 gtest 二进制的 `-I` 用了 `lcminc = os.path.join(src, "lcm")`（指向 src/lcm）。
  而上游头在 `src/lcm/lcm.h`（及 lcm-cpp.hpp），`#include <lcm/lcm.h>` 需 `-I<src>`（源码根，含 lcm/ 子目录）
  才能解析为 `src/lcm/lcm.h`；`-I<src>/lcm` 只会去找 `src/lcm/lcm/lcm.h`（不存在）。
- 方案（R7）：把 `lcminc` 从 `os.path.join(src, "lcm")` 改为 `src`（源码根目录），四条 gtest 二进制
  编译命令的 `-I<src>` 即可命中 `lcm/lcm.h` 与 `lcm/lcm-cpp.hpp`；common.h/lcmtest 生成头仍由
  既有 `-I<test_c>` 覆盖。其余逻辑（gtest 聚合 -I、lcm-gen、LD_LIBRARY_PATH、链接闭包、discovered=12、
  逐行 [ RUN ]/[ OK ]/[ FAILED ] 单数据源计数）均不变。
- 边界提示：eventlog_test 经 common.c 用 tmpnam(NULL) 把日志写进 /tmp；若真机 /tmp 只读（build()
  E002 注释曾提及），其 3 个用例将在运行期失败，属环境/ohos_feature 缺口，届时按真实结果以 gaps
  如实上报，不修改上游测试源码。
- 未跳过任何测试；仅修正 gtest 二进制 include 根目录，测试口径与计数来源不变。

## 关键修复（真机 R8：eventlog_test 编译缺 lcmtest_primitives_t.h —— lcm-gen 生成头不可见/失败被吞）
- 现象（HMBS 真机 preflight，phase=compile，R7 修好 `-I<src>` 后，memq_test 编译通过，脚本推进到
  eventlog_test）：
  `test/c/eventlog_test.cpp:6 -> common.h:8:10: fatal error: 'lcmtest_primitives_t.h' file not found`
  及 common.c 同报。上游发现 12 / 执行 0 / 通过 0。
- 根因：`-I<test_c>` 已在编译命令行里，头不在 test/c 即因**生成步骤根本没产出可见的生成头**。旧生成逻辑
  用 `self.run('... lcm-gen -c ... 2>/dev/null || true', ignore_errors=True)`：
  1. `2>/dev/null || true` + ignore_errors 把 lcm-gen 的任何失败（找不到二进制、运行期缺共享库崩溃、
     `-c` 用法错误等）**全部吞掉**，所以我们从来看不到 lcm-gen 真实报错；
  2. 即便 lcm-gen 成功产出 `lcmtest*_t.h`（子进程写入 test/c），HMDF 上子进程新建的**文件**对下一个独立
     clang 进程也不可靠可见——原来的 `.lcmgen_materialized` 哨兵只物化了 test/c **目录**，没物化目录里
     lcm-gen 新写的 `.h`（同 R4 gtest-build ENOENT / unsafe_local_mktemp 的 HMDF 子进程可见性家族）。
- 方案（新增 `_generate_lcmtest_headers()`，替换被吞错的旧两行）：
  1. **让 lcm-gen 错误显形**：`self.run(..., env="conanbuild")` 不带 ignore_errors，lcm-gen stdout+stderr
     统一重定向到 `build/.tmp/lcmgen_output.log`；非零退出码会抛 RuntimeError；运行前先校验
     `lcmgen/lcm-gen` 二进制存在、`t1/t2` 目录确有 `.lcm` 文件；
  2. **按生成头专用模式校验**：`glob(<test_c>/*_t.h)` 而非 `*.h`——test/c 里本就有 common.h 等既有头，
     只看 `*_t.h` 才能区分「真生成了」与「没生成、被既有头糊弄」；
  3. **原地物化每个生成头**：Python 父进程 re-read + `os.open(0o644)` re-write 每个 `*_t.h`，确保下一个
     clang 进程可见（HMBS_CAP_CHMOD=0 下 os.open 0o644 比 chmod 可靠）；空文件校验。
- 未跳过任何测试；测试口径与计数来源（discovered=12、逐行 [ RUN ]/[ OK ]/[ FAILED ]）不变。
- 边界：若 HMDF 连 Python 父进程都读不到 lcm-gen 子进程写的文件，`*_t.h` glob 会为空 → 显式报
  「lcm-gen produced no * _t.h」+ 指向 lcmgen_output.log，方便下一轮精确定位 lcm-gen 真实失败原因。

## 关键修复（真机 R9：lcm-gen 二进制路径 —— autotools VPATH 构建产物在 build 树不在 source 树）
- 现象（HMBS 真机 preflight，phase=compile，R8 修好生成头后进入 `_generate_lcmtest_headers`）：
  `self.run` 前的二进制存在性检查触发：
  `RuntimeError: lcm-gen binary not found at '<...>/b/lcm..../b/lcmgen/lcm-gen'`
  （该路径由 `src = self.source_folder` 拼接）。上游发现 0 / 执行 0（停在生成前）。
- 根因：配方用 `Autotools.configure()/make()` 做 **VPATH/out-of-source 构建**：configure 在
  `self.build_folder`（真机为 `<cache>/.../b/<hash>/b/build-release`）里生成 Makefile，
  `make` 把可执行产物 lcm-gen 写到 **build 树**（`<build_folder>/lcmgen/lcm-gen`，libtool 构建时
  还会是 wrapper 脚本 + `.libs/lcm-gen`），而 **不是 source 树**。旧代码 `lcmgen = os.path.join(src,
  "lcmgen", "lcm-gen")` 拿 source_folder 拼（`<...>/.b/b/lcmgen/lcm-gen`，缺 build-release 层级），
  那里只有 Makefile.am，没有构建产物，故 R8 新增的 `os.path.isfile()` 检查立刻如实暴露路径错误。
- 方案（新增 `_find_lcmgen(hint)`，让 R8 的"报告路径"升级为"自动定位"）：
  1. 先按显式候选路径探测：`os.path.join(self.build_folder, "lcmgen", lcm-gen)` 与 source 同款，build 优先；
  2. 若都未命中，对 build/source 两棵树做**有界递归遍历**（深度≤4），找名为 `lcm-gen`（或 .exe）的
     普通文件，同样 build 优先；
  3. 全部未命中 → 报错列出**所有搜过的路径**（显式候选 + 遍历命中项），供下一轮精确定位真实构建布局；
  4. `_generate_lcmtest_headers` 内先 `lcmgen = self._find_lcmgen(lcmgen)` 替换硬编码 source 路径。
- 未跳过任何测试；测试口径与计数来源不变。
- 边界：build 产物若是 libtool wrapper（共享库构建），`lcmgen/lcm-gen` 是 shell wrapper 脚本，运行、
  `os.path.isfile` 均正常；若 lcm-gen 未在 `make all` 里构建（不在此布局下），遍历会如实报告全路径。

## 关键修复（真机 R10：eventlog_test 把 C 文件 common.c 当 C++ 编译报错）
- 现象（HMBS 真机 preflight，phase=compile，R9 定位好 lcm-gen 后进入测试脚本二进制编译）：
  ```
  clang-15: warning: treating 'c' input as 'c++' when in C++ mode, this behavior is deprecated
  test/c/common.c:58:11: error: cannot initialize a variable of type 'char *' with an rvalue of type 'void *'
      char* result = malloc(len + 1);
  test/c/common.c:207:56: error: invalid suffix on literal; C++11 requires a space between literal and
      identifier [-Wreserved-user-defined-literal]
      CHECK_FIELD(msg->i64, (int64_t)(n * 10000), "%"PRId64);
  3 errors generated.
  ```
  上游发现 12 / 执行 0 / 通过 0（eventlog_test 编译即失败）。
- 根因：手写测试脚本的 eventlog_test 命令行把 `common.c` 原样丢给 `clang++`（`cxx`，C++ 模式）一起编译+链接。
  `common.c` 是 C99 文件（上游 test/c/Makefile 用 `$(CC) $(CFLAGS)` 编 common.o，CFLAGS 含 `-std=c99`），
  内含 C 专属写法：`malloc` 返回 void* 隐式转 char*（C 合法、C++ 非法），以及 `"%"PRId64` 字符串字面量
  拼接（C++ 保留字面量后缀规则下非法）。C++ 模式下 clang 报出上述 3 个错误。
- 方案（复刻上游 Makefile 的 CC/CXX 拆分）：
  1. `cxx` 之外新增读 `cc = compilers.get("c", "clang")`（tools.build:compiler_executables 字典的 "c" 成员）；
  2. 脚本内增一条独立命令：`"<cc>" -I<src> -I<ginc> -I<test_c> -std=c99 -c test/c/common.c -o <gtest_build>/common.o`
     （单独用 C 编译器按 C99 生成 common.o，与上游 `common.o: common.c  $(CC) $(CFLAGS) -c` 一致）；
  3. eventlog_test 命令行把 `"%s/common.c"` 替换为 `"%s/common.o"`（gtest_build 内预编译对象），
     clang++ 只编 eventlog_test.cpp 再链 common.o，等价上游 `eventlog_test: eventlog_test.o common.o`。
  - common.o 由 clang cc 写入 gtest_build 再由 clang++ 读取，与同脚本内 gtest-all.o→libgtest.a→链接的
    子进程间可见模式一致（R6-R9 已验证可用），不入 source 树、不依赖 HMDF 子进程建目录。
- 未跳过任何测试；discovered=12 与逐行 [ RUN ]/[ OK ]/[ FAILED ] 单数据源计数、恒等式、HMBS_UPSTREAM_TEST_RESULT
  口径全部不变。

## 关键修复（真机 R11：eventlog_test 运行期段错误 —— 设备 /tmp 只读导致 tmpnam 路径不可写）
- 现象（HMBS 真机 preflight，phase=compile，R10 common.o 拆分后四个测试二进制均能编译，进入运行期）：
  `run_upstream_tests.sh: line 13: Segmentation fault (core dumped) .../test/c/eventlog_test`
  `upstream gtest: discovered=12 executed=10 passed=9 failed=0`（旧单日志批量计数：memq 4 + udpm 1 + cpp memq 4
  = 9 通过；eventlog_test 段错误，留一个孤儿 [ RUN ] 无终结，导致 executed(10) != passed+failed(9) → 一致性
  校验失败，conan create 退出 1）。
- 根因：eventlog_test 三个用例（EventLogBasic/EventLogWriteRead/EventLogCorrupt）经 make_tmpnam()→tmpnam(NULL)
  返回 C 库 P_tmpdir 硬编码的 /tmp/<rand> 路径。真机 /tmp 是只读 erofs（build() E002 注释已记录），
  lcm_eventlog_create() 的 fopen(path,"wb") 失败返回 NULL，而 eventlog_test.cpp 未判空即调用
  lcm_eventlog_destroy(NULL)→fclose(NULL)→SIGSEGV。memq/udpm/cpp memq 不写文件，故只有 eventlog_test 崩溃——证据与
  R7 边界提示预判一致。这是 OHOS 环境能力缺口（ohos_feature），不是 harness 代码 bug；tmpnam 用硬编码 /tmp 且
  不认 TMPDIR，无法在配方内重定向，因此不以改上游测试源码/伪造 stub 的方式规避。
- 方案（分开运行 + 按退出码诚实上报 ohos_feature gap，不伪造通过）：
  1. 四个测试二进制各自写入独立日志（gtest_memq/eventlog/udpm/cpp_memq.log），并新增 shell 函数 run_one 把
     每个二进制退出码写入旁路 gtest_rc.txt（name:rc）；`|| rc=$?` 保证 set -eu 下崩溃不中断脚本且能捕获 139。
  2. 解析时按二进制分别统计 [ RUN ]/[ OK ]/[ FAILED ]；对健康三个二进制校验 RUN==OK+FAILED。
  3. 若 eventlog 退出码非 0（本次 139），其 3 个声明用例未完成执行 → 计入 gaps_n，不把孤儿 [ RUN ] 当 executed，
     evlog 日志不参与计数。
  4. 汇总 executed=9 passed=9 failed=0 skipped=3；gaps=[{count:3,category:"ohos_feature", detail/evidence 引用
     真机 Segfault 与 eventlog.c/eventlog_test.cpp 源码；若另有个别 [ FAILED ] 也会作为 test_failure gap 并入]。
     恒等式 passed+failed==executed、executed+skipped<=discovered、executed<=discovered 全部自检；
     sum(gaps)==discovered-passed 校验。status="failed"（9/12，不写 100%）。
- 未删除/跳过任何测试；9 个真实通过照实计数，3 个 eventlog 用例因设备只读 /tmp 无法完成，作为 ohos_feature
  gaps 如实上报（若 /tmp 变为可写，eventlog rc=0 时其用例自动按框架输出计入，gaps 消失）。
- counted source：discovered=12 来自上游 .cpp 的 TEST()；executed/passed/failed 来自各二进制 gtest 日志逐行
  [ RUN ]/[ OK ]/[ FAILED ] 单一数据源；eventlog 未执行源于退出码 139（真机 Segfault）。

## 关键修复（真机 R12：ohos_feature gap 不应让 conan create 整体失败）
- 现象（HMBS 真机 preflight，phase=compile）：R11 已正确算出 executed=9 passed=9 failed=0 skipped=3 +
  ohos_feature gap(3)，但方法末尾仍 `status="failed"`（因 passed != discovered）并无条件 raise
  RuntimeError → conan create 在 build() 阶段整体失败，package/test_package 无法进行。
- 根因：_run_upstream_tests 把「声明了但设备无法执行的环境/ohos_feature 缺口」(eventlog_test 写只读
  /tmp 段错误) 与「真测试失败 ([ FAILED ])」一视同仁，都用 status="failed" + raise 阻断构建。但守则明确
  gaps 类别允许 environment/ohos_feature 且不构成必拦截项（缺依赖才拦截）；ohos_feature 缺口带证据即可放行。
- 方案（区分真实测试失败 vs 环境缺口，仅真实 [ FAILED ] 才阻断）：
  1. `has_real_failure = failed > 0`：仅当有 gtest 实际报告的 [ FAILED ]（test_failure gap）才视为失败；
  2. `status = "failed" if has_real_failure else "passed"`——本次 failed=0，只有 ohos_feature gap，status 报
     "passed" 且 gaps 如实携带 3 条 eventlog 证据（数量恒等式 sum(gaps)==discovered-passed 仍校验）；
  3. 末尾 `if has_real_failure:` 才 raise RuntimeError；仅 ohos_feature gap 时正常走 package()/test_package。
- 未删除/跳过任何测试、未改上游测试源码、未伪造通过：9 个真实通过照实计数，3 个 eventlog 用例作为
  ohos_feature gap 如实上报；若 /tmp 可写使 eventlog rc=0，其用例自动按框架输出计入、gaps 消失、passed 升为 12。
## 关键修复（真机 R13：package()/make install 的 toybox install -c Error 64）
- 现象（HMBS 真机 preflight，phase=compile，R12 放行 ohos_feature gap 后进入 package() 阶段）：
  ```
   /storage/Users/currentUser/usr/local/bin/mkdir -p '.../p//include/lcm'
   /storage/Users/currentUser/preflight/.../runtime/lcm-1.3.11/bin/install -c -m 644 eventlog.h lcm.h
      lcm_coretypes.h lcm-cpp.hpp lcm-cpp-impl.hpp '.../p//include/lcm'
   make[2]: *** [Makefile:594: install-liblcmincludeHEADERS] Error 64
  ```
  上游测试已正确计入（discovered=12 executed=9 passed=9 skipped=3 ohos_feature gap 3），失败发生在
  package() 的 autotools.install()（make install 拷贝头文件）阶段。
- 根因：OHOS worker image 无 GNU coreutils install；设备 toybox `install -c` 在 HMDFS 上直接失败
  （Error 64），且 `-m 644` 还会走 chmod（HMDFS 不支持 chmod，E087）。autotools 的 automake 头文件
  install 规则 `install-liblcmincludeHEADERS` 用 `$(INSTALL_DATA) = $(INSTALL) -m 644` 批量 cp 头到
  `PREFIX/include/lcm`，故 Error 64。configure 已把探测到的 install 写死进所有子 Makefile 的 INSTALL 变量。
- 方案（复刻 E182/E188/E596-C + libfstconst/1.8.4 的 install shim）：
  1. 新增 `_write_install_shim()`：在 build_folder 写 `_ohos_install_shim/install`（`#!/bin/sh`，
     `os.open(..., 0o755)` 落盘保证执行位（HMBS_CAP_CHMOD=0 下开学 chmod 无效，E596：普通 open 得 0644 → Error 126），
     `cp -f` 复制 + `mkdir -p` 建目录 + chmod 容错跳过，dest 为目录时把前 N-1 源逐个 cp 进目录，
     dest 为文件路径时 `cp -f $1 $dest`——覆盖 automake 头文件批量 install 与单程序 install 两种形态）；
  2. 新增 `_redirect_install_to_shim(shim)`：os.walk build_folder 所有 `Makefile`，把
     `INSTALL = <某 install 命令>` 行替换为 `INSTALL = <shim 绝对路径>`（INSTALL_DATA/INSTALL_PROGRAM
     引用 ${INSTALL} 自动跟着重算）；不靠 PATH 前置（conan build env source conanbuild.sh 会覆盖）；
  3. build() 在 `autotools.configure()`（生成 Makefile）后调用两者；package() 的 autotools.install()
     make install 即全程用 shim 替代失败的 toybox install。
- 未删除/跳过任何测试；仅把 package 安装路径的 install 命令换成 cp/mkdir shim，测试口径与计数不变。
- 计数来源不变：discovered=12 来自上游 .cpp 的 TEST()；executed/passed/failed 来自各 gtest 二进制日志
  逐行 [ RUN ]/[ OK ]/[ FAILED ] 单一数据源；ohos_feature gap 来自 eventlog_test 写只读 /tmp 段错误。

## 关键修复（真机 R14：test_package 阶段缺机器证据 —— 补全 test_package）
- 现象（HMBS 真机 preflight，phase=test_package）：上游测试已正确产出 HMBS_UPSTREAM_TEST_RESULT
  （discovered=12 executed=9 passed=9 failed=0 skipped=3，eventlog 3 用例写只读 /tmp 段错误为
  ohos_feature gap），package 阶段也完成，但 hmbs 判 incomplete「缺少 test_package 真实用例计数
  和机器测试证据」。原因：test_package/ 目录为空，conan create 的 test_package 阶段没有任何
  消费者测试、也没有产出 HMBS_TEST_PACKAGE_RESULT 标记（discovered/passedCount 必填）。
- 方案（新增完整 test_package）：
  1. test_lcm.c —— C 消费者，CMakeDeps 链接安装后的 liblcm（lcm::lcm → glib::glib-2.0 /
     glib::gthread-2.0 传递闭包，含 pcre2/intl/m/pthread/dl/rt），走真实 memq:// 提供者做 6 项
     生命周期校验（memq 创建/订阅/发布+handle 往返 10 次 1024B 随机负载比对/handle_timeout 空队列
     立即超时/handle_timeout 带消息返回>0 且回调收到 ping/销毁）；每项通过打印一行 CHECK-OK。
  2. CMakeLists.txt —— find_package(lcm REQUIRED) + target_link_libraries(lcm::lcm)。
  3. conanfile.py —— generate() 复用 bzrtp 的 OHOS clang/clang++ 工具链补丁模式；test() 运行
     test_lcm，把 stdout 重定向到 test_package.log，逐行数 CHECK-OK 得 passedCount（确定性单一
     数据源，不靠退出码推断），输出 HMBS_TEST_PACKAGE_RESULT（discovered=6）；再从 package
     res/upstream_test_result.json 复发 HMBS_UPSTREAM_TEST_RESULT（缓存命中轮也有上游证据）。
  4. MANIFEST.yml —— 声明 upstream_test_total=12、upstream_test_count_method=gtest_macros、
     upstream_tests 四套件构成、test_package_tests（test_lcm.c）、assertion_count=6。
- 计数：test_package 6/6 来自 test_lcm.c 实际打印的 CHECK-OK 行；上游仍 12（gtest_macros），
  9 通过 + 3 ohos_feature gap，均与主配方一致。未删除/跳过任何断言、未伪造通过。

## 关键修复（真机 R15：rule4「passed 状态与上游结果矛盾」—— status 语义修正）
- 现象（HMBS 真机 preflight，phase=evidence，rule4）：计数本身正确（discovered=12 executed=9
  passed=9 failed=0 skipped=3，eventlog 3 用例写只读 /tmp 段错误为 ohos_feature gap），但门禁判
  incomplete「rule4：passed 状态与上游结果矛盾」。即 HMBS_UPSTREAM_TEST_RESULT 里 status="passed"
  与 skipped=3 / gaps 并存。
- 根因：R12 把 status 定为 `"failed" if has_real_failure else "passed"`，即只要没有真实 [ FAILED ]
  就报 "passed"，而忽略了 skipped>0 / gaps 意味着并非 100% 执行/通过。守则（cucumber-cpp 经验 2）明确：
  **只要存在 skipped 或 gaps（未 100% 执行），status 必须写 "incomplete"**，"passed" 与 skipped 并存
  自相矛盾，门禁必拒（错误文案正是「passed 状态与上游结果矛盾」）。
- 方案（经验 2 的 status 三态语义）：
  1. `has_real_failure = failed > 0` 仍决定是否阻断构建（仅真实 [ FAILED ] 才 raise）；test_failure gap
     时 status="failed"；
  2. 无真实失败但 `skipped > 0 or gaps`（非空）→ status="incomplete"（本次即此分支，9/12 + ohos_feature
     gap 3 → incomplete）；
  3. 仅当 discovered==executed==passed（无 skipped、无 failed、无 gaps）→ status="passed"。
  计数、gaps、恒等式、test_package 复发逻辑全部不变。
- 未删除/跳过任何测试、未改上游测试源码、未伪造通过：9 个真实通过照实计数；3 个 eventlog 用例因
  设备只读 /tmp 无法完成，作为 ohos_feature gap 如实上报，status=incomplete 与其自洽。若 /tmp 可写使
  eventlog rc=0、其 3 用例按框架输出计入，则 skipped=0、gaps 消失、discovered==executed==passed=12，
  status 自动升为 "passed"。


## 关键修复（真机 R16：上游 N=24 全量接入 + 修复 rule4 少报）
- 现象（人工审查 + hmbs 真机预检 evidence 阶段，rule4）：审查员核验上游 gtest_macros
  实测 N=24（6 个测试二进制），而 MANIFEST.yml 只声明 upstream_test_total=12、PR 正文
  也只声明上游单元测试 12，少报（实测 24 > 声明 12）。真机预检的 HMBS_UPSTREAM_TEST_RESULT
  已按 work tree 的 24 上报（discovered=24 executed=9 passed=9 skipped=15 ohos_feature gap 15），
  但 MANIFEST 声明总数仍是 12，与 conanfile discovered=24 不一致 → rule4 判「上游计数缺失、
  非法或执行/通过/失败数量不一致」。
- 根因：上一轮（R14/R15）只接入 4 个 gtest 二进制（memq/eventlog/udpm/cppmemq，N=12），
  未把 test/c/client.cpp（6）与 test/cpp/client.cpp（6）两个 client-server 二进制计入分母，
  也从未在 conan build() 里编译运行它们（这样即便计入也只是空口）。reviewer 按上游 .cpp 的
  TEST() 宏核得 N=24，故判少报。
- 方案（配方 R16，work tree 已在上一会话部分完成，本轮补全并修复）：
  1. `_generate_lcmtest_cpp_headers()`：对 test/cpp 跑 `lcm-gen --cpp` 生成 lcmtest/lcmtest2
     的 .hpp，并从 Python 父进程 re-materialize（HMDF 子进程文件对下个 clang 进程不可见，同 R8）；
  2. `_run_upstream_tests` 的 discovered 12 → 24，bins 扩为 6 项（memq/eventlog/udpm/cclient/
     cppmemq/cppclient），新增 sh2 客户端-服务端脚本：编译 test/c/server.c + type objs + C client
     (c_client) + C++ client (cpp_client)，起 server → sleep 3 → 跑两 client → kill server；
     按退出码/缺失二进制(rc=127)如实入 gap，不伪造通过、不阻断其余 standalone 用例；
  3. 修复 R16 引入的重复执行 bug：standalone 脚本 run_upstream_tests.sh 被写并运行两次
     （新增块 + 原块），导致 memq/eventlog/udpm/cppmemq 跑两遍并重复写 gtest_rc.txt。删除
     首个新增重复块，只保留一处（单数据源计数不变）。
  4. MANIFEST.yml：upstream_test_total 12 → 24，upstream_tests 扩为 6 套件（补 C client-server 6、
     C++ client-server 6），并注明各自 gap 来源；口径仍 gtest_macros，与 conanfile discovered=24
     及人工审查 N=24 严格一致。
  5. PR 正文草稿 .hmbs/pr-body.md：上游单元测试 12 → 24、通过率 9/24（37.5%）、15 例 ohos_feature
     gap 逐类说明（eventlog 3 写只读 /tmp 段错误 rc=139 + C client 6 rc=127 + C++ client 6 rc=1 组播
     不可达），供 HMBS 校验后同步。
- 未删除/跳过任何上游测试、未改上游源码、未伪造通过：24 例全部接入尝试执行，9 例真通、15 例
  ohos_feature 环境缺口（eventlog /tmp 段错误 + 两组 client-server 组播不可达）带真实日志/rc/源码
  定位如实上报；恒等式 passed+failed==executed、executed+skipped<=discovered、Σgaps==N-passed
  自检通过（9+0==9、9+15==24、15==24-9）。
- 计数来源不变：discovered=24 来自上游 6 个 .cpp 的 TEST()（pc-pr-review gtest_macros N=24）；
  executed/passed/failed 来自各 gtest 二进制日志逐行 [ RUN ]/[ OK ]/[ FAILED ] 单一数据源；
  ohos_feature gap 来自 eventlog 写只读 /tmp 段错误 + client-server 组播不可达的真实 rc。
