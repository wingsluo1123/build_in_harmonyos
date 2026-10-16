# vacation 3.3.3-nmu1 HarmonyOS PC 适配说明

## 源码与依赖

- 使用 Debian-native 官方发布归档 `vacation_3.3.3+nmu1.tar.xz`，版本在
  Conan 中按仓库规则表示为 `3.3.3-nmu1`。
- 源码调用 Berkeley DB 1.85 的 `dbopen`/`DBT` 接口，因此依赖已发布的
  `db1-compat/2.1.3`，不是 GDBM。
- 构建沿用上游单文件 Makefile，并显式传入 Conan 依赖的头文件和库目录。

## 适配内容

1. 在固定上限内把 RFC 5322 物理行重组为逻辑邮件头，再执行
   `Auto-Submitted`、`Precedence`、`X-Spam-Flag`、收件人与主题策略。
2. 同时接受 LF 与 CRLF，超长物理行、悬空续行和超界逻辑头均失败关闭。
3. `Auto-Submitted` 只有精确值 `no` 可继续自动回复，避免前缀比较把
   `nobody` 等非 `no` 值误判为人工邮件。
4. 回复主动写入 `Auto-Submitted: auto-replied`，并允许通过
   `VACATION_SENDMAIL` 指定 sendmail 兼容端点；未设置时保持上游默认路径。
5. OHOS 应用 UID 没有 passwd 条目时，仅在消息文件和数据库均为绝对路径的
   模式下接受显式逻辑用户名；相对路径仍要求真实 passwd home，不放宽边界。

## 测试

上游发布包无测试目录、测试源文件、`make check/test` 目标或文档化测试命令，
上游测试分母为 0。新增 12 个安装后消费者场景，其中包含一个完整的
HarmonyOS PC 专项流程：邮件输入经逻辑头策略、Berkeley DB、管道、派生进程
和 sendmail 兼容端点生成捕获回复。其余场景覆盖折叠策略头、CRLF、节流、
折叠收件人/主题/Return-Path、精确 `no` 与有界失败关闭。

最终真机 `conan create` 通过，日志 SHA256 为
`8041b67f3b0fa11210869593793c028d9a5f3b1f45fd0a8b4f5ab57c1560955d`。
三臂策略实验 9/9 符合预期，日志 SHA256 为
`fe5cc1481e5a6ddd5057cdeba42172c916c1b802d0003bfcfb0f745b21499631`。

## 产物审计

安装包包含 `bin/vacation`、手册页和许可证。最终 ELF 为 AArch64 PIE，依赖
`libdb.so` 与 `libc.so`，无 RPATH/RUNPATH、无个人或 Conan 缓存路径，且
`.codesign` 恰好一节。最终发布状态以官方 CI、审核及制品仓结果为准。

## 编译结束

本地真机构建、安装后消费者测试、三臂回归和产物审计均已完成；当前版本级
状态为 `built`。
