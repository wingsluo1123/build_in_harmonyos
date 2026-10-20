# fonttosfnt 1.2.5 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 自带 `configure`，**不需要** `autoreconf`）
- 编译日期: 2026-10-18
- 编译器: clang 15（`/data/service/hnp/bin/clang`，经 profile `tools.build:compiler_executables` 注入）
- 平台: HarmonyOS PC aarch64（`uname -s` = `HarmonyOS`，`uname -r` = `HongMeng Kernel 1.12.0`）
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / compiler=clang 15 / Release）
- 状态: published

## 编译步骤

```bash
# W0 依赖发布核验（精确名，禁用通配 conan list）
conan download --only-recipe xorgproto/2025.1      -r=ohpcd   # OK
conan download --only-recipe freetype/2.14.3.2.1   -r=ohpcd   # OK
conan download --only-recipe libfontenc/1.1.7      -r=ohpcd   # OK
conan download --only-recipe zlib/1.3.1            -r=ohpcd   # OK

# 配方验证（G0-G4 + 消费者测试）
python3 scripts/ohc-run.py conan-verify fonttosfnt 1.2.5

# 收尾
python3 scripts/ohc-run.py finish fonttosfnt 1.2.5 published
```

`configure` 由 `AutotoolsToolchain` 驱动，实际命令行（conan create 日志原文）：

```
RUN: ".../b/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' \
     '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include'
```

三个 pkg-config 模块由 `PkgConfigDeps` 生成（`xproto.pc` / `freetype2.pc` / `fontenc.pc`
落在 generators 目录），`AutotoolsDeps` 另贡献整图 `CPPFLAGS/LDFLAGS`。

## 依赖版本

| 依赖 | 版本 | 用途 | 角色 |
|------|------|------|------|
| xorgproto | 2025.1 | `xproto >= 7.0.33`，X11 协议头（read.c 用 `X11/Xos.h`） | 头文件 |
| freetype | 2.14.3.2.1 | `freetype2`，read.c 用 FreeType BDF 驱动读 BDF/PCF（`FT_Open_Face`/`FT_Get_Font_Format`） | 共享库 |
| libfontenc | 1.1.7 | `fontenc`，read.c 用 `FontEncMapFind`/`FontMapReverse` 做非 ISO10646 重编码 | 共享库 |
| zlib | 1.3.1 | libfontenc 的传递依赖 | 共享库 |

⚠ **libfontenc 钉 1.1.7**：仓内 `archives/l/libfontenc/1.1.9` 已归档，但**未发布到 ohpcd**。
判据不能只看报错文本 —— `conan download --only-recipe` 对"不存在的名/版本"与"未发布版本"
返回**同一条**远程错误（`ERROR: error:system acceleration policy not enabled.`），
本轮用控制探针（bogus 名/版本 = `libfontenc/9.9.9`、`zzznotapkg/1.0`）确认这是
"未找到"的通用文案，才敢下"未发布"的结论（R35）。

## 遇到的问题与解决方案

| # | 问题（原文） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` + `can't create .../cgXXXXXX/dummy.c: Permission denied` | (a) 本包 `config.guess` 时间戳 2024-07-27，不认 `uname -s = HarmonyOS`（E007/E072）；(b) `set_cc_for_build` 用 `umask 077 && mktemp -d` 建 700 目录，HMDFS 拒写（E011/E114） | 补 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`；三处 `umask 077` → `022`（`patches/0001-config.guess.patch`） |
| 2 | `configure: error: cannot create a temporary directory` / `could not make ./config.status`（candidate 早期形态） | `configure` 的 config.status 临时目录 `umask 077 && mktemp -d "./confXXXXXX"`，HMDFS 上不可写（E011/E114） | 两处 `umask 077` → `022`（`patches/0002-configure.patch`）；config.status 在 configure 期继承该块，故必须真正写回磁盘 |
| 3 | `configure: error: cannot run C compiled programs.`（`config.log`：`Error loading shared library libfontenc.so.1: (needed by ./conftest)` + `libfreetype.so.6`，退出码 127） | `AutotoolsDeps` 把整图 `-L/-l` 注入 autoconf 首个 sanity 探针，conftest 因此链接 conan 共享库；OHOS 加载器默认搜不到 conan 缓存目录 | `generate()` 里把各依赖 `cpp_info.libdirs` 前置进 **build scope** 的 `LD_LIBRARY_PATH`（同签名既有先例：`xdriinfo/1.0.8`，另 aaphoto/0.45、dirb/2.22）。**保持 native 构建**（不传 `--build/--host`），三元组仍由打过补丁的 config.guess 解出 |
| 4 | `configure: error: could not make ./config.status`（分隔符自检 6 轮不收敛） | ⚠ **环境坑，非配方缺陷**：设备 `sed` 是 **toybox 0.8.12**（非 GNU sed），对含多字节字符的行处理不正确 | 换用**纯 ASCII 的 CONAN_HOME 路径**（见下节 A/B 对照）。⛔ 未为此改源码/加补丁 |

## 源码修改

两件补丁，全部落在 autotools **分发 shell 脚本**，由 `refresh-patch --auto`（编辑追踪器
精准模式）从 `.orig`/`.work` 差异生成（R7）：

| 补丁 | 内容 |
|------|------|
| `0001-config.guess.patch` | ① 在 `case $UNAME_MACHINE:$UNAME_SYSTEM:...` 分派首位插入 `*:HarmonyOS:*:*)` 分支，按 `$UNAME_MACHINE` 映射后 `GUESS=$MACHINE-unknown-linux-ohos`；② `set_cc_for_build` 的三处 `umask 077` → `022` |
| `0002-configure.patch` | config.status 临时目录的 `umask 077` → `022`（两行） |

- **全文无 `__OHOS__` 等平台预处理器宏**（R8/PF5）——只按 `uname -s` 的名字识别操作系统。
- **本包 `config.sub` 不需要补**：tarball 自带的已是新版，**已含** `ohos*`（第 2070 行）与
  `linux-ohos*`（第 2213 行）。实测 `config.sub aarch64-unknown-linux-ohos` →
  `aarch64-unknown-linux-ohos`（rc=0）。⚠ 因此**不能照抄 bdftopcf 的三件套**。
- **不用 `--build/--host` 绕过 config.guess**（适配检查清单 Autotools #4 / E566 的建议路线本轮
  未采用）：本包 `configure.ac` 有 `AC_CHECK_FUNC(setenv)`（决定 `NEED_SETENV` 条件编译 env.c）、
  `AC_CHECK_FUNCS(vasprintf)`、`AC_CHECK_DECLS(va_copy)` 三个探针，把它判成交叉编译会改变这三个
  探针的语义、写出错的 `config.h`。选定路线与 `xdriinfo/1.0.8` 一致：**native 构建 + 补
  config.guess**。

## 环境陷阱：CONAN_HOME 路径禁用非 ASCII（A/B 对照实证）

本轮最初按惯例把 CONAN_HOME 设为 `~/tmp/ch/home-主理7-fonttosfnt`，`conan create` 在
`configure` 末段必挂：

```
configure: creating ./config.status
configure: error: could not make ./config.status
```

深挖（`bash -x` 追踪 + 用注入钩子把中间件 `conf$$subs.awk` 捞出来保留）：

1. autoconf 2.72 的分隔符自检 `ac_delim_n=`sed -n "s/.*$ac_delim\$/X/p" conf$$subs.awk | grep -c X``
   在 `ac_delim` 长 **2184 字符**时，toybox sed 只匹配到 **125** 行；同一文件用 POSIX awk
   `index()` 计数是 **127** 行（= `ac_delim_num`，真值）⇒ 自检 6 轮不收敛。
   少的 2 行恰好是两个**值里含中文路径**的变量。
2. 就算放过这一关，config.status 内的 148 字节分行 `sed` 也会把含多字节的替换值切坏，
   生成的 `subs.awk` 出现引号失配：
   `gawk: ./confXXXXXX/subs.awk:6: S["FONTTOSFNT_LIBS!-L/.../home-\M-d\M-8\M-;\M-g\M-^P\M-^F7-...` →
   `unterminated string` → `config.status: error: could not create Makefile`。
   （`\M-d\M-8\M-;` = `主` 的 UTF-8 字节，`\M-g\M-^P\M-^F` = `理`。config.status 里三处
   引号失配的行，正是三个值里带中文路径的 `FONTTOSFNT_LIBS`/`FONTTOSFNT_CFLAGS`/`PKG_CONFIG_PATH`。）

**A/B 对照**（同一源码、同一配方、同一 `ci/conan/profiles/ohos-aarch64`，唯一变量是 HOME 路径）：

| CONAN_HOME | 结果 |
|---|---|
| `~/tmp/ch/home-主理7-fonttosfnt`（含中文） | ❌ `could not make ./config.status`；`LC_ALL=C` 复跑同样失败 |
| `~/tmp/ch/home-zhuli7-fonttosfnt`（纯 ASCII） | ✅ 一次通过：`config.status: creating Makefile / man/Makefile / config.h` → `executing depfiles commands` |

**结论**：这是**设备侧环境选择**问题（OHOS 自带 `sed` 是 toybox，不是 GNU sed），
与上游源码、配方均无关；CI worker 的路径形态为 ASCII，不受影响。⇒ 本轮把 CONAN_HOME
换成 ASCII 名，**没有为此改一行源码或加补丁**。附带记录一个反证：我先按"toybox sed 对
长正则失配"写了个 `sed`→`awk` 的 configure 补丁，换 ASCII 路径后**撤掉该补丁复跑仍然通过**
（`CONTROL CONFIGURE RC=0`），故该补丁**已回退、未进交付**（避免无谓偏离上游）。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify fonttosfnt 1.2.5
✅ 配方验证通过: fonttosfnt 1.2.5
  ✅ G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 L4 L5 PASS
```
- G3 原文：`无 lib/ 目录（纯可执行包）` + `无系统同名库冲突（R26 通过）`
  （设备 `/lib`、`/lib64` 下无 `libfreetype*`、`libfontenc*`，二者均为 conan 管理）
- `conan create` 内真实执行 `make check`：`man/` 报 `Nothing to be done for 'check'`，rc=0（上游无用例）
- 消费者测试（`test_package/test.sh`，调用已安装的 `fonttosfnt` 二进制）：

```
PASS 1: --version -> [fonttosfnt 1.2.5]
PASS 2: --help renders usage (rc=0)
PASS 3: no -o -> rc=1 + 'Missing required -o option'
PASS 4: unknown arg -> rc=1 + 'Unknown argument:'
PASS 5: -g without value -> rc=1 + 'Missing argument to'
PASS 6: fonttosfnt -o out.otb font.bdf -> rc=0, product present
PASS 7: product size = 772 bytes
PASS 8: sfnt version = 00 01 00 00
PASS 9: numTables = 13 (EBDT/EBLC/OS2/PCLT/cmap/glyf/head/hhea/hmtx/loca/maxp/name/post)
PASS 10: all 13 table tags present in table directory
PASS 11: head magicNumber 5F 0F 3C F5 present
PASS 12: stdin -> out.otb rc=0, sfnt version ok
PASS 13: -b -c -r -g 1 -m 2 -> rc=0, sfnt version ok
PASS 14: -g 0 -m 0 -> rc=0, numTables=10 (< 13), no glyf/loca
PASS 15: corrupt input -> rc=1 + "Couldn't open face"
PASS 16: missing input -> rc=1 + "Couldn't open face"
test fonttosfnt 1.2.5: 16/16 checks PASS
```

## 测试口径（五维账本，同源：本件 / manifest.yaml / test_package/MANIFEST.yml / reports/test-report.md）

| 维度 | 值 | 依据 |
|------|----|------|
| `N_static` 上游静态声明 | **0** | `Makefile.am`/`man/Makefile.am` 无 `TESTS`、无 `check_PROGRAMS`；`configure.ac` 无测试宏；全树无 test 目录（§12.72 四口径逐项 0，清点命令见 `test_package/MANIFEST.yml`） |
| `N_registered` 构建系统注册 | **0** | 同上，automake 未注册任何测试目标 |
| `N_executed` 实际执行 | **0** | `make check` 在 `build()` 内**真实执行**，`man/` 报 `Nothing to be done for 'check'`，rc=0（空转，无用例可跑） |
| 未执行分类数 | **0** | 无跳过、无预期失败、无条件注册项 |
| `N_consumer` 新增消费者测试 | **16** | `test_package/test.sh`，1 个消费者程序（`N_consumer_programs=1`），16 条可执行断言，实测 **16/16 PASS** |

## 未执行 / 未覆盖的检查

- 上游**没有**自动化测试套件（`N_static=0`），因此"上游测试通过率"分母为 0；
  按手册/04 §10 口径改以真实执行的消费者测试承载行为验证（真实 BDF→`.otb` 转换 +
  逐项解析 sfnt 结构），未声称跑过不存在的上游用例。
- `finish` step5b 的 `check_knowledge_gap` 对 `knowledge_gained` 行要求含 `ref:` 字样；
  本件各行均已带 `(ref: …)`，但该判据与全仓既有写法存在框架级矛盾（手册/04 §11.5②：
  仓内 4997 个非空包中 4623 个同为红），若本地显示红属**存量现象**、非本包缺陷。
- 本轮 `ohc-run.py build fonttosfnt 1.2.5` 一条龙**未跑通**（框架侧网络取数：
  `subprocess.TimeoutExpired: Command '['/data/service/hnp/bin/git', 'fetch', '--depth=1',
  'origin', 'main']' timed out after 30 seconds`，栈在
  `driver._step3_configure → dependency_resolver.get_package_for_tool → _get_index →
  _update_index_repo._fetch_update`，框架自身已退避重试 3 次；同源旁证：规则仓 `$P claims`
  报"离线：ls-remote 失败"）。按同族先例（§12.60①）改走模式 B：手工落配方 + 直接
  `conan-verify`，已全过。另：本 worktree 的模板文件为 `*.tmpl` 后缀而 `init_archive.py:139`
  找无后缀名，故 `init-build` 报"模板不可用"——同属框架类，无提交通道。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 配方（3 依赖、PkgConfigDeps+AutotoolsDeps、build-scope LD_LIBRARY_PATH、make check 真实执行） |
| `conandata.yml` | 官方直链 + 实测 sha256 + 2 件补丁声明 |
| `patches/0001-config.guess.patch` | HarmonyOS 分支 + umask 022 |
| `patches/0002-configure.patch` | config.status 临时目录 umask 022 |
| `test_package/{conanfile.py,test.sh,font.bdf,MANIFEST.yml}` | 消费者测试：真实 BDF→`.otb` 转换 + 16 条断言 |
| `manifest.yaml` / `notes.md` / `reports/` | 元数据与证据 |
| `archives/f/fonttosfnt/{manifest.yaml,commands.json}` | 软件级元数据 + CLI 声明（R38/PF8） |

## 注意事项

- 本包 `config.guess` 是 **2024-07-27 新版**（`GUESS=` 变量式，分支只赋值不 `exit`），
  与 bdftopcf 的 2017 老版（`echo <tuple>; exit ;;`）**写法不可互抄**。
- 消费者测试**必须落盘**一个真实 `.otb`（`writeFile` 用 `fopen("wb+")` 且要 `fseek` 回填
  校验和，不能像 bdftopcf 那样用 `-o /dev/null`）；脚本写进 `$TMPDIR` 下的 `mktemp -d`
  并在退出时删除，不往 `test_package/` 落任何文件（§12.71②）。
- 本包产物只有 `bin/fonttosfnt` 与 man 页，无库无头文件 ⇒ `package_type=application` +
  软件级 `commands.json`（R38/PF8）。设备 `/lib`、`/lib64` 无同名库，不触发 R26。

**编译结束**: 2026-10-18
**最终状态**: published（conan-verify G0-G4 全过；消费者测试 16/16 PASS）
---

**编译结束**: 2026-10-18 03:59
**最终状态**: published

---

## 附：断言 10「seen 为空」真红的根因与最终修法（2026-10-18 链主-116）

### 症状（CI 原文，逐字）

当前 HEAD `4c2590ab89` → build **#98688**（buildid 113332 / worker `OpenHarmonyPCDeveloper-CI-002`）
`results=2` / `state_string=failed 构建测试完成 (failure)`，首错取自 step5 `conan-build-test`
（logid 591742）：

```
PASS 9: numTables = 13 (EBDT/EBLC/OS2/PCLT/cmap/glyf/head/hhea/hmtx/loca/maxp/name/post)
FAIL 10: missing table tags: EBDT EBLC OS/2 PCLT cmap glyf head hhea hmtx loca maxp name post (seen: )
PASS 11: head magicNumber 5F 0F 3C F5 present
...
PASS 14: -g 0 -m 0 -> rc=0, numTables=10 (< 13), no glyf/loca
test fonttosfnt 1.2.5: 15/16 checks PASS
ERROR: fonttosfnt/1.2.5 (test package): Error in test() method, line 38
	ConanException: Error 1 while executing
```

⇒ 产物正确（772 B、numTables=13、head magic 5F0F3CF5 三项全 PASS），坏的只是「从二进制表目录抽 tag」。

### 根因（与前任判断不同，已实测定位）

**不是** bash 丢 NUL 字节（`dd … of=` 已落盘、也没有 null byte 告警），而是
**CI worker 的 PATH 让 `grep` 命中 toybox 0.8.12**：

- CI 日志 `environment:` 段逐字：`PATH=/data/app/bin:/system/bin:/system/sbin:/vendor/bin:/storage/Users/currentUser/.local/bin`
  （`/data/app/bin`、`/system/sbin`、`/vendor/bin` 在该 worker 上不存在）⇒ `grep`/`od`/`tr`/`dd`/`sort`
  全部落在 **`/system/bin/toybox` 0.8.12**（`/data/service/hnp/bin` 只进 build 步骤的 buildenv，
  不进 test_package 的 runenv）；测试进程本身是 `/data/service/hnp/bin/bash`（5.3）。
- toybox 0.8.12 `grep` 在本产物的 **208 字节二进制表目录**上：

  | 命令（同一 dir.bin / 同一 worker PATH） | 结果 |
  |---|---|
  | `grep -a -o -E 'EBDT\|EBLC\|…(13 个交替式)'  dir.bin` | **空集** ← 本包实际用的形态 |
  | `grep -a -o -E 'EBDT'  dir.bin`（单模式） | `EBDT`（有输出） |
  | `grep -a -o -e EBDT -e EBLC dir.bin` | `EBDT`（有输出） |
  | `grep -o -E 'EBDT\|EBLC\|…' dir.bin`（无 `-a`） | `Binary file dir.bin matches` |
  | 同一条命令在本机 **GNU grep 3.12** | 13 个 tag 全出 |

  ⇒ 触发条件是「**交替式 `-E` + `-o` + 二进制输入**」三者同时成立 ⇒ 静默空集；
  又因命令带 `2>/dev/null`，错误被吞、`seen` 空、断言 10 必 FAIL。
  这解释了「本机 16/16 而 CI 15/16」的分裂：**不是 shell NUL 语义，是 grep 实现差异**。

### 已试过的失败方案（不要再重复）

1. `dir=$(dd … bs=1 skip=12 count=208)` + `printf '%s' "$dir" | grep -a -o -E …`
   → CI 丢 NUL 告警 + `seen` 空（build #98154 / buildid 112796 / worker CI-013）。
2. `dd … of="$d/dir.bin"` 落临时文件后再 `grep -a -o -E … "$d/dir.bin" | sort -u | tr`
   → 无告警但 `seen` 仍空（build #98688）——**根因未变，换载体无用**。

### 最终方案（只改 `test_package/test.sh`，判据与分母不动）

新增 `sfnt_tags()`：**只用 `od` 的十六进制文本通道**（`od -An -v -tx1 "$f" | tr -d ' \n'`，
该通道已由断言 8/9/11 在同一 worker 上证明可用），按 sfnt 表目录结构切片
（offset 12 起、每表 16 B ⇒ 每 32 个 hex 字符取前 8 个为 tag 的十六进制形），
再在**纯 shell `case`** 里与 13 个 tag 的 hex 常量比对。⇒ 全程不经 `grep`/`sort`，
不把二进制塞进命令替换，也不依赖具体 coreutils 实现。断言 10、14 共用它。
断言 14 按主理裁定**加空集守卫** `[ -n "$tags0" ]`（空集即 FAIL）——原来是空集恒真的**空过**
（旧 CI 日志确实 PASS 14）。

### 本机复现与验证（同一 CI shell + 同一 CI PATH + 真实产物，非「本机过」）

| 项 | BEFORE（HEAD 4c2590ab） | AFTER（本提交） |
|---|---|---|
| 断言 10 | `FAIL 10: missing table tags: … (seen: )` | `PASS 10: all 13 table tags present in table directory` |
| 断言 14 | PASS（tags0 空 ⇒ 空过） | PASS（tags0 实读 10 个 tag：`EBDT EBLC OS/2 PCLT cmap head hhea maxp name post`，非空、无 glyf/loca） |
| 合计 | **15/16** | **16/16** |

执行环境：`/data/service/hnp/bin/bash` 5.3 + `PATH=<pkg bin>:/data/app/bin:/system/bin:/system/sbin:/vendor/bin:…/.local/bin`
（grep/od/tr 实测均解析到 `/system/bin`），产物为本包真实 772 B `out.otb` 与 696 B `g0.otb`。
另：`conan-verify fonttosfnt 1.2.5` G0–G4 全过（G2 `conan create` 含 test_package 真实执行）。

### 结构性备注

- 断言 10/14 之外未删断言、未改期望值、未把 FAIL 改 SKIP、未动 `N_consumer=16` 分母，
  未动 `conanfile.py` 构建/打包逻辑与上游源码。
- 同类教训（建议）：**消费者测试脚本里凡是要从二进制产物里取字节/字符串的断言，
  一律走 `od -An -v -tx1` 文本通道 + 纯 shell 解析**，不要 `grep -o -E` 二进制、
  也不要把二进制放进 `$( )`；CI worker 的 coreutils 是 toybox 0.8.12，与设备侧 GNU 行为不同。
