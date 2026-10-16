# bdftopcf 1.1 适配笔记

## 编译环境
- 构建系统: autotools（上游 `configure` + `Makefile.am`，X.Org 官方发布路径）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（OHOS profile `ci/conan/profiles/ohos-aarch64`，`os=OHOS`、`arch=armv8`）
- 平台: aarch64-unknown-linux-ohos（HarmonyOS，HongMeng Kernel 1.12.0）
- 状态: built

## 货源（权威，勿改）

| 项 | 值 |
|---|---|
| 官方直链 | `https://www.x.org/releases/individual/app/bdftopcf-1.1.tar.bz2` |
| sha256 | `4b4df05fc53f1e98993638d6f7e178d95b31745c4568cee407e167491fd311a2` |
| 字节数 | **150815**（本机 `curl -fsSL` + `sha256sum` 实测，2026-10-08） |

- 该直链 `301 → http://www.x.org/archive/... → https://xorg.freedesktop.org/archive/...`，
  最终 200、`Content-Length: 150815`。`conandata.yml` 保留 https 官方标量 URL（PF7 只查本文件）。
- ⛔ 不得用 Debian 池址当货源（PF7 拉黑 `deb.debian.org`）。
- ⚠ 上游另有 **`individual/util/bdftopcf-1.1.2.tar.xz`（200，146188B）** —— 见下文
  「W0b 历史归档核验」；**本任务版本 = 1.1**，登记表行、归档目录、分支名、conan 版本
  全部钉在 `1.1`，不得改用 1.1.2。

## 编译步骤

1. `recipe-search bdftopcf -b autotools`（top1 骨架分值 0.35，属低相似 ⇒ 以同族 `appres 1.0.7`
   的 autotools 本地改法为底稿，而非空白模板起步）。
2. `preflight_check.sh bdftopcf/1.1` → `[OK] 所有依赖均已发布到制品仓`（依赖只有 `xorgproto/2025.1`），
   且 `[OK] 版本号未被占用: bdftopcf/1.1`（R37）。
3. `init-build bdftopcf 1.1 --url=<官方直链>` → `.orig`（只读基线）/ `.work`（可写工作副本）双轨，
   基线指纹 48 个文件。
4. `lang-preflight bdftopcf 1.1 --src $BUILD_SRC_DIR --lang c` → `task=c, detected=c`（exit 0），
   证据：`build_system=autotools` / `manifest=configure.ac、Makefile.am 存在` / `源文件 15 个（c:15），主体占比 100%`。
5. 探索阶段（R1：只给 `--prefix`）：`./configure --prefix=... && make -j2 && make install`
   + `make check`（证据见下）。修好后本地验绿，再烧 `conan create` 轮次。
6. `conan-init` 生成首稿 → 手工按 CLI 工具改正（`package_type`、`package_info`、依赖、
   `_patch_autotools_scripts`、`test_package` 消费者测试）。
7. `conan-verify bdftopcf 1.1` → **RC=0 / `✅ 配方验证通过`**（G0/G1/G2/G3/G4 + L2/L4/L5）。
8. `finish bdftopcf 1.1 built`（内含 refresh-patch、W2 结构、R36 依赖、W3 本地 CI）。

## 测试数（五维账本，`手册/04 §10.1`；与 `manifest.yaml` / `notes.md` / `test_package/MANIFEST.yml` 三处同源）

| 维度 | 数值 | 来源 |
|---|---|---|
| `N_static`（上游静态声明） | **0** | `Makefile.am`/`man/Makefile.am` 无 `TESTS`、无 `check_PROGRAMS`；`configure.ac` 无测试宏；全树 48 文件、唯一子目录 `man/` |
| `N_registered`（构建系统注册） | **0** | `grep -n '^TESTS\|check-TESTS\|check_PROGRAMS' Makefile man/Makefile` → **0 行** |
| `N_executed`（实际执行） | **0** | `make check` 实测：`man/: Nothing to be done for 'check'`、顶层无 `check-TESTS`，**rc=0** |
| 未执行分类数 | **0** | 无跳过、无预期失败、无条件注册（根本无注册项） |
| `N_consumer`（新增消费者测试） | **7** | `test_package/test.sh`，实测 **`7/7 checks PASS`** |

**上游表合计 = `N_static` = 0；适配后合计 = 0（上游）+ 7（消费者）= 7。**

按 `§12.72` 四类在源码树就地清点（2026-10-08，`.orig` 48 文件）：

| 类别 | 实测 | 命令与说明 |
|---|---|---|
| `test*/` 框架源码 | **0** | `find . -type d` → 仅 `.` 与 `./man`；`find . -iname '*test*'` → 0 |
| `*/res` 语料 | **0** | `find . -type d \( -name res -o -name tests -o -name test \)` → 0 |
| `**/*RUNTEST*` 脚本 | **0** | `find . -iname '*runtest*'` → 0 |
| `src/demo\|examples/*.c` 示例 | **0** | `find . -path '*demo*' -o -path '*example*'` → 0 |

> ⇒ **上游确无测试资产**（附上述四条清点证据），`make check` 实测空转。
> 语言面：`c/c++ 文件 28 个`（15 `.c` + 13 `.h`）、脚本 0，与任务声明 `c` 一致（c↔cpp 兼容族）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 错误模式 | 解决方案 |
|---|------|------|----------|----------|
| 1 | `build` 一条龙首轮 `EXIT_REASON: init_build_failed` / `STEP_FAILED: Step1` | registry 无 `bdftopcf` 条目，URL 搜索落到无关的 Savannah 域名 | — | 按 **`§12.60①`** 跳过 `build` 一条龙，改 `init-build --url=<官方直链>`，配方就位后**直走 `conan-verify`**（其 create 不触发 init ⇒ 不会覆盖手写配方）；⛔ 不改 `scripts/` |
| 2 | 首条真实错误：`configure: error: cannot guess build type; you must specify one`（`config.guess timestamp = 2017-08-08`、`uname -s = HarmonyOS`） | GNU `config.guess` 不认识 `uname -s = HarmonyOS` | **E007** / E072 | `build()` 内幂等插入 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos` |
| 3 | ⚠ **照抄 `appres` 的 `GUESS=…` 写法在本包无效**：分支匹配了却仍报 `unable to guess system type` | appres 的 tarball 带**新版** `config.guess`（有 `GUESS=` 变量、末尾 `echo $GUESS`）；**bdftopcf 是 2017 老版，每个分支形如 `echo <tuple>; exit ;;`** | E007 变体 | 本包分支改为 **`echo ${MACHINE}-unknown-linux-ohos` + `exit ;;`**。同族两版 `config.guess` **不可互抄** |
| 4 | `configure: error: /bin/sh ./config.sub aarch64-unknown-linux-ohos failed` → ``Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized``` | `config.sub`（2017-04-02）的 **KERNEL-OS 列表**无 `linux-ohos*` ⇒ `basic_machine` 被切成 `aarch64-unknown-linux` | **E072 第 1 处** | 顶部 `maybe_os` 列表加 `linux-ohos*`（`basic_machine` 才收敛成 `aarch64-unknown`） |
| 5 | 若只补第 4 处，`os=-linux-ohos` 仍会被后面 `-linux*)` 别名分支改写成 `-linux-gnu-ohos` | 2017 版 `config.sub` 的「basic system types」列表无 `-linux-ohos*`，而 `-linux*)` 别名在它之后 | **E072 第 2 处** | 「basic system types」列表再加 `-linux-ohos*`（在 `-linux*)` 之前匹配即止）。两处各有独立 guard，**不共用裸子串**（否则先写入的子串会让后一处误判"已存在" —— `appres` 曾踩同坑） |
| 6 | `fatal error: 'X11/Xos.h' file not found` 等 8 头缺失 | 上游不装也不查 X11 头，需外部注入 include 路径 | — | 依赖声明 `xorgproto/2025.1` + `generate()` 里 `AutotoolsDeps`（其 `cpp_info.libs=[]` ⇒ 只进 `CPPFLAGS`，不往链接行塞 `-l`） |
| 7 | 模板 `package_type="library"` + `cpp_info.libs=["bdftopcf"]` + `test_package` 是 CMake `test.c` 打印壳 | conan-init 按模板默认生成 | R38/R34/PF3/PF8 | 改 `package_type="application"`、`package_info.bindirs=["bin"]`（`includedirs/libdirs` 置空）、删 `CMakeLists.txt`/`test.c` 改 `test.sh` 真跑二进制，另建软件级 `commands.json` |

> **`configure` 的 `umask 077 && mktemp -d "./confXXXXXX"`（`config.status` 沿用）在 HMDFS 上建 700 目录不可写
> （E110/E112）**：本包一并改 022 + `mkdir`，`conan create` 实测通过。
> 本包 `config.status` 首轮即被上表 #2/#4 挡在前面，未单独复现 E112 报错 —— 该改动属**同族已知必修项的前置修复**，
> 非凭空添加。

## 源码修改

**未修改任何 `.c`/`.h` 源文件。** 全部改动落在 **autotools 分发 shell 脚本**（`config.guess` / `config.sub` / `configure`），
由 `conanfile.py` 的 `_patch_autotools_scripts()` 在 `build()` 内以「已存在即跳过」的幂等方式施加；
`apply_conandata_patches()` 在其之前先跑，`finish` 的 `refresh-patch --auto` 会把同一份差异固化成 `patches/` 补丁。
（历史 `1.1.2` 归档的三件补丁 `0001-config.guess` / `0002-config.sub` / `0003-configure` 与本包**同名同因**。）

- **R8 / PF5：不注入平台宏** —— 全文**无 `__OHOS__` 字面量**（`config.guess` 靠 uname 名 `HarmonyOS` 识别，
  不靠 C 宏；历史 `1.1.2` notes 记的 `__OHOS__ LIBC 检测` 写法按现行 PF5 会被拦，本包不采用）。
- ⚠ **未采用 `--build`/`--host` 绕过 `config.guess`**：会被 autoconf 判为交叉编译、跳过 `AC_RUN_IFELSE`
  生成错误 `config.h`（`appres` notes 同口径）。

## 依赖版本

| 依赖 | 版本 | 来源 | 用途 |
|------|------|------|------|
| `xorgproto` | `2025.1` | ohpcd 制品仓（`conan list xorgproto/* -r=ohpcd` → 1 条；`conan install --build=never` 实测**预编译二进制可下载**） | 提供全部 8 个被包含的 X11 头 |

**全树只有这一个 conan 依赖**，证据：

- `grep -E 'AC_CHECK|PKG_|AC_SEARCH' configure.ac` → **0 命中**（`configure.ac` 无库探测）；
- `Makefile.am` 链接行只有 `AM_CFLAGS = $(CWARNFLAGS)`，**无 `-lX11` 任何链接库**；
- 8 个被包含头逐一在 conan `xorgproto` 包里实测存在：
  `X11/{X.h,Xproto.h,Xos.h,Xfuncproto.h,Xfuncs.h,Xdefs.h}` +
  `X11/fonts/{fontstruct.h,FSproto.h}` —— `find $CONAN_HOME/p -name <hdr>` 全部命中同一 `xorgp*/p/include`。
- 故**不 `requires libx11`**：`bdftopcf` 是纯头文件消费者，链接面为空，多拉 `libx11/libxcb/libxau/xtrans`
  只会放大 CI 构建面而无收益。
- `W0 preflight_check.sh bdftopcf/1.1` → `[OK] 已发布: xorgproto/2025.1` + `[OK] 版本号未被占用`。

## 验证结果

```bash
# 1) 探索阶段本地全链路（R1 只给 --prefix）
$ ./configure --prefix=<pfx> && make -j2 && make install && make check
configure rc=0 / make rc=0 / make install rc=0
make check: man/: Nothing to be done for 'check'. （rc=0，上游无测试）

# 2) W0 preflight
$ bash ci/scripts/preflight_check.sh bdftopcf/1.1
[OK] 已发布: xorgproto/2025.1
[OK] 版本号未被占用: bdftopcf/1.1
[OK] 所有依赖均已发布到制品仓，可以安全开始适配 bdftopcf/1.1

# 3) conan-verify 8 道门禁（G0/G1/G2/G3/G4 + L2/L4/L5）
$ ohc-run.py conan-verify bdftopcf 1.1
✅ 配方验证通过: bdftopcf 1.1     # VERIFY_RC=0
#   脚注（与 bdf2sfd 同口径披露）：明细里 G4 = 「⚠️ 无法找到程序包 ID」、
#   L2/L4/L5 = 「⏭️ 跳过（无 cache 路径）」—— 工具在各段标 ✅，但这两类不是实质检查通过。
#   「8 道门禁 PASS」的实质依据是 G0/G1/G2/G3（G2 = conan create 真跑）；
#   产物面以 reports/conan-verify-report.md 与 reports/conan-create.log 手工读数为准。

# 4) 消费者测试（conan create 内 test_package，reports/conan-create.log:281-288）
--- bdftopcf 1.1 consumer verification ---
PASS 1: -o <out> <in> exit 0
PASS 2: PCF magic = 01 66 63 70 (LSBFirst 'fcp')
PASS 3: stdout PCF stream = 824 bytes
PASS 4: stdin -> stdout conversion exit 0
PASS 5: -p8 accepted, exit 0
PASS 6: corrupt input -> rc=1 + 'corrupt' diagnostic
PASS 7: missing input -> rc=1 + "can't open bdf source file"
test bdftopcf 1.1: 7/7 checks PASS

# 5) 产物（探索阶段实装）
$ bdftopcf -o out.pcf font.bdf ; xxd out.pcf | head -1
00000000: 0166 6370 0900 0000 0100 0000 0e00 0000  .fcp...    # PCF magic，rc=0
```

通过率口径：**上游执行项 0/0（无注册项）；静态全量 0/0；消费者断言 7/7。**

## W0b 历史经验核验（`SKILL.md` W0b，本轮读数）

**`archives/b/bdftopcf/1.1.2` 在上游 main 上确有历史归档，且已被删除**，逐项取证：

| 事实 | 读数 |
|---|---|
| 加入 | `5138116a6d`（2026-06-25 10:25）首次；`f83589810a`（2026-06-30 21:18）再加 |
| 删除 | `a5ebd25809`（2026-06-30 23:48）**整目录删除 7 文件 410 行**（`--diff-filter=D` 实测） |
| 现状 | `git ls-tree HEAD archives/b/ \| grep bdftopcf` → 空（main 上已无） |
| 内容 | `1.1.2/{manifest.yaml,notes.md,patches/0001-config.guess.patch,0002-config.sub.patch,0003-configure.patch}` + 软件级 `README.md`/`manifest.yaml` |

**逐项比对结论（历史踩坑 = 已验证结论，本包全部遵循；偏离处已写明）**：

| # | 历史结论 | 本包 | 判定 |
|---|---|---|---|
| 1 | `config.guess` 不识 HarmonyOS ⇒ E007 补丁 | 同，已修（表 #2） | **遵循** |
| 2 | `config.sub` 缺 `linux-ohos*` 内核兼容 ⇒ E007 补充 | 同，且**多发现并补了 2017 版第 2 处**（表 #4/#5） | **遵循 + 加强** |
| 3 | `configure` `umask 077` ⇒ E011/E110 | 同，已修 | **遵循** |
| 4 | 「bdftopcf 无 `--version`，验证用真实 BDF→PCF 转换而非 `--version`」 | 实测复核：`--version`/`--help` 均走 `invalid option` + usage、rc=1；**消费者测试全部基于真实转换与错误路径** | **遵循** |
| 5 | `-j2` 触发 HMDFS `mkfifo` 警告、jobserver 自动降级单线程，不影响结果 | 配方保留 `make -j2`（同族同参），无失败 | **遵循** |
| 6 | 依赖 `xorgproto` | 同（版本升 `2025.1`，制品仓有预编译二进制） | **遵循** |
| 7 | 依赖 `util-macros/1.20.2`（设备 cmd-pkgs 预编译包） | **未引入** —— 上游 tarball 自带已生成的 `configure`/`aclocal.m4`，本包不跑 `autoreconf`；`configure` 阶段对 `xorg-macros.pc` 只打印一行 warning 且 **rc=0**（实测）。cmd-pkgs 预编译包**CI 侧不存在**，属「环境语义不可迁移」 | **偏离（W0b 第 1 项判定）** |
| 8 | 货源 `individual/util/bdftopcf-1.1.2.tar.xz`、版本 `1.1.2` | **本任务 = `1.1`**、货源 `individual/app/bdftopcf-1.1.tar.bz2`（登记表行 + ST 实测 GET 200/150815B 一致）。两 URL 均实测 200，见「货源」表 | **按任务口径，不改** |
| 9 | 历史 `manifest.yaml` 的 `sha256` 留空 | 本包 sha256 已实测填齐 | **补齐** |

> **环境语义可迁移性（W0b 第 1 项）**：历史成功靠**设备 cmd-pkgs 预编译包 + `ohc-run.py package`**，
> 命令在 CI 远端 clean 环境**逐字不可执行**；本包改为 conan `xorgproto/2025.1`（制品仓预编译二进制，
> `conan install --build=never -r=ohpcd` 实测通过），CI 可复现。

## 适配面（B 判定的支撑读数；**B 判定列归主理裁**，此处只给四范围查重读数）

**范围1 历史归档**：`archives/b/bdftopcf` **有历史归档（1.1.2）但已在 main 删除**（读数见上节表格）；
`git log --diff-filter=D -- 'archives/b/bdftopcf/**'` 命中 `a5ebd25809`。

**范围2 知识图谱 `E*`**：
- `bdftopcf` 在 `knowledge/graph/index.tsv`（768 行）**命中 0**；`knowledge/` 全树 `grep -ril bdftopcf` → **0**。
- 同族/同机制命中：**E007**（`hit_count=1`、`evidence=patch-autotools-script`、severity 2）与
  **E072**（`hit_count=1`、同 evidence、severity 3）= `config.guess`/`config.sub` 不识 HarmonyOS；
  **E110**（`hit_count=0`）、**E112**（`hit_count=0`）= `config.status` 700 目录 / `mktemp`；
  `config.guess` 关键词在 index.tsv 共 **9 行**命中。
- E471（headless/no-display 测试分类）与本包**无关** —— `bdftopcf` 不连 X server（纯本地文件转换），
  消费者测试 7 条断言**全部无需 `DISPLAY`**（实测 `DISPLAY` 未设仍 7/7 PASS）。

**范围3 经验库（含 `14-最终防错清单.md`）**：
- `grep -ril bdftopcf 经验文档/经验库/` → **0**；
- `14-最终防错清单.md` 内 `config.guess|E007|E072|HarmonyOS case` → **0 行**；
- `config.guess` 命中 6 个册子（`05-Autotools-HMDFS-musl.md`、`12a`、`12b`、`12c`、`12d`、`12e`）。

**范围4 B 草稿库**：`grep -ril 'config.guess|config.sub' 经验文档/B草稿库/` → 2 组（`host-os-linux-substring-match-enables-werror`、
`gnulib-gettext-futex-deadlock-gtk-option-group`），**均非本机制**；`bdftopcf` → **0**。

**设备能力面**：`B潜力低`（SCT 一手普查 12 项空白区机制逐项 grep 全 0）；本包实测同向 ——
纯 X11 协议头 + 文件 IO，无 X server 交互、无平台行为差异面。

## 注意事项

- **`bdftopcf` 没有 `--version`/`--help`**：任何 `-v`/`--foo` 都走 `invalid option` + usage、**rc=1**；
  写测试/验证时别断言版本号输出，用真实 BDF→PCF 转换断言（历史 `1.1.2` notes 同口径，已实测复核）。
- **`-o` 必须是选项**：`bdftopcf in.bdf out.pcf` 会把 `out.pcf` 当第二个输入报
  `invalid option '…'`；正确形态 `bdftopcf -o out.pcf in.bdf`（或不给 `-o` 走 stdout）。
- **测试不落盘**：`test_package/test.sh` 输出文件一律 `-o /dev/null`，数据面走 stdout 管道取前 4 字节 ——
  设备 `/tmp` 只读，且目录级 `git add` 会把产物扫进提交（§12.71②）。
- **不连 X**：`bdftopcf` 是纯本地文件编译器，`DISPLAY` 未设不影响任何断言；`test_package` 也**不**依赖 X server。
- `catalog.tsv` 是本地生成物（`recipe-search` 重建），**绝不提交**（JC5）。
- 本机 `git status` 恒报 `archives/l/libXext/{README.md,manifest.yaml}` 变更 = **HMDFS 幻影**，不提交也不清理。
---

**编译结束**: 2026-10-08 00:55
**最终状态**: built
