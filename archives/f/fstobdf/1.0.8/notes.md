# fstobdf 1.0.8 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 已内置生成好的 `configure`）
- 编译日期: 2026-10-16
- 编译器: clang / clang++（`/data/service/hnp/bin/clang` 15.0.4，toolchain 由 Conan `AutotoolsToolchain` 注入）
- 目标平台: ohos-aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

```bash
# 配方目录 archives/f/fstobdf/1.0.8 的 build() 内部即：
#   apply_conandata_patches()   -> 0001 config.guess、0002 configure
#   Autotools.configure()       -> conan 传 --prefix=/ 与各子目录 + pkg-config 视图
#   make -j1                    -> 5 个 C 单元，无上游测试套件
conan create archives/f/fstobdf/1.0.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# configure 关键行（实测）：
#   checking for a BSD-compatible install... /storage/.../usr/local/bin/ginstall -c
#   checking for FSTOBDF... yes          <- PKG_CHECK_MODULES(xproto >= 7.0.25 x11 libfs)
#   config.status: creating Makefile / man/Makefile / config.h
# install 实测：
#   ginstall -c -m 644 fstobdf.1 <pkg>/share/man/man1
#   ginstall -c fstobdf          <pkg>/bin
```

## 遇到的问题与解决方案（每行均为本机真实读数）

| # | 适配点 | 首条真实错误原文 | 处置 |
|---|--------|------------------|------|
| 1 | `config.guess` 不认识 `uname -s = HarmonyOS` | `configure: error: cannot guess build type; you must specify one`（同次输出上下文：`uname -s = HarmonyOS` / `UNAME_MACHINE = "aarch64"`） | 补丁 0001：在 `case $UNAME_MACHINE:$UNAME_SYSTEM:…` 前插 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`（E007 完整命中）。⛔ 不用 `--build/--host` 绕过（会让 autoconf 当成交叉编译、跳过 `AC_RUN_IFELSE`，产出错误 `config.h`） |
| 2 | `config.status` 临时目录用 `umask 077 && mktemp -d` 建出 700 目录，HMDFS 拒写 | `./config.status: line 593: ./conf5hU5rv/subs1.awk: Permission denied` 紧接 `config.status: error: could not setup config files machinery` | 补丁 0002：改成 `tmp=./conf$$-$RANDOM` + `(umask 022 && mkdir "$tmp" && chmod 755 "$tmp")`（E129 推荐做法；E110/E112 同域） |
| 3 | GNU make 的 jobserver 需要 FIFO，本平台 `mkfifo` 被拒 | `make: jobserver mkfifo: /storage/Users/currentUser/GMfifo42366: Operation not permitted` | 配方固定 `make -j1`（本包仅 5 个 C 单元，串行编译耗时无影响） |
| 4 | 同族「三补丁模板」里的 `config.sub` 补丁对本包**不需要** | 非错误，实测读数：`./config.sub aarch64-unknown-linux-ohos` → 原样回显 `aarch64-unknown-linux-ohos`，`rc=0`（其 OS 白名单已含 `ohos*`、内核-OS 白名单已含 `linux-ohos*`，见 `config.sub:2070` / `:2213`） | **不携带** config.sub 补丁（appres / fslsfonts / bdftopcf 各带了它，是因为那些 tarball 的 config.sub 较旧）。教训：领同族包先跑 `./config.sub <triplet>` 探针再决定补丁集 |
| 5 | HMDFS 下 `pwd`(getcwd) 在「父目录不可达」时失效，configure 自检中止 | `configure: error: working directory cannot be determined`（同次上下文逐字：`shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported`、`pwd: error retrieving current directory: getcwd: cannot access parent directories: No error information`）—— 出自 G0 干净构建验证日志（`~/ohc-verify-fstobdf-*/g0-configure.log`） | 补丁 0002 前半：`ac_pwd=\`pwd\` || ac_pwd=$PWD`（E386 家族；与已合入同族 `fslsfonts 1.0.7` / `xcmsdb 1.0.7` 的既有 hunk 一致）。⛔ 不设 `os.environ["PWD"]`（E386 `forbid_2` 明文反对 `os.environ.*CONFIG_SHELL` 一类配方侧注入）。⚠ **如实披露**：本环境下该 cwd 失效更彻底（`cd $ac_pwd` 亦失败），打上本 hunk 后错误前移为 `configure: error: pwd does not report name of working directory` ⇒ **本 hunk 不能使 G0 通过**；而该 G0 失败非阻塞（SKILL Step 3 明标 clean-verify 非阻塞；同族 `bdftopcf`/`appres`/`liblksctp` 均有同款记录），事后复查该目录 `pwd` 与 `ls -di` 均正常 ⇒ 属验证期间一次性 cwd 失效。**CI 权威路径（`conan create`）不需要本 hunk**（真实构建目录内子进程 `pwd` 实测 rc=0、stderr 为空） |
| 6 | pkg-config 视图陷阱：`libx11` 包内自带的 `x11.pc` 的 `prefix` 是 `/` | `chars.c:49:10: fatal error: 'X11/Xlib.h' file not found`（此时 `configure` 却是**通过**的：`checking for FSTOBDF... yes` —— 因为 `pkg-config --cflags x11` 解析出死路径 `-I//include`） | 必须用 **PkgConfigDeps 生成到 generators 目录**的 `x11.pc`（绝对路径正确），而不是依赖包内 `lib/pkgconfig` 的自带件。配方 `generate()` 里 `PkgConfigDeps(self).generate()` + `VirtualBuildEnv(self).generate()` 即为正解 |
| 7 | `xorg-macros` 未安装的 pkg-config 告警（非致命） | `Package xorg-macros was not found in the pkg-config search path.` / `No package 'xorg-macros' found` | 无需处置：`XORG_MACROS_VERSION` 只在 autoconf 期展开，tarball 内 `configure` 已把宏体内联，configure 继续并 `rc=0`（随后 `config.status: creating Makefile` 全过）。如实披露，不掩盖 |
| 8 | `install -c` 在本平台**未失败**（与 fslsfonts / xcmsdb 结论相反） | 非错误，实测读数：`checking for a BSD-compatible install... /storage/.../usr/local/bin/ginstall -c`；`make install` 中 `ginstall -c -m 644 fstobdf.1 …` 与 `ginstall -c fstobdf …` 均成功，整体 `install rc=0` | **不携带** install shim（appres 同样不带）。附带发现：fslsfonts 的 shim 改写条件是 `"/install" in line`，而实际值是 `.../bin/ginstall`（不含子串 `/install`）⇒ 该 shim 从未生效，属无害死代码。E182/E188 描述的是 toybox `install` 路径，本平台 configure 解析到 GNU `ginstall` |
| 9 | G0 预警 E490（autotools 辅助脚本可能丢失可执行位） | G0 原文：`⚠️ 已知风险 E490 未在配方中处理 … ⚡ G2 conan create 可能因此失败，建议先修复` | 实测**不成立**：`configure` 正常执行并产出 `config.status`，说明 Conan `get()` 解包与 `apply_conandata_patches` 后脚本可执行位保留 ⇒ 不加 `chmod +x`（R1 最少化；且 E386 `forbid_1` 反对 blanket `chmod +x`） |
| 10 | W3 本地 CI 的 JC 门禁对**过期基线**误报（非本包缺陷） | `[FAIL] JC6: 本 PR 涉及 1209 个软件包，违反 W2 单软件原子性`；`[FAIL] JC1: 4 个运行时状态文件被跟踪` 与 `[FAIL] JC5: 4 个 archives 下未登记的隐藏文件`（这两条点名的 4 件均为**他人**的 `archives/{k,l,o,r}/…/.staging-verified`） | 实测 `origin/main` 落后 `upstream/main` **2532 个提交** ⇒ JC6 把上游所有既有新增都算成本 PR 改动。按 AGENTS §8「基线可能过期」+ 本仓既定做法，用 **`JUNK_PR_DIFF=<本包 diff>`** 把 JC 口径对齐 CI 的 prdiff 范围后复跑 |

## 源码修改

| 补丁 | 文件 | 类型 | 说明 |
|------|------|------|------|
| 0001-config.guess.patch | config.guess | portability | 补 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos`（E007） |
| 0002-configure-hmdfs-pwd-tmpdir.patch | configure | portability | ① `ac_pwd` 失败时回退 `$PWD`（E386 家族）；② `config.status` 临时目录 `umask 077 + mktemp -d` → `umask 022 + mkdir + chmod 755`（E129/E110/E112） |


两件均为对上游随 tarball 分发的 autotools **分发脚本**的移植性修复，**不含任何平台预处理器宏**（R8/PF5 合规）；
上游 C 源码（chars.c / fstobdf.c / header.c / props.c / fstobdf.h）**零改动**。
两件补丁在干净 tar 原件上用 `patch -p1` 逐件实打验证：输出 `patching config.guess` / `patching configure`，`rc=0`。

## 依赖版本

- **libfs/1.0.10** — 提供 `X11/fonts/FSlib.h`、`libFS.so.6`、`libfs.pc`；经 W0 精确复证已发布
- **libx11/1.8.13** — 提供 `x11.pc` 与 `X11/Xlib.h`（chars.c 直接 include）；同族 `libxt/1.3.1` 亦钉此版本，`6.4.0` 会与 X11 app 族冲突
- **xorgproto/2025.1** — 提供 `xproto.pc`（实测 7.0.34 ≥ 上游要求的 7.0.25）与 `X11/Xosdefs.h`

W0 证据（R35 口径：用精确 `conan install --build=never`，⛔ 不用通配 `conan list` 判 binary）：
`conan install` 实测从 ohpcd 下载 7 个二进制（libfs/1.0.10、libx11/1.8.13.1、xorgproto/2025.1、
libxau/1.0.12、libxcb/1.17.0.1、libxdmcp/1.1.5、xtrans/1.6.0）并 `Install finished successfully`，`EXIT=0`。

## 验证结果

```bash
# 官方验证（conan-verify，含真实 conan create）RC=0
python3 scripts/ohc-run.py conan-verify fstobdf 1.0.8
#   G0 PASS / G1 PASS / G2 PASS（conan create 成功）/ G3 PASS（无 lib/，纯可执行包）/ G4 PASS
#   L2 / L4 / L5 输出「跳过（无 cache 路径）」= 工具在无 cache 路径时的既有行为，非实质检查通过

# test_package 实测（reports/conan-create.log，真跑二进制）
# PASS 1: binary resolved -> <pkg>/bin/fstobdf
# PASS 2: -version -> 'fstobdf 1.0.8' on stdout, rc=0, stderr empty
# PASS 3: no arguments -> 'No font name specified' + usage on stderr, rc=0, stdout empty
# PASS 4: '-fn' without value -> '-fn requires an argument', rc=0
# PASS 5: '-server' without value -> '-server requires an argument', rc=0
# PASS 6: '-bogus' -> "unrecognized option '-bogus'", rc=0
# PASS 7: '-fn fixed' with no font server -> 'No font server specified.', rc=0, no BDF emitted
# PASS 8: man page installed -> <pkg>/share/man/man1/fstobdf.1 (2645 bytes)
# NEEDED: libX11.so.6 libxcb.so.1 libXdmcp.so.6 libXau.so.6 libFS.so.6 libc.so
# PASS 9: dependency closure complete
# fstobdf 1.0.8 test_package: declared=9 passed=9 skipped=0 failed=0

# 负向对照（证明断言真的会咬，不是恒真/空壳）
# A) 把断言 2 的期望改成 'fstobdf 1.0.9' -> conan create rc=1，
#    FAIL: -version stdout is not exactly 'fstobdf 1.0.8': [fstobdf 1.0.8]
# B) 把断言 7 的「不得输出 BDF」守卫取反 -> conan create rc=1，
#    FAIL: no-server run emitted BDF on stdout: []
# 还原后（与备份 diff 逐字节相同）复跑：conan create rc=0，9/9 通过
```

上游测试清点（N_static = 0，无对比基线）：
`find . -type d -name 'test*'` → 0；`grep -rE 'TESTS|check_PROGRAMS|check_SCRIPTS' Makefile.am man/Makefile.am configure.ac` → 0 命中（rc=1）；
无 `tests/`、无 `t/`；源码仅 4 个 `.c` + 1 个 `.h`。
⇒ 全部测试均为 test_package 自造消费者断言，**声明数 = 实测执行数 = 9**。

## 注意事项

- **运行期能力面（如实披露）**：fstobdf 的主功能路径（从 font server 导出字体并打印 BDF）需要**可达的 X Font Server**（`FONTSERVER` 环境变量或 `-server <host:port>`），构建/CI 环境不提供 font server。因此 test_package 只断言不依赖服务器的路径，以及「无服务器时按上游文档干净退出」的路径；这是运行期能力墙，不是本次适配引入的缺陷。
- **上游 `usage()` 以 `exit(0)` 结束**（`fstobdf.c:56-62`，上游行为），故所有用法错误路径的退出码都是 0。负向对照因此落在 **stderr 文案 + stdout 为空 + 不得输出 BDF** 三条上，而不是退出码 —— 断言 7 的「stdout 不得出现 STARTFONT/ENDFONT」即为此设计。
- 上游**没有 `-help`**（`-help` 走 `unrecognized option` 分支），与同族 fslsfonts 不同，故断言未沿用 fslsfonts 的 `-help` 用例。
- 构建目录与 `CONAN_HOME` 一律使用纯 ASCII 路径（本任务 `CONAN_HOME=~/tmp/ch/home-fstobdf`）：同族实测过 toybox `sed` 对含 UTF-8 行做 `.*…$` 匹配会失配。

### 对话记录 #1（2026-10-16，链主-fstobdf / 主理-5 派发）

- **W0**：`preflight_check.sh fstobdf/1.0.8` → `[OK] 预检通过（无依赖需要检查）`（conanfile 尚未生成，符合预期）；
  `recipe-search fstobdf` → `⚠️ 无相似配方（语料 9338 条）—— 首稿走 conan-init 模板`（同族 fslsfonts 尚未合入语料）；
  依赖用**精确 `conan install --build=never`** 复证（R35）：7 个二进制全部从 ohpcd 下载成功、`EXIT=0`。
- **`build` 一键**：`EXIT_REASON=init_build_failed`、`EXIT_CODE=2`、`STEP_FAILED=Step1`；首条真实错误逐字
  `❌ 源码目录不存在: …/archives/f/fstobdf-1.0.8/src`（自动 URL 搜索还给出与本题无关的 Savannah 地址）。
  根因：`scripts/software-registry.yaml` 无 `fstobdf`（自主提名的外部候选）⇒ 按先例走 `init-build --url=<官方源>`
  建立骨架 + 上下文，配方就位后直接 `conan-verify`（其 `conan create` 不触发 init）。
- **补丁**：由 `~/builds/fstobdf-1.0.8.orig`（tar 原件）与改动副本逐文件 `diff -u` 生成，而非手写。
  生成前先做**mtime 保真**复核 —— 首次探索用 `cp -r` 让 `aclocal.m4` 的 mtime 早于 `configure.ac`，
  诱发了假故障 `missing: line 85: aclocal-1.18: command not found`；改用 `cp -a`（真实 tar 顺序：
  `aclocal.m4` 1776548631 > `configure.ac` 1776548629）后该故障消失 ⇒ **判为探索脚本假象，不计入适配点**。
- **配方手写**：模板生成器对本包不可用（`conanfile.py`/`conandata.yml`/`test_package` 模板均报
  "模板不可用，跳过"），故按同族 `fslsfonts 1.0.7`（同为 libfs 客户端）+ `appres 1.0.7` 的既有形态落笔，
  再按本包实测**做减法**：去掉 **config.sub 补丁**（本代 tarball 已支持 ohos 三元组）与 **install shim**
  （`ginstall -c` 实测成功）两处；`$PWD` 兜底一度按 conan 构建目录探针去掉，随后 G0 干净构建验证
  实测到 `working directory cannot be determined`（见上表第 5 行）⇒ **恢复携带**（与同族一致，
  仅作 HMDFS 降级，不设 `os.environ["PWD"]`）。
- **W3 / conan-verify**：`conan-verify` **一次通过**（G0–G4 + L2/L4/L5，RC=0），test_package 9/9。
- **负向对照**：两处注入故障各实测一次（见上），均 `conan create rc=1` 且 FAIL 行正确，还原后复绿。
- **`finish` 首轮**：`EXIT_REASON=w3_local_ci_failed` / `STEP_FAILED=Step5`，JC 门禁 3 条全红。
  逐条归因后确认**三条都不是本包缺陷**：JC1/JC5 点名的 4 件 `.staging-verified` 属他人归档；
  JC6 的「1209 个软件包」源于 `origin/main` 落后 `upstream/main` 2532 个提交（过期基线假阳性）。
  处置：用 `JUNK_PR_DIFF=<本包 pr.diff>` 对齐 CI 的 prdiff 口径后复跑（AGENTS §8 明文做法）。
- **G0 clean-verify**：报 `working directory cannot be determined` → 应用 `$PWD` hunk 后错误前移为
  `pwd does not report name of working directory`，仍失败；该步**非阻塞**（SKILL Step 3 明标），
  且同族 `bdftopcf`/`appres`/`liblksctp` 有同款记录；事后复查该目录 `pwd`/`ls -di` 均正常 ⇒ 判一次性 cwd 失效。
- **不携带项的依据**：E490 实测不成立、appres 先例（无 install shim）、fslsfonts 日志实证（其 shim 从未命中改写条件）、
  本代 config.sub 实测已支持 ohos 三元组。
- **B 判定建议**：`hit` —— config.guess 面 E007 完整命中（同症状同解法），HMDFS 临时目录面 E129/E110/E112 命中，
  getcwd/shell 面 E386 覆盖；本包未产生知识库未覆盖的新机制。`recipe-search` 语料 0 相似、
  历史归档 `git log --all -- 'archives/f/fstobdf*'` = 0 提交（本目录为新建）。
---

**编译结束**: 2026-10-16 14:47
**最终状态**: built
