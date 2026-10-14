# libc 鉴别 guard 模板（musl × glibc 可共存）

> 适用场景：同一份源码要在 OpenHarmony（musl 派生 sysroot，带 bionic 派生 UAPI 头）与
> glibc 发行版上都能编译 —— 典型症状是 `error: redefinition of 'struct sockaddr_storage'`。
>
> 铁律口径（R8 / preflight PF5）：**补丁中禁止 `__OHOS__` 平台宏**（也不要在 conanfile 里
> `-D__OHOS__` 注入，PF5 会拦）。用 **libc 鉴别探针**（`__GLIBC__` / `__UCLIBC__` /
> `__BIONIC__` / `__musl__`）表达差异。
>
> 检测工具：`knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py`
> （`--print-template` 直接输出本模板；`includes` / `sysroot` / `lint` 三个模式分别做
> TU 级体检、sysroot 实测、补丁合规 lint）

## 0. 机理（为什么 glibc 不报、musl 报）

| 侧 | 定义者 | glibc 生态 | OpenHarmony（musl 派生） |
| --- | --- | --- | --- |
| libc 头 `<sys/socket.h>` | libc | `struct sockaddr_storage` | 同左 |
| 内核 UAPI `<linux/socket.h>` | bionic 派生内核头 | `#ifndef __GLIBC__` 守卫 → **不定义** | 无该守卫 → **重复定义** |

因此 glibc 上"同时包含 `<net/if.h>` 与 `<linux/rtnetlink.h>`"毫无问题，musl 派生 sysroot
上必然重定义。修复不是删掉某个 include（那会丢功能），而是**在引入 UAPI 头期间把内核侧的
同名定义改掉**，让 libc 的那份保持权威。

## 1. 形态 A（推荐）：引入 UAPI 头期间重命名内核侧定义

```c
/* 只在非 glibc 的 Linux 上生效；glibc 上内核头本就带 __GLIBC__ 守卫，保持语义最小变更 */
#if defined(__linux__) && !defined(__GLIBC__)
#  define sockaddr_storage __linux_uapi_sockaddr_storage
#  define <PREFIX>_RESTORE_SOCKADDR_STORAGE 1
#endif
#include <linux/rtnetlink.h>          /* 内核头：其内的 sockaddr_storage 被改名 */
#ifdef <PREFIX>_RESTORE_SOCKADDR_STORAGE
#  undef sockaddr_storage
#  undef <PREFIX>_RESTORE_SOCKADDR_STORAGE
#endif
/* 此后 sockaddr_storage 一律指 libc 那份（与 glibc 行为一致） */
```

要点：

* `<PREFIX>` 用库自身前缀（如 `KEA`、`GLIB`），避免不同库的 guard 宏互相污染。
* `#define` / `#undef` 必须**紧包**内核头 include，中间不要插业务代码。
* `!defined(__GLIBC__)` 不可省：省了虽然多数情况无害，但会让 glibc 构建也进入改名分支，
  属于对 glibc 的语义无谓改动，评审会要求收敛。

## 2. 形态 B：冲突来自"先 UAPI 后 libc"的顺序

若内核头在前（例如某个第三方头先引入 `<linux/*.h>`），libc 头在后同样会报重定义。
两种收敛方式：

```c
/* B-1：把 libc 头提到最前，保证 libc 定义先落地 */
#include <sys/socket.h>               /* libc：权威定义 */
#if defined(__linux__) && !defined(__GLIBC__)
#  define sockaddr_storage __linux_uapi_sockaddr_storage
#  define <PREFIX>_RESTORE_SOCKADDR_STORAGE 1
#endif
#include <linux/rtnetlink.h>
#ifdef <PREFIX>_RESTORE_SOCKADDR_STORAGE
#  undef sockaddr_storage
#  undef <PREFIX>_RESTORE_SOCKADDR_STORAGE
#endif
```

```c
/* B-2：把内核头挪到 TU 末尾单独引入（其后不再使用 libc 类型） */
/* ... 业务代码（可用 struct sockaddr_storage）... */
#if defined(__linux__) && !defined(__GLIBC__)
#  define sockaddr_storage __linux_uapi_sockaddr_storage
#endif
#include <linux/rtnetlink.h>
#if defined(__linux__) && !defined(__GLIBC__)
#  undef sockaddr_storage
#endif
```

## 3. 形态 C：项目自身重定义了 libc/UAPI 名字

`detect-libc-symbol-clash.py source` 命中的情形（项目里自己写了 `struct sockaddr_storage`）：

```c
/* 改项目侧名字，不动 libc */
struct <PREFIX>_sockaddr_storage { ... };
```

不要把 libc 的名字 `#define` 掉来给项目让路 —— 那会污染所有包含该头的翻译单元。

## 4. 反例（评审会拒）

```c
/* ✗ 平台宏：不可移植，且 preflight PF5 在建 PR 前就拦下 */
#if defined(__OHOS__)
#  define sockaddr_storage __linux_uapi_sockaddr_storage
#endif

/* ✗ conanfile 里注入平台宏（同样被 PF5 拦） */
self.cpp_info.defines = ["__OHOS__"]
```

## 5. 验证清单（提交前逐项过）

1. `python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py includes --src <src> [--sysroot "$OHOS_SYSROOT"]`
   → 命中清零。给 `--sysroot` 时只报两侧实测同现的符号；已 guard 的 TU 自动降级为 `LOW`
   （`confidence=guarded`），因此 `--min-severity HIGH` 的退出码 0 即可作为门禁判据；
2. `python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py lint --patches <patches/>` → 无 `GUARD-001`；
3. `patch -p1 --dry-run < patches/000X-*.patch` → 干净应用；
4. `conan create` 在干净环境（无缓存）复现构建通过（W3 口径）；
5. 编译期自查：`static_assert(sizeof(struct sockaddr_storage) == <libc 期望值>)`，确认最终生效
   的是 libc 那份定义。

## 6. 实证样例

`archives/k/kea-hook-host-cmds/3.0.3/patches/0002-src-lib-dhcp-iface_mgr_linux.cc.patch`
（Kea 3.0.3 `src/lib/dhcp/iface_mgr_linux.cc`：`<net/if.h>` × `<linux/rtnetlink.h>` 触发
`struct sockaddr_storage` 重定义，按形态 A 修复）。
