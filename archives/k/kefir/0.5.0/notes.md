# kefir 0.5.0 适配笔记

## 上游信息

- 名称：kefir（独立 C17/C23 编译器）
- 版本：0.5.0（2025-09-09）
- 主页：https://kefir.protopopov.lv
- 主仓库：https://git.sr.ht/~jprotopopov/kefir（SourceHut，主）
- 作者仓库：https://git.protopopov.lv/kefir.git（`git ls-remote` 实测含 `refs/tags/v0.5.0`，提交 `080078d9d6b2000c53f377be36398377a8d18cd6`）
- 配方源码包：https://github.com/sourcehut-mirrors/kefir/archive/refs/tags/v0.5.0.tar.gz（GitHub 镜像，提交与作者标签一致，CI 自动加 gh-proxy 回退）
- sha256：`ae69cb14457ce975a37a963da64bf54b5c997ab6e57b93c4841c7fb50a8b1a98`（本地下载实测）
- 许可证：编译器 GPL-3.0-only，运行时头 BSD-3
- 构建系统：自定义 Makefile（非 autotools/cmake/meson），C11，需 Bash/GNU Make/coreutils/m4

## 关键约束（x86_64 专属）

- kefir 只生成 x86_64 System-V ABI 汇编（README/TLDR 明确：no non-x86_64 targets yet），支持 Linux glibc/musl 与 FreeBSD/NetBSD/OpenBSD。
- kefir 自身是可移植 C11，可在 OHOS aarch64 上编译运行；但其产物是 x86_64 汇编，需外部 GNU as/ld 与 x86_64 libc 才能链接运行，OHOS aarch64 无法执行。
- 因此 `make test` 中所有编译后执行环节（integration/system/end2end）在 OHOS 上必然失败，属 `ohos_feature`，非配方缺陷。

## 上游测试盘点

- `make test` 固定总数约 1883（custom Makefile 口径，MANIFEST 记 `auto` 并附审计）：
  - unit：1 套件二进制（76 个 `.c` 文件）
  - integration：231 个 `*.test.c`
  - system：152 个 `*.test.c`
  - end2end：832 个测试目录 + 255 个 `*.kefir.asmgen.c` + 412 个 `*.kefir.also.asmgen`
- csmith（随机生成）与 external（60+ 真实项目）是独立目标，不计入固定总数。
- 配方 `build()` 执行 `make -k test`（`-k` 保证全量尝试），以 `bin/**/*.done` 文件数作为 passed 确定性来源。

## 编译步骤

```
cd archives/k/kefir/0.5.0
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- `generate()` 从 `tools.build:compiler_executables` 取 CC/CXX/AR/RANLIB，写入 `kefirbuild` 脚本（R33；脚本名不得用裸 `conanbuild`，否则会被 Conan 聚合脚本 `conanbuild.sh` 覆盖形成自引用，真机表现为 printenv E2BIG + Signal 9/137 且 make 永不执行）。
- `build()` 只构建 `.BINARIES`（跳过需 groff/mandoc 的 man 页），`USE_SHARED=no` 避免共享库签名问题；`PROFILE=release` 保持 `-DNDEBUG/-DKEFIR_BUILD_RELEASE`，另附 `EXTRA_CFLAGS="-O1"`（clang 以最后一个 `-O` 为准，在 2663 文件单任务构建下降低 `-O3` 代码生成开销，真机预检曾在默认预算下于 `.BINARIES` 中途掉线）；`DETECT_HOST_ENV=no` 跳过仅支持 Linux/BSD 的主机探测（HongMeng 上必然失败并回退为空 `config.h`，直接禁用可确定性得到同一结果）。
- `package()` 用 python 复制 `bin/kefir*`、libs、headers、licenses，不调用需 `install(1)` 的 `make install`。
- `package_type=application`，`bindirs=["bin"]`。

## test_package（R34）

- `kefir --version` 在 OHOS aarch64 真机运行。
- `kefir --target host-none -S -o hello.s hello.c` 编译最小 C 文件到汇编（host-none 为上游自有 freestanding 模式，跳过 KEFIR_GNU_INCLUDE/KEFIR_RTINC 要求；-S 只做 codegen 不链接，避开 OHOS 缺失 x86_64 GNU libc 所需的 KEFIR_GNU_LIB），断言产物非空且含 x86_64 标记（`%rax`/`%rdi`/`ret`/`.text` 等），证明 codegen 在不执行 x86_64 的前提下工作。
- 输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=2）。

## 待真机验证

- 首轮仅完成未提交工作树，真机 `make -k test` 的 `.done` 计数与 `test_package` 结果待 hmbs 预检返回后填入 PR 正文与 manifest。

## 真机预检修复记录（pre-PR，未提交工作树）

- round1: profile 钉定的 `/data/service/hnp/bin/clang` 在预检机上报 `inaccessible or not found`（可达性随会话/挂载状态变化，keyd 先例），配方改为运行时存活探测（`--version` 直接执行）+ PATH 顺序回退。
- round2: 全部编译链接通过，但每个 `.done` 目标报 `env: exec bash: No such file`（上游全部测试驱动为 `#!/usr/bin/env bash`），test_package 报 packaged `kefir: Permission denied`（126）。配方改为 OHOS 风味优先 + bash 入 PATH + package 复制后 best-effort chmod 755。
- round3: round2 的 PATH 式 bash 仍未生效（profile `[buildenv]` 后于配方 env 脚本被 source，会覆盖 PATH/SHELL，keyd 问题 #3 同族）。改用调用钉定：`build()` 内把 `source/tests/**/*.sh` 的 shebang 改写为存活 bash 绝对路径（仅解释器定位，测试逻辑与计数不变）；CC 选择改用 `clang -dumpmachine` 含 `ohos` 作为风味判定（hnp clang 报 `aarch64-unknown-linux-ohos`，而 `--version` 只有通用 `clang version 15.0.4`）；链接追加 `EXTRA_LDFLAGS="-fuse-ld=lld"`（DRAFT-6048：只有 lld 产物可在 OHOS 执行，GNU ld 产物报 126；kakasi 先例）；test_package 改用打包绝对路径做 stat + Python 内解析 PT_INTERP（期望 OHOS/musl 产物 `/lib/ld-musl-aarch64.so.1`）。
- groff 缺失：`docs/man/Makefile.mk` 的 `$(MDOC_CONV) -Tascii | sed > .txt` 管道以 sed 退出码 0 继续，缺 groff 时帮助文本为空但构建不中断；`--version` 与 codegen 不受影响，仅 `--help` 文本为空（OHOS 真机限制，如实记录）。
- round4: round2 PATH式bash与round3绝对路径shebang钉定以相同 env: exec bash 指纹两次失败，证明本会话真机根本不存在可用bash（/data/service/hnp/bin/bash随挂载门控，PATH无其他bash），提供bash路线已证伪。改走消除依赖路线：build()内把5个测试驱动（unit/integration/system/end2end run.sh + end2end compile.sh）的方言机械转为POSIX sh（env bash改/bin/sh，function f转f()、source转.、[[转[、==转=），测试命令/退出码/diff逻辑不变；*.profile本就是纯赋值已兼容。另修ELF探针struct解析错位（旧版e_phentsize/e_phnum恒错导致interp恒报static-or-none），新增machine（183=aarch64/62=x86_64）+interp双证据并在.BINARIES后打点；_install_bin改用umask(022)+O_CREAT 0755建时定权（chmod后补在子能力0文件系统上被忽略导致包内750与126）。
- round5: 上轮预检（228/1883）暴露三个可修复根因，均不碰上游测试：① `USE_SHARED=no` 时 driver/cc1 以 `-static` 链接，产物为 aarch64/static-or-none 却在 OHOS 报 126（树内 `./bin/kefir` 与包内 `kefir --version` 同一指纹，而同 CC 的动态测试二进制可正常执行），`build()` 新增 `_drop_static_link()` 去掉两处 `-static`（仍链静态归档，仅出动态 musl 可执行）；② 单测 `ast_constant_expression2.c:127` 系宿主 char 符号性错配（ARM 默认 unsigned，x86_64 目标默认 signed，`(char)j` 期望值分叉），`EXTRA_CFLAGS` 追加 `-fsigned-char` 对齐目标假设；③ 包内仍 750 系 `_install_bin` 对已存在文件 `O_TRUNC` 不改模式，创建前先 `unlink` 使 0755 生效。
- round6: 上轮去 `-static` 生效（包内 interp 由 static-or-none 变为 `/lib/ld-musl-aarch64.so.1`，包体积同步缩小；单测 char 断言已过，新卡点变为 `bigint1.c:2181` 长双精度断言，属 aarch64/80-bit 表示差异，记缺口不碰测试），但树内与包内 `kefir` 仍同报 126 且包内仍 750，证明单文件级 umask+open 两次均未存活。换不同策略：① 全进程级 `os.umask(0o022)` 置于 `build()`/`package()` 入口且不再中途恢复，让链接器与所有新建文件原生 755；② `STRIP=true` 禁掉 release 的 `$(STRIP)`（设备 strip 未钉定，疑破坏 freshly linked 驱动，而从不 strip 的测试二进制可正常执行；只增体积不改语义）。
- round7: 上轮全进程 umask + 禁 strip 生效（上游 228→873，end2end 由 126 变为真实 asmgen-diff Error 1；`kefir --version` 已过）。test_package 第二步 `kefir -o hello.s` 触发链接阶段 `KEFIR_GNU_LIB` 缺失（target_configuration.c:307/454，仅链接路径要求 x86_64 GNU libc 启动文件，OHOS 无此物）。改用上游 asmgen 同款 `-S`（`kefir -S -o hello.s hello.c`，只做 codegen 不链接），与测试初衷（验证 x86_64 汇编产出）完全一致，不碰上游测试。
- round8: 预检 `kefir -S` 仍报 `Runtime include path shall be passed as KEFIR_RTINC`（target_configuration.c:156，include_rtinc 路径连 -S 也强制要求）。根因是配方未复刻上游 install.mk：上游把链接产物装成 `bindir/kefir-cc` 并由 scripts/kefir.m4 生成 `bindir/kefir` 包装脚本（未设环境时默认 `KEFIR_RTINC=<prefix>/include/kefir/runtime` 再 exec kefir-cc），而旧 package() 把裸 driver 直接装成 `bin/kefir`。修复：裸 driver 改装为 `bin/kefir-cc` 并生成同款 POSIX sh 包装 `bin/kefir`（755 建时定权，复用 umask 022+unlink 纪律；$0 含斜杠时相对定位 runtime，PATH 调用时依赖 runenv）；package_info 新增 `runenv_info.define("KEFIR_RTINC", <prefix>/include/kefir/runtime)` 使 conanrun 下 PATH 调用亦可用。同时 conandata.yml url 改为有序列表（gh-proxy 镜像在前、官方原 URL 保底，sha256 不变），与 ci/conan/build_and_test.sh 的 GitHub 镜像映射一致，缓解真机 github 直连 ConnectTimeout 重试。
- round9: 预检首编译规则即死 `Makefile.mk:133`：`/bin/sh: .../.harmonybrew/bin/dirname: Operation not permitted` + `mkdir: missing operand`。根因是全部构建规则用 `mkdir -p $(shell dirname "$@")` 而设备 dirname shim 不可执行，shell 展开为空致 mkdir 缺参。修复（build-local，不碰测试逻辑）：① `build()` 新增 `_fix_makefile_dirname()`，把全部 `Makefile`/`*.mk` 的 `$(shell dirname X)` 换成 GNU make 内建 `$(dir X)`（mkdir -p 语义等价，尾斜杠无害，不再 spawn 外部二进制）；② `_sh_posixify_test_drivers()` 在每个测试驱动 `.sh` 的 shebang 后注入 POSIX `dirname()`/`basename()` 函数（参数展开实现，basename 保留双参去后缀形），覆盖 integration/system `run.sh` 与 end2end `compile.sh` 的运行时外部调用（同属 EPERM 同族，basename 同目录大概率同坏，提前覆盖省一轮）。
- round10: 预检 `kefir -S` 报 `GNU include path shall be passed as KEFIR_GNU_INCLUDE`（target_configuration.c:191）。根因是默认目标为 x86_64-linux-gnu，其 `-S` 路径在 `include_stdinc` 为真时仍强制要求 GNU 头（与链接无关，codegen 本身不需要系统头）。上游自有独立模式 `source/tests/end2end/compile.sh` 用 `--target host-none`（= x86_64-linux-none，arch/platform 取 host 默认、variant 为 none），在 variant NONE 下同时跳过 GNU/MUSL stdinc 与 RTINC 要求（target_configuration.c：`include_rtinc && variant != NONE`，LINUX+NONE 时 stdinc 无要求），且仍走完整 preprocess+compile。test_package 的 TEST_C 无任何 `#include`，属同类 freestanding 源，故改用上游同款 `--target host-none -S`（非跳过测试，仍校验非空汇编与 x86_64 标记 `%rax/%rdi/ret/.text`）；runenv 的 KEFIR_RTINC 保留（默认 gnu 目标仍可用）。
- round11: 上轮 `make -k test` 得 873/1883，但单个 lumped gap（1010 全归 x86_64 执行）不准确：unit 的 `bigint1.c:2181 fabsl<1e-8` 是宿主 long double 表示差异（x86_64 80-bit extended vs aarch64 128-bit，`KEFIR_DISABLE_LONG_DOUBLE` 在 unit/run.sh 仅 valgrind 下才置位），integration  portable 预处理套件报 `Terminated Signal 5 / Error 127`（run.sh 127=被测二进制非零，128=diff 不一致，需按用例 stdout 分诊，不能笼统归为执行缺失），system 卡在 `$AS`（run.sh[93] `as: inaccessible or not found`，即使 `as` 可用也是 aarch64 `as`，无法汇编 x86_64），end2end run 需链接执行 x86_64（TLDR 明确无非 x86_64 目标）而 asmgen 系纯翻译 diff 失败集中在 long_double/vararg（宿主表示差异）。改动（与 round10 不同策略，不碰测试逻辑）：`build()` 新增 `_count_suite_done()` 按 `bin/tests/` 下互斥文件名族（unit.tests.done / integration `*.done` / system `*.test.done` / end2end `*.test.done` 与 `*.test.{,also.}asmgen.done`）确定性计数，`suite_discovered={1,231,152,832,667}` 合计 1883，gaps 按套件逐项出具（unit/system/end2end 两类为 ohos_feature，integration 暂记 test_failure 待分诊），计数之和恒等于 `failed`，恒等式 `passed+failed==executed` 保持。
