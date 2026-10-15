# kea

ISC Kea DHCP 服务器套件（守护进程 + 运行库 + hook 插件 + 公共头文件），
适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

Kea 家族的**伞形包**：与 kea-hooks（callout 框架库）、kea-perfdhcp（压测客户端）
同一源码树（`kea-3.2.0.tar.xz`）的"整机产品面"。

- **守护进程**：`kea-dhcp4`（DHCPv4 服务器）、`kea-dhcp6`（DHCPv6 服务器）、
  `kea-dhcp-ddns`（D2，动态 DNS，源自 `src/bin/d2`）、`kea-lfc`（租约文件
  清理）
- **客户端工具**：`perfdhcp`（DHCP 性能/压力测试）
- **运行库**：全部 `libkea-*` 共享库（asiolink/cc/cfgrpt/config/cryptolink/
  database/d2/dhcp/dhcpsrv/dns/eval/exceptions/hooks/http/log/
  log-interprocess/process/stats/tcp/util 等）
- **hook 插件**：`lib/kea/hooks/` 下的内置 `libdhcp_*.so`（bootp、class_cmds、
  ddns_tuning、flex_id、flex_option、forensic_log、high_availability、
  host_cache、host_cmds、lease_cmds、lease_query、limits、perfmon、
  ping_check、radius、run_script、stat_cmds、subnet_cmds、user_chk 等）
- **公共头文件**：`include/kea/`（`src/lib` 全树安装头，供消费者编译）

> 3.2.0 上游变化：`kea-ctrl-agent` 已被上游移除（发行 ChangeLog），二进制集
> 因此为以上五个。

- 上游项目：ISC Kea 3.2.0（MPL-2.0）
- 安装路径：上游 `sbindir`/`bindir`（本包按 Conan 约定统一落 `bin/`）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件，须固定版本；头文件泄漏进 `kea/dhcp/pkt.h`、`kea/util/str.h` 等安装头（`transitive_headers=True`，与已合入 kea-hooks 同口径） |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端（配置期运行探针需 LD_LIBRARY_PATH） |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（`CRYPTO_DEP`） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

## OHOS 适配要点

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`，使
   `iface_mgr_linux.cc` / `pkt_filter_lpf.cc` 等 Linux 后端源码被选中。
2. **UAPI 头冲突**：OHOS 的 `linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → 包含 netlink 头时用 define-guard 重命名内核侧
   定义（`__linux__ && !__GLIBC__` 守卫，无需平台宏）。
3. **shebang 脚本 execve**：OHOS 内核拒绝 `#!/bin/sh` 脚本直接 execve（EACCES）
   → 同一内核行为的四个暴露面各自处置：① 配置期脚本（`cd-and-run.sh`/`env.sh`/
   `grabber.py`/`config-report.sh`/`mk_cfgrpt.sh`）经 `/bin/sh` 或 python3 全路径
   调用（补丁 0003/0004）；② meson 测试执行器对脚本套件的 spawn 经 `SH`/`PYTHON`
   包装（补丁 0006）；③ run_script hook 的 `ProcessSpawn` 子进程在 execve
   EACCES/ENOEXEC 时以 `/bin/sh` + 同 argv/env 回退（补丁 0007）；④ 构建树辅助
   脚本 `kea-admin`/`keactrl` 去 shebang，依赖 POSIX shell 回退解释（补丁 0008）。
4. **netlink 沙箱限制**：OHOS 应用沙箱禁止 `AF_NETLINK` socket `bind`（EPERM）
   → `iface_mgr_linux.cc` 增加 `getifaddrs()` 回退路径（两段式 Iface 构建；
   netlink 可用时行为不变，回退时无动态接口事件）。
5. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
6. **Meson 工具链**：需同时使用 `PkgConfigDeps`（依赖 `.pc`）与
   `MesonToolchain`；配置期 `cpp.run()` 探针要求 host 共享依赖在
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径。
7. **symlink EPERM**：soname 以真实拷贝落盘，`package()` 含 0 字节自愈。
8. **测试面平台前提**：OHOS 沙箱拒绝 AF_UNIX 路径名 `bind`（EPERM）且 PC `/tmp`
   只读 → 控制通道类用例按同型 `bind` 探针 + 逐用例 `GTEST_SKIP`（补丁 0013-0018，
   skip 消息写明平台语义），测试沙箱与相关套件临时文件路径 `TMPDIR` 优先、
   未设时回退原路径（补丁 0010/0018/0019/0020），`SIOCGIFHWADDR` ioctl 被拒时
   测试 MAC 校验回退 `getifaddrs()` AF_PACKET（补丁 0011）。

## 上游测试

整棵树 Meson 书写 **105** 处 `test()`（1 处 foreach 展开 7 项），19 处条件
不注册（mysql 4 / pgsql 4 / netconf 6 / krb5·gss-tsig 2，另无 sudo 环境
3 处 sudo-* 套件）→ 实测**注册 92 个套件**
（66 gtest + 26 脚本）；源码
`TEST_F 10741 + TEST 1538 + TEST_P 2 = 12281` 个用例宏（列首
`^TEST(_F|_P)?` 锚定，含 38 处 `DISABLED_`）。本包适配整棵树，
**不设套件过滤**，在 `build()` 内真实执行：

```bash
meson test -v --timeout-multiplier 4 -C <builddir>
```

本版本实测（2026-10-04，真机 conan-verify）：92/92 套件全部通过
（`Ok: 92 / Fail: 0`）；gtest 用例级 10544 执行 = **10336 通过 + 208 跳过 + 0 失败**
（跳过 = 154 项平台前提探针 + 54 项上游既有需 root 前提，明细见 `3.2.0/notes.md`）；
26 个脚本套件 26/26 通过。套件过滤为零、名单裁剪为零。

## test_package（消费者视角 + 鸿蒙特有用例）

`conan create` 的 test 阶段真实编译并执行 4 个测试（CMake + `find_package(kea)`）：

| 测试 | 检查项 | 内容 |
|------|------|------|
| `test_kea_api.cpp` | 10 | 按包内头文件编译（含 boost 依赖的 `dhcp/pkt.h`、`util/str.h`），链接 `libkea-exceptions`/`libkea-util`，驱动 `isc::Exception` 异常模型与 `util::str::trim` 真实符号 |
| `test_kea_daemons.py` | 12 | 5 个可执行文件 `-v` 版本输出；`kea-dhcp4`/`kea-dhcp-ddns` 的 `-W` 构建配置报告；`kea-dhcp4`/`kea-dhcp6` 的 `-t` 配置检查（合法退出 0；未知参数/缺失文件非 0） |
| `test_ohos_platform`（**鸿蒙特有**） | 11 | 包内 `bin/kea-dhcp4` 的 OHOS 平台 ABI 特征：ELFCLASS64 / `EM_AARCH64`、`DT_NEEDED` 链接 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so`；OHOS 加载器 `dlopen(RTLD_NOW)` 解析其 libkea-* 闭包 |
| `test_ohos_runtime`（**鸿蒙特有**） | 96 | `lib/` 全部 69 个 `libkea-*.so*` 文件与 `lib/kea/hooks/` 全部 19 个 hook 插件逐个 `dlopen(RTLD_NOW)`（88 项）+ 8 项契约/规模检查；hook 契约 `version()/load()/unload()` 可解析且 `version()==30200` |

鸿蒙特有测试程序 **2 个**，实测 **2/2 通过**（107/107 检查项；连同 `test_kea_api` 10 项
与 `test_kea_daemons` 12 项，test_package 4 个程序合计 **129 项检查全 ok、0 FAIL**）。

## 使用

```bash
conan install --requires=kea/3.2.0 -pr:h=<ohos-aarch64 profile>

# 版本 / 构建配置报告
kea-dhcp4 -v
kea-dhcp4 -W

# 配置检查（不启动服务）
kea-dhcp4 -t /etc/kea/kea-dhcp4.conf

# 启动（需 root 或 CAP_NET_BIND_SERVICE）
kea-dhcp4 -c /etc/kea/kea-dhcp4.conf

# 压测（对 DHCPv6 服务器，100 次 SARR 交换）
perfdhcp -6 -r 100 -n 100 -D 3 -l <iface> <server-address>
```
