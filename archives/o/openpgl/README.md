# OpenPGL - Intel Open Path Guiding Library

## 简介
Intel Open Path Guiding Library (Open PGL) 实现了一组表示和训练算法，用于将路径引导集成到渲染器中。Open PGL 提供当前最先进的路径引导方法的实现，可以提高采样质量，从而提高渲染器的效率。

## 版本
- **0.7.1** (2026-06-08) - 当前版本，已编译发布

## 依赖
- **TBB** (Intel Threading Building Blocks) - 必需

## 平台适配说明

### HarmonyOS (ARM 架构)
- **设备类型**: 必须使用 `PGL_DEVICE_TYPE_CPU_4`
- **SIMD**: NEON (4-wide)
- **限制**: CPU_8 设备类型不支持

### 使用示例
```cpp
// 创建设备 - 使用 CPU_4
PGLDevice device = pglNewDevice(PGL_DEVICE_TYPE_CPU_4, 0);

// 创建 FieldArguments
PGLFieldArguments args;
pglFieldArgumentsSetDefaults(args, PGL_SPATIAL_STRUCTURE_KDTREE,
                              PGL_DIRECTIONAL_DISTRIBUTION_PARALLAX_AWARE_VMM,
                              true, 32000);

// 创建 SampleStorage
PGLSampleStorage sampleStorage = pglNewSampleStorage();
PGLSampleData sample;
sample.position = {0.0f, 0.0f, 0.0f};
sample.direction = {1.0f, 0.0f, 0.0f};
sample.weight = 1.0f;
sample.pdf = 0.25f;
pglSampleStorageAddSample(sampleStorage, sample);
```

## 功能测试结果 (0.7.1)
- 测试通过: 17
- 测试失败: 2 (CPU_8 设备不支持)
- 结论: 功能可用，存在架构限制

## 产物
- 库文件: `lib/libopenpgl.so`
- 头文件: `include/openpgl/*.h`
- CMake 配置: `lib/cmake/openpgl-0.7.1/*.cmake`

## 补丁
编译过程中应用了以下补丁：
1. `0001-CMakeLists-arm-detection.patch` - ARM 架构检测增强
2. `0002-openpgl-CMakeLists-narrowing.patch` - 禁用窄化转换警告
3. `0003-embree-sysinfo-ohos.patch` - pthread affinity API 替代
4. `0004-embree-thread-ohos.patch` - pthread_cancel 替代

## 参考
- [GitHub 仓库](https://github.com/OpenPathGuidingLibrary/openpgl)
- [官方文档](http://www.openpgl.org)