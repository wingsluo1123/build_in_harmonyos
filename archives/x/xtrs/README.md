# xtrs — TRS-80 Model I/III/4/4P 模拟器（X11）

`xtrs` 是基于 Z80 的 TRS-80 模拟器。`z80.c` 是纯 C 的 Z80 指令解释器；界面为
X11 客户端。上游随包还提供三个无头工具：`mkdisk`（生成空白软盘镜像）、
`hex2cmd`（Intel-HEX → TRS-80 `.cmd`）、`cmddump`（转储 `.cmd`）。

- 上游：<http://www.tim-mann.org/xtrs>
- 许可：Clarendon Hill Software 自定义许可（保留版权即可使用/再分发）

## 用法

```sh
# 生成一张 TRS-80 Model III 软盘镜像
mkdisk -3 disk3.dsk
# Intel-HEX → CMD
hex2cmd rom.hex > rom.cmd
cmddump rom.cmd
# 运行模拟器（需要 X display）
xtrs -model 4 -rom fakerom.hex
```

## OHOS 适配要点

- OHOS clang 定义了 `__linux`/`__linux__`/`linux`，会误激活厂商 `#if __linux`
  特性块，拉入 `<sys/soundcard.h>`（OSS）、`<linux/fd.h>`（物理软驱）等 Linux
  专有头 → 补丁按**能力**探测收敛为 `#if defined(__linux) && __has_include(<…>)`
  （不以 `__OHOS__` 等平台身份宏分支）。
- X11 头来自 `libX11` 与传递依赖 `xorgproto`（`X11/keysym.h` 等），构建时
  聚合两者 include 目录。
- `xtrs` 运行需 X display（无 display 时打印 `Unable to open display`）；
  `mkdisk`/`hex2cmd`/`cmddump` 可无头运行。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/xtrs` | TRS-80 模拟器（链 `libX11`） |
| `bin/mkdisk` `bin/hex2cmd` `bin/cmddump` | 无头 CLI 工具 |
| `share/man/man1/*.1` | man 页 |

## 参考

- 上游：<http://www.tim-mann.org/xtrs>
- 许可：Clarendon Hill Software（见源码头部与 `licenses/README`）
