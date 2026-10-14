# sng 1.1.1 适配笔记

## 编译环境
- 构建系统: makefile（手写 GNU Makefile，无 configure）
- 编译日期: 2026-10-07
- 编译器: clang（OHOS NDK，`aarch64-linux-ohos`）
- 状态: built
- 提交身份: zyj070505

## W0 / W0b / 语言预检
- W0 依赖（`conan download <pkg> -r=ohpcd --only-recipe`）：`libpng/1.6.58.3` ✅（其 requires 为 `zlib/1.3.2`，随依赖图解析）、
  `rgb/1.1.1` ✅（提供 `share/X11/rgb.txt`，其依赖 `xorgproto/2025.1` 已发布）。无缺失依赖，未捎带适配任何依赖。
- W0b：仓库无 sng 历史归档；`rgb`、`pngmeta` 的 notes 作为同类先例阅读（rgb.txt 位置、libpng 消费、toybox `diff -c`）。
- 语言预检：`detect_language` = `c`（build_system=make，源文件 3 个 c:3，占比 100%），默认口径放行，无需 `--lang`。

## 编译步骤
1. `init-build sng 1.1.1 --url=https://deb.debian.org/debian/pool/main/s/sng/sng_1.1.1.orig.tar.xz`，解包后对 `.work` 全量 `cp --remove-destination` 断开与 `.orig` 的硬链接（E543）。
2. 配方（`conanfile.py`）在源码目录原地构建，只构建 `sng` 目标：
   `make sng VERSION=1.1.1 RGBTXT="<package_folder>/share/X11/rgb.txt" LDFLAGS=<Conan 生成的 LDFLAGS>`。
   CC / CFLAGS / CPPFLAGS / LIBS（`-lpng16 -lm`、`-I`）由 `AutotoolsToolchain` + `AutotoolsDeps` 环境传入。
3. `build()` 内：先把 `rgb` 依赖的 `rgb.txt` 复制到 `<package_folder>/share/X11/`（RGBTXT 指向这里；上游回归先于 `package()` 运行）→ make → 对 `sng` 自签 → 运行上游回归。
4. `package()`：`bin/sng`、`share/man/man1/sng.1`（上游预渲染）、`share/X11/rgb.txt`、`licenses/COPYING`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 `make` = `all: sng man html`，man/html 需要 asciidoctor | 构建机无 asciidoctor；`sng.1` 已随 tarball 预渲染 | 只 `make sng`，`package()` 直接复制 `sng.1` |
| 2 | 首次尝试 `make -e` 后 `main.c: use of undeclared identifier 'RGBTXT'` / `expected ')'` | `-e` 让环境变量压过 Makefile 内全部赋值，包括 `CPPFLAGS += -DVERSION=... -DRGBTXT=...` 的追加，宏整条丢失 | 去掉 `-e`；Makefile 写死的 `LDFLAGS=-lpng` 会丢 `-L`，所以只把 Conan 生成的 LDFLAGS 放到 make 命令行，其余走环境 |
| 3 | `sng` 运行时需要 X11 颜色表，缺失时 `fatal("RGB database %s is missing.")` | `RGBTXT` 默认 `/usr/share/X11/rgb.txt`，OHOS 没有 | 依赖已发布 `rgb/1.1.1`，把其 `rgb.txt` 复制进本包，`RGBTXT` 烤成包内路径 |
| 4 | `sng_regress` 硬编码 `/tmp`、`diff -c` | OHOS `/tmp` 只读（E002），toybox `diff` 无 `-c` | `patches/0001`：`${TMPDIR:-/tmp}` 与 `diff -u`，只改测试脚本，不影响产物 |
| 5 | `sng_regress` 失败时退出码仍为 0 | 脚本只 `echo` 失败行，无汇总退出码（实测 `bad.png` 4 行 failed，exit=0） | 配方捕获 stdout 断言为空；libpng 的 warning 在 stderr，不并入判据（知识草稿 E700-draft-C8C9） |
| 6 | 无法在 x86 runner 上执行 aarch64 产物 | 缺 `/lib/ld-musl-aarch64.so.1`（E544 形态） | 配方里探针运行失败且 build 机非原生架构时如实 WARN + skip；本地用同源 `.c` 静态重链做 qemu 实跑（见下） |

## 源码修改
- `patches/0001-sng_regress.patch`：仅 `sng_regress`（上游回归脚本，不安装）。
  1. `tmp=${TMPDIR:-/tmp}`，所有 `/tmp/...` 改 `"$tmp"/...`；
  2. `diff -c` → `diff -u`（POSIX，toybox 可用）。
  不含任何平台宏。`main.c` / `sngc.c` / `sngd.c` 零修改。

## 依赖版本
- libpng 1.6.58.3（→ zlib 1.3.2）、rgb 1.1.1（→ xorgproto 2025.1，仅头文件）。

## 上游测试清点（R51）
- 上游测试入口：`make check` = `shellcheck sng_regress` + `./sng_regress test.sng pngsuite/[a-wyz]*.png`。
- 清点：无 `tests/` 目录，无 ctest/pytest 注册；测试体只有 1 个脚本 `sng_regress`（N = 1）。
  `pngsuite/`（Willem van Schaik 的 PNG 测试集）**不在上游发布包内**，`shellcheck` 构建机没有。
- 实际运行（N′ = 1）：`bash ./sng_regress test.sng snglogo.png`（发布包自带的 SNG 与 PNG 各 1 个，覆盖
  SNG→PNG→SNG 规范化往返与 PNG→SNG→PNG 往返）。配方 `build()` 在可执行目标二进制的机器上实跑，输出必须为空。
  x86 runner 上无法执行 aarch64 产物，配方打 WARN 并跳过——**不写成通过**，由 aarch64 原生 CI 实跑。
- 本地 qemu 实跑（同源 `.c` 用 NDK clang 静态重链，**不等于交付产物已实跑**）：`sng_regress test.sng snglogo.png`
  stdout 0 字节、exit=0；反例 `bad.png` 打印 4 行 failed（证明判据会红）。

## 鸿蒙特有测试（rule12）：1 条完整消费者流程
`test_package/`：`conanfile.py` + `check_png.c` + `sample.sng`。
- 被测包 `sng` 参与构建：`test_package` 通过 Conan 同时消费 `sng/1.1.1` 与 `libpng/1.6.58.3`；
- `build()` 用 Conan 配置的 OHOS C 编译器编译链接 `check_png.c`（libpng 解码程序）并自签；
- `test()`：`sng < sample.sng > out1.png`（调色板含 X11 颜色名 `red` / `dark slate gray` / `gold`，经包内 `share/X11/rgb.txt` 解析）→
  `check_png out1.png` 用 libpng 校验尺寸 4x2 / 位深 8 / 调色板 RGB / 像素索引 / tEXt →
  `sng < out1.png` 反编译并校验文本 → 重新编译 → `check_png out2.png` 再校验 → 垃圾输入被拒绝（退出码非 0）。
- 覆盖本次适配改动点：`RGBTXT` 烤入路径 + 包内 `rgb.txt`、LDFLAGS 传递（链接 libpng）、OHOS 自签。
- 执行证据：x86 runner 上 `conan create` 因无法执行 aarch64 动态产物，`test()` 打印 `[SKIP] runtime checks`（消费者程序已交叉编译链接）。
  **本地以 qemu-aarch64 实跑同源静态重链副本**：全部步骤 exit=0（记录见 `reports/test-report.md`）。
  **交付产物本身的运行时检查由 aarch64 原生 CI 执行**——用例在 `conan create` 必跑路径上，CI 出结果后需到日志确认未被 skip。

## 源码 URL
- 任务书给的是 Debian `sng_1.1.1.orig.tar.xz`；PF7（R39）把 `deb.debian.org` 判为下游重打包源，故 `conandata.yml` 改用 sng 官方 SourceForge 项目发布文件
  `https://downloads.sourceforge.net/project/sng/sng-1.1.1.tar.xz`。
  三个来源（Debian orig、SourceForge、`http://www.catb.org/~esr/sng/sng-1.1.1.tar.xz`）下载后字节一致，sha256 均为
  `c9bdfb80f5a17db1aab9337baed64a8ebea5c0ddf82915c6887b8cfb87ece61e`（55928 字节）。
- 其它来源不可用：`gitlab.com/esr/sng` 对非浏览器客户端 403；`catb.org` 只有 http 且 https 证书校验失败；Gentoo / MacPorts / OpenBSD 无此文件。

## 注意事项
- 版本号 `1.1.1` 为首次适配，无后缀。
- `sng` 为命令行工具 → 软件级目录有 `commands.json`。
- 手写 Makefile 里的 `.PATH: $(.PARSEDIR)` 是 BSD make 语法，GNU make 4.4 忽略它，不影响构建。

## 知识沉淀
- E700-draft-C8C9: 上游回归脚本无输出即通过、退出码恒为 0；配方须捕获 stdout 断言为空（`knowledge/drafts/E700-draft-C8C9.kv`）

---

**编译结束**: 2026-10-07 22:54
**最终状态**: built
