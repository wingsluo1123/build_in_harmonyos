# Draft: FreeBSD 系源码移植 musl/OHOS 的系统性陷阱集 — `__FreeBSD_version` 未定义激活远古兼容块 + musl 缺 BSD 字节序辅助函数

## 使用说明

适用场景：拿到一份 FreeBSD 血统的 C 源码（ports 树内工具、FreeBSD src 移植物、
libbsd 化的 Linux 移植版），要在 OHOS/musl 上交叉编译。本文不是单个符号的
case-by-case（libbsd 假依赖见 DRAFT-rdate/DRAFT-7C3E，getprogname 的
`/proc/self/exe` 能力宏方案见 DRAFT-mesa-24.3.4），而是**预处理器层面的
机制性陷阱**：不改也会"看起来能过静态分析、一编译必炸"的守卫表达式，以及
musl `<endian.h>` 的能力空洞。给出一套编译前静态扫描清单 + 两个可直接
复制的兼容层代码模板。

## 适用范围

- 正向：任何 `#include <sys/endian.h>` / 使用 `leNNenc/leNNdec` /
  `#if __FreeBSD_version ...` / `getprogname()` 的 FreeBSD 系 C 源码。
- 负向：Linux/glibc 原生源码（无 FreeBSD 守卫与 BSD 头）；纯 libbsd 依赖
  审查（先读 rdate/7C3E 两条）；已带完善 portability 层的库（如 libbsd
  消费者已条件化）。

与既有条目的分工：
- getprogname 的**符号级**替换（musl `__progname` 方案）见正式条目 E203
  （libdispatch 贡献）；本文的 static fallback 是最省事形态，需要真实
  程序名时升级为 E203 方案；
- libbsd 假依赖 / 符号探针方法论见 DRAFT-rdate-1.11、DRAFT-7C3E-metastore；
- 本文独有增量：`__FreeBSD_version` 未定义激活远古兼容块的机制与守卫修法、
  musl `<endian.h>` 缺 leNNenc/dec 的兼容层模板、以及"先修守卫再读报错"
  的诊断顺序——这些在既有 getprogname/libbsd 条目中均未覆盖。

## 输入 / 输出定义

输入：上游 .c/.h 文件（或其锁定下载副本）。
输出：一份补丁决策表，三类固定处置：

| 静态扫描命中 | 机制 | 处置 |
|---|---|---|
| `#if __FreeBSD_version < N` | musl 不定义该宏，`#if` 视 0 → `0 < N` 恒真，**FreeBSD 4.x 远古兼容块被激活**（本次实测：`typedef u_quad_t uintmax_t` 与 musl alltypes.h 重定义，直接 error） | 补丁为 `#if defined(__FreeBSD__) && __FreeBSD_version < N` |
| `#include <sys/endian.h>`（或使用 `le64enc/le64dec/le32enc/le32dec`） | FreeBSD 专有头；musl `<endian.h>` 只有字节序宏，**没有** leNNenc/dec 函数族 | 条件包含 + 内联字节序兼容层（模板见下） |
| `getprogname()` | OHOS musl **有符号但头文件不声明**（隐式声明告警 + 格式串 `%s` 收到 int） | 非 FreeBSD 下给 static fallback 或改 `/proc/self/exe`（mesa 草稿方案） |

同时确认**无需处置**的项（避免过度补丁）：`arc4random`（musl 1.2 内建）、
`err/errx`（`<err.h>`）、`timersub`/`struct timeval`、`O_DIRECT`（宏有定义，
open 语义差异交给测试当错误路径覆盖）。

## 兼容层模板（已真机验证 r3 pass）

字节序（插在原 `#include <sys/endian.h>` 位置）：

```c
#if defined(__linux__) || defined(__OHOS__)
#include <endian.h>
static inline void le64enc(void *pp, uint64_t u) {
    unsigned char *p = (unsigned char *)pp;
    p[0]=(unsigned char)u; p[1]=(unsigned char)(u>>8);
    p[2]=(unsigned char)(u>>16); p[3]=(unsigned char)(u>>24);
    p[4]=(unsigned char)(u>>32); p[5]=(unsigned char)(u>>40);
    p[6]=(unsigned char)(u>>48); p[7]=(unsigned char)(u>>56);
}
static inline uint64_t le64dec(const void *pp) {
    const unsigned char *p = (const unsigned char *)pp;
    return (uint64_t)p[0] | ((uint64_t)p[1]<<8) | ((uint64_t)p[2]<<16)
         | ((uint64_t)p[3]<<24) | ((uint64_t)p[4]<<32)
         | ((uint64_t)p[5]<<40) | ((uint64_t)p[6]<<48)
         | ((uint64_t)p[7]<<56);
}
/* le32enc/le32dec 同型，4 字节 */
#else
#include <sys/endian.h>
#endif
```

getprogname fallback：

```c
#if !defined(__FreeBSD__)
static const char *getprogname(void) { return ("<toolname>"); }
#endif
```

## 示例（真实失败链，raidtest 1.3）

naive 补丁（只换 endian 头）→ 交叉编译报：

```text
patched.c:52:18: error: typedef redefinition with different types
    ('u_quad_t' (aka 'unsigned long long') vs 'unsigned long')
typedef u_quad_t uintmax_t;
sysroot/.../bits/alltypes.h:154: note: previous definition is here
```

根因不是 typedef 本身，而是它上方 `#if __FreeBSD_version < 500028` 在
musl 下恒真。补丁 2 加 `defined(__FreeBSD__) &&` 后该错误与随之的
`strtoumax→strtouq` 宏一并消失。**教训：先修守卫表达式，再读后续报错——
不修守卫时后续报错全是噪声。**

## 验证命令

```sh
# 编译前静态扫描三类命中
grep -n "__FreeBSD_version" *.c *.h
grep -n "sys/endian.h\|le32enc\|le32dec\|le64enc\|le64dec" *.c *.h
grep -n "getprogname" *.c *.h
# 交叉编译定性（OHOS SDK）
clang --target=aarch64-linux-ohos --sysroot=$OHOS_SDK/sysroot -O2 -Wall patched.c -o out
```

source_event: raidtest 1.3（FreeBSD ports 工具）2026-10-04 适配：naive 补丁
r0 交叉编译 2 error 9 warning，完整补丁集 r3 真机零告警全门禁 pass。
