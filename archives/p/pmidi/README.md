# pmidi

ALSA 命令行 MIDI 文件播放器（command line MIDI player for ALSA）。通过 ALSA sequencer
播放 MIDI 文件；因为可以在命令行指定目标 client/port，也常用于测试 ALSA 或需要接收
sequencer 事件的客户端。

- 上游：Steve Ratcliffe，<https://www.parabola.me.uk/alsa/pmidi.html>
- 发布点：SourceForge pmidi 项目
- 依赖：alsa-lib（OHOS 制品仓 `alsa-lib`）

## Versions

| Version | Status | Date | 说明 |
|---------|--------|------|------|
| 1.7.1 | built | 2026-10-13 | autotools；3 补丁（config.guess / config.sub / configure-umask）；产物 `bin/pmidi` + `share/man/man1/pmidi.1` |

## OHOS 适配要点

- `config.guess` 补 HarmonyOS 分支（`aarch64-unknown-linux-ohos`，需 echo+exit）
- `config.sub` 接受 `linux-ohos` 三元组（maybe_os 列表 + OS 白名单）
- `configure` 的 `config.status` 临时目录 umask `077` → `022`（HMDFS 不可写）
- 构建环境需把依赖 lib 目录加入 `LD_LIBRARY_PATH`（configure 试探程序与运行期加载 `libasound.so`）
- 运行期限制：OHOS 内核无 ALSA sequencer 设备，播放与 `-l` 端口枚举不可用；`pmidi -v` 正常
