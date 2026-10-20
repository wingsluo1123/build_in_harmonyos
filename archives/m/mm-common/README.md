# mm-common — GNOME C++ 绑定的共享构建支撑

`mm-common` 是 GNOME C++ 绑定项目的公共基础设施包，被 libsigc++、glibmm、gtkmm、pangomm、
atkmm、cairomm 等模块在 autogen/Meson setup 阶段使用。

## 功能概述

- **mm-common-get**：把共享的 Meson 构建脚本（`dist-changelog.py`、`doc-reference.py`、
  `generate-binding.py` 等）和文档工具复制进调用方源码树。
- **mm-common-prepare**：Autotools 版本的同类命令，复制 `compile-binding.am`、`dist-changelog.am`、
  `doc-reference.am`、`generate-binding.am` 到 `AC_CONFIG_AUX_DIR`，并按 `MM_CONFIG_DOCTOOL_DIR`
  复制文档工具。
- **Autoconf 宏**：`mm-*.m4`（`MM_ARG_ENABLE_WARNINGS`、`MM_AX_CXX_COMPILE_STDCXX`、
  `MM_PKG_CONFIG_SUBST`、`MM_CONFIG_DOCTOOL_DIR` 等），供 `aclocal` 引入。
- **文档工具**：doxygen 样式表、`doc-install.pl`/`doc_install.py`、`doc-postprocess.pl`/
  `doc_postprocess.py`、tagfile→devhelp2 的 XSL。
- **doctags**：上游打包的 `libstdc++.tag`（3.6 MB），离线可用。
- **骨架工程**：`skeletonmm.tar.{gz,xz}`，新绑定的起点。
- **pkg-config 模块**：`mm-common-util`（doctooldir）、`mm-common-libstdc++`（doxytagfile）。

整个包不含编译产物：只有 shell/Python 脚本、m4 宏、数据文件和手册页。

## 构建系统

上游 1.0.x 同时有 `configure.ac` 和 `meson.build`，但 **release tarball 是 `meson dist` 产物**：

- 没有 `configure`、没有 `Makefile.in`，Autotools 路线要先 `autoreconf`（autoconf+automake+libtool
  maintainer mode）。
- `meson.build` 完整可用，`-Duse-network` 选项决定 `libstdc++.tag` 是下载还是从源码树复制。

因此 OHOS 适配走 Meson：`-Duse-network=false` 离线构建，`meson.test()` 不用（上游无测试目标）。

## OHOS 适配要点

| 适配点 | 说明 |
|--------|------|
| 可重定位安装 | Conan 用 `--prefix=/` + DESTDIR 安装，上游烤进脚本的 `/share` 数据路径会失效；补丁 0001 改成按脚本自身位置推导（见版本目录 notes.md 5.1） |
| `.pc` 前缀 | Meson 生成的 `.pc` 以 `prefix=/` 开头，`package()` 改用 `${pcfiledir}/../..`（notes.md 5.2） |
| 离线 doctag | `-Duse-network=false`，避免 worker 访问 gcc.gnu.org |
| shebang | 保留上游 `#!/usr/bin/env python3` 与 `#! /bin/sh -e`，真机镜像两者均存在（见共性问题指南） |
| 无 C 产物 | 只有 `project()` 的一次编译器探测，不用链接/签名 |

## 依赖关系

- 编译期：`meson >= 0.62.0`、`ninja`、`python3`（worker 自带，历史记录为 meson 1.11.1 / ninja 1.13.1）。
- 运行时：`python3`（mm-common-get）；`sed`/`mkdir`/`cp`（mm-common-prepare，由 toybox 提供）。
- conan `requires`：无。

## 已归档版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.0.8 | built | 真机 shadow CI 全绿（L0/L1/L2/L4/L5 + L1e，test_package 14/14，Total 1 / Success 1）；34 个文件，`.pc` 可重定位，脚本按自身位置找数据 |

## 参考资料

- **官网**: https://gtkmm.gnome.org/
- **源码仓库**: https://gitlab.gnome.org/GNOME/mm-common
- **源码**: https://download.gnome.org/sources/mm-common/1.0/
- **许可证**: GPL-2.0-or-later
