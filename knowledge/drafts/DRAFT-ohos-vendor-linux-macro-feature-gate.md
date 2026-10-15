# OHOS 定义 `__linux`：厂商 `#if __linux` 特性块被误激活并拉入 Linux 专有头

> 草稿：`draft: true` · contributor_id：`frj__` · 来源任务 xtrs 4.9d（任务号 12210）

## 错误特征

在 OHOS 上构建"用 `#if __linux` 开启 Linux 特性"的上游库时，预处理阶段直接报缺头：

```
trs_cassette.c:79:10: fatal error: 'sys/soundcard.h' file not found
trs_disk.c:48:10: fatal error: 'linux/fd.h' file not found
```

这些头是 Linux 内核/驱动专有头（OSS、软驱控制器），OHOS sysroot 里根本没有；错误
只报"找不到头"，没有类型/符号级提示，容易被误当成"少装了个包"。

## 触发条件

- 平台：OHOS PC / AArch64，OHOS clang（target `aarch64-unknown-linux-ohos`）。
- 代码模式：上游把 `__linux`（或 `linux`）当作**"在 Linux 上启用某特性"的厂商开关**，
  该特性的 `#include` 指向内核/驱动专有头。
- 实测 OHOS clang 预定义（`echo | clang -dM -E -x c -`）：

```
#define __OHOS__ 1
#define __linux  1
#define __linux__ 1
#define linux    1
```

即 `#if __linux` 为真 → 特性块被激活。

## 根因分析

`__linux` / `__linux__` / `linux` 在 OHOS clang 上均为 1，于是任何以 `#if __linux`
判定的**特性开关**都被当成"在 Linux 上"而生效。xtrs 4.9d 实测 10 处 `#if __linux`
需要处理（`trs_cassette.c` / `trs_disk.c`）：

| 位置 | 归属特性 | 误激活后需要 | OHOS |
|---|---|---|---|
| `trs_cassette.c`（`HAVE_OSS`/`OSS_SOUND`） | OSS 声音/卡带直读 | `<sys/soundcard.h>` | 无此头 |
| `trs_disk.c`（物理软驱控制器） | `/dev/fd*` 原始软驱 | `<linux/fd.h>`、`<linux/fdreg.h>` | 无此头 |

注意与"musl 缺 Linux 专有 API"（E102/E147/E148）**不是同一层**：那里是代码块能编译
但引用了 musl 未实现的**符号/类型**（incomplete type / undeclared）；这里是代码块
引用了 OHOS 根本不存在的**内核头文件**，失败在 **include 层**（预处理）。

## 解决方案

**推荐（按能力探测，而非平台身份）**：用 `__has_include` 探测所需头是否真实存在：

```c
/* trs_cassette.c */
-#if __linux
+#if defined(__linux) && __has_include(<sys/soundcard.h>)

/* trs_disk.c */
-#if __linux
+#if defined(__linux) && __has_include(<linux/fd.h>)
```

对 xtrs 批量执行（2 文件 10 处，补丁 `0001-ohos-guard-linux-only-feature-blocks.patch`）：

```sh
sed -i 's|#if __linux|#if defined(__linux) && __has_include(<sys/soundcard.h>)|' trs_cassette.c
sed -i 's|#if __linux|#if defined(__linux) && __has_include(<linux/fd.h>)|'          trs_disk.c
```

收敛后仅"OSS 声音/物理软驱"这些依赖 Linux 内核/驱动的能力在 OHOS 上停用，
纯软件路径（磁盘镜像文件、卡带文件、Z80 核心）不受影响；实测 4 个程序全部编译通过。

**禁止做法**：

1. **用 `!defined(__OHOS__)` / `defined(__OHOS__)` 等平台身份宏判分支**——仓库
   R8/PF5 明令禁止（补丁新增行不得出现私有平台宏，应以 POSIX/能力探测适配）；
   且它按"平台是不是 OHOS"而非"头/能力是否存在"分支，libc/头布局一变仍会带病。
2. 给 OHOS 造 `sys/soundcard.h`/`linux/fd.h` 桩头——只骗过预处理，接口在 OHOS 上
   不存在，运行期仍不可能工作，且会污染后续编译单元。

**备选**：由构建系统探测能力后以特性宏传入（`-DHAVE_OSS=0 -DHAVE_LINUX_FLOPPY=0`），
源码只判断 `HAVE_*`；补丁新增行同样不含平台身份宏。

## 通用性证据

同一判据层面的机制可复现于任意"以 `__linux`/`linux` 判定平台特性"的上游库：

| 语料 | 需要处理的 `#if __linux` | 依赖的 Linux 专有头 |
|---|---|---|
| xtrs 4.9d | 10（`trs_cassette.c` + `trs_disk.c`） | `<sys/soundcard.h>`、`<linux/fd.h>`、`<linux/fdreg.h>` |
| 本仓同类先例 | E102/E147/E148 记录的 `__linux__` 分支（mmsg/cpu-affinity） | musl 未实现的 Linux 专有 API |

关键是**修法层面**：本条的收敛点是"**头/能力是否存在**"（`__has_include`），而
E102/E147/E148 是"**是否有该 libc API**"（分流到无该 API 的路径）——同属"OHOS 误判为
Linux"根因，但子族不同（内核头缺失 vs libc 符号缺失）。

## 查重反证（逐条 vs 既有条目）

- `node tools/kb-check.mjs __linux soundcard "asm/io.h" "linux/fd.h" OSS`：
  `soundcard`/`asm/io.h`/`linux/fd.h` = 0；`__linux` 命中 E102/E147/E148。
- E102/E148（`mmsghdr`/`recvmmsg`/`sendmmsg`）与 E147（`cpu_set_t`/`sched_*affinity`）：
  根因同为"OHOS 被误判为 Linux"，但现象是 **incomplete type / undeclared symbol**
  （编译/类型层），修法是把 OHOS 从 `__linux__` 条件分流到无该 API 的路径。
- 本条是**厂商特性块拉入 Linux 内核/驱动头**（`file not found`，include 层），
  用 `__linux` 而非 `__linux__`，修法在**能力探测层**（`__has_include` guard）。属不同子族。

## 证据

- 宏实测：`clang -dM -E` 显示 `__linux`/`__linux__`/`linux` 皆 1。
- 复现：直接 `make` → `fatal error: 'sys/soundcard.h' file not found`（本族）。
- 修复：补丁（2 文件 10 处）后 `make -j1 … xtrs mkdisk hex2cmd cmddump` → 4 程序全部产出；
  `conan create` 退出码 0，消费者测试 5/5。
- 关联 PR/issue：（路径 C+B，随本 PR 提交草稿）。

## 元信息

- authors: `frj__ <241250055@smail.nju.edu.cn>`
- draft: `true` · contributor_id: `frj__`
