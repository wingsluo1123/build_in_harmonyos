# zyre 2.0.1 适配笔记

## 编译环境
- 构建系统: cmake（上游双轨 autotools/CMake，本配方走 CMake，与 czmq/zeromq 模板一致）
- 编译日期: 2026-10-16
- 编译器: clang 15（OHOS 工具链，aarch64-linux-ohos triplet）
- 目标: OHOS aarch64（conan profile ohos-aarch64）
- 状态: built

## 配方要点

- conanfile.py 骨架取自刚合入 main 的 archives/c/czmq/4.2.1（同为 zproject 生成的
  CMake 工程，宿主依赖链上游直系模板）；requirements 写法取自
  archives/c/cppzmq/4.10.0（self.requires("czmq/4.2.1")）
- generate() 显式设置：ZYRE_BUILD_SHARED/STATIC、ENABLE_DRAFTS=OFF、
  CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH 注入 czmq+zeromq 包 include/lib 目录
  （Findczmq/Findlibzmq 为 MODULE 模式，pkg-config 查不到时经 find_path/find_library
  兜底命中）、E330 两变量（HarmonyOS 平台 SONAME）、
  LIBZMQ_LIBRARIES="-L<dir>;-lzmq"（发布版 libzmq.so 无 SONAME，经搜索路径链接
  得到相对 DT_NEEDED；libczmq.so 有 SONAME，find_library 直连即可）
- package() 复用 czmq 的 OHOS ELF 自签名步骤（llvm-objcopy 去 .codesign +
  binary-sign-tool selfSign），覆盖 lib/**/*.so* 与 bin/ 下 ELF（bin/zpinger）
- package_info：cmake_file_name=zyre、cmake_target_name=zyre（别名 zyre-static）、
  pkg_config_name=libzyre（上游 src/libzyre.pc.in 的 Name 契约）、system_libs pthread/rt

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x configure 直接报错 | 上游 cmake_minimum_required(VERSION 2.8.12)，CMake 4.x 已移除 <3.5 兼容 | 补丁 0001-CMakeLists.txt.patch 提升至 3.5...3.27（zeromq/czmq 同款做法） |
| 2 | Findczmq.cmake/Findlibzmq.cmake（MODULE 模式）找不到依赖 | 两模块走 pkg_check_modules + 裸 find_path/find_library；Conan 只把 generators 目录放入 CMAKE_PREFIX_PATH，且 czmq 包名探测目标（libczmq/libzmq .pc）不在探测路径上 | generate() 经 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH 注入 czmq/zeromq 包 include/lib 目录（czmq 配方对 libzmq 同款先例） |
| 3 | libzyre.so 的 DT_NEEDED 若直连 conan 缓存绝对路径（libzmq） | 发布版 zeromq 二进制 libzmq.so 自身无 SONAME，链接器只能把全路径写进 NEEDED | generate() 把 Findlibzmq 的 LIBZMQ_LIBRARIES 预置为 "-L<dir>;-lzmq"，链接经搜索路径完成，NEEDED 落成相对名 libzmq.so（czmq 先例） |
| 4 | test_package 编译期找不到 czmq.h/zmq.h | zyre.h 透传包含 <czmq.h>，czmq.h 再透传包含 "zmq.h"；Conan CMakeDeps 对二阶传递依赖刻意剥离 include/libs 数据 | test_package 显式 self.requires("czmq/4.2.1") + self.requires("zeromq/4.3.5")（与 zyre 配方同版本，直连依赖恢复完整数据） |
| 5 | bin/zpinger 触发 R38 | 上游 CMakeLists 仅将 zpinger install 到 bin（zyre_selftest/perf_*/ztester_* 只构建不安装） | 软件级 commands.json（type=tool）必备 |
| 6 | 双节点同主机 UDP beacon 端口冲突疑虑 | ZRE 发现默认 UDP 5670，两个节点需同时绑定 | czmq zbeacon 自测实证 zbeacon socket 带 SO_REUSEADDR 系标志可同绑；test_ohos_flow 双线程双节点真机实测通过 |
| 7 | test_ohos_flow 编译警告 -Wformat-security | zyre_set_header 为 printf 风格变参（CHECK_PRINTF(3)），非字面量实参触发告警 | 以 "X-FLOW", "%s", ctx->name 显式格式串传参，交付源零警告 |

## 上游测试（设备实测）

- 入口：构建树根目录执行 `./zyre_selftest --test <name>`（公开用例 zyre/zyre_event）；
  私有用例 zre_msg/zyre_peer/zyre_group/zyre_election/zyre_node 需以
  enable_drafts=True 构建变体后在同入口执行
- 公开用例（Release，ENABLE_DRAFTS=OFF）：zyre、zyre_event 全部 PASS（含 inproc
  gossip 双节点互联、组播收发、EXIT 优雅退出全流程）
- 私有用例（enable_drafts=True 构建变体）：5/5 全部 PASS（zyre_node 走完整 ZRE
  流程，UDP beacon 真实可用；详见 logs/selftest-kit/，.draft.out 后缀为变体证据）
- 真机 UDP beacon 全链路：test_package 的 test_ohos_flow 双节点用例实证
  （ENTER 发现 + JOIN + SHOUT 组播收发，flow-report.txt 落盘证据）

## 权威 CI（ci/conan/build_and_test.sh）

- 第 1 轮：L0/L1/L4/L5 全 pass，L2 skip（zpinger 为常驻 ping 工具，无
  --version/--help 约定，属工具习惯差异，非阻塞），G0/KC/JC pass，单包 100% 通过
- CI 后按 E415 恢复 conandata.yml 为 HEAD 逐字节一致（镜像改写残留清理）

## 注意事项

- 设备直连 github.com 不通：源码经 conandata 官方 URL + SHA256 钉死，
  CI mirror-fallback（gh-proxy）/预下载通道获取；sources_cache 已预置同 SHA256
  归档作兜底
- zyre 上游 selftest 的 zyre 用例经 inproc gossip 发现（无网络也可跑）；
  UDP beacon 真实网络路径由 test_ohos_flow 双节点用例覆盖
- ENABLE_DRAFTS=ON 变体仅用于上游私有用例验证，发布形态保持默认 OFF

---

**编译结束**: 2026-10-16
**最终状态**: built
