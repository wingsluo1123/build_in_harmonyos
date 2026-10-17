# ircd-ircu

Undernet IRC 守护进程（ircu2）—— ircu 的现役维护分支，GPL-2.0。

IRC 服务端守护进程，纯 C 实现，支持 IPv4/IPv6、epoll/poll/select 可选事件引擎、
服务操作员（oper）体系、频道属性（chattr）、gline/kill 规则、whowas、jupe（服务器
合并伪装）等传统 IRCd 能力。

## 上游

- 项目：<https://github.com/UndernetIRC/ircu2>
- 发行 tag：`u2.10.12.19`
- 说明：原始 ircu 项目（ircu.org / github.com/ircu/ircu）已停摆，Undernet IRC
  是 ircu2 的现役维护方；Debian 源码包 `ircd-ircu 2.10.12.19+dfsg` 亦派生自此版本。

## 产物

安装到 `bin/`：

| 可执行文件 | 说明 |
|------------|------|
| `ircd` | IRC 服务端守护进程 |
| `umkpasswd` | 生成 IRC 口令哈希（oper 口令用） |
| `convert-conf` | 把旧版 `ircd.conf` 转换成当前格式 |

同时在 `ircd/` 下安装上游示例配置 `example.conf`（来自 `doc/example.conf`）。

## 快速上手

```bash
ircd -v                       # 打印版本与编译进来的事件引擎
ircd -?                       # 用法
ircd -k -d <datadir> -f ircd.conf   # 只校验配置然后退出
ircd -n -d <datadir> -f ircd.conf   # 前台运行（不 detach）
```

配置模板见 `ircd/example.conf`，各版本的适配细节见
[`2.10.12.19/notes.md`](2.10.12.19/notes.md)。