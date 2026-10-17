# libpillowfight

Libpillowfight is a library containing various image processing algorithms
(paper scan cleanup): Automatic Color Equalization (ACE), Unpaper's
algorithms (blackfilter, blurfilter, border, grayfilter, masks,
noisefilter), Canny edge detection, Gaussian filter, Sobel operator and
Stroke Width Transformation (SWT).

- Upstream: https://github.com/openpaperwork/libpillowfight
- License: GPL-2.0-only
- Language: C (C99/C11)
- Build system: CMake

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 0.3.1   | built  | 已有适配（gitlab 归档源） |
| 0.2.4   | built  | 本轮适配（GitHub 官方 tag 0.2.4，sha256 32933926…） |

## 适配要点

- CMake 构建，`-DNO_PYTHON` 排除 Python 绑定，仅编译纯 C 库。
- `src/pillowfight/_version.h` 由上游构建要求生成（定义
  `INTERNAL_PILLOWFIGHT_VERSION`），源码包不含，需在配方 `build()` 中动态生成。
- 上游测试为 pytest（Python），OHOS 交叉目标下不可运行；以 test_package
  消费者测试（pf_get_version）与鸿蒙特有测试（pf_ace 实际处理位图）替代验证。
