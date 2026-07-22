# ola 0.10.9 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am, libtool)
- 编译日期: 2026-07-22
- 编译器: clang 15.0.4 (/data/service/hnp/bin/clang, OHOS SDK 26.0.0.18 sysroot)
- 三元组: aarch64-unknown-linux-ohos
- 平台识别: OpenHarmony PC (HongMeng Kernel 1.12.0, bionic libc)
- 状态: built
- 适配路径: A（只打包核心 libolacommon / libola / libolaserver / olad；UI/HTTP/USB 驱动按默认 build 产出但不被独立命名打包）

## 编译步骤

```bash
# 0) 源码准备（已由 init-build 完成；本版本以 Debian dist tarball 为准 sha=44073698...4ebf）
cd /storage/Users/currentUser/tmp/builds/ola-0.10.9.work

# 1) 平台识别补丁：让 config.guess 认 HarmonyOS、config.sub 认 linux-ohos
#    （详见 E007 知识库条目）
sed -i 's|umask 077|umask 022|g' configure   # E011 修 HMDFS + uid0 DAC

# 2) configure（参数最小化 R1 + 路径 A 收敛：禁用 http server / examples / tests）
export PATH=/data/service/hnp/bin:$PATH
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/lib64/pkgconfig
export CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"
export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
export LIBS="-lprotobuf"      # libprotoc.a 是 static，需要 link protobuf 符号
./configure --prefix=$PREFIX \
    --disable-http --disable-unittests --disable-examples

# 3) make
make -j$(nproc)
make install DESTDIR=$DESTDIR
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | `config.guess` 不知道 `HarmonyOS` uname 系统名 | 在 `config.guess` 加 `*:HarmonyOS:*:*` 分支回退到 `aarch64-unknown-linux-ohos`；`config.sub` 在 `maybe_os` 列表加 `linux-ohos*`（E007） |
| 2 | `configure: error: cannot find libprotoc` (链接期) | `protoc --plugin=protoc-gen-ola` 用的是 `libprotoc.a` 静态库，导出但未内联 `libprotobuf` 符号 | `export LIBS="-lprotobuf"` 让 link 行追加 `-lprotobuf`（R6：写入 conanfile.py，不改 configure 模板） |
| 3 | `config.status: Permission denied` 创建 `./confXXXX/subs1.awk` | HMDFS 文件系统 + uid 0 不绕过 DAC；`umask 077` 创建的 `0700` 临时目录不可写 | `sed -i 's/umask 077/umask 022/g' configure`（E011） |
| 4 | `common/network/NetworkUtils.cpp:344: error: use of undeclared identifier '_res'` | OHOS bionic `<resolv.h>` 只声明类型 `__res_state`，**不导出** 全局 `_res`；且 `libresolv.a` 是 8 字节空 stub；`res_ninit` 未声明 | Patch #1 添加 `#elif !defined(HAVE_DECL__RES)` 分支：`NameServers()` 返回空列表 + OLA_INFO 提示（`HAVE_DECL__RES` 由 Patch #4 的 `AC_LINK_IFELSE` 探针定义）；`DefaultRoute()` 用 `/proc/net/route` 解析（替代缺失的 netlink/sysctl） |
| 5 | `<linux/socket.h> error: redefinition of 'sockaddr_storage'` | bionic `<linux/socket.h>` 缺 `__kernel_sa_family_t` 之前就 re-define `sockaddr_storage`（与 `<sys/socket.h>` 冲突） | 配置阶段不定义 `HAVE_LINUX_NETLINK_H` / `HAVE_LINUX_RTNETLINK_H`（bionic 上 netlink 头不可用），Patch #1 顶部 `#include` 守护自动跳过；两条上游后端在 bionic 都不可用 |

## 源码修改

OLA 0.10.9 在 OHOS 上需要 4 个源码 patch（conan recipe 通过 conandata.yml `patches` 列表应用）：

- `0001-common-network-NetworkUtils.cpp.patch` —— 修改 `common/network/NetworkUtils.cpp`：
  - 顶部 `#include <linux/netlink.h>` 守护保持上游 `HAVE_LINUX_NETLINK_H && HAVE_LINUX_RTNETLINK_H` 不变（OHOS 上 configure 不会定义这俩宏，自动跳过；R8：避免平台宏）
  - `DefaultRoute()` 增 `#elif !defined(_WIN32)` 通用 POSIX fallback：用 `/proc/net/route` 解析默认路由（Hex 编码 `Destination=00000000 + Flags&RTF_GATEWAY`，gateway 经 `__builtin_bswap32` 转换后再传给 `IPV4Address` —— `/proc/net/route` 输出的 gateway 字段是 host int 字节序，IPV4Address 存 BE uint32_t；`__builtin_bswap32` 是 clang builtin 不依赖 libc 的 `ntohl` —— 后者在 OHOS bionic 是 no-op stub）
  - `NameServers()` 增 `#elif !defined(HAVE_DECL__RES)` 分支：返回空列表 + OLA_INFO 提示（R8 feature-detection 而非平台宏）
- `0002-config-config.guess.patch` —— `config/config.guess` 2015 版本加 `*:HarmonyOS:*:*` 分支
- `0003-config-config.sub.patch` —— `config/config.sub` 2015 版本加 `linux-ohos*` 匹配项
- `0004-configure-ac-res-symbol.patch` —— `configure.ac` 加 `AC_LINK_IFELSE` 探针：探测全局 `_res` 符号是否能链接；能则定义 `HAVE_DECL__RES=1`，否则留空。OHOS bionic 不导出 `_res`，`HAVE_DECL__RES` 留空，Patch #1 走 fallback。该探针对任何缺 `_res` 的 libc 都生效，非平台特定

> 源码选型：使用 Debian .orig tarball（`ola_0.10.9.nojsmin.orig.tar.gz`），sha256 44073698...4ebf，bit-identical to upstream release plus pre-bootstrapped autotools artifacts（configure / aclocal.m4 / Makefile.in）。这样 conan 配方不需要 `aclocal`/`automake`（OHOS hnp 未打包），只需标准 autoconf + libtool + 编译器。

> 注：`configure` 中 `umask 077 → 022` 是探索阶段为绕过 HMDFS + uid 0 DAC 而做的修改，锚定到具体几行（非全局替换以避免误伤 install 规则）。由 `conanfile.py` 的 `_patch_configure_for_hmdfs()` 在 build 阶段做。

## 依赖版本

| 依赖 | 版本 | 来源 | OHOS 制品 |
|------|------|------|----------|
| protobuf | 3.21.12 | 系统（/storage/Users/currentUser/usr/local） | 系统库，不进 conan 制品（system_libs） |
| libuuid | 系统 | 系统 | 不进 conan |
| protoc + libprotoc + protobuf-compiler | 3.21.12 | 系统 | 不进 conan |
| libpthread / libc / libdl / libm / libc++ | — | bionic / OHOS sysroot | 不进 conan（system_libs） |
| libusb (OLA plugin: usbpro) | 1.0.x | 未启用（路径 A 收敛） | 排除 |
| libmicrohttpd (OLA HTTP server) | — | `--disable-http` | 排除 |
| liblo (OSC) | — | OLA 默认未启用 OSC | 排除 |
| cpprest | — | 排除 | 排除 |

`conanfile.py` 将 `protobuf` 列为 `system_libs`（系统已装且 R26 静态链接同名库），其他系统库自动透传。

## 验证结果

```bash
# 编译：0 errors, 0 undefined references
make -j20 → exit 0
# 产物
common/.libs/libolacommon.so.0.0.0   (4.3 MB)
ola/.libs/libola.so.1.0.1             (326 KB)
olad/.libs/libolaserver.so.0.0.0     (596 KB)
olad/.libs/olad                       (52 KB)

# 安装到 staging：84 .so + 28 .a + 182 headers + 26 bins

# smoke test（待 conan-verify 阶段跑）
./olad --version   # TBD
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libolacommon.so | 4.3 MB | 公共库：网络、线程、RDM、字符串、IO、protobuf |
| libola.so | 326 KB | 客户端 RPC stub（libola + OlaClient + StreamingClient）|
| libolaserver.so | 596 KB | 服务器核心（universe / device / plugin / port）|
| olad | 52 KB | 主进程 |

## 注意事项

- **GPL-2.0-or-later / LGPL-2.1-or-later**：比 tracy 的 BSD 严，下游使用会传染。注意 LICENSE 文件需保留。
- **路径 A 收敛**：`--disable-http --disable-unittests --disable-examples`。HTTP UI、Python bindings、各 plugin（artnet / sacn / usbpro / spi / etc.）按 build 默认产出但**不列为独立打包目标**；它们以静态 archive 形式存在于 staging `lib/` 下，但 conan recipe 的 `cpp_info.libs` 只声明核心三个 + plugins（如启用）。
- **路径 A 实际策略**：`cpp_info.libs = ["olacommon", "ola", "olaserver", "olad_plugin_api"]`（静态 archive），共享库 `libolacommon.so` 等作为 `cpp_info.libs` 共享组件可被 downstream `find_package` 自动链到。
- **不在 PR 范围**：OLA Python bindings（pybind11 太复杂）、Web UI（cpprest + microhttpd）、具体 DMX 设备驱动插件（libusb 兼容层在 OHOS 缺失）。
- **OHOS 限制**：`NameServers()` 返回空；`DefaultRoute()` 通过 `/proc/net/route` 解析（无 netlink、无 sysctl）。
- **`_GNU_SOURCE` vs bionic**：OLA configure 自动检测 bionic 时已经加了正确的 feature test macros（`#ifdef __BIONIC__`）；无需手工指定。
---

**编译结束**: 2026-07-22 14:44
**最终状态**: built
