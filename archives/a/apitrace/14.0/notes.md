# apitrace 14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载 apitrace 14.0 源码 + 8 个 git submodules
2. 应用补丁:
   - 0001-CMakeLists.txt: 添加 ENABLE_LTO 选项
   - 0002-thirdparty-brotli.cmake: 添加缺失的 brotli 源文件
3. CMake 构建: ENABLE_LTO=OFF, ENABLE_GUI=OFF, ENABLE_X11=OFF, ENABLE_EGL=ON
4. make check 通过 (5 个测试)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | brotli hidden symbol 链接错误 | brotli 1.2.0 新增源文件未在 brotli.cmake 中列出 | 补丁 0002 |
| 2 | LTO 导致 brotli hidden symbol 无法解析 | CMAKE_INTERPROCEDURAL_OPTIMIZATION 导致 lld 无法解析隐藏符号 | 补丁 0001: ENABLE_LTO=OFF |
| 3 | GUI 依赖 Qt 不可用 | OHOS 无 Qt | ENABLE_GUI=OFF |
| 4 | X11 不可用 | OHOS 无 X11 | ENABLE_X11=OFF |
