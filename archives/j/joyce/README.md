# Joyce (Amstrad PCW 模拟器)

Joyce 是一个在类 Unix 主机上模拟 Amstrad PCW 系列（PCW8256/8512/9512 与
PCW16/Anne）的模拟器。本适配面向 HarmonyOS PC（aarch64）。

- 上游：https://www.seasip.info/Unix/Joyce/
- 许可证：GPL-2.0-or-later
- 构建系统：Autotools

## 内容

- GUI 前端：`xjoyce`、`xanne`（SDL 1.2）
- 磁盘工具（bundled LibDsk tools）：`dskconv`、`dsklabel`、`dskform`、
  `dsktrans`、`dskid`、`dskdump`、`dskscan`、`dskutil`、`md3serial`、
  `apriboot`、`lsgotek`

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.4.2 | built | Autotools 构建，接入 bundled LibDsk 上游测试 |

详见 `2.4.2/notes.md`。
