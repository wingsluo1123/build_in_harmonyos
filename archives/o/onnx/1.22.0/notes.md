# ONNX 1.22.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-16
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤
1. git clone from gitcode.com/onnx/onnx (tag v1.22.0)
2. abseil-cpp 和 protobuf 先安装到 $DEFAULT_PREFIX
3. CMake 配置: cmake .. -DCMAKE_PREFIX_PATH=$DEFAULT_PREFIX -DONNX_BUILD_CUSTOM_PROTOBUF=OFF -DONNX_ML=ON
4. make -j4 → 100% 编译成功
5. make install → 2个静态库 (libonnx.a, libonnx_proto.a) + CMake 配置 + 头文件

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conandata.yml SHA256 不匹配 | gitcode clone tarball 与 GitHub archive tarball 不同 | 用 conan create 从 GitHub 下载的实际 SHA256 |
| 2 | test_package 找不到 onnx/onnx.pb.h | ONNX_ML=ON 时安装的文件名为 onnx-ml.pb.h | package_info 声明 ONNX_ML=1 define |
| 3 | test_package 编译报 unknown type 'TypeProto' | schema.h 内部类型无命名空间前缀 | 改用 onnx/onnx_pb.h + onnx::ModelProto 直接测试 |

## 源码修改
无补丁，无源码修改。

## 依赖版本
- abseil-cpp/20260107.1
- protobuf/34.1

## 验证结果
- conan create: ✅ PASS
- G1-G4 全部通过
