# tuntox

基于 Tox 协议(Toxcore) 的 TCP 端口转发工具。在服务端把本地端口开放给远端，
客户端通过 Tox ID 安全地把本地 TCP 端口或 stdin/stdout（SSH ProxyCommand
模式）转发到服务端，无需公网 IP 即可打通两机。

## 功能概述
- 服务端：监听并转发传入的 TCP 连接请求到指定 hostname/port 组合（可用
  `-f rules` 白名单、`-i` ToxID 白名单限制）
- 客户端：`-L localport:remotehost:remoteport` 本地端口转发；
  `-W host:port` stdin/stdout（SSH ProxyCommand）转发
- 跨机安全：经由 Tox 加密 P2P 通道，支持共享密钥认证、NAT 穿透

## OHOS 适配
- tuntox 是 c-toxcore 之上的应用，c-toxcore 未在本仓库单独适配：配方在
  `source()` 内联下载 c-toxcore v0.2.19，`build()` 用 CMakeToolchain 静态
  构建其核心（`BUILD_TOXAV=OFF`，仅需 libsodium），再把 tuntox 链接其上
- toxcore 核心唯一硬依赖为 libsodium，由 `PkgConfigDeps` 生成的
  `libsodium.pc` 供其 CMake 的 pkg_search_module 检索
- tuntox Makefile 硬编码 `gcc`/`-static`/`pkg-config`：用 `make tuntox_nostatic`
  并命令行覆盖 `CC=clang CFLAGS=... DSO_LDFLAGS=...`（OHOS musl 无静态
  libc，且静态会破坏 DNS 解析）
- `tox_bootstrap.h`/`gitversion.h` 已随发布包自带，避免触发需要
  requests+jinja2 并联网 nodes.tox.chat 的 `generate_tox_bootstrap.py`

## 依赖关系
- 编译：libsodium/1.0.22（Conan 包，toxcore 核心依赖）
- vendor 内联：c-toxcore v0.2.19（配方内 source() 下载 + build() 静态构建）
- 运行：libsodium 符号

## 参考资料
- 上游仓库：https://github.com/gjedeer/tuntox
- 上游 BUILD.md：需安装 c-toxcore（libtoxav/DNS 客户端不需）
