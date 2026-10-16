# joyutils 1.8.1 适配笔记

## 上游信息
- 上游：`https://sourceforge.net/projects/linuxconsole`（Linux Console Project）
- 源码包：`linuxconsoletools-1.8.1.tar.bz2`（官方 SourceForge 发布）
- 下载地址：`https://downloads.sourceforge.net/project/linuxconsole/linuxconsoletools-1.8.1.tar.bz2`
- SHA256：`4da29745c782b7db18f5f37c49e77bf163121dd3761e2fc7636fa0cbf35c2456`
  - 已用 Python 下载 53715 字节实测验证，与 Buildroot `linuxconsoletools.hash`、Void Linux 模板 checksum 一致
- 许可证：GPL-2.0-only（COPYING）
- 申请人：`gcw_uQ09W7jl`，队伍名称：`干`

## 构建系统
- 纯 Makefile（顶层 Makefile 委托 `utils/` 与 `docs/`；无 configure、无 CMake、无 meson）
- 关键变量：`DISABLE_INPUTATTACH`、`DISABLE_JOYSTICK`、`DISABLE_FORCEFEEDBACK`、`PREFIX`、`DESTDIR`、`SYSTEMD_SUPPORT`
- 本配方仅构建摇杆工具子集：`make -j1 CC=<toolchain> DISABLE_INPUTATTACH=1 DISABLE_FORCEFEEDBACK=1`
  - 关闭 `inputattach`（串口旧设备）与 force-feedback（含需 SDL2 的 `ffmvforce`），从而零 Conan 依赖（R36 无阻塞）
  - 保留 `jstest jscal jscal-restore jscal-store evdev-joystick`（joyutils 范畴）
  - 不开 `SYSTEMD_SUPPORT`（无需 libsystemd）
- 安装：不再调用 `make install`（真机 `install -d <pkg>/bin` 在 `utils/Makefile:106` 报 Error 64，OHOS/toybox install 与 GNU 语义不兼容 E098/E188）。`package()` 用 Python `makedirs+copy2+chmod` 复刻 `utils/Makefile` 与 `docs/Makefile` 的安装布局（PREFIX 为空口径）：`bin/`（5 个程序，755）、`share/joystick/`（extract/filter/ident，755）、`lib/udev/` + `lib/udev/rules.d/80-stelladaptor-joystick.rules`（模板中 `@@PREFIX@@` 置空，与上游 `sed "s^@@PREFIX@@^^g"` 一致，644）、`share/man/man1/`（5 个 man 页，644）。`lib/udev/` 在 OHOS 下无害、仅为与上游一致而保留。
- 编译器取自 `tools.build:compiler_executables`（R33：不裸用 shell 的 CC/CFLAGS）
- 平台判断统一用 `in ("Linux", "OHOS")`（R32）
- 无补丁（`patches: []`）

## 上游测试审计（结论：无测试）
- 顶层仅 `COPYING/Makefile/NEWS/README + utils/ + docs/`，无 `tests/`、`test/`、` *_test.*`
- 顶层 Makefile 仅 `all/compile/clean/distclean/install/dist`，无 `check/test`
- `utils/Makefile` 仅 `compile/clean/distclean/install`，无 `check_PROGRAMS/TESTS/test`
- `docs/Makefile` 仅安装 man 页，无测试目标
- Alpine 构建日志明示 `APKBUILD does not run any tests / does not have a testsuite`
- 因此 `test_package/MANIFEST.yml` 记 `upstream_tests_exist: false`、`upstream_test_total: 0`、`method: autotools_tests`（make check 口径空集），`status: no_tests`

## test_package 设计（4 用例，均无需摇杆硬件）
- `test_joyutils.sh`（`sh`，`set -u`，TMPDIR 优先 HMBS 注入）：
  1. `jstest --help` 应退出 1 且含 `Usage: jstest`、输出非空
  2. `jscal -h` 应退出 0 且含 `Usage: jscal`、输出非空
  3. 无参 `jscal` 应退出 1 且含 `Usage: jscal`、输出非空
  4. 负控：`jstest /dev/nonexistent-joytest-xyz` 必须失败（证伪空输出全过；参照 toybox tar 空 fixture 教训）
- `conanfile.py` 解析确定性 `RESULT: P passed, F failed` 尾行生成 `HMBS_TEST_PACKAGE_RESULT`（discovered=passed+failed）；同步重发 `HMBS_UPSTREAM_TEST_RESULT`（no_tests，0 计数，因主配方输出在 cache-hit 轮可能被跳过）
- OHOS 下对两二进制做可写 TMPDIR 拷贝 + `binary-sign-tool` 自签名（c10t 先例；HMDFS 只读与内核签名门禁）
- R34：真实执行包内二进制；R34 反向验证：删二进制即 `ConanException` 失败

## 验证结果
- 本轮为工作树准备轮（严禁 commit/push/PR），真机 rule4 预检由 HMBS 后台执行
- `manifest.yaml` 内 `test_results.status: pending`，待预检证据轮回填真实通过率
- 待确认项：OHOS 内核头是否提供 `linux/joystick.h`、`linux/input.h`；`evdev-joystick` 的 ioctl 路径在无硬件时仅编译期依赖头文件，运行期测试不触硬件

## 交付物
- `bin/jstest`、`bin/jscal`、`bin/jscal-store`、`bin/jscal-restore`、`bin/evdev-joystick`
- `share/joystick/extract filter ident`、`share/man`（docs）、`lib/udev/` 规则
- 工具包：`archives/j/joyutils/commands.json`（type tool，binary true）
