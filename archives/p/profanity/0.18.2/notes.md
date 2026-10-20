# profanity 0.18.2 -- OHOS 适配笔记

## 基本信息

- **适配状态**: `built`（待真机预检确认后由 HMBS 更新）
- **适配版本**: 0.18.2（上游正式 release，2026-06-08）
- **对应 Issue**: 待认领（申请人 gcw_uQ09W7jl，队伍 干）
- **申请人**: gcw_uQ09W7jl
- **队伍**: 干
- **构建系统**: Meson（上游 0.18.0 起移除 Autotools，仅支持 Meson >= 0.56.0）
- **语言**: C（gnu99）
- **适配路径**: 路径 A（基础适配）

## 上游信息

- 官网：https://profanity-im.github.io/
- 仓库：https://github.com/profanity-im/profanity
- Release：https://github.com/profanity-im/profanity/releases/tag/0.18.2
- 源码包：`profanity-0.18.2.tar.xz`
- sha256：`46964928742733fffcf8ca65d37ac0874c8ccd6270cbc065cb1013cee94e9e3b`（官网公布值）
- License：GPL-3.0-or-later

## 依赖说明

必需依赖（meson `dependency()`，均为 registry 已有配方）：

- `glib/2.84.0.1`（glib-2.0 + gio-2.0）
- `ncurses/6.6`（宽字符 ncursesw，终端 UI）
- `readline/8.3`（命令行编辑）
- `curl/8.15.0.1`（libcurl，HTTP 上传/下载）
- `sqlite3/3.49.1`（聊天记录/联系人数据库）
- `expat/2.8.2.1.1` + `openssl/3.5.6.1` + `zlib/1.3.1.1`（内嵌 libstrophe
  的 configure 经 pkg-config 探测的三件套；均为 ohpcd 已有二进制）

`libstrophe/0.14.0` 不再是 conan 依赖，而是**内嵌静态构建**
（见下「构建步骤」）：远端 libstrophe 包无 OHOS 二进制，其配方在真机
`autoreconf -fi` 直接失败；补加 autoconf 工具链的尝试同样失败——其
conancenter m4 依赖的 configure 在真机调用
`/data/service/hnp/bin/bash` 报 inaccessible（Error 127）。因此改用上游
`make dist` 发布包（自带预生成 `configure`，彻底摆脱 autotools 链），
以 `--disable-shared --enable-static` 编译后静态链接进 `bin/profanity`，
发布包不新增 `.so`，无运行时搜索路径需求。

构建工具：`meson/1.11.0`（conan，纯 Python，无编译；`ninja` 用 HMBS 真机系统工具链，不再经 conan 构建——conan 构建 ninja 会因 `System is unknown to cmake` 失败，见 qdl/2.7、vali/0.1.1、cairo/1.18.4.2 先例）与 `pkgconf/3.0.5`（conan tool_requires，经 build context 向 conanbuild 供给真实 pkg-config；真机无系统 pkg-config，见 zurl/1.12.0 notes #36 同款先例）。
测试依赖：`cmocka/2.0.2`（仅构建上游 `unittests` 二进制，用
`test_requires` 声明，不进入发布包依赖）。

可选功能（notifications、python/c plugins、OTR、PGP、OMEMO、
icons-and-clipboard、gdk-pixbuf、xscreensaver、spellcheck、qrcode）
全部保持上游默认 disabled，不引入额外依赖。

## 构建步骤

```bash
conan create . --user=ohpcd --channel=stable -pr:h=<ohos-profile> -pr:b=<ohos-profile>
```

Meson 流程：

1. `source()`：下载官方 `profanity-0.18.2.tar.xz`（镜像优先、官方兜底）
   与内嵌 `libstrophe-0.14.0` 发布包（`make dist` 产物，自带 `configure`；
   sha256 已实测），并以纯 Python 文本替换完成 `tls_free` →
   `strophe_tls_free` 移植（6 处，与 `patches-libstrophe/` 内 5 个补丁同语义；
   不再调用 conan `patch()`，以规避其 a/b 头 strip 解析失败）
2. `generate()`：MesonToolchain（`-Dtests=true`）+ PkgConfigDeps +
   ar/ranlib 绝对路径注入 `conan_meson_native.ini`
3. `build()`：直接运行内嵌 libstrophe 自带 `configure`
   （`--disable-examples --disable-fuzzing --disable-shared
   --enable-static`，无 autoreconf、无 autotools 依赖）→ `make install`
   到构建内前缀，经 `nm` 确认含 OpenSSL 后端引用后，手写 `libstrophe.pc`
   入 generators 目录供 meson 解析；随后 `meson setup` + `meson compile`，
   再运行上游 `unittests` 二进制并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记
4. `package()`：`meson install`（bin/profanity、themes、icons、man 手册）

## OHOS 适配补丁

- profanity 上游本体：无。上游 meson.build 已用 `dependency()` +
  `find_library()` 回退处理 ncurses/readline 查找，不需要 OHOS 专用补丁。
- 内嵌 libstrophe：`tls_free` 重命名为 `strophe_tls_free`（规避与
  OpenSSL 符号冲突导致编译失败），由 `conanfile.py source()` 内纯 Python
  文本替换实施（5 文件 6 处，逐文件计数校验，与 in-repo
  `libstrophe/0.14.0/patches/` 5 个补丁同语义）；`patches-libstrophe/0001~0005`
  保留为审计对照。

## 上游测试

`meson test` 注册 2 个条目（`upstream_test_total: 2`，口径
`ctest_entries`，即 meson.build 内 `test()` 注册数）：

1. `unit tests`：cmocka 二进制 `unittests`，`conanfile.py build()` 内
   真机执行，逐行解析 `[ OK ]` / `[ FAILED ]` 计数。
2. `functional tests`：需要 stabber XMPP stub 服务器 + libutil，
   OHOS 均无（registry 无 stabber 配方，bionic 无 libutil），该条目
   在 meson 配置阶段即不注册，记为 skipped（见结果标记 gaps）。

test_package：`test_profanity` 辅助程序对安装后的
`bin/profanity` 做静态验证（真机可执行签名门禁以 EPERM/126 拒绝一切
直接执行，缓存内与拷贝到构建树均失败，见上）：① 有效的 64 位
AArch64 ELF 头（magic + class + e_machine），② 二进制镜像内嵌
`0.18.2` 版本串（即 `--version` 打印的同一字符串），共 2 个断言，
输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 已知限制

- 仅最小功能构建：OTR/PGP/OMEMO 加密、桌面通知、插件、拼写检查
  等可选功能未启用（上游要求显式 `-Dxxx=enabled`，后续版本可按需加）。
- `functional tests` 在 OHOS 跳过（见上）。
- test_package 为静态验证：真机可执行签名门禁以 EPERM/126 拒绝直接
  执行安装后 ELF（缓存内与拷贝到构建树两轮均失败），改为校验 ELF 头
 （64 位 AArch64）与内嵌版本串。
- 终端运行需要 terminfo：ncurses 包自带 `TERMINFO` runenv 定义。

## 文件清单

- `conanfile.py` — Conan 配方（Meson 应用包 + 内嵌 libstrophe 静态构建）
- `conandata.yml` — 官方源码 URL + sha256（含内嵌 libstrophe 快照）
- `patches-libstrophe/` — 内嵌 libstrophe 5 个移植补丁（源自 in-repo 同版本配方）
- `manifest.yaml` — 版本元数据
- `notes.md` — 本文件
- `test_package/conanfile.py` — 测试入口（含结果标记）
- `test_package/CMakeLists.txt` — 辅助测试程序构建
- `test_package/test.c` — 安装产物的静态检查（ELF 头 + 版本串）
- `test_package/MANIFEST.yml` — 上游/新增测试声明
