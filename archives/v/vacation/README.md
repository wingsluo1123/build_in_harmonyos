# vacation

`vacation` 是一个带发送者节流数据库的邮件自动回复命令行工具。

## OHOS 适配

适配使用已发布的 `db1-compat` 提供 Berkeley DB 1.85 API，并保持上游
Makefile 的单文件构建方式。邮件头处理改为先有界重组 RFC 5322 逻辑头，
再执行 `Auto-Submitted`、`Precedence` 等循环抑制策略；回复中写入
`Auto-Submitted: auto-replied`。安装后消费者测试在 HarmonyOS PC 上实际
运行数据库、管道、派生进程和 sendmail 兼容接口。

## 依赖关系

- `db1-compat/2.1.3`：回复节流数据库。
- 运行时可与提供 sendmail 兼容命令行接口的邮件传输代理集成。

## 参考资料

- https://packages.debian.org/source/sid/vacation
- https://www.rfc-editor.org/rfc/rfc5322
- https://www.rfc-editor.org/rfc/rfc3834
