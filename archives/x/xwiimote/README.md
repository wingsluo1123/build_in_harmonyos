# xwiimote

Linux 下 Nintendo Wii Remote（wiimote）设备访问库与配套工具。上游同时提供：

- `libxwiimote`：设备枚举、事件读取、LED/震动/加速度计等能力的 C 库（基于 udev + uinput）
- `xwiishow`：ncurses 交互式设备信息查看工具

## 鸿蒙 PC 适配状态

| 项 | 值 |
|---|---|
| 版本 | `2`（制品 ref `xwiimote/2.0`，上游 tag `xwiimote-2`） |
| 构建系统 | autotools（上游无预生成 `configure`，配方内 `autoreconf -i` 生成） |
| 依赖 | `libudev-zero/1.0.4`、`ncurses/6.6`（静态） |
| 产物 | `lib/libxwiimote.so`、`bin/xwiishow`、`include/xwiimote.h`、`lib/pkgconfig/libxwiimote.pc` |
| 状态 | built（本地 `conan create` 通过，待 release 发布） |

## 使用

```bash
conan install --requires=xwiimote/2.0 -r=ohpcd --build=missing
# 运行时查看 wiimote 设备（需终端 + 实体设备）
xwiishow
```

## 适配要点

- udev 能力由 `libudev-zero` 提供：上游 `PKG_CHECK_MODULES([libudev])` 的模块名与 Conan
  包名（`libudev-zero`）不一致，配方 `generate()` 按依赖 `cpp_info` 生成 `libudev.pc` /
  `ncurses.pc` 注入，不改上游构建脚本。
- HarmonyOS 内核不被 `config.guess` 识别，配方在 OHOS 下显式传
  `--build=<arch>-unknown-linux-ohos`。
- `config.status` 临时目录在 HMDFS 上不可写（autoconf `umask 077` + setgid），
  生成 `configure` 后放宽为 `022`（知识条目 E129）。
- **已知限制**：OHOS 上 `xwii_monitor_new()` 实测返回 NULL（`libudev-zero/1.0.4` 的
  枚举路径未生效），设备枚举/事件监控尚未经实体 wiimote 验证，待真机复验；库本体
  的接口/校验路径（`xwii_iface_new` 等）已由消费者测试覆盖。
- `commands.json` 的键/`ref` 按目录版本 `2` 登记（PF8 口径），实际 Conan 引用为
  `xwiimote/2.0`。

详细适配记录见 [`2/notes.md`](2/notes.md)。
