# tiff 4.6.0 — 编译适配记录

> 归档创建: 2026-10-04
> 库: tiff (libtiff, https://gitlab.com/libtiff/libtiff)
> 状态: built（本地 W3 验证通过）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | tiff (libtiff) |
| 版本 | 4.6.0 |
| 构建系统 | CMake |
| 源码 | https://gitlab.com/libtiff/libtiff/-/archive/v4.6.0/libtiff-v4.6.0.tar.gz |
| SHA-256 | fdd1a2a35b20734a5232527a81d7365eb66e54732bfc44474a3124bcb85221c7 |

## 二、适配要点
1. E092: CMake 不识别 HarmonyOS → `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（配方 generate() 内按 os 判断映射）。
2. OHOS 工具链 clang-15 不接受 `-stdlib=libstdc++`，profile 必须 `compiler.libcxx=libc++`。
3. 可选依赖（jbig/lerc/lzma/zstd/webp/deflate）在 OHOS 上禁用，仅保留已发布的 zlib/1.3.1 + libjpeg/10。
4. 静态构建（BUILD_SHARED_LIBS=OFF），产物 libtiff.a / libtiffxx.a + CLI 工具（tiffinfo/tiffcp/tiffdump/tiffset/tiffsplit）。
5. cmake 4.x 兼容：`CMAKE_POLICY_VERSION_MINIMUM=3.5`。

## 三、验证
- conan create: 通过（test_package 1/1，consumer 用例 test_tiff 真实调用公开 API 创建/读写 TIFF 文件）
- 上游测试: 52/52 通过（19 个独立可执行用例 + 33 个工具/转换用例，ctest 全过）
- 鸿蒙专项测试: test_ohos_tiff.c 基于 TIFFClientOpen 内存 IO 往返校验通过（__OHOS__ 守卫真实编译生效）
- W3 本地 CI 模拟: 通过（build_and_test.sh + setup.sh，JC/L0 全过，prdiff 模式，Junk Files: 0）

## 四、CLI 声明（R38）
- 软件级 commands.json 已声明 type=tool，versions.4.6.0，5 个 CLI 工具实测可运行（tiffinfo 读取测试图像 RC=0）。
---

**编译结束**: 2026-10-05 00:00
**最终状态**: built
