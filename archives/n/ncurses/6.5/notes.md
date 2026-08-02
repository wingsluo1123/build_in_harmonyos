# ncurses 6.5 适配笔记

## 当前策略

- 构建系统: autotools
- 交付方式: static-only
- 关键配置: `--without-shared --enable-widec --enable-overwrite --disable-stripping`
- 上游测试入口: `make -C test -j1 && make -C test check`

## B 路径证据

- Emacs 29.1 `configure` 在 OHOS runner 上已经进入编译器探测阶段，但因缺少 `tputs` 所在的 terminfo/curses 库失败。
- 远端 `ohpcd` 当前没有 `ncurses/*` 可解析 recipe，因此 Emacs batch 工具链需要先补 ncurses Conan 包。
- ncurses upstream `test/Makefile.in` 提供 `check::` 目标，用于逐个编译公开头文件；recipe 同时构建 `test/` 目录测试程序，保留上游测试证据。

## OHOS 注意事项

| 问题 | 处理 |
|---|---|
| `/tmp` 只读 | 设置 `TMPDIR` 到 runner 可写目录 |
| `config.status` 的 `umask 077` 临时目录不可写 | OHOS 下补丁改为 `umask 022`，保留 group/other 访问位 |
| 默认 `expr/sed` 是 toybox | 将 `$HOME/usr/local/bin` 前置到 `PATH`，优先使用 GNU coreutils/sed |
| `install -s` 调用 `strip` 权限失败 | configure 增加 `--disable-stripping` |
| 共享 ncurses 可能影响系统 shell | 禁用 shared，仅打包静态 wide-char 库 |

## 验证结果

- 远端 job: `ncurses-6.5-poc-20260803-003138`
- run id: `codex-a-6.5-ncurses-6.5-poc-20260803-003138-conan-20260803-014122-15073`
- 结果: L0 pass, L1 pass, L2 pass, L4 pass, L5 pass
- 上游测试: `make -C test -j1` 已构建 upstream test programs；`make -C test check` 已执行并完成 header compile checks，日志包含 `The test-programs are interactive`
- test_package: consumer probe 编译并运行 `setupterm/tigetstr/tputs`，随后运行 `TERM=xterm-256color tput colors >/dev/null`
- 负向测试: runner L1e 移走 `bin/`、`lib/`、`include/` 后确认测试依赖 ncurses 产物
- 注意: 本次为旧端口 `56267` 隔离 POC 证据；提交前如新端口恢复，应补新端口/正式 CI 证据
