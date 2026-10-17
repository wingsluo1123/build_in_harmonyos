# tup

tup 是一个基于文件依赖图的增量构建系统（build system），用 C 编写，自带
lua 脚本、sqlite3 图数据库、pcre2 与 inih 解析器，无第三方运行时依赖。

- Website: https://github.com/gittup/tup
- Source: https://github.com/gittup/tup
- License: GPL-2.0-or-later
- Build system: 上游自带 `build.sh`（既非 cmake，也非 autotools/make）
- Category: build-tool / 增量构建系统

## 功能概述

- **基于文件依赖图的增量构建**：用一个 sqlite3 图数据库记录命令与文件的读写
  关系，精确到"某条命令读了哪个文件、写了哪个文件"，从而只重建真正受影响的
  目标，而不像 make 那样只看时间戳。
- **自动发现依赖**：通过 LD_PRELOAD 注入（`tup-ldpreload.so`）或 FUSE 挂载
  拦截 libc 调用，自动捕获编译器/脚本读到的头文件等隐式输入，无需手写
  `.d` 文件或 `-M` 规则。
- **Tupfile / Tupfile.lua / Tupfile.ini**：支持声明式规则与 lua 脚本两种写法，
  并能通过 `tup.import` 复用变量。
- **全量依赖模式**（`updater.full_deps`）：可把进程级外部依赖（`/` 扫描、
  getaddrinfo、getcwd/nprocs 等）也纳入图，跨进程边界保持重建正确性。
- **守护进程与监视**：`tup server` / `tup monitor` 提供后台服务与 inotify
  文件监视，避免每次运行都做完整文件系统扫描。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/tup` | 构建系统 CLI（自包含，内嵌 lua/sqlite3/pcre2/inih） |
| `bin/tup-ldpreload.so` | LD_PRELOAD 依赖追踪注入库 |

> **两者必须同目录安装**：`src/tup/server/depfile.c` 按 `tup` 可执行文件自身
> 的路径推导注入库名（`<exe-path>-ldpreload.so`）。分开放置会让所有走
> ldpreload 后端的构建在运行时静默失败。

## OHOS 适配

本平台的适配要点（细节与补丁见版本级 `notes.md`）：

- **必须使用 ldpreload 后端**：OHOS PC 沙箱内无可用 `/dev/fuse`（且 `/dev`
  不可写），fuse/fuse2/fuse3 后端均不可用，只能走 LD_PRELOAD 注入。
  `build.sh` 原本按 `uname -s` 分派平台，而 OHOS 返回的是 `HarmonyOS`
  （不是 `Linux`），因此需要显式新增该分支。
- **musl 运行时**：OHOS 运行时是 musl + Linux ABI（clang 定义 `__linux__`），
  但 musl 把 `open64`/`fopen64`/`stat64` 定义为宏，glibc 专有的
  `__xstat*`/`*_chk` 包装器必须用 `__GLIBC__` 守卫隔离。
- **`/tmp` 只读**：鸿蒙 `/tmp` 是 erofs 只读挂载，libc 的 `tmpfile()`
  （glibc 与 musl 都将 `/tmp` 硬编码为 `P_tmpdir`）因此完全不可用。
  tup 需要用 `$TMPDIR` → 项目内 `.tup/tmp` → `/tmp` 的回退链，并把 `TMPDIR`
  像 `PATH`/`HOME` 一样白名单传递给子进程，否则 clang/gcc 等需要临时目录的
  命令会报 `unable to make temporary file: Read-only file system`。
- **toybox 用户态**：OHOS 的 `touch` 是 toybox 实现，与 GNU coreutils 语义
  不同（新建文件只 `open(O_CREAT)`，已存在文件只 `utimensat`），而上游
  shim 只按 `O_WRONLY/O_RDWR` 判定"写"、且从不包装 `utimensat`，导致所有用
  `touch` 产出输出的规则都被判为"没有写文件"。适配在 shim 侧对齐语义，
  **不修改系统用户态**，因此对 GNU 用户态仍是正确行为。

### 已知问题（平台限制，非适配缺陷）

- 无 `/dev/fuse` → fuse 后端不可选（本包已固定为 ldpreload）。
- HMDFS 不允许创建硬链接、不允许扫描 `/` 根目录 → 上游 full-deps 系列用例
  （t4062–t4067/t4171/t4205–t4215 等）与个别用例在沙箱内无法通过。
- 沙箱缺 `ccache`/`sqlite3`/`gcc` 等外部工具 → 相关用例按平台阻塞记录。
- 上游 ldpreload 后端自身有 `vardict_fd = -1 /* TODO */` 限制（t3000 系列
  变量用例）。

## 依赖关系

- **编译依赖**：无。tup 自包含内嵌 lua、sqlite3、pcre2、inih。
- **运行依赖**：仅 libc（musl）+ pthread + libm + libdl；运行时需要
  `bin/tup-ldpreload.so` 与 `bin/tup` 同目录。
- **子进程环境白名单**：tup 只把"数据库记录过的环境变量"（`PATH`/`HOME`，
  以及 Tupfile 里 `export` 过或 `@VAR@` 引用过的）传给构建命令。若某条构建
  命令自身需要可写临时目录，必须在 Tupfile 里显式 `export TMPDIR=...`，
  仅在 shell 里 `export TMPDIR` 是无效的——这是 tup 的既有设计。

## 参考资料

- 源码仓库：https://github.com/gittup/tup
- 上游手册：https://gittup.org/tup/manual.html
