# DRAFT-rpcgen-2.6.4: OHOS 无 /etc/netconfig——libtirpc 旧式 clnttcp_create() 报 "RPC: Unknown protocol"，传输层构造器可完全绕开

- **条目 ID**: `DRAFT-rpcgen-2.6.4-ohos-no-netconfig-tirpc-transport-constructors`
- **严重度**: 2（🟡 中等——只影响 TI-RPC 旧式 API 消费者，且编译/链接期完全静默）
- **类别**: portability, libc, ohos, network, conan, testing
- **触发工具/阶段**: libtirpc / clang / ld / 运行期 — testing / runtime
- **来源**: rpcgen 2.6.4 适配（feat/rpcgen-2.6.4，OHOS PC aarch64；test_package 消费者端到端用例首次暴露）
- **路径**: Path B（知识库扩展）；同包 Path A 适配已完成
- **关联**: [[DRAFT-snort-3.12.2.0-ohos-no-rpc-program-db-configure-gate-static-fallback]]（同族：OHOS 的 Sun-RPC 生态缺口——彼为编译期 configure 硬门，本条目为运行期 netid 解析失败）；[[DRAFT-libnfsidmap-ldap-2.6.4-*]]（同树 nfs-utils 姊妹包）

## 症状

在 HarmonyOS PC 上用 libtirpc 做真实 RPC 往返时，客户端构造器直接失败：

```
clnttcp_create: RPC: Unknown protocol
```

程序编译与链接**全部成功**（`-ltirpc` 正常解析），失败只发生在运行期创建客户端句柄这一步。
服务端侧同源问题表现为 rpcgen 生成的 `*_svc.c` 自带 main() 无法注册
（`pmap_unset` + `svc_register(..., IPPROTO_TCP)` 依赖 portmapper）。

实测环境（2026-10-16，鸿蒙 PC HAD-W32 / HarmonyOS / aarch64 / clang 15.0.4）：

```
$ conan install --requires=libtirpc/1.3.7 -pr:h=ohos-aarch64 --build=never   # exit 0，包可得
$ ls -l /etc/netconfig
ls: /etc/netconfig: No such file or directory
$ grep -n 'define NETCONFIG' <libtirpc pkg>/include/tirpc/netconfig.h
8:#define NETCONFIG "/etc/netconfig"
```

## 根因

libtirpc 的**旧式**客户端构造器 `clnttcp_create()`（以及其上的 `clnt_create()`）
在真正建连之前，先要把 netid `"tcp"` 解析成 `struct netconfig`：

```
clnttcp_create() → __rpc_getconfip("tcp") → getnetconfigent("tcp") → 读 netconfig 文件
```

该文件路径是 libtirpc 的**编译期常量**（`netconfig.h: #define NETCONFIG "/etc/netconfig"`）。
实测把 `NETCONFIG` 指向 libtirpc 包自带的 `etc/netconfig` **无效**（仍报同一错误，
说明该版本未读取该环境变量），而 OHOS 上 `/etc` 只读、也没有 netconfig 文件。
解析失败即置 `RPC_UNKNOWNPROTO` 并返回 NULL —— 这就是 "RPC: Unknown protocol" 的全部来源。

对照实验（同一份 rpcgen 生成代码，只换构造器）：

| 侧 | 旧式 API | OHOS 结果 | 传输层 API | OHOS 结果 |
|---|---|---|---|---|
| 客户端 | `clnttcp_create(&sin, prog, vers, &sock, 0, 0)` | ❌ `RPC: Unknown protocol` | `clnt_vc_create(fd, &netbuf, prog, vers, 0, 0)` | ✅ 正常 |
| 服务端 | 生成 main()：`pmap_unset` + `svc_register(..., IPPROTO_TCP)` | ❌ 无 rpcbind | `svc_vc_create(fd,0,0)` + `svc_register(..., 0)` + `svc_run()` | ✅ 正常 |

结论：**netconfig/rpcbind 依赖只存在于旧式 API 外壳**；`*_vc_create` 传输层构造器
用「已连接 fd + 地址」直接工作，在 OHOS 上完全可用（本包 test_package 的两次真实
TCP RPC 往返即以此跑通，业务结果 13/42/81 全部断言通过）。

## 影响面

- 任何在 OHOS 上调用 `clnt_create()` / `clnttcp_create()` / `clntudp_create()` 的消费者；
- 直接使用 rpcgen 生成的 `*_svc.c` 自带 main() 的服务端程序（依赖 portmapper）；
- 以「编译链接通过」为验收口径的流程——该缺陷**编译期零症状**，只有真实往返才暴露。

## 验证命令

```sh
ls -l /etc/netconfig                                        # 期望: No such file or directory
grep -n 'define NETCONFIG' "$(conan cache path libtirpc/1.3.7)"/include/tirpc/netconfig.h
# 反例复现：调用 clnttcp_create() 的消费者 → "RPC: Unknown protocol"
# 正例：改 clnt_vc_create(fd,&addr,prog,vers,0,0) → 往返成功
```

## 建议方案

1. **客户端**：`socket()` + `connect()` 后调用
   `clnt_vc_create(fd, &addr, prog, vers, 0, 0)`（`addr` 为 `struct netbuf{maxlen,len,buf}`，
   `buf` 指向填充好的 `sockaddr_in`）。
2. **服务端**：`bind()`+`listen()` 的监听 fd 交给 `svc_vc_create(fd, 0, 0)`，再
   `svc_register(transp, PROG, VERS, dispatch, 0)`——protocol 传 **0** 表示只做本地注册、
   不联系 portmapper；随后 `svc_run()`。
3. **端口传递**：bind 到端口 0 后 `getsockname()` 取实际端口，经 pipe 交给客户端
   （无 rpcbind 可查询；TCP loopback 在 OHOS 上正常，注意与 AF_UNIX 路径名 socket 的
   限制区分）。
4. **复用 rpcgen 生成的服务端分发器**：其 dispatcher 是 `static`，可在消费者 TU 内
   `#define main <renamed>` → `#include "foo_svc.c"` → `#undef main`，让生成的分发器
   参与真实调用，同时屏蔽依赖 portmapper 的生成 main；生成文件本身保持不改。
5. **验收口径**：必须在目标机执行真实 RPC 往返并断言业务结果，不能只断言非空指针或
   仅编译链接。
6. 若确需 netid 解析/portmapper 语义，须先在 OHOS 侧提供 netconfig 与 rpcbind
   （当前制品仓两者皆无），不要试图用环境变量绕过（实测无效）。

## 判定口径

“换个网络正常的机器能否解决” → 不能（是平台能力缺失，不是网络问题）→ 归类为
**平台适配缺口**，方案是改用传输层构造器，而非等待外部依赖。

## 证据来源

- `archives/r/rpcgen/2.6.4/test_package/calc_consumer.c`（两次真实 TCP RPC 往返，3 项业务断言）
- `archives/r/rpcgen/2.6.4/notes.md` 问题表第 7 条
- 本地完整日志：`$HOME/tmp/rpcgen-recon/consumer/`（原型）与 `conan-create-clean.log`（conan create）
