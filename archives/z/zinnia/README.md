# zinnia

Yet Another Hand Written Character Recognizer（手写字符识别库）。

- **官方主页**: https://zinnia.sourceforge.net/
- **构建系统**: autotools
- **许可证**: BSD-3-Clause

## 能力

- C++ 手写字符识别库（`libzinnia`，SVM-based）
- 命令行工具：`zinnia`（识别器）、`zinnia_learn`（SVM 训练器）、`zinnia_convert`（模型转换）
- 无第三方依赖（仅依赖系统 libc / libc++_shared / libm）

## 鸿蒙 PC 适配说明

- 版本 `0.06` 已适配编译到 `aarch64-linux-ohos`（HarmonyOS PC）
- 适配补丁：config.guess/sub 增加 HarmonyOS 三元组识别、configure umask 022 规避 HMDFS 权限陷阱、trainer.cpp C++11 make_pair 兼容修复
- 详见 `0.06/notes.md`
