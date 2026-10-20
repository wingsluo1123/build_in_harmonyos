# profanity

## 简介

profanity 是一款用 C 编写的控制台 XMPP 聊天客户端，使用 ncurses
做文本界面、libstrophe 处理 XMPP 协议，操作风格类似 Irssi。

## OHOS 适配

- 构建系统：Meson（上游 0.18.0 起移除 Autotools，仅支持 Meson）
- 最小功能构建：通知、插件、OTR/PGP/OMEMO、图标、拼写检查等可选
  功能保持关闭，仅需 glib、libstrophe、ncurses、readline、curl、
  sqlite3 六个必需依赖
- 上游 `meson test` 注册 `unit tests`（cmocka）与
  `functional tests`（需 stabber 服务器 + libutil，OHOS 无，跳过）

## 依赖

- glib 2.84.0.1
- libstrophe 0.14.0
- ncurses 6.6
- readline 8.3
- curl 8.15.0
- sqlite3 3.49.1

## 功能验证

```bash
profanity --version   # 期望输出含 0.18.2
profanity --help      # 期望退出码 0
```

## 参考

- 官网：https://profanity-im.github.io/
- 源码：https://github.com/profanity-im/profanity
