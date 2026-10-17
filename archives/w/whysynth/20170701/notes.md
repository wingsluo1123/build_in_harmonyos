# whysynth 20170701 适配笔记

## 概览

| 项 | 值 |
|---|---|
| 上游 | https://github.com/theabolton/whysynth |
| 版本/tag | 20170701（commit c4559ca4a4f5d6bea0a5473e0d564edf08ab9582） |
| 源码包 | https://github.com/theabolton/whysynth/archive/refs/tags/20170701.tar.gz |
| sha256 | 217671b105005f0a0fdc09ad2f922c40c896269a1503b59db1462702b8cc2e21 |
| 语言/构建 | C / autotools（`lang-preflight` 实测 detected=c） |
| 产物 | `lib/dssi/whysynth.so`（DSSI 插件模块，libtool `-module -avoid-version`） |
| 平台 | HarmonyOS PC / aarch64，**原生 build=host**（不使用 `--build/--host/--target`） |
| 交付形态 | 不是库、也不是命令行工具 → 软件级 **不需要** `commands.json`（CI 的 L0k 实测输出 `library package, commands.json not required`） |

whysynth 是一个 DSSI 软件合成器插件，消费方是 DSSI 宿主；它和本仓
`dssi/1.1.1` 的示例插件装在同一个目录 `lib/dssi/`。

## 依赖

| 依赖 | 用途 |
|---|---|
| dssi/1.1.1 | `dssi.pc`：dssi.h / ladspa.h / alsa 头 |
| **fftw3f**/3.3.10 | `fftw3f.pc`：PadSynth 振荡器的单精度 FFT |
| liblo/0.32 | `liblo.pc`：configure 强制要求（GUI 用 OSC） |
| alsa-lib/1.2.16.1 | `alsa.pc`：插件链接 libasound；DSSI 事件用 `snd_seq_event_t` |

### 关键坑：FFTW 精度 —— 必须用 fftw3f 而不是 fftw

上游 `configure.ac` 写的是 `PKG_CHECK_MODULES(PLUGIN, fftw3f >= 3.0.1)`，
而本仓 `fftw/*`（3.3.10 / 3.3.10.1~.3 / 3.3.11）**全部只建 double 精度**：
装出来的 `lib/pkgconfig/` 下**只有 `fftw3.pc`，没有 `fftw3f.pc`**。

单精度是**独立的包** `fftw3f/*`（`pkg_config_name = "fftw3f"`，3.3.10 的
recipe 里 `ENABLE_FLOAT=ON`），已在 ohpcd 发布 OHOS 二进制。所以这里
`requires("fftw3f/3.3.10")`；写成 `fftw/3.3.10` 会让 configure 直接报找不到 fftw3f。

## 引导（bootstrap）与平台识别

tag 归档里**只有 `configure.ac`/`Makefile.am`，没有 `configure`/
`Makefile.in`/`config.guess`/`config.sub`**，所以必须在 build() 里现场引导
（`autoreconf -fi`）；automake/libtool/m4/autoconf 走 `tool_requires`
（zvbi 0.2.44、rnnoise 同款）。

平台识别按 **E007 的正解**处理，**没有**用 `--build/--host/--target`：

* 本机 `uname -s` 是 `HarmonyOS`（不是 `Linux`），老 config.guess 会
  "cannot guess build type"；
* 做法是在 `autoreconf -fi` **之后**把 `autoconf/2.72` 制品里
  `share/autoconf/build-aux/` 的 `config.guess`/`config.sub` 覆盖进源码树，
  然后断言一次三元组：

  ```
  WHYSYNTH_NATIVE_TRIPLET=aarch64-unknown-linux-ohos
  ```

  认不出来就硬失败（把根因钉在 config.* 上，而不是让 configure 报含糊的
  "cannot guess build type"）。

**为什么必须放在 autoreconf 之后**：`autoreconf -fi` 会给 automake 传
`--force-missing`，把 config.guess/config.sub 换回工具包自带的那份，放前面会被覆盖。

**为什么用 conan 制品里那份、不用设备 `/data/service/hnp` 下同名 2.72 的**：
制品里那份已经按 `scripts/patch-autotools-ohos.pl` 打过 OHOS 补丁（多了
`*:HarmonyOS:*:*` 分支），设备安装的是原版；原版在新版 autotools-dev 逻辑下
会走**编译探针**，而探针建临时目录用 `umask 077`（0700），本机 HMDFS 上 0700
目录不可写（E011），于是探针必然失败、config.guess 直接 exit 1。

**为什么不用更新的 autotools-dev 20240727**：同一原因——它把"按 uname 静态
判定"全换成了编译探针（实测 `config.guess[1741]: can't create
.../cgGNGbFa/dummy.c: Permission denied`）。

### 另外两个引导坑

* 仓里提交的那份 `aclocal.m4` 首行是 `# libtool.m4 - Configure libtool ...`，
  不含 `generated ... by aclocal` → autoreconf 的护栏会判定"本包不用 aclocal"，
  **整体跳过 aclocal 和 automake**，随后 configure.ac 里的
  `AM_INIT_AUTOMAKE`/`AM_CONFIG_HEADER`/`PKG_CHECK_MODULES` 全部报
  "possibly undefined macro"。修法是先删掉这份陈旧 aclocal.m4（等价于上游
  `autogen.sh` 里那句 `aclocal`）。
* conan perl 与设备自带 perl 的二进制模块 ABI 不兼容（实测设备 perl 加载
  conan perl 的 `Cwd.so` 报 `Perl_my_cxt_init: symbol not found`）。统一到
  automake 脚本 shebang 里的那个 perl（设备自带），并把 `PERL5LIB` 只指向
  automake 自己的模块目录。

## GUI（WhySynth_gtk）不构建

上游把 GTK+2 GUI 当可选项：`AM_PATH_GTK_2_0(2.24.0, with_gtk=yes,
AC_MSG_WARN([GUI will not be built...]))`，找不到就只打警告、不装
`WhySynth_gtk`。本次不引入 gtk2：GUI 需要显示设备，真机无法驱动更无法断言，
而交付物是 DSSI 插件本体。构建日志里能看到 configure 的 "GUI will not be
built" 警告，这是预期行为——**但要小心**：

「GTK+ 没装」与「gtk-2.0.m4 没装」是两回事。构建机没有 gtk-2.0.m4 时
`AM_PATH_GTK_2_0` 这个宏**根本没有定义**，autoconf 会以
`possibly undefined macro: AM_PATH_GTK_2_0` **直接失败**，连可选项都轮不到。
`patches/0001-configure.ac.patch` 把这次调用包进 `m4_ifdef` 修的就是这一点，
语义不变：有宏的机器照旧探测 GTK+，没宏的机器照旧跳过 GUI。

## 上游测试清点（R51）

**上游无测试套件**（本次实测复查，证据如下）：

* 解包的源码树顶层只有 `AUTHORS/COPYING/ChangeLog/INSTALL/Makefile.am/
  README.rst/TODO/aclocal.m4/autogen.sh/config.h.ac/configure.ac` + `doc/`
  `extra/` `src/`；`find . -type d -iname '*test*'` **无命中**
* `Makefile.am` 与 `src/Makefile.am` 里 **没有** `TESTS`、`check_PROGRAMS`、
  `check-local`（grep 无命中，rc=1）
* 没有 `CMakeLists.txt` / `src/CMakeLists.txt` / `meson.build`
* `src/` 下 24 个 `.c`，其中 18 个属于插件目标 `whysynth_la_SOURCES`
  （其余是 GUI 的 `gui_*.c`/`gtkknob.c`，本次不构建）

因此 `build()` 里没有 `make check`（无处可调），上游测试计数为
**TOTAL=0（NOT_RUN=0）**，真实功能验证全部由 `test_package/` 承担
（消费者测试，见下）。这不是"没环境跑"，是"上游确实没有"。

## 消费者测试（test_package）：最小 DSSI 宿主

`test_package/test_whysynth.c` 不是「dlopen 成功就算过」的探针，而是按 DSSI
宿主的最小流程真的把插件跑起来：

1. `dlopen(<pkg>/lib/dssi/whysynth.so)`（鸿蒙上必然要求 `.codesign`）
2. 取 `ladspa_descriptor`/`dssi_descriptor`，核对 UniqueID 2187、
   Label `WhySynth`、198 个端口、端口 0/1 是音频输出、2..197 是控制输入
3. `instantiate(44100)` —— 这一步走 `sampleset_instantiate()`，启动
   sampleset 的非实时 worker 线程
4. `connect_port` 接满 198 个端口（控制口初值见下），再 `select_program(0,0)`，
   断言插件把内建默认 patch 写回了宿主缓冲区（DSSI 端口往返）
5. `configure("polyphony","8")` 走接受路径、`configure("polyphony","999")`
   走拒绝路径（后者在 `y_synth_handle_polyphony` 里必然返回错误消息）
6. `activate` + `run_synth(NOTEON, A4, vel=100)` 渲染 0.5 秒，断言
   输出**非静音**（peak > 1e-4）且逐样本有限
7. 再送 `NOTEOFF` 渲染一段并断言有限；`deactivate`/`cleanup`/`dlclose`

「非静音」不是弱信号：它证明事件处理、声部分配、振荡器/包络/效果整条
DSP 链路真的产出了信号；插件若能加载但 DSP 坏了，输出会恒为 0 而失败。

### 控制端口初值必须取自端口声明的取值范围（本次的关键修正）

初值原本用的是统一的哨兵 `-12345.0f`（好处：`select_program()` 写回默认值时
一眼能看出来）。**这在真机上直接段错误**：

* `select_program()` 只写 patch 参数，**不写第 197 号端口 `Tuning`**
  （`gui_callbacks.c:1564` 注释即"handle tuning specially, since it's not
  stored in patch"）→ 哨兵值一路留到 DSP
* `Tuning` 的声明范围是 **415.3..466.2 Hz**，whysynth 直接把它当频率用：

  ```
  whysynth_voice_render.c:2612  voice->current_pitch *= synth->pitch_bend * *(synth->tuning);
  whysynth_voice_render.c:2641  oscillator(..., deltat * osc1_omega);   /* w0 = tuning / 44100 */
  ```

* 实测（instrumented 构建打印）：`w0=-0.279932` = **-12345/44100**；
  相位累加器 `pos` 向负方向一路跑（`if (pos >= 1.0f) pos -= 1.0f;` 对负数
  永不触发），32 个块后 `pos ≈ -537`；
  `padsynth.c:612` 的 `sine_wave[i + 4]`（`i = lrintf(pos*1024) ≈ -5.5e5`）
  越界读取 → **Signal 11**。

上游在这条路径上不做钳位，宿主本来也不该给越界值，所以这是**测试激励非法**，
不是移植缺陷（照 LADSPA 约定，宿主可以给端口设任何**合法**值）。修正：控制口
初值改为按各端口声明的**下界**取（未声明下界的取 0.0）——正对应"宿主把控制
数组清零、再按各端口的声明范围夹到合法值"的真实情形，全部合法，且与 friendly
patch 的默认值普遍不同，仍然能检出 `select_program()` 有没有写回默认参数。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `PKG_CHECK_MODULES(PLUGIN, fftw3f)` 找不到 | 本仓 fftw 只建 double，无 fftw3f.pc | 依赖独立的 `fftw3f/3.3.10` |
| 2 | 归档无 `configure` | tag 归档只带 configure.ac | build() 里 `autoreconf -fi` 引导 |
| 3 | `uname -s` = HarmonyOS，config.guess 认不出 | E007 | 引导后用 autoconf/2.72 制品中打过 OHOS 补丁的 config.guess/sub，并断言三元组 |
| 4 | autoreconf 整体跳过 aclocal/automake | 仓里提交的陈旧 `aclocal.m4` 无 aclocal 标记 | 先删除它 |
| 5 | autoconf 报 `possibly undefined macro: AM_PATH_GTK_2_0` | 构建机无 gtk-2.0.m4，而 GUI 是上游可选项 | 补丁 0001 用 `m4_ifdef` 守卫该调用 |
| 6 | configure 报 `cannot run C compiled programs` | AutotoolsDeps 把依赖塞进 LIBS，conftest 加载不到依赖 .so | 给依赖 lib 目录写 DT_RPATH（`--disable-new-dtags`） |
| 7 | `package()` 抛 `TypeError: copy() got an unexpected keyword argument 'delete'` | Conan 2.x 的 `copy()` 没有 `delete=`；ADR §4 模板那句是 Conan 1 写法 | 改用 `rm()`；**并注意 `rm()` 默认非递归**——插件 `.la` 在 `lib/dssi/` 子目录，必须 `recursive=True`，否则 .la 会带着构建机绝对路径留在包里 |
| 8 | 消费者测试 `run_synth(NOTEON)` 段错误（Signal 11） | 见上「控制端口初值」：越界哨兵经非 patch 端口 `Tuning` 进入 DSP 频率计算 | 按端口声明的下界取合法初值 |

第 7、8 两条是本次（attempt 2）修掉的；第 7 条在中断前上一次运行里是 G2 FAIL
的直接原因（`package() line 174`），第 8 条在修掉第 7 条后暴露出来。

## 源码修改

`patches/0001-configure.ac.patch` —— 唯一的补丁，把可选的 GTK+2 检查包进
`m4_ifdef`（理由见上）。**没有**针对平台去改 DSP 源码：FFTW 精度靠选对依赖包
解决，平台识别靠替换 config.* 解决，GTK+2 可选项由上游自己的 `AC_MSG_WARN`
路径 + 这一个 m4 守卫解决。

## 门禁实测

### conan-verify（真机，OHOS/aarch64 原生）

作业 `whysynth-verify-20261016-4`，日志
`/storage/Users/currentUser/.local/share/ohpc-porting/runs/whysynth-verify-20261016-4/output.log`：

```
G0: PASS   （知识图谱预查询）
G1: PASS   （配方完整性：name/version/source/build/package/package_info/
             export_sources/补丁调用/conandata.yml/test_package/MANIFEST.yml）
G2: PASS   （干净 conan create + test_package）
G3: PASS   （系统同名库隔离，R26）
G4: PASS   （产物完整性）
✅ 配方验证通过: whysynth 20170701
```

`test_package` 逐项计数（取自 G2 的 `reports/conan-create.log`）：

```
select_program(0,0) wrote 130 of 196 control ports
note-on  block peak = 0.028450
note-off block peak = 0.028454
RESULT PASS  (26 checks, 0 failures)
```

即 **TOTAL=26，PASS=26，FAIL=0，SKIP=0，NOT_RUN=0**。

### 上游测试

**TOTAL=0**（上游无测试套件，清点证据见上「上游测试清点（R51）」）；
NOT_RUN=0。**没有**把消费者测试的用例数混进上游计数。

### CI 同构（`ci/conan/build_and_test.sh`，真机）

作业 `whysynth-ci-20261016-3`，日志
`/storage/Users/currentUser/.local/share/ohpc-porting/runs/whysynth-ci-20261016-3/output.log`，
退出码 **0**（2026-10-16T07:33:47Z → 07:36:24Z）。命令：

```sh
CI_PACKAGES="archives/w/whysynth/20170701" \
CI_REPO_ROOT=<worktree> CONAN_PROFILE=<根仓库 ci/conan/profiles/ohos-aarch64> \
JUNK_PR_DIFF=<本 PR 的 diff> \
zsh ci/conan/build_and_test.sh
```

```
G0_RESULT=pass   G0e 根目录白名单 pass
KC_RESULT=pass   （知识库草稿/占位符/字段检查）
JC 检查模式: prdiff (8 个文件)，涉及软件数: 1（合规）→ JC_RESULT=pass
L0_RESULT=pass   L0i 8 个依赖全部在 registry；L0j version not in registry yet
                 (first publish)；L0k library package, commands.json not required；
                 L0m directory structure valid
L1_RESULT=pass   L1a test_package was executed；L1b 有编译/运行痕迹；
                 L1c 上游无 make check（本库上游本来就没有测试）；
                 L1e 破坏性反向验证通过：移走 lib/ 后重新 conan test 失败
                 （→ 测试确实依赖被测包，R34）
L2_RESULT=skip   no bin/（插件包，预期）
L4_RESULT=pass   patches clean
L5_RESULT=pass   lib/ has content
Total: 1  Success: 1  Failed: 0
```

L0j 的 "version not in registry yet" 说明这是该版本的**首次发布**（不是重复库）。

**注意**：CI 会把 `conandata.yml` 的 `sources.url` 改写成 gh-proxy 镜像列表
（并留下 `conandata.yml.orig` / `conandata.yml.ghfast-bak` 两个被 gitignore 的
备份）。跑完必须 `git checkout -- archives/w/whysynth/20170701/conandata.yml`
还原，否则会把镜像 URL 提交进去（PF7/R39）。本次已还原并核对。

## 注意事项

* 插件 `.so` 必须签名（`.codesign`），否则鸿蒙上 `dlopen` 直接 Permission
  denied；`package()` 里签的是 `lib/dssi/*.so` 真实 ELF。
* `test_package` 运行时要显式给 `LD_LIBRARY_PATH`（插件运行期要加载
  `libfftw3f.so.3`、`libasound.so.2`），链接期 rpath 对被 dlopen 的模块不生效。
* 本库是**插件**：`package_info()` 里 `cpp_info.libs = []`、`includedirs = []`，
  只通过 `runenv_info` 往 `DSSI_PATH` 里加 `lib/dssi`，与 `dssi/1.1.1`
  的插件搜索约定一致。
