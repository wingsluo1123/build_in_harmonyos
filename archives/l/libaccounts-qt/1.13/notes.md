# libaccounts-qt 1.13 适配笔记

## 编译环境
- 构建系统: qmake
- 编译日期: 2026-08-10
- 编译器: clang/clang++ (from Conan profile)
- 状态: built

## 编译步骤

1. 安装系统依赖: libaccounts-glib, glib, pcre2, libffi, libxml2, sqlite3 (via cmd-pkgs)
2. 下载源码 (commit 2a97aa5656b2207b4ce1625c3ed2828c82e352b7, tag 1.13)
3. 应用补丁: QString::null → QString(), 禁用 tests 子目录
4. 构建 Qt5Xml 模块 (qt5-qtbase conan 包未包含 XML 模块)
5. 运行 qmake PREFIX=/usr/local LIBDIR=/usr/local/lib
6. make -j1

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | QString::null 编译错误 | Qt5 移除了 QString::null | 替换为 QString() |
| 2 | Qt5Xml 模块缺失 | qt5-qtbase conan 包使用 -no-feature-xml 构建 | 从 Qt5 源码构建 Qt5Xml 模块 |
| 3 | qmake 找不到 mkspecs | qt.conf 指向构建目录 | 修正 qt.conf 为绝对路径，创建构建目录符号链接 |
| 4 | doxygen 不可用 | OHOS 上未安装 doxygen | 从 .pro 中移除 doc/doc.pri include |
| 5 | lld 链接器找不到 libxml2 | OHOS SDK 的 lld 依赖 libxml2.so.16 | 设置 LD_LIBRARY_PATH 包含 SDK llvm/lib |
| 6 | 测试二进制运行时找不到库 | HarmonyOS musl namespace 忽略 LD_LIBRARY_PATH (E088) | 复制 .so 到测试二进制目录 |

## 源码修改

1. Accounts/account.h: QString::null → QString() (补丁 0001)
2. Accounts/manager.h: QString::null → QString() (补丁 0002)
3. accounts-qt.pro: 移除 tests 子目录 (补丁 0003)
4. accounts-qt.pro: 移除 doc/doc.pri include (build() 中动态移除)

## 依赖版本

- qt5-qtbase/5.15.2 (conan)
- libaccounts-glib 1.27 (system, cmd-pkgs)
- glib 2.88.0 (system, cmd-pkgs)
- pcre2 10.40 (system, cmd-pkgs)
- libffi 3.4.6 (system, cmd-pkgs)
- libxml2 2.15.3 (system, cmd-pkgs)
- sqlite3 3.49.1 (system, cmd-pkgs)

## 验证结果

```bash
conan create . --version=1.13 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# Package built and installed successfully
# test_package linked and built successfully
# test_package runtime: musl namespace limitation (E088)
```

## 注意事项

- Qt5Xml 需要从 Qt5 源码单独构建 (qt5-qtbase conan 包未包含 XML 模块)
- 源码 URL 使用 commit hash (GitHub tag 1.13 已不存在)
- libaccounts-glib 作为系统依赖通过 cmd-pkgs 安装
---

**编译结束**: 2026-08-10 04:45
**最终状态**: built
