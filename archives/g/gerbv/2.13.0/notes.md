# gerbv 2.13.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-17
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: failed (配方框架已生成，编译因依赖缺失未完全通过)

## 编译步骤
1. init-build: python3 scripts/ohc-run.py init-build gerbv 2.13.0
2. 源码获取: git clone --depth 1 --branch v2.13.0 https://github.com/gerbv/gerbv.git
3. CMake 构建: cmake -B build -DCMAKE_BUILD_TYPE=Release
4. 依赖安装: 使用 ohc-run.py resolve-deps 或 Conan 包管理安装 glib 2.88.0, cairo 1.18.2, gtk4 4.22.4, libxml2 2.15.3, gettext 0.22.5

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub release URL 404 | 官方release页面无源码tarball,仅提供二进制包 | 使用git clone获取源码 |
| 2 | gtk+-2.0 不可用 | OHOS 上无 gtk2 预编译包或 conan 包 | 报告依赖缺失，需先适配 gtk2 |
| 3 | cairo 安装不完整 | cmd-pkgs cairo 1.18.2 缺少头文件和 pkgconfig | 手动创建 cairo.pc |
| 4 | 缺少 gdk-pixbuf/pango/pcre2 等 .pc 文件 | 预编译包安装时未安装开发文件 | 手动创建 .pc 文件 |
| 5 | CMakeLists.txt 项目版本为 4.0 | git 仓库版本号与发行版本号不一致 | 忽略，git tag 为 v2.13.0 |

## 依赖版本
- glib 2.88.0 (预编译包)
- cairo 1.18.2 (预编译包, 开发文件不完整)
- libxml2 2.15.3 (预编译包)
- gettext 0.22.5 (预编译包)
- gtk4 4.22.4 (预编译包, 但 gerbv 需要 gtk+-2.0)
- gtk2 2.24 (缺失 - 需要在 OHOS 上先适配发布)

## 验证结果
```bash
# 因 gtk2 缺失，编译未通过，无法验证二进制产物
# cmake configure 失败: gtk+-2.0 not found
```

## 注意事项
1. gerbv 上游已从 Autotools 迁移到 CMake（git tag v2.13.0 使用 CMake）
2. 核心依赖 gtk+ 2.x 在 OHOS 上不可用，需要先适配 gtk2
3. 如改用 gtk3/gtk4 需要大量源码级适配（API 不兼容）
4. CLI 导出模式（-x png/pdf/svg等）不需要显示，但编译仍依赖 GTK 头文件
---

**编译结束**: 2026-07-17 20:34
**最终状态**: failed
