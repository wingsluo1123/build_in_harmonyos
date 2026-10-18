# notes.md for mfoc 0.10.7-git20180724
# 申请人：sheepss，队伍：来都来了

## 上游信息
- 名称：mfoc (Mifare Classic Offline Cracker)
- 版本：0.10.7-git20180724 (master snapshot ba072f1, 2018-07-24)
- 主页：https://github.com/nfc-tools/mfoc
- 源码：https://github.com/nfc-tools/mfoc/archive/ba072f16f6b2a655d51da2171ecfb83e26c0ef58.tar.gz
- sha256：e9e01a38896d1b8dbff591cc2f39236d91b4995ea52abb63d0b7fe02aa8ab4bb (本地实测 38779 字节)
- 构建系统：Autotools (configure.ac + src/Makefile.am)
- 依赖：libnfc >= 1.7.0 (本配方使用 libnfc/1.8.0，已在制品仓)
- 类型：application (仅 bin/mfoc + man)，需 commands.json

## 上游测试清点
- configure.ac：AC_INIT/AM_INIT_AUTOMAKE/PKG_CHECK_MODULES，无测试宏
- Makefile.am：SUBDIRS = src，无 TESTS/check_PROGRAMS
- src/Makefile.am：bin_PROGRAMS = mfoc，无 TESTS/check_PROGRAMS
- 全树无 tests/、test/ 目录，无 gtest/pytest 用例
- make check 为 automake 默认空目标，0 用例
- 结论：upstream_tests_exist: false，test_package/MANIFEST.yml 已声明审计

## 适配要点
- GitHub 归档无 configure，需 autoreconf -fi，tool_requires automake/1.18 + libtool/2.5.4.1 (E178，同 bwm-ng/apertium)
- 不传 --build/--host (R15)，改由 _apply_e007 修 config.guess/config.sub
- configure 的 umask 077 改 022 (E114，HMDFS)，TMPDIR/SHELL 按 HMBS 注入复用
- PKG_CONFIG_PATH/CPPFLAGS/LDFLAGS/LIBS 注入 libnfc 路径 (同 libnfc 配方模式)
- test_package：test.sh 跑 `mfoc -h` (exit 0 + Usage + 0.10.7) 与无参负向对照 (缺 -O 必失败，证伪 harness)
- HMBS 标记：build() 与 test() 均输出 HMBS_UPSTREAM_TEST_RESULT(no_tests/0) 与 HMBS_TEST_PACKAGE_RESULT(discovered=1)

## 验证结果
- 在 HarmonyOS aarch64 环境实测 (以真机预检日志为准)
- 上游测试：0 用例 (确无套件)
- 新增测试：test.sh 1 用例 (help + 负向对照)

## 2026-10-15 真机修复 (config.guess 无法识别 HarmonyOS)
- 现象：conan create 在 autoreconf 后 `config.guess: unable to guess system type`
  (UNAME_SYSTEM="HarmonyOS")，`configure: error: cannot guess build type`。
- 根因：旧 _patch_config_guess_python 对 HarmonyOS 分支是 `pass` 空操作，
  且 generate() 剥掉 --build/--host 后 configure 仍走 guess 路径。
- 修复：generate() 按 arch 显式追加 `--build=<arch>-unknown-linux-gnu`
  与同值 `--host` 绕过猜测；_patch 对全树 config.guess 在 UNAME 赋值后
  插入 HarmonyOS|HongMeng*→Linux 归一化兜底；config.sub 不再做破坏性替换。

## 2026-10-15 真机修复 (test_package Error 127)
- 现象：conan create 在 test 阶段 `Error 127 while executing`，
  `/bin/sh test.sh "<pkg>/bin/mfoc"` 在打印 `[test] mfoc -h` 后中止，
  `HMBS_TEST_PACKAGE_RESULT={passed:false, discovered:1, passedCount:0}`。
- 根因（双缺陷，均在测试接入层，与 mfoc 二进制无关）：
  1) 模板注释已警示 OHOS `/system/bin/sh` (mksh) 不能执行 ELF（127），
     但 conanfile 取 `CONFIG_SHELL`（真机被注入为 `/bin/sh`）运行 test.sh，
     脚本内 `"${MFOC_BIN}" -h` 在该 shell 下 127；
  2) test.sh 用 `set -eu`，`mfoc -h` 的非零退出在 `rc=$?` 捕获前直接中止脚本，
     丢失诊断且跳过断言（证伪与非空检查 points 均未执行）。
- 修复：
  1) conanfile 新增 shell 优选：`/data/service/hnp/bin/bash` 存在可执行则优先，
     否则回退 CONFIG_SHELL/SHELL//bin/sh，并记录所选 shell；
  2) test.sh 改 `set -u`（去 `-e`），两次二进制调用均 `set +e` 包裹 + 显式 rc 捕获，
     失败时打印 LD_LIBRARY_PATH / ls -l / file / ldd 诊断；
  3) 绝对路径 bin 用 `test -x` 判定（替代 `command -v` 绝对路径的未定义行为），
     `-h` 输出增加非空校验；conanfile 用绝对 test.sh 路径调用，不再依赖 cwd。
- 上游审计结论不变：确无测试套件（no_tests/0）；test_package 仍为单用例
  (`mfoc -h` 断言 Usage + 0.10.7，非空校验；无参负向对照必失败）。

## 2026-10-16 真机修复 (libltdl.so.7 运行时缺失)
- 前次对比：上轮改测试接入层（hnp bash + 去 set -e）已生效——本轮日志显示
  测试确用 `/data/service/hnp/bin/bash` 运行并输出真实诊断，而非原样重复失败。
- 现象：`[test] mfoc -h` 报 `exit 127`，
  `Error loading shared library libltdl.so.7: (needed by .../p/bin/mfoc)`；
  当时 `LD_LIBRARY_PATH` 仅含 libusb 包 lib dir + /usr/local/lib + magic-cli，
  无 libtool/libnfc 的 lib dir。`file` 确认产物为 musl aarch64 动态 PIE。
- 根因：制品仓 libnfc/1.8.0 为静态库；generate() 全上下文注入把 libtool
  构建依赖的 `-lltdl` 带进链接（构建期 -L 能找到故链接成功），但
  VirtualRunEnv 只把 host 依赖带进 conanrun，运行时 loader 找不到
  libltdl.so.7。缺的是运行时依赖声明，不是测试脚本问题。
- 修复（与上轮不同策略：改配方依赖而非测试脚本）：
  requirements() 新增 host `requires("libtool/2.5.4.1")`（保留原
  tool_requires 供 autoreconf 使用），使其 libdir 进入 conanrun
  LD_LIBRARY_PATH；manifest.yaml dependencies 同步记录。

## 2026-10-16 真机修复 (tar fork OOM)
- 现象：预检 compile 阶段 tar (child): Cannot fork: Out of memory，tar Child returned status 2，上游测试 0/0/0。
- 定位：mfoc 源码仅 38779 字节，tar 包本身极小，非归档损坏（sha256 校验通过且历史轮可解包）；失败点为解包子进程 fork 失败，属共享真机全局内存压力下的偶发资源故障，同类见 cpluff/0.2.0 峰值资源被终止。
- 修复（最小资源加固，不碰测试口径）：generate() 追加 --disable-dependency-tracking 降低 IO 开销；extra_cflags 追加 -g0 -Os 去调试符号降峰值内存；extra_ldflags 追加 -Wl,--strip-debug；保持 make -j1 与 make check 全量不变。

## 2026-10-17 CI修复 (autoreconf EAGAIN间歇失败，同指纹第2轮换策略)
- 前次对比：上轮采取零修改等待基础设施恢复策略，本轮同构建#96090同错误重复出现，说明单纯等待未推进，必须换配方侧韧性策略。
- 现象：CI-031上generate成功后首条autoreconf即ConanException/Error Errno 11，无子命令输出；真机同HEAD可通过。
- 根因：共享Worker进程/内存压力下fork()被拒(EAGAIN)，autoreconf自举链最先受害；mfoc仅提供git快照无预生成configure，无法移除自举(见DRAFT-11327边界)。
- 修复(与上轮不同)：build()中autoreconf加3次瞬时资源失败重试(匹配Errno 11/cant-fork/try again子串，20s*attempt冷却)，成功路径命令与参数不变，保持make -j1与make check不变。
