# scribus 1.6.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-29
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: built

## 编译步骤

- init-build 生成骨架（注意：init_build.py 误判 autotools，实际是 CMake，R47 lang-preflight 已确认）
- 源码修改 3 处（Qt5LinguistTools 缺口 + translations 条件化 + CMAKE_PREFIX_PATH 追加）
- refresh-patch --auto 生成 2 个补丁
- conan-init 生成配方后重写为 CMake 版本（conanfile.py 参照 qastools E438 + ball E092 模式）
- conan create 编译验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt5LinguistTools 缺失（find_package REQUIRED 硬失败） | qt5-qtbase 制品不含 LinguistTools（属 qttools 模块），制品仓无 qt5-qttools | 参照 qastools 先例：改为 QUIET 查找 + WANT_TRANSLATIONS OFF 跳过 .qm 生成（翻译运行时加载，界面回退英文） |
| 2 | Qt5OpenGL 组件声明缺失 | qt5-qtbase conan 组件声明缺 Qt5OpenGL，但包内含 libQt5OpenGL.so + Qt5OpenGL cmake 配置 | QT_PREFIX 指向 qtbase 包目录，CMAKE_PREFIX_PATH 追加 qtbase 包（qastools E438 同款），find_package(Qt5OpenGL) 找到原生 config |
| 3 | 上游 set(CMAKE_PREFIX_PATH) 覆盖 conan 注入路径 | CMakeLists_Dependencies.cmake 用 set() 覆盖 CMAKE_PREFIX_PATH，破坏 CMakeDeps 生成的 config 查找 | 改为 list(APPEND CMAKE_PREFIX_PATH "${QT_PREFIX}")（源码补丁 0002） |
| 4 | conan install 版本冲突（zlib/1.3.1 vs 1.3.1.1） | poppler 链依赖 zlib/1.3.1.1，Scribus 直连 zlib/1.3.1 | 配方统一使用 poppler 链版本（zlib/1.3.1.1 等） |
| 5 | OHOS GUI 二进制执行被拒（E077） | 用户存储路径未签名 ELF 执行时 EPERM | package() 阶段用 binary-sign-tool 自签 scribus 二进制（qastools 先例） |

## 源码修改

- CMakeLists_Dependencies.cmake: Qt5LinguistTools REQUIRED→QUIET + WANT_TRANSLATIONS OFF；CMAKE_PREFIX_PATH 改为追加 qtbase 包目录
- CMakeLists.txt: resources/translations 子目录按 WANT_TRANSLATIONS 条件化

## 依赖版本

- qt5-qtbase/5.15.2.2（含 Qt5OpenGL 产物 + 原生 cmake 配置）
- poppler/25.12.0, zlib/1.3.1.1, libjpeg-turbo/3.2.0, libpng/1.6.58, libtiff/4.7.2
- freetype/2.14.3, fontconfig/2.18.1, cairo/1.18.4, lcms2/2.19, libxml2/2.15.3
- cups/2.4.19, harfbuzz/14.2.0, icu/76.1, python/3.12.9
- hunspell/1.7.3, boost/1.90.0.3, librevenge/0.0.5（可选，默认启用）

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | - | CMake 配方（application 类型，签名逻辑） |
| conandata.yml | - | 源码 URL + sha256 + 2 个补丁声明 |
| patches/0001-CMakeLists.txt.patch | 854B | translations 条件化 |
| patches/0002-CMakeLists_Dependencies.cmake.patch | - | Qt5LinguistTools QUIET + CMAKE_PREFIX_PATH 追加 |
| test_package/ | - | 真实 exec 消费者测试（scribus --version） |

## 注意事项

- OHC_PROJECT_DIR 必须指向工作仓库，否则 init-build/conan-init 误写 SKILL 目录
- scribus 构建超时已配置 14400s（ci/config/build_timeouts.txt）
---

**编译结束**: 2026-10-02 18:30
**最终状态**: built

## 知识候选台账（W5 必检，2026-10-02）
| # | 候选 | 状态 | 依据 |
|---|------|------|------|
| 1 | CRLF 行尾源文件补丁生成失败（refresh-patch 产 LF 补丁 dry-run 不匹配 CRLF 源文件，须手动 CRLF 补丁置独立目录） | DRAFT_READY | 草稿 DRAFT-scribus-166-crlf-source-patch(.kv/.md)；draft-review 疑似新知，相似度最高 0.14（E510），正式条目 E254/E484/E066 属另一场景 |
| 2 | OHOS Qt5 制品缺 QCoreApplication::argc()/argv() 成员（WITH_TESTS 开启后 scribusapp.cpp 编译失败） | VERSION_LOCAL | 上游正常 Qt 有该成员，qt5-qtbase 制品裁剪；本任务置空 testargs 绕过；不建草稿 |
| 3 | Qt5Test 在 qt5-qtbase 包内但 CMakeDeps 未暴露 QT_QTTEST_LIBRARY/QT_LIBRARIES（WITH_TESTS 链接 cellareatests 需注入） | REUSED_EXISTING | DRAFT-E5xx-qt5-conan-split-cmake-bridge 同族（Qt5 拆包桥接），本任务复用既有注入模式 |
| 4 | cmake 等构建工具运行时需 SDK c++ 子目录 libc++_shared.so（W3 模拟 cmake 无法启动） | REUSED_EXISTING | E540 runner-path-prepend 同族（runner PATH/LD_LIBRARY_PATH 注入）；binary-sign-tool 同源坑已记录 |

结论：保存 1 个 DRAFT_READY 草稿 → PR 前缀【知识库扩展】。
