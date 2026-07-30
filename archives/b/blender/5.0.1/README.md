# Blender 5.0.1

> 专业3D创作套件 - HarmonyOS 无头版本

## 简介

Blender 是全球领先的开源3D创作套件，支持建模、动画、模拟、渲染、合成和运动追踪等功能。

本适配版本针对 HarmonyOS (OHOS) 平台进行优化，编译为**无头模式(headless)**，适用于服务器渲染和自动化流水线。

## OHOS 适配要点

1. **无头模式构建**: `WITH_HEADLESS=ON`，禁用所有 GUI 组件
2. **GPU 特性禁用**: CUDA/HIP/OpenCL 在 OHOS 上不可用，默认禁用
3. **Python 禁用**: 为降低适配复杂度，默认关闭 Python 集成
4. **平台识别**: CMake 已添加 OHOS 平台检测

## 功能验证

```bash
# 版本检查
blender --version

# 渲染测试 (需要 .blend 文件)
blender -b -o /tmp/render_####.png -s 1 -e 1 -a /path/to/scene.blend
```

## 已知限制

- GUI 功能不可用 (OHOS 无图形界面)
- GPU 渲染功能不可用 (无 CUDA/HIP/OpenCL)
- Python API 不可用
- 部分编解码器功能受限

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| CMake | ≥3.10 | 构建系统 |
| LLVM/Clang | - | OHOS 系统自带 |
| zlib | - | 系统库 |

## 参考

- [官方文档](https://docs.blender.org/)
- [源码仓库](https://github.com/blender/blender)
- [构建指南](https://wiki.blender.org/wiki/Building_Blender)
