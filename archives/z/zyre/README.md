# zyre 2.0.1 for HarmonyOS PC

## 概述

Zyre 是基于 ZeroMQ/ZMTP 的局域网近邻发现与 P2P 组播消息框架（zproject 生成的纯 C 库）：
节点经 UDP beacon（IANA 注册端口 5670）或 gossip 相互发现，交换头信息（ENTER）、
按组收发消息（JOIN/LEAVE/SHOUT/WHISPER），并提供 zyre_event 事件解析 API。
本条目为 zyre 2.0.1（上游 2021-01-24 发布，MPL-2.0）在 HarmonyOS/OpenHarmony PC
(aarch64) 上的 v3.0 Conan 配方适配。

## 归档信息

| 项目 | 值 |
|------|-----|
| 名称 | zyre |
| 版本 | 2.0.1 |
| Conan 引用 | zyre/2.0.1 |
| 源码 | https://github.com/zeromq/zyre/releases/download/v2.0.1/zyre-2.0.1.tar.gz |
| SHA256 | 0ba43fcdf70fa1f35b068843a90fdf50b34d65a9be7f2c193924a87a4031a98c |
| License | MPL-2.0 |
| 状态 | built |

## 构建

```bash
conan create archives/z/zyre/2.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

- 依赖：czmq/4.2.1（conan requires；zeromq/4.3.5 为其传递依赖）
- 开关：ZYRE_BUILD_SHARED=ON、ENABLE_DRAFTS=OFF（zyre 的 5 个私有类仅在
  enable_drafts=True 时编入）
- SONAME（E330）：CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON +
  CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,（HarmonyOS 为 CMake 未知平台，
  默认无 SONAME；产物单文件 libzyre.so、SONAME=libzyre.so，不生成版本化软链）
- 补丁：0001-CMakeLists.txt.patch（cmake_minimum_required 2.8.12 → 3.5...3.27，
  CMake 4.x 兼容）

## 产物

- lib/libzyre.so（SONAME=libzyre.so，OHOS ELF 自签名）
- include/（zyre.h + zyre_event.h + zyre_library.h）
- bin/zpinger（OHOS ELF 自签名）
- lib/libzyre.pc（pkg-config 名 libzyre）、share/cmake/zyre/（CMake config）
- perf_local/perf_remote/ztester_beacon/ztester_gossip/zyre_selftest 只构建不安装，
  不进入包产物

## 上游测试（设备实测）

- 形态：单二进制 selftest，构建树根目录执行
  `./zyre_selftest <TEST>`；公开用例 zyre、zyre_event 在 Release（ENABLE_DRAFTS=OFF）
  构建；私有用例 zre_msg、zyre_peer、zyre_group、zyre_election、zyre_node 需
  enable_drafts=True 构建变体
- 网络类：zyre 与 zyre_node 走完整 ZRE 流程；上游 selftest 的 zyre 用例经
  inproc gossip 发现（无网络也可跑），真机 UDP beacon 全链路由 test_package 的
  test_ohos_flow 双节点用例覆盖

## 下游契约

- pkg-config 名 libzyre（Findzyre.cmake 的 pkg_check_modules 约定）
- CMake config 包名 zyre，导出目标 zyre / zyre-static
- 头文件 zyre.h include <czmq.h>（czmq.h 再 include zmq.h）：Conan 消费者建议
  同时直接 requires czmq 与 zeromq（CMakeDeps 对二阶传递依赖剥离 include 数据）
- ENABLE_DRAFTS 如未来需开启，以 `-o zyre/*:enable_drafts=True` 重建即可，
  .pc 的 Cflags 自动携带 -DZYRE_BUILD_DRAFT_API=1
