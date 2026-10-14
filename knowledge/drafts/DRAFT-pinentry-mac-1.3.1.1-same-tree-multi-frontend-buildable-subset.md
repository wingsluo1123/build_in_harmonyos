# 平台专属前端包名不等于整包不可适配——同源多前端 tarball 的可构建子集判定

- **草稿 ID**：`DRAFT-pinentry-mac-1.3.1.1-same-tree-multi-frontend-buildable-subset`
- **沉淀自**：`pinentry-mac` 1.3.1.1 适配任务（平台 task id `13904`）
- **配套 kv**：`DRAFT-pinentry-mac-1.3.1.1-same-tree-multi-frontend-buildable-subset.kv`

## 一句话结论

平台任务名指向某个**平台专属前端**（`*-mac` / `*-win32` / `*-w32` / `*-os2`）时，
**不能**因为「那个前端的 host 闸门在目标平台为假」就判整包不可适配 ——
上游常用**一个源码树交付多个前端**，被排除的只是其中一个子目录。必须先把同树全部前端
遍历一遍，确认是否存在目标平台可用的可构建子集。

## 判据：可构建子集四步勘察

### 1. 列出顶层前端目录 + 语言构成

```bash
for d in */; do
  printf '%-12s .c=%s .m=%s\n' "$d" \
    "$(find $d -maxdepth 1 -name '*.c' | wc -l)" \
    "$(find $d -maxdepth 1 -name '*.m' | wc -l)"
done
```

pinentry v1.3.1.1 实测输出（节选）：

```
curses/      .c=1  .m=0     <-- 纯 C，可移植
tty/         .c=1  .m=0     <-- 纯 C，可移植
gnome3/      .c=1  .m=0
gtk+-2/      .c=1  .m=0
efl/ emacs/  .c=1  .m=0
w32/         .c=1  .m=0     <-- Windows 专属 API
macosx/      .c=0  .m=7     <-- 纯 Objective-C，Apple 专属
```

**只要存在含 `.c` 的前端，整包就有可适配的可能。**

### 2. 读 `SUBDIRS` 汇总行（关键，别只看专属前端自己的条件）

```
# Makefile.am:120
SUBDIRS = m4 secmem pinentry ${pinentry_curses} ${pinentry_tty} ...
```

`${pinentry_curses}` / `${pinentry_tty}` 是**变量拼接**：只要对应 `AM_CONDITIONAL`
在目标平台置位，`SUBDIRS` 就会包含它们。**`macosx/` 被排除并不影响整包出制品。**

### 3. 用 `--enable/--disable` 精选子集直接验证

```bash
./configure --host=aarch64-unknown-linux-ohos \
  --enable-pinentry-curses --enable-pinentry-tty \
  --disable-pinentry-qt --disable-pinentry-qt4 --disable-pinentry-qt5 \
  --disable-pinentry-tqt --disable-pinentry-gtk2 --disable-pinentry-gnome3 \
  --disable-pinentry-fltk --disable-pinentry-efl --disable-pinentry-w32 \
  --disable-inside-emacs
```

当且仅当 `CONFIGURE_RC=0`、`Default Pinentry` 指向该前端、对应 `Makefile` 生成，子集成立。
实测：

```
CONFIGURE_RC=0
        Mac OS X Pinentry : no          <-- 被自动排除，符合预期
        Default Pinentry .: pinentry-curses
build/curses/pinentry-curses  ELF 64-bit LSB pie executable, ARM aarch64  (490760 B)
build/tty/pinentry-tty        ELF 64-bit LSB pie executable, ARM aarch64  ( 86384 B)
```

### 4. 只有真的没有可用前端时才判不可适配

当且仅当**所有**前端目录都是平台专属实现（全 `.m`、或全 Windows API），
或 `SUBDIRS` 里不存在任何目标平台可置位的前端变量时，才判 `env_unsupported`。

## 反例（本条目的来源：一次真实误判）

先前仅凭两条证据就判 `pinentry-mac` 「结构性不可适配」：

- `configure.ac:127` `*-apple-darwin*)` → `have_macosx_system=yes`
- `macosx/Makefile.am:12` `-framework Cocoa -framework Security`

并且确实观察到 `macosx/Makefile` 始终不生成、`configure` 报 `No pinentry enabled`。

**但这个结论是错的。** 把 `macosx` 交给 autotools 自动排除后，`curses/` 与 `tty/`
两个纯 C 前端用 OHOS 工具链**真实产出了 ELF64 aarch64 制品**。

误判根源：把「包名含 `-mac`」等同于「该包制品只能由 `macosx/` 产出」。
实际上上游是**同一份 tarball、同一套构建系统**，任务名并未在源码层面独占 `macosx/`。

> 教训：**「某个前端不可移植」≠「这个包不可适配」。**
> 判不可适配前必须遍历同树全部前端 —— 这是最省时间也最容易漏的一步。

## 易踩的坑

| # | 坑 | 现象 | 正解 |
|---|---|---|---|
| ① | `autoreconf -fi` 会**重新生成** `build-aux/config.sub` | 明明打了 ohos 补丁，`configure` 仍报 ``OS `ohos' not recognized`` | 先 `autoreconf`，**再**打 config.sub 补丁；或把补丁交给配方 `patches/` 统一应用 |
| ② | 只提供 `.pc` 不够 | `checking for gpgrt-config... no` → `You need libgpg-error` | gpg-error/libassuan 用**脚本**探测：把依赖包 `bin/` 前置到 `PATH`，并导出 `GPGRT_CONFIG` / `LIBASSUAN_CONFIG` |
| ③ | 依赖 include 未传递 | `fatal error: 'assuan.h' file not found`，补上后又 `'gpg-error.h' file not found`（链式） | 显式加 `-I<dep>/include`（本项目 CFLAGS 未带依赖 include，光靠 pkg-config 不够） |
| ④ | `doc/` texinfo 步骤失败 | `make: *** [doc/pinentry.info] Error 1`（`undefined flag: UPDATED`） | 与产物无关：只 make 需要的子目录，或 `MAKEINFO=true` |

## 适用场景与收益

**适用**：包名指向 GUI/平台专属前端的第三方库任务；上游用单树多前端（autotools
`AM_CONDITIONAL` / CMake option）交付的项目。

**收益**：
- 避免把**本可交付**的适配任务误判为不可适配，白烧数小时并产出一份错误的报告；
- 给出可直接复用的四步勘察命令，10 分钟内完成「可适配 / 不可适配」定性；
- 同时沉淀了 autotools + OHOS 交叉编译的三个高频踩坑点（见上表）。

## 最小复现

```bash
tar xzf pinentry-1.3.1.1.tar.gz && cd pinentry-1.3.1.1
autoreconf -fi
# 之后再给 build-aux/config.sub 打 ohos 补丁（OS 白名单 + linux-ohos* 配对）
for d in */; do printf '%-12s .c=%s .m=%s\n' "$d" \
  "$(find $d -maxdepth 1 -name '*.c'|wc -l)" "$(find $d -maxdepth 1 -name '*.m'|wc -l)"; done
grep -n 'SUBDIRS' Makefile.am
./configure --host=aarch64-unknown-linux-ohos --enable-pinentry-curses --enable-pinentry-tty \
  --disable-pinentry-qt --disable-pinentry-qt4 --disable-pinentry-qt5 --disable-pinentry-tqt \
  --disable-pinentry-gtk2 --disable-pinentry-gnome3 --disable-pinentry-fltk \
  --disable-pinentry-efl --disable-pinentry-w32 --disable-inside-emacs
make -C curses && file curses/pinentry-curses    # -> ELF 64-bit ... ARM aarch64
```

## 关联

- 相似条目：E240、E532
- 上游：https://github.com/GPGTools/pinentry （tag `v1.3.1.1`，
  sha256 `ba929dd1c57b102fbfca12bc2d784be441498e7c82ee97a1231cbe03dcda7ae9`，767631 字节）
- 相关系统知识：`config.sub` 的 OHOS 支持（OS 白名单 + `linux-ohos*` 内核-OS 配对）
