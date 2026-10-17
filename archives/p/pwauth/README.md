# pwauth

pwauth 是一个供 Apache `mod_auth_external` / `mod_authnz_external` 调用的 Unix
口令认证器：从 stdin 读取 `login\npassword\n`，只通过退出码报告认证结果
（`0` 成功、`1` 未知用户或口令错误、`2` 口令错误、`3` uid 低于 `MIN_UNIX_UID`、
`50` 调用者 uid 不允许、`51` 参数/输入错误、`52` 内部错误、`53` 读不到口令库）。

本目录是 pwauth 在 HarmonyOS PC（OHOS 6.0 / aarch64）上的 Conan 适配归档。

- 上游仓库：<https://github.com/phokz/pwauth>（原 Google Code 项目）
- 适配版本：`2.3.11`
- 包类型：`application`（命令行工具），产物 `bin/pwauth`
- 构建系统：纯 Makefile（没有 `configure`，也没有 `install`/`check` 目标）

## OHOS 适配要点

- **认证后端选 PAM**（依赖 `linux-pam/1.7.2`），与 Debian `pwauth 2.3.11-6` 的
  打包口径一致。OHOS 侧暴露 `shadow.h` 但未声明 `getspnam()`，`SHADOW_SUN`
  后端无法链接，而 `SHADOW_NONE/BSD` 又依赖 glibc/BSD 的影子口令语义。
- **`config.h` 通过补丁改为 OHOS/PAM 默认值**：启用 `PAM`、取消 `SHADOW_SUN`；
  关闭 `UNIX_LASTLOG`/`HAVE_LASTLOG_H`、`NOLOGIN_FILE`/`MIN_NOLOGIN_UID`、
  `CHECK_LOGIN_EXPIRATION`/`CHECK_PASSWORD_EXPIRATION`、`SLEEP_LOCK`
  （`/var/run` 睡眠锁），并取消写死的 `SERVER_UIDS`（改由安装权限 04755 约束），
  `MIN_UNIX_UID` 由 500 调整为 Debian 使用的 100。
- **`main.c` 可移植性**：补上 `main()` 的显式 `int` 返回类型；`bzero()`（遗留 BSD
  接口，`pwauth.h` 只包含 `string.h`）改为等价的 `memset()`。
- **`auth_pam.c` 端到端测试钩子（补丁 0003）**：当环境变量 `PWAUTH_PAM_CONFDIR` 存在
  且进程未提权（`getuid() == geteuid()`）时，用 Linux-PAM 的 `pam_start_confdir()`
  把服务查找指向私有目录。设备没有 `/etc/pam.d`，没有这个钩子就无法在测试中跑出
  “认证成功”；setuid 安装始终使用系统 PAM 配置，非特权调用者无法借此绕过系统认证。
- **纯 Makefile 构建（R33）**：上游 `Makefile` 自己赋值 `CC/CFLAGS/LIB`，
  makefile 赋值会覆盖环境变量，因此编译参数经 `make` 命令行传入：
  `CC` 取自 `tools.build:compiler_executables`，`CFLAGS` 取自 `AutotoolsToolchain`，
  `LIB="-L<linux-pam>/lib -Wl,-rpath,<linux-pam>/lib -lpam -ldl"`。
- **打包**：上游没有 `install` 目标，`package()` 直接把构建出的 `pwauth`
  拷进 `bin/`；`checkfaillog`/`unixgroup` 不构建也不打包（PAM 后端下无意义，
  Debian 同样不打包）。
- **运行时**：二进制声明 `NEEDED libpam.so.0`；除 Conan `conanrun`
  环境外，recipe 还写入指向 linux-pam 的 rpath，便于直接运行。

## 依赖

| 依赖 | 类型 | 状态 |
| --- | --- | --- |
| `linux-pam/1.7.2` | 构建 + 运行 | 已在本仓适配并发布到 `ohpcd` |

## 验证状态

- 真机（HarmonyOS PC aarch64）单包 shadow CI：`L0/L1/L4/L5 pass`、
  `L2 skip`（上游无 `--version/--help`，该步非阻塞）、`Total 1 / Success 1 / Failed 0`
- `test_package`：7/7 通过，含**完整的端到端消费者用例**——`test_consumer.c` 按
  `mod_authnz_external` 的方式调用已安装的 `pwauth`（fork/exec + stdin 凭据 +
  退出码结果），配合私有 PAM 服务（`pam_permit.so`）验证一条真正跑通的认证成功链路
  （退出码 0），以及两条端到端失败/默认链路；其余检查覆盖失败路径断言与 `libpam`
  动态依赖校验
- 上游自动化测试数：**0**（发布包无测试目录、Makefile 无 `check`/`test` 目标），
  因此适配后以消费者视角补全验证，详见 `2.3.11/test_package/MANIFEST.yml`
- 适配过程、真机证据与已知限制见 `2.3.11/notes.md` 与
  `2.3.11/reports/W0-and-source-analysis.md`
