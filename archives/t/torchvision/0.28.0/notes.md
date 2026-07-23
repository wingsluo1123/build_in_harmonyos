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

### 1. OHOS CMake platform settings
- OHOS 平台 cmake 报 "System is unknown"
- Set `CMAKE_SYSTEM_NAME=Linux` only when `settings.os == "OHOS"`
- Set `CMAKE_SYSTEM_PROCESSOR=aarch64` for the OHOS armv8 target; this override is guarded to OHOS only
- 必须同时设置 `CMAKE_CROSSCOMPILING=OFF` (否则 sleef 的 add_host_executable 走 IMPORTED 分支)

### 2. CMAKE_LINK_WHAT_YOU_USE 禁用
- PyTorch CMakeLists.txt 第79行硬编码 `CMAKE_LINK_WHAT_YOU_USE TRUE`
- OHOS 无 ldd 命令，LWYU 检查失败
- 修改为 `CMAKE_LINK_WHAT_YOU_USE FALSE`

### 3. libtorch dependency-side patches
- `torch/headeronly/macros/Macros.h` `__assert_fail` declaration compatibility is a libtorch source adaptation item.
- `c10/util/Enumerate.h` `ssize_t` compatibility is also a libtorch source adaptation item.
- This torchvision recipe does not patch libtorch sources directly; those changes belong in the future `libtorch/2.9.0` recipe.
- Because the libtorch Conan dependency is not available yet, this PR remains `status: failed`.

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
  # OHOS only: CMAKE_SYSTEM_NAME=Linux, CMAKE_SYSTEM_PROCESSOR=aarch64 \
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
- 编译: failed, libtorch 2.9.0 is not yet available as a Conan dependency for validation
- 验证: waiting for full Conan recipe validation after libtorch 2.9.0 is available in the Conan artifact registry
- Current limitation: libtorch 2.9.0 is not available as a Conan dependency yet, so this recipe remains failed until the dependency is available and validation succeeds
---

**编译结束**: 2026-07-16 15:26
**最终状态**: failed
