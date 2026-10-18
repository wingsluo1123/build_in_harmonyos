# esmtp

sendmail 兼容的 SMTP 中继客户端：从 stdin 读邮件，转发给预配置的中继 MTA，
并提供 `sendmail` / `mailq` / `newaliases` 入口。协议能力（EHLO 能力协商、
STARTTLS 升级、SASL 机制选择）由 [libESMTP](https://github.com/libesmtp/libESMTP) 提供。

- 上游主页：https://esmtp.sourceforge.net/
- 当前版本：1.2（2009-12-24 终版，上游已冻结）
- 构建系统：autotools
- 依赖：`libesmtp/1.1.0`

## 目录

- `1.2/` — 版本级配方（`conanfile.py`、`conandata.yml`、`patches/`、`test_package/`、`reports/`）
- `commands.json` — CLI 包声明（R38/L0k）

## 适配要点

见 [`1.2/notes.md`](1.2/notes.md)（问题表含根因与解法）与软件级 `manifest.yaml`
的 `ohos_adaptation.key_points`。
