# czmq

CZMQ 是 ZeroMQ 的高层 C 封装（纯 C）：在 libzmq 之上提供便利类、zactor 服务与通用数据结构，
附带证书命令行工具 zmakecert。

## 功能概述

- 消息层封装：zsock / zframe / zmsg / zstr / zpoller
- zactor 服务类：zauth / zbeacon / zgossip / zmonitor / zproxy
- 数据结构与工具：zhashx / zlistx / ztrie / zuuid / zclock / zarmour / zchunk / zdigest / zrex / zsys / ziflist / zfile / zdir
- 证书：zcert / zcertstore，命令行 zmakecert

## OHOS 适配要点

- CMake 构建：上游 cmake_minimum_required(2.8.12) 与 CMake 4.x 不兼容，需提升至 3.5...3.27（见 4.2.1 补丁）
- zproject 生成的 Findlibzmq.cmake 走 MODULE 模式（pkg-config + 裸 find_path/find_library），
  Conan 只把 generators 目录放入 CMAKE_PREFIX_PATH，配方需经 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH 注入 zeromq 包路径
- 产物 libczmq.so 与 bin/zmakecert 需 OHOS ELF 自签名（llvm-objcopy + binary-sign-tool）
- 可选依赖 uuid/systemd/lz4/libcurl/nss/libmicrohttpd 在 generate() 中显式关闭，避免随探测环境漂移
- ENABLE_DRAFTS Release 默认 OFF；draft 类（zproc/zargs/ztrie/zhttp_* 等）不编译

## 依赖关系

- 必选：zeromq (libzmq) 4.3.5
- 可选（本配方全部关闭）：uuid / systemd / lz4 / libcurl / nss / libmicrohttpd
- 下游消费者：zyre 2.0.1 经 find_package(czmq REQUIRED) + Findczmq.cmake 消费
  （pkg-config 名固定为 libczmq，CMake config 包名 czmq，导出目标 czmq / czmq-static）

## 参考资料

- https://github.com/zeromq/czmq
- https://zeromq.org
