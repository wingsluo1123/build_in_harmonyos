# DRAFT-SOCK-MACRO: socket 扩展宏被兼容层兜底覆盖

## 基本信息
- **严重度**: 2（🟡 中：`-Werror` 下阻断编译；宽松编译下构建通过但运行期语义丢失）
- **类别**: libc, compat, portability, socket, ohos
- **草稿编号**: DRAFT-SOCK-MACRO
- **状态**: pending-editor-review（待主编审核入库，未自行 promote 为 E 编号）
- **作者**: weijiapan <weijiapan@noreply.gitcode.com>
- **来源 PR**: #16451
- **来源提交**: a17f738ef1
- **关联工具**: `knowledge/tools/kb-sock-macro/`（README / detect.sh / fix.sh / notes.md / reproduce.sh / sample）

## 错误特征
```
'SOCK_CLOEXEC' macro redefined|'SOCK_NONBLOCK' macro redefined|
                         macro redefined \[-Wmacro-redefined\]|
                         redefinition of 'SOCK_CLOEXEC'|
                         previous definition is here
```

## 根因分析
1. **平台真值**：OHOS 的 libc 是 musl，sysroot 的 `<sys/socket.h>` 已提供 socket 扩展位。
   本机实测（`clang -dM -E`）：`SOCK_CLOEXEC=02000000`(524288)、`SOCK_NONBLOCK=04000`(2048)、
   `SOCK_SEQPACKET=5`、`MSG_NOSIGNAL=0x4000`、`MSG_CMSG_CLOEXEC=0x40000000`、`SO_REUSEPORT=15`。
2. **兼容层兜底**：BSD 移植层（`bsd-compat/`、`compat/`、`portable/` 一类目录）为兼容老系统写
   `#ifndef HAVE_SOCK_CLOEXEC` → `#define SOCK_CLOEXEC 0`。当上游 configure 不探测
   `HAVE_SOCK_CLOEXEC`（交叉编译与新增平台分支常缺）时兜底生效，**把系统真值覆盖成 0**。
   真实命中点：`sndio-1.10.0/bsd-compat/bsd-compat.h:58`。
3. **后果两级**：
   - 编译期：同名宏两次定义且值不同 → `warning: 'SOCK_CLOEXEC' macro redefined
     [-Wmacro-redefined]` + `note` 指回 `sys/socket.h:99` 的 `02000000`；
     `-Werror` / `-Werror=macro-redefined`（发行构建与 CI 常态）下直接 error。
   - 运行期：宏被改为 0 后 `socket(AF_UNIX, SOCK_STREAM|SOCK_CLOEXEC|SOCK_NONBLOCK, 0)`
     只剩 `SOCK_STREAM`，`socket()` 返回成功，但 `fcntl(fd, F_GETFD)` 无 `FD_CLOEXEC`、
     `F_GETFL` 无 `O_NONBLOCK` —— fd 泄漏给 exec 的子进程、非阻塞语义丢失。
     **编译通过 ≠ 行为正确。**
4. **覆盖方向取决于 include 顺序**：兼容层头在系统头之前 include 时系统会再覆盖回来（仅告警），
   在其之后 include 时兜底值胜出（告警 + 语义丢失）。顺序是偶然的，重构会翻转结果，
   不能靠"运行没问题"忽略告警。

## 影响范围
带 `bsd-compat/`、`compat/`、`portable/` 目录的 BSD 系代码与 OpenBSD ports（sndio、tmux、openssh、
mtree 等），以及 configure 未探测 `HAVE_SOCK_CLOEXEC` / `HAVE_SOCK_NONBLOCK` 的交叉编译配方；
以 `socket(AF_*, SOCK_STREAM|SOCK_CLOEXEC|SOCK_NONBLOCK, 0)` 传扩展位的库均可能命中。

**限制（不覆盖）**：目标平台确实没有该宏时的合法兜底（判据必须带"平台已定义"前提）；
`MSG_NOSIGNAL` / `SO_REUSEPORT` 等"语义不同但值非 0"的情形需逐条人工判断，不走守卫机械修。

## 推荐方案
**方法**: `patch-ifndef-guard`（给兜底定义补 `#ifndef <MACRO>` 硬守卫）

**说明**: 系统已提供时以系统真值为准；平台真没有时兜底照旧生效。守卫以宏名自身为条件，
不引入平台宏，可向上游提交。

**验证/命令**:
```
bash knowledge/tools/kb-sock-macro/detect.sh --src <source-dir> --log <build.log> --cc <clang>
bash knowledge/tools/kb-sock-macro/fix.sh --src <source-dir> --cc <clang>
bash knowledge/tools/kb-sock-macro/reproduce.sh --json
```

## 回退方案
源码不可改（vendored / 生成代码）时，仅在构建侧抑制该告警（`-Wno-macro-redefined`），
**必须**在 `test_package` 用行为断言收口：`fcntl(fd, F_GETFD) & FD_CLOEXEC`、
`fcntl(fd, F_GETFL) & O_NONBLOCK`，并在 notes/PR 显式披露为降级方案。
参考断言实现：`knowledge/tools/kb-sock-macro/sample/sockcloexec-demo/test/check_cloexec.c`。

## 禁止策略
| 模式 | 原因 | 后果 |
|------|------|------|
| `-Wno-macro-redefined` 且无行为断言 | 该告警是编译期唯一能发现"平台宏真值被覆盖"的信号，无断言压制等于把缺陷推到运行期 | `socket()` 静默丢失 CLOEXEC/NONBLOCK 位，子进程继承不该继承的 fd |
| `-DSOCK_CLOEXEC=` / `-DHAVE_SOCK_CLOEXEC` | 把平台值或探测结论煮进构建命令，换平台即错 | 换 SDK/架构后宏值再次不一致，缺陷复发且更难定位 |

## 验证与复现证据（实测）
- **真实现场**：`sndio-1.10.0.pristine` 上 `detect.sh` 单处命中 `bsd-compat/bsd-compat.h:58`；
  严格编译（`-Werror`）1 error；`fix.sh` 后编译 `rc=0`，`detect.sh` 计数归零。
- **样例复现**（`sample/sockcloexec-demo/`，关掉知识库即复现原故障形态）：
  OFF 阶段宽松编译 2 warning + 运行时 2 断言失败；OFF 阶段严格编译直接 error；
  ON 阶段 `rc=0`、断言全 `ok`。
- **脚本双向验收**：`reproduce.sh --keep --json` → `phase1=reproduced, phase2=fixed`，退出码 0，
  完整日志 857 行。

## 关键词
`SOCK_CLOEXEC`, `SOCK_NONBLOCK`, `HAVE_SOCK_CLOEXEC`, `HAVE_SOCK_NONBLOCK`, `bsd-compat`,
`bsd-compat.h`, `macro redefined`, `FD_CLOEXEC`, `O_NONBLOCK`, `F_GETFD`, `F_GETFL`,
`02000000`, `musl`, `OHOS`, fd 泄漏, 静默违规, 兼容层兜底

## 关联条目
- **E086** `ohos-guard-ucred` — 同为 BSD 兼容层与 musl 头文件差异导致的 socket 域适配问题；
  该条走"缺结构体则内联定义"，本条走"有宏则不要覆盖"。
- **E510** — 同类"补丁静默不生效"教训的相邻条目（修法必须带可验证判据）。

---
*草稿由 sndio 1.10.0 适配过程沉淀；入库决策保留在人工审核。*
