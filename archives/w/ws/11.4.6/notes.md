# ws 11.4.6 适配笔记

> 上游：IXWebSocket 11.4.6（https://github.com/machinezone/IXWebSocket，tag v11.4.6）。
> Alpine 将该软件打包名为 `ws`（CLI 名），本仓跟随该命名，包含 libixwebsocket + `ws` 命令行工具。

## 编译环境
- 构建系统: cmake（上游 CMakeLists，非 autotools——init-build 按 URL 猜成 autotools，已纠正）
- 编译日期: 2026-10-13
- 编译器: clang 15.0.4 (OHOS SDK, libc++)，本机即鸿蒙 PC arm64（原生构建）
- 状态: published

## 编译步骤

```bash
# 依赖（全部来自 ohpcd 制品仓，均为预编译二进制）
conan install --requires=zlib/1.3.1 --requires=openssl/3.5.8.1 \
  --requires=spdlog/1.11.0 --requires=fmt/8.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -g CMakeToolchain -g CMakeDeps

cmake -S .. -B . -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release -DUSE_TLS=ON -DUSE_ZLIB=ON -DUSE_WS=ON -DUSE_TEST=ON
cmake --build . -j4
ctest            # 14 项上游测试
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(VERSION 3.4.1...)` 被本机 cmake 4.1.2 拒绝（< 3.5 兼容已移除） | 上游声明版本过旧 | 补丁：3.4.1 → 3.5（纯构建系统修复） |
| 2 | spdlog 由上游 FetchContent 网络拉取（v1.8.0），非 hermetic | 上游构建假设有网络且不锁定制品 | 补丁：改 `find_package(spdlog CONFIG REQUIRED)`，链接 `spdlog::spdlog` |
| 3 | `ZLIB::ZLIB` / `OPENSSL_LIBRARIES` 等 FindOpenSSL/FindZLIB 模块变量在 conan CMakeDeps 下为空 | conan 提供的是 imported target（zlib::zlib/openssl::openssl），非模块变量 | 补丁：`if (TARGET openssl::openssl)` 分支链接 conan target；zlib 链接改 `zlib::zlib` |
| 4 | 编译报 `'fmt/core.h' file not found`（ws.cpp/test） | **conan 2 skip_shared_packages 策略**：spdlog 是 shared 包，其传递依赖 fmt 的 cpp_info 被清空（CMakeDeps 生成空数据）；最小复现已验证（直接 require fmt → 数据完整；经 spdlog 传递 → 空） | 配方 `requirements()` 把 `fmt/8.1.1` 声明为直接依赖 + CMake 显式 `find_package(fmt)`+链接 `fmt::fmt` |
| 5 | IXUnityBuildsTest 编译报 `'openssl/bio.h' file not found` | 上游把 OpenSSL include 以 `BUILD_INTERFACE` 挂 PUBLIC；conan 分支走 PRIVATE 链接后 in-tree 消费者（测试/ws）拿不到 openssl 头文件（IXSocketOpenSSL.h 是公共头，内含 `<openssl/*.h>`） | 补丁：conan 分支补 `target_include_directories(ixwebsocket PUBLIC $<BUILD_INTERFACE:$<TARGET_PROPERTY:openssl::openssl,INTERFACE_INCLUDE_DIRECTORIES>>)` |
| 6 | 测试二进制加载失败 `libspdlog.so.1.11 not found` | conan shared 依赖不在加载器搜索路径 | 运行时 source conanrun.sh（LD_LIBRARY_PATH 指向 conan 包 lib/） |

## 源码修改（patches/，由 refresh-patch --auto 从 .work 树生成）

- `CMakeLists.txt`：① cmake_minimum_required 3.4.1→3.5；② spdlog FetchContent→find_package + fmt 显式链接；③ OpenSSL conan target 兼容分支（含 BUILD_INTERFACE include 传播）；④ ZLIB::ZLIB→zlib::zlib
- `ws/CMakeLists.txt`：spdlog→`spdlog::spdlog fmt::fmt`
- `test/CMakeLists.txt`：同上（ixwebsocket_test 与各测试目标）

均为纯构建系统修复，无平台宏（R8 合规）、无源码语义改动。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| zlib | 1.3.1 | ohpcd（预编译） | permessage-deflate 压缩 |
| openssl | 3.5.8.1 | ohpcd（预编译） | TLS（wss/curl 子命令），静态 |
| spdlog | 1.11.0 | ohpcd（预编译） | ws CLI / 测试日志 |
| fmt | 8.1.1 | ohpcd（预编译） | spdlog 外置 fmt；**必须直接依赖**（见问题#4） |

## R51 上游测试申报表

- 上游清点（三种粒度，实测自洽）：`test/` 目录共 **23 个含 TEST_CASE 的测试文件**（`grep -l TEST_CASE test/*.cpp | wc -l`；Catch2 v2.13.8，单头内置，无 FetchContent）——本次申报采用的上游全量口径；**16 项**在上游 `test/CMakeLists.txt` 注册为 ctest 目标（`ctest -N`；13 基础 + 2 项 `if (UNIX)` 门控 [IXHttpServerTest/IXWebSocketChatTest] + 1 项 `if (USE_ZLIB)` 门控 [IXWebSocketPerMessageDeflateCompressorTest]）——即任何 UNIX 类平台（Linux/macOS/OHOS）注册执行的最大集；16 个注册文件内 TEST_CASE 声明 20 个，23 个文件合计 36 个。其余 **7 项为上游自身禁用、未在任何平台注册**（与适配无关）：5 项被上游 CMakeLists 注释禁用——IXHttpClientTest（FIXME httpbin.org does not seem normal）、IXWebSocketBroadcastTest（FIXME was depending on cobra）、IXWebSocketPingTest/IXWebSocketPingTimeoutTest（上游注释：fails intermittently, disabling for now）、IXWebSocketLeakTest（上游注释：#224 未修复、不编译）；另有 2 项上游 CMakeLists 完全未接线——IXSentryClientTest、IXStreamSqlTest（零引用）。
- UNIX 门控 2 项补测：上游 `if (UNIX)` 还注册 IXHttpServerTest/IXWebSocketChatTest。探索构建为原生手工环境（未设 CMAKE_SYSTEM_NAME，CMake 将 HarmonyOS 视为未知平台 → UNIX 为空），该 2 项默认不注册故 ctest -N 为 14；补跑（-DUNIX=1，注册 16 项）实测：IXWebSocketChatTest ✓；IXHttpServerTest 2 用例 1 过 1 败，失败用例为 makeRedirectServer("http://www.google.com") 重定向后需访问 google.com，同外网不可达限制（errorCode=1 连接超时 60s），非适配问题。打包构建工具链下 CMAKE_SYSTEM_NAME=OHOS（Platform/OHOS.cmake → include Platform/Linux/UnixPaths → set(UNIX 1)）会注册全部 16 项。
- 实测环境：本机（鸿蒙 PC arm64 真机），13/14 通过：

| # | 测试 | 结果 | 耗时 | 说明 |
|---|------|------|------|------|
| 1 | IXSocketTest | ✗ Failed | 3.1s | 唯一失败项：用例"Connect to google HTTPS server over port 443"需访问 google.com:443，**构建环境网络不可达**（curl https://www.google.com → 000 超时；对照组 baidu.com → 200 正常）。本地断言 6/7 通过，仅外网连接断言失败（按上游 timeoutSecs=3 取消等待）。非适配问题，真机完整外网环境下应通过 |
| 2 | IXSocketConnectTest | ✓ | 5.1s | 含垃圾主机名 DNS 失败用例等待时间 |
| 3 | IXWebSocketServerTest | ✓ | 5.0s | 本机回环 server/client |
| 4 | IXWebSocketTestConnectionDisconnection | ✓ | 13.5s | |
| 5 | IXUrlParserTest | ✓ | 0.06s | |
| 6 | IXUnityBuildsTest | ✓ | 0.04s | 全部公共头 unity 编译 |
| 7 | IXHttpTest | ✓ | 0.06s | |
| 8 | IXDNSLookupTest | ✓ | 2.4s | 真实 DNS 解析 |
| 9 | IXWebSocketSubProtocolTest | ✓ | 0.07s | |
| 10 | IXStrCaseCompareTest | ✓ | 0.06s | |
| 11 | IXExponentialBackoffTest | ✓ | 0.04s | |
| 12 | IXWebSocketCloseTest | ✓ | 7.8s | |
| 13 | IXWebSocketHostTest | ✓ | 0.10s | |
| 14 | IXWebSocketPerMessageDeflateCompressorTest | ✓ | 0.04s | zlib 压缩协商路径 |

**通过率 13/14 = 92.9%**（唯一失败为外部网络不可达，证据见上）。

UNIX 门控补测（启用 `if (UNIX)` 注册，编号续上表）：

| # | 测试 | 结果 | 说明 |
|---|------|------|------|
| 15 | IXWebSocketChatTest | ✓ | 本机回环 chat server/client |
| 16 | IXHttpServerTest | ✗ Failed | 2 用例 1 过 1 败：失败用例重定向目标 http://www.google.com（外网不可达，errorCode=1 连接超时 60s）；通过的用例为本地 301 重定向不跟随。非适配问题 |

补测汇总：ctest 注册的 16 项上游测试全部运行，14 过 2 败，两个失败项均为外网不可达限制（google.com:443 / google.com 重定向），本地回环类用例全部通过。（`test/` 文件全量口径 23 项，其余 7 项为上游自身禁用、任何平台均不注册，见上清点；16 项注册集与上游 Linux/macOS 行为完全一致，无适配裁剪。）

## 验证结果

```bash
$ ws --version
ws ixwebsocket/11.4.6 linux ssl/OpenSSL OpenSSL 3.5.8 25 Aug 2026 zlib 1.3.1

$ ws echo_server --port 8765 &   # + 客户端连接
[info] Listening on 127.0.0.1:8765
[info] New connection / remote ip: 127.0.0.1
[info] Headers: Connection: Upgrade / Sec-WebSocket-Extensions: permessage-deflate; server_max_window_bits=15; client_max_window_bits=15
# ↑ ws CLI 客户端 ↔ 服务端完整 WebSocket 握手（含 permessage-deflate 压缩协商）在本机回环验证通过

$ ctest
93% tests passed, 1 tests failed out of 14   # 失败项见 R51 表
```

## 注意事项

- spdlog→fmt 的 skip_shared_packages 行为（问题#4）是环境级知识，已生成知识图谱草稿。
- `ws connect` 在管道模式下发完消息保持连接（交互式语义），做自动化验证时注意加超时。
- 上游测试运行需 `source conanrun.sh`（LD_LIBRARY_PATH 含 spdlog/fmt 的 .so）。

### 对话 #1（2026-10-13，适配主会话）

1. 原生编译：USE_TLS/USE_ZLIB/USE_WS/USE_TEST 全开 → 4 类错误逐个定位
   （cmake_minimum_required 3.4.1、ZLIB::ZLIB、OPENSSL_INCLUDE_DIR 空、
   spdlog FetchContent 改 find_package 后 fmt 头丢失）。
2. 真机跑 14 个上游测试：13/14 通过，IXSocketTest 仅外网连接断言失败
   （curl google.com→000 超时 vs baidu.com→200，环境网络受限）。
3. 功能回环：`ws echo_server` + `ws connect` 完成 WebSocket 握手与
   permessage-deflate 协商（日志见上）。
4. 配方化：conanfile.py + 3 个补丁 + test_package（echo 回环 + CLI 冒烟），
   conan-verify 8 项门禁全过（过程历经 CMakeDeps 缺失、XPM 签名两处修复）。
5. finish：W3 本地 CI 通过（zsh here-doc 需 TMPPREFIX，见知识条目 E482），
   知识沉淀 E429/E430/E431 草稿，submit 就绪。

### 对话 #2（2026-10-13，W4 审计与修复）

1. W4 独立审计轮 1：抓出 2×P1——本地 W3 镜像回退改写 conandata.yml
   未还原（git checkout 还原）+ 缺软件级 manifest.yaml（按模板补齐）。
2. W4 独立审计轮 2：确认 2 个 P1 已修；抓出新 P1——我补写的 UNIX 门控
   说明把平台语义写反（实测 OHOS 工具链 UNIX=1，是原生环境 UNIX 空）。
3. 按审计实证修正说明，并补跑 2 项 UNIX 门控测试：IXWebSocketChatTest
   通过、IXHttpServerTest 唯一失败用例重定向 google.com（外网不可达）。
   上游 ctest 注册集 16/23 项全部运行：14 过 2 败（均为外网限制；
   其余 7 项为上游禁用、不注册）。
4. 修正后重新提交审计（轮 3）。

---

**编译结束**: 2026-10-13 18:04
**最终状态**: published
