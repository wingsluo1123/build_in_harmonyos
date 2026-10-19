# rtkit

`rtkit`（RealtimeKit）是 D-Bus 系统服务，按客户端请求把用户进程/线程的调度策略
切到 `SCHED_RR`（或提升 nice 级别），是 PipeWire / JACK 等低延迟音频栈的授权中间层。

## Versions

| Version | Status |
| --- | --- |
| 0.14 | built |

Homepage: https://gitlab.freedesktop.org/pipewire/rtkit/

上游原先托管在 <https://github.com/heftig/rtkit>（已归档，最后版本 0.13），
现行 canonical 仓库为 <https://gitlab.freedesktop.org/pipewire/rtkit/>。
本适配采用现行仓库的 v0.14。

## 产物

| 路径 | 说明 |
| --- | --- |
| `bin/rtkitctl` | 控制工具（reset-known / reset-all / start / exit / suspend / resume） |
| `libexec/rtkit-daemon` | 服务本体（上游约定装在 libexec） |
| `libexec/installed-tests/rtkit/rtkit-test` | 上游自带的客户端库自测程序 |
| `share/dbus-1/system-services/org.freedesktop.RealtimeKit1.service` | 总线激活文件 |
| `share/dbus-1/system.d/org.freedesktop.RealtimeKit1.conf` | 总线策略 |
| `share/dbus-1/interfaces/org.freedesktop.RealtimeKit1.xml` | 接口自省 |
| `share/polkit-1/actions/org.freedesktop.RealtimeKit1.policy` | polkit 动作 |
| `lib/sysusers.d/rtkit.conf`、`lib/systemd/system/rtkit-daemon.service` | 系统集成（OHOS 无 systemd，随包保留供参考） |
