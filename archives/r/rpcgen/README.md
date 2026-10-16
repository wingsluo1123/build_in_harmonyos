# rpcgen

## 简介

Sun/TIRPC 的 **RPC 协议编译器**（`rpcgen`）：读入 RPC 接口定义（`.x`），生成 C 头文件、
客户端存根、服务端存根与 XDR（数据编解码）例程。

上游没有独立发布轨——维护中的副本是 **nfs-utils 源码树的 `tools/rpcgen/`**
（Olaf Kirch 对 Sun TIRPC `rpcgen.new` 的清理版，含 musl/apple 修补）。因此本包
版本号 2.6.4 即 nfs-utils 的版本号，源码取 nfs-utils 官方 tarball；Alpine 等发行版
的 `rpcgen` 包同样由该目录构建。

## 产物

- `bin/rpcgen`（aarch64 可执行文件）
- `share/man/man1/rpcgen.1`

## 依赖

四个依赖都是 nfs-utils **顶层 configure 的无条件门禁**（顶层 configure 必须运行，
因为 `tools/rpcgen` 通过该树的 autotools 体系构建）。它们都**不参与链接**——
`rpcgen_LDADD = $(LIBINTL)`，产品二进制不链接其中任何一个：

| 依赖 | configure 中的门禁 |
|---|---|
| libtirpc/1.3.7 | `PKG_CHECK_MODULES([TIRPC], [libtirpc])` → `rpc/rpc.h` |
| uuid/2.40.1 | `AC_CHECK_HEADER(uuid/uuid.h)` |
| libevent/2.1.13 | `AC_LIBEVENT` |
| sqlite3/3.49.1 | `AC_SQLITE3_VERS` |

同一源码树的姊妹包 `libnfsidmap-ldap/2.6.4` 以同样方式声明 sqlite3（组件本身不使用）。

## OHOS 适配

- 构建系统: autotools（in-tree 构建；只构建 `tools/rpcgen` 子目录）
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- `config.guess`/`config.sub` 增加 HarmonyOS/ohos 三元组（E007/E122），不使用 `--build/--host`
- `configure`：getrpcbynumber 树级硬门禁降级为警告；config.status 临时目录改为 `$$` 名 + `umask 000`（HMDFS，E110/E112/E118）
- `tools/rpcgen/rpc_main.c`：BSD 遗留的 `rindex()` → POSIX `strrchr()`
- `-D_LARGEFILE64_SOURCE`：rpc_main.c 使用 LFS64 的 `struct stat64`/`stat64()`，OHOS libc 仅在该 POSIX 特性宏下提供这些别名

## 运行说明（重要）

`rpcgen` 运行期需要**外部 C 预处理器**：上游依次查找 `/lib/cpp`、`PATH` 中的 `cpp`，
或用 `-Y <dir>` 指定含 `cpp` 的目录。HarmonyOS 把预处理器提供为工具链前缀下的
`clang-cpp`，**没有名为 `cpp` 的命令**，因此直接运行会报
`cannot find C preprocessor: cpp`。两种可用做法：

```sh
# 方式一：自建 cpp 入口并加入 PATH（clang 需 -x c 才会以预处理模式读 .x）
mkdir -p "$HOME/cpp-bin"
printf '#!/bin/sh\nexec %s -E -x c "$@"\n' "$(command -v clang)" > "$HOME/cpp-bin/cpp"
chmod 755 "$HOME/cpp-bin/cpp"
PATH="$HOME/cpp-bin:$PATH" rpcgen calc.x

# 方式二：用 -Y 指定目录（rpcgen 会拼接该目录下的 /cpp）
PATH="$HOME/cpp-bin:$PATH" rpcgen -Y "$HOME/cpp-bin" calc.x
```

## 测试

- 上游 `tools/rpcgen` **无任何自动化测试**（`Makefile.am` 无 `TESTS`/`check_PROGRAMS`，
  目录内无测试文件；整树仅 rpc.statd 与 nsm_client 测试）。清点证据见 `test_package/MANIFEST.yml`。
- `test_package/` 提供消费者端到端用例 **RPCGEN-CONSUMER-E2E**：用安装后的 `bin/rpcgen`
  对真实接口定义 `calc.x` 生成四个文件（`-h`/`-c`/`-l`/`-m`），把它们编译链接进消费者程序，
  再 fork 服务端 + 客户端做两次真实 TCP RPC 往返（结构体入参/回参、标量入参/回参），
  断言业务结果 13 / 42 / 81。
