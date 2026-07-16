# torchvision 0.28.0 适配笔记

## 基本信息
- 软件名: torchvision
- 版本: 0.28.0
- 上游: https://github.com/pytorch/vision
- 构建系统: CMake (C++ 扩展库)
- 构建产物: libtorchvision.so (共享库)

## 核心依赖
- **libtorch (PyTorch 2.9.0)**: 核心依赖，制品仓不可用，从源码编译
  - 源码: https://github.com/pytorch/pytorch v2.9.0
  - 最小化配置: 无CUDA/Python/ROCm/MKLDNN/Distributed
  - 需要手动下载的子模块: pocketfft(cpp分支), eigen, fmt, nlohmann, flatbuffers(v24.12.23), protobuf(v21.12), onnx, sleef, tlfloat, cpuinfo, pthreadpool, FP16, FXdiv, psimd, gemmlowp, kineto
- **libpng**: 制品仓有 libpng/1.6.58 (本次禁用,可后续启用)
- **libjpeg**: 制品仓有 libjpeg/10 (本次禁用,可后续启用)

## 平台适配 (OHOS)

### 1. CMAKE_SYSTEM_NAME 设置
- OHOS 平台 cmake 报 "System is unknown"
- 设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`
- 必须同时设置 `CMAKE_CROSSCOMPILING=OFF` (否则 sleef 的 add_host_executable 走 IMPORTED 分支)

### 2. CMAKE_LINK_WHAT_YOU_USE 禁用
- PyTorch CMakeLists.txt 第79行硬编码 `CMAKE_LINK_WHAT_YOU_USE TRUE`
- OHOS 无 ldd 命令，LWYU 检查失败
- 修改为 `CMAKE_LINK_WHAT_YOU_USE FALSE`

### 3. __assert_fail 声明冲突
- 文件: torch/headeronly/macros/Macros.h:434
- OHOS 系统 __assert_fail 用 `int` 非 `unsigned int`，无 __noreturn__ 属性
- 修改声明匹配系统: `int line` + 移除 `__attribute__((__noreturn__))`

### 4. ssize_t 未定义
- 文件: c10/util/Enumerate.h
- OHOS 不默认定义 ssize_t
- 添加 `#include <sys/types.h>` (非 Windows 平台)

### 5. ldd wrapper
- 创建 /storage/Users/currentUser/usr/local/bin/ldd
- 使用 readelf -d 替代 ldd 功能

### 6. LIBRARY_PATH 设置
- 链接 libtorch_cpu.so 时找不到 libtlfloat
- 设置 `LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib`

### 7. flatbuffers 版本
- PyTorch 要求 flatbuffers 24.12.23
- 从 main 分支下载的是 25.x，需指定 v24.12.23 tag

### 8. pocketfft 分支
- 需要使用 `cpp` 分支而非 `master` 分支
- cpp 分支有 pocketfft_hdronly.h 文件

## CMake 配置参数
```
cmake .. \
  -DCMAKE_PREFIX_PATH=<libtorch安装路径> \
  -DWITH_PNG=OFF \
  -DWITH_JPEG=OFF \
  -DWITH_WEBP=OFF \
  -DCMAKE_BUILD_TYPE=Release
```

## PyTorch CMake 配置参数 (libtorch 构建)
```
cmake .. \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_CROSSCOMPILING=OFF \
  -DBUILD_PYTHON=OFF \
  -DUSE_CUDA=OFF -DUSE_ROCM=OFF -DUSE_MPS=OFF \
  -DUSE_FBGEMM=OFF -DUSE_KINETO=OFF \
  -DUSE_NNPACK=OFF -DUSE_XNNPACK=OFF \
  -DUSE_MKLDNN=OFF -DUSE_DISTRIBUTED=OFF \
  -DUSE_KLEIDIAI=OFF \
  -DUSE_SYSTEM_EIGEN_INSTALL=OFF \
  -DBUILD_TEST=OFF -DBLAS=Eigen \
  -DCMAKE_BUILD_TYPE=Release
```

## 构建产物
- libtorchvision.so (805KB)
- 头文件: include/torchvision/
- CMake config: share/cmake/TorchVision/

## 状态
- 编译: 成功
- 验证: 待 Conan 配方验证
---

**编译结束**: 2026-07-16 15:26
**最终状态**: failed
