# pingu 1.5.1 适配笔记

## 编译环境

- 构建系统: 手写 `./configure`（shell 脚本，非 autotools）+ GNU make
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4（OHOS sysroot，os=OHOS 6.0 / armv8）
- 依赖: libev/4.33（Conan 预编译包，shared）
- 状态: built（本地 W3 `conan create` + 6 条 test_package 用例全绿）

## 上游测试清点（R51 三步法第 1 步）

| 检查项 | 结果 |
|---|---|
| `tests/` 目录 | 不存在 |
| `*test*.c` 源文件 | 0 个（17 个 .c 全是产品代码） |
| `configure` 中的 check/test 分支 | 无（仅 strlcpy/libev 探测） |
| `Makefile` / `src/Makefile` 目标 | 仅 `all` / `install` / `clean` |
| `make check` | `make: *** No rule to make target 'check'. Stop.` |
| README.md | 只描述 libev、asciidoc 两个构建要求，未提测试 |

结论：**上游没有自动化测试入口**，本库不修改上游测试用例（无测试用例可改）。
适配方新增 `test_package/test_pingu.sh` 作为可执行回归测试（6 条用例，含 1 条鸿蒙特有检查），
该测试不替代上游统计（上游统计为 0）。

## 编译步骤

```bash
# 依赖（conan，已在制品仓验证可消费）
conan download "libev/4.33" -r=ohpcd

# 构建
./configure --prefix=/usr --exec-prefix=/usr --sysconfdir=/etc \
            --localstatedir=/var --disable-doc
make -j4

# 验证（W3）
conan create archives/p/pingu/1.5.1 -pr ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 `libev is required`（libev 明明已就位） | 手写 configure 用 `pkg-config --exist libev` 探测，pkg-config 只有 `--exists`，探测恒失败 → 回退 `LIBEV_LIBS="-lev"`，不带 `-I/-L`（E568 手写 configure 系） | 补丁 0001 把 `--exist` 改成 `--exists`，并让配方用 `PkgConfigDeps` 生成 libev.pc |
| 2 | `mtu.c: redefinition of 'sockaddr_storage'`、`netlink.c` 同报 | musl 派生 sysroot 的 `<linux/socket.h>` 不像 glibc 那样屏蔽内核 UAPI 结构，同一 TU 里 libc 头与 netlink UAPI 头双双生效（E1604） | 补丁 0003-0007：在引入 UAPI 头窗口内用 libc 鉴别探针 `#if defined(__linux__) && !defined(__GLIBC__)` 重命名内核侧 `sockaddr_storage`，出窗口 `#undef`；不使用 `__OHOS__` 平台宏 |
| 3 | `pingu_adm.c / pinguctl.c: 'ev.h' file not found` | `src/Makefile` 的对象规则展开 `$($@_CFLAGS)`（`$@` 是 `pingu_adm.o`），永远匹配不到 `pingu_CFLAGS`，`LIBEV_CFLAGS` 被丢弃；只有 libev 在默认 include 路径时才碰巧通过 | 补丁 0002：`$(pingu_OBJS) $(pinguctl_OBJS): CFLAGS += $(LIBEV_CFLAGS)` |
| 4 | `configure` 探测程序写 `/tmp` 报只读 | OpenHarmony 上 `/tmp` 只读（E002） | 配方在 `generate()` 里把 `TMPDIR` 指到 build 目录（随 `conanbuild` 环境注入） |
| 5 | `make install` 报 `install: No such file or directory` | OHOS 用户态无 coreutils `install(1)`（只有 busybox applet） | 不在 package() 里调用 `make install`，直接拷贝 `pingu`/`pinguctl`/`mtu`/`pingu.conf` 到包内 `sbin/`、`bin/`、`etc/pingu/` |

## 源码修改（patches/）

| 补丁 | 内容 |
|------|------|
| 0001-configure.patch | `pkg-config --exist` → `--exists`（上游拼写错误，导致探测恒失败） |
| 0002-src-Makefile.patch | 把 `LIBEV_CFLAGS` 显式加到 pingu/pinguctl 对象上（对象规则变量名缺陷） |
| 0003..0007 | 5 个 TU（mtu.c / netlink.c / pingu_host.c / pingu_iface.c / pingu_netlink.c）在引入 UAPI 头期间用 libc 鉴别探针重命名 `sockaddr_storage` |

补丁均不含平台宏（R8），glibc 路径行为逐字不变。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| libev | 4.33 | Conan `ohpcd` 制品仓（shared，os=OHOS/armv8/clang15） | 上游要求 libev 3 或更新 |

可选依赖 `lua`（`--with-luapc`，默认关闭）与 `asciidoc`（`--disable-doc` 关闭）未启用，
与上游默认配置一致。

## 验证结果

```bash
# W3（conan create + test_package）
pingu/1.5.1: Checking for libev: yes
PASS [T1] pingu -V -> 'pingu 1.5'
PASS [T2] pingu -h prints usage and exits 1
PASS [T3] pingu -d -c <missing> reports the configuration error and exits 1
PASS [T4] pinguctl -a <missing socket> reports the socket error and exits 1
PASS [T5] mtu without arguments prints usage and exits 3
PASS [T6] OHOS/musl build: interpreter=/lib/ld-musl-aarch64.so.1, NEEDED libev.so, netlink glue linked
pingu test summary: PASS=6 FAIL=0 SKIP=0
```

产物：`sbin/pingu`、`sbin/pinguctl`、`bin/mtu`、`etc/pingu/pingu.conf`。

## 注意事项

- `pingu -V` 输出 `pingu 1.5` 而不是 `1.5.1`：上游 `configure` 里 `PACKAGE_VERSION=1.5` 是硬编码，
  且源码包没有 `.git`，顶层 Makefile 的 `git describe` 分支不会生效。这是上游行为，未打补丁修改。
- 默认路径在编译期固化：`/etc/pingu/pingu.conf`、`/var/run/pingu/pingu.pid`、
  `/var/run/pingu/pingu.ctl`（可用 `-c/-p/-a` 覆盖）。
- `pingu` 会修改策略路由/多路径路由表，运行需要 root 与 netlink 权限；
  本次未在真机上启动守护进程做路由变更测试（避免改动共享主机路由），只验证二进制可执行路径。
- 未做 L2/L4/L5 之外的运行时压力测试（守护进程常态运行行为需真机 root）。
---

**编译结束**: 2026-10-17 20:51
**最终状态**: built
