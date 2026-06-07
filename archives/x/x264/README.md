# x264 - H.264视频编码核心库

## 软件信息
- **名称**: x264
- **版本**: master (0.165.x)
- **许可证**: Non-GPL commercial
- **构建系统**: Autotools

## 功能简介
x264是开源的H.264/AVC视频编码库，提供高性能的视频编码能力。

## 鸿蒙适配状态
- **状态**: ✅ 编译成功
- **构建日期**: 2026-05-31
- **编译器**: clang 15.0.4
- **架构**: aarch64 (arm64-v8a)

## 编译产物
- `bin/x264`: 可执行文件（186KB）
- `lib/libx264.a`: 静态库（1.5MB）
- `include/x264.h`: 头文件
- `include/x264_config.h`: 配置头文件

## 适配说明
- HMDFS不支持heredoc，导致configure无法生成配置文件
- 通过手动修改Makefile绕过限制
- 禁用了asm和opencl功能
- 生成静态库而非动态库

## 测试验证
```bash
x264 --version
x264 0.165.x
built on May 30 2026, clang: 15.0.4
```

## 参考资料
- 上游地址: https://code.videolan.org/videolan/x264
- 官网: https://www.videolan.org/developers/x264.html