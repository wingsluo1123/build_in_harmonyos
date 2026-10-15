# run-parts 5.23.2 适配笔记

## 编译环境
- 构建系统: custom（源码为 autotools 声明，但 tarball 无 configure；配方直接编译单文件 C）
- 编译日期: 2026-10-07
- 编译器: OHOS clang 15.0.4（aarch64-unknown-linux-ohos）
- 状态: published（conan-verify G1–G4 通过）

## 语言预检（R47）
- `detect_language` 判定 `c`：源文件 3 个（c:3），主体占比 100%，构建系统 autotools，与默认任务语言兼容，`lang-preflight` 放行。
- 依赖: libc-only（W0 无需检查制品仓）。

## 历史核验（W0b）
- 仓库已有 `archives/d/debianutils/5.23.2`（同一源码包，含 run-parts/tempfile/ischroot 与脚本，补丁禁用 po4a）。
- 本包只打包 `run-parts`，不复用其补丁：直接编译 `run-parts.c`，不经过 Makefile.am，因此不需要 po4a 补丁。
- 历史配方硬编码 `PACKAGE_VERSION=5.23.1`：确认为上游 `acinclude.m4` 的内置值（5.23.2 tarball 内仍为 5.23.1），沿用该值。
- 历史命令（autoreconf、设备原生编译）在 CI 不可逐字执行，故不采用；本配方只依赖 clang。

## 编译步骤
1. `init-build run-parts 5.23.2 --url=https://salsa.debian.org/debian/debianutils/-/archive/debian/5.23.2/debianutils-debian-5.23.2.tar.gz`，sha256 `d38965ef7b095247c729cf798593dcb12541d17e8044c1dd9d0f772fbbb9d31c`；解包后用 `cp --remove-destination` 断开 `.work`/`.orig` 硬链接。
   最初用 `deb.debian.org` 的 `debianutils_5.23.2.tar.xz` 做手工验证；因 PF7 将 Debian 下游池视为重打包源，配方改用 Debian 官方仓库（salsa）`debian/5.23.2` tag 归档，并逐文件比对 `run-parts.c`、`debian/tests/run-parts.test`、`acinclude.m4` 的 sha256，与 tarball 完全一致。
2. 手工交叉编译验证：
   `aarch64-unknown-linux-ohos-clang -O2 -fPIE -DPACKAGE_VERSION='"5.23.1"' -DHAVE_GETOPT_H -DHAVE_PATHS_H -D_FILE_OFFSET_BITS=64 run-parts.c -static-pie`，无报错（仅 `ignored` 变量 unused 警告）。
3. `conan-init` 生成骨架后手写 `conanfile.py` / `conandata.yml` / `test_package/`；`conan-verify` 首次 G2 失败，见下表。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tarball 无 `configure`，`Makefile.am` 强制 `SUBDIRS = po4a`，缺 `po4a-translate` 时 `po4a/de/Makefile.am:9` 的 `TRANSLATE` 为 `exit 1` | Debian native 源码包只发布 configure.ac/Makefile.am | 不跑 autotools，直接编译 `run-parts.c` 并手工提供 `PACKAGE_VERSION`/`HAVE_GETOPT_H`/`HAVE_PATHS_H`/`_FILE_OFFSET_BITS` |
| 2 | `conan-verify` G1 报缺 `export_sources()` 与补丁应用调用 | G1 门禁对无补丁配方同样要求 | 补 `export_conandata_patches` / `apply_conandata_patches`（无补丁时为空操作） |
| 3 | G2 `ConanException: 'tools.build:compiler_executables:c' does not exist in configuration list` | 该 conf 是 dict，不存在 `:c` 子键（`templates/conanfile-makefile.py.tmpl` 的写法无效） | `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")` |
| 4 | CI（真机 buildbot worker）上 `test_package` 的 `--stdin` 用例失败：`run-parts: failed to write to temporary file` / `failed to copy content of stdin` | 上游 `open_tmpfile_rw()` 的 `open(O_TMPFILE)` 在该文件系统上失败，`copy_stdin()` 不检查 fd，后续 `write(-1)` 报错（本机 x86 的 O_TMPFILE 可用，首轮本地未暴露）。用 `O_TMPFILE|O_RDONLY` 强制 open 返回 EINVAL 可在本机复现同样报错 | 补丁：open 失败时回退 `mkstemp`+`unlink`；强制失败变体下未打补丁 rc=1、打补丁 rc=0 且输出与 test_package 期望一致 |
| 5 | `run-parts --version` 打印 5.23.1 | 上游 `acinclude.m4` 内置版本未随 5.23.2 更新 | 与上游保持一致，test_package 不断言 `--version` 的版本号 |

## 源码修改
`patches/0001-run-parts.c.patch`（`run-parts.c` `open_tmpfile_rw()`）：`open(TMPDIR, O_TMPFILE|O_RDWR|O_EXCL)` 返回 -1 时回退到 `mkstemp("$TMPDIR/run-parts.stdin.XXXXXX")` 并立即 `unlink`，保持无名临时文件语义。补丁不含平台宏，运行时按返回值判断。

## 依赖版本
- 构建: OHOS clang 15.0.4；运行: 无（static-pie，仅 libc 静态）。

## 上游测试清点（R51）
- 上游无 `make check` / ctest。测试为 `debian/tests/control` 声明的 2 个 autopkgtest 脚本：
  - `debian/tests/run-parts.test`（针对 run-parts，bash，83 行）
  - `debian/tests/smoke`（针对 which/ischroot/tempfile/savelog，与本包无关）
- N=2，适用于本包 N′=1，实跑 1/1 通过（100%）；加入 `--stdin` 回退补丁后的产物重跑同一脚本，退出码仍为 0。`smoke` 不适用：本包不含这些工具。
- 实跑方式：对 conan 打包产物（`.conan2-ohos/p/b/.../bin/run-parts`，aarch64 static-pie）在 x86 runner 经 qemu-user binfmt 执行
  `bash debian/tests/run-parts.test`，退出码 0，3 条 `Success!` 断言行出现；脚本内 `--version/--help/--list/--test/-v/--report/--reverse/--exit-on-error` 均执行。
- 未修改上游测试用例。

## 鸿蒙特有测试（rule12）
- `test_package/` 为完整消费者流程：Conan 通过 CMakeToolchain 用 OHOS 工具链把 `consumer_hook.c` 编成 aarch64 静态 ELF，作为 hook 放进目录，
  由打包产物 `run-parts` 执行并逐字节比对输出：`--list`、`--test`、`-a`、`--stdin`（`$TMPDIR` 下 `O_TMPFILE`，OHOS `/tmp` 只读）、`-u`（umask）、`--exit-on-error`（退出码 3 透传，第二个 hook 不执行）。
- 断言数 9，本地 `conan create` 内实跑通过（x86 runner 经 qemu binfmt 执行静态 aarch64 产物）。本地实跑不等于在真机 HarmonyOS 上实跑；真机行为由 CI 的同一用例验证。
- 本包鸿蒙特有测试 N=1（`test_package`，含 9 条断言）。

## 验证结果
- `conan-verify`: G1/G2/G3/G4 通过；L2/L4/L5 因无 cache 路径被工具跳过（非本包失败）。
- 产物: `ELF 64-bit LSB pie executable, ARM aarch64, static-pie linked, stripped`，含 `GNU_RELRO`，`GNU_STACK` 为 RW（无可执行栈）。

## 注意事项
- OHOS `/tmp` 只读：`--stdin` 需要可写 `TMPDIR`；补丁后 `O_TMPFILE` 不可用时回退 `mkstemp`（同一 `TMPDIR`）。仅当 `O_TMPFILE` 宏未定义时才回退硬编码 `/tmp`（OHOS musl 已定义该宏）。
- 与 `debianutils/5.23.2` 同包含 `run-parts` 命令，注意不要同时安装到同一前缀。
---

**编译结束**: 2026-10-14 02:37
**最终状态**: published
