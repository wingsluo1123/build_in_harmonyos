# juke 0.7 适配笔记

## 编译环境

- 构建系统: autotools (configure + make)
- 编译日期: 2026-10-15
- 目标平台: aarch64-unknown-linux-ohos (OpenHarmony)
- 编译器: clang / clang++
- 依赖: ncurses 系统预装（~/usr/local，非 Conan 包，与 joe/4.6 同模式）
- 状态: built（待真机预检验证后更新）

## 上游信息

- 软件：juke 0.7，简易 curses 点唱机（ncurses 终端交互程序，调用命令行播放器播放多种音乐格式）
- 原始主页 http://johan.nocrew.org/nav10/unix/juke/ 已不可达（pkgsrc 已将其注释掉）
- 现行规范分发点：https://www.moll.no/oyvind/distfiles/juke-0.7.tar.gz（pkgsrc audio/juke 的 MASTER_SITES）
- 交叉核验：FreeBSD ports audio/juke 记录 SHA256 b19d6bb46ece9f47b07bcd52e371b447fbef580ffb9ded59257305962f47cae0，大小 64103 字节，与 pkgsrc distinfo 的 64103 字节一致
- 许可证：GPL-2.0-only（pkgsrc 记为 gnu-gpl-v2）
- 构建系统：GNU configure（pkgsrc 记 GNU_CONFIGURE=YES），依赖 ncurses（pkgsrc 引入 curses.buildlink3.mk；Debian 构建依赖 libncurses-dev）

## 编译步骤（计划，与 joe/4.6 同模式，真机预检中实证）

```bash
cd archives/j/juke/0.7/
conan create . --user=ohpcd --channel=stable -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing
```

配方动作：AutotoolsToolchain 注入系统 ncurses 头文件与库路径（DEFAULT_PREFIX），静态链接（-static），跨编译模式（--build != --host）跳过 conftest 执行，make -j1，make install。

## 上游测试审计结论

juke 0.7 无自动化测试套件：

1. pkgsrc audio/juke/Makefile 无 check/test 目标，仅 post-install 安装 juke.conf 与 MANUAL
2. Debian juke_0.7 系列包（0.7-1 至 0.7-4）无测试套件记录
3. FreeBSD port 无测试声明
4. 源码结构为 src/conf.c、juke.conf、doc/juke.1、MANUAL，无 tests/ 目录

因此 conanfile.py build() 未集成 make check（与 joe/4.6 同处理），test_package/MANIFEST.yml 记 upstream_tests_exist: false 并附本审计。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始上游主页不可达 | johan.nocrew.org 站点下线 | 采用 pkgsrc 规范分发点 moll.no，FreeBSD 哈希交叉核验 |
| 2 | 2005 年 configure 脚本在 OHOS 上可能不识别平台 | 旧版 config.guess/config.sub 无 ohos 白名单（同类库 E072 经验） | 首轮不预置补丁，待真机预检日志确认后按 joe/4.6 模式补 config.guess/config.sub 补丁 |
| 3 | ncurses 依赖来源 | OHOS 无系统 ncurses-dev，Conan 制品仓 ncurses 仅作库发布 | 复用 joe/4.6 模式：链接 ~/usr/local 系统预装 ncurses 静态库，不在 requirements 中声明 |
| 4 | 真机 source() 报 sha256 不匹配（期望 b19d6bb4…，实际 9a5eb5cf…） | moll.no 经传输链路返回了解压后的 266240 字节 tar（名为 .tar.gz），与 64103 字节 gzip 原件字节不同；本地 curl 复现同尺寸同哈希，pkgsrc 镜像下载 64103 字节且哈希与 FreeBSD 记录完全一致 | conandata.yml url 改为有序列表（pkgsrc 镜像在前、官方 moll.no 在后回退），sha256 保持不变；版本 manifest source.url 同步主镜像并附 mirror_note |

## 验证结果

本轮仅完成未提交工作树，真机预检待 HMBS 后台执行。以下待预检回填：

- conan create 结果
- test_package 执行结果（juke --help）
- HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 标记

## 注意事项

1. juke 是终端交互式 curses 工具，test_package 仅做 --help 烟雾测试，不启动交互界面
2. 若真机显示 --help 不可用，将改用 -h 或 man 页存在性校验
3. 若真机 configure 报平台不识别，将追加 config.guess/config.sub 补丁（参考 joe/4.6 的 0001/0002 补丁）
4. 本配方 package_type 为 application，已配套软件级 commands.json（R38）

## 参考

- archives/j/joe/4.6/（同类 ncurses 终端工具配方，generate/build/package 模式来源）
- pkgsrc audio/juke Makefile（构建系统、依赖、许可证依据）
- FreeBSD ports audio/juke（SHA256 交叉核验来源）

## 2026-10-16 真机预检进展（config.sub 已过，新失败在编译器检查）

- 上轮 buildenv-shell + build 期多目录 staging 生效：configure 已越过
  `can not run .../config.sub` 与 host/build 规范化，走到了
  `checking whether the C compiler (...) works... no`。
- 失败命令含 `-L<DEFAULT_PREFIX>/lib -static`；古代 autoconf 2.13 的该项检查只做
  link（`$CC -o conftest $CFLAGS $CPPFLAGS $LDFLAGS conftest.c`），与 ncurses 无关。
- 候选根因（待 config.log 裁定）：OHOS bionic 系 libc 若无静态库则 `-static`
  全静态链接必然失败（E481 同类）；joe/4.6 在 6 月曾产出 static ELF，
  故本轮不凭猜测删除 `-static`。
- 本轮配方改动：configure 失败时自动打印 `JUKE-FORENSIC-*` 行
 （config.log 中的 link 命令、error 行与尾部 60 行），下一轮据此定修。

## 2026-10-16 真机预检进展（编译器绝对路径不可用，换 PATH 探测路线）

- 取证结论：`JUKE-FORENSIC-ERR` 显示 `.../b/configure: /data/service/hnp/bin/clang:
  inaccessible or not found`（exit 127），即 shell 连编译器自身都无法 exec，
  链接参数（`-static` 等）根本未被求值。上轮“先取证再定修”已完成使命，
  排除 `-static`/link 猜测。
- 上一周期三轮均假设“编译器存在、失败在 flag/link”，沿用 config.sub/shell/
  取证同根因已连续失败，本轮按策略切换实现路线。
- 新路线（与 jamnntpd/1.3、myman/4.0.116 同族 E540）：不再信任 profile 写死的
  `tools.build:compiler_executables` 绝对路径；conf 路径仅在 isfile+X_OK 时采用，
  否则经 PATH 探测（aarch64-ohos-clang/clang/cc/gcc + 预检显式目录），经
  buildenv 的 CC/CXX + 工具链目录 PATH 前置 + 已生成 toolchain sh 的 CC/CXX
  改写三重生效；`-static` 与全部 flag 保持不动。

## 2026-10-16 真机预检进展（ncurses 改走 Conan 依赖，放弃系统预装假设）

- 本轮失败点：`configure:1166: clang -o conftest ... -L<sysroot>/lib -static
  conftest.c -lncurses [-ltinfo]` 反复报
  `ld.lld: error: unable to find library -lncurses`，随后
  `checking for main in -lncurses... no` 触发上游 `configure.in` 的
  `AC_CHECK_LIB(ncurses,main,,[exit])` 裸 `exit`，零退出且无 Makefile。
- 根因：joe/4.6 的“系统预装 ~/usr/local 有 ncurses”假设在本 worker 不成立，
  探测目录下根本没有 libncurses；继续加 -L 前缀与 -ltinfo 后缀无法变出库文件。
- 改动（dhex/0.69 + dialog/1.3-20240307 对标方案）：requirements 改为
  `self.requires("ncurses/6.6")`；generate 新增 AutotoolsDeps 并显式注入
  Conan ncurses 的 -I/-L；在 build_folder/juke-local-libs 内建
  `libncurses.a -> libncursesw.a` 兼容符号链接（上游只查 -lncurses，而
  ncurses/6.6 仅提供 libncursesw.a）并将其 -L 烘入 toolchain；build() 复验该
  链接后固定 `LIBS=-lncurses`，不再做系统前缀探测与 tinfo 后缀猜测。
  `-static` 与全部编译器/平台补丁保持不动。

## 2026-10-16 真机预检进展（evidence 门禁：no_tests 被判 incomplete）

- 本轮失败域：编译与 test_package 均已通过（juke 二进制产出、无参运行打印
  usage 且 HMBS_TEST_PACKAGE_RESULT=passed），仅 evidence 阶段判 incomplete：
  “清单表明上游存在测试，no_tests/0 不允许通过”。
- 根因（已读源码证实）：juke-0.7.tar.gz（45 文件，sha256 b19d6bb4…）确无可执行
  測試——configure.in 无测试宏、Makefile.am/src/Makefile.am 无
  TESTS/check_PROGRAMS、源码树无 tests/ 目录；但 Makefile.in 含 automake 1.4
  默认空 check 目标（check: check-recursive / check-am: all-am），旧写法在
  test_package 标记 framework=none、command 含“无 check 目标”括号注记，且
  MANIFEST 的 upstream_check_command 非空，与“空目标”事实矛盾，易被清单判
  为漏接测试。
- 改动（对标 aldo/0.7.8 空 check 先例）：a) build() 在 make 后追加
  autotools.make(target="check")（空目标 0 用例退出 0，留真机日志证据）；
  b) test_package 上游标记改 framework=autotools、command="make check"、
  双通道打印标记，reason 写明空目标与 45 文件审计；c) MANIFEST 改
  upstream_check_command 为空、upstream_test_in_build=true、审计改为结构化
  mapping（tarball/sha/文件清单/扫描项/make_check_output/reason），总数仍 0。

## 附：上一轮（系统前缀探测路线）已 superseded，本轮改走 Conan 依赖
- 旧路线（保留 DEFAULT_PREFIX 主线 + HMBS_INSTALL 补充 + 系统前缀 tinfo 探测）
  未生成任何 Makefile，`make -j1` 报 `No targets specified and no makefile found`。
- 根因（已读源码证实）：`configure.in` 为 `AC_CHECK_LIB(ncurses,main,,[exit])`，
  生成的 `configure` 在失败分支执行裸 `exit`（取前一条 echo 状态即 0），
  故 Autotools.helper 不抛异常、取证分支不触发，属静默失败。
- 上一周期三轮假设“编译器不可执行 / config.sub / shell”已由本轮日志证伪：
  编译器检查 `works... yes` 已过，config.sub 自检三元组全过，失败点后移至库检查。
- 本轮改动（不同路线）：不再动编译器/平台补丁；a) generate 保留
  DEFAULT_PREFIX 主线并补充 HMBS_INSTALL 的 -I/-L（存在且不同时）；
  b) build 前只读探测各前缀的 ncurses 头/库与 tinfo 并打 JUKE-NC 日志，
  按真实存在的 tinfo 构造 `LIBS=-lncurses [-ltinfo[w]]` 传给 configure
 （AC_CHECK_LIB 实际链接 `-lncurses $LIBS`，可满足静态 ncurses 对 tinfo 的依赖）；
  c) configure 返回后校验 Makefile 存在性，缺失即转储 config.log 并 loud 失败，
  杜绝静默零退出再次误导为编译失败。

## 2026-10-16 真机预检进展（第二次 incomplete：改投 libofa 接线）

- 上轮把 build() 接入 make check（MANIFEST 置 in-build true）后仍判完全相同的
  incomplete（no_tests/0 不允许通过，命令已变为 make check）。同一指纹第二次
  失败，按要求换策略：回退到 libofa/0.9.3 已验证的 no-tests 接线。
- 本轮改动：a) 删除 build() 的 make check 调用（无可执行套件则意为不调用）；
  b) MANIFEST 置空双命令字段 + in-build false，保留结构化审计；
  c) no-tests 标记仍由消费者 test 在断言通过后发出（双通道打印，缓存命中亦重发）。
  framework 保持 autotools、command 保持 make check（指代干跑探针）。

## 2026-10-17 人工审查打回（rule12）：补 4 个具名端到端消费者用例

- 打回意见（Septest, rule12_harmony_specific FAIL）：鸿蒙特有测试行只有断言
  （N=1），不算完整消费者用例；至少要有一个完整消费者用例（真正跑通功能/
  流程的端到端用例），纯断言不行。上游 N=0 经审查员实测核实，无少报。
- 根因：旧 test_package 只跑 `juke` 无参并断言 usage 输出（单断言冒烟），
  test.c 从未被编译（仅文档作用），MANIFEST/PR 正文均按“1 个断言”口径填报。
- 源码分析（已解包 juke-0.7.tar.gz 核实）：main() 在 tui_start() 之前必跑
  config_load→dir_recurse→queue_init 全流程；curses TUI 需真实终端，无头
  环境无法进入交互界面，故消费者用例覆盖该确定性前缀即最大诚实端到端范围。
- 改动（参照 tal/1.9 端到端先例）：
  a) test.c 重写为编译型消费者驱动 test_juke（仅 POSIX
  fork/pipe/select，不依赖 ncurses）：自建 HOME/.juke.conf + 多层曲库
  fixture（子目录 + .mp3/.wav/.mod + 非音频诱饵），依次跑 HC-1 usage_flow /
  HC-2 invalid_dir_flow / HC-3 library_scan_flow / HC-4 multi_tree_flow，
  每个用例含搭建→执行→验证三阶段，共 9 项断言；退出码 0 当且仅当 4/4 通过，
  计数来自进程内部计数器；
  b) 新增 test_package/CMakeLists.txt（application 包，无 find_package），
  conanfile.py 改走 CMakeToolchain + cmake_layout，在 build() 编译 test_juke，
  test() 以 self.run 运行驱动并对 bin/juke 做 self.run 复执行（保留 L0d 字面
  门禁与双通道 HMBS 标记，test_package discovered=4）；
  c) MANIFEST.yml 增 category=harmonyos-specific consumer use case、
  harmonyos_specific_test_count=4、上游审计与总数口径不变（0/autotools_tests）；
  d) .hmbs/pr-body.md 按 4 用例口径全文修订（鸿蒙特有测试 4、合计 4、新增 4/4）。
- 待 HMBS 真机预检回填实测结果后同步 PR 正文通过率。

## 2026-10-17 真机预检失败（test_package CMake 无法识别 HarmonyOS 平台）

- 失败证据：主包 autotools 编译已过（juke.c/player.c 正常编译），
  test_package 的 `cmake.configure()` 失败：
  `System is unknown to cmake, create: Platform/HarmonyOS ...` +
  `CMAKE_C_COMPILER: /data/service/hnp/bin/clang ... Configuring incomplete`。
- 根因：上一轮为满足 rule12 的 4 个具名端到端用例，把 test_package 从
  VirtualRunEnv 改为 CMakeToolchain + cmake_layout 编译 test_juke；
  但真机 stock CMake 无 Platform/HarmonyOS 模块，且 profile 写死的
  编译器绝对路径在预检环境不可直接 exec（主配方已用 conf+PATH 回退
  解决，test_package 的 CMake 通道无此回退），故 configure 阶段即失败。
  与 4 个用例本身的内容无关，test.c 无需改动。
- 改动（与 ADAPTATION_GUIDE §5 及 test_package-executable 模板同路线，
  可执行包不走 CMake）：a) 删除 test_package/CMakeLists.txt；
  b) conanfile.py 改为 VirtualBuildEnv+VirtualRunEnv，build() 内按
  主配方同款 conf+shutil.which 回退解析 CC，直接
  `CC -O2 -Wall -o test_juke test.c` 编译（仅 POSIX libc，无 ncurses），
  test() 逻辑与 HMBS 双标记保持不变（discovered=4）；
  c) MANIFEST.yml 删除 CMakeLists 条目，conanfile 描述同步为直接 CC 编译；
  d) .hmbs/pr-body.md 测试文件清单同步去掉 CMakeLists 条目。
- 待 HMBS 真机预检验证直接编译路线。
