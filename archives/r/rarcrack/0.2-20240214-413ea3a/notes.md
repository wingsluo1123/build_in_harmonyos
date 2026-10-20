# rarcrack 0.2-20240214-413ea3a 适配笔记

任务：积分赛。上游 rarcrack（David Zoltan Kedves 原作，现由 Jared Burrows
维护），RAR/7Z/ZIP 加密压缩包暴力破解工具：多线程逐个试探口令，调用外部
`unrar` / `7z` / `unzip` 验证，通过 `file -i` 做类型自动探测，XML 状态文件
记录进度。产物为单文件 CLI `rarcrack`（构建期依赖 libxml2 + pthreads）。

## 上游形态

- 版本锚点：`github.com/jaredsburrows/rarcrack` commit
  `413ea3a549f9ac1e5c1f4d7913881047bfaa71a6`（2024-02-14，
  与 Debian `rarcrack 0.2+20240214~413ea3a` 同源，Debian d/watch 已重定向
  到该仓库）。tarball
  `https://github.com/jaredsburrows/rarcrack/archive/413ea3a549f9ac1e5c1f4d7913881047bfaa71a6.tar.gz`
  sha256 `a4713c5e…1443a95cd0` 经本机实下验证。
- 许可证：GPL-2.0-only（上游 LICENSE 为 GPLv2 正文）。
- 构建形态为**裸 Makefile**（非 autotools / 非 cmake）：`all`（单文件
  `rarcrack.c` + `-pthread` + 反引号 `xml2-config` 链接为 `rarcrack`）、
  `debug`、`clean`、`install`、`uninstall` 五个目标；无 configure、
  无 check/test 目标。上游 CI（.github/workflows/build.yml）的所谓
  “测试”只是手动启动 `./rarcrack --type zip test.zip`（无断言、无注册
  用例、不会结束），不构成自动化测试套件。
- 上游测试：**无**。源码树无 tests/ 或 test/ 目录、无 *test* 测试架文件；
  Makefile 无 check/test/TESTS 目标；fixtures（test.rar/test.7z/test.zip）
  仅供手动试跑。详见 `test_package/MANIFEST.yml` 审计结论
  （`upstream_tests_exist: false`，`upstream_test_total: 0`）。
- CLI 用法：`rarcrack encrypted_archive.ext [--threads NUM] [--type rar|zip|7z]`
  （线程 1–12，超限钳制到 12；`--help` 打印选项；文件缺失报 not exists；
  非法 --type 报 WARNING；类型未指定时靠 `file -i` 探测）。
- main() 恒返回 EXIT_SUCCESS（所有错误路径均为打印后返回），因此反向
  对照不用退出码，改用“WORK 内不得出现状态 *.xml”的副作用断言。

## OHOS 适配要点

1. W0/R36：构建期唯一 Conan 依赖 `libxml2/2.15.3.1`（本仓 R37 适配后缀
   版本，同上游 v2.15.3 tarball、同构建方式、零 tool_requires，仓内独有）
   按 R36 要求须已发布到制品仓；预检将以 `conan download` 实证，若未
   发布则先停本包。刻意不用裸 `2.15.3`：真机预检远端顺序 conancenter
   在前，双远端共存的裸版本命中 CCI 配方，其 tool_requires("cmake")
   拉起 conandata 无 OHOS 条目的 cmake/4.4.x，从源码构建即报
   KeyError: 'OHOS'（2026-10-08 预检实证；zurl/1.12.0 notes #26-#27、
   baka/2.0.4、atracdenc/0.2.3 同型先例）。
2. R33：编译器从 `tools.build:compiler_executables` 取（CI 上 `$CC` 为空）；
   以 make 命令行变量传 `CC` / `XML2_CFLAGS` / `XML2_LIBS`
   （make 命令行变量优先级高于 Makefile 内定义），`-j1`（R9）。
   编译器解析复用 regldg/1.0.1 的 PATH + ~/usr/local/bin 回退模式。
3. patches/0001：上游 Makefile 的宿主机 `` `xml2-config` `` 反引号在
   OHOS 构建下会混入宿主 -I/-L，改为 `$(XML2_CFLAGS)` / `$(XML2_LIBS)`
   变量；`CC=gcc` 改为 `CC?=`。不含 `__OHOS__` 平台宏（R8/PF5 合规），
   不碰 debug/clean/install/uninstall 目标。
4. 不调用上游 `make install`（其 `install -s` 依赖 strip 且写绝对
   PREFIX），package() 直接 copy 二进制到 `bin/`、LICENSE 到
   `licenses/`、README.md/CHANGELOG 到 `share/doc/rarcrack/`。
5. R26 不适用：单文件 CLI，无 .so 产物，不存在系统同名库污染风险
   （链接的 libxml2 来自 Conan 依赖，不随本包发布）。
6. R38：命令行工具，在软件级目录新建 `commands.json`（type=tool，
   ref 对齐 rarcrack/0.2-20240214-413ea3a）。
7. R34：test_package 非空壳——`test_rarcrack.sh` 6 项真实断言：
   无参数 USAGE 文本、`--help` 选项文本、缺失文件 not exists、
   非法 --type WARNING、`--threads 20` 钳制到 12（输出落盘 HMFS
   可写目录）、反向对照（WORK 内无状态 *.xml，证明未启动破解且
   harness 能观察到真实行为）。脚本刻意只用 `set -u` 不用 `set -e`，
   保证任何单项失败后仍执行并打印 RESULT 尾行（真机门禁解析该行计数）。
8. 刻意不启动真实破解：crack_start() 在目标机缺少 unrar/7z/unzip
   时会空转永不退出；实际破解能力依赖目标机具备这些**外部程序**
   （非 Conan 库依赖，配方不声明 requires），PR 正文补充说明如实声明。
9. 机器 evidence（`HMBS_TEST_PACKAGE_RESULT` / `HMBS_UPSTREAM_TEST_RESULT`
   双标记）由 test_package/conanfile.py 在真机实测后发出，计数取自脚本
   RESULT 尾行正则解析，无算术修补、无猜测修正分支。

## 待 HMBS 真机预检

- 本轮仅完成未提交工作树；`conan create` 编译 + test_package 6 项断言 +
  双标记 evidence 待 HMBS 后台真机验证后回填 PR 正文通过率。
- 风险项（若真机日志报错下一轮修复）：musl 下 `strcasestr` 应为内建声明，
  若 OHOS 头文件行为有异则追加 `-D_GNU_SOURCE`；libxml2 2.15.3.1 的
  `xmlInitThreads` 已标记 deprecated，若真机 CFLAGS 含 -Werror 则需
  在 CFLAGS 中追加 `-Wno-deprecated-declarations`（当前配方未预置，
  保持最小 flags）。

---

**编写日期**: 2026-10-04
**最终状态**: 待真机预检（工作树未提交）
