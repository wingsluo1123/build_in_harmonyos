# syntax-highlighting 6.28.0 适配笔记

KDE Frameworks 6 语法高亮引擎，构建产物 `libKF6SyntaxHighlighting.so`（另含上游 `ksyntaxhighlighter6` CLI）。
本版本按任务卡名 `syntax-highlighting` 建档（旧的 ksyntaxhighlighting 6.x 线保留各自包名，两线并存）。

## 编译环境
- 构建系统: cmake（KDE ECM 工程，CMake >= 3.29）
- 编译日期: 2026-10-17
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: built（conan-verify G0-G4 全通过）
- 分支: feat/syntax-highlighting-6.28.0

## 依赖
- qtbase/6.11.1（Qt6 Core/Network/Gui/Test）
- ecm/6.28.0（tool_requires；上游 `find_package(ECM 6.28.0)` 硬要求）
- perl/5.42.2（tool_requires，上游源码用 Perl 生成器）
- 全部命中 ohpcd 制品仓（R36 通过）

## 源码
- URL: https://mirrors.nju.edu.cn/kde/stable/frameworks/6.28/syntax-highlighting-6.28.0.tar.xz
- SHA256: b9d90a03b4e9a48170a14f7a4a79c44f0aae9f14e1b94b7b1fc75d5c3fb31d3a（nju 与 aliyun 双镜像字节一致交叉验证）
- download.kde.org 在 CI worker 上超时（网络受限），源改用权威镜像 nju（kconfig 6.28.0 先例）

## 配方关键点
- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单
- `KF_SKIP_PO_PROCESSING=ON` + 补丁跳过 `ecm_install_po_files_as_qm(poqm)`（无 Qt Linguist 工具链）
- `BUILD_EXAMPLES=OFF` + 补丁添加 BUILD_EXAMPLES option（库打包不需要 examples）
- `QRC_SYNTAX=ON`：语法定义内嵌 QRC，消费者无需外部数据文件
- `BUILD_TESTING=ON`：上游 6 个 CTest 全量执行
- `_library_runtime_env()` 对 OHOS prepend `/system/lib64`（libc++_shared.so 遮蔽修复）
- katehighlightingindexer.cpp 使用 `std::strong_ordering`（C++20），而 profile `compiler.cppstd=17` 作为普通变量在 conan_toolchain.cmake 中遮蔽了 CACHE 写入的 20 → 通过 CMakeLists 补丁强制 `set(CMAKE_CXX_STANDARD 20)`，另在 toolchain 里以 `CMAKE_CXX_FLAGS=-std=c++20` 双保险

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI worker 下载 download.kde.org 超时 | CI 网络受限 | 源改用 mirrors.nju.edu.cn 权威镜像（sha256 双镜像交叉验证，kconfig 6.28.0 先例） |
| 2 | conan create 中 host cmake/qtpaths 运行报 libc++ 符号重定位失败 | 沙箱 LD_LIBRARY_PATH 中不兼容的 libc++_shared.so 遮蔽了兼容版本 | `_library_runtime_env()` 对 OHOS prepend `/system/lib64`（ksanecore/kconfig/kcrash/kio 6.26.0 先例） |
| 3 | katehighlightingindexer.cpp 的 `std::strong_ordering` 编译失败 | profile cppstd=17 普通变量遮蔽 conanfile CACHE 写入 20 | CMakeLists.txt 补丁强制 `set(CMAKE_CXX_STANDARD 20)` + `CMAKE_CXX_STANDARD_REQUIRED ON` |
| 4 | test_package 构建阶段同样被不兼容 libc++ 遮蔽 | 同上 | test_package 的 `_libcxx_env()` prepend `/system/lib64`，build() 与 test() 均应用 |
| 5 | 6.26.0 旧补丁 hunk 行号与 6.28.0 源码不匹配 | 上游 CMakeLists 结构调整 | 在 6.28.0 源码上重放三处改动后重新生成补丁（patch -p1 应用后逐字节比对通过） |

## 测试
- 上游 CTest：**6/6 通过**（wildcardmatcher_test, repository_test, theme_test, testhighlighter_test, htmlhighlighter_test, folding_test）
- highlighter_benchmark / repository_benchmark：BENCHMARK 配置，常规 CTest 不注册
- test_package：消费者链接 KF6::SyntaxHighlighting，加载内嵌 C++ 语法与 Breeze Light 主题 → PASS

## 交付物
- conanfile.py、conandata.yml、manifest.yaml、notes.md、test_package/、patches/0001-CMakeLists.txt.patch

## 知识候选（最终结论）
- 候选 A（KDE tarball utils/*/pyproject.toml 导致 lang-preflight 误判 python）→ **REUSED_EXISTING**：复用 DRAFT-bptree-lang-preflight-pyproject-tooling-false-positive（同 6.26.0 记录）
- 候选 B（profile cppstd=17 普通变量遮蔽 recipe CACHE CMAKE_CXX_STANDARD=20 → CMakeLists 补丁强制项目标准）→ **REUSED_EXISTING**：E096 显式设置 CMAKE_CXX_STANDARD 方案族（6.26.0 同型）
- 候选 C（conan 沙箱 libc++_shared.so 遮蔽宿主 cmake/qtpaths 符号重定位 → LD_LIBRARY_PATH prepend /system/lib64）→ **REUSED_EXISTING**：E657 草稿（6.26.0 创建，本包第二轮复现实证）
- 候选 D（CI worker 下载 download.kde.org 超时 → 权威镜像 nju + sha256 双镜像交叉验证）→ 复用 kconfig 6.28.0 已记录的镜像源适配（本包为第二个实证点）

**编译结束**: 2026-10-17
**最终状态**: built（待 CI 发布后置 published）
