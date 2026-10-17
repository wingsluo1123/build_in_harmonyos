# DRAFT-sphde-1.4.0-autotools-portability-fix-family

> autotools 系库在 OHOS 的编译/测试可移植修复族：clang -Werror 告警抑制、toybox install -c 64 接管 INSTALL、ac_pwd $PWD 回退与 make check LOG_COMPILER 逐测试超时

## 问题特征（真实日志片段/标记）

sphde/1.4.0 真机预检在 compile/configure/package/test_package 多个阶段依次暴露缺陷，均为 autotools 系库与 OHOS 平台的共性冲突：

- **configure abort**：`configure: error: working directory cannot be determined` —— HMDFS 上 getcwd(2) 沿 `..` 上溯失败，shell pwd 内建回退 getcwd 也失败，autoconf 的 `ac_pwd` 检查直接中止。
- **补丁解析失败**：`error: patch stream is incomplete!` / `source file is different - b'configure'` / `actual: b'}'` —— hunk 头声明的行号/行数与 tarball 自带 configure 不符，GNU patch 靠 offset/fuzz 勉强应用，Conan 用更严格的 patch_ng 解析即拒绝。
- **clang 独有告警被 -Werror 泛化**（OHOS 编译恒含 `-Wall -Werror`）：
  - `argument unused during compilation: '-mhtm' [-Werror,-Wunused-command-line-argument]`
  - `unknown type name 'key_t'`（sasshm.h 传递包含链未先提供 `<sys/types.h>`）
  - `unused function 'SASCompoundHeapPercentFree' [-Werror,-Wunused-function]`
  - `variable 'touch' set but not used [-Werror,-Wunused-but-set-variable]`
  - `format specifies type unsigned long but the argument has type unsigned long long [-Werror,-Wformat]` 与 `taking the absolute value of unsigned type has no effect [-Werror,-Wabsolute-value]`
  - `incompatible integer to pointer conversion`（`strerror_r`：glibc GNU 版返回 `char*`，musl 恒返 `int`）
- **package 安装失败**：`[Makefile:...: install-libsphdeincludeHEADERS] Error 64` —— autoconf 将探测到的 toybox `install -c` 烘焙进 `INSTALL/INSTALL_DATA`，HMDFS 下 `-c` 路径返回退出码 64。
- **make check 无限挂起 / 平台崩溃**：`FAIL: sphsinglepcqueue_ttt`、`Signal 31 (core dumped)`（SIGSYS，OHOS seccomp 阻断 System V shm/固定地址 mmap）、上游 `make check` 单测无界自旋拖垮整作业；`test_package` `passedCount=158`（崩溃码 `128+31` 越界）门禁判定非法。

## 根因

autotools 系 C/C++ 库在 OHOS 真机常遇四类共性可移植问题，本轮 sphde 恰好逐类触发且答案可跨库复用：

1. **clang -Werror 失配**：上游 `AM_CFLAGS/AM_CXXFLAGS` 恒含 `-Wall -Werror`，本来按 GCC 构建（GCC 对 static inline 豁免 -Wunused-function、不报 -Wunused-but-set-variable 等），OHOS 用 clang 后这些「无害但 clang 独有」的告警全部被 `-Werror` 提升为致命错误；`-mhtm` 这类架构特有探测接受（Accept）≠真正使用（Use），aarch64 clang 接受但无硬件事务内存即报 unused-argument。
2. **HMDFS 路径/安装语义**：getcwd 上溯失败断送 configure；toybox `install -c` 在 HMDFS 权限/UUID 映射下退出 64、无 GNU coreutils、HMDFS 不支持 chmod，`make install` 头文件列表即失败。
3. **libc 差异**：musl 的 `strerror_r` 恒返 int、glibc 内部 `__pid_t` 未暴露、`<sys/ipc.h>` 传递包含的 `key_t` 顺序变化，均触发编译错误。
4. **平台功能限制**：OHOS seccomp 阻断 System V 共享内存与固定地址 `mmap(MAP_FIXED)` → SIGSYS，上游多线程 SPSC 测试的无界自旋 `while(SPHSinglePCQueueFull/Empty) sched_yield();` 在共享内存语义下双双自旋不推进 → make check 永不结束（属 ohos_feature gap，非缺依赖、不可用 CFLAGS 抑制）。

## 修复方案（rec）

1. **补丁生成与验证基线**：所有补丁基于官方 tag release tarball（sha256 核验），用 `diff -u` 从原样文件生成、补足尾随空行使 hunk 体行数与头声明一致；在 `/tmp` 用官方 tarball 按 0001→…→顺序以 GNU patch `--fuzz=0` 与 Conan 同源 `patch_ng`（`fromfile` 非 None + `apply(strip=0, root, fuzz=False)` 全 True）严格验证；`conandata.yml`/`manifest.yaml`/`notes.md` 同步登记。
2. **configure ac_pwd $PWD 回退**：把 configure 的 `ac_pwd=\`pwd\`` 改为 `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"`；`build()` 里在 apply 补丁与 configure 之前 `os.chdir(self.build_folder)` 并 `os.environ["PWD"]=self.build_folder`，让 shell pwd 内建直接信任有效 PWD。
3. **AX_CHECK 探测对齐真实告警级别**：将 `-mhtm` 探测编译命令改为 `CFLAGS="$CFLAGS -Wall -Werror -mhtm"`，使探测在真实告警级别下进行，aarch64 clang 探测失败即不注入 `-mhtm`、不注册 HTM 条件类型。
4. **头部自包含**：给 `src/sasshm.h` 在 include 守卫后显式 `#include <sys/types.h>` 提供 `key_t`。
5. **clang 告警抑制族（0006/0008）**：在 `src/Makefile.in` 的 `AM_CFLAGS/AM_CXXFLAGS` 末尾（位于 `-Werror` 之后生效）追加 `-Wno-unused-function -Wno-unused-but-set-variable`，再并入 `-Wno-format -Wno-absolute-value`；只关无害告警类、不动功能、不影响 make check 用例。
6. **source 可靠性 / 生成规则剪除**：`sources.url` 改为镜像优先有序列表（前置 gh-proxy.com、官方兜底、sha256 不变）；`dist_doc_DATA` 改为仅 `COPYING` 并删除依赖 `#!/bin/bash` 的 `generate-changelog.sh` 生成规则（OHOS 无 /bin/bash，Error 126）。
7. **libc 可移植改写**：`__pid_t`→`pid_t`；`strerror_r` 改可移植写法（忽略返回值、预清零 buf、从 buf 读消息），去掉对 glibc GNU 返回值类型的依赖。
8. **toybox install 接管（package 阶段）**：采用 E596 openfst-family 已验证方案，以 index-install（非 `-c`）或其他安装动作接管 autoconf 烘焙进 `INSTALL/INSTALL_DATA` 的 toybox `install -c`，绕过退出码 64。
9. **LOG_COMPILER 逐测试超时**：`build()` 写纯 sh 的 `test-timeout-wrapper.sh`（后台 watchdog `kill -0`，超时 kill，默认 `SPHDE_TEST_TIMEOUT=300s`）并 `setenv LOG_COMPILER` 指向它；sphde 生成 Makefile 未定义 LOG_COMPILER，环境变量被 GNU make 采纳并随递归子 make 传播进 `src/`，把每个上游测试限制在超时内，挂起测试被 kill 后 automake 记为 FAIL 并归入 ohos_feature gap。
10. **如实申报平台 gap 而非伪造通过**：test_package `passedCount` 按 rc 语义三分支（0→6、1..6→rc-1、其它即信号/未完成→0），保证恒为合法整数；`if not passed_bool and not gaps:` 才 raise —— 已如实上报的 ohos_feature gap（SIGSYS、shm/mmap 阻断、14/23 上游崩溃）不再硬判为构建失败，非平台的真失败仍会 raise；计数只读 `test-suite.log` 单一来源，不伪造 100%。

## 禁止策略

- 禁止伪造通过：`HMBS_UPSTREAM_TEST_RESULT` 不得虚报 passed 数量，不得用崩溃码越界计数（如 passedCount=158）充当通过，Signal 31/SIGSYS 不得硬判为失败或硬改写为通过。
- 禁止伪造 `L1_RESULT=pass` / 注入虚假通过标记；平台限制必须走 gaps(ohos_feature) + 源码定位证据如实申报。
- 禁止对随机的资源型环境故障（`can't fork - try again`，fork EAGAIN）做无意义改动——先复核配方无 fork 爆炸/失控子进程，确属环境故障则仅记录证据。
- 禁止臆造补丁：hunk 必须来自 tarball 原样文件且 fuzz=0 可应用，不得依赖 offset/fuzz 蒙混；不得手写多 hunk 静默漏 hunk。
- 禁止用 `-Wno-*` 抑制掩盖真实功能缺陷/平台 gap，抑制对象只能是 clang 独有的无害告警。

## 与相近条目的边界（查重）

- **vs DRAFT-openfst-1.4.1-install-c-64-force-install**：本条目将 toybox `install -c 64` 问题并入更大的 autotools 移植修复族并给族级定位，openfst 条目聚焦单点的 install 接管，二者互为支撑而非重复。
- **vs DRAFT-viennarna-1.0.0-ac-pwd-getcwd-fallback**：ac_pwd $PWD 回退在本条目作为 autotools 族的一个成员被泛化，viennarna 条目是该单点独立师生；不抹消原单点条目。
- **vs DRAFT-ccrtp-1.0.0-demo-as-upstream-regression**：ccrtp 处理「上游无 formal 测试时把 demo 提升为回归套件」，本条目处理的是「测试存在但被平台/编译/超时问题卡住」的移植性修复，领域不重叠。

## 适用判断

当目标库满足以下任一特征时优先套用本条目：

- 用 autotools（configure + Makefile.am）构建、以 clang + `-Wall -Werror` 编译，出现 clang 独有告警被提升为致命错误；
- configure 在 HMDFS 上因 getcwd/ac_pwd 失败而 abort；
- make/patch 阶段遭 `patch stream is incomplete`/`source file is different` 等严格补丁解析失败；
- `make install` 因 toybox `install -c` 退出 64 而失败（无 GNU coreutils）；
- make check 存在无界自旋/长挂测试，或依赖 System V IPC/固定地址 mmap 触发 SIGSYS。

判定为【知识库扩展】核心依据：所有修复均为可复用于任意 autotools/C/C++ 库的通用内核（`-Wno-*` 告警抑制、`install -c 64` 接管、`ac_pwd $PWD` 回退、`LOG_COMPILER` 逐测试超时），对单库做了 10+ 轮补丁与多类跨库可迁移修复，且经真机门禁验证（passed）、方法经 patch_ng/GNU patch fuzz=0 严格验证，证据充分。
