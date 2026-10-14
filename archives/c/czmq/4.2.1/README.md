# czmq 4.2.1 for HarmonyOS PC

## 概述

CZMQ 4.2.1（ZeroMQ 高层 C 封装，纯 C）在 HarmonyOS/OpenHarmony PC (aarch64) 上的
Conan 配方适配。构建系统 CMake；4.2.1 为上游最新稳定版（2021-01-17 发布，此后无更高版本）。
本版本由前任 autotools partial 记录升级为 v3.0 完整 conan 配方。

## 归档信息

| 项目 | 值 |
|------|-----|
| 名称 | czmq |
| 版本 | 4.2.1 |
| Conan 引用 | czmq/4.2.1 |
| 源码 | https://github.com/zeromq/czmq/releases/download/v4.2.1/czmq-4.2.1.tar.gz |
| SHA256 | 5d720a204c2a58645d6f7643af15d563a712dad98c9d32c1ed913377daa6ac39 |
| License | MPL-2.0 |
| 状态 | built |

## 构建

```bash
conan create archives/c/czmq/4.2.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

- 依赖：zeromq/4.3.5（conan requires）
- 开关：CZMQ_BUILD_SHARED=ON、ENABLE_DRAFTS=OFF、6 个 CZMQ_WITH_* 可选依赖全 OFF
- SONAME（E330）：CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON +
  CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,（HarmonyOS 为 CMake 未知平台，
  默认无 SONAME；产物单文件 libczmq.so、SONAME=libczmq.so，不生成版本化软链）
- 补丁：0001-CMakeLists.txt.patch（cmake_minimum_required 2.8.12 → 3.5...3.27，CMake 4.x 兼容）

## 产物

- lib/libczmq.so（SONAME=libczmq.so，OHOS ELF 自签名）
- include/（czmq.h + czmq_library.h + 21 个稳定类头）
- bin/zmakecert（OHOS ELF 自签名）
- lib/libczmq.pc（pkg-config 名 libczmq）、share/cmake/czmq/（CMake config）

## 上游测试（设备实测）

- 形态：单二进制 selftest，构建树根目录执行
  `./czmq_selftest --continue --verbose --test <CLASS>`（与上游 ctest 同构 cwd）
- 结果：30 个稳定类全部 PASS
- 网络类：zauth/zmonitor/zproxy/zgossip 真实走 tcp://127.0.0.1 回环；
  zbeacon 的 UDP 广播在本机可用，正常跑完（无需优雅跳过路径）

## 下游契约（zyre 2.0.1）

- pkg-config 名 libczmq（Findczmq.cmake 的 pkg_check_modules 与 configure.ac PKG_CHECK_MODULES 依赖此名）
- CMake config 包名 czmq，导出目标 czmq / czmq-static
- 头文件 czmq.h 位于 include/ 根（Findczmq.cmake 的 find_path NAMES czmq.h）
- ENABLE_DRAFTS 如未来需开启，以 `-o czmq/*:enable_drafts=True` 重建即可，
  .pc 的 Cflags 自动携带 -DCZMQ_BUILD_DRAFT_API=1 并被 zyre 的 Findczmq.cmake 透传
- 消费侧注意：czmq 公共头透传包含 zmq.h，Conan 消费者建议同时直接 requires zeromq
