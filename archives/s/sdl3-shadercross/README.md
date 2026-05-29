# SDL3 Shadercross

SDL3_shadercross 是 SDL3 的着色器交叉编译扩展库，用于将 SPIRV 或 HLSL 着色器转换为 DXBC、DXIL、SPIRV、MSL 或 HLSL 格式。

## 描述

这是一个用于将着色器转换为不同格式的库，专为 SDL 的 GPU API 设计。它支持：

- **输入格式**: SPIRV、HLSL
- **输出格式**: DXBC、DXIL、SPIRV、MSL、HLSL

该库可以执行运行时翻译，并方便地从 HLSL 或 SPIRV 源返回编译后的 SDL GPU 着色器对象。同时提供命令行工具用于离线着色器翻译。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 3.0.0-preview1 | built | 2026-05-29 | 首次编译，vendored 模式 |

## 编译依赖

- SDL3 3.4.8+（核心库）
- SPIRV-Cross（vendored）
- SPIRV-Headers（vendored）
- SPIRV-Tools（vendored）

## 特殊说明

1. **Vendored 模式必需**: 当前无 SPIRV-Cross 预编译包，必须使用 `-DSDLSHADERCROSS_VENDORED=ON`
2. **NEEDED 路径修复**: 构建系统生成的依赖路径需手动修复（见 3.0.0-preview1 notes.md）
3. **DXC 功能禁用**: OpenHarmony 不支持 DirectX Shader Compiler，使用 `-DSDLSHADERCROSS_DXC=OFF`
4. **__stdcall 警告**: Windows 特定调用约定在 ARM64 上不支持，但不影响编译

## 许可证

Zlib license

## 官方资源

- 项目主页: https://github.com/libsdl-org/SDL_shadercross
- SDL3 主项目: https://github.com/libsdl-org/SDL