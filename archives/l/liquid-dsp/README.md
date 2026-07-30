# liquid-dsp

## 简介
liquid-dsp 是一个免费开源的信号处理库，专为软件定义无线电（SDR）设计。使用 C 语言编写，提供模块化 DSP 组件。

## OHOS 适配

### 构建要点
- **构建系统**: CMake（v1.8.0 已迁移至 CMake）
- **编译方式**: 零补丁编译通过
- **静态库**: `libliquid.a`（Release, aarch64，~1.7MB）
- **产物**: 静态库 + 头文件 + CMake配置 + pkg-config

### 依赖
无外部依赖。仅依赖 libc + libm，系统自带。

## 功能验证
```bash
# 验证版本号
cc -o test_version test_version.c -lliquid -lm
./test_version
```

## 参考
- 官网：https://liquidsdr.org
- 源码：https://github.com/jgaeddert/liquid-dsp
- 许可证：MIT
