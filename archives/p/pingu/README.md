# pingu

pingu 是一个小型网络守护进程：周期性 ping 一组主机，根据链路连通性重新配置内核策略路由
（policy routing / fwmark 规则、nexthop 多路径），实现多 ISP 环境的故障切换与负载分担，
状态变化时可执行用户脚本。

## 功能概述

- 多 ISP 故障切换：链路 up/down 时自动增删路由与规则
- 负载均衡：nexthop 多路径
- 基于 fwmark 的路由规则（可选）
- DHCP / PPP 链路支持
- 链路状态变化时执行自定义脚本
- 配套工具：`pinguctl`（通过 unix socket 查询/控制守护进程）、`mtu`（PMTU 探测与注入）

## OHOS 适配

适配要点（详见版本级 `1.5.1/notes.md` 与 `patches/`）：

1. **musl sysroot 的 UAPI 头冲突**（知识库 E1604）：OpenHarmony 的 `<linux/socket.h>`
   不像 glibc 那样屏蔽内核 UAPI 的 `struct sockaddr_storage`，与 libc 头同时可见的
   5 个 TU 会报重定义。补丁用 `__linux__ && !__GLIBC__` 探针在引入 UAPI 头期间重命名，
   不使用平台宏。
2. **手写 configure 的 pkg-config 探测拼写错误**（E568 同族）：上游写 `--exist`，
   导致 libev 不在默认路径时必然失败；补丁改为 `--exists`，配方用 `PkgConfigDeps` 提供 `libev.pc`。
3. **src/Makefile 变量名缺陷**：对象规则 `$($@_CFLAGS)` 展开成 `pingu_adm.o_CFLAGS`，
   `LIBEV_CFLAGS` 被丢弃；补丁把 CFLAGS 显式挂到 pingu/pinguctl 的对象上。
4. `/tmp` 只读（E002）：configure 的探测程序改用构建目录内的 `TMPDIR`。
5. OHOS 用户态无 coreutils `install(1)`：配方在 `package()` 中直接拷贝产物，不调用 `make install`。

已知差异/限制：

- `pingu -V` 输出 `pingu 1.5`：上游 `configure` 硬编码 `PACKAGE_VERSION=1.5`，且源码包无 `.git`，
  这是上游行为，未打补丁修改。
- 默认路径在编译期固化：`/etc/pingu/pingu.conf`、`/var/run/pingu/pingu.pid`、`/var/run/pingu/pingu.ctl`，
  可用 `-c` / `-p` / `-a` 覆盖。
- 守护进程运行需要 root 与 netlink 权限，并且会修改策略路由表；本次未在真机启动守护进程做路由变更测试。

## 依赖关系

- 编译依赖：`libev`（>= 3，本仓使用 4.33，Conan 制品仓预编译包）
- 可选：`lua`（`--with-luapc`，默认关闭）、`asciidoc`（生成 man page，`--disable-doc` 关闭）
- 运行依赖：`libev.so`（Conan 动态库，`conanrun` 环境自动注入 `LD_LIBRARY_PATH`）

## 参考资料

- 上游仓库：https://github.com/ncopa/pingu
- 上游发布：https://github.com/ncopa/pingu/archive/refs/tags/v1.5.1.tar.gz
- 发行版来源：Alpine Linux `main/pingu 1.5.1-r0`
