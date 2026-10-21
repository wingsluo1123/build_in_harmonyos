# xlax 2.4 测试报告（HarmonyOS PC / aarch64）

- 生成时间：2026-10-17
- 目标：`xlax/2.4` → OpenHarmony / HarmonyOS PC aarch64（`os=OHOS os.version=6.0 arch=armv8`）
- 工具链：Conan 2.29.1 + clang 15（profile `ci/conan/profiles/ohos-aarch64`）
- 结论：上游测试 **N = 0**（无测试入口，取证见 §2）；适配新增鸿蒙消费者用例 **11 条 shell 断言 + 12 项程序化自检**，全部通过。

---

## 1. 源码与上游形态

| 项 | 值 |
|----|----|
| URL | `https://hea-www.harvard.edu/~fine/Tech/xlax2.4.tar.gz` |
| sha256 | `aae925379d15ccec6fa9f82b14096d14613c9d342820e515aa61052bbe9ad2dc` |
| 与 Debian orig 一致性 | 同一 sha256（`xlax_2.4.orig.tar.gz`） |
| 文件数 | 11（`Imakefile` `LICENSE` `README` `TODO` `dot-mkxlax` `mkxlax` `mkxlax.man` `vroot.h` `xlax.c` `xlax.h` `xlax.man`） |
| 构建系统 | 上游 Imake（`xmkmf`），OHOS 无该工具 → recipe 直接编译单一翻译单元 |

---

## 2. 上游测试入口核验（结论：无测试入口）

真实命令与原始输出：

```
$ ls -1 xlax2.4
Imakefile
LICENSE
README
TODO
dot-mkxlax
mkxlax
mkxlax.man
vroot.h
xlax.c
xlax.h
xlax.man

$ find xlax2.4 -iname "*test*" -o -iname "*check*"
(无输出)

$ grep -Ei "test|check" xlax2.4/Imakefile
(无匹配，退出码 1)

$ cat xlax2.4/Imakefile
#Imakefile for xlax
            DEPLIBS = XawClientDepLibs
    LOCAL_LIBRARIES = XawClientLibs
               SRCS = xlax.c
               OBJS = xlax.o
ComplexProgramTarget(xlax)
```

判定依据：

1. 发布包内无 `tests/`、无 `check_PROGRAMS`、无 `TESTS`、无任何测试脚本；
2. `Imakefile` 只有 `ComplexProgramTarget(xlax)`，Imake 体系里这意味着只有 `xlax` 一个 building rule，不存在 `check` 伪目标；
3. `README` 只描述 `xmkmf` / `make` / `make install` 与 `mkxlax` 手工起多窗口，无测试章节；
4. Debian 打包（`xlax 2.4-3`）的 `debian/rules` 只有 `dh $@`，补丁集只有 `typos / use-libbsd / fix-warnings / protos` 四个可移植性补丁，未引入测试。

因此 `make check` 等价入口**不存在**，上游测试统计恒为 0/0/0/0（§5）。

---

## 3. OHOS 适配点（源码级）

| # | 适配 | 补丁 |
|---|------|------|
| 1 | Imake → 直接编译（`XawClientLibs` = `Xaw Xmu Xt X11` 展开成 `-lXaw7 -lXmu -lXt -lX11 -lXext -lXpm -lm`） | 无（recipe 层） |
| 2 | 编译告警/类型修复（`XQueryTree`/`XGetWindowProperty` 计数改无符号、`Window` 用 `%lu`、`kcmap` 下标转 `unsigned char`） | `0001-fix-warnings.patch` |
| 3 | K&R → ANSI 原型（`WindowIndex` → `size_t`） | `0002-ansi-prototypes.patch` |
| 4 | 无头入口 `--version` / `--selftest` + `<string.h>` | `0003-headless-selftest.patch` |
| 5 | 不应用 Debian `use-libbsd.diff`（OHOS libc 自带 `strlcpy`，`<bsd/string.h>` 不存在） | — |
| 6 | `mkxlax`（Perl）装到 `share/xlax/` 而非 `bin/`（OHOS 基础系统无 perl） | 无（recipe 层） |

---

## 4. 真实构建

```
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=libxext/6.4.0.1 --build=libxpm/3.5.17 --build=xlax/*
（退出码 0；完整日志 archives/x/xlax/2.4/reports/conan-create.log）
```

编译行为真实 clang 调用（取自 `conan-create.log` 的 `RUN:` 行，路径已截断）：

```
xlax/2.4: RUN: $CC -std=gnu17 -O2 -Wall -Wno-unused-result -I"<dep>/include"… xlax.c -o xlax \
    -L"<dep>/lib"… -lXaw7 -lXmu -lXt -lX11 -lXext -lXpm -lm
```

产物引用：

```
xlax/2.4@ohpcd/stable: Full package reference:
  xlax/2.4@ohpcd/stable#c073691262f27b651a10ddf801942e8e:85b666b369f85d1e12dffd09f67543d888ff503d#f0bc2fe756272a70d81d8948a683dde2
```

依赖处置（经批准）：`libxext/6.4.0.1`、`libxpm/3.5.17` 因 `libxaw/libxmu` 的 `force=True libx11/1.8.13` 改变了 package_id（`minor_mode`），制品仓无对应二进制 → 本次从远端配方源码重建；其余 5 个依赖（libxaw/libxmu/libxt/libx11/xorgproto）严格使用已发布二进制。

---

## 5. 上游测试统计

| 项 | 值 |
|----|----|
| 测试命令 | 无（上游无测试入口，见 §2） |
| 用例总数 | 0 |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | 0 |
| 用例名称 | 无 |
| 日志路径 | 无（不适用于无测试套件的项目） |

说明：`test_package` **不**计入上游统计，单独列在 §6。

---

## 6. 适配新增的鸿蒙消费者用例（test_package）

命令（由 `conan create` 的 test 阶段真实执行）：

```
$ bash test_package/test_xlax.sh <package>/bin/xlax <package>
```

日志：`archives/x/xlax/2.4/reports/conan-create.log`，末行 `[step] 汇总: 11 passed, 0 failed`（退出码 0）。

| # | 用例名（脚本输出的 `[ok]` 行） | 断言内容 |
|---|------------------------------|----------|
| 1 | `bin/xlax 已装配且可执行` | 包内 `bin/xlax` 存在且可执行 |
| 2 | `share/man/man1/xlax.1 已装配且内容提及 xlax` | 手册页安装且内容相关 |
| 3 | `share/man/man1/mkxlax.1 已装配` | 第二个手册页安装 |
| 4 | `Perl 助手 mkxlax 与样例 dot-mkxlax 以数据形式装配在 share/xlax` | Perl 助手与样例配置作为数据安装 |
| 5 | `--version 输出 'xlax 2.4' 且退出码 0` | 上游 CLI 合约 |
| 6 | `xlax --selftest: 12 项检查全部通过` | 12 项程序化自检全绿 |
| 7 | `libXaw 的 widget class 记录在运行期可解析` | libXaw 的 widget class 记录在运行期真的读到 |
| 8 | `无显示启动按预期失败闭合，Xt 给出 display 诊断 (rc=1)` | 无 X server 时按预期失败（证明整条 X11 栈被加载初始化） |
| 9 | `装配后的可执行文件是 ELF64 AArch64` | 架构正确 |
| 10 | `可执行文件记录 libXaw/libXmu/libXt/libX11 的 DT_NEEDED` | 动态依赖完整 |
| 11 | `可执行文件未链接 libbsd` | 无 Debian 伪依赖 |

`--selftest` 的 12 项内部检查（真实运行输出，见 §7）：

```
ok   libXt headers report XtSpecificationRelease >= 6
ok   XtToolkitInitialize()/XtCreateApplicationContext() execute
ok   XtMalloc(64) returns memory from the libXt allocator
ok   libXaw exports the form widget class record
ok   libXaw exports the command widget class record
ok   libXaw exports the label widget class record
ok   libXaw exports the asciiText widget class record
ok   libXaw exports the scrollbar widget class record
ok   libXaw exports the toggle widget class record
ok   libXaw exports the viewport widget class record
ok   libXmu exports XmuClientWindow()
ok   libX11 headers report XlibSpecificationRelease >= 6
selftest: 12/12 checks passed
```

合计断言 11 + 12 = 23（不重复计入 §5 的上游统计）。

---

## 7. 运行期证据（包外独立复跑）

```
$ . conanrun.sh                      # VirtualRunEnv 生成的库路径
$ $PKG/bin/xlax --version
xlax 2.4                             # 退出码 0
$ $PKG/bin/xlax --selftest
… 12 条 ok …
selftest: 12/12 checks passed        # 退出码 0
$ DISPLAY= $PKG/bin/xlax -find
Error: Can't open display:           # 退出码 1（预期的失败闭合路径）
```

日志：`_scratch/xlax_w0/manual_checks.log`。

---

## 8. 安全检查与产物基线（L2/L4/L5 手工等价执行）

```
$ readelf -h bin/xlax | grep -E "Class|Type|Machine"
  Class:   ELF64
  Type:    DYN (Position-Independent Executable file)
  Machine: AArch64
$ readelf -lW bin/xlax | grep -E "GNU_STACK|GNU_RELRO"
  GNU_RELRO 0x0049a0 … R 0x1
  GNU_STACK 0x000000 … RW 0         # 无 E 位 → NX 生效
$ readelf -d bin/xlax | grep NEEDED
  libXaw.so.7 libXmu.so.6 libXt.so.6 libX11.so.6 libXext.so.6 libXpm.so.4 libc.so
$ ls -l bin/xlax ; sha256sum bin/xlax
  39296 B
  2ff987408362e2855fa90d409f6337ef410d19cb66106f7eeac5cd766212328f
```

结论：PIE ✅、NX ✅、RELRO ✅、无 `libbsd` ✅、无 RPATH/RUNPATH ✅。

---

## 9. 复现命令

```bash
conan create archives/x/xlax/2.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=libxext/6.4.0.1 --build=libxpm/3.5.17 --build=xlax/*
```

## 10. 证据文件

| 文件 | 内容 |
|------|------|
| `reports/conan-create.log` | 完整 `conan create` 输出（含补丁应用、编译命令行、test_package 逐条断言） |
| `reports/conan-verify-report.md` | G0–G5 门禁结论（PASS） |
| `reports/w3-local-ci.log` | 本地 CI 模拟（setup.sh + build_and_test.sh）完整日志 |
| `reports/test-report.md` | 本文件 |

> 说明：W4 提交前只读审计的结论快照（`reports/audit-result.json`）属本地流程产物，
> 不随 PR 提交（该文件已在 `.gitignore` 覆盖范围内，仅用于本地门禁复核）。

## 11. 本地 CI 模拟（W3）结果

`build_and_test.sh xlax/2.4` 以 prdiff 模式（**14 个变更文件**）执行，日志 `reports/w3-local-ci.log`：

| 门禁 | 结果 | 说明 |
|------|------|------|
| KC | pass | 知识完整性检查通过 |
| JC | pass | junk 检查（prdiff 模式，逐文件）通过 |
| L0a–L0k | pass | `L0_RESULT=pass: all checks passed`（含 L0e MANIFEST.yml、L0k software-level commands.json type=tool） |
| L1 | pass | `L1_RESULT=pass: test_package executed`（真实执行 test_xlax.sh，11 条断言） |
| L2 | **skip（非阻塞）** | `[warn] L2: xlax --version/--help failed (non-blocking)`；见下方说明 |
| L4 | pass | `patches clean` |
| L5 | pass | `bin/ has content` |

L2 说明：smoke 门禁直接执行包内二进制、未注入依赖库搜索路径。xlax 的 `DT_NEEDED` 含
`libXaw.so.7/libXmu.so.6/libXt.so.6/libX11.so.6/libXext.so.6/libXpm.so.4`，这些库在 Conan 缓存里
（不在系统默认搜索路径），因此裸执行会 `Error loading shared library libXaw.so.7`。
在运行时环境（`conanrun.sh` 提供的 `LD_LIBRARY_PATH`）下 `--version` 正常输出 `xlax 2.4`
（§7 实测）。CI 把该情形定义为 non-blocking，故记为 skip；本包不放 RPATH（遵循仓库约定）。

## 12. 收尾门禁（finish / finalize / packaging）

`python3 scripts/ohc-run.py finish xlax 2.4 built` 的逐步结果（日志 `finish9.log`）：

| 步骤 | 结果 | 证据 |
|------|------|------|
| Step 0 前置 | pass | `test-report.md ✅`、`.staging-verified ✅`、`conanfile.py ✅ (v3.0 配方)` |
| Step 1 补丁生成 | pass | `refresh-patch`：`无差异，保留现有补丁`（3 个补丁 sha256 未变） |
| Step 2 归档收尾 | pass | `manifest.yaml → built`、`.build-closed` 已创建 |
| Step 3 G0 clean-verify | 部分 | `✅ G0: 3 个补丁全部应用成功`；`❌ G0: configure 失败 (exit 127)` —— 见下方边界说明 |
| Step 4 质量验证 | pass | conan-verify `G1/G0/G2/G3` 全 PASS，`✅ 配方验证通过` |
| Step 5 W3 本地 CI | pass | §11，prdiff 14 文件全绿 |
| Step 6 归档校验 | **pass** | `✅ finalize-archive 通过`：缺失项 0、一致性问题 0、打包产物 2 |
| Step 7 知识图谱 W5 | 仓库级失败 | 本包 `unreferenced=0`（`✅ 知识完整性检查通过`）；但 `check_knowledge_completeness` 返回 1，因 96 个**历史** `E*.kv` 的 `root_cause`/`error_signature`/`rec_approach` 为空 —— 该批文件在 `origin/main` 上既已如此，本包 `knowledge/` 变更数为 0 |
| Step 8 SUMMARY | 框架缺陷 | `gen_summary 失败: 'str' object has no attribute 'append'`，在 main 仓库同样复现 |
| Step 9 W2 原子性 | pass（需独立复算） | finish 内部因 `origin/main...HEAD` 为空打印「无变更文件」（空集）；按同一 `_FRAMEWORK_PATHS` 对工作树 14 文件独立复算：框架 0 / 配方 14 → PASS |
| Step 10 submit 预检 | **pass** | `test-report.md ✅`、`packaging/ ✅`、`.staging-verified ✅`、`build-closed marker ✅` → `✅ submit 就绪` |

### Step 3 G0 的适用边界（非补丁缺陷）

`scripts/ohc/clean_verify.py` 面向 autotools 包：解压 tarball → 应用补丁 → **无条件**
执行 `./configure` → `make`。xlax 是 1992 年的 Imake 工程（`build_system: custom`，
OHOS 无 `imake`/`xmkmf`，配方直接用 clang 编译单一 `xlax.c`），源码树里没有 `configure`，
故 `exit 127`。G0 真正要证明的「补丁自包含」这一段已实测通过（`3 个补丁全部应用成功`，
干净 tarball 上按序 apply、无 fuzz 依赖）；补丁自包含性另有 conan create 的 3 条
`Apply patch (...)` 佐证。仓库内 583 个 `build_system: custom` 包同此状态。

### packaging 产物

`packaging/` 下按框架流程生成（该目录被 `.gitignore:2` 整目录忽略，不进 PR）：

| 文件 | 大小 | 内容 |
|------|------|------|
| `xlax-2.4-ohos-aarch64.tar.gz` | 57884 B | `bin/xlax`、`share/man/man1/{xlax,mkxlax}.1`、`share/xlax/{mkxlax,dot-mkxlax}`、`licenses/LICENSE` |
| `xlax-2.4-ohos-aarch64-debug.tar.gz` | 29207 B | `xlax.debug`（`--only-keep-debug` 分离） |

打包时对 `bin/xlax` 依次 `--strip-debug` → `--add-gnu-debuglink` → ELF 签名（`sign_single` RC=0）。
strip 后 34640 B、签名后 34624 B。**签名后用 conanrun 环境实测**：`--version` → `xlax 2.4`（rc=0），
`--selftest` → `selftest: 12/12 checks passed`（rc=0），未因剥离/签名失效。

### 未决项（均非本包可修）

1. `step5b`：仓库级 `check_knowledge_completeness` 因历史 `E*.kv` 字段为空恒返回 1，故 finish 退出码为 1；
   本包已把 5 条 `knowledge_gained` 全部加上真实 graph 引用（E1200/E1083/E1419/E637，第 4 条为对 E1993 的实测反驳），
   `check_knowledge_gap` 实测 `unreferenced=0`。
2. `gen_summary`：框架缺陷，main 可复现。
