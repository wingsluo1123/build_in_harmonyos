# xdrawchem

XDrawChem — 二维分子结构绘制与分析程序（Qt5 + Open Babel）。

## 概述

XDrawChem 是定位同 ChemDraw 的自由软件：绘制/编辑二维分子结构式与反应式，
读写 MDL Molfile（`.mol`/`.rxn`）、CML、CDX/CDXML、SMILES 等格式，做 2D↔3D
转换，并提供 NMR/IR 图谱工具与肽链构建器。分子格式的解析与生成由
Open Babel 3 承担（`application_ob.cpp` / `molecule_obmol.cpp` 等）。

## 已编译版本

- **1.11.1** (2026-10-16) — clang 15.0.4 / libc++，qmake（`-spec linux-clang`），
  OHOS aarch64（HarmonyOS PC），`-O2` release 构建

## 关键信息

- **上游**: <https://gitlab.com/yamanq/xdrawchem> （tag `v1.11.1`，2024-05-29）
  - 该 fork 是 1.11.x 系列的**唯一上游**：GitHub 镜像 `bryanherger/xdrawchem`
    与 SourceForge 项目页都只到 `1.10.2-1`（另加 2026 年的 v2.0rc*/v2.0/v2.0.1），
    Debian/Ubuntu 的 `1:1.11.1` 即取自该 GitLab（`debian/copyright` 的
    `Source:` 与 `debian/watch` 的 `searchmode=plain` 双重佐证）。
- **构建系统**: qmake（`xdrawchem.pro`，in-source build，`make install` 安装
  `bin/xdrawchem` + `share/xdrawchem/{ring,doc}`）
- **依赖**: `qt5-qtbase/5.15.2.2`（Core/Gui/Widgets/Network/Xml/PrintSupport）、
  `qt5-qtsvg/5.15.2`（`QT += svg`）、`openbabel/3.2.1`（`PKGCONFIG += openbabel-3`）；
  传递 zlib/1.3.1、dbus/1.14.10、expat/2.8.2、libxml2/2.15.3.1、eigen/3.4.1、rapidjson/1.1.0
- **平台**: aarch64 (HarmonyOS / OpenHarmony)

## 鸿蒙适配要点

1. **Qt5 qmake 模块描述失效**：`qt5-qtbase` / `qt5-qtsvg` 包内
   `mkspecs/modules/*.pri`（及 `bin/qt.conf` 的 `[Paths] Prefix`）记录的是
   **构建期** conan 私有前缀 `.../p/b/<hash>/b`，构建目录已随包清理消失；
   qmake 会把 `QT += core gui xml network widgets printsupport` 全部判成
   `Unknown module(s)`。修法：复制两个包的 `modules` + `modules-inst` 到构建目录，
   正则整体改写为真实 package 目录，经 `QMAKEMODULES` 暴露（该目录优先于 Qt 安装
   自带的 mkspecs 条目）；同时生成修正版 `qt.conf` 以 `-qtconf` 加载，并显式钉住
   `QMAKE_RCC/QMAKE_MOC/QMAKE_UIC`（命令行赋值优先级最高）。参照仓内
   `archives/q/qconf/2.5` 与 `archives/b/baka/2.0.4` 先例。
2. **Qt5 版本统一**：`qt5-qtsvg/5.15.2` 精确 `requires qt5-qtbase/5.15.2`，而该
   版本为 `-no-widgets` 构建（不含 Qt5Widgets）→ 配方
   `self.requires("qt5-qtbase/5.15.2.2", override=True)`（补丁版本，ABI 兼容）。
3. **pkg-config 依赖**：`openbabel` 包内 `openbabel-3.pc` 的 `prefix`/`libdir`
   指向已消失的构建目录 → 用 Conan `PkgConfigDeps` 重新生成（
   `set_property("openbabel", "pkg_config_name", "openbabel-3")` 对齐上游探测名），
   并把 generators 目录注入 `PKG_CONFIG_PATH`（PkgConfigDeps 本身不注入）。
4. **上游硬编码 debug**：`.pro` 的 `CONFIG += debug`（`-O0 -g3`）在 qmake 命令行
   无法覆盖（`.pro` 在命令行赋值之后求值）→ 补丁移除，配方按 `build_type` 传 `CONFIG`。
5. **Qt 5.15 头依赖收紧**：`http.cpp` 用 `qDebug() << …` 却未包含 `<QDebug>`
   （Qt 5.15 的 `qlogging.h` 只前置声明 `QDebug`）→ 补丁补 include。
6. **安装期 strip 会让二进制无法执行**：上游 `install_target` 规则带
   `-$(STRIP) <安装后的二进制>`（Makefile 中 `STRIP = strip`），而 **OHOS 加载器拒绝
   stripped ELF**（execve 返回 `Operation not permitted`）→ qmake 命令行传
   `QMAKE_STRIP=true`（环境变量 `QMAKE_STRIP` / `make QMAKE_STRIP=` 均无效，Makefile
   变量名是 `STRIP`）。
7. `make -j1`（HMDFS 无 mkfifo，jobserver 不可用）。

## 依赖关系

- **编译依赖**: qt5-qtbase/5.15.2.2、qt5-qtsvg/5.15.2、openbabel/3.2.1（+ 传递依赖）
- **运行依赖**: Qt5Core/Qt5Gui/Qt5Widgets/Qt5Network/Qt5Xml/Qt5PrintSupport/Qt5Svg
  与 libopenbabel（由 Conan 依赖链提供，`conanrun` 环境注入 `LD_LIBRARY_PATH`/`BABEL_LIBDIR`）

## 上游测试

上游**无自动化测试套件**：v1.11.1 归档内 `find . -iname "*test*"` 0 命中，顶层无
`tests/`，`xdrawchem.pro` 无 `check`/`test` 目标，也无 CTest / pytest / meson 注册。
验证入口 = 手工运行 `qmake && make && ./bin/xdrawchem`；本次以消费者视角的
`test_package`（5 条，实质执行被测包二进制）作为验证证据。

## 参考

- 上游仓库: <https://gitlab.com/yamanq/xdrawchem>
- 上游镜像: <https://github.com/bryanherger/xdrawchem>
- 项目主页: <https://www.woodsidelabs.com/chemistry/xdrawchem.php>
