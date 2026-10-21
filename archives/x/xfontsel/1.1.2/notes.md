# xfontsel 1.1.2 适配笔记

## 编译环境
- 构建系统: autotools (configure + make，tarball 自带预生成 configure/Makefile.in，无需 autoreconf)
- 编译日期: 2026-10-16
- 编译器: clang 15 (OHOS SDK，profile `ci/conan/profiles/ohos-aarch64`)
- 目标: OHOS aarch64 **原生 build=host**（不传 `--build/--host/--target`，铁律 #0）
- 状态: built（PR 阶段，未 upload）

## 编译步骤

```bash
# 由 CI/hmbs 在 HarmonyOS aarch64 真机执行（profile: ohos-aarch64）
conan create archives/x/xfontsel/1.1.2 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

1. `source()`：下载 X.Org 官方 tarball `xfontsel-1.1.2.tar.xz`（sha256
   `78ff0187…553f`，148792 字节，与官方发布一致）
2. `build()`：`apply_conandata_patches` → `./configure`（原生三元组，见下）→ `make -j1`
   → `make check`（上游 0 用例）
3. `package()`：`make install` → `bin/xfontsel` + `share/X11/app-defaults/XFontSel`
   + `share/man/man1/xfontsel.1`；对 `bin/xfontsel` 做 OHOS ELF 自签（E077）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` / 原生 build 无法判定 | tarball 自带 `config.guess`（2024-07-27）用 `uname -s` 识别系统，设备返回 `HarmonyOS` 不在其已知 OS 列表；且它对 `Linux|GNU` 分支编译探针写 `$TMPDIR`，HMFS 上失败。铁律 #0 禁止 `--build/--host/--target` | 补丁 `0001-config.guess.patch`：加 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`；`__OHOS__` 时 `LIBC=ohos`；编译探针临时目录 `umask 077→022`（E007/E205/E011）。tarball 自带 `config.sub`（2024-05-27）**已接受** `ohos*`/`linux-ohos*`，无需 config.sub 补丁 |
| 2 | `configure: error: working directory cannot be determined`（HMDFS 下） | conan 缓存父目录对 `getcwd()` 不可达；autoconf 2.73 生成的 configure 顶部严格 `pwd` 判定直接 abort | 补丁 `0002-configure.patch`：`ac_pwd=\`pwd\`` 加 `2>/dev/null || ac_pwd="$PWD"` 回退（2 处） |
| 3 | `config.status: cannot create a temporary directory in .` | `config.status` 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，HMFS 上 0700 目录不可写（E011/E114） | 同一补丁 `0002`：`umask 077→022`（2 处） |
| 4 | `configure` 的 `PKG_CHECK_MODULES(XFONTSEL, xaw7 xmu xt x11 xproto >= 7.0.17)` 找不到 `xmu`/`xproto` | PkgConfigDeps 生成的 `.pc` 名取自 Conan `pkg_config_name`：libxmu 的 Xmu 组件发布名是 `libxmu`，xorgproto 未设 `pkg_config_name`（默认 `xorgproto`） | `generate()` 里 `set_property("libxmu::xmu","pkg_config_name","xmu")`、`set_property("xorgproto","pkg_config_name","xproto")`（libxaw/1.0.14 同款）；`build()` 里以 generators 目录优先拼 `PKG_CONFIG_PATH` |
| 5 | `make install` 时 app-defaults 安装到 `/`（appdefaultdir 为空） | conan `xt.pc` 无 `appdefaultdir` 变量，`xt_appdefaultdir=` 取到空串 | 显式 `--with-appdefaultdir=/share/X11/app-defaults`（`$(DESTDIR)` 前缀化后落到包内路径） |
| 6 | 依赖 `libxext/6.4.0.1` / `libxpm/3.5.17` 被判为「无匹配已发布二进制」而需从源码重建 | libxaw/1.0.14 + libxmu/1.3.1.1 链路 force pin `libx11/1.8.13`，改变了 libxext/libxpm 的 package_id（libxaw 配方注释已记载「代价是二者从源码重建」） | 依赖侧行为，非本配方问题；重建成功即可（本次 conan-verify 与 CI 门禁均重建通过） |
| 7 | 依赖 `libxext/6.4.0.1` 重建 `make` 阶段报 `zsh:cd:21: no such file or directory: man src specs` → `all-recursive Error 1` | 依赖配方 `libxext` 的 `_ohos_shell()` 优先取 `os.environ["CONFIG_SHELL"]/["SHELL"]`，本机 porting 会话残留 `SHELL=/usr/bin/zsh`；其生成的 Makefile `SHELL=/usr/bin/zsh`，而 **zsh 默认不对未加引号展开做 IFS 词分割**，automake `all-recursive` 把整个 `SUBDIRS`（`man src specs`）当成一个目录名（知识库 E540 家族 / 草稿 `DRAFT-libcaca-…-autotools-ohos-shell-and-deps-env` 同款现象） | 按平台 profile `[buildenv]` 自己声明的构建 shell 运行：`env SHELL=/data/service/hnp/bin/bash CONFIG_SHELL=/data/service/hnp/bin/bash …`（bash 同时满足 `7<&0` fd 重定向与 IFS 词分割）。**未修改任何依赖配方** |

## 源码修改

- `patches/0001-config.guess.patch`：教 config.guess 识别 HarmonyOS →
  `aarch64-unknown-linux-ohos`，并把编译探针临时目录 umask 放宽为 022。
- `patches/0002-configure.patch`：configure 顶部加 `$PWD` 回退（HMDFS
  getcwd 不可达），config.status 临时目录 umask 077→022。
- 两个补丁均由 `refresh-patch --auto` 从真实源文件改动生成（e/.work），
  实测 `patch -p1` 对原始 tarball 干净应用（rc=0）。
- `xfontsel.c` / `ULabel.c` 未改动。

## 依赖版本

- `libxaw/1.0.14`（组件 xaw7）、`libxmu/1.3.1.1`、`libxt/1.3.1`、
  `libxext/6.4.0.1`、`libx11/1.8.13`（force，与 libxmu/libxaw 同轨）、
  `xorgproto/2025.1`（提供 xproto.pc）
- 运行期闭合（run=True，仅供 test_package conanrun 环境）：
  `libxcb/1.17.0`、`libxau/1.0.11`、`libxdmcp/1.1.5`
- 全部为 ohpcd 已发布 OHOS/armv8 二进制或按上述 note 由源码重建

## 验证结果

```bash
# conan-verify（xfontsel-conanverify-20261016-4，rc=0）
#   G0 预构建风险 PASS / G1 配方完整性 PASS / G2 conan create PASS
#   G3 系统同名库隔离 PASS / G4 产物完整性 PASS
#   L2 smoke / L4 checksec / L5 基线 无 FAIL
# 消费者测试（test_package，真机 conan create test 阶段）
#   test_xfontsel.py：discovered=5, passedCount=5
#     -version  → stdout "xfontsel 1.1.2"  rc=0
#     --version → stdout "xfontsel 1.1.2"  rc=0
#     -help     → usage 文本（"where options include:"）rc=0
#     --help    → usage 文本              rc=0
#     无 DISPLAY → rc=1 "Error: Can't open display:"（XtAppInitialize 干净失败）
#   运行期以依赖图全部实体 .so 经 LD_PRELOAD 注入（OHOS loader 可能忽略
#   LD_LIBRARY_PATH、HMFS 不保证 symlink 链，E050）
# 上游测试：xfontsel 1.1.2 无测试套件（Makefile.am 无 TESTS/check_PROGRAMS/
#   check-local；meson.build 无 test()；发布包无 tests/ 目录），构建仍显式跑
#   make check，HMBS_UPSTREAM_TEST_RESULT status=no_tests，discovered=0
```

## 注意事项

- 上游无自动化测试套件：`test_package/MANIFEST.yml` 写入
  `upstream_tests_exist: false` + 非空 `upstream_test_audit`（发布包清单 /
  Makefile.am / man/Makefile.am / meson.build / configure.ac 五处审计）。
- xfontsel 需 X server 才能完整运行；真机 CI 无 X 环境，test_package 走
  `-version/-help`（main() 在 XtAppInitialize 之前处理）与无 DISPLAY 失败路径。
- 版本号 1.1.2 为首版适配（R37）。
