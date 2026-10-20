# sniffit 0.7 适配笔记

## 基本信息

- 上游：https://github.com/resurrecting-open-source-projects/sniffit（历史抓包与监控工具，原作者 Brecht Claerhout 1996–1998，社区复活维护）
- 版本：0.7（tag `sniffit-0.7`，2025-09-23；修复 GCC 14/15 构建告警、SunOS NETDEV_NR、构建系统改进）
- 源码包：`https://github.com/resurrecting-open-source-projects/sniffit/archive/refs/tags/sniffit-0.7.tar.gz`
- sha256：`9a8c3472414e105479296b6ca83be419cfd37551982e6ddaca34dfa4916a4c47`（与 FreeBSD ports 对同 tag 的 GH0 包 distinfo 交叉核对：TIMESTAMP 1758606858 / SIZE 59904）
- 构建系统：autotools（`configure.ac` + 顶层/`src/Makefile.am`，automake foreign；`sbin_PROGRAMS = sniffit`）
- 许可证：BSD-3-Clause（`LICENSE` 随包交付到 `licenses/`）
- 状态：built（首轮仅完成未提交工作树，待 HMBS 真机 rule4 门禁）
- 编译器：clang（HarmonyOS PC 真机 `/data/service/hnp/bin/clang`，profile `ci/conan/profiles/ohos-aarch64`）

## 编译步骤

配方侧等价命令（`conan create` 实际执行）：

```sh
# 1) 上游源码包（官方 GitHub tag 快照）
tar -xzf sniffit-0.7.tar.gz && cd sniffit-0.7

# 2) 生成 config.h（配方 build() 内按 configure.ac 探针在 OHOS aarch64 下的
#    确定答案手写：HAVE_LIBNCURSES/HAVE_NCURSES_H/HAVE_SHMGET/HAVE_ATEXIT/
#    HAVE_SETSERVENT=1，short=2/long=8/int=4 即 USE_32_INT；信源见配方
#    _write_config_h() 注释。不在设备端跑 autoreconf，故不构建 m4）
#    策略切换说明见本文件问题 #9。

# 3) 直编（AutotoolsDeps/Toolchain 经 conanbuild 提供 libpcap/ncurses 的
#    -I/-L/-l 与 OHOS target/sysroot 标志；7 个 TU 取自 src/Makefile.am
#    SOURCES，sn_conn_desc.c 不在上游构建列表内，必须排除）
$CC $CPPFLAGS $CFLAGS -I<gen> -Isrc src/sn_packets.c src/sn_generation.c \
    src/sn_interface.c src/sn_cfgfile.c src/sn_logfile.c src/sn_resolv.c \
    src/sniffit.c $LDFLAGS $LIBS -lpcap -lncurses -o sniffit

# 4) 安装（配方 package() 直拷：bin/sniffit、man/*.5/*.8、LICENSE）
```

`configure` 探测关键点：`AC_CHECK_LIB(pcap, ...)` 缺失即 fatal（故必须 requires libpcap）；
`AC_CHECK_LIB(ncurses, ...)` + `AC_CHECK_HEADERS([ncurses.h])` 决定 `config.h` 的
`HAVE_LIBNCURSES`，进而决定 `src/sn_config.h` 是否保留 `INCLUDE_INTERFACE`
（ncurses 交互模式 `-i/-I` 与 `GENERATION`）。本配方固定 requires ncurses/6.6，
使该特性集确定。

打包落点：

| 路径 | 内容 |
|------|------|
| `<pkg>/bin/sniffit` | 主程序（`sbin_PROGRAMS` 经 toolchain `--sbindir` 落入 `bin/`；若落入 `sbin/` 则镜像到 `bin/`） |
| `<pkg>/share/man/man5/sniffit.5`、`man8/sniffit.8` | 手册页（上游 `man_MANS`） |
| `<pkg>/licenses/LICENSE` | 上游 BSD-3-Clause 原文 |

## 依赖版本

- `libpcap/1.10.6#e4d43bf9a29fdaabd60dee919243c781`（requires，抓包；configure 硬性要求；RREV-pin 到 ohpcd cmake 配方，见问题 #10；裸引用会在预检被 conancenter 遮蔽）
- `ncurses/6.6`（requires，交互界面 `-i/-I`；上游可选但本配方固定以保证确定性）
- 无 build_requirements（策略见 #9：直编后不再需要 automake/autoconf/libtool，不进包；此前为 E178 引导所需）
- 运行时仅需 OHOS libc（musl）与上述依赖的静态/动态闭包；无其他主机依赖（R36 对下游无约束）

## 上游测试清点（R51）

**上游测试程序数：0。** 四条清点证据（均在 sniffit-0.7 发布树内）：

1. 发布树文件清单：根 `Makefile.am` 仅 `SUBDIRS = src` + `man_MANS`；`src/Makefile.am`
   仅 `sbin_PROGRAMS = sniffit` + 源文件列表；`src/` 下 30 个文件全为 `sn_*.c/.h`、
   `sniffit.c/.h` 与两个 `.plug` 插件示例，无 `tests/`、`test/` 目录，
   无 `*test*`/`*check*` 命名文件。
2. `grep -rn "TESTS\|check_PROGRAMS\|enable_testing\|add_test" configure.ac Makefile.am src/Makefile.am`
   无命中——automake 无任何测试注册。
3. `configure.ac` 的测试相关内容仅为特性探测（`AC_CHECK_LIB/HEADERS/FUNCS/SIZEOF`），
   无测试开关；`make check` 在该树上只有 automake 默认空目标。
4. Debian/Ubuntu 打包层（`sniffit_0.7-1build1.debian.tar.xz`）只做打包冒烟，
   非上游测试套件；上游 `examples/`、`docs/`、`man/` 均为用法文档与配置样例。

因此 `conanfile.py:build()` 里**不执行** `make check`（写了只会得到假的红或空转），
`test_package/MANIFEST.yml` 以 `upstream_tests_exist: false` + 完整审计 +
`upstream_test_total: 0` / `upstream_test_count_method: autotools_tests` 如实声明。
缺失的上游套件由 test_package 的真消费者测试补足（R34：必须真正执行被测二进制
并断言其真实输出，不允许只打印字符串；含版本契约精确匹配与负向对照，防
loader 误报与空跑误报）。

五维测试数字（待真机预检回填实测）：

| 维度 | 数量 | 口径 |
|------|------|------|
| 静态 | 0 | 上游无测试注册可枚举（见上四条） |
| 注册 | 5 | `test_package/MANIFEST.yml` 的 `assertion_count: 5`，对应 `test_sniffit.sh` 用例 1..5 |
| 实测 | 待真机回填 | 真机 `conan create` 触发的 test_package 实际执行并通过的断言数 |
| 跳过 | 0 | 无按平台跳过的断言（用例 4 对 root/非 root 双语境均不断言跳过） |
| 失败 | 0 | 目标：无失败断言 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub tag 快照无 `configure`，`Autotools.configure()` 无法启动 | tag 归档是 git 快照，只带 `configure.ac/Makefile.am/autogen.sh` | `build()` 先 `autoreconf --install --verbose`（E178；`build_requirements` 拉 automake/autoconf/libtool） |
| 2 | 新生成的 `config.guess/config.sub` 不认识 HarmonyOS | automake 自带三元组表无 ohos | 构建时内联 Python 补丁加 `*:HarmonyOS` 分支与 `linux-ohos` 三元组（E007；arp-scan 同款，不进 `patches/`，因改的是生成文件） |
| 3 | `configure` 在 HMDFS 下建临时目录后失败（同族先例） | 生成的 `configure` 用 `umask 077` 建 scratch 目录 | 生成后把 `umask 077` 放宽为 `umask 022`（E011；改的是构建时生成物，非上游源码） |
| 4 | `sniffit` 无 `--version`，冒烟测试无从下手 | 上游 CLI 只认 `-v`（版本）与 `quit()` 用法函数 | 消费者测试用 `sniffit -v`（`quit()` 前即打印 `Sniffit Version 0.7` 并 `exit(0)`，无需 root）做版本契约；裸调与非法主机名做双语境/负向对照 |
| 5 | `sniffit` 多数路径 `exit(0)`（用法函数），负向对照难做 | 未知选项/`-L` 无 `-c` 等全部进 `quit()`（exit 0） | 负向用例选 `-t <非法主机>`：root 下 `getaddrbyname` 报 `Non existing host!` exit 1；非 root 下先触发 `You should be root` exit 1——两种都是 exit 非零的真实应用失败 |
| 6 | 二进制可能落进 `sbin/` 而测试只看 `bin/` | 上游是 `sbin_PROGRAMS` | `package()` 在 `sbin/sniffit` 存在而 `bin/sniffit` 缺失时镜像一份；`package_info` 保持 `bindirs = ["bin"]`（R38 工具约定） |
| 7 | 真机预检在 m4/1.4.19 `configure[139]` 报 `/data/service/hnp/bin/bash: inaccessible`（Error 127），本包后续 `configure` 同理 | 仓库 profile 把 SHELL/CONFIG_SHELL 钉死到该 hnp bash，部分 HMBS 主机上不可执行；HMBS 注入 SHELL=/bin/sh（capabilities shell=/bin/sh） | bwm/0.6.3 同款加固：`generate()` 存 build 域 `sniffit_hmos_fix` 脚本强制 SHELL/CONFIG_SHELL 到可用 shell + 可写 TMPDIR + 编译器回退，`build()/package()` 在 conanbuild.sh 生效后内联重导出并经可用 shell 显式调 configure/make（不用 Autotools.configure()/install()），失败时转储 config.log |
| 8 | 同一 m4 失败第二轮复现（工作树已含 #7 加固，预检仍卡 m4 `configure[139]` Error 127，本包构建未被执行到） | 与 #7 不同：失败点在三方依赖构建（conancenter 的 m4/1.4.19，直调 `autotools.configure()`），Conan 先构建依赖，本包 `generate()` 的 env 脚本对其无影响；且 m4/autoconf/flex/bison/libpcap 均解析到 conancenter 配方（首远端优先），ohpcd 的适配版 m4（_select_shell）未被采用；runner（47.122.125.180）缺 profile 钉死的 hnp bash | 本轮不重复加固、不改配方逻辑：保留 #7（本包 configure 仍需要它），判定为真机环境/工具链漂移，请后端恢复该 runner 的 `/data/service/hnp/bin/bash` 或调整 profile/远端优先级；链分析见本条，下轮以新 runner 或新远端顺序复检 |
| 9 | 上轮 #7 加固连续三轮无效：预检仍卡 conancenter m4/1.4.19 `configure[139]` Error 127，本包构建从未被执行到 | #7 根因假设（本包 SHELL 加固可带活构建）对依赖构建不成立：Conan 先构建 tool_requires 依赖，m4 的 configure 由其自身配方的 `autotools.configure()` 经 profile 的 stale CONFIG_SHELL 重 exec，本包 `generate()` 的 `sniffit_hmos_fix` 脚本只作用于本包构建域；改本包 shell 逻辑属于同一根因假设的重复，不可能触及 m4。证据：三轮日志失败点均为 m4 构建，本包 configure 日志从未出现 | 改走不同实现路线（aldo/0.7.8 vendoring 先例的变体）：删掉 `automake/autoconf/libtool` tool_requires，`build()` 直编 `src/Makefile.am` SOURCES 的 7 个 TU（排除不在列表的 `sn_conn_desc.c`），`config.h` 按 `configure.ac` 探针的 OHOS 确定答案在构建时生成（`_write_config_h`），`package()` 直拷二进制/手册页；m4 构建边被消除，hnp-bash 缺失的 runner 上也不再经过该故障点。待本轮真机复检验证 |
| 10 | 直编后预检仍从源码构建 conancenter m4/1.4.19（`configure[139]` Error 127，package ID `579a4b17` 与 alberta 轮次完全一致；本包已无任何 tool_requires，ohpcd 侧 libpcap（cmake）与 ncurses（无 tool_requires）配方均干净） | 残留边来自依赖：裸 `libpcap/1.10.6` 在预检按远端顺序先命中 conancenter（CCI 有 1.10.6 而无 ncurses/6.6，故 ncurses 无辜），CCI autotools 版 libpcap 的 `tool_requires(bison/flex)` → CCI bison `requires(m4/1.4.19)` → CCI m4 源码构建重 exec 缺失的 hnp bash。证据：CCI 三配方源码、mgen/5.02.c5.1.1 同指纹 `libpcap -> bison/flex -> m4` 记录、conan.io 版本页 | 与 mgen 的删依赖不同（sniffit 对 libpcap 是 configure 致命依赖，不可删）：沿 abuild-sudo/openssl、alberta/libtirpc、debsig-verify/ncurses 先例做 RREV-pin——`requires("libpcap/1.10.6#e4d43bf9a29fdaabd60dee919243c781")`（lltdscan 2026-10-10 以 sanctioned 的 `conan download --only-recipe` 实测 ohpcd 单一 revision，armv8/Release 二进制可取），ncurses/6.6 保持裸引用；manifest 同步。待本轮真机复检验证 |

## 源码修改

无 `patches/` 补丁。OHOS 相关处理为构建时生成 `config.h`
（`configure.ac` 探针在 OHOS aarch64 下的确定答案，见配方 `_write_config_h`）
与直编 7 个上游 TU，不改上游源码，不引入 `__OHOS__` 平台宏（R8/PF5 合规）。
`config.h` 写到构建目录隔离区，不污染源码树（R6 合规）。E007/E011 的
config.guess/config.sub 与 umask 处理随 autoreconf 流程一并移除（不再有
configure 产物需要打补丁）。

## 验证结果

待 HMBS 真机预检回填（首轮仅完成未提交工作树）：

- 编译状态：待真机 `conan create` 实测
- 上游测试用例通过率：0/0（上游无测试套件，`HMBS_UPSTREAM_TEST_RESULT status=no_tests`）
- 新增测试用例通过率：待真机回填（设计 5/5，用例：二进制在位、`-v` 退出码、`-v` 版本契约、裸调用法/权限双语境、非法主机负向对照）

## 交付物

| 文件 | 说明 |
|------|------|
| `<pkg>/bin/sniffit` | 抓包主程序（TCP/UDP/ICMP，libpcap 驱动；ncurses 交互模式可用） |
| `<pkg>/share/man/...` | 上游手册页（sniffit.5 配置格式、sniffit.8 命令参考） |
| `<pkg>/licenses/LICENSE` | BSD-3-Clause 原文 |

## 注意事项

1. 抓包运行需要 root 与可用网卡（`pcap_open_live`）；消费者测试只覆盖**不抓包**的
   CLI 契约（`-v`/用法/参数校验），不打开任何网卡，CI/真机无特权也可通过。
2. `sniffit -v` 的输出含编译日期时间（`Binary build __DATE__ __TIME__`），测试只断言
   `Sniffit Version 0.7` 前缀，不锁定日期行。
3. 若后续上游引入 `make check`，`build()` 与 `MANIFEST.yml` 需同步回填。

**编译结束**：2026-10-12（工作树，未提交）
**最终状态**：built
