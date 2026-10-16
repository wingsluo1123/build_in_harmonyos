# xwpe

- **上游**：https://codeberg.org/mendezr/xwpe （面向程序员的终端编辑器/IDE，含 LSP/DAP 支持）
- **版本**：**1.6.6**（与平台清单一致）
- **形态**：C / autotools
- **许可证**：GPL-2.0-or-later
- **依赖**：`ncurses/6.6`（必需 **ncursesw**）+ `json-c/0.18`（必需；DAP 线格式）

## 归档内容

```
xwpe/
  commands.json            软件级命令声明（R38：本包产出真编译的 ELF 可执行文件）
  1.6.6/
    conandata.yml          源（Debian orig .tar.xz + sha256，本地实测值）
    conanfile.py           配方（autotools + 逐个直跑上游 18 个单测 + 两处环境处理）
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（测试体系接入 5 处 + makeinfo + /tmp 可移植性修正 + 阻塞证据）
    test_package/          消费者校验（6 项，全部离线）
```

## 构建要点

1. **可选层全关**：`--without-x`、`--without-gpm`（X/Xft/cairo/pango/libvterm 都不在该库依赖清单里）
2. **`MAKEINFO=true`**：本环境无 texinfo，`make` / `make check` / `make install` 三处都会因 info 文档
   规则中断（Error 127）→ 传该变量让文档步骤空转，不改上游 `Makefile.am`
3. **测试临时目录可移植性修正**：11 个 `tests/*.c` 里写死的 `/tmp/...` → 相对路径 `./...`
   （本沙箱 `/tmp` 只读，否则用例 abort）。**判定逻辑与用例数量一字未改**

## 上游测试

**上游自带 18 个 C 单元测试**（顶层 `Makefile.am:187` `check_PROGRAMS`）。conan 是 out-of-source 构建，
配方改为**逐个直跑**：解析构建目录 Makefile 的名单 → make → 逐个执行，并补齐 automake 会导出的
`srcdir`/`LD_LIBRARY_PATH`/`TMPDIR` 等运行条件。

本地实测：**通过 11 / 跳过 7 / 0 失败**。跳过是上游自身设计（`exit 77`），因为所需外部工具
（Go/Rust/Scala 工具链与对应 LSP/DAP server）在本机**装不上**——`dl.google.com` 与 GitHub releases
不可达（HTTP=000）、`static.rust-lang.org` 仅 21 KB/s（rustup-init 18.9MB / 工具链 1.5–2GB）、
Maven 仅 ~2 KB/s。**带证据如实记录，不冒充通过**。

## 消费者校验

`test_package/check_xwpe.py` **6 项，全部离线**：产物齐备（`bin/we` + `bin/wpe`）/ ELF 头自检
（ELF64、machine=0xB7）/ 动态依赖自检（**json-c 动态**：NEEDED 必须含 `libjson-c.so.*`，否则 fail；**ncurses 静态链入**：conan 包只有 `libncursesw.a`、无 `.so`，故 NEEDED 不含它）/ `we --version` 真跑尝试
（全屏程序无 tty → rc=-11，如实记录）/ 许可证随包 / 证据。
实测 `checks=6 fails=0 skips=0` / `RESULT: PASS`。
