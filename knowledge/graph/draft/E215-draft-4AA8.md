# E215 — OHOS musl struct udphdr 成员名差异（BSD 风格 uh_* vs glibc source/dest/len/check）

## 错误特征

在 HarmonyOS PC（OHOS musl）上编译直接构造 DHCP/UDP 报文的 C 项目时，编译器报：

```
src/dhcp.c:110:24: error: no member named 'dest' in 'struct udphdr'
        if (67 != htons(udph->dest) && 68 != htons(udph->dest))
                       ~~~~  ^
src/udp.c:131:24: error: no member named 'source' in 'struct udphdr'
```

同类成员 `dest`、`source`、`len`、`check` 均不存在。

## 触发条件

- 构建系统: autotools / make（直接 `#include <netinet/udp.h>` 的 C 代码）
- 阶段: 编译（compilation）
- 平台: OHOS musl（aarch64-unknown-linux-ohos，OHOS SDK sysroot）

## 根因分析

HarmonyOS musl 的 sysroot 头文件 `usr/include/netinet/udp.h` 中 `struct udphdr` 采用 **BSD 风格成员名**：

```c
struct udphdr {
    uint16_t uh_sport;
    uint16_t uh_dport;
    uint16_t uh_ulen;
    uint16_t uh_sum;
};
```

而 glibc 风格为 `source` / `dest` / `len` / `check`。上游 dhcpstarv 源码按 glibc 假设编写，直接访问 `udph->dest` 等成员，因此编译失败。

两者均为 4 个 `uint16_t`，结构体布局一致，仅是**成员名命名约定差异**，不存在字节序或布局问题，修复方式为成员名映射。

## 解决方案

### 推荐方案（patch 成员名）

将 glibc 风格成员名替换为 OHOS musl BSD 风格：

| glibc | OHOS musl |
|-------|-----------|
| `udp->source` | `udp->uh_sport` |
| `udp->dest` | `udp->uh_dport` |
| `udp->len` | `udp->uh_ulen` |
| `udp->check` | `udp->uh_sum` |
| `udph->dest` | `udph->uh_dport` |

dhcpstarv 涉及两处（已合入 PR #3951 补丁）：

- `patches/0002-dhcp.c-udphdr.patch`：`udph->dest` → `udph->uh_dport`（src/dhcp.c:110）
- `patches/0003-udp.c-udphdr.patch`：`source/dest/len/check` → `uh_sport/uh_dport/uh_ulen/uh_sum`（src/udp.c:131-134）

### 回退方案（条件编译）

若需同时兼容 glibc 与 OHOS musl：

```c
#ifdef __OHOS__
    udph->uh_dport
#else
    udph->dest
#endif
```

### 禁止做法

- ❌ 在头文件层面 `typedef struct udphdr` 或 `#define dest uh_dport` 重定义系统结构体/宏——污染全局命名空间，影响其他翻译单元。
- ❌ 按 glibc 偏移对结构体 `memset` 后手工赋值——绕过成员名检查，失去可移植性。

## 验证

```bash
# 1. 确认 OHOS musl 头文件成员名
grep -n -A 6 'struct udphdr' /data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot/usr/include/netinet/udp.h

# 2. 修复后编译（dhcpstarv 0.2.3）
cd build_in_harmonyos && conan create archives/d/dhcpstarv/0.2.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 3. smoke test
dhcpstarv --help   # 打印 "dhcpstarv - DHCP starvation utility 0.2.3"，退出码 0
```

## 可复用场景

任何依赖 `netinet/udp.h` 并以 glibc 风格成员名访问 `struct udphdr` 的 C 库（DHCP、TFTP、网络探测等工具类库）均可复用此诊断模式与成员名映射修复。

## 关联条目

- 相关: E007（config.guess/config.sub OHOS 三元组）——同为 OHOS 头文件/工具链差异类
- 来源 PR: #3951（dhcpstarv 0.2.3，路径 B + HarmonyOS 系统差异专项候选）
