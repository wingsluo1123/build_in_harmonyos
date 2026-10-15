# vxi 0.0.20121221 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure，无需 autoreconf）
- 编译日期: 2026-10-14
- 编译器: clang/clang++
- 状态: built（待真机 rule4 门禁确认）
- 申请人: gcw_6a3w2yXz（队伍：来都来了）

## 上游信息
- 软件：vxi（VXI-11 RPC 协议客户端/服务端桩库，LXI 仪器通信）
- 版本：0.0.20121221（Debian vxi 源码包）
- 归档：vxi_0.0.20121221.orig.tar.gz，95500 B
- sha256：12b04dbc8f8538dfebb062c16fbaa8fdf11a3ca110e8ffabdeba60363e3af8d8
- 主 URL：https://deb.debian.org/debian/pool/main/v/vxi/vxi_0.0.20121221.orig.tar.gz
- 镜像：https://mirrors.aliyun.com/debian/pool/main/v/vxi/vxi_0.0.20121221.orig.tar.gz（同文件同校验，本机实测可达；官方 URL 保留为回退）
- 上游主页：https://tracker.debian.org/pkg/vxi（原始规范来源 http://www.ivifoundation.org/specifications/default.aspx）
- 许可证：vxi.x/vxi_intr.x 为 Public Domain（VXIbus 联盟 VXI-11 规范附录 C）；configure.ac/Makefile.am/debian/* 为 GPL-2+；配方 license 取 GPL-2.0-or-later
- 内容：共 14 个条目；vxi.x（4225 B）定义 DEVICE_CORE=0x0607AF / DEVICE_ASYNC=0x0607B0 程序与 13 个 RPC 过程，vxi_intr.x 定义 DEVICE_INTR=0x0607B1；Makefile.am 以 rpcgen 生成全部 C/H 并归档 libvxiclient.a/libvxiserver.a，安装 vxi.h/vxi_intr.h

## 编译步骤

1. `get()` 解压 orig.tar.gz（strip_root）。
2. `generate()`：AutotoolsToolchain 去掉 --build/--host（R15），追加 --enable-static/--disable-shared（R26），从 `tools.build:compiler_executables` 取 CC（R33），extra_cflags 注入 `-fPIC` 与 libtirpc 头目录（Debian rules 的 `-I/usr/include/tirpc` 的 conan 等价）。
3. `build()`：将 configure/config.status 的 `umask 077` 改写为 `umask 000`（E011 HMDFS 陷阱，libtirpc/gadap 同源）；`_ensure_rpcgen()` 优先用系统 `rpcgen`，缺失时从 conandata.yml 的 rpcsvc-proto 1.4.4 源码原生编译私有 rpcgen（仅构建期工具，不打包；同样做 umask 改写；复用 tools.build:compiler_executables 的 CC 与 user.hmbs:make_path）并将其目录前置到 PATH 后再 `configure` + 先 `make BUILT_SOURCES` 生成 rpcgen 桩并归一绝对 include（VPATH 陷阱修复，见问题 7）+ `make -j1`。不调用 `make check`（上游无测试）。：将 configure/config.status 的 `umask 077` 改写为 `umask 000`（E011 HMDFS 陷阱，libtirpc/gadap 同源）；`_ensure_rpcgen()` 优先用系统 `rpcgen`，缺失时从 conandata.yml 的 rpcsvc-proto 1.4.4 源码原生编译私有 rpcgen（仅构建期工具，不打包；同样做 umask 改写；复用 tools.build:compiler_executables 的 CC 与 user.hmbs:make_path）并将其目录前置到 PATH 后再 `configure` + `make -j1`。不调用 `make check`（上游无测试）。
4. `package()`：不调用 `make install`（真机 install -c -m 644 报 Error 64，见问题 9），直接用 conan copy() 从源码/构建树收缴 4 件产物（2 静态库 + 2 头），缺件即显式失败，绝不产空包。：`make install` 落盘 libvxiclient.a/libvxiserver.a 与 vxi.h/vxi_intr.h，另带回退 copy。
5. `test_package`：CC 编译 test_vxi.c（-lvxiclient -lvxiserver -ltirpc），运行 4 项 CHECK 并输出 HMBS 双标记；上游标记按 no_tests 口径输出。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | deb.debian.org 在本机 TLS 握手失败/HTTP 空回包 | 本机到 Debian 官方源网络不可达（curl schannel 35 / HTTP 52） | conandata.yml 采用有序 URL 列表：Aliyun Debian 镜像在前（本机实测 95500 B 同校验通过），官方 deb.debian.org 置后回退；sha256 不变 |
| 2 | 构建期需要 rpcgen（Makefile.am 规则 `%_clnt.c/%_xdr.c/%_svr.c/%.h: %.x`），真机 PATH 无系统 rpcgen | 上游从规范源生成全部源码，无预生成文件；OHOS 真机/CI 均无 rpcsvc-proto | `_ensure_rpcgen()`：有系统 rpcgen 直接用，无则从 rpcsvc-proto 1.4.4 官方 GitHub release 原生编译私有 rpcgen（构建期专用，不打包；.x 仍为唯一规范源，不预置生成文件） |
| 3 | tirpc 头路径 | Debian rules 传 CPPFLAGS=-I/usr/include/tirpc；conan 的 libtirpc 头在包内 | generate() 遍历 libtirpc 依赖的 includedirs 注入 -I；requirements 声明 transitive_headers/transitive_libs |
| 4 | HMDFS umask 陷阱 | configure/config.status 的 `umask 077 && mktemp -d` 在 HMDFS 产生不可写临时目录 | 构建前改写为 `umask 000`（libtirpc 配方同法） |
| 5 | 上游无测试，rule4 需要证据 | 14 文件包无 tests/、无 TESTS，make check 为 no-op | test_package/MANIFEST.yml 结构化审计 + upstream_test_total: 0（autotools_tests）+ upstream_tests_exist: false；test_package 阶段输出 no_tests 标记（bwm/0.6.3 范例）；消费者 test_vxi.c 补 4 项真实断言 |
| 7 | VPATH 异地构建 rpcgen 绝对 include 导致编译失败（真机 2026-10-14：vxi_clnt.c:7 `#include "/.../b/vxi.h" file not found`，而 vxi.h 已生成在 build-release/） | Makefile.am 用 `rpcgen -h/-c/-l/-m -o $@ $<`，VPATH 下 $< 为 srcdir 限定的绝对 .x 路径；新版 rpcsvc-proto rpcgen 把输入目录嵌入生成 C 文件的 #include，-o 却把头写进 build dir，源/构建目录错位 | build() 先 `make BUILT_SOURCES` 生成桩，再 `_fix_rpcgen_absolute_includes()` 把绝对 include 归一为 basename（-I. 解析 build dir 头）并把头镜像到 source dir 兜底，然后 `make -j1` 编译（桩比 .x 新，不会重生成覆盖）；package() 回退 copy 同时查 source/build/build-release 三处 |
| 6 | 私有 rpcgen 链接失败 undefined symbol: rindex（rpc_main.c mkfile_output） | OHOS libc 无 BSD rindex（有 index/strchr） | _ensure_rpcgen() 在解压 rpcsvc-proto 后将整词 rindex 改写为 strrchr（仅构建期工具源码，不打包；strrchr 由已包含的 string.h 声明） |

## 源码修改

无 conandata 补丁（patches_applied: []）。构建时改写仅针对构建期临时源码：configure 的 umask 077→000，以及私有 rpcgen 工具源码的 rindex→strrchr 整词改写；均不进补丁、不打包。

## 依赖版本

| 包 | 版本 | 来源 | 用途 |
|----|------|------|------|
| libtirpc | 1.3.7 | ohpcd 制品仓 | XDR 运行时 rpc/rpc.h、链接 -ltirpc |

构建工具：rpcgen（构建主机 PATH 必备，Debian rpcsvc-proto 对等物）。

## 验证结果

- 本轮为首轮工作树（未提交），待 HMBS 真机预检执行 `conan create`（HarmonyOS aarch64 实测）后回填：
  - 上游测试用例通过率：无上游测试（no_tests，0/0）
  - 新增测试用例通过率：待真机输出 `HMBS_TEST_PACKAGE_RESULT` 后填写（设计 4/4）
- 证伪要求：test_vxi 二进制非空断言（3 类 XDR 编解码往返 + 程序号常量 + 符号解析），退出码非零即失败；标记数字仅来自测试二进制退出码对应的已知用例数，无字符串计数与算术修补。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/v/vxi/0.0.20121221/conanfile.py | 主配方（autotools + tirpc + rpcgen 探测） |
| archives/v/vxi/0.0.20121221/conandata.yml | 双 URL + sha256 |
| archives/v/vxi/0.0.20121221/manifest.yaml | 版本级 manifest |
| archives/v/vxi/0.0.20121221/test_package/test_vxi.c | 4 断言消费者测试 |
| archives/v/vxi/0.0.20121221/test_package/conanfile.py | 编译运行 + 双 HMBS 标记 |
| archives/v/vxi/0.0.20121221/test_package/MANIFEST.yml | 上游无测试审计 + total 0 |
| archives/v/vxi/0.0.20121221/notes.md | 本文件 |

## CI #91983 follow-up (round 2, English note to avoid GBK pipe issues)

- Symptom: toolchain[13] cannot fork twice + KC3 fork retry, downloads already OK.
- Change: _run_fork_tolerant with 4 attempts and 5/15/30s backoff on 3 build-tool self.run calls only. URLs/sha/tests unchanged.

## 注意事项

- 本机 Windows 检出存在两处与本改动无关的环境 artifact：`archives/g/gama/...0002-*.patch??`（文件名含 CR，Windows 无法创建）与 `archives/l/libXext`/`libxext` 大小写碰撞；均未纳入本次改动，PR 仅含 `archives/v/vxi/`。
- 真机无系统 rpcgen 为预期情况：配方自动走私有 rpcgen 构建（rpcsvc-proto 1.4.4 官方 release，CI 自动加 gh-proxy 镜像回退），不得跳过上游构建或伪造预生成文件。
- PR 正文测试数字留待真机 evidence 轮填写，本轮不猜测。

| 8 | 第二轮复盘（2026-10-14 真机 line 528 仍同错）：上一轮 Makefile 内联 sed 为空操作 | 内联补丁的 sed 追加行被缩进进 `if stripped.startswith("#"): continue` 之后不可达分支，`changed` 恒 False，零文件被改（本地复核 py_compile 通过但逻辑恒为 no-op；真机行号 451→528 证明新代码已同步但修复未生效） | 本轮改用不同策略：不再解析/补丁 Makefile，改为 configure 后用 basename 输入预生成全部 8 个桩并 touch 到最新，make 时模式规则因 up-to-date 跳过 rpcgen；附带 python 正则归一化（无需 sed/chmod），post-make 扫尾保留 |
| 9 | `package()` 的 `make install` 报 install-libLIBRARIES Error 64（真机 2026-10-14 line 549，编译已过） | automake 安装规则调用 HMBS install shim `install -c -m 644`，toybox/HMBS install -c 在 HMDFS 上失败且 -m 走 chmod（HMBS 上报 chmod:0；E596/E087 同类平台缺陷） | 不再调用 `autotools.install()`，package() 直接 copy 4 件产物（libvxiclient.a/libvxiserver.a + vxi.h/vxi_intr.h，递归搜构建树并排除 rpcgen-priv），缺件抛错 |
| 10 | 私有 rpcgen 持续产出 241 字节空头（真机 2026-10-14：`vxi.h lacks DEVICE_CORE/Create_LinkParms`，compiled shim + `-Y` 后依旧） | 编译器驱动语言陷阱：垫片执行 `CC -E` 时驱动把未知 `.x` 后缀当链接器输入，直接跳过预处理且退出码仍为 0（本机 MinGW 实测：`gcc -E -C -DRPC_HDR vxi.x` → 139 B、无 program；`cpp` 同文件 → 4576 B 含 DEVICE_CORE）→ rpcgen 解析零定义、静默输出空头 | 垫片改为 `CC -E -x c` 强制 C 语言（本机同条件验证 4576 B、has_program=True）；pre-grow 每次调用前先删 stale 产物（避开 rpcgen 已存在即 crash），保留 verify/package 双门禁 |
| 11 | 私有 rpcgen 源码下载失败（真机 2026-10-14：gh-proxy.com 403 forbidden + github.com 直连 connect timeout×2，conan create 在 build()/_ensure_rpcgen 抛 ConanException） | 单代理回退不足：conandata 仅列 gh-proxy.com + 官方，403 后唯一回退是直连 GitHub，而真机到 github.com 超时；且 get() 无额外 retry 参数，瞬时网关抖动直接失败 | conandata rpcgen_sources 改为 4 路有序列表（ghfast.top + mirror.ghproxy.com + gh-proxy.com + 官方兜底，E017/dasel 多代理先例，同归档 sha256 不变）+ source()/rpcgen get() 加 retry=3/retry_wait=10 |
