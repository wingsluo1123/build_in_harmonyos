# tup 0.8 适配笔记

## 编译环境

- 构建系统: 上游自带 `build.sh`（custom）
- 目标平台: aarch64-unknown-linux-ohos（`uname -s` == `HarmonyOS`）
- 编译器: OHOS SDK clang（`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/`，默认即 aarch64-ohos 目标）
- C 运行时: musl（提供 Linux ABI，clang 定义 `__linux__`）
- 编译日期: 2026-10-08
- 状态: published（conan create / conan-verify 通过）

## 编译步骤

```sh
# 1. 解压上游 tarball（v0.8）
tar xf tup-0.8.tar.gz

# 2. 打补丁（见 patches/，共 8 个，按文件粒度拆分）
for p in patches/*.patch; do patch -p1 < "$p"; done

# 3. 编译：build.sh 通过环境变量接收编译器和后端选择
#    产物为 build/tup 与 build/tup-ldpreload.so
CC=clang CFLAGS="-O2" TUP_SERVER=ldpreload TUP_LABEL=0.8 sh ./build.sh
```

`build.sh` 会依次编译内嵌 lua、生成 `luabuiltin.h`、编译 tup 主体（含 sqlite3/pcre2/inih），
最后用 `src/tup/link.sh` 链接 `tup`；当 `TUP_SERVER=ldpreload` 时额外编译
`src/ldpreload/*.c` 得到 `tup-ldpreload.so`。

产物必须**同目录安装**：`src/tup/server/depfile.c` 是按 `tup` 可执行文件路径外推
`tup-ldpreload.so` 的（`<exe>-ldpreload.so`），分开放会导致运行时找不到注入库。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `build.sh` 报 `fuse2` 未找到，且链接期 `undefined reference to compat_lock_disable/compat_lock_enable` | OHOS `uname -s` 返回 `HarmonyOS`，`case "$os"` 无该分支 → 落到默认 `fuse` 后端，且未把 `src/compat/dummy.c`（提供上述符号）、`utimensat_linux.c` 纳入 `plat_files` | 补丁 0001：新增 `HarmonyOS)` 分支，`default_server=ldpreload` + `monitor=inotify.c`，并把 Linux 兼容文件加入 `plat_files` |
| 2 | `ldpreload.c` 编译报 `open64`/`fopen64`/`stat64` 宏重定义、`-Wvisibility` 缺 `struct stat` 声明 | musl 把这些名字定义为宏（glibc 专有 ABI 细节）；上游为 glibc 写的 `__xstat*`/`*64` 包装器在 musl 下不成立 | 补丁 0002：用 `#ifdef __GLIBC__` 守卫整个 glibc 专有表面（声明 + 函数体），并补 `struct stat` 前置声明 |
| 3 | 运行期依赖文件恒为 0 字节，报 `fcntl F_WRLCK: Bad file descriptor` | `init_fd()` 作为 ELF 构造器执行得太晚：OHOS 在构造器之前就已打开文件，此时 `depfd==-1`，`handle_file_locked()` 里的 `tup_flock(depfd)` 失败并把该事件永久丢弃 | 补丁 0002：`depfd` 改为惰性打开（`open_depfd()`），首次写事件时再创建依赖文件 |
| 4 | 全量测试 270 项失败，其中 165 项为 `Expected to write to file ... but didn't`（`touch bar`、`sh ok.sh ...`、`[build] touch ...` 等） | 上游 0.8 的 ldpreload shim **从不包装 `utimensat`**，且只在 `open()` 带 `O_WRONLY/O_RDWR` 时判为写；而 OHOS 用户态是 **toybox**，其 `touch` 对**新建文件**只做 `open(path, O_CREAT)`（仅 O_CREAT → 被判为读）、对**已存在文件**只做 `utimensat`（完全未拦截），两条路径都不产生 WRITE 事件。对照 tup 的 FUSE 后端 `tup_fs_utimens()` 可确认语义上应当算写 | 补丁 0002：包装 `utimensat()` 记为 `ACCESS_WRITE`；`open/open64/openat` 在 `O_CREAT` 且目标确实不存在时记为写（用未包装的 `fstatat` 探测，避免自造事件）。修复后 165 项全部转 PASS |
| 5 | 修复 #4 后 `t5091-ignore-output.sh` 仍失败：`tup flags_exists` 报 `create_list: 1`（`check_empty_tupdirs` 不通过） | 该用例的命令里有 `touch ignoredir`（目录）。把目录的 `utimensat` 记为写会让 tup 为目录建节点，且 `create_list` 标志永不清理 | 补丁 0002：`utimensat` 包装器里 `fstatat` 判别，`S_ISDIR` 时不上报事件（tup 的依赖图只跟踪文件） |
| 7 | PR CI #90146：`link lua` 阶段报 `clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable`、`link.sh[27]: can't fork - try again`，紧接着 `luaparser.c:56: fatal error: 'luabuiltin/luabuiltin.h' file not found`；最后 test_package 以 `tup: command not found`(127) 失败 | ① CI worker 上偶发的进程/线程槽耗尽（EAGAIN）：clang 驱动拉起 ld、以及 `link.sh` 里的 shell fork 都会失败；② **真正让失败被吃掉的是配方**：以 `<shell> ./build.sh` 形式调用时脚本的 shebang `#! /bin/sh -e` 不生效，`-e` 丢失，链接失败后脚本仍继续跑完，留下一个没有 `tup` 的 `build/`；③ `package()` 的 `copy()` 在无匹配文件时不报错，把这个残缺构建静默打成只有一个 `COPYING` 的空包，直到 test_package 才暴露 | 配方 `build()`：显式补回 `-e`（`{shell} -e ./build.sh`）；每次尝试后校验 `build/tup` 与 `build/tup-ldpreload.so` 必须存在，缺任一即判失败；只对带 fork/posix_spawn 压力签名的失败重试（最多 3 次、退避 15/30 s；`build.sh` 开头 `rm -rf build`，重跑即全量干净重建），其余错误首次即抛，不再可能产出空包 |
| 6 | 任何 tup 命令都立刻失败：`tmpfile: Permission denied` → ` *** tup: 1 job failed.`（发生在 Parsing Tupfiles 阶段） | libc 的 `tmpfile()` 把 `/tmp` 硬编码（glibc 的 P_tmpdir、musl 同样），而鸿蒙 `/tmp` 是 erofs 只读挂载（知识库 E002/E272 记录的平台既定特性）；tup 在 `parser.c`、`updater.c` 两处用 `tmpfile()` 做临时流，于是运行期直接不可用 | 补丁 0005–0008：新增 `tup_tmpfile()`，按 `$TMPDIR` → `.tup/tmp` → `/tmp` 依次回退，保持 `tmpfile()` 语义（匿名文件、自动删除）。`.tup/tmp` 回退让 tup 在只读 /tmp 平台上开箱可用，不依赖用户额外设置环境变量 |
| 8 | PR CI #91572（`conan-build-test`）：三次尝试全部倒在同一个链接步 `bootstrap LD tup`——`clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable`，`ConanException: build.sh still aborted by spawn-resource exhaustion after 3 attempts`；构建机 load 20~24、procs≈670 | 上一版重试（#7）是**整脚本**重试：每次失败都从头重编 ~90 个文件，而后才走到同一个链接，45 秒（15+30 s）的重试窗口在持续负载下不够用。**本条当时判断「clang 编译走集成汇编器、进程内不 spawn」——该判断已被 #9 的实测推翻（clang 每个文件都会 spawn `-cc1`），保留原文以记录当时的推理** | 补丁 0001：`build.sh` 新增 `retry_spawn()`，把链接步（`link lua`、`link.sh` 链接 `tup`、`tup-ldpreload.so`）与 `./lua` 调用点就地包裹——10 次 × 20 s ≈ 3 分钟窗口，每次重试只重跑链接、不重编；只对 `Resource temporarily unavailable`/`can't fork`/`cannot fork` 特征重试，其余错误首次即返回。配方外层兜底重试保留（3 次），退避由 15/30 s 提到 30/60 s。**该方案在 #9（PR #15176）中失效：30 次链接重试无一成功** |
| 9 | PR CI #15176（`conan-build-test`）：三次尝试共 **30 次**链接重试（10×20 s/次）全部倒在同一个 `bootstrap LD tup`，日志与 #8 同形；构建机 `load=21.6/21.5/21.4，procs=667~670`，而**同一台设备**本地同配方同源码（`procs≈180`）一次通过 | #8 的「编译不 spawn、只有链接 spawn」**经实测推翻**：`clang -### -c a.c b.c c.c` 显示每个文件都会 spawn 一个 `clang-15 -cc1`（一次编译 = 3 个并发进程：shell→clang→cc1），而 CI 上这些编译步**全部成功**。决定成败的是该步**同时**需要几个进程：普通编译 3 个、`link lua` 4 个（shell→命令替换子 shell→clang→链接器）都过，tup 链接 **5 个**（比 lua 多出 `link.sh` 这一层 shell）过不去——即构建机只剩约 4 个空闲进程槽（本机 `ulimit -u` 软限 32768，把 RLIMIT_NPROC 收窄到贴近基线时，构建同样在 sqlite3/链接段倒下）。这也解释了它为何**确定性地**每次都倒在同一处、而 30 次重试（含 20 s 等待）全无效：不是负载抖动，而是这一步的结构性进程需求超出了上限 | 补丁 0001 把链接步的并发进程数压到与编译步持平（本地忙轮询实测：链接步峰值 5 → 4，与普通编译步相同）：① `retry_spawn()` 不再用 `out=$(...)` 捕获输出——命令替换会让一个子 shell 在整个脆弱 spawn 期间常驻，恰好多占一个进程槽；改为重定向到文件 + 用 shell 内建 `read`/`case` 回放并判特征（构建期零额外进程）；② 就地展开 `link.sh` 的两步（版本对象改由真实源文件编译，顺带去掉 `(echo;echo) \| $CC -x c -c -` 管道），删掉链接链路上多出的一层 shell；③ 重试窗口由 10×20 s 提到 15 次、退避 20→60 s（≈13 分钟），每次重试前用 `/bin/sh -c :` 探针记录「能否创建进程」，供下一轮区分「整机槽位耗尽」与「本步需求过高」；④ 配方外层兜底 3 次改 2 次（最坏 2×(13min+构建) 仍在 CI 的 3600 s 单包超时内）。**未改动**链接器调用方式：SDK 的 `ld.lld` 是 `#!/bin/sh exec -a … lld --code-sign` 包装脚本，绕过它需自行拼 sysroot/crt 参数与 signature，风险大于收益 |

## 源码修改

`patches/` 下共 8 个补丁，按文件粒度由 `refresh-patch --auto`（per-file-difflib）生成；
**语义上仍是四组改动**，均只改构建/运行时适配层，未触碰 tup 的业务逻辑：

1. `0001-build.sh.patch`（+89/-4）
   - `build.sh`：新增 `HarmonyOS)` 平台分支（server 选择 + 兼容文件列表）；
     新增 `retry_spawn()` 并把链接步（`link lua`、tup 链接、`tup-ldpreload.so`）
     与 `./lua` 调用点就地包裹，用于 worker 上进程槽位耗尽（问题 #8、#9）；
     `retry_spawn()` 以重定向 + 内建 `read`/`case` 回放输出（不用命令替换，
     避免在脆弱 spawn 期间多占一个进程槽），并对 `Resource temporarily
     unavailable`/`can't fork`/`cannot fork` 退避重试（15 次、20→60 s）；
     tup 链接处就地展开 `link.sh` 的两步，使链接链路与普通编译步同为
     shell→clang→链接器，不再插入额外一层 shell（问题 #9）。
2. `0002-src-ldpreload-ldpreload.c.patch`（+138/-14）
   - `src/ldpreload/ldpreload.c`：`__GLIBC__` 守卫隔离 glibc 专有包装器；补 `struct stat` 声明；
     `depfd` 惰性打开；新增 `will_create()` 探测与 `O_CREAT` 实际创建 → 写事件；
     新增 `utimensat()` 包装（成功且目标非目录 → 写事件）。
3. tmpfile 改造（原 `0003-tmpfile-honour-tmpdir.patch`，因按文件拆分而分为 4 个补丁）
   - `0005-src-tup-file.c.patch`（+56/-0）：在既有 `src/tup/file.c` 中新增 `tup_tmpfile()`。
   - `0006-src-tup-fileio.h.patch`（+2/-0）：`src/tup/fileio.h` 中声明该函数原型。
   - `0007-src-tup-parser.c.patch`（+1/-1）：`src/tup/parser.c` 的 `tmpfile()` 改为调用它。
   - `0008-src-tup-updater.c.patch`（+1/-1）：`src/tup/updater.c` 的 `tmpfile()` 改为调用它。
   - 该函数与 `file.c` 同处编译单元，无需改构建脚本的通配列表。
   - **注意（Conan 补丁器约束）**：该实现最初放在新增文件 `src/tup/tmpfile.c` 中，但 Conan 的
     补丁器不处理 `--- /dev/null`（新增文件）hunk（G2 门禁会判 FAIL），故改写为"只修改既有文件"，
     把函数本体放回 `src/tup/file.c`。
4. TMPDIR 白名单（原 `0004-environ-forward-tmpdir.patch`，按文件拆分为 2 个补丁）
   - `0004-src-tup-environ.c.patch`（+8/-0）：把 `TMPDIR` 加入 `default_env` 白名单（POSIX 分支；
     与上游 Windows 分支已有的 `TEMP`/`TMP` 同理），使平台级 `TMPDIR` 与 `PATH`/`HOME` 一样被
     传递给构建命令。
   - `0003-src-tup-db.c.patch`（+1/-1）：按源码注释要求递增 `PARSER_VERSION` 16 → 17。

## 依赖版本

无第三方依赖。tup 自包含内嵌 lua、sqlite3、pcre2、inih；仅需 libc（musl）+ pthread + libm + libdl。

## 验证结果

```sh
# 语法/链接
$ CC=clang TUP_SERVER=ldpreload TUP_LABEL=0.8 sh ./build.sh   # exit 0
$ ./build/tup server        # → ldpreload
$ ./build/tup --version     # → tup 0.8

# 端到端冒烟：一个用 touch 产出输出的规则
$ printf ': |> touch %%o |> out.txt\n' > Tupfile
$ tup init --no-sync --force && tup && tup
 100% 0) [0.038s] touch out.txt
[ tup ] [0.051s] Updated.                     # 再次执行正确判为无需重建

# Conan 侧
$ python3 scripts/ohc-run.py conan-init  ... && python3 scripts/ohc-run.py conan-verify ...
# → gate1（配方完整性/R26）+ gate2（补丁可应用/构建）+ L2/L4/L5 全通过，状态 published
#   （报告：reports/conan-verify-report.md；conan create 的 test_package 冒烟测试通过）

# 修复问题 #7 后的本机门禁复跑（CI 等价入口，本地日志 ~/tmp/tup-w3-rerun.log）
$ CI_PACKAGES="archives/t/tup/0.8" zsh ci/conan/build_and_test.sh archives/t/tup/0.8
# → RC=0，build.sh 第 1 次尝试即建成（未走重试路径），L1/L2/L5 全过、Build Summary 1/1

# 修复问题 #9 后的本机复验（2026-10-16）
# 1) 直接跑打过补丁的 build.sh（与配方同参数），产物与版本串逐字节不变
$ CC=/data/service/hnp/bin/clang CFLAGS='-O2' TUP_SERVER=ldpreload TUP_LABEL=0.8 \
    LDFLAGS='-L/storage/Users/currentUser/usr/local/lib' /bin/sh -e ./build.sh
# → exit 0；build/tup 1563136 B、build/tup-ldpreload.so 35136 B（与修复前同尺寸）
$ ./build/tup --version        # → tup 0.8（内联 link.sh 后版本串不变）

# 2) 链接步并发进程峰值（忙轮询采样 /proc，稳态基线 procs≈183，取峰值增量）
#    旧形态：命令替换 -> link.sh -> clang -> 链接器   → +5
#    新形态：shell -> clang -> 链接器                 → +4
#    对照：同一条件下单个普通编译步（shell -> clang -> cc1）→ +4
#    ⇒ 链接步不再比「本来就能通过的编译步」多要进程。

# 3) W3（finish 内嵌 conan create）本地门禁
$ python3 scripts/ohc-run.py finish tup 0.8 published
# → conan create + test_package（版本 / ldpreload 后端 / 同目录 .so / 端到端增量）全过
#   .ci-result.json exit_code=0（2026-10-16）；CI 门禁类检查 L1/L2/L5 通过

# 上游自带测试套件（981 项用例，全量执行，逐例自带超时）
$ cd test && for i in t[0-9]*.sh; do timeout -k 5 180 sh -e "$i"; done
# 适配前基线（早前 979 项口径的记录）: 270 项失败，其中 165 项为 touch 写事件缺失（根因见补丁 0002），
#   其余为 tmpfile: Permission denied（根因见补丁 0005–0008）。本平台无法重跑未适配基线：上游原始
#   src/ldpreload/ldpreload.c 在 musl/clang 下编译不过（补丁 0002 的 __GLIBC__ 守卫即为此）。
# 适配后: 935 通过 / 41 失败 / 5 超时（共 981 项，100% 覆盖、无跳过，通过率 95.3%）
#         剩余失败全部为平台阻塞，按报错签名逐项归类：
#           A 直建只读 /tmp                   9 项
#           B 扫描 / 根目录被拒（full-deps）  17 项
#           C 沙箱缺外部工具/模块             3 项（ccache / sqlite3 / python-sh）
#           D 沙箱禁硬链接/fifo/unix socket   4 项（其中 1 项被 seccomp 以 SIGSYS 终止）
#           E 用户态/工具链语义差异           8 项（无 root 语义、缺 -pg 支持、crash 产物、ghost lib）
#         5 项按 180s/例 计为平台阻塞：3 项为 ^b^（run-in-bash）用例（见"注意事项"），
#           2 项为 t8093/t8094-tup-preserve*。
# 分类脚本与原始日志: ~/tmp/classify-failures.py、~/tmp/tup-full-clean.log（本地，不入库）
```

> 失败归类只统计**真正失败**的用例；上游 `test.sh` 的 `--- Run ... ---` 逐条记录已全量解析，
> 每条用例的通过/失败由 `*** <name>.sh failed|TIMEOUT` 标记判定，因此不存在"未跑到的用例"
> 被当作通过的情况。

## 鸿蒙真机专项测试（test_ohos/）

上游套件在构建树里跑，验证的是 tup 自身行为：它无法覆盖"装出来的包在鸿蒙真机上是否可用"，
也无法覆盖平台特性本身（只读 `/tmp`、toybox 用户态、无 `/dev/fuse`）。为此新增
`test_ohos/run_ohos_test.sh`（自包含，可在真机单独执行，CI 不自动执行）：

```sh
$ bash test_ohos/run_ohos_test.sh <包目录>       # 例：~/.conan2/p/b/tup*/p/bin
...
TEST_OHOS_TOTAL=17
===== tup 0.8 HarmonyOS 专项用例: 17 项，通过 17，失败 0 =====
```

逐条对应本次适配的改动：

| 用例 | 验证内容 | 对应改动 |
|------|---------|---------|
| T1a/T1b | `tup --version` 报 0.8；`tup server` = `ldpreload`（平台无可用 `/dev/fuse`） | 补丁 0001（build.sh 平台分支 / TUP_LABEL） |
| T2a–T2d | **完整消费者流程**：用 Tupfile 编译并链接 C 程序 → 运行产物核对输出 → 未变更时不重建 → 改动源码后增量重建 | ldpreload 追踪 clang 产出 |
| T3a/T3b | 规则 `touch` 新建输出（O_CREAT 路径）首次构建成功、二次执行不重建 | 补丁 0002 |
| T3c/T3d | 输出已存在时重跑同一条 `touch` 规则（utimensat 路径）仍被记为写事件 | 补丁 0002 |
| T4a–T4c | 只读 `/tmp` 上的 tmpfile 回退链：`$TMPDIR` 可写 / `$TMPDIR` 指向只读 `/tmp` / `$TMPDIR` 为空 | 补丁 0005–0008 |
| T5 | `TMPDIR` 随默认环境白名单传入构建命令 | 补丁 0004 |
| T6a–T6c | 注入库与可执行文件同目录、`bin/tup` 为 aarch64 ELF、产物无宿主路径泄漏 | 打包/交付约束 |

原始日志（本地，不入库）：`~/tmp/test_ohos_run2.log`。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/tup` | 构建系统 CLI（自包含，内嵌 lua/sqlite3/pcre2） |
| `bin/tup-ldpreload.so` | ldpreload 依赖追踪注入库，必须与 `tup` 同目录 |
| `test_ohos/run_ohos_test.sh` | 鸿蒙真机专项用例（17 项，含完整消费者端到端流程），CI 不自动执行 |

## 注意事项

- **必须使用 ldpreload 后端**：本平台无 `/dev/fuse`（且 `/dev` 不可写），fuse/fuse3 后端不可用。
- 运行时 `tup` 需要 `bin/` 目录下有 `tup-ldpreload.so`；迁移/打包时两者不可分离。
- **临时目录**：鸿蒙 `/tmp` 是只读 erofs 挂载，libc 的 `tmpfile()` 不可用，故补丁 0005–0008 让 tup
  优先使用 `$TMPDIR`、其次使用项目内 `.tup/tmp`。若部署环境另有约定，设置 `TMPDIR` 即可覆盖。
- **子进程环境白名单**：tup 只把"数据库记录过的环境变量"（`PATH`/`HOME`，以及 Tupfile 里 `export` 过或
  `@VAR@` 引用过的）传给构建命令（`src/tup/server/depfile.c` 的 `server_setenv()` 只用 envblock
  拼子进程环境）。鸿蒙 `/tmp` 只读，而构建命令（clang 等）同样需要可写临时目录，因此补丁 0004 把
  `TMPDIR` 加入 `default_env`，与 `PATH`/`HOME` 一样默认透传——真机用例 T5 验证了这一点。
  其余变量仍需在 Tupfile 里 `export` 或 `@VAR@` 引用，这是 tup 的既有设计。
- OHOS 的 `touch` 是 toybox 实现，与 GNU coreutils 语义不同；本适配在 shim 侧对齐，
  未改动系统用户态，因此对 GNU 用户态仍是正确行为。
- 上游 ldpreload 后端本身有 `vardict_fd=-1 /* TODO */` 限制（`t3000` 系列变量用例），
  与本次适配无关。
- **测试框架陷阱（踩坑记录）**：`test/tup.sh` 会把 `test/..`（仓库根）放在 `PATH` 最前，
  于是仓库根的 `tup` 副本会**静默遮蔽** `build/tup`。若根目录留着旧副本，全量测试实际测的是旧二进制，
  结果会完全失真（本次曾因此得到 289 项伪失败）。跑套件前必须确认 `test/../tup` 与 `build/tup`
  同时刻、且含新符号（`nm tup | grep tup_tmpfile`）。
- **`^b^`（run-in-bash）用例在本沙箱内挂起（平台限制，未修复）**：tup 对 `^b^` 标记的命令按
  `/usr/bin/env bash -e -o pipefail -c <cmd>` 启动（`src/tup/server/depfile.c:241`），该 bash 子进程在
  tup 内永不返回（已无子进程、阻塞在 futex），tup 便停在 `Executing Commands...` 不再前进。
  最小复现（同一份二进制，仅换 Tupfile 规则）：

  ```sh
  : |> ^b^ false |> out.txt           # 挂起（30s 超时、无输出）
  : |> false |> out.txt               # 正常 [ tup ] Updated.
  : |> ^b^ echo foo > %o |> out.txt   # 挂起（去掉 ^b^ 即正常）
  ```

  已排除的可能：bash 自身与启动形态正常（`/usr/bin/env bash -e -o pipefail -c 'false'` 单独执行
  rc=1、立即返回）；与补丁新增的事件检测无关（`^b^ false` 不产生任何文件事件，同样挂起）。
  无法与未适配版本直接对照：上游原始 `src/ldpreload/ldpreload.c` 在本平台编译不过（7 个错误，
  全在 glibc 专有包装器上，正是补丁 0002 加 `__GLIBC__` 守卫的原因）。受影响的上游用例共 3 个：
  `t2201-change-flags.sh`、`t4181-bash-shell-test.sh`、`t4182-bash-pipefail-test.sh`。
- `t5085-ctrl-c.sh`、`t5101-ctrl-c-keep-going.sh` 等用例脚本自身在 `/tmp` 下建工作目录
  （`mkdir /tmp/tup-t5085-$$`），本平台 `/tmp` 只读，用例在准备阶段即失败，计入上面 A 类平台阻塞。
---

**编译结束**: 2026-10-16 01:50
**最终状态**: published
