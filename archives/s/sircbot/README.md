# sircbot

极简 IRC bot，面向「脚本/CI 触发发消息」场景（上游自述："a small IRC bot for use with
git hooks, cronjobs, scripts etc"）。

## 是什么

`sircbot` 连接一个 IRC 服务器并加入指定频道。每加入一个频道，它就在本机建立一个 AF_UNIX
socket；任何脚本把内容写进该 socket，bot 就把它作为 `PRIVMSG` 转发到对应频道。反向地，频道
里每收到一条消息，bot 会执行钩子目录下该频道的全部脚本，并传入「发送者、消息、频道名」三个
参数。

| 产物 | 说明 |
|------|------|
| `bin/sircbot` | 守护进程：连接 IRC、加入频道、持有频道 socket、执行钩子 |
| `bin/sircbot-send` | 命令行客户端：把 stdin 写入指定频道的 socket |

典型用法：

```sh
# 守护进程：连接服务器并加入频道（鸿蒙上需先指定可写的运行目录）
SIRCBOT_RUNDIR="$HOME/.sircbot/run" sircbot -s irc.example.org -n mybot '#channel1'

# 从任意脚本/CI 投递消息
echo "build finished" | sircbot-send '#channel1'
```

## 依赖

无第三方依赖，仅需 C 编译器和 GNU make（上游 README 的原始要求）。本适配不引入任何
Conan 依赖。

上游另一个可选组件是 Lua 绑定（`lua/lsircbot.c`）。本适配**未构建**该绑定：制品仓只发布
lua 的开发件而无解释器可执行文件，无法在目标机验证绑定的真实运行行为。详见
`0.4/notes.md`。

## 上游测试

**上游没有测试。** Makefile 无 `check`/`test` 目标（`make -n check` 返回
"No rule to make target 'check'"），源码中无任何断言或测试程序，源码包内也没有测试目录。
因此上游实测数为 0，本适配的验证全部来自 `0.4/test_package/` 新增的消费者端到端用例。

## HarmonyOS 适配要点

1. **unix socket 位置**：鸿蒙拒绝在用户可写目录 `bind` 路径名 AF_UNIX socket（任意目录均
   返回 `EPERM`），而抽象命名空间可用。补丁让通道 socket「路径名优先、被拒则回退抽象命名
   空间」，守护进程与 `sircbot-send` 对称实现。因此在鸿蒙上 socket 不会出现在文件系统中，
   可用 `grep <频道名> /proc/net/unix` 查看（条目以 `@` 开头）。
2. **运行目录**：鸿蒙既没有 `/var/run`，`/var` 也不可写。用 `SIRCBOT_RUNDIR` 指定可写目录；
   守护进程模式（不带 `-f`）会写 pidfile，该目录必须可写，否则进程启动即退出。
3. **钩子目录**：鸿蒙 `/etc` 为只读文件系统，用 `SIRCBOT_HOOKSDIR` 指定脚本目录。
4. **run-parts**：系统没有 `run-parts(8)`（busybox 提供同功能 applet 但没有同名命令）。
   补丁在 `SIRCBOT_RUNPARTS` / `/bin/run-parts` / PATH 三种方式都不可用时，用内置的 POSIX
   目录扫描执行钩子，参数语义与 `run-parts -a` 一致。

补丁全部为「历史行为优先 + 运行期覆盖/回退」的可移植实现，未使用任何平台宏。

## 版本

| 版本 | 状态 | 构建日期 | 备注 |
|------|------|----------|------|
| 0.4 | built | 2026-10-15 | 首个鸿蒙适配版本 |
