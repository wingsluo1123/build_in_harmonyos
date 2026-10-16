# qpage — QuickPage SNPP/IXO 寻呼客户端

`QuickPage`（作者 Thomas Dwyer III，1995–1999）通过 **SNPP（RFC 1861）** 与
**IXO/TAP** 协议向数字寻呼机发送文本消息。它既能作为客户端把消息提交给 SNPP
服务器，也能作为服务器/守护进程接收 SNPP 提交、写队列并驱动调制解调器发送。

## 用法（客户端）

```
qpage [ options ] [ pagerid ] [ message ]
```

常用选项：

| 选项 | 说明 |
|------|------|
| `-p pager` | 收件人 pagerid（可多个，逗号分隔） |
| `-s server` | SNPP 服务器主机名（默认 `localhost`，可用环境变量 `SNPP_SERVER`） |
| `-f from` | 发送者（SNPP `CALLerid`） |
| `-l level` | 服务等级 0–11（0=优先） |
| `-c coverage` | 覆盖区/服务名 |
| `-a time` | 定时发送（`+hhmm` 或 `YYMMDDHHMMSS`） |
| `-m` | 从 stdin 读一封 RFC-822 邮件构造消息 |
| `-v` / `-h` | 版本 / 帮助 |

## OHOS 适配要点

- **单二进制、零三方依赖**：自带 `configure`（autoconf 2.12 生成）+ 手写
  `Makefile`，直接 `sh ./configure` 后 `make`。
- **源码形态**：上游只发布 `qpage-3.3.tar.Z`（`compress(1)` LZW 容器，明文 HTTP）。
  配方改从 NetBSD pkgsrc distfiles 镜像（HTTPS，sha256 固定）取字节一致的 distfile，
  并在 `source()` 里用纯 Python 解码 `.Z`。
- **无上游测试**：由 `test_package` 的消费者测试补齐——本地 mock SNPP 服务器 +
  `LD_PRELOAD` 端口改写，验证真实的 SNPP 命令序列。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/qpage` | 客户端/服务器可执行文件 |
| `share/man/man1/qpage.1` | 手册页 |
| `etc/qpage.conf.sample` | 服务器配置样例 |

## 参考资料

- 官网：<http://www.qpage.org/>（作者 tomiii@qpage.org）
- 协议：RFC 1861（SNPP）
- 许可证：自定义（可自由使用/复制，**禁止未经许可的营利性使用/转售**）
