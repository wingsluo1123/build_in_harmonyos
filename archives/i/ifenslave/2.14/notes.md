# ifenslave 2.14 适配笔记

## 上游信息

- 名称: ifenslave 2.14
- 上游仓库: https://salsa.debian.org/debian/ifenslave
- 文档: https://wiki.linuxfoundation.org/networking/bonding
- 许可证: GPL-3.0-or-later
- 源码包: https://deb.debian.org/debian/pool/main/i/ifenslave/ifenslave_2.14.tar.xz
- SHA256: `684e7c80da5346ed15f61ace0743c66fdb4442b445dec872a5317be5afe883c9`（12,840 字节，经 `mirrors.aliyun.com` 实测下载验证，与 `.dsc` 记录一致）
- 源码形态: Debian-native 包（`Format: 3.0 (native)`），解包仅 22 个条目，全部位于 `debian/` 下，无 C 源码、无 `configure`、无 `Makefile`、无 `CMakeLists.txt`

关键发现（`debian/README.source` 原文）:

> Originally, the Linux kernel documentation contained a file named `ifenslave.c`
> which could be used to add/remove slaves from a bonding master. ... Therefore,
> the binary has now been replaced by a shell script which accepts the same options
> as the original binary.

且 `debian/NEWS`（2.10）明确: `This version of the ifenslave package no longer
provides /sbin/ifenslave.` 当前 2.14 仅提供 ifupdown 钩子与 systemd link，不再编译任何二进制。

## 适配策略（路径 A：基础适配）

纯脚本包，无编译单元：

- `source()`: `get()` 解包（`strip_root=True` 后得到 `debian/`）
- `build()`: 校验 3 个上游钩子存在（`ifenslave.if-pre-up` / `ifenslave.if-up` / `ifenslave.if-post-down`），不做编译
- `package()`: 将 3 个钩子安装到 `bin/`（保留上游文件名，加可执行位，HMDFS 下 `chmod` 失败仅告警），文档与示例安装到 `share/doc/ifenslave/`（`README.Debian`、`README.source`、`NEWS`、`copyright`、`98-net-bonding.link` + 4 个 `examples/` 配置）
- `package_info()`: `bindirs = ["bin"]`，`libdirs = []`，`includedirs = []`
- `settings = "os", "arch"`（无编译器依赖，与 `abcde` 同形态）
- 无外部依赖（`ifupdown` / `iproute2` 为 Debian 运行时依赖，非 Conan 包，不声明 `requires`）
- 无补丁（`patches: {}`）

## 上游测试审计（结论：无测试）

对 `ifenslave_2.14.tar.xz`（22 条目）逐项清点：

1. 无 `tests/`、`test/` 目录
2. 无 `Makefile` / `Makefile.am` / `configure` / `configure.ac` / `CMakeLists.txt` / `meson.build` / `setup.py`
3. 无 `TESTS` / `check_PROGRAMS` / `ctest` / `pytest` 注册
4. `debian/rules` 仅为 `dh` 空规则（无 `override_dh_auto_test`）
5. 交付物为 3 个 `#!/bin/sh` 钩子 + 1 个 systemd link + 4 个接口配置示例，均为静态文本，无可执行测试入口

因此 `build()` 中无上游测试可运行，`test_package/MANIFEST.yml` 声明
`upstream_tests_exist: false` + `upstream_test_total: 0`（`manual_audit`），
`HMBS_UPSTREAM_TEST_RESULT` 输出 `status: "no_tests"`。

## 消费者测试（test_package）

`test_package/test_ifenslave.sh` 对已安装的 `bin/` 做 6 个确定性场景（不触碰 `/sys`、不调用 `ip`/`ifquery`、无需 root）：

1. 3 个钩子存在且可执行
2. 首行均为 `#!/bin/sh`
3. `sh -n` 语法检查通过（3 个文件）
4. `if-pre-up` 包含建 master 与 enslavement 核心函数（`add_master` + `enslave_slaves`）
5. `if-post-down` 包含释放 slave 与删除 bond 的 sysfs 契约（`bonding/slaves` + `ip link del`）
6. 示例与文档已随包安装（`examples/two_ethernet` + `README.Debian`）

每个场景恰增一次计数，无字符串数数、无算术修补，恒等式
`passed + failed == executed`、`executed <= discovered` 由脚本结构保证。
脚本末尾输出：

- `HMBS_TEST_PACKAGE_RESULT={"executed":true,...,"discovered":6,"passedCount":6}`
- `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...,"discovered":0,...}`

## HarmonyOS 说明与限制

- 钩子依赖 Linux 专属运行时（`ifupdown` 环境变量 `$IFACE`/`$BOND_*`、`ip` 命令、`/sys/class/net/*/bonding/` sysfs、`/proc/net/dev`），HarmonyOS PC 无此栈，脚本在 OHOS 上不直接执行bond操作，仅做文本分发与静态校验
- 测试全程静态（存在性/shebang/`sh -n`/关键字/文档），在 Linux 与 OHOS 均可运行，无平台条件分支
- 适配路径：路径 A（基础适配）

## 验证

本轮仅完成未提交工作树，按任务守则不做本地 `conan create`（真机预检由 HMBS 后台执行）。
待真机 evidence 轮按预检日志回填 PR 正文通过率表格。

## 交付物

- `archives/i/ifenslave/2.14/conanfile.py`
- `archives/i/ifenslave/2.14/conandata.yml`
- `archives/i/ifenslave/2.14/manifest.yaml`
- `archives/i/ifenslave/2.14/notes.md`（本文件）
- `archives/i/ifenslave/2.14/test_package/conanfile.py`
- `archives/i/ifenslave/2.14/test_package/MANIFEST.yml`
- `archives/i/ifenslave/2.14/test_package/test_ifenslave.sh`
- `archives/i/ifenslave/commands.json`
- `archives/i/ifenslave/README.md`
- `archives/i/ifenslave/manifest.yaml`
