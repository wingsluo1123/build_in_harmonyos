# openpgl 0.7.1 编译笔记

## 编译日期
2026-06-08

## 编译环境
- 系统: HarmonyOS
- 架构: aarch64 (ARM)
- 编译器: Clang 15.0.4
- CMake: 3.x

## 依赖
- TBB 2021.13.0 (已安装在 ~/usr/local)

## 编译问题及解决方案

### 问题 1: C++11 窄化转换错误
**症状**: embree 的 avx2neon.h 中使用 `char` 类型初始化 `int8x16_t` 导致窄化转换警告被当作错误处理。
```
error: non-constant-expression cannot be narrowed from type 'char' to 'int8_t' in initializer list [-Wc++11-narrowing]
```
**解决**: 在 openpgl/CMakeLists.txt 的 ARM 架构编译选项中添加 `-Wno-c++11-narrowing`。

### 问题 2: 架构检测失败
**症状**: CMAKE_SYSTEM_PROCESSOR 为 "unknown"，导致 OPENPGL_ARM 未设置，ARM 编译选项未生效。
**解决**: 在 CMakeLists.txt 的架构检测逻辑中添加对 NEON ISA 的检测，强制启用 ARM 模式。

### 问题 3: pthread_getaffinity_np/pthread_setaffinity_np 不可用
**症状**: embree 的 sysinfo.cpp 和 thread.cpp 使用了 `pthread_getaffinity_np` 和 `pthread_setaffinity_np`，这些函数在鸿蒙系统上不可用。
```
error: use of undeclared identifier 'pthread_getaffinity_np'
```
**解决**: 修改 third-party/embreeSrc/common/sys/sysinfo.cpp 和 thread.cpp，添加 `__OHOS__` 宏定义处理，使用 `sched_setaffinity` 替代。

### 问题 4: pthread_cancel 不可用
**症状**: `pthread_cancel` 在鸿蒙系统上未实现。
**解决**: 在 destroyThread 函数中添加 `__OHOS__` 条件，和 Android 一样输出错误提示而非调用 pthread_cancel。

## 修改文件列表
1. openpgl/CMakeLists.txt - 添加 `-Wno-c++11-narrowing` 和 NEON ISA 架构检测
2. CMakeLists.txt - 添加 NEON ISA 强制 ARM 模式
3. third-party/embreeSrc/common/sys/sysinfo.cpp - 添加 `__OHOS__` 处理
4. third-party/embreeSrc/common/sys/thread.cpp - 添加 `__OHOS__` 处理，使用 sched_setaffinity 替代 pthread_setaffinity_np

## 编译参数
```bash
cmake \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DOPENPGL_ISA_NEON=ON \
  -DOPENPGL_ISA_NEON2X=OFF \
  -DOPENPGL_ISA_SSE4=OFF \
  -DOPENPGL_ISA_AVX2=OFF \
  ..
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 安装产物
- lib/libopenpgl.so (1.0M)
- include/openpgl/*.h (34 个头文件)
- lib/cmake/openpgl-0.7.1/*.cmake

## 依赖库
- libtbb.so (TBB 2021.13.0)
- libc++_shared.so
- libc.so

## 验证结果
- ✅ 编译成功
- ✅ 安装成功
- ✅ 库文件生成
- ✅ 头文件完整

---

## 功能测试结果

### 测试日期
2026-06-08

### 测试摘要
| 类别 | 通过 | 失败 |
|------|------|------|
| 版本信息 | 1 | 0 |
| 类型定义 | 4 | 0 |
| 数据结构 | 4 | 0 |
| 设备管理 | 2 | 1 |
| SampleStorage | 5 | 0 |
| FieldArguments | 1 | 0 |
| **总计** | **17** | **2** |

### 已验证功能
- ✅ 设备创建（CPU_4）正常
- ✅ SampleStorage 创建和操作正常
- ✅ 数据结构正确（pgl_vec3f, pgl_point3f, pgl_box3f, PGLSampleData）
- ✅ 类型定义正确（枚举和常量）
- ✅ 版本信息正确（0.7.1）

### 功能限制
- ⚠️ CPU_8 设备类型不支持（"invalid vectorSize parameter!"）
- ⚠️ 必须使用 CPU_4 设备类型作为默认配置

### 使用建议
```cpp
// 正确方式：使用 CPU_4 设备
PGLDevice device = pglNewDevice(PGL_DEVICE_TYPE_CPU_4, 0);

// 错误方式：不要使用 CPU_8
PGLDevice device = pglNewDevice(PGL_DEVICE_TYPE_CPU_8, 0);  // 会失败
```

### 问题分析
CPU_8（对应 8-wide SIMD）在 ARM 架构上不支持，可能原因：
1. NEON 向量宽度配置问题
2. 编译选项 `-DOPENPGL_ISA_NEON=ON` 仅启用 4-wide SIMD
3. Intel AVX/AVX2 与 ARM NEON 的架构差异

测试报告详见：`reports/test-report.md`
