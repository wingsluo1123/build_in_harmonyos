# libu2f-host

Yubico Universal 2nd Factor (U2F) host-side C library (`libu2f-host`) and the
`u2f-host` command line utility, used to talk to U2F/FIDO hardware security
keys.

## 功能特性

- U2F 主机侧注册 / 认证 API（`u2fh_register*` / `u2fh_authenticate*`）
- 设备枚举与 U2FHID 报文收发（`u2fh_devs_*` / `u2fh_sendrecv`）
- 版本 / 错误码辅助 API（`u2fh_check_version` / `u2fh_strerror*`）
- 命令行工具 `u2f-host`

## OHOS 适配

- 使用 GNU Autotools 构建（官方发布 tarball 已自带 `configure`）
- `config.guess`/`config.sub`(2019) 不识别 HarmonyOS → 显式传入
  `--build/--host=aarch64-unknown-linux-gnu`
- 依赖 `json-c` 与 `hidapi`（Conan 制品仓提供）；上游 `configure.ac` 通过
  pkg-config 探测 `json-c`/`json` 与 `hidapi`/`hidapi-hidraw`，而 Conan 包提供
  `json-c.pc` 与 `hidapi-libusb.pc`，因此通过注入 `LIBJSON_*` / `HIDAPI_*`
  覆盖变量满足 `PKG_CHECK_MODULES`，无需改动上游源码
- 头文件布局差异：`hidapi.h` 位于 `include/hidapi/`、`json.h` 位于
  `include/json-c/`，而源码使用 `<hidapi.h>` / `<json.h>`，故补充相应 include 路径
- OHOS 无 `help2man`/`gengetopt`：tarball 已自带 `src/u2f-host.1` 与
  `src/cmdline.{c,h}`，刷新其时间戳跳过对应再生规则
- musl libc 缺少依赖共享库引用的少量符号 → `-Wl,--allow-shlib-undefined`

## 参考

- 主页: https://github.com/Yubico/libu2f-host
- 许可: LGPL-2.1-or-later
