# hackrf 2024.02.1 适配笔记

## 构建环境

- 构建系统: CMake
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 平台: HarmonyOS PC (aarch64)
- 状态: built

## 源码与依赖

- 源码: https://github.com/greatscottgadgets/hackrf/releases/download/v2024.02.1/hackrf-2024.02.1.tar.xz
- SHA-256: `d9ced67e6b801cd02c18d0c4654ed18a4bcb36c24a64330c347dfccbd859ad16`
- Conan 依赖: `libusb/1.0.27`
- FFTW: 可选；缺失时不构建 `hackrf_sweep`

## Conan 配方

配方使用 Conan 2.x CMake 工具：

- 从源码树的 `host/` 子目录配置 CMake。
- 设置 `BUILD_SHARED_LIBS=OFF`，生成静态 `libhackrf`。
- 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，兼容上游旧版 CMake 配置。
- 应用 `0001-host-hackrf-tools-src-CMakeLists.txt.patch`，使 FFTW 可选。
- 应用 `0002-host-respect-build-shared-libs.patch`，让上游遵循静态库选项并在 OHOS 上安装库和头文件。
- 生成并安装 HackRF 命令行工具及 `libhackrf`。

## 验证

`test_package` 通过 `hackrf::hackrf` 链接 `libhackrf`，并调用
`hackrf_init()` 和 `hackrf_exit()`。在未连接 HackRF 设备或 USB 后端不可用时，
测试接受 `HACKRF_ERROR_LIBUSB`；其他未预期错误会使测试失败。

## 注意事项

- `hackrf_sweep` 需要 FFTW；当前配方未声明 FFTW，因此该工具不会构建。
- 其他工具运行时可能需要 HackRF 硬件设备。
