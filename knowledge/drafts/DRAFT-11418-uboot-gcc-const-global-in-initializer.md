# E-DRAFT: 静态初始化器对 const 全局变量成员做下标访问——GCC 扩展 vs C99 6.6（clang 拒绝）

- **触发实例**：u-boot 2026.07 适配（2026-09-30，任务 11418，分支 feat/uboot-2026.07，
  patch 0010-dhcpv6-ethaddr-compound-literal.patch）
- **错误签名**：
  `initializer element is not a compile-time constant` →
  `net/dhcpv6.c:35:62`，note 指向 `include/net6.h:100` 宏展开
  `_ip6_addr.in6_u.u6_addr8[12]`
- **类别**：gcc-extension-dependence
- **严重度**：2（确定性编译失败；修复一行且语义无损，但暴露一整类上游 gcc
  扩展依赖，clang 构建会逐个引爆）

## 症状

```text
/data/storage/el2/base/.conan2/p/b/uboot.../b/net/dhcpv6.c:35:62: error: initializer element is not a compile-time constant
const u8 net_dhcp6_mcast_ethaddr[6] = IPV6_ALL_NODE_ETH_ADDR(dhcp_mcast_ip6);
                                      ~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
.../include/net6.h:100:7: note: expanded from macro 'IPV6_ALL_NODE_ETH_ADDR'
                                  _ip6_addr.in6_u.u6_addr8[12], \
                                  ^~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

## 根因

`include/net6.h` 的宏把「IPv6 组播地址 → 以太网组播地址」的 RFC2464 变换
写成对**实参的成员下标访问**：

```c
#define IPV6_ALL_NODE_ETH_ADDR(_ip6_addr)  {0x33, 0x33, \
    _ip6_addr.in6_u.u6_addr8[12], _ip6_addr.in6_u.u6_addr8[13], \
    _ip6_addr.in6_u.u6_addr8[14], _ip6_addr.in6_u.u6_addr8[15]}
```

而 dhcpv6.c 传入的是一个**声明的 const 全局变量**：

```c
const struct in6_addr dhcp_mcast_ip6 = DHCP6_MULTICAST_ADDR;
const u8 net_dhcp6_mcast_ethaddr[6] = IPV6_ALL_NODE_ETH_ADDR(dhcp_mcast_ip6);
```

按 C99 6.6，非字面量对象的左值不是常量表达式（const 限定也不行）。
**GCC 有历史悠久的扩展**：const 限定、常量初始化的文件作用域对象可以在
常量表达式位置使用（与「static const 数组作数组长度」同族）——上游 CI 用
gcc 构建 sandbox，永远看不到这个错。clang 严格实现标准 → 拒绝。

## 最小修复（复合字面量，标准语义）

把宏实参换成同一初始化器的 C99 复合字面量：

```c
const u8 net_dhcp6_mcast_ethaddr[6] =
    IPV6_ALL_NODE_ETH_ADDR((struct in6_addr)DHCP6_MULTICAST_ADDR);
```

- C99 6.5.2.5p5：文件作用域复合字面量有**静态存储期**；
- 静态存储期对象 + 常量下标 + 成员访问 = 标准常量表达式，gcc/clang 双收；
- 字节值与原形式**完全相同**（DHCP6_MULTICAST_ADDR 正是 dhcp_mcast_ip6 的
  初始化器）；
- `dhcp_mcast_ip6` 全局保留——dhcpv6.c:207/257 仍以值使用它。

**真机最小复现双向验证（设备 clang 15.0.4，t8.c）**：左值形式报错、
复合字面量形式通过，与最终构建失败签名逐字一致。

## 禁忌

- 禁止 `__extension__`/`-Wno-*` 压报错（clang 没有可开启的等价折叠扩展，
  旗标级压制掩盖真违规）；
- 禁止把全局改成非 const（动链接/ABI 语义）；
- 手写字面字节 `{0x33,0x33,0x00,0x01,0x00,0x02}` 是 fallback——能编译但
  与宏解耦，上游改组播地址时静默失配；复合字面量保住派生关系。

## 适用范围与查重

- **适用**：所有 clang 构建的上游 C 项目——「const 全局成员进初始化器 /
  数组长度 / case 标号」的 gcc 扩展依赖是族式问题（u-boot 这类 gcc 为主的
  项目会逐个文件暴露；net6.h 的宏是全树唯一的直接实例，但同族模式
  「宏吃实参做成员下标」值得 grep 预防）。
- **查重**：grep 现有 drafts 无 compound literal / constant expression /
  gcc-extension 条目；E 系列 clang 相关条目多为 typedef 重定义（如本任务的
  wchar 草稿），本条是「常量表达式合法性」维度的不同机制。draft-review
  相似度预期 0.30 以下，建议 create。
