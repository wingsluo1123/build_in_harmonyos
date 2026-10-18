# 本机 W3 全绿、远端 CI 红：conan home 落在两个权限语义不同的挂载上

- **草稿 ID**: DRAFT-xine-0.99.14-hmdfs-mount-semantics-local-green-ci-red
- **来源**: xine/0.99.14 HarmonyOS PC 适配，PR #16499，远端 CI build `#97272`（2026-10-17）
- **分类**: hmdfs / filesystem / permission / ci-vs-local / autotools
- **状态**: 本地草稿（路径 B 知识库扩展）
- **与既有条目的边界**: 修复动作与取值归 **E129**（`sed-replace`，rec 1，`rec_auto_fix: true`）与 **E114**（`bypass-mktemp`）；“HMDFS 属主 uid ≠ 进程 uid → 权限检查落 group 分支”的机理见 **DRAFT-10863**。本条只记三件它们都没有覆盖的东西：**本机绿不构成 CI 绿的证据**、**鸿蒙的 `mktemp` 是 toybox 因而受 umask 影响**、**umask 站点要按构建路径可达性筛选**。

## 问题 / 错误签名

远端 CI 在 `conan create` 阶段失败，其余门禁全绿：

```
./config.status: line 655: ./confhGIGfN/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
ERROR: xine/0.99.14: Error in build() method, line 119
        autotools.configure()
ConanException: Error 1 while executing
```

同一时刻本机：`finish` 的 W3（`build_and_test.sh`）rc=0、`conan-verify` G0–G3 PASS、`test_package` 27/27。

同签名先例（本仓库内）：`archives/a/analog/homebrew/notes.md:34-38` 的 pcre2，
`./config.status: line 823: ./confFbDlCH/subs1.awk: Permission denied`（Buildbot `#7020`），修复动作同为 `umask 077 → umask 022`；
**该处只记了失败与修复动作，没有重跑回执**，所以它只能作取值佐证，不能当作“022 已被远端验证过”的证据。
更强的先例是同族依赖包 `xine-lib/1.2.13`：它的 `patches/0003-configure.patch` 对**同一份 autoconf `configure` 的同一站点**就是这两处 `umask 022`，与本包补丁逐字同形。

## 根因：两侧 conan home 不在同一种文件系统语义上

| | 本机 | CI worker |
|---|---|---|
| conan home | `/data/storage/el2/base/files/home/.conan2`（**应用私有挂载**） | `/storage/Users/currentUser/.cache/conan2`（**HMDFS**，见 `#97272` 日志的 `WARN: Build folder` 行） |
| 新建目录 mode（`umask 077` + `mktemp -d ./confXXXXXX`） | `drwx------` | `drwx--S---`（E129 记录的签名） |
| 本机在同一 HMDFS 挂载上的实测 | 同一命令得 `drwx--S---`，**但仍可写** | — |
| 权限检查落点 | owner（进程 uid == 记录属主 uid，两个挂载上都成立） | 未证实；`DRAFT-10863` 按“HMDFS 记录的属主 uid ≠ 进程 uid → 落 group 分支”解释，本条不把它写成事实 |
| 结果 | 可写 → configure 通过（本机在任何挂载上都复现不出拒写） | 写 `subs1.awk` EACCES → configure 中止 |

autoconf 生成的这段代码是崩溃现场（`configure` 与它生成的 `config.status` 里文本相同）：

```sh
{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
}
ac_tmp=$tmp
...
echo 'BEGIN {' >"$ac_tmp/subs1.awk" &&      # ← CI 在这一行 EACCES
```

CI 里的目录名是 `confhGIGfN`（6 位随机字母数字），说明走的是 `mktemp -d "./confXXXXXX"` 分支，不是 `conf$$-$RANDOM` 回落分支。

## 关键实测：toybox 的 `mktemp -d` 受 umask 影响

这一步决定了“改 umask 是不是空操作”。GNU coreutils 的 `mktemp -d` 恒以 0700 建目录（与 umask 无关），若本机是 coreutils，那么 sed 改 `configure` 里的 umask 对 `mktemp` 分支毫无作用。鸿蒙设备上实测（`mktemp --version` → **toybox 0.8.12**）：

| umask | HMDFS 挂载上的目录 mode | group 位 | 私有挂载 |
|---|---|---|---|
| `077` | `drwx--S---` | 无 r/w/x | `drwx------` |
| `022` | `drwxr-s--x` | r + x（无 w） | `drwx------` |
| `007` | `drwxrws---` | r + w | `drwx------` |
| `002` | `drwxrws--x` | r + w | `drwx------` |

复现命令（同目录内逐值跑）：

```sh
for u in 077 022 007 002; do
  d=$( (umask $u; mktemp -d "./c${u}XXXXXX") )
  ls -ld "$d"; ( cd "$d" && : > f ) && echo WRITABLE || echo DENIED
done
```

注意：**本机上四种 umask 都显示 WRITABLE**（因为走了 owner 分支）。也就是说 mode 字符串能复现，**拒写不能复现**——这正是“本地测不出、只能靠远端”的那类问题。

## 取值判据：按“同族兄弟包同站点是否已如此修 + 知识图谱 rec 原值”取值，不按本机看起来更严格取值

`umask 022` 只给 group `r-x`（无 `w`），单看 group 分支的静态分析会让人倾向 `007`/`002`（`DRAFT-10863` 即主张 `007`，其场景是真机 `./configure`，无 CI 记录）。这个静态张力本条不强行自圆；在只有 2 轮修复预算的前提下按证据强度排序：

1. **同族兄弟包在同一站点已如此修**：`xine-lib/1.2.13`（本包的引擎依赖，已在制品仓）的 `patches/0003-configure.patch` 对同一份 autoconf `configure` 的同一处 `mktemp -d "./confXXXXXX"` 块就是两处 `umask 022`，与本包补丁逐字同形；
2. E129 rec 1 的原值就是 `umask 022`（`rec_auto_fix: true`）；
3. 仓库内该取值是绝对主流（可复算口径：遍历 `archives/*/*/*/patches/*.patch`，取含 `-… umask 077` 删除行的 1382 个补丁，统计其 `+` 行的 umask 取值 → `022` 2117 行 / 636 个不同包名，`000` 377/136，`002` 78/30，`007` 49/18）；
4. 与本条**逐字同签名**的 pcre2 失败（`#7020`）修复动作也是 `umask 022`，但无重跑回执，只作佐证。

→ 取 `umask 022`。结果检验：远端 `#97272` 红 → 改后 `#97351` 绿（两轮之间只多这一个 hunk），该取值成立。构建账目为**两次红同签名**（`#97241` @CI-030、`#97272` @CI-001——中间那次只是把第三轮审计的文档改动重推一次，没碰修复）＋**三次绿**（`#97351` @CI-040、`#97427` @CI-021、`#97445` @CI-026）：五次构建落在五台不同 worker，跨机一致，「单机抖动」解释被排除；也说明**修复轮要按错误签名计而不是按构建次数计**，否则 1 轮的真修复会被记成 2 轮、把 R42 预算虚耗光。若远端当时仍以同一行 EACCES 失败，第 2 轮才升级到给 **group** 写位的取值（`007` 得 `drwxrws---`、`002` 得 `drwxrws--x`，两者 other 仍无写位）。

## 站点筛选：文本命中 ≠ 需要改

对 sha256 已核过的 `.orig` 源码树整树逐行普查，`umask 077` 共 **9 行 / 6 个文件**，只有 `configure` 的两处在构建路径上（别只 grep 三个熟悉的名字就下“只剩两处”的结论，会漏计）：

| 站点 | 是否在构建路径上 | 判据 |
|---|---|---|
| `configure:16709/16714`（2 处 mktemp 块） | **是** | `autotools.configure()` 直接执行它；`config.status` 又由它生成 |
| `config.guess:119/120/121`（`set_cc_for_build()` 内） | 否 | 新增的 `aarch64:HarmonyOS:*:*)` 分支直接赋值 `GUESS`、不调用该函数。实测 `sh config.guess` → `aarch64-unknown-linux-ohos`、rc=0、且不产生任何 `cgXXXXXX` 目录（把 `TMPDIR` 指到 HMDFS 亦然）。pcre2 的 `#7004` 正是走进该函数才被拒 |
| `Makefile.in:748`（`distcheck` 的 `$$dc_destdir`） | 否 | `make` / `make install` 不触达该规则 |
| `misc/xine-bugreport:19`、`misc/xine-check:19`、`misc/xine-check.sh.in:19` | 否（**运行期**） | 是随包安装、`commands.json` 声明的命令，`umask 077` 只影响脚本自己建的临时文件；本机实跑 `xine-check` rc=0，但其在真机/worker 上的运行期语义属未验证面，应记录而不是当作无关文件忽略 |

`config.status` 不必单独打补丁：tarball 内不存在它，它是 `configure` 运行时写出的生成物（R6 只改源文件）。传导可用生成物直接证明：

```sh
grep -c "umask 077" <build_folder>/config.status     # → 0
grep -n "umask 0"   <build_folder>/config.status     # → :626 / :631 均为 umask 022
```

## 排查口诀

> 本机 W3 与 `conan-verify` 全绿、远端 CI 在 `conan create` 里报 `config.status: … ./confXXXXXX/…: Permission denied`：
> 这不是配方差异，是**挂载差异**。先比对两侧 conan home 在哪个挂载，再在同一目录里用不同 umask 跑 `mktemp -d` 列出 mode 表；
> 本机复现出 mode 但复现不出拒写 = 命中本条。修复取值以“同族兄弟包在同一站点的既有补丁 + 知识图谱 rec 原值”为准，不看本机看起来哪个值更严格；
> 改完一定看**生成物** `config.status` 的 umask 行来确认传导，而不是看本机是否又绿一次。

## 适用范围

- 所有“本机判定绿 → 交远端 CI”的 autotools 包（`configure`/`config.status`/`config.guess` 任一环节建临时目录）。
- 更一般：任何在本机与 CI 上 conan home 挂载点不同的包，其**权限类**失败都不应期望由本地复验证明修复有效。
- 需要知道 `mktemp` 语义的平台：本设备是 toybox，`mktemp -d` 受 umask 影响；移植到 GNU coreutils 环境时该结论不成立。

## 关联文件

- `archives/x/xine/0.99.14/patches/0003-configure.patch`（第二个 hunk：`umask 077` → `umask 022`）
- `archives/x/xine/0.99.14/notes.md`（问题 1、问题 15 与「远端 CI 第 1 轮红 → 修复 → 复验」表）
- `archives/a/analog/homebrew/notes.md`（pcre2 同签名的远端先例 `#7020`）
- `knowledge/graph/E129.kv`、`knowledge/graph/E114.kv`、`knowledge/drafts/DRAFT-10863-hmdfs-umask077-uid-mapping-group-perm.kv`
