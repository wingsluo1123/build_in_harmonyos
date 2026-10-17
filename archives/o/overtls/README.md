# overtls

## 简介

overtls 是一个极简的 **WebSocket over TLS 隧道代理**：客户端在本机开一个 SOCKS5
入口，把应用流量经 `ws://` / `wss://` 隧道送到远端服务端，由服务端建立到目标地址
的 TCP 连接并转发，用于穿透与代理场景。上游为 Rust 单 crate 项目
（`ShadowsocksR-Live/overtls`）。

## 功能概述

- **客户端 SOCKS5 代理**：本地 `listen_host:listen_port` 提供 SOCKS5 入口，支持
  可选的 `listen_user` / `listen_password` 认证与连接池（`pool_max_size`）。
- **服务端隧道接入**：按 `tunnel_path` 匹配 WebSocket 升级请求，从客户端下发的
  `TargetAddress`（`weirduri` 头）取目标地址并建立出站 TCP；非隧道路径按
  `forward_addr` 直接转发。
- **两种传输模式**：`disable_tls=false` 时走 `wss://`（rustls，服务端需
  `certfile`/`keyfile`）；`disable_tls=true` 时走明文 `ws://`（本包 test_package
  用的就是这条路径）。
- **UDP 中继 / DNS 缓存 / 流量统计与面板同步**（`udprelay`、`cache_dns`、
  `panel_sync`、`traffic_audit`）。
- **SSR 风格节点 URL**：`ssr://` URL 与 JSON 配置可互转（`-g` 生成 URL）。
- **多平台交付**：上游同时产出 CLI 二进制与 `staticlib`/`cdylib` C API 库
  （`cbindgen` 生成 `overtls.h`）。

## OHOS 适配

### 适配要点

- **构建系统**：Cargo（Rust），`cargo build --release` 直接编译，无 configure 步骤。
- **工具链**：仓库内 conan 包 `rust-toolchain/1.97.1`（`tool_requires`），宿主与
  目标均为 `aarch64-unknown-linux-ohos`。该包二进制**不带 OHOS code signature**，
  配方在构建期用 `binary-sign-tool` 自签名，并以
  `RUSTFLAGS=--sysroot=<工具包目录>` 固定 sysroot（搬离包目录会 `E0463`）。
- **不用 harmonybrew rust bottle**：`rust-1.97.1` bottle 已 404（实测）；cargo 自身
  运行期仍需 `openssl@3` / `zlib-ng-compat` / `ca-certificates` 三个 bottle（实测 200）。
- **TLS 面**：`rustls` + `ring`（纯 Rust），**不引 `openssl-sys`** → 系统 OpenSSL
  头/库不参与编译（组件裁剪标注：无需系统 TLS 库）。
  ⚠ 需一处源补丁：`reqwest` 0.13.x 的 `rustls` feature 硬编码启用 `aws-lc-rs`，
  而 `aws-lc-sys 0.45.0` 在 OHOS/aarch64 上不产出 perlasm 汇编对象 → 链接期
  200+ 个 `aws_lc_0_45_0_*` 符号未定义。配方以
  `patches/0001-Cargo.toml-reqwest-rustls-no-provider.patch` 把 `reqwest` 改为
  `rustls-no-provider`（全树只剩 `ring`）；上游 `src/lib.rs` 本就安装
  `rustls::crypto::ring` 默认 provider、`src/tls.rs` 显式用 ring 密码套件，
  故无功能损失。
- **crate 源**：`.cargo/config.toml` 追加 `rsproxy.cn` sparse 镜像与
  `retry=10 / timeout=600 / low-speed-limit=1`（设备与 CI worker 无 crates.io CA bundle）。
- **链接与并行度**：`RUSTFLAGS=-C linker=/data/service/hnp/bin/clang`，
  `CARGO_BUILD_JOBS=1`。
- **临时目录**：OHOS `/tmp` 只读，`TMPDIR`/`TMP`/`TEMP` 指向构建目录下可写目录。
- **产物**：`bin/overtls-bin`（CLI，`--version` / `--help` 可用）+ `licenses/LICENSE`
  + `share/overtls/config.json`（上游默认配置样例）。
- **消费者验证**：`test_package/test_overtls.sh` 14 项断言，含**端到端数据面**
  —— 起服务端与客户端进程 → SOCKS5 握手 → overtls 隧道 → 服务端 TCP 转发 →
  回显目标字节往返一致（不 mock、不降级为存在性检查）。

### 已知问题

- 上游 tarball **不含 `Cargo.lock`**（上游 `.gitignore` 忽略），故不能用
  `--locked`；依赖解析由 rsproxy 在构建时完成，跨时间重建可能解析到不同小版本。
- 上游唯一的注册测试 `test_config` 会向 `www.gov.cn:443` 发起一次真实 TCP 连接
  （上游测试自身的外网依赖），离线环境该用例会失败。
- 本工具链无 `rustdoc`，doc-test 阶段不可执行；v0.3.12 的 `src/` 内 0 个代码块，
  不存在被跳过的真实 doctest。
- `bin/overtls-bin` 运行期静态链接，无 RPATH 需求；仅在 `--version`/`--help` 与
  本地回环代理场景下验证过，未做真实外网中转验证。

## 依赖关系

- **构建依赖**：`rust-toolchain/1.97.1`（conan `tool_requires`）；cargo 运行期
  动态库 `libssl.so` / `libcrypto.so` / `libz.so`（Harmonybrew bottle，构建期注入
  `LD_LIBRARY_PATH`）。
- **Conan 运行依赖**：无（`requirements()` 为空；Rust 侧依赖由 crates.io 经
  rsproxy 镜像解析）。
- **系统运行依赖**：无（静态链接；OHOS `/system/lib64` 的 libc 由加载器提供）。

## 参考资料

- 上游仓库：<https://github.com/ShadowsocksR-Live/overtls>
- 上游 README：<https://github.com/ShadowsocksR-Live/overtls/blob/master/readme.md>
- 本包版本归档：`archives/o/overtls/0.3.12/`
