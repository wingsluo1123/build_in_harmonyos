# userinfo — 本地用户信息收集工具

`Userinfo`（作者 Ben Kibbey）是一个控制台小工具，用于显示一个或多个本地用户的各类
信息。功能以**可动态加载的模块**实现，输出以分隔符隔开，便于在 shell 脚本里处理。

## 用法

```
ui [-vhVL] [-c <filename>] [-t fmt] [-m c] [-F c] [-d]
   [[-xX] -O <module1> [options] [-- [-xX] -O <module2> [...]]]
   [- | username | -f filename] [...]
```

| 选项 | 说明 |
|------|------|
| `-O module` | 加载模块（可多次；模块名不带路径时在 `PREFIX/lib/userinfo` 查找） |
| `-d` | 加载默认模块（`passwd.so`、`mail.so`、`login.so`） |
| `-c file` | 读取配置文件（每行一个模块） |
| `-F c` | 字段分隔符（默认 `:`） |
| `-m c` | 多值分隔符（默认 `,`） |
| `-t fmt` | `strftime(3)` 时间格式 |
| `-v` | 详细输出（加组名等） |
| `-V` / `-h` | 版本 / 帮助 |

示例：

```
$ ui -O passwd.so root
root:x:0:0,...:-:-:!:!:-:/bin/false:!
```

## OHOS 适配要点

- **autotools**：release 自带预生成的 `configure` + `Makefile.in` + libtool，无需
  autoreconf。显式传 `--build/--host/--target=aarch64-unknown-linux-gnu` 以绕开
  不认 HarmonyOS 的老 `config.guess/sub`；`--program-prefix=` 恢复程序名为 `ui`。
- **补丁 0001**：autoconf `config.status` 用 `umask 077` 建临时目录（0700），HMDFS
  拒绝在 group/other 无 x 位的目录里创建文件 → 改为 `umask 022`。
- **模块加载**：`ui` 通过编译期 RUNPATH 定位 `lib/userinfo/*.so`；配方以最终包目录
  为 prefix，使 RUNPATH 直接有效。
- **无上游测试**：由 `test_package` 的消费者测试补齐（CLI + 三个模块 + 配置文件）。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/ui` | 主程序 |
| `lib/userinfo/passwd.so` | 口令/组信息模块 |
| `lib/userinfo/mail.so` | 邮件信息模块 |
| `lib/userinfo/login.so` | 登录/最近登录模块 |
| `share/man/man1/ui.1` | 手册页 |

## 参考资料

- 官网：<http://userinfo.sourceforge.net/>（上游 GitLab：<https://gitlab.com/bjk/userinfo>）
- 许可证：GPL-2.0-or-later
