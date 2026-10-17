# erlang 28.5.0.7 适配笔记

## 编译环境
- 构建系统: custom（上游自带手写顶层 `configure` + `otp_build` 递归 make 体系，非单一 autotools/CMake 工程）
- 编译日期: 2026-10-13
- 编译器: clang 15 / clang++
- 目标三元组: `aarch64-unknown-linux-ohos`（OHOS profile，`os=OHOS os.version=6.0 arch=armv8`）
- 状态: built（`conan create` 本地 rc=0，test_package 15/15 断言通过）

## 编译步骤

```bash
# 配方等价命令（conanfile.py 内即此三步，不套 AutotoolsToolchain）
export CC=clang CXX=clang++
export CPPFLAGS="-I<openssl>/include -I<zlib>/include -I<ncurses>/include"
export LDFLAGS="-L<openssl>/lib -L<zlib>/lib -L<ncurses>/lib"
export CONFIG_SHELL=/data/service/hnp/bin/bash SHELL=/data/service/hnp/bin/bash LC_ALL=C
./configure --prefix=<stage> \
  --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos \
  --without-wx --without-odbc --without-javac \
  --with-ssl=<openssl> --with-ssl-incl=<openssl>
make -j8 --jobserver-style=pipe
make install
```

`--jobserver-style=pipe` 是必需项：OHOS 无 `mkfifo(1)`，GNU make 默认的 FIFO jobserver 建不起来，
递归 make 会静默退化成 `-j1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `configure` 在 `erts` 阶段行为异常/失败 | OHOS `/system/bin/sh`(mksh) 承载不了 autoconf 脚本 | 注入 `CONFIG_SHELL`/`SHELL=/data/service/hnp/bin/bash`（configure 自举重入 bash，递归 make 继承） |
| 2 | `aarch64-unknown-linux-ohos` 不被接受 | 自带 `config.sub` 未登记 ohos | 补 `ohos*` OS 与 `linux-ohos*-` 内核模式（树内 3 份 config.sub） |
| 3 | autoconf 辅助脚本建的临时目录不可写 | 脚本用 `umask 077` | 统一改 `umask 022`（13 个脚本） |
| 4 | `configure: error: No curses library functions found` | 探测只找 `tinfo/ncurses/curses/termcap/termlib`，OHOS 侧是宽字符归档 `libncursesw.a` | `termcap_libs` 增加 `ncursesw` |
| 5 | `call to undeclared function 'gethostid'`（erl_interface） | OHOS musl 无 `gethostid()` | `ei_connect.c` 在 `__OHOS__` 下 `s.hid = 0`（上游已有 Android/Haiku 分支） |
| 6 | `utils.c` 编译缺 `mallopt()` 原型 | 原型在 `<malloc.h>` | 条件编译加入 `__OHOS__` |
| 7 | `inet` 驱动打警告 `uname: unexpected release 'HongMeng Kernel 1.12.0'` | `uname()` 返回厂商内核串，不符合 `%u.%u` | `__OHOS__` 下按"现代内核（SO_BSDCOMPAT 已废弃）"处理，不打警告 |
| 8 | `ts:install` / `make release_tests` 报 `cannot guess build type` | 自带 `config.guess` 识别 `Linux` 但不识别 `HarmonyOS`（`uname -s` = HarmonyOS） | `config.guess` 增加 `HarmonyOS/OpenHarmony/OHOS` 分支输出 `<arch>-unknown-linux-ohos` |
| 9 | 递归 make 退化为 `-j1` | OHOS 无 `mkfifo` | `make --jobserver-style=pipe`（GNU make ≥ 4.4） |
| 10 | 上游测试 harness 里 6+ 例 `peer:start_it` / `run_on_shielded_node` 失败 | HMDFS `chmod` 不生效 → `~/.erlang.cookie` 过不了 auth owner-only 校验 → 节点间握手失败（`net_adm:ping` = pang，但 epmd 与裸 TCP 正常） | 用 `-setcookie`/`ERL_AFLAGS` 显式给 cookie；需要第二节点的用例按平台边界归因（详见 learninglog/reports/upstream-tests.md） |
| 11 | conan 配方 API 连撞 3 处 | 2.29.1 与旧经验/文档不一致 | `apply_conandata_patches(self)`（无 `base_path`）；`self.run(env=...)` 只接受 env 文件列表；变量注入用 `Environment(...).vars(self, scope="build").apply()` |

## 源码修改

7 个 per-file 补丁（`patches/`，与 `conandata.yml` 逐条对应，全部以 tar 解压的 pristine 树为基准生成）：

| 补丁 | 覆盖文件数 | 内容 |
|---|---|---|
| 0001-config-sub-ohos.patch | 3 | `ohos*` OS + `linux-ohos*-` 内核模式（make/erts/common_test 三份 config.sub） |
| 0002-configure-umask-022.patch | 13 | autoconf 辅助脚本 `umask 077`→`022`（含 3 份 config.guess） |
| 0003-erts-termcap-ncursesw.patch | 2 | `termcap_libs` 增加 `ncursesw`（configure + configure.ac） |
| 0004-erl-interface-gethostid-ohos.patch | 1 | `__OHOS__` 下跳过 `gethostid()` |
| 0005-erts-mallopt-ohos.patch | 1 | `__OHOS__` 下纳入 `HAVE_MALLOC_H` 分支 |
| 0006-erts-inet-uname-ohos.patch | 1 | `__OHOS__` 下厂商内核串按现代内核处理 |
| 0007-config-guess-ohos.patch | 3 | `config.guess` 识别 HarmonyOS uname → `<arch>-unknown-linux-ohos` |

上游源码语义未做任何裁剪（otp 核心 application 全开）；`wx`/`odbc`/`jinterface` 三个依赖 GUI 工具包/unixODBC/Java
编译器的 application 以 `--without-wx --without-odbc --without-javac` 显式关闭（OHOS PC 不可达）。

## 依赖版本

- `openssl/3.5.7`（crypto NIF）、`zlib/1.3.1`（zlib NIF）、`ncurses/6.5`（erl 交互式终端）
- 三者均已在 ohpcd 制品仓发布（实测 `conan download … -r=ohpcd --only-recipe` 成功）

## 验证结果

```bash
# ① VM 自举
erl -noshell -eval 'io:format("~s~n",[erlang:system_info(otp_release)]),halt().'
28
# ② conan create（OHOS profile）rc=0；test_package
======== Testing the package: Executing test ========
assertions=15 failures=0
consumer test PASSED
# ③ 上游 release_tests（otp_build tests + ts:install + ts:run）
compiler: 5536 ok,   6 failed,  12 skipped of 5554
kernel:     758 ok, 494 failed, 581 skipped of 1833
stdlib:    1921 ok, 104 failed, 468 skipped of 2493
system:      79 ok,  26 failed,   7 skipped of  112
合计:      8294 ok, 630 failed, 1068 skipped of 9992   # 口径2 执行分母 92.94%；口径3 99.01%
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 直接驱动 configure/make/make install；`Environment.vars(scope="build").apply()` 注入环境 |
| `conandata.yml` | 源码 URL/sha256（`OTP-28.5.0.7`，双源互核 ddf17db6…93）+ 7 条 patch 声明 |
| `patches/` | 7 个 per-file 补丁 |
| `test_package/` | `conanfile.py` + `test.sh`（15 条断言）+ `MANIFEST.yml`（上游测试声明） |
| `manifest.yaml` / `notes.md` | 版本级元数据与适配笔记 |

## 注意事项

- **CI 超时**：OTP 全量自举 + 安装 + test_package 远超默认 3600s（本机 aarch64 OHOS PC、-j8、HMDFS 实测 9761s），
  已在 `ci/config/build_timeouts.txt` 追加 `erlang/28.5.0.7 14700`（= 实测 × 1.5）。
- **平台边界**：HMDFS 不能表达 owner-only 权限，导致 Erlang distribution 的节点间握手不可用；需要第二节点/受保护节点的
  上游用例（`peer`/`global`/`erl_distribution`/`slave`/`io_proto` stdin 节点等）按环境归因，不计入移植缺陷。
- `os:type()` 返回 `{unix,harmonyos}` 由 erts 的 `os_flavor()` 运行时 `uname()` 决定，编译期无需改动。
- `escript` 脚本需带 `#!` 头（无头脚本上游解析器会按"跳过首行"处理）；`-eval` 表达式中 `=<<` 需写成 `= <<`（Erlang 词法）。
