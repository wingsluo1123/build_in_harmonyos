# oed 7.4 适配笔记

## 概述

- 软件：**oed**（Portable OpenBSD `ed(1)`，POSIX 行编辑器）
- 上游版本：**7.4**（tag `oed-7.4`，commit `a8965fb17bc7bdebaa1cbf7599bacb1723e8edb3`）
- 上游仓库：https://github.com/ibara/oed
- 上游发布源：https://github.com/ibara/oed/releases/download/oed-7.4/oed-7.4.tar.gz
- 语言：纯 C（C89，14 个 `.c` 文件）；无外部依赖（仅 libc）
- 适配路径：**路径 A（基础适配）+ 路径 B 补全测试**（上游确无测试，见「上游测试清点」）

## 编译环境

- 构建系统: custom（上游自带手写 POSIX sh `configure`，生成纯 Makefile，**非 autoconf**）
- 编译日期: 2026-10-12
- 编译器: clang（设备原生编译，aarch64 / OHOS）
- 状态: published

## 编译步骤

上游用 Brian Callahan 手写的 `configure`（探测 CC、`pledge`、`reallocarray`、`strlcat`、`strlcpy`
并逐个试装 CFLAGS），因此直接驱动 configure/make：

```bash
./configure --prefix=<pkg_prefix> --cc=<clang> --program-name=ed
make -j1
make install              # 上游 install target：install -d / install -c -s -m 755
```

实测 configure 输出（摘自 `reports/conan-create.log`；HarmonyOS 被正确识别，`pledge` 不存在 → 走 `#define` 兜底）：

```
checking for C compiler... <cc>
checking whether <cc> accepts -fPIC... yes
checking whether <cc> accepts -O2... yes
checking whether <cc> accepts -I.... yes
checking for OS... HarmonyOS
checking for pledge... no
checking for reallocarray... no
checking for strlcat... yes
checking for strlcpy... yes
creating Makefile... done
```

注意 `checking for reallocarray... no`：configure 如实判定系统头未声明 `reallocarray`，
于是把 `extern void *reallocarray(...)` 写入 `config.h` 作为兜底声明（见下方问题 4）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ed` 启动即 `cannot open temp file`（`/tmp/ed.XXXXXXXXXX: Read-only file system`），任何命令都无法执行 | HarmonyOS PC 的 `/tmp` 是 **erofs 只读挂载**（`/proc/mounts`：`/dev/block/dm-0 /tmp erofs ro,...`；`/var/tmp`、`/dev/shm`、`/data/local/tmp` 同样不可写）。上游 `buf.c` 把 scratch 文件模板**编译期写死**为 `/tmp/ed.XXXXXXXXXX`，而 `init_buffers()` 在启动时无条件调用 `open_sbuf()` → 必然失败 | 补丁 `0001-buf.c.patch`：`open_sbuf()` 依次尝试 `$TMPDIR` → 编译期内置目录 → `$HOME`，任一可写即用；未设 `TMPDIR` 且内置目录可写的系统（如常规 Linux/macOS）第一次尝试即成功，行为与上游一致 |
| 2 | 产物名随构建机环境漂移：PATH 中已有 `ed` 时会装成 `oed` | 上游 `configure:146-150` 用 `command -v ed` 决定 `prog`，非确定性 | 显式传 `--program-name=ed` 固定可执行文件名 |
| 3 | `make install` 报 `install: No such file or directory`（本机排查） | 本沙箱 shell 的 `PATH` 不含 `/bin`（`/bin/install` 实际存在） | 环境问题，非平台差异；CI 与设备正常 PATH 下无需处理 |
| 4 | 干净构建（G0，`./configure && make`）在 `glbl.c` 报 `reallocarray` 隐式声明 → int 转指针错误（exit 2） | configure 用 `-I$(pwd)` 构造自包含路径（`configure:255,257`）。`getcwd()` 失败的环境（容器/沙箱/已删除的 cwd）下 `$(pwd)` 展开为空，`-I` 变成无参数被编译器探测判为 `no` 而**被丢弃**；于是 `<regex.h>` 命中系统头，树内 `regex.h`（其第 44 行 `#include "config.h"` 带来 `extern void *reallocarray(...)` 声明）不再被包含，而 configure 的 reallocarray 探测如实返回 `no`，其兜底声明只写进 `config.h`、必须经树内 `regex.h` 才可见（详见下方问题 4） | 补丁 `0002-configure.patch`：`-I$(pwd)` → `-I.`。`make` 始终在源码目录执行，语义与上游意图等价且不受 `getcwd()` 影响 |

## 源码修改

共两个补丁，均由 `refresh-patch --auto` 生成，`patch --dry-run -p1` 验证可干净应用。
（说明：本库的 `configure` 是上游**手写 POSIX sh 源码**，不是 autoconf 生成的产物，
因此对它的补丁属于源码修改而非改生成文件。）

### `patches/0001-buf.c.patch`

- 文件：`buf.c`
- 内容：把编译期常量 `SCRATCH_TEMPLATE` 拆成 `SCRATCH_DIR` + `SCRATCH_NAME`，`sfn` 由
  `sizeof(SCRATCH_TEMPLATE)+1` 放大为 `PATH_MAX`；`open_sbuf()` 改为遍历候选目录
  `$TMPDIR` → `SCRATCH_DIR`（默认 `/tmp`）→ `$HOME`，第一个 `mkstemp()` 成功的即采用。
- **不含任何平台宏**（无 `#ifdef __OHOS__` 之类），是通用可移植性修复，`__TERMUX__` 分支原样保留。
- 平台行为影响：`/tmp` 可写的系统（Linux/macOS）第一次尝试成功，行为与上游逐字一致；
  仅当内置目录不可写时才启用回退。

### `patches/0002-configure.patch`

- 文件：`configure`（第 255、257 行）
- 内容：`-I$(pwd)` → `-I.`。
- 原因：`getcwd()` 失败的环境下 `$(pwd)` 展开为空 → `-I` 失效 → 树内 `regex.h` 不被
  `<regex.h>` 命中 → 其中的 `#include "config.h"` 带来的 `extern reallocarray` 声明丢失
  → clang 16+ 对 `glbl.c:155` 的隐式声明报 int 转指针错误。
- **不含任何平台宏**；`make` 在源码目录执行，`-I.` 与上游 `-I$(pwd)` 意图完全等价，
  正常环境下行为不变。

## 上游测试清点（R51 第一步）

| 项 | 结果 |
|----|------|
| `make test` | target 存在但仅 `@echo "No tests"`（configure:406 写入 Makefile） |
| `tests/` 目录 | 不存在 |
| ctest / meson / pytest 注册 | 无 |
| GitHub API tree(`oed-7.4`) | 共 32 项，全部为源码与构建设施，**0 个测试文件** |
| `.travis.yml` | 仅编译矩阵，不运行测试 |
| **上游用例合计** | **0** |

实测证据（原始输出）：

```
$ make test
No tests
$ find . -maxdepth 2 -iname '*test*' | wc -l
0
```

→ 上游确无测试，按 R51 走**路径 B**：在 `test_package/` 补全消费者测试；
`test_package/MANIFEST.yml` 已如实填写 `upstream_tests: []` 与 `assertion_count: 25`。

## 依赖版本

无外部依赖（仅系统 libc）。`conanfile.py` 无 `requires()`；`manifest.yaml` 的
`build.dependencies` 为空。

## 验证结果

消费者测试（真实调用安装出的 `ed` 可执行文件，`test_package/test.sh`）：

```
===== 结果: PASS=25 FAIL=0 =====
全部 25 项断言通过
```

- A 组（18 项，上游功能等价）：新建文件写入、`1,$p`/`2p`/`$p` 寻址、正则替换、
  全局替换、删除行、撤销、`g/^b/d` 全局命令、`r` 读入拼接、就地编辑既有文件、
  非法命令脚本安全契约（`?` 诊断 + 非零退出 + 不落盘）、500 行长缓冲落盘
- B 组（7 项，鸿蒙特有）：`TMPDIR` 可写 / 不可写 / 不存在 / 未设置四种情形下
  scratch 目录回退链均可用，退出后无 `ed.*` 残留

平台行为补充实测：未设 `TMPDIR` 时，`/tmp` 只读 → 经 `$HOME` 回退，`ed` 正常工作
（这条即本适配要解决的核心问题）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `oed-7.4-ohos-aarch64.tar.gz` | 见 packaging/ | release 产物（bin/ed + man/man1/ed.1） |
| `debug-symbols/` | 见 packaging/ | 调试符号 |

## 注意事项

- 鸿蒙上 `/tmp` 只读，任何依赖 `/tmp` 写权限的程序都需显式指定可写临时目录
  （`TMPDIR`）。本补丁已内建回退，使用者无需额外配置。
- `make install` 使用 `install -c -s`，会 strip 二进制；调试符号需从构建目录取未 strip 的 `ed`。
- 上游无版本化的 man page 生成步骤，`ed.1` 直接来自源码树。
---

**编译结束**: 2026-10-12 16:21
**最终状态**: published
