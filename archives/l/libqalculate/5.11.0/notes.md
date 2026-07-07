# libqalculate 5.11.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-01
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **下载源码**: 从 GitHub releases 下载 libqalculate-5.11.0.tar.gz (sha256: 6217a634eeb9659ebb4080c265dfab47d8f8dd4c33394b48fd5a1f83ef4538c4)
2. **应用补丁**: 通过 Conan 的 `apply_conandata_patches()` 自动应用 3 个补丁
3. **设置环境变量**: CONFIG_SHELL=/usr/bin/sh, SHELL=/usr/bin/sh, CC=clang, CXX=clang++, PKG_CONFIG_PATH 指向系统依赖
4. **配置**: 使用 Conan AutotoolsToolchain + Autotools helper 执行 `./configure --without-libcurl --without-icu`
5. **编译**: `make -j1` (单线程编译，避免内存不足)
6. **安装**: `make install DESTDIR=<package_folder>` (Autotools helper 自动管理 prefix)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测分支 | 补丁 0001: 在 config.guess 中添加 `aarch64:HarmonyOS:*:*` case，映射为 `aarch64-unknown-linux-gnu` |
| 2 | configure 创建临时目录失败 | HMDFS 文件系统不支持 `umask 077 && mktemp -d` 组合 | 补丁 0002: 移除 configure 中的 `umask 077` 调用 |
| 3 | pthread_cancel 链接失败 | OHOS 平台不支持 pthread_cancel/pthread_setcancelstate | 补丁 0003: 用 `#ifndef __OHOS__` 守卫 pthread cancellation 函数调用 |
| 4 | configure 找不到系统依赖 | PKG_CONFIG_PATH 未包含 ~/usr/local/lib/pkgconfig | 在 generate() 中通过 Environment 设置 PKG_CONFIG_PATH |
| 5 | make 并行编译内存不足 | aarch64 设备内存有限 | 使用 `make -j1` 单线程编译 |
| 6 | libcurl 依赖缺失 | 系统未安装 libcurl | configure 添加 `--without-libcurl` |
| 7 | ICU 依赖缺失 | 系统未安装 ICU | configure 添加 `--without-icu` |
| 8 | test_package CMake 无法识别平台 | CMake 不认识 HarmonyOS 系统名称 (E092) | test_package 设置 CMAKE_SYSTEM_NAME=Linux |
| 9 | conanfile.py 硬编码路径 | 使用 self.run() 手动执行 configure/make | 改用 Conan Autotools helper |

## 源码修改

### 补丁 0001: config.guess.patch
- **文件**: config.guess
- **修改**: 在 `case $UNAME_SYSTEM` 中将 `HarmonyOS` 加入 `Linux|GNU|GNU/*` 分支；添加 `aarch64:HarmonyOS:*:*` case 映射为 `aarch64-unknown-linux-gnu`

### 补丁 0002: configure.patch
- **文件**: configure
- **修改**: 移除临时目录创建时的 `umask 077` 调用，适配 HMDFS 文件系统

### 补丁 0003: libqalculate-util.cc.patch
- **文件**: libqalculate/util.cc
- **修改**: 用编译期特性检测 `#ifdef HAVE_PTHREAD_CANCEL` 等宏守卫 pthread 取消函数调用（R8 合规，不使用平台宏）

## 依赖版本

| 依赖 | 版本 | 安装方式 |
|------|------|----------|
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
# G4: PASS - 产物完整性检查通过 (bin/lib/include)
# L2: PASS - 平台功能测试通过 (qalc --version: 5.11.0)
# L4: PASS - 静态安全扫描通过
# L5: PASS - 产物基线对比通过
# 最终状态: published
```

## 注意事项

- libqalculate 是 C++ 库，test_package 必须使用 CXX 项目类型
- 系统依赖不通过 Conan 管理，而是预装在 ~/usr/local，通过 PKG_CONFIG_PATH 发现
- OHOS 平台不支持 pthread_cancel，相关功能在运行时被禁用
- conandata.yml 必须使用原始 GitHub URL，不可使用代理 URL
- conanfile.py 应使用 Autotools helper 而非 self.run() 手动执行命令
---

**编译结束**: 2026-07-01 19:36
**最终状态**: published
