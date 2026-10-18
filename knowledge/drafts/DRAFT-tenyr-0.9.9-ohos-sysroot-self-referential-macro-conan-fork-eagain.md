# DRAFT-tenyr-0.9.9-ohos-sysroot-self-referential-macro-conan-fork-eagain
> OHOS sysroot 自引用宏触发 -Werror=disabled-macro-expansion 的通用降级与 Conan env fork EAGAIN 防护

## 问题特征（真实日志片段/标记）

真机 compile 阶段在直接引用标准流/字符分类宏的位置报硬错误：


/storage/.../b/src/asm.c:113:38: error: disabled expansion of recursive macro [-Werror,-Wdisabled-macro-expansion]
15 warnings and 1 error generated.
make[1]: *** [.../mk/rules.mk:22: asm.o] Error 1
make: *** [Makefile:79: all] Error 2


同一任务在修复过程中先命中 `tas.c` 的 `in = stdin;`、`out = stdout;`，再命中 `src/common.c` 的 `stderr`，最后命中 `src/asm.c:113` 的 `isprint()`，呈逐对象连环失败。

另一路失败出现在 `build()` 的第一个 `self.run`，尚未真正执行 make：


/system/bin/sh: .../build-release/conan/conanbuildenv-release-armv8.sh[13]: can't fork - try again


同轮 CI 日志伴生 `fork: retry: Resource temporarily unavailable`，说明 worker 的 fork 资源已耗尽。

平台能力上下文（`HMBS_PLATFORM_CAPABILITIES`）显示 `"jobs":1`，构建工具经 `HMBS_BUILD_TOOLS` 指向 hnp 的 cmake/make/ninja/python3。

## 根因

1. **自引用宏**：OHOS sysroot 的 `stdio.h`/`ctype.h` 把 `stdin`/`stdout`/`stderr` 以及 `isprint`/`isspace`/`isdigit` 等声明为自引用宏（如 `#define stdin (stdin)`）。源码中直接使用这些名字时，预处理产生不再展开的递归宏，clang 触发 `-Wdisabled-macro-expansion`。
2. **无条件 -Werror**：tenyr 的 `mk/compiler/clang.mk` 把 `-Weverything` 与 `-Werror=disabled-macro-expansion` **无条件**追加进 `PEDANTIC_FLAGS`（与 `PEDANTIC` 无关），因此配方传 `PEDANTIC=0` 无效，警告被升级为硬错误。
3. **逐对象豁免不可持续**：先豁免 `tas.o/tsim.o/tld.o/serial.o`（stdin/stdout），再补 `common.o`（stderr），又撞上 `asm.o`（isprint）。引用点分散在多个编译单元，逐对象列表天然漏项。
4. **fork EAGAIN**：Conan 默认 `tools.env:deactivation_mode` 未设置时，生成的 `conanbuildenv-*.sh` 对每个环境变量执行 `value=$(printenv $v)`，每 source 一次即多次 fork。fork 紧张的 worker 上首个 fork 就 `EAGAIN`，`build()` 在执行 make 前失败。GNU make 自身的 parse-time `$(shell which/uname/...)` 与递归 `mkdir` 探测同样会撞上该压力，命令行覆盖无法抑制。

## 修复方案（rec）（编号步骤，含具体文件与命令）

1. **全局降级诊断**：在 `Makefile` 顶部加一条，一次性覆盖所有对象的自引用宏诊断（与上游对 flex/bison 生成对象使用 `-W$(PEDANTRY_EXCEPTION)` 的做法一致）：
   make
   CFLAGS += -W$(PEDANTRY_EXCEPTION)disabled-macro-expansion
   
   以补丁 `patches/0002-fix-disabled-macro-expansion-stdin-stdout.patch` 形式落地；hunk 头须基于 pristine tarball 重新生成并用 `git apply --check` 验证可干净应用（曾因 `@@ -115,6` 偏移导致 `hunk no.1 doesn't match source file at line 115`）。
2. **同步登记**：更新 `conandata.yml` 的 `patch_description`、`manifest.yaml`、`test_package/MANIFEST.yml` 与 `notes.md`，说明这是可移植修复而非 OHOS 专用宏。
3. **关闭 env 脚本 fork**：在主配方与 `test_package/conanfile.py` 各加：
   python
   def configure(self):
       self.conf.define("tools.env:deactivation_mode", "function")
   
   生成的 env 脚本改用 shell 内建（`eval`/`export`/`unset`）与 `deactivate_*() {}` 函数体，`grep -c printenv conanbuildenv-*.sh` 应为 0，环境语义不变。
4. **瞬时 fork 有限重试**：`build()`/`check_sw`/`package()` 统一走 `_run_capture`，仅当捕获输出命中 `Resource temporarily unavailable`/`can't fork` 等瞬时指纹或取不到退出码时重试（最多 3 次）；真实编译/链接错误以真实 rc 原样上抛，不重试。`test_package` 仅在无结果行且命中该指纹时重试。
5. **保留真实计数**：上游 `make check_sw` 与 `test_package` 的计数口径零改动，通过解析日志输出 `HMBS_UPSTREAM_TEST_RESULT`（tenyr 为 88/88）与 `HMBS_TEST_PACKAGE_RESULT`（6/6），不以 returncode 猜测。
6. **本地验证**：用同版本 flex 2.6.4/bison 3.8.2 + clang 本地构建 `EXIT=0`，`check_sw` 88/88 全 ok；`conan install` 核对生成的 `conanbuildenv-*.sh` 中 `printenv` 为 0 且含 `deactivate_*` 函数体。真机 attempt 54236/58655 均 `gateOutcome=passed`。

## 禁止策略

- **禁止靠 `PEDANTIC=0` 关闭诊断**：`-Werror=disabled-macro-expansion` 是无条件追加，与 `PEDANTIC` 无关，传参无效，只会让修复轮原地打转。
- **禁止只做逐对象豁免就收工**：必须全局降级；按对象列举会在 `common.o`、`asm.o` 等引用点连环漏项。
- **禁止手改 hunk 行号后不复验**：补丁必须对 pristine 源 `git apply --check` 通过，避免 `hunk doesn't match source file`。
- **禁止用 returncode 猜测测试结果**：必须解析日志中的确定性结果行并输出机器证据标记，零证据不得放行。
- **禁止吞掉真实编译错误重试**：只有瞬时 fork 指纹才重试，真实 rc 必须原样上抛。

## 与相近条目的边界（查重）

- `DRAFT-E672`、`mailx`、`rawrec`、`libnxt`、`ndpi`、`crosstool` 分别针对 GNU 扩展头、编译器路径回退、thin archive、生成头安装、vendor bootstrap，均非本场景内核（自引用标准宏 + 无条件 -Werror + env fork）。
- `DRAFT-13532`、`DRAFT-14257`、`DRAFT-14257-clang15` 命中后连续 3 轮未通过，说明既有技能库未覆盖本场景；本条目以全局降级 + `deactivation_mode=function` + 有限重试组合区分。
- `DRAFT-yasw-0.6`、`DRAFT-11327` 提供 fork 瞬时错误有限重试的先例，本条目将其与 OHOS 自引用宏降级合并为同一适配任务的两条独立失败路径。
- 与 tenyr 特有的 `-j1`/`$PWD`/`os_find_self` 修复不同：那些是 check_sw 运行期问题且多轮被证伪，本条目只覆盖已由 attempt 54236/58655 证实的编译期宏诊断与 env fork 两条主线。

## 适用判断

当同时满足以下条件时套用本条目：

1. OHOS 真机日志出现 `disabled expansion of recursive macro [-Werror,-Wdisabled-macro-expansion]`，且报错位置是 `stdin`/`stdout`/`stderr`/`isprint` 等标准宏的直接引用；
2. 上游构建系统无条件追加 `-Weverything` 或 `-Werror=...`，调 `PEDANTIC` 等开关无效；
3. 或日志在 `self.run` 前出现 `can't fork - try again`/`fork: retry: Resource temporarily unavailable`，伴生 `conanbuildenv-*.sh[...]`。

满足 (1)(2) 时优先全局 CFLAGS 降级；满足 (3) 时优先 `tools.env:deactivation_mode=function`，仍偶发再叠加有限重试。若仅是个别对象的精度/截断类告警（如 `-Wshorten-64-to-32`），应改用显式类型转换的可移植补丁，不属于本条目。
