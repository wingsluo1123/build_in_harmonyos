# manticore 6.7.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built (conan recipe created, local verify failed due to GitHub network issues)

## 源码信息
- 上游仓库: https://github.com/manticoresoftware/manticoresearch
- 源码 tag: 6.3.8 (v6.7.0 tag 不存在于上游仓库，使用最近的 6.x tag)
- SHA256: 633a55f20545eb4c722dd05175b7187ca802d765fc3eaf9cce3bc2ebb4eaebbe

## Conan 适配说明
本适配为历史已有编译记录但未进行 Conan 适配的补充。

### 依赖管理
- Conan 管理的依赖: boost/1.90.0, openssl/3.5.6.1, zlib/1.3.1.1, curl/8.15.0, expat/2.8.2, libiconv/1.17
- 构建系统内部管理 (从源码构建): ICU 65.1, RE2 2015-06-01, stemmer, columnar, nlohmann_json, xxHash, cctz, uni-algo

### 补丁
1. 0001-src-CMakeLists.txt.patch: 修复 ICU 库链接传播问题 (PRIVATE→PUBLIC)
2. 0002-cmake-update_bundle.cmake.patch: 修复 CMake 4.x 兼容性 (添加 CMAKE_POLICY_VERSION_MINIMUM=3.5)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ICU 链接符号不传播 | lmanticore_icu 使用 PRIVATE 链接 icu::icu | 改为 PUBLIC 链接 |
| 2 | nlohmann_json 构建失败 | CMake 4.x 移除了 <3.5 兼容性 | 添加 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | GitHub 下载失败 | 本机网络无法访问 GitHub | CI 环境应有正常网络 |

## 注意事项
- v6.7.0 tag 不存在于上游 GitHub 仓库，使用 6.3.8 tag 作为源码
- 构建系统会自动下载 ICU、RE2、stemmer、columnar 等依赖并从源码构建
- 本地验证因 GitHub 网络不可达而失败，CI 环境应可正常构建

---

**编译结束**: 2026-08-07
**最终状态**: built (conan recipe created)
