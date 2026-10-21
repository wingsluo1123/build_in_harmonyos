# usbauth

USB 设备授权守护：配合 udev 规则在设备接入时按配置决定是否授权（白名单式管控 USB 设备）。
上游：<https://github.com/kochstefan/usbauth-all>

| 版本 | 说明 |
|------|------|
| [1.0.5](1.0.5/notes.md) | 当前适配版本（HarmonyOS PC / ohos-aarch64） |

## 这个包提供什么

- `sbin/usbauth` —— 由 udev 规则调用的授权判定程序（上游是 `sbin_PROGRAMS`，产物**不在 bin/**）
- `etc/usbauth.conf` —— 授权策略配置示例
- `lib/udev/rules.d/20-usbauth.rules` —— 触发规则
- `share/man/man8/usbauth.8` —— 手册页

## 适配要点（细节见各版本 notes.md）

1. **依赖三项全在仓**：`libusbauth-configparser`（配置解析库）+ `libudev`（本仓库由 `libudev-zero`
   提供同名 `.pc`）+ `dbus-1` → 不需要任何前置依赖适配。
2. **autotools 自举四道坎**：`automake`/`libtool` 走 `tool_requires`；自举前清 `PERL5LIB`/`PERL5OPT`；
   补缺失的 `m4/` 空目录；**在 autoreconf 之后**把 `configure` 里的 `umask 077` 改成 `022`
   （HMDFS 下不改会让 `config.status` 报 `Permission denied`）；另给 `--build=` 三元组。
3. **自检环境的 `LD_LIBRARY_PATH` 要并入全部 host 依赖**（含传递依赖）—— 漏一个 .so 时加载器会以
   `rc=127` 直接退出，容易被误判成"参数不支持"。
4. **测试边界**：正常功能依赖真实 USB 设备 + udev/dbus 运行时，沙箱/CI 只验证"产物可用 + 配置与规则
   随包"，并在 PR 正文如实说明。
