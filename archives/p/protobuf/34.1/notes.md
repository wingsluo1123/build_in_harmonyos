# protobuf 34.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-16
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤
1. git clone from gitcode.com/protocolbuffers/protobuf (tag v34.1)
2. abseil-cpp 先安装到 $DEFAULT_PREFIX (91个静态库)
3. CMake 配置: cmake .. -DCMAKE_PREFIX_PATH=$DEFAULT_PREFIX -Dprotobuf_BUILD_TESTS=OFF -Dprotobuf_BUILD_SHARED_LIBS=OFF
4. make -j4 → 100% 编译成功
5. make install → 6个静态库 + protoc 可执行文件

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conandata.yml SHA256 不匹配 | gitcode clone tarball 与 GitHub archive tarball 不同 | 用 conan create 从 GitHub 下载的实际 SHA256 |
| 2 | test_package 找不到 absl/base/attributes.h | abseil-cpp 依赖未声明为 transitive | requirements 加 transitive_headers=True, package_info 加 cpp_info.requires |
| 3 | test_package 编译失败 no member 'c_str' in string_view | protobuf 34.1 name() 返回 string_view | 用 std::string(desc->name()) 转换 |

## 源码修改
无补丁，无源码修改。

## 依赖版本
- abseil-cpp/20260107.1

## 验证结果
- conan create: ✅ PASS
- G1-G4 全部通过
