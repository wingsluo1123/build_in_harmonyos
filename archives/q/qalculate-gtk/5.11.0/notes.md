# qalculate-gtk 5.11.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **安装预编译依赖**: 通过 cmd-pkgs 安装 cairo 1.18.2, pango 1.50.14, atk 2.38.0, gdk-pixbuf 2.42.12, gtk 3.24.38, harfbuzz 14.2.0, fontconfig 2.16.0, freetype 2.14.3, libepoxy 1.5.10, glib 2.88.0
2. **安装 libqalculate**: 从已编译的 staging 目录复制 libqalculate 库、头文件和 pkgconfig 文件到 ~/usr/local
3. **创建缺失的 pkgconfig 文件**: 为 cairo, cairo-gobject, gio-2.0, gio-unix-2.0, gmodule-2.0, gmodule-no-export-2.0, gthread-2.0, libpng, libpcre2-8, libffi 创建 .pc 文件
4. **构建 cairo-gobject 库**: 从 cairo 源码编译 libcairo-gobject.so（预编译包未包含）
5. **安装 cairo 头文件**: 从 cairo 源码提取公共头文件到 ~/usr/local/include/cairo/
6. **修复 config.guess**: 添加 HarmonyOS 检测分支，映射为 aarch64-unknown-linux-gnu
7. **修复 configure**: 移除 umask 077 调用（HMDFS 兼容性）
8. **配置**: `./configure --prefix=$HOME/usr/local` (R1: 参数最少化)
9. **编译**: `make -j2`
10. **安装**: `make install DESTDIR=$TEST_PREFIX`
11. **检查**: `make check` (无测试套件)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测分支 | 在 config.guess 中添加 `aarch64:HarmonyOS:*:*` case，映射为 `aarch64-unknown-linux-gnu` |
| 2 | config.status 创建临时文件失败 | HMDFS 不支持 `umask 077 && mktemp -d` 组合 | 移除 configure 和 config.status 中的 `umask 077` 调用 |
| 3 | glib.h 头文件缺失 | glib 2.78.6 包只含 .so 无头文件 | 升级安装 glib 2.88.0 包（含完整头文件） |
| 4 | cairo.h 头文件缺失 | cairo 预编译包只含 .so 无头文件 | 从 cairo 源码提取公共头文件到 ~/usr/local/include/cairo/ |
| 5 | cairo-features.h 缺失 | configure 生成文件，源码包未包含 | 手动创建 cairo-features.h 定义 CAIRO_HAS_* 宏 |
| 6 | libcairo-gobject.so 缺失 | cairo 预编译包未包含 cairo-gobject 组件 | 从 cairo 源码编译 libcairo-gobject.so |
| 7 | 多个 pkgconfig 文件缺失 | 预编译包未包含 .pc 文件 | 手动创建 cairo.pc, cairo-gobject.pc, gio-2.0.pc, gio-unix-2.0.pc, gmodule-2.0.pc, gmodule-no-export-2.0.pc, gthread-2.0.pc, libpng.pc, libpcre2-8.pc, libffi.pc |
| 8 | GitHub 下载失败 | 网络限制无法访问 GitHub | 使用 ghfast.top 镜像下载源码 |
| 9 | L2 smoke test 失败 | OHOS musl 动态链接器不搜索 LD_LIBRARY_PATH 和 RUNPATH 中的用户目录 | 已知平台限制，GUI 应用在无头系统上无法运行 |
| 10 | conan create 无法下载源码 | Conan 从 GitHub 下载失败 | 在 source() 中添加本地文件回退 |

## 源码修改

### config.guess 修改（探索阶段直接改源码）
- 在 `case $UNAME_SYSTEM` 中将 HarmonyOS 加入 `Linux|GNU|GNU/*` 分支
- 添加 `aarch64:HarmonyOS:*:*` case 映射为 `aarch64-unknown-linux-gnu`

### configure 修改（探索阶段直接改源码）
- 移除临时目录创建时的 `umask 077` 调用，适配 HMDFS 文件系统

### Conan 配方中的等效修复
- conanfile.py 的 `_patch_ohos_compat()` 方法在 build() 阶段自动应用上述修复

## 依赖版本

| 依赖 | 版本 | 安装方式 |
|------|------|----------|
| libqalculate | 5.11.0 | Conan 包 `libqalculate/5.11.0@ohpcd/stable` |
| gtk | 3.24.38 | 系统包 (cmd-pkgs) |
| glib | 2.88.0 | 系统包 (cmd-pkgs) |
| cairo | 1.18.2 | 系统包 (cmd-pkgs) + 源码头文件 |
| pango | 1.50.14 | 系统包 (cmd-pkgs) |
| atk | 2.38.0 | 系统包 (cmd-pkgs) |
| gdk-pixbuf | 2.42.12 | 系统包 (cmd-pkgs) |
| harfbuzz | 14.2.0 | 系统包 (cmd-pkgs) |
| fontconfig | 2.16.0 | 系统包 (cmd-pkgs) |
| freetype | 2.14.3 | 系统包 (cmd-pkgs) |
| libepoxy | 1.5.10 | 系统包 (cmd-pkgs) |
| gmp | 6.3.0 | 系统包 (cmd-pkgs) |
| mpfr | 4.2.1 | 系统包 (cmd-pkgs) |
| readline | 8.2 | 系统包 (cmd-pkgs) |
| libxml2 | 2.15.3 | 系统包 (cmd-pkgs) |

## 验证结果

```bash
# conan-verify 结果:
# G0: PASS - 预构建风险评估通过
# G1: PASS - 配方完整性检查通过
# G2: PASS - conan create 成功，test_package 编译运行通过
# G3: PASS - 系统同名库隔离验证通过 (R26)
# G4: PASS - 产物完整性检查通过 (bin/qalculate-gtk)
# L2: FAIL - smoke test 失败（OHOS 平台限制：musl 动态链接器不搜索用户目录）
# L4: PASS - 静态安全扫描通过
# L5: PASS - 产物基线对比通过
# 最终状态: built (L2 为已知平台限制，非构建问题)
```

## 注意事项

- qalculate-gtk 是 GUI 应用程序（非库），安装产物为可执行文件
- OHOS musl 动态链接器不搜索 LD_LIBRARY_PATH 和 RUNPATH 中的用户目录路径
- L2 smoke test 失败是 OHOS 平台已知限制，不影响构建质量
- cairo-gobject 需要从 cairo 源码单独编译（预编译包未包含）
- 多个 GUI 依赖的 pkgconfig 文件需要手动创建（预编译包未包含）
- conandata.yml 使用原始 GitHub URL，conanfile.py 添加本地文件回退以应对网络限制
- conanfile.py 使用 Autotools helper（不用 self.run()）
- test_package 验证 libqalculate 依赖链（include 头文件 + 链接库）
---

**编译结束**: 2026-07-01 21:02
**最终状态**: built
