# abseil-cpp 20260107.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-16
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤
1. git clone from gitcode.com/abseil/abseil-cpp (tag 20260107.1)
2. CMake 配置: cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DABSL_PROPAGATE_CXX_STD=ON -DABSL_ENABLE_INSTALL=ON
3. make -j4 → 100% 编译成功
4. make install DESTDIR=$TEST_PREFIX → 91 个静态库安装成功

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conandata.yml SHA256 不匹配 | gitcode clone 的 tarball 与 GitHub 官方 tarball 内容不同 | 使用 conan create 从 GitHub 下载的实际 SHA256 |
| 2 | test_package CMake target 名错误 | cmake_file_name=absl 但 target 名为 abseil-cpp::abseil-cpp | 修正 CMakeLists.txt 中的 target_link_libraries |

## 源码修改
无补丁，无源码修改。

## 依赖版本
无外部依赖。

## 验证结果
- conan create: ✅ PASS
- G1-G4 全部通过
- W3 本地 CI 模拟通过
