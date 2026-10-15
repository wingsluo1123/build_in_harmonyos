# run-parts

Debian `run-parts`：依次执行指定目录中的所有可执行脚本/程序（`--list`、`--test`、`--stdin`、`--exit-on-error`、`--regex` 等）。

## 版本历史

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 5.23.2 | published | 1 |

## 软件信息

- **官方网站**: https://salsa.debian.org/debian/debianutils
- **源码**: https://salsa.debian.org/debian/debianutils/-/archive/debian/5.23.2/debianutils-debian-5.23.2.tar.gz（debianutils 源码包中的 `run-parts.c`）
- **License**: GPL-2.0-or-later
- **依赖**: 仅 libc

## OHOS 适配说明

- 源码包无预生成 `configure`，且 `Makefile.am` 强制 `SUBDIRS = po4a`；run-parts 为单文件 C 程序，配方绕过 autotools 直接编译并手工提供 `PACKAGE_VERSION` / `HAVE_GETOPT_H` / `_FILE_OFFSET_BITS`。
- 静态 PIE 链接（`-static-pie`），无共享库依赖。
- 补丁 `0001-run-parts.c.patch`：`--stdin` 先用 `$TMPDIR` 下的 `open(O_TMPFILE)`，上游不检查返回值；在 HarmonyOS CI 文件系统上该调用失败，表现为 `failed to write to temporary file`。补丁在失败时回退到 `mkstemp` 并立即 `unlink`。OHOS 上 `/tmp` 只读，使用 `--stdin` 时需设置可写 `TMPDIR`。
- 上游源码内置版本号仍为 `5.23.1`，`run-parts --version` 输出 5.23.1。
- 与 `debianutils/5.23.2`（含 run-parts、tempfile、ischroot 及脚本）同源；本包只含 run-parts。
