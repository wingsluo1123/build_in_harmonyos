# mtink 1.0.16 适配笔记（HarmonyOS PC / aarch64）

## 编译环境
- 构建系统：**上游手写 `Configure` + `Makefile.ORG`**（不是 autotools/cmake，无 configure.ac）
- 编译日期：2026-10-18
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`，native OHOS arm64）
- profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS arch=armv8 compiler=clang-15 libc++ Release）
- 零补丁（`patches/` 不存在，conandata.yml 无 `patches` 键）
- 状态：built（`conan create` rc=0 + test_package **29/29**）

## 软件与产物
mtink 是 EPSON 喷墨打印机的状态监视器：GUI 版 `mtink`（Motif）、打印机选择器 `mtinkc`、
命令行版 `ttink`、共享守护进程 `mtinkd`，另有并口/USB 设备 ID 查询器 `detect/askPrinter`
与若干构建期工具（`utils/bldRes`、`utils/rdPrtDesc`、`utils/chckRes`）。

交付产物（`package_type=application`，`archives/m/mtink/commands.json` 已声明）：

| 路径 | 说明 |
|------|------|
| `bin/ttink` | 命令行状态监视器（`-s` 状态 / `-i` 识别 / `-c` 清洗 / `-n` 喷嘴检查 / `-a` 对齐 / `-l` 型号表） |
| `bin/mtinkd` | 打印机共享守护进程（SysV shm + FIFO，pid 文件落 `/var/run/mtink`） |
| `bin/askPrinter` | 设备 ID 查询：并口走 `PPSETMODE/PPCLAIM/PPNEGOT`，USB 走 `LPIOC_GET_DEVICE_ID` |
| `share/mtink/printer.desc.bldin`、`share/mtink/C42.align` | 上游 `make install-desc` 的运行期数据 |
| `share/doc/mtink/*.html`、`*.gif` | 上游文档（19 html + 29 gif） |
| `licenses/LICENCE`、`licenses/CHANGE.LOG` | 许可证与变更日志 |

三个 ELF 均由 `binary-sign-tool -selfSign` 自签（`llvm-readelf -SW` 实测 `.codesign` 各 1 节）。

## 依赖决策：**零硬依赖**（三条各自实测）
| 候选依赖 | 结论 | 实测依据 |
|---|---|---|
| `motif/2.3.8` + `libx11` + `libxext` + `libxt` + `libxp` + `libxpm` | **不声明** | `conan install --requires=motif/2.3.8 -pr:h=ohos-aarch64 --build=never` → `ERROR: Missing prebuilt package for 'libxext/6.4.0.1'`（配方级版本分裂：`motif` 要 `libx11/1.8.Z`，而 `libxext/6.4.0.1` 的发布二进制按 `libx11/6.4.Z` 构建）。CI 以 `--build="${pkg_name}/*"` 建包（`ci/conan/build_and_test.sh:1367`），依赖必须预编译可得 ⇒ Motif 面结构性不可交付 |
| `libusb-compat/0.1.7` | **不需要** | `mainSrc/usbHlp.c` 整体在 `#ifdef MACOS` 内；Linux/OHOS 面 `usbHlp.o` 是空 TU。交付 ELF 已 strip（无 `.symtab`），裸 `llvm-nm -u` 恒为空表**不可作证**；改用 `llvm-nm -D -u`（动态符号表）实测 `bin/ttink` 72 行 / `bin/mtinkd` 68 行未定义符号、其中 `usb_`/`libusb` 命中 **0**，并以 `__libc_start_main` 存在作正控 |
| X11（GUI 面）| 不上 | 同上，`Configure -x` 使 `PRG` 不含 GUI 目标（配方在 build() 里断言 `PRG` 无 `mtink`/`mtinkc`）|

**GUI 面处置**：上游自带 `Configure -x|--no-x`（"If you want only the tty based version use the -x option"），
该模式让 GUI 的编译/链接规则整段退出构建面，`MOLIB=-lXm`、`-lXp`、`-lXpm`、`-lXext`、`-lXt`、`-lX11`
全部不再被引用 —— 因此**不需要**为裁剪 GUI 改任何源文件。风险记录：Motif 闭包在 ohpcd 上
不可用（见上表），若后续要交付 GUI 需先解决 `libxext/6.4.0.1` 与 `libx11/1.8.Z` 的发布面分裂
（属依赖链任务，R36），届时把 `-x` 去掉即可。

## 0 个补丁 + 1 个必要编译开关
`Configure` 用 `-x -p /` 生成 Makefile 后，编译面只需要一个开关：

- **`-fcommon`**：clang 15 默认 `-fno-common`，2007 年的 C 代码用**暂定定义**
  （`int firstConfig;` 写在头/多 TU）⇒ 链接期 `ld.lld: error: duplicate symbol: firstConfig /
  newPrinter / exchangeCartridge / alignHead`（`ttink` 与 `mtinkd` 两个 target 都命中）。
  加 `-fcommon` 后一次通过。知识库已有条目 **E1490**（`duplicate symbol, -fno-common, tentative
  definition, GCC 10, clang 15` / 推荐 `append-fcommon-flags`）与 **E705** 覆盖此坑，故未新建草稿。
- `CC`/`CFLAGS` 从 Conan conf 取（R33），以 make 命令行变量注入 —— 手写 Makefile 的
  `$(CFLAGS) $(MTINK_CFLAGS)` 是唯一标志通道（知识库 **E590** 同型）。

## 遇到的问题与解决（全部实测）
| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | `ld.lld: error: duplicate symbol: firstConfig` 等 4 个符号，`ttink`/`mtinkd` 均失败 | clang 15 默认 `-fno-common`；上游 2007 代码大量暂定定义 | `CFLAGS="-O2 -fPIC -fcommon"`（零源码改动）|
| 2 | `mainSrc/rdRes.c:605:19: error: non-void function 'searchCmp' should return a value` | 该 `return;` 在 `#if RESCHECK` 块内，只有开发工具 `utils/chckRes` 会以 `-DRESCHECK=1` 编译它 | 不构建开发工具（`make ttink mtinkd detect/askPrinter`），交付面不包含它们，因此不改 2007 年代码 |
| 3 | `make` 默认 `all` 不构建 `mtinkd`/`askPrinter` | 上游 `Configure` 用 ``uname` = "Linux"` 判断，本平台 `uname` = **HarmonyOS** | 在 build() 显式点名三个 target |
| 4 | 上游 `make install*` 全部不可用 | 每个 `install-*` 都被 `if id | grep '=0(root)'` 包住，并写 `/etc/init.d`、`/etc/rc.d`、`/usr/lib/cups/backend` | `package()` 用 `copy()` 自行落盘 + `_verify_installed_tree()` |
| 5 | 构建共 **260** 行 `warning:`，其中 **228** 条是 `illegal character encoding in string literal`（`-Winvalid-source-encoding`） | 上游字符串表是 Latin-1（2007 年）；其余为 `-Wpointer-to-int-cast` 16、`-Wunused-command-line-argument` 7、`-Wimplicit-function-declaration` 5、`-Wpointer-sign` 2 | 仅告警（`tres.c` 是内建资源表，英文/数字表项正确）；如实登记为已知限制 |
| 6 | 运行期 `mtinkd` 打 `mkdir : No such file or directory` | 设备**无 `/var`**；mtinkd 要建 `/var/run/mtink/<pid>` 与 FIFO `/var/mtink/<dev>` | 不改上游；作为确定性消费者断言（rc=0 + 该消息）。知识库 **E816** 已覆盖 `/var` 缺失，故未新建草稿 |

## 运行期设备面的取证（无头入口 / 探针，不使用"跑不起来"当结论）
本机（HarmonyOS PC）**没有任何打印机设备节点**，逐字读数：

```
ABSENT  /dev/lp0        ABSENT  /dev/lp1       ABSENT  /dev/parport0
ABSENT  /dev/usb/lp0    ABSENT  /dev/usblp0
PRESENT /dev/tty        PRESENT /dev/null      PRESENT /dev/urandom   PRESENT /dev/watchdog
```

而 **sysroot 里有** `linux/lp.h`、`linux/ppdev.h`、`linux/parport.h`（另上游自带
`detect/parport.h`/`detect/ppdev.h` 副本）⇒ 并口/`LPIOC_GET_DEVICE_ID`/`PPCLAIM` 这一整面
**编译能过、链接能过、运行期无物可测**。取数方式不是"跑不起来"，而是用上游自带的命令行入口
走真实代码路径并取**退出码**：

| 命令 | 退出码 | 逐字输出 |
|------|--------|----------|
| `ttink -v` | 0 | `ttink   : V 1.0.16` / `compiled: Oct 18 2026 16:40:38`（干净轮构建时间戳；手工首轮为 16:16:29） |
| `ttink -l` | 0 | 90 行型号表（`%3d: %-20s %s` 逐字：首行 `  1: C20SX                Stylus C20SX`，末行 ` 90: Scan_2500            Stylus Scan 2500`；`Stylus Photo R2400` 在第 78 行 ` 78: Photo_R2400          Stylus Photo R2400`） |
| `ttink -h` | 0 | stdout `Arguments for ttink` + `-d device_file --device device_file` |
| `ttink`（无参）| 1 | 用法打 stderr（fail-closed） |
| `ttink -d /dev/lp0 -i` | 1 | `No access to device file or no attached printer.` |
| `ttink -d /dev/null -i` | 1 | 同上（设备在、非打印机 ⇒ 同一措辞，失败点在打印机应答而非 open） |
| `askPrinter /dev/lp0` | 1 | **无任何输出**（stdout 0 B、stderr 0 B，静默 `exit(1)`；并口面先试 `/dev/parports/0` 再试 `/dev/parport0`，`access()` 均失败） |
| `askPrinter /dev/usb/lp0` | 1 | stderr `open: No such file or directory`（USB 面走 `open("/dev/usb/lp0", O_RDONLY)`） |
| `mtinkd`（15s 限时）| 0 | stderr `mkdir : No such file or directory`，进程自行退出、不留后台服务 |

型号表交叉核对：`ttink -l` 行数 90 == `share/mtink/printer.desc.bldin` 的 `.PRINTER` 块数 91 - 1
（上游 `while (i < defaultConfigDataSize-1)` 的 off-by-one，属可断言的观测契约）。

## 消费者断言的不可证伪性自证（审计 P1 修复的正面证据）
交付 ELF 是 **stripped** 的（`file bin/ttink` → `ELF … stripped`），因此 `llvm-nm -u` 的
stdout 恒为空（只往 stderr 打 `<path>: no symbols`）——只用它做「某符号不存在」的断言会
**恒真**（与是否链接 libusb 无关）。修复：改用 `llvm-nm -D -u`（动态符号表）并要求
「表非空 **且** 含 CRT 入口 `__libc_start_main`」作为正控后，才允许负向断言通过。
把 `llvm-nm` 换成不输出的桩即可证明该断言可失败：

```sh
# 正常：discovered 30 / passed 30
# 桩：PATH 前置一个 `exit 1` 且无 stdout 的 llvm-nm
PATH="$W/fakebin:$PATH" bash test_mtink.sh <pkg> <res> <work>
#   → [FAIL] ...(nm rc=1 rows=0 positive_control=no libusb_hits=0 ...)
#   → passed 28/30（A29/A30 转 FAIL）
```

## 上游测试统计（N = 0）
清点命令与逐字读数：
```sh
find . -iname '*test*' -o -iname '*check*'      # 3 命中，全部非测试：
                                                #   ./checkMotifVersion.sh  (Configure 构建期探针)
                                                #   ./mainSrc/checkenv.c    (运行期环境自检模块)
                                                #   ./mainSrc/checkenv.h
make check                                      # rc=2
                                                # make: *** No rule to make target 'check'.  Stop.
grep -nE '^(check|test)' Makefile.ORG           # 0 命中（无 check/test 目标）
```
无 `tests/` 目录、无 ctest/pytest/cmocka 注册、无 `check_PROGRAMS`、无 assertion 文件 ⇒
四种候选口径（源码宏 / 框架注册 / assertion / 消费者断言）**上游全部为 0**，
`TOTAL = PASS + FAIL + SKIP + NOT_RUN = 0`。

## 验证结果
```bash
conan create archives/m/mtink/1.0.16 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
#   → rc=0；HMBS_TEST_PACKAGE_RESULT {"discovered":30,"passed":30}
```

## 知识增量
- 并口/`ppdev`/`lp` 设备面在鸿蒙 PC 上「编译可过、运行期无设备」的系统性缺口（设备节点全缺
  而 sysroot 有 `linux/lp.h`、`linux/ppdev.h`、`linux/parport.h`）此前在知识图谱中 **0 命中**
  → 新建草稿 **E4312**（`knowledge/drafts/E4312-draft-*.kv`）。
- `/var` 缺失（mtinkd 的 `/var/run/mtink` + `/var/mtink`）命中既有条目 **E816**；
  `-fno-common` 重复符号命中既有条目 **E1490/E705**；手写 Makefile 命令行标志通道命中 **E590**
  ⇒ 这三条不再新建草稿（宁缺勿滥）。
