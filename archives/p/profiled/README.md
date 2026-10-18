# profiled

Sailfish OS / Nemo Mobile 的 **profile settings 守护进程**（不是 CPU profiler）。
它从已安装的 profile 数据包读取默认设置，通过 D-Bus 广播 profile 变更，
并提供客户端库 `libprofile` 与命令行工具 `profileclient`。

- 上游：<https://github.com/sailfishos/profiled>
- 许可证：BSD-2-Clause
- 构建系统：手写 Makefile（`make`），依赖 pkg-config 取 `dbus-1` + `glib-2.0`

## Version

| Version | Status | Build date | Patches |
| --- | --- | --- | --- |
| 1.0.13 | built | 2026-10-17 | 1 |

## 产物

| 路径 | 内容 |
| --- | --- |
| `bin/profiled` | 守护进程，注册 D-Bus 名 `com.nokia.profiled` |
| `bin/profileclient` | 查询/切换 profile 的命令行工具 |
| `bin/profile-tracker` | profile 变更跟踪调试工具 |
| `lib/libprofile.so.0`、`lib/libprofile.so`、`lib/libprofile.a` | 客户端库 |
| `include/profiled/{libprofile.h,profileval.h}` | 公开头文件（`libprofile.h` 暴露 `<dbus/dbus.h>`，已开 `transitive_headers`） |
| `lib/pkgconfig/profile.pc` | pkg-config 元数据（Version=1.0.13） |
| `share/dbus-1/services/com.nokia.profiled.service` | 会话总线激活文件 |

## Build Notes

- 源码：`https://github.com/sailfishos/profiled/archive/refs/tags/1.0.13.tar.gz`
- `dbus-gmain/` 是 git submodule，归档包不含内容：配方按上游记录的
  commit `d42176ae` 取 `sailfishos-mirror/dbus-glib` 的 `dbus-gmain.{c,h}` 补齐后再编译。
- `VERS` 取自 `debian/changelog`（停在 1.0.12），配方用 `make VERS=1.0.13` 覆盖。
- `dbus` 依赖只提供静态库且没有 `dbus-1.pc`，配方在 `generate()` 里补一份。
- OHOS 无 `install(1)`：不调用上游 `install-*` 目标，`package()` 直接落盘。

## 运行期

- 需要可用的 D-Bus 会话总线（`DBUS_SESSION_BUS_ADDRESS`）。OHOS 沙箱下建议
  `dbus-daemon --config-file=<tcp session 配置>`（`listen=tcp:host=127.0.0.1,port=0`）。
- 用户态状态目录 `$HOME/.profiled`（`current`、`custom.ini`）由守护进程自建。
- `/etc/profiled/*.ini` 缺失时使用内建 profile：`general`、`meeting`、`outdoors`、`silent`。

## 上游测试

上游**没有自动化测试套件**（无 `tests/`、Makefile 无 `test`/`check` 目标、无 CI 配置）。
可运行的真实入口是 `examples/` 下 3 个示例程序，本适配已全部构建并实际运行，
测试明细见 `1.0.13/notes.md`（完整 W3 日志与 test-report 保留在本地 `reports/`，不入仓）。
