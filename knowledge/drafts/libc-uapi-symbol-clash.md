# Draft: musl 派生 sysroot 下的 libc × 内核 UAPI 同名符号冲突

> 本文件是 `libc-uapi-symbol-clash.kv` 的人类可读配套（promote 时会并入正式条目文档）。
> 类型：**类级问题**（不止单库补丁）——配方体检/门禁脚本 + 修复模板 + 样例库成套交付。

## 1. 现象

在 musl 派生的 OHOS sysroot 上，某些 TU 一旦同时包含 libc 头与内核 UAPI 头，编译期即报
**同名结构重定义**（`error: redefinition of 'struct sockaddr_storage'`，同族还有 `sockaddr` /
`msghdr` / `ifreq` / `in_addr`）。特征：

* **只在"两侧都可见"的 TU 里爆发**：同一工程其它 TU 完全正常，报错文件数与用法无关，只与
  include 组合有关（例如 kea 3.0.3 全树 1436 个 TU，唯一报错点就是 `src/lib/dhcp/iface_mgr_linux.cc`）。
* **与 glibc 环境表现不同**：glibc 的 `linux/socket.h` 用 `#ifndef __GLIBC__` 把 UAPI 侧定义挡掉，
  musl 派生 sysroot 的 UAPI 头往往照抄 bionic（`#include <sys/socket.h>` 且无该互斥），于是同一对
  头文件在 glibc 上永不冲突、在 OHOS 上必然冲突。
* **报错信息指向头文件而非自己的代码**，容易被误判为"上游代码问题"或"sysroot 坏了"。

## 2. 根因

`<net/if.h>`（musl）经 `<sys/socket.h>` 提供 `struct sockaddr_storage` 等定义；随后
`<linux/rtnetlink.h>` → `<linux/socket.h>`（bionic 派生）再次定义同名结构。C 语言不允许结构体
重定义，故编译失败。可移植的隔离手段不是"平台宏"，而是**libc 鉴别探针**——在引入 UAPI 头的
那两行之间临时改名，保持 glibc 路径行为不变：

```c
#if defined(__linux__) && !defined(__GLIBC__)
#  define sockaddr_storage __linux_uapi_sockaddr_storage
#  define RESTORE_SOCKADDR_STORAGE 1
#endif
#include <linux/rtnetlink.h>
#ifdef RESTORE_SOCKADDR_STORAGE
#  undef sockaddr_storage
#  undef RESTORE_SOCKADDR_STORAGE
#endif
```

完整形态（含多个符号、guard 收尾）见 `knowledge/tools/libc-symbol-clash/libc-detection-guard.md`。

## 3. 实证（Kea 3.0.3 全族）

* 上游源码树 1436 个 TU，检测器唯一 HIGH 命中：`CLASH-001` `sockaddr_storage` @
  `src/lib/dhcp/iface_mgr_linux.cc` —— 与归档补丁实际修改的文件一致。
* 归档补丁 `archives/k/kea-hook-host-cmds/3.0.3/patches/0002-src-lib-dhcp-iface_mgr_linux.cc.patch`
  （host-cmds / lease-cmds / perfmon / radius / stat-cmds / lease-query / limits 全族逐字节一致）以
  上述形态 A 修复；`patch -p1 --dry-run` rc=0、应用 rc=0。
* 打补丁后复测：HIGH 清零，`--min-severity HIGH` 退出码 0（该符号降级为 `guarded`/LOW 留痕）。

## 4. 检测与门禁

```bash
# 体检（无 sysroot 亦可跑：候选按 confidence 标注）
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py includes --src <src>
# 权威口径 + 可当门禁（可判绿）
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py includes --src <src> --sysroot "$OHOS_SYSROOT" --min-severity HIGH
# 补丁面：禁平台宏 __OHOS__
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py lint --patches <patches/>
# sysroot 侧体检：哪些符号在两侧都声明
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py sysroot --sysroot "$OHOS_SYSROOT"
```

设计要点：内置基线（8 条，`verified`/`candidate` 分层）→ 无需 sysroot 也能给候选；给 `--sysroot`
时按"两侧实测同现"收敛并剔除未复现候选；TU 内已有 guard 见证（`#define <ident> <新名>` /
`#undef <ident>`）时降级为 LOW，从而使同一命令既能体检、也能在修复后判绿。

## 5. 边界与已知局限

* 只覆盖 **libc × 内核 UAPI** 这一类；C++ 标准库/编译器内置的同类冲突不在此列。
* 无 sysroot 时 `candidate` 条目是"同族已知重叠"推断，须以 `sysroot` 模式复核后再当结论。
* "已 guard"判定是文本级的（同 TU 内出现改名/还原即视为已处理），不保证覆盖该 TU 的所有使用点；
  最终仍以 `conan create` 结果为准。
* 修复形态刻意不用平台宏（`__OHOS__`），原因见 `.gitcode/code-style.md` 与 CI 门禁 PF5：平台宏在
  非鸿蒙构建上语义缺失，且会随平台演进失效；libc 鉴别探针表达的是"musl 与 glibc 的差异"这一
  真正的原因。
