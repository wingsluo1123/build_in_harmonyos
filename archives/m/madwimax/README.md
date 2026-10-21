# madwimax

- **上游**：https://github.com/ago/madwimax （WiMAX USB 设备的用户态驱动）
- **版本**：**0.1.1**（与平台清单一致，tag `v0.1.1` 命中）
- **形态**：C / autotools
- **许可证**：GPL-2.0-or-later
- **依赖**：**只有一个外部依赖** —— `libusb/1.0.27`（+ 系统 pthread）

## 归档内容

```
madwimax/
  commands.json            软件级命令声明（R38：本包产出真编译的 ELF 可执行文件）
  0.1.1/
    conandata.yml          源（GitHub tag v0.1.1 + sha256，本地实测值）
    conanfile.py           配方（autotools + libusb + 三处适配 + 补的断言）
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（asciidoc 硬检查 / musl 头冲突 / sbin 布局）
    test_package/          消费者校验（7 项，全部离线）
```

## 构建要点（三处，详见 notes.md）

1. **`--without-man-pages`**：上游默认生成 man 页并在 configure 里**硬检查 asciidoc**（会直接挡住
   configure）→ 文档非必需时用该开关绕开
2. **`-D__MUSL__`**：`src/tap_dev.c` 先 include `<sys/socket.h>` 再 include `<linux/if.h>` →
   `linux/socket.h` 重复定义 `sockaddr_storage`；musl 侧 `sys/socket.h:376` 是 `#ifndef __MUSL__`
   包裹 → 定义 `__MUSL__` 后冲突消失（**一个 -D 的补丁，不改源码**）
3. **`package()` 显式补装 `bin/madwimax`**：上游是 `sbin_PROGRAMS`，实测 `make install` 没落到 `bin/`

## 上游测试

**上游测试数 = 0**（无 `test/`，`Makefile.am` 无 `TESTS`）→ 配方里补两条功能级断言：`madwimax --help`
（打印用法 ✓）与 `madwimax --version`（输出 `madwimax 0.1.1` ✓）。真实驱动功能需 WiMAX USB 设备 + TAP
设备，本环境不执行（如实记录）。

## 消费者校验

`test_package/check_madwimax.py` **7 项，全部离线**：产物齐备 / ELF 头自检（ELF64、machine=0xB7）/
`--help` / `--version` / 许可证随包 / 证据 / 运行边界如实记录。
实测 `checks=7 fails=0` / `RESULT: PASS`。
