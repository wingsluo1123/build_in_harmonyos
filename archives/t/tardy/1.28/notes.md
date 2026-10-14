# tardy 1.28 适配笔记

## 任务来源

- 平台任务 contrib-11034（开源鸿蒙PC专项积分赛），分支 `feat/tardy-1.28`，2026-09-27 认领（API 留证：open→assigned，claimer=Ember5843）
- 上游：Peter Miller tardy 1.28（SourceForge，官网首页标题即版本），sha256=79b4652a1d90745e131efcfc8512f4427b1388695036718938ec79fa5bc6c26f
- 语言实测（R47 lang-preflight）：**C++**（175 .cc + 130 .h，源码统计）
- 依赖实测（源码 grep，2026-09-29）：bzip2（configure 硬探针 BZ2_bzopen）、xz（configure 硬探针 lzma）、boost（`libtardy/{file/input.h,file/output.h,filenamelist.h,tar/input.h,tar/output.h}` 五处硬 `#include <boost/shared_ptr.hpp>`，纯头文件使用，不链 boost 库）、libexplain（29 个源文件硬 `#include <libexplain/>`）。四者均无 HAVE_ 开关或 --without 选项。

## 选库核验（§3.2 否决线）

1. 他人已移植：main 档案无 tardy；制品仓 conan list "tardy/*" -r=ohpcd = 0；同版本无他人 claim
2. 语言/构建生态：C++ + autotools（autoconf 2.68 生成物自带，无需自举）；外部库依赖 bzip2 + xz（configure 硬探针，制品仓已发布 bzip2/1.0.8 + xz/5.6.2，直接引用）
3. 可行性：高（tar 后处理器，小体量，486 条目）
4. 难度定级：A（纯编译适配，零补丁）

## 依赖缺口 verdict（§3.7，2026-09-27 设备实测）

- configure 三硬探针：bzip2 ✓（制品仓 1.0.8 已引用）、xz ✓（制品仓 5.6.2 已引用）、**libexplain ✗**
- libexplain 状态：**已解除（2026-09-29）**——PR #11768 于 06:40 合入 main（commit `f23d8e705`，合入人 clancyxie），平台任务 completedAt=2026-09-28T22:40:51Z，制品仓 07:03 发布 revision `1877eab4`，OHOS/armv8 Release clang15 二进制在位。配方 `requires("libexplain/1.4.d001")` 已接上，当日交付。
- tardy 29 个源文件 `#include <libexplain/...>`，无 HAVE_ 开关、无 --without 选项，剥离=实质重写（难度 C），今晚不做
- 处置（§3.7 第二行）：上报平台 + 等发布后完整交付；libexplain 一合入发布，tardy 当天交 PR（分支与配方保留，requires 行已就绪）

## 降级边界声明

- 只装 `install-bin`（tardy 单工具）：`install-doc/install-man` 需 GROFF+ps2pdf（PDF 手册），设备/CI 无此工具链，故文档不随包
- 上游测试 56 shell 用例（`make sure`）是否在设备全量跑通，以真机实测为准（见 reports/）；验证由 3 项断言的消费者测试承担

## CI 反馈修复：boost 组件化依赖的 flag 传递（2026-09-29）

CI 构建 #64254 失败（conan-build-test ❌，rc=2，head c91a78ec）：

```
./libtardy/file/input.h:23:10: fatal error: 'boost/shared_ptr.hpp' file not found
make: *** [Makefile:226: libtardy/file/input.o] Error 1
```

两处根因，都不在配方 requires 列表的表面：

1. **requires 漏 boost**。tardy 的 boost 依赖是头文件级硬依赖，CI 前的设备全绿
   （CREATE_RC=0）是因为上一轮设备跑的是当时的配方、boost 恰好在 include 搜索路径上；
   CI 换干净 conan 缓存后暴露。
2. **`_build_environment` 只读顶层 `cpp_info`，读不到组件的 include 与 define**。
   boost/1.84.0 配方导出 7 个组件（boost_headers / boost_filesystem / boost_regex /
   boost_program_options / boost_iostreams / boost_system / boost_date_time），
   聚合 `cpp_info` 的 `includedirs` 虽然有值、`libs` 为空，而
   `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 只挂在 `boost_headers.defines` 上。
   设备实测（boostprobe/0.1 探针配方，conan create rc=0）：只按聚合 cppflags 编译
   `#include <boost/shared_ptr.hpp>` 会报
   `use of undeclared identifier 'pthread_setcancelstate'`（OHOS musl 无此符号，
   boost 的 OHOS 补丁正是靠这个宏绕开它）。

修复：requires 补 `boost/1.84.0`；`_build_environment` 遍历
`cpp_info.components.values()` 收集 includedirs/libdirs/libs/defines，
defines 以 `-D` 追加进 CPPFLAGS。shared_ptr 是纯头文件库，tardy 不链任何 boost 库。

## 构建要点

- 三元组按 rnnoise/zvbi 先例用 aarch64-unknown-linux-gnu（自带 config.sub 为 2.68 年代，未必认识 ohos）
- hmdfs umask 077→022（configure 生成物，0 命中即报错）；构建期清空 LD_LIBRARY_PATH；不做 strip；make -j1
- test_package 按 opustags 先例用 VirtualRunEnv + env="conanrun"；工具包形态按 opustags 软件级 commands.json（type=tool）

## 编译结束

（设备 conan create + conan-verify 结果见 reports/）

## R4：真实执行上游测试套件（2026-10-13）

人工裁决 rule4（PR #13691，gcw_RIhAOSxD）判 FAIL：上游 56 用例一个没跑（0/56）。
本次把上游 `test/00/*.sh` 全套真实执行，逐条计数。

1. **实测 N = 56**（源码重新清点，不采信自述）：`test/00/` 下 56 个 `t*.sh`，
   Makefile `test_files` 变量列 56 个目标、`check: sure`、`sure: $(test_files)`。
   逐条用例名：t0001a…t0075a（完整列表见 $HOME/tmp/ohpc-porting/
   tardy-r4-20261013-1/logs-final/ 下 56 个 .out）。声明 N=56 与实测一致。
2. **设备四类适配修复（配方补丁，非改上游断言）**：
   - 补丁 0001（`libtardy/tar/format.cc`）：uid/gid/size/mtime 读取支持 GNU
     base-256 扩展。**性质：防御性/健壮性修复，当前 56 用例不触达该路径。**
     根因（真实、可复现）：平台 uid=20001006 > 2097151，平台 toybox tar 用 `\x80`
     前缀的 base-256 编码 uid，tardy 的 `octal()` 遇 0x80 返回 -1 → fatal
     `"corrupted uid field {tar-posix}"`。触发证据：`tar cf a.tar a.txt`（平台
     toybox tar）后 `tardy a.tar -list` 即报该 fatal（真实 uid 的 tar）；用
     Python tarfile 以 GNU_FORMAT 显式写小 uid（0）则 tardy 正常读取。
     **为何当前套件不触达**：补丁 0004/0005 的 GNU 兼容前端把夹具 uid/gid 一律写成
     0（复现上游以 root 运行的测试环境，与 t0010a/t0075a 等期望的 uid 0/root 一致），
     故夹具不含 base-256 编码。实证：在最终构建树上**还原补丁 0001**（format.cc 的
     numeric→octal）后重跑套件仍 **56/56**（日志
     `$HOME/.local/share/ohpc-porting/runs/tardy-1.28-r4-no0001/output.log`）。
     该补丁保留的理由是让 tardy 能读取平台真实 tar（uid 过大的归档），不是为通过
     这 56 条用例。
   - 补丁 0002（`libtardy/tar/output/filter/gzip.cc`）：mkstemp 临时文件改走
     `$TMPDIR`（回退 /tmp）。根因：设备 `/tmp` 是只读 erofs 挂载（`mount` 实测），
     硬编码 `/tmp/tardy-XXXXXX` mkstemp 报 EROFS。t0017a 因此失败（真实触达）。
   - 补丁 0003（`script/test_prelude.sh.in`）：harness 临时目录 `testdir` 由
     硬编码 `/tmp/icomp-$$` 改为 `${TMPDIR:-/tmp}/icomp-$$`（同上，/tmp 只读；
     真实触达——不修则全部 56 条都在 mkdir 阶段 exit 2）。
   - 补丁 0004/0005（`test/cpio`、`test/tar`）：平台 tar/cpio 是 toybox 0.8.12，
     缺 GNU 语义（tar 无 append 'r'、`tvf` 时间列多一空格；cpio 仅 newc，无
     crc/odc 且读不了 odc）。提供 Python 实现的 GNU 兼容测试前端（仅测试环境用，
     不改上游用例），由 build() 置于 PATH 前部。hmdfs（`hmmac=use_task`）忽略
     chmod，夹具模式由该前端合成（目录 0755 / 文件 0644，即 umask 022 标准创建模式）。
3. **接入构建**：`build()` OHOS 路径在 `make bin/tardy` 后运行
   `chmod +x test/tar test/cpio && make bin/test_prelude && umask 022 &&
   PATH="$PWD/test:$PWD/bin:$PATH" make -o all check`（`-o all` 跳过需 ps2pdf 的
   PDF 手册目标）。跑的是刚构建出的 bin/tardy。
4. **结果（设备实测，TOTAL=PASS+FAIL+SKIP+NOT_RUN）**：
   PASS 56 / FAIL 0 / SKIP 0 / NOT_RUN 0，TOTAL 56。
   逐条原始日志：`$HOME/tmp/ohpc-porting/tardy-r4-20261013-1/logs-final/`（56 个
   per-case .out）与 porting run 日志
   `$HOME/.local/share/ohpc-porting/runs/tardy-1.28-r4-final-suite-2/output.log`；
   构建内执行证据：CI 同构门禁
   `$HOME/.local/share/ohpc-porting/runs/tardy-1.28-cigate-20261013-7/output.log`
   （56×`PASSED` + `Passed All Tests` + L1c）。
5. **未改**：未改任何上游测试断言、未删用例、未跳过套件；N/N′ 由最终日志复算。
   - 备用消费者测试（test_package/test_tardy.sh，3 断言）继续作为工具级验证。

## 上游测试逐条统计（2026-10-13，R4）

TOTAL = 56 = PASS 56 + FAIL 0 + SKIP 0 + NOT_RUN 0
逐条：t0001a t0002a t0003a t0004a t0005a t0006a t0007a t0008a t0009a t0010a
t0011a t0012a t0013a t0014a t0015a t0016a t0017a t0018a t0019a t0020a t0021a
t0022a t0023a t0025a t0026a t0027a t0028a t0029a t0030a t0031a t0032a t0033a
t0035a t0036a t0037a t0039a t0050a t0051a t0052a t0053a t0055a t0056a t0057a
t0058a t0059a t0060a t0061a t0062a t0063a t0065a t0067a t0068a t0070a t0072a
t0073a t0075a —— 均 PASSED。
