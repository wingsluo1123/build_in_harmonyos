# 按命令模式获取控制终端，保留 CLI 无终端执行路径

> 状态：B 路径知识草稿，未获委员会批准；关联 sacc/1.07 [PR #15167](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/15167)。

## 现象与根因

某些 CLI 有终端界面，也提供不需键盘输入的命令。若在初始化时无条件 `open("/dev/tty", O_RDONLY)`，在 CI、`setsid` 或服务进程中会得到 `ENXIO`，随后提前退出；批处理的文件或网络处理代码从未运行。stdin、stdout 可用并不意味着进程有控制终端。

`sacc/1.07` 是实测实例。旧 HEAD 在 [OHOS armv8 Buildbot #80046](https://ohpcd.atomgit.com/buildbot/#/builders/1/builds/80046) 完成编译和打包，但消费者 2/4；两条本地 Gopher 请求在服务端 `accept()` 前退出。本地无终端环境定位到 `setup()` 的 `/dev/tty` 打开失败。补丁 `archives/s/sacc/1.07/patches/0001-allow-headless-output.patch` 仅在非交互输出场景允许继续；保留交互场景对控制终端的需求。本地 Linux 无终端重建和消费者 4/4 通过。**该补丁的 OHOS 当前 HEAD 构建仍未通过有效 CI，因此目标端结论待定。**

## 判别与修复

1. 先判命令语义：本次是否需要读取键盘命令？仅凭 stdin 是否为 TTY 不足以判断，因为批处理可能从管道读取内容。
2. 需要交互时，打开 `/dev/tty`；失败应提示缺少控制终端并返回非零，不可假装完成。若业务还要从 stdin 读取内容，用单独的控制终端通道。
3. 无需交互时，保留原 stdin/stdout，不要求 `/dev/tty`。如果旧代码结构要求先尝试打开，仅对预期的无控制终端错误做模式限定的回退；其他 I/O 故障继续报告。
4. 用 `setsid` 验证无控制终端的真实业务输出，用伪终端验证交互路径，同时断言退出码。不能只断言程序没有崩溃。

| 条件 | 期望 |
| --- | --- |
| 无控制终端，批处理模式 | 完整输出，退出 0 |
| 无控制终端，交互模式 | 明确报缺少控制终端，非零退出 |
| 有控制终端，交互模式 | 正常进入交互功能 |

独立 C 夹具 `knowledge/drafts/fixtures/tty_mode_fixture.c` 与同目录测试脚本可复现：`setsid --legacy` 退出 2；`setsid --batch` 输出 `batch payload` 且退出 0；`setsid --interactive` 退出 2；`script -qec ... --interactive` 返回 `interactive ready` 且退出 0。执行方法：

```sh
cc -Wall -Wextra -Werror -o /tmp/tty-mode-fixture knowledge/drafts/fixtures/tty_mode_fixture.c
python3 knowledge/drafts/fixtures/tty_mode_fixture_test.py
```

这验证方法可迁移，不能当作 OHOS 真机测试。

## 适用边界与既有知识

仅用于**确有无交互业务路径**的 CLI。纯 TUI、打开 `/dev/tty` 后仍需按键才能完成的程序，不能套用批处理回退；应使用伪终端测试。已有 `DRAFT-E569-mdp-stdin-tty-freopen-pty-dual-channel` 讲述纯 TUI 在 CI 中如何用 PTY 双通道测试。本条增加模式判别和程序侧回退设计，针对同一 CLI 的无交互路径；若评审认为与 E569 重叠，应合并而非重复计分。`E214` 讨论 shell `read` 阻塞，也不覆盖 C CLI 的无控制终端早退。

## 证据与待补

- [sacc PR #15167](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/15167)：补丁、消费者测试和来源。
- [旧 OHOS 构建 #80046](https://ohpcd.atomgit.com/buildbot/#/builders/1/builds/80046)：2/4 的目标运行实证，不能作为修复成功证据。
- 修订后 WSL 无终端 `conan create` 4/4；独立 C 夹具四种模式可按上节命令复现，初次日志在 `/home/prummn/tmp/tty-mode-fixture-test.log`。
- 新 HEAD 的官方 OHOS 运行结果尚缺；委员会批准前要补入，且须确认知识与 E569 的差异足够形成新条目。
