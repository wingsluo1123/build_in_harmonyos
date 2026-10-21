# tenyr 0.9.9 适配笔记

## 编译环境
- 构建系统: makefile（上层裸 GNU make，无 autotools/CMake；lexer.l/parser.y 构建时用 flex+bison 再生成 lexer.c/parser.c）
- 编译日期: 2026-10-12
- 编译器: clang（OHOS 工具链 `tools.build:compiler_executables`，透传给 make 的 CC）
- 状态: built（真机 rule4 门禁通过后转 published）

## 编译步骤
```bash
# 源：https://github.com/kulp/tenyr/archive/refs/tags/v0.9.9.tar.gz
# 配方（conan create）内部：
make -j1 CC=<toolchain-clang> JIT=0 SDL=0 PEDANTIC=0        # 构建 tas/tsim/tld + 测试插件
make -j1 check_sw JIT=0 SDL=0 PEDANTIC=0 CC=<toolchain-clang>    # 运行上游软件测试套件（配 PWD=build_folder，见问题 7）
make install INSTALL_DIR=<package_folder> JIT=0 SDL=0 PEDANTIC=0 CC=<toolchain-clang>  # 安装 bin/ + share/tenyr/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建尝试编译 SDL 设备（sdlled/sdlvga）并 find 不到 SDL.h | `mk/sdl.mk` 用 `ifneq ($(SDL),0)`，变量未定义时（空 != 0）为真 → SDL 设备默认启用 | 配方传 `SDL=0`（仅需软件模拟核心） |
| 2 | 构建尝试链接 libtenyrjit 需要 `-llightning` | `mk/jit.mk` 同样用 `ifneq ($(JIT),0)` 默认启用 JIT → 依赖 GNU Lightning | 配方传 `JIT=0` |
| 3 | clang 编译 src/common.o 报 `-Werror=shorten-64-to-32`：implicit conversion loses integer precision 'long' to 'int32_t' | `mk/compiler/clang.mk` 无条件追加 `-Weverything` 与 `-Werror=shorten-64-to-32`；`SEXTEND32()` 里 `return ext | (val & ((1L << bits) - 1))` 在 LP64 下 long→int32 隐式窄化 | 补丁 0001：对返回值显式 `(int32_t)` 强转（可移植修复，非 OHOS 专属宏） |
| 4 | `PEDANTIC=1`（默认）时 `-Werror` 把大量移植性警告变成硬错误 | mk/pedantic.mk 默认 `-Werror -pedantic-errors` | 配方传 `PEDANTIC=0` 关闭 -Werror |
| 5 | 上游 `make check` 的 check_hw 需要 Icarus Verilog + VPI 工具链 | check_hw 跑 Verilog 硬件仿真 | 配方只跑 `check_sw`（软件检查，无硬件需求） |
| 6 | OHOS clang 编译多个 .o（common.o/asm.o/...）报 `error: disabled expansion of recursive macro [-Werror,-Wdisabled-macro-expansion]`（common.c 用 stderr；tas.c/tsim.c/tld.c/serial.c 用 stdin/stdout；asm.c 用 isprint() 等） | OHOS sysroot stdio.h/ctype.h 把 stdin/stdout/stderr 与 ctype 助手（isprint/isspace/isdigit 等）定义为自引用/递归宏；`-Weverything` 报 `-Wdisabled-macro-expansion`，而 mk/compiler/clang.mk 把 `-Werror=disabled-macro-expansion` **无条件**追加进 PEDANTIC_FLAGS（与 PEDANTIC 无关），凡直接展开此类宏的对象都会成为硬错误（逐个对象豁免会出现连环失败） | 补丁 0002：Makefile 顶部**全局**追加 `CFLAGS += -W$(PEDANTRY_EXCEPTION)disabled-macro-expansion`（= `-Wno-error=disabled-macro-expansion` 对所有对象降级为警告），覆盖 stdin/stdout/stderr 与 ctype 递归宏，避免逐对象多次失败；与上游对 flex/bison 生成的 lexer.o/parser.o 的处理机制一致（可移植修复，非 OHOS 专属） |
| 7 | 真机 `make check_sw` 全 88 条模拟测试只有 header 无 ok（0 ok），日志末尾大量 `job-working-directory: ... getcwd: cannot access parent directories: Bad file descriptor` | **已否决（第 2 策略周期）**：早期把 `-j1`/`$PWD` 当作 hnp bash/make 在 HMDFS 深路径 getcwd 损坏的修复，连续三轮真机现象逐字节一致（88/0 不变），证明 getcwd/jobserver/PWD 均非根因。关键证据：同一 hnp-bash（broken getcwd）环境下 dogfood（tas/tld）正常通过，说明 broken getcwd 不阻止工具运行；88 个失败用例唯一共同点是都调用 `$(tsim)`，而 tas/tld 从不调用 | 转到问题 8（tsim 运行时路径）；诊断改为逐用例抓真实 tsim 报错 + tsim interp smoke |
| 8 | 真机 `make check_sw` 报 executed=88 passed=0 failed=88 | **真机诊断揭示真根因（第 3 次修复）**：不是 tsim 运行时失败，而是配方计数正则被 getcwd 噪音拆行误导。逐用例诊断显示每个 `(sim,interp)` header 之后紧跟一行的 `ok`——测试实际全部通过！`mk/misc.mk` 把 SHELL 设为 hnp bash，其在深路径启动时打印 `shell-init: ... getcwd ...`，因 MAKESTEP -n 无换行，该噪音被拼到 header 行尾，把成功 `ok` 挤到下一行；旧正则要求 `(sim,...)[^\n]*ok` 同行才能算过，故 88 个 header 全被误判 failed。之前 0003（os_find_self readlink）与 getcwd/jobserver/PWD 均非根因（已移除 0003） | 配方计数改为按 header 分块：每块（header→下一 header）含 `ok`（同行 `... ok` 或独立 `ok` 行）即通过，兼容原生单行与 HMDFS 拆行两种格式。本地原生 88/88、真机格式合成 88/88、单条真失败仍能识别 |

> 注意：mk/compiler/clang.mk 里 `-Weverything` 与 `-Werror=shorten-64-to-32`/`-Werror=disabled-macro-expansion` 等是**无条件**追加的，**与 `PEDANTIC` 无关**；`PEDANTIC=0` 只关闭 mk/pedantic.mk 的全局 `-Werror`，并不能关闭 clang.mk 的这些逐项 `-Werror=...`。因此这两类问题必须用补丁显式处理（0001 修 SEXTEND32，0002 降级 disabled-macro-expansion）。

## 源码修改
- `patches/0001-fix-sextend32-long-to-int32-cast.patch`：
  `src/common.h` `SEXTEND32()` 返回值 `return ext | (val & ((1L << bits) - 1));` 改为
  `return (int32_t)(ext | (val & ((1L << bits) - 1)));`。
  被 clang 严格模式 `-Werror=shorten-64-to-32` 判为硬错误；显式强转为通用可移植修复。
- `patches/0002-fix-disabled-macro-expansion-stdin-stdout.patch`：
  `Makefile` 顶部**全局**追加
  `CFLAGS += -W$(PEDANTRY_EXCEPTION)disabled-macro-expansion`（= `-Wno-error=disabled-macro-expansion`），
  把 OHOS sysroot 自引用/递归宏（stdin/stdout/stderr 与 ctype 助手 isprint 等）触发的
  `-Wdisabled-macro-expansion` 从硬错误降级为警告，对所有对象生效（避免逐对象豁免连环失败）。
  与上游对 lexer.o/parser.o 的既有处理机制一致。

注：上一轮曾加入 0003（os_find_self/readlink 加固），经本轮真机逐用例诊断证明 tsim 实际正常、
 0003 并非根因，已移除（patches/、conandata、manifest、test_package MANIFEST、交付物均同步清理）。

## 依赖版本
- 构建期 tool_requires：`flex/2.6.4`、`bison/3.8.2`（用于再生成 lexer/parser）
- 运行时依赖：无

## 上游测试审计
tenyr 提供 `make check` → `check_sw`（软件）+ `check_hw`（Icarus Verilog 硬件仿真，OHOS 无 iverilog 工具链，不纳入）。
配方运行 `make check_sw`，其测试程序登记口径（与审查员实测 N=112 一致）为：
**check_sim 44 程序 + check_compile 66 程序 + SDL 门控 2 用例 = 112**。

- **op 测试（16）**：test/op/add and andn at eq gte lsh lt mult or orn pack rsha rshl sub xor
- **run 测试（25）**：test/run/at_rigorous code_modification escapes increment-set jitops linked longname loop overshift_type0/1/2 precedence px reloc reloc_maths reloc_pass reloc_set reloc_shifts reloc_special selfmod strings sugar sugar2 unary zero
- **示例 demo（3）**：ex/qsort_demo bsearch_demo trailz_demo
- **正汇编（41）**：test/pass_compile/*.tas（must assemble，日志 `[ TAS ] <file>.tas`）
- **负汇编（25）**：test/fail_compile/*.tas（must fail，日志 `failed as expected`）
- **SDL 门控（2）**：led、bm_mults（mk/misc.mk `SDL_RUNS`，仅在 `ifneq ($(SDL),0)` 时注册）

check_sim 的 44 个程序 × 2 个模拟器风格（interp、interp_prealloc）= **88** 次执行，日志逐条打印
`Testing ... (sim,<flavour>) ... ok`，可直接解析计数。本地原生验证：88 执行全部 ok，0 失败。
check_args/check_behaviour/check_obj/dogfood 为外壳断言，不纳入计数口径。

真机执行 110（44 sim + 66 compile），110 通过、0 失败；2 个 SDL 设备用例在 SDL=0
软件核心下不注册/不执行（environment gap，与上游 CI wine job 的 SDL=0/JIT=0 配置一致）。

`upstream_test_total: 112`、`upstream_test_count_method: "auto"`（单一且可解析的 make-check 测试程序登记）；
实际通过数以真机 conan create 的 make check_sw 日志为准。

## HMBS 机器证据标记（rule4 硬门禁）

配方的 `build()` 运行 `make check_sw` 并把输出重定向到 `check_sw.log`，随后：
- 用确定性解析源统计测试程序：check_sim 每行 `... (sim,(interp|interp_prealloc)) ... ok`
  对应一次模拟执行，按程序去重得 44 个程序；尾部 `ok` 仅在 `$(run) && $(MAKESTEP) ok`
  成功时打印，故失败的规则不会在该行带 `ok`（源码：mk/misc.mk test_op_%/test_run_%/test_demo_%）。
- check_compile 段（`Building tests from test/` … `Done building in test/.`）统计
  `[ TAS ] <file>.tas` 41 个（正汇编）+ `failed as expected` 25 个（负汇编）= 66 个程序。
- 聚合：`executed=110`（44 sim + 66 compile）、`passed=110`、`failed=0`；
  上游注册总数 `discovered=112`（另 2 个 SDL 设备用例 led/bm_mults 在 SDL=0 下不注册），
  `skipped=2`，`gaps=[{count:2, category:"environment", ...}]`。
- 输出 `HMBS_UPSTREAM_TEST_RESULT={"status":"incomplete","framework":"make-check",
  "discovered":112,"executed":110,"passed":110,"failed":0,"skipped":2,...}`。
  rule4 语义：`passed` 等价要求 `passed == discovered`（100%）；存在 gaps 时状态必须为
  `incomplete`（libngf/0.28、libm2k/0.9.0、libambix/0.1.2、odiff/4.5.0 先例）。
  上一轮 110/110 却标 `passed` + `skipped=2` + gaps，被判「passed 状态与上游结果矛盾」。

`test_package/conanfile.py` 运行 test_tenyr.sh 并把输出重定向到 `test_package.log`，
解析确定性汇总行 `tenyr test result: N passed, M failed`：
- `discovered=N+M`、`passedCount=N`、`passed=(M==0)`。
- 输出 `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":6,"passedCount":6}`。

本地原生（gcc）验证：check_sw.log 88 行 `(sim,*)` 全部以 `ok` 结尾 → sim 44 程序全部通过；
check_compile 段 41 个 `[ TAS ]` + 25 个 `failed as expected` = 66 程序 → executed=passed=110、
discovered=112（含 2 个 SDL 门控）；test_tenyr.sh 输出 `6 passed, 0 failed` → discovered=6、passedCount=6。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（application 工具包，JIT=0/SDL=0 软件核心，flex/bison tool_requires，跑 check_sw，INSTALL_DIR 安装；`configure()` 启用 `tools.env:deactivation_mode=function` 消除 env 脚本的 printenv fork；失败时逐用例打印真实 tsim 报错 + tsim interp smoke） |
| conandata.yml | 官方源码 URL + sha256 + 补丁声明 |
| patches/0001-*.patch | SEXTEND32 精度丢失移植性修复 |
| patches/0002-*.patch | OHOS sysroot 自引用/递归宏（stdin/stdout/stderr/ctype）触发的 disabled-macro-expansion 硬错误全局降级 |
| test_package/ | test_tenyr.sh（真实执行 tas→tld→tsim）+ conanfile + MANIFEST.yml |
| commands.json | 工具包命令声明（tas/tsim/tld） |

## 注意事项
- tenyr 的 Makefile 通过 `ifneq ($(VAR),0)` 在变量未定义时默认启用 SDL/JIT；配软件模拟核心必须传 `JIT=0 SDL=0`。
- **`make install` 也必须带 `JIT=0 SDL=0 PEDANTIC=0 CC=...`**：install 目标是 `all` 的依赖，不带这些标志会重新
  求值并尝试编译 SDL 设备（缺 SDL.h）导致安装失败。build/package 两处标志必须一致。
- make 用 `-j1`（E074：HMDFS jobserver fifo EPERM）。
- 测试/安装需要 bash（misc.mk `SHELL := $(shell which bash)`）；OHOS 的 bash 位于 /data/service/hnp/bin/bash，
  由 profile buildenv PATH 提供。
- 上游 `check_hw`（Icarus Verilog 硬件仿真）因 OHOS 无 iverilog 工具链未执行；配方只跑 `check_sw`。
- **check_sw 的 88 条 sim 测试实际全部通过**：hnp bash 在深路径启动时的 `shell-init: ... getcwd ...` 噪音因
  MAKESTEP -n 无换行被拼到 header 行尾，把成功 `ok` 挤到下一行，导致旧的"同行 `...ok`"正则误判 passed=0。
  配方计数已改为按 header 分块、块内含 `ok`（同行 `... ok` 或独立 `ok` 行）即算通过，兼容原生与 HMDFS 拆行两种格式。

## CI #88335（worker CI-005）修复：Conan 环境脚本 printenv fork 导致 build() 首个 self.run 失败

- 失败现象（CI #88335，conan-build-test）：
  ```
  tenyr/0.9.9: RUN: make -j1 CC=/data/service/hnp/bin/clang JIT=0 SDL=0 PEDANTIC=0
  /system/bin/sh: .../build-release/conan/conanbuildenv-release-armv8.sh[13]: can't fork - try again
  ERROR: tenyr/0.9.9: Error in build() method, line 94  self.run(...)
  ```
  同一日志里 CI 自身脚本也报 `ci/scripts/knowledge_check.sh: fork: retry: Resource temporarily unavailable`，
  说明该 worker 处于 fork 资源紧张状态（E491 forbid_3 / DRAFT-11327 同型）。
- 定位：Conan 对**每一次** `self.run()` 都会把 `conanbuild.sh` source 进子 shell；默认
  `tools.env:deactivation_mode` 未设置时，生成的 `conanbuildenv-*.sh` 用
  `value=$(printenv $v) || ...` 为**每个变量 fork 一次 `printenv`**（正是第 13 行 `done` 处报的
  `can't fork`）。也就是说，在真正执行 `make` 之前，Conan 自己就先把 fork 预算花掉了；
  worker 一紧张，第一条命令就死在环境脚本上，根本到不了编译器。
- 方案（与 libappindicator `ad8048e797`「消除 configure 里的 fork 探测」同类，不改测试口径）：
  在 `configure()` 里 `self.conf.define("tools.env:deactivation_mode", "function")`，
  改用 Conan 内建的 function 反激活模式：生成的 env 脚本只用 shell 内建
  （`eval`/`export`/`unset`），**不再有 `$(printenv ...)` 子进程**，每次 source 少若干次 fork。
  环境变量语义完全不变，未删除/跳过任何测试。
  主配方与 `test_package/conanfile.py` 都加了同一句（消费者测试同样 source `conanrun.sh`）。
- 本地核对（Linux 宿主，conan 2.29.1）：加 `configure()` 后 `conan install` 生成的
  `conanbuildenv-release-x86_64.sh` / `conanrunenv-release-x86_64.sh` 中 `grep -c printenv` = **0**，
  且含 `deactivate_conanbuildenv_* () { ... }` 函数体；未加时默认模式含 `value=$(printenv $v)`。


## CI #90025（worker CI-027）修复：make 解析期 fork EAGAIN 的有限重试（第 2 次同指纹修复，换策略）

- 失败现象（CI #90025，conan-build-test，构建包 archives/t/tenyr/0.9.9）：
  ```
  tenyr/0.9.9: RUN: make -j1 CC=/data/service/hnp/bin/clang JIT=0 SDL=0 PEDANTIC=0
  make: which: Resource temporarily unavailable
  make: uname: Resource temporarily unavailable
  make: /bin/sh: Resource temporarily unavailable
  make: /data/service/hnp/bin/clang: Resource temporarily unavailable
  make: mkdir: Resource temporarily unavailable
  make: *** [Makefile:78: all] Error 127
  ```
  拉取 Buildbot 原始 stdio 日志（logid 537043）逐行核对：失败段 15 行**全部**是
  `Resource temporarily unavailable`，`grep -c 'error:'` = **0**（无任何 clang 语法/符号/链接诊断），
  即失败发生在 GNU make 解析 Makefile 与派发递归子 make 的 `which`/`uname`/`mkdir`/`clang`
  探针处，尚未编译任何 .c。机器人归类的「编译失败（语法/未定义符号/缺链接库）」是误判。
- 与上一轮（#88335，`can't fork - try again`）的关系：**同一 fork 资源耗尽指纹的第 2 次**。
  上一轮方案是 `tools.env:deactivation_mode=function`（消除 env 脚本的 `$(printenv)` fork），
  它降低了每次 `self.run()` 的 fork 次数，但**并不能保证** make 自身在解析期派生的
  `$(shell which/uname/...)` 与递归子 make 的 `mkdir` 一定能 fork 成功；当 worker 资源更紧时
  这些探针仍会 EAGAIN。故本轮**不再重复**上一轮方案，改用不同的实现路线。
- 本轮方案（有限重试，仅在瞬时 fork 指纹上触发；参考 DRAFT-yasw-0.6 / DRAFT-11327 的
  "只对该指纹做有限重试、非该指纹原样上抛"）：
  新增 `_run_capture(cmd, log, attempts=3, delay=10)`：把每条 make 命令的输出重定向到日志，
  并用 `echo $? > <log>.rc` 侧写真实退出码（Conan 的 `self.run(..., ignore_errors=True)` 返回
  `None` 而非 rc，不能直接用它判定）。仅当捕获输出命中
  `Resource temporarily unavailable` / `can't fork` / `fork: retry` / `fork failed: out of memory`
  之一，或**完全取不到退出码**（env 脚本 fork 失败、命令根本没跑）时才重试，最多 3 次；
  非瞬时失败（真实编译/链接错误）**不重试**，以真实 rc 经 `_fail_from_log` 原样上抛。
  `build()` / `check_sw` / `package()` 三处 make 均改走该 helper；`check_sw` 若输出为空
  （重试耗尽仍没跑起来）显式失败，避免产生全 0 的误导性测试结果。
- 本地验证（逻辑单测，不依赖真机）：脚本化 `self.run` 覆盖四种情形——瞬时失败后成功（重试到
  rc=0）、真实编译错误（不重试、rc 原样返回）、env fork 失败取不到 rc（重试后成功）、重试耗尽
  （返回最后一次 rc 且 transient=True）——全部通过。语法 `python3 -m py_compile` 通过。
- 不改测试口径：`make check_sw` 的 88 条模拟用例、计数解析、test_package 断言均未改动。

## 真机 evidence 修复：rule4「passed 状态与上游结果矛盾」（第 2 策略周期）

- 现象（本轮真机预检）：上游测试发现 112、执行 110、通过 110、失败 0、跳过 2，
  但 `HMBS_UPSTREAM_TEST_RESULT` 标 `"status":"passed"` 并附 `gaps`（count=2）→
  rule4 判 `passed 状态与上游结果矛盾`，预检 incomplete。
- 根因：状态判定仍是「failed==0 && check_rc==0 → passed」，未把 `passed==discovered`
  作为 `passed` 的必要条件。rule4 语义下 `passed` 等价 100% 全过；存在 `skipped`/`gaps`
  时必须用 `incomplete`（libngf/0.28、libm2k/0.9.0、libambix/0.1.2、odiff/4.5.0 先例）。
  上一策略周期三次都只在计数/口径上调整，没有改状态语义，故同一判据反复命中。
- 修复（不改测试口径、计数源与断言）：
  1) `conanfile.py` 状态三档：`failed`（check_rc!=0 或 failed>0）→
     `passed`（executed>0 且 passed==discovered）→ 否则 `incomplete`；
     新增 `reason` 说明 44 sim + 66 compile 全过、2 个 SDL 门控用例在 SDL=0 下不可运行。
  2) 失败诊断分支由 `ut_status != "passed"` 改为 `== "failed"`，避免 `incomplete`
     被误当作真实测试失败抛出 RuntimeError（测试实际全过）。
  3) 同步 notes.md / test_package/MANIFEST.yml 的 verification 与 .hmbs/pr-body.md
     通过率（110/112，不再写 110/110=100%）。
- 计数恒等式不变：passed(110)+failed(0)==executed(110)；executed(110)+skipped(2)==discovered(112)；
  gaps 合计 2 == discovered-passed = 2。
- 待验证：下一轮真机预检应输出 `status:"incomplete"` 且不再被判矛盾。
