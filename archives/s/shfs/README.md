# shfs

**SSH 文件系统挂载工具**（SourceForge 项目，作者 Miroslav Spousta / QIWIN）

shfs 用一条已有的 shell 或 perl 会话把远端目录挂载成本地文件系统：不需要在远端装特殊服务端，
只要能用 `ssh`/`rsh` 起一个 shell，`shfsmount` 就把自己的协议脚本投递过去执行。
本项目同时含 Linux 内核模块 `shfs/` 与用户态工具 `shfsmount/`。

## 用法

```bash
shfsmount [OPTION] [[user@]host[:root]] mount_point
shfsumount mount_point
```

| 选项 | 说明 |
|------|------|
| `-c, --cmd=COMMAND` | 起远端通道的命令（如 `ssh %u@%h perl -e 'use POSIX; exec "/bin/sh"'`）；`%u %h %P` 分别替换 user/host/port |
| `-t, --type=TYPE` | 连接类型：`shell` 或 `perl`；不指定时上游会逐个探测并选稳定者 |
| `-u, --cmd-user=USER` | 以指定用户执行远端命令（root only） |
| `-P, --port=PORT` | 连接端口 |
| `-p, --persistent` | 保持连接 |
| `-s, --stable` | 解引用符号链接（若可行） |
| `-o, --options=OPTIONS` | 挂载选项（逗号分隔）：`cachesize=N` `cachemax=N` `preserve` `ttl=TIME` `uid=`/`gid=`/`rmode=`/`suid`/`dev`/`ro`/`rw`/`nosuid`/`nodev`/`exec`/`noexec`/`user`/`users` 等 |
| `-n, --nomtab` | 不更新 `/etc/mtab` |
| `-v, --verbose` | 打印调试信息（可叠加，`-vvv` 为全量协议跟踪） |
| `-V, --version` | 打印版本（形如 `shfsmount version 0.35(2)`，括号内是协议号） |

`shfsumount` 只接受挂载点一个参数（`-v` 打印版本），靠 statfs 魔数守卫确认目标是 shfs 挂载才卸载。

## 构建

- 构建系统：纯 Makefile（`shfsmount/Makefile`），**无 configure、无 `make check`**
- 上游测试工件：仅 `shfsmount/shell-test.in`、`shfsmount/perl-test.in` 两个能力探测脚本，
  运行时被投递给远端执行并读回结论（`ok stable` / `ok stable preserve`）
- 版本串：Makefile 从 `Changelog` 首行推导，配方应显式传 `SHFS_VERSION`
- 许可证：上游 `COPYING` 是 GPL-2.0 单文本，`debian/copyright` 写 "version 2, or any later version"
  → 记 `GPL-2.0-or-later`
- 源码：https://sourceforge.net/projects/shfs/files/shfs/shfs-0.35/shfs-0.35.tar.gz/download

## OHOS 适配

- 只构建用户态 `shfsmount/`：顶层 `all: module utils docs` 的 `module` 分支进 `shfs/` 编 Linux 内核模块，
  本平台无内核模块加载能力，配方不下探该目录
- `Makefile` 的 GCC 遗留 include 分隔符 `-I-` 改写为 `-iquote`（clang 不支持 `-I-`）
- `addmntent(3)`（glibc 扩展）替换为包内 static 写侧 helper，直接按 mtab(5) 六字段 `fprintf`
  —— OHOS libc 的 `<mntent.h>` 只有读侧 `setmntent/getmntent/getmntent_r/endmntent`
- `mount(2)` 被鸿蒙 seccomp 拦截：全链路会停在 SIGSYS(159)。这是平台 syscall 能力边界，
  适配层不伪造挂载成功；端到端用例把"恰好停在 mount(2) 且 `/proc/mounts` 无残留"固化成断言
- 归档解压排除 `debian/`（唯一符号链接成员所在目录，平台文件系统不支持设置符号链接自身属性，
  conan 的 source→build 复制会 EACCES）
- 交付两个命令，故有软件级 `commands.json`（R38）
