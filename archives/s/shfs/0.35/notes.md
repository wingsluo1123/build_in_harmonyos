# shfs 0.35 适配笔记

## 编译环境
- 构建系统: makefile（`shfsmount/Makefile` 裸 make，无 configure/cmake/meson）
- 编译日期: 2026-10-17
- 编译器: clang 15 / aarch64-unknown-linux-ohos（musl libc + libc++，OHOS SDK 26.0.0.18 sysroot）
- 状态: built（R29 口径：conan create/verify 已 PASS 但配方尚未 `conan upload` 到制品仓；合并后由发布流水线上传成功再转 published）

## 编译步骤

shfs 0.35 是"Linux 内核模块 + 用户态 mount 工具"的混合体。本平台只取用户态部分：

1. 取源码：SourceForge 官方 tarball（URL 以 `/download` 结尾，归档扩展名被隐藏，
   配方里用 conandata 的 `filename: "shfs-0.35.tar.gz"` 显式给出，否则格式嗅探失败）。
   解压时排除 `debian/`（发行版打包元数据，内含唯一的符号链接成员）。
2. 应用 3 个移植补丁（`refresh-patch --auto shfs 0.35` 生成，见"源码修改"）。
3. 构建：`make -j1 -C shfsmount CC="clang" LINKER="clang" SHFS_VERSION="0.35"`。
   只进 `shfsmount/` 子目录——顶层 `all: module utils docs` 的 `module` 分支进 `shfs/`
   编 Linux 内核模块，本平台无对应物；命令行 `CC/LINKER` 覆盖 Makefile 里硬编码的 `gcc`
   （make 命令行赋值优先级高于 `:=` 与 `=`）。
4. 无 configure 步骤，因此没有 `--prefix` 之类的参数需要治理；`SHFS_VERSION` 必须显式传，
   否则 Makefile 从 `Changelog` 首行推导，与配方版本可能不一致。
5. 打包：`bin/{shfsmount,shfsumount}`、`licenses/COPYING`（上游 COPYING 为 GPL-2.0，
   `debian/copyright` 写 "version 2, or any later version" → 配方 license 记 GPL-2.0-or-later）、
   `res/shfs/{shell-test.in,perl-test.in}`（上游自带能力探测脚本随包分发，让 test_package
   逐字执行上游用例而不是重抄一遍）。

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| `clang-15: error: '-I-' not supported, please use -iquote instead`，第一条编译命令即失败 | `-I-` 是 GCC 4.x 以前的 include 路径分隔符，clang 从未实现；错误在 driver 参数解析阶段，与头文件内容无关 | `SEARCHDIRS` 按原语义改写为 `-iquote . -iquote ../shfs/Linux-2.4/`（补丁 0001）；知识图谱 E2141 |
| `ld.lld: error: undefined symbol: addmntent` | `addmntent(3)` 是 glibc 扩展，OHOS sysroot 的 `mntent.h` 只导出读侧 `setmntent/getmntent/getmntent_r/endmntent`（`MOUNTED "/etc/mtab"` 也在该头）；clang 15 把隐式函数声明降为 warning，所以错误面落在链接期 | 在两个源文件内各补一个 `static shfs_addmntent()`，按 mtab(5) 六字段直接 `fprintf` 并保持"出错返回非 0"契约（补丁 0002/0003）；知识图谱 E2142 |
| `conan create` 在 `BadZipFile: File is not a zip file` | SourceForge 下载 URL 以 `/download` 结尾，conan 靠扩展名嗅探归档格式，识别不到 `.tar.gz` | conandata.yml 增加 `filename: "shfs-0.35.tar.gz"`（既给 download 缓存名，也让解压走 tar 分支）；已有知识 E483/E276 |
| `Error copying sources to build folder` + `[Errno 13] Permission denied` 落在 `debian/changelog` | tar 里该成员是符号链接（type=2, mode=0120777 → `../Changelog`，由上游 `deb-changelog` 目标 `ln -fs` 生成）。conan 的 `installer._copy_sources()` 用 `copytree(..., symlinks=True)`，CPython 3.12 `_copytree` 建链成功后紧接着 `copystat(follow_symlinks=False)`，而平台文件系统不支持改符号链接自身属性 → lchmod 返回 EACCES。失败早于 `build()`，在 build() 里删链接删不到 | `get(..., excludes=["*/debian/*"])` 在解压阶段排除（`untargz` 用未 strip_root 的原始成员名做 fnmatch）；知识图谱 E2143 |
| shell 协议全链路的自动化用例耗时会随 CI 沙箱的 /tmp 策略漂移 | 上游 `shell-code.in` 的 `s_init` 对硬编码 `/tmp/._shfs_.<i>` 逐个 `mkdir` 试探，失败时用 `expr` 自增重试到 10000；实测纯循环 10000 次 fork 为 4 分 15 秒 | 上游 shell 探测脚本本身逐字执行并断言（U1），协议全链路端到端走 perl 分支（H1，`s_init` 只设环境变量并回 `### 200`，无循环）；shell 全链路保留手工验证记录 |
| `mount(2)` 被 seccomp 拦截，`shfsmount` 收不到挂载成功 | 平台 syscall 能力边界，非适配缺陷 | 把"恰好停在 SIGSYS(159) 且 /proc/mounts 无残留"固化为 H1 断言；mtab 写入分支只有链接期证明，运行期走不到（见 reports/test-report.md） |

## 源码修改

三个补丁均由 `refresh-patch --auto shfs 0.35` 从工作树与原始树逐文件 diff 生成，只动上游源文件，无生成文件改动：

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-shfsmount-Makefile.patch` | `shfsmount/Makefile` | `SEARCHDIRS := -I- -I. -I../shfs/Linux-2.4/` → `-iquote . -iquote ../shfs/Linux-2.4/` |
| `0002-shfsmount-shfsmount.c.patch` | `shfsmount/shfsmount.c` | 新增 `static int shfs_addmntent(FILE *, struct mntent *)`，`update_mtab()` 内 `addmntent(mtab, &ment) == 1` → `shfs_addmntent(mtab, &ment)` |
| `0003-shfsmount-shfsumount.c.patch` | `shfsmount/shfsumount.c` | 同名 helper，mtab 重写循环里 `addmntent(new_mtab, ment)` → `shfs_addmntent(new_mtab, ment)` |

补丁无平台宏（`shfs_addmntent` 是纯 POSIX 写法，可原样提交上游），注释为英文并说明动机，符合上游风格。

## 依赖版本

- Conan 侧依赖：无。`shfsmount/Makefile` 的 `LOADLIBES` 为空，两个二进制只链 OHOS sysroot 的 musl libc，无第三方库，因此配方里 `requirements()` 为空、`package_type="application"`。
- 构建工具：clang 15 / make / GNU tar（系统自带），`GnuToolchain` 只生成环境变量，不注入任何 conan 包。
- 运行时外部依赖：`shfsmount` 通过 `fork`+`execvp` 起远端通道，H1/U2 用到平台 `/bin/sh` 与 `perl`（perl 在 `/data/service/hnp/bin`，test_package 里按需补 PATH）。

## 验证结果

```bash
conan create archives/s/shfs/0.35 --profile=<ohos-arm64>
# test_package 执行 test_shfs.sh：9 个用例（U1 U2 上游 2/2 全量、H1 H2 鸿蒙特有、C1..C5 CLI 契约）
# [PASS] U1-shell-test.in ... [PASS] C5-umount-contract
# 9 cases run, 0 failed
# OK: shfs 0.35 OHOS suite passed (9/9)
file <package>/bin/shfsmount      # ELF 64-bit LSB, ARM aarch64, musl OHOS
shfsmount -V                      # shfsmount version 0.35(2)   （证明 SHFS_VERSION 已烧进二进制）
shfsumount -v                     # shfsumount version 0.35(2)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/shfsmount` | 72128 B | 挂载入口，含 shfs 协议 client（`proto.c` 编入） |
| `bin/shfsumount` | 31104 B | 卸载入口，statfs 魔数守卫 + mtab 重写 |
| `licenses/COPYING` | 17992 B | 上游 GPL-2.0 原文 |
| `res/shfs/shell-test.in` | 231 B | 上游 shell 能力探测（U1 逐字执行） |
| `res/shfs/perl-test.in` | 350 B | 上游 perl 能力探测（U2 逐字执行） |

## 注意事项

- 顶层 `make`（`all: module utils docs`）在没有 Linux 内核头文件的平台上必然失败，配方只 `-C shfsmount`。
- `shfsmount` 需要 `mount(2)` 才能真正挂载，OHOS 上被 seccomp 拦为 SIGSYS；测试断言以此停止点为契约，不要把它当构建缺陷去"修"。
- `-n/--nomtab` 是配套的：不挂载时避免去写 `/etc/mtab`；H1/H2 均带 `-n`。
- `shfsumount` 不认 `--version`/`--help`（getopt 只认 `-v`），W3 的 L2 冒烟检查对此报 non-blocking warning，属上游 CLI 形态，不是回归。

## 发现与知识

| # | 发现 | 判定 | 去向 |
|---|------|------|------|
| 1 | `-I-`（GCC 遗留 include 分隔符）被 clang driver 直接拒绝，错误面无文件名/行号，改写为 `-iquote` 才收敛 | ✅ 已提取为通用条目 | knowledge_ref: knowledge/drafts/E2141-draft-24E4.kv |
| 2 | OHOS libc 的 `mntent.h` 只有读侧，`addmntent(3)` 缺失导致链接期 undefined symbol；包内 static 写侧 helper 是最小可上游方案 | ✅ 已提取为通用条目 | knowledge_ref: knowledge/drafts/E2142-draft-24E4.kv |
| 3 | 源码 tar 含符号链接成员时，conan 的 source→build `copytree(symlinks=True)` 因 `copystat(follow_symlinks=False)`（lchmod）在鸿蒙文件系统上 EACCES 而失败，且早于 `build()`；解压阶段 `excludes` 排除是最稳的解 | ✅ 已提取为通用条目 | knowledge_ref: knowledge/drafts/E2143-draft-24E4.kv |
| 4 | SourceForge `/download` 结尾 URL 让 conan 归档格式嗅探失败（BadZipFile），需 conandata `filename:` 补齐扩展名 | ✅ 已有条目覆盖，本次仅复用 | knowledge_ref: knowledge/graph/E483.kv |
| 5 | `mount(2)`/`umount2(2)` 在 OHOS 被 seccomp 拦为 SIGSYS，用户态挂载工具的端到端契约应固化为"停在 syscall 边界且无状态残留" | ✅ 已有条目覆盖，本次仅复用 | knowledge_ref: knowledge/drafts/DRAFT-mhddfs-0.1.39.0-ohos-fuse-consumer-mount-boundary.kv |
| 6 | 上游自带"测试"在只有能力探测脚本的项目里 = 全部可执行用例，必须逐字执行并在 test_package 里随包分发脚本，而不是另写等价物 | ✅ 已沉淀到 test_package/MANIFEST.yml 与 reports/test-report.md 口径 | knowledge_ref: knowledge/drafts/DRAFT-mhddfs-0.1.39.0-fuse-consumer-test-construction.kv |
---

**编译结束**: 2026-10-17 19:49
**最终状态**: built
