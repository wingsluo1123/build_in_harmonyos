# Janus 1.4.1 HarmonyOS PC 移植记录

## 适配范围

- 目标：HarmonyOS PC 6.0，aarch64 / `OHOS/armv8`，Clang 15，`libc++`；Janus 本体为 C 项目。
- 包含 Janus C 服务端、REST/HTTP 与 WebSocket transport，以及 EchoTest、VideoCall、VideoRoom 插件。
- 禁用 data channel/usrsctp、SIP、消息代理、脚本插件、其他插件、事件处理器、日志插件、文档和 post-processing。
- 上游：<https://github.com/meetecho/janus-gateway>，tag `v1.4.1`，commit `85304a7a4bdb2719583ad53ae04130a8273dba6a`。
- 官方源码压缩包 SHA256：`cba1e7aac44f4458701c5e14698e791a0eee13ecacbdacc71b4245716c442c08`。

## 依赖与 ABI 选择

- `libnice/0.1.21` 使用 ohpcd 已发布的 HarmonyOS aarch64 制品。
- 该制品声明 OpenSSL 1.1.1w；`libwebsockets/4.3.5.1` 的配方默认要求 OpenSSL 3.5.6。Janus 根图统一覆盖到 OpenSSL 1.1.1w，并需按该版本从源码构建 libwebsockets，避免将已发布 libnice 二进制与不同 OpenSSL ABI 混用。
- Autotools 工具依赖：autoconf 2.72、automake 1.19、libtool 2.5.4.1、m4 1.4.19、Perl 5.42.2、pkgconf 3.0.6。

## 发现与知识

- ✅ 已将“复用的预编译依赖绑定 OpenSSL 旧 ABI、源码依赖默认选择新版本”的 Conan 图一致性经验整理为知识草稿 knowledge/drafts/E429-draft-2C1E.md，对应 kv 为 knowledge/drafts/E429-draft-2C1E.kv。查重时对照了 E412、E509；草稿说明本次在构建前发现并预防了风险，没有声称复现过错误 ABI 运行故障。
## 构建和验证

- 构建系统：Autotools（上游 tag 含 `autogen.sh`/`configure.ac`，不含生成后的 `configure`）。
- 依赖预检：在 `ohpcd` 上对直接依赖、传递依赖和 Autotools 工具依赖执行 `conan download --only-recipe`，18 个配方均返回成功。
- 原生构建：在 HarmonyOS PC 6.0 AArch64 设备上以 Clang 15、`libc++`、`os.version=6.0` 执行 `conan create . --build=janus/1.4.1 -pr:h default -pr:b default -s:h os.version=6.0 -s:b os.version=6.0 -s:h compiler.libcxx=libc++ -s:b compiler.libcxx=libc++ -r ohpcd`。包设置为 `OHOS/6.0`、`armv8`、Clang 15、Release；Janus 包 ID 为 `0bc54dde41397d1212b204986b6f4364ff012b55`，配方修订 `b5cdc3ce72b4ade7d704926eadbd2934`，最终包修订 `76e71b08276637860ac58332d9923a5f`。核心、三个插件和两个 transport 均成功编译链接。
- 上游检查：在设备上成功运行 Janus v1.4.1 的 `fuzzers/build.sh`，并将 RTCP 88 个、RTP 32 个、SDP 69 个上游 seed 文件分别作为输入传给对应 fuzzer，共 189 个实际语料输入项。原 `make check-fuzzers` 假定 in-source 构建并硬编码 `/bin/bash`；配方在 Conan build 目录中调用同一上游脚本，并为 HNP Bash 显式设置 `PWD`。跨编译阶段不能在宿主机运行 AArch64 fuzzers，因此由设备原生构建执行。
- Conan test package：完成 6 项包检查：可执行文件存在、ELF 头有效、ELF64、little-endian、AArch64 machine ID，以及 `janus --version` 成功；设备输出版本 `1.4.1`。
- HarmonyOS 专项测试：`test_package/test_janus_harmonyos.py` 在设备上启动打包后的 Janus 进程，查询启用的模块，通过 REST 完成 session create、EchoTest attach/detach 和 session destroy；另对 WebSocket 执行 RFC 6455 upgrade、mask/subprotocol 协商，并请求 Janus `info`。清单记录 18 项实际响应与能力检查；加上 Conan 包的 6 项检查，适配后共 24 项新增检查。连同保留的 189 个上游 seed 输入，适配后共 213 个实际测试项。最终强制重建的 `conan create` 退出码为 0。设备端预检与最终构建日志位于 `/storage/Users/currentUser/tmp/janus-1-4-1-port-1791889301542/`。

## 当前状态

本地 AArch64 原生构建、三项上游 fuzzer 语料回归、Conan test package 和 HarmonyOS REST/WebSocket 集成测试均已通过；包状态为 `built`，尚未发布。
