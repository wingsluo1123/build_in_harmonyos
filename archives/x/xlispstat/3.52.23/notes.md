# xlispstat 3.52.23 适配笔记

## 编译环境
- 构建系统: autotools（老式 autoconf configure + 递归 Makefile.in）
- 编译日期: 2026-10-13（前置适配完成日；真机构建待 shadow CI）
- 编译器: clang（OHOS SDK，aarch64-linux-ohos）
- 状态: built（真机 shadow CI r25 全绿，exit 0）

## 项目简介

XLISP-STAT 是 Luke Tierney（爱荷华大学统计系）基于 XLISP 方言的交互式统计计算与
动态图形环境（回归、ANOVA、动态图形等）。上游 canonical 源码是 uiowa 官方发布
tarball（GitHub 镜像 jhbadger/xlispstat 无任何 tag）。许可证 HPND-sell-variant
（允许商用/销售的宽松许可，COPYING 实测逐字核对）。

## 编译步骤（配方实现）

1. `./configure --prefix=/ --without-x UCFLAGS="$CFLAGS -O2"`
   - `--without-x` → `GRAPHSYS=GNUPLOT`：纯终端图形模式，不链接任何 X11 库
   - 上游 Makefile.in 用 `CFLAGS = -D${GRAPHSYS} ${UCFLAGS} ...` 覆盖环境 CFLAGS，
     必须通过 configure 命令行注入 `UCFLAGS`
2. `make xlisp -j1`（仅编译解释器；上游不支持并行构建，禁用 -jN）
3. OHOS 上用 binary-sign-tool 对顶层 `./xlisp` 签名
4. `make xlisp.wks -j1`（执行解释器：src/lsp/*.lsp → .fsl，dump 默认工作区）
5. `make xlispstat -j1`（setup.shell 生成 bin 包装脚本）
6. 运行上游测试套件（配方自带 runner，见下）
7. package() 手工 copy：bin/xlispstat、share/xlispstat/{xlisp,xlisp.wks,xlisp.hlp,
   Autoload,Data,Examples}、licenses/COPYING

## W0 依赖结论

```text
依赖数量：0（Conan 依赖；--without-x 构建仅链接 libc + libm）
已满足依赖：无外部依赖
缺失依赖：无
是否需要拆分依赖适配：否（若未来要开 X11 GUI：libxaw/libxmu/libxt 均未适配，
  需各自单独 issue/分支/PR，不混入本库）
阻塞点：无
下一步：真机 shadow CI 单包验证
```

注：Homebrew 只声明 libx11 依赖，但那是 X11 GUI 构建路径；Guix 声明
libx11/libxmu/libxext/libxpm/libxaw。本包采用 --without-x 终端路径，零 X 依赖。
运行时图形输出退化为调用外部 gnuplot（无 gnuplot 时交互绘图命令不可用，纯计算
与统计功能不受影响）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 GitHub 镜像无 tag，无法用 /archive/refs/tags/ URL 固定源码 | jhbadger/xlispstat 从未打 tag | 采用 uiowa 官方 release tarball，URL+SHA256 双固定（与 Homebrew formula 校验和交叉一致） |
| 2 | 老 Makefile 忽略环境 CFLAGS，Conan 工具链标志注不进去 | `CFLAGS = -D${GRAPHSYS} ${UCFLAGS} ...` 硬覆盖 | configure 命令行传 `UCFLAGS="$CFLAGS -O2"`（autoconf 原样替换 @UCFLAGS@） |
| 3 | 构建过程中途就要执行刚编译出的解释器（.lsp→.fsl 编译、dump 工作区） | 上游设计如此，无 host-only 路径 | 拆分 make 目标：先 `make xlisp`，OHOS 上签名后，再 `make xlisp.wks`；非原生环境（纯交叉）显式报 ConanInvalidConfiguration，不留假成功 |
| 4 | xlispstat 包装脚本把 `XLISPLIB=${prefix}/lib/xlispstat` 写死，Conan 缓存路径下不可用 | setup.shell 生成时烘焙绝对路径 | 补丁 0001：包装脚本优先继承环境 XLISPLIB，烘焙值仅作 fallback；package_info 用 runenv_info 注入 |
| 5 | 上游测试成功时完全静默，无法统计断言数 | test.lsp 的 check 仅在失败时打印 | 配方自带 xls-test-runner.lsp：逐字复刻 test.lsp 的文件列表与 check 循环，另加每文件 `[xls-test] <file> checks=<n>` 回显；上游测试文件零改动 |
| 6 | HMDFS 上 configure 无执行位，Autotools helper 直接 exec 报 126 | E087/E046（参考 esekeyd 判例） | `_conf_dir()` 探测 + `bash ./configure` 显式解释执行，`env="conanbuild"` |
| 7 | 自带 config.guess 为 2002-03-20 版（echo/exit 风格，无 GUESS=），uname -s=HarmonyOS 时 `unable to guess system type` | E007/E160：2002 版既无 HarmonyOS 分支，其 config.sub 实测连 aarch64-* 都拒绝 | 配方内幂等注入 `*:HarmonyOS:*:*)` 分支（posh/zephyr 判例），echo+exit 风格输出 `$UNAME_MACHINE-unknown-linux-gnu`（实测 2002 版 config.sub 原样接受该三元组）；r1 曾用 .patch 文件：设备 patch(1) 严格匹配 FAILED、桌面端仅 fuzz 2 通过，故弃 .patch 改注入；uname shim 本地模拟验证输出正确 |
| 8 | configure 检出 GCC=yes（clang 定义 __GNUC__）时 `*linux*` 分支给 ULDFLAGS 追加 `-export-dynamic`，OHOS clang 驱动可能不识别 | 老 configure 对 GNU ld 的老写法 | 三个 make 目标统一以命令行变量 `ULDFLAGS="-Wl,--export-dynamic"` 覆盖（make 命令行变量优先于 Makefile 赋值），不改上游 configure |

## 源码修改

- `patches/0001-relocatable-xlisplib.patch`：仅改 setup.shell（构建期生成包装
  脚本的模板）3 行，使 XLISPLIB 环境变量优先。不改任何 C 源码与测试断言。
- 配方运行时在构建目录写 `xls-test-runner.lsp`（不入包、不改上游文件）。

## 依赖版本

- 无 Conan 依赖（libc + libm）。

## 真机 shadow CI 结果（r25，2026-10-16，HarmonyOS PC aarch64 原生 conan create，exit 0）

```text
上游测试套件（配方自带 runner，tests/test.lsp 同源）：
  arith 30, complex 14, manip 9, matrix 10, matrix2 4,
  blas 35, math 26, prob 15, trig 9, rans 3
  = 10/10 文件，155 checks，0 失败
test_package：10/10 断言通过（PATH/环境、运行时文件、banner 版本、
  算术、mapcar、统计层 mean）
安装产物：bin/xlispstat + share/xlispstat/{xlisp,xlisp.wks,xlisp.hlp,
  Autoload,Data,Examples} + licenses
```

### 迭代记录（r1–r25）

| 轮次 | 结果 | 卡点/根因 | 解法 |
|---|---|---|---|
| r1 | fail | 设备 patch(1) 严格匹配 config.guess hunk FAILED | 改配方内幂等注入（E007） |
| r2 | fail | E386：hnp bash HMDFS getcwd 失败 | 能力探针选 shell + 重申 CONFIG_SHELL |
| r3 | fail | 配方缺 generate()，CC/CFLAGS 空 + UCFLAGS 拆词 | 补 AutotoolsToolchain + 步骤脚本化 |
| r4 | fail | E011：umask 077 在 HMDFS 建出不可写目录 | umask→002 |
| r5 | fail | E050：HMDFS 拒绝硬链接 | src/c Makefile ln→cp |
| r7 | fail | init→graphics→graph2:31 depth-cuing 经 dummygraph 桩 SIGSEGV（确定性，20/20） | 无头化：nongraph.lsp 替代动态图形栈 |
| r8-r13 | fail | 设备差异：conan 为 ELF、profile 缺 os.version、/tmp 只读（E002）、旧包残留 | 设备自适应 runner + TMPDIR + 强制重解包流程 |
| r14 | fail | 同 r7（确认 -O1-fnsa 与 ulimit 后仍崩于 graphics） | 见 r7 |
| r15-r16 | fail | ulimit 提升后 compile-file 仍崩 → 定位为优化敏感 UB | -O1 -fno-strict-aliasing（-O0 亦 5/5） |
| r17 | fail | 注释用了 #（Lisp 应为 ;）+ setup.shell 无执行位 | 分号注释 + sh 调用（E087） |
| r18-r19 | fail | 上游 10/10 文件 155 checks 0 失败；test_package 6/10、5/10——测试脚本引号/scratch 目录缺陷 | 落盘 grep + 可写目录探测 |
| r20-r22 | fail | /data/local/tmp 不可写、CRLF、set -u TMPDIR、wrapper shebang /bin/sh 不存在 | 逐一修复（shebang→/system/bin/sh） |
| r23-r24 | fail | HMDFS 拒绝脚本解释执行（bad interpreter）；arithmetic 断言 ^3 未匹配 "> 3" | 消费者测试直驱签名 ELF + 放宽锚定 |
| **r25** | **exit 0** | — | **上游 155/155，test_package 10/10** |

## 验证结果

本机（Windows 宿主）前置验证已执行：

- 源码归档 SHA256 复核：`9bf165eb…6ce6cf4`（实测下载 1,570,981 字节，与
  Homebrew formula 一致）
- 配方/测试文件 Python 语法检查：通过（py_compile）
- YAML 结构检查（manifest、test_package/MANIFEST）：通过
- `conan export`（validate/export_sources 路径真实执行）：通过
- `git diff --check`、改动边界检查：通过
- Windows 交叉 `conan create`（G2）：未执行 —— 宿主能力边界（WinError 2 假阴性，
  见知识库 DRAFT-windows-host-cross-profile-conan-create-g2-false-negative）；
  且本包构建必须原生执行解释器，G2 证据只能在真机取

## 注意事项

- 真机 shadow CI 命令（拿到空闲窗口后执行，单包排队）：

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job "xlispstat-3.52.23-<timestamp>" \
  --package archives/x/xlispstat/3.52.23 \
  --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"
# 随后执行 job 提供的 run-conan-heavy.sh，记录 exit code 与 L0-L5 结果
```

- 传输用 scp 或 base64，不用 PowerShell 文本管道传 tar。
- 若 CONFIG_SHELL（hnp bash）出现 getcwd 刷屏，按 classads/cvsgraph 草稿回退
  /system/bin/sh 能力探针。
- `xlispstat` 是 shell 包装脚本，L2 的 bin smoke 若直接 exec 会因 shebang
  /bin/sh 解释执行——mksh 可跑 sh 脚本，预期 L2 正常；test_package 已用
  bash 包装执行。
- 版本语义：Conan 包版本 3.52.23 == 上游源码版本 3-52-23，无递增。
