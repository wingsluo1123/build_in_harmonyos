# xine（上游 xine-ui）— xine 媒体播放器的 X11 前端

> 包名 `xine`（Conan 制品 `xine/0.99.14`）对应上游项目 **xine-ui**；引擎依赖为同族包
> [`xine-lib`](../xine-lib/)。下文 `xine-ui` 一律指上游项目名。

## 软件简介

xine-ui 是 xine 媒体引擎的官方 X11 前端（Gtk+ 时代的 xitk 自绘工具包），负责播放器窗口、
皮肤、快捷键、DVD/菜单交互与桌面集成（desktop entry、mime 关联、图标、man 页面）。
它本身不含解码能力，播放全部通过 `libxine` 调用 xine-lib 引擎。

**交付的三个命令**:
- `xine` — 主播放器：`xine [选项] [MRL]`，支持本地文件、`http://`、`dvd://`、`vcd://` 等 MRL
- `xine-check` — 系统诊断脚本：检查内核/设备/编解码器/X 环境并给出问题清单
- `xine-bugreport` — 交互式缺陷报告生成器（`xine-check` 的副本 + 16 项菜单）

**主要功能**（选项名以打包后 `xine --help` 实测输出为准）:
- `-p/--auto-play`、`--enqueue <mrl>`、`-l/--loop`、`-P/--playlist`：播放、队列与循环控制
- `--keymap [=option]`：`default`/`remapped`/`lirc`/`man`/`file:<filename>` 导出或比对快捷键表（无需 X display 即可运行）
- `-n/--network` + `--network-port`：启用远程控制服务器，配合 `-S session=n`、`--enqueue` 驱动运行中的实例
- `--visual <class-or-id>`、`--install`：X11 视觉与私有 colormap
- `-f/--fullscreen`、`-F/--xineramafull`、`-G/--geometry`、`-B/--borderless`、`-R/--root`、`-W/--wid`：输出窗口形态
- 皮肤（`share/xine/skins`）、图标（`share/pixmaps`）、desktop/mime 与 man 页面数据安装

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.99.14 | published ✅ | 2026-10-17 | 5 |

## 使用方法

```bash
# 播放本地文件（需要可用的 X display）
xine movie.mp4

# 只查询用法与版本（无显示环境也可运行）
xine --version
xine --help

# 导出的快捷键表落地为用户配置后再次导出（字节级闭环）
xine --keymap=default  >  ~/.xine/keymap
xine --keymap=remapped

# 系统诊断（鸿蒙上能识别 HarmonyOS，无 DISPLAY 时跳过 X 项继续）
xine-check

# 生成缺陷报告（交互式，逐项选择 1..16）
xine-bugreport
```

> 运行时依赖：`xine` 链接 `libxine.so.2` 等 Conan 依赖库，需用 Conan 生成的 run-environment
> （`conanrunenv-release-armv8.sh`，即 `LD_LIBRARY_PATH` 指向各依赖 libdir）启动。

## 平台适配说明

### 鸿蒙系统适配

**编译补丁**（全部由 `ohc refresh-patch --auto` 从 `.orig`/`.work` 差分生成，无 `__OHOS__` 平台宏）:
1. `0001-config.guess.patch`: 识别 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`
   - 原因: 随源码分发的 config.guess(2022-01-09) 不识别 `uname -s=HarmonyOS`；OHOS 上 build==host，
     Autotools 不会自动下发 `--build/--host` 三元组，必须让探测自己得出结论（知识图谱 E566 的鸿蒙分支）
2. `0002-config.sub.patch`: 接受 `ohos*` / `linux-ohos*` 内核字段
   - 原因: 未打补丁的 config.sub 对 `aarch64-unknown-linux-ohos` 返回 rc=1，是补丁 1 的前置条件
     （这里与 E566 的"只需显式三元组"建议有实测偏离，理由与证据见 `0.99.14/notes.md` 问题 1b）
3. `0003-configure.patch`: 两个 hunk。①`XINE_MIME` 改为先取 `plugindir` 并在空值时回落；②`config.status`
   安全临时目录的 `umask 077` → `umask 022`
   - ①原因: Conan 合成的 `libxine.pc` 不带 `plugindir` 字段，`pkg-config --variable=plugindir libxine`
     **返回空且 rc=0**，`|| xine-config` 短路不会触发，结果拼出 `/mime.types`；空值时改用树内 `mime.default`
   - ②原因: 远端 CI 在 `conan create` 的 `autotools.configure()` 失败——HMDFS 上 `(umask 077 && mktemp -d
     "./confXXXXXX")` 建出 `drwx--S---`，`config.status` 写 `subs1.awk` 即 EACCES（知识图谱 E129，同族 E114；
     本机 conan home 在应用私有挂载因而复现不出，见 `0.99.14/notes.md` 问题 15）
   - 只补生成物 `configure`（构建实际执行的文件）；等价源行 `configure.ac:102` 逐字相同，若在具备
     完整 autotools 的环境重跑 autoreconf 需一并回写，理由与代价见 `0.99.14/notes.md` 注意事项 14。
     `config.status` 不单独打补丁（tarball 内不存在，是 `configure` 生成的），实测生成物内已无 `umask 077`
4. `0004-misc-desktops-Makefile.am.patch`: `xine.desktop` 规则里 `"$(srcdir)/mime.default"` 去掉字面双引号
   （模板侧）
5. `0005-misc-desktops-Makefile.in.patch`: 与 `0004` 同一处的生成物修改（`.am`/`.in` 必须成对——OHOS 不重跑
   autoreconf，构建读的是生成的 `.in`，只改 `.am` 不生效）

**固定门控**（不是环境妥协，是可复现性要求）:
- `--without-fb`: OHOS libc 无 `pthread_cancel`/`pthread_testcancel`（E085），且鸿蒙 PC 无 framebuffer 控制台
- `--disable-nls`: `AM_GNU_GETTEXT` 以"是否预装 GNU gettext"决定 `USE_NLS`，不显式关闭会让
  CI worker 与本机结果不一致

**其他要点**:
- `readline`/`xine-remote` 自动关闭：`m4/readline.m4` 只遍历硬编码前缀、且探测 `-lncurses`，
  而 OHOS ncurses 仅发布 `libncursesw.a`
- `session_ctrl`（上游 `EXTRA_PROGRAMS` 测试入口）在配方中**只编译不执行**：其
  `connect_to_session()` 无条件调用 `setreuid()`，OHOS 系统调用策略以 SIGSYS 终止进程（E051，不可捕获）
- `configure`/`make` 会运行刚链接的 conftest，必须把依赖 libdir 前插 `LD_LIBRARY_PATH`；
  `PKG_CONFIG_LIBDIR` 钉到 `generators_folder` 防系统 `.pc` 抢依赖
- autotools helper 需按需补执行位（E490）；构建一律 `-j1`（避免顺序依赖竞态）

**编译依赖**（11 个直接依赖，W0 逐个实测 `conan download --only-recipe` 已发布）:
- xine-lib/1.2.13（媒体引擎）
- libx11/6.4.0、libxext/6.4.0、libxv/1.0.13、libxinerama/1.1.5、libxxf86vm/1.1.5、libxtst/1.2.5、libxscrnsaver/1.2.5
- libpng/1.6.58、libjpeg-turbo/3.2.0.1、curl/8.15.0.1
- 传递依赖 9 个由 Conan 图解析（libxau/libxcb/libxdmcp/libxfixes/libxi/xorgproto/xtrans/openssl/zlib）

**构建系统**: autotools

## 验证结果

### 上游测试覆盖口径

| 口径 | 数量 |
|------|------|
| 上游自动化测试套件 | 0（`make check`：20 个唯一 check 目录 / 27 次进入事件 / 19 行 "Nothing to be done"，0 用例执行；全文见 `0.99.14/reports/upstream-test-census.txt` §B） |
| 上游程序级测试入口（清点） | 10 = 实测 4 + 不适用 6 |
| 实测入口 | 4（`xine` / `xine-check` / `xine-bugreport` / `session_ctrl`） |
| 实测调用次数 | 9 |
| 判定不适用的入口 | 6（`test` / `xine-remote` / `fbxine` / `aaxine` / `cacaxine` / `dfbxine`，各有实测证据） |
| test_package 断言 | 27（PASSED 27 / FAILED 0） |
| 其中鸿蒙特有端到端消费者用例 | 3 |

### 功能测试

| 测试项 | 结果 |
|--------|------|
| `xine` 5 次调用（`--version`/`--help`/`--keymap` 三种模式） | ✅ 通过 |
| `xine-check` 无显示诊断（rc=0，44 行，识别 HarmonyOS） | ✅ 通过 |
| `xine-bugreport` 交互式实测（2468 行后阻塞于菜单） | ✅ 已实测，判定不入自动化 |
| `session_ctrl` OHOS 交叉编译（27008 B ELF arm64） | ✅ 通过（仅编译） |
| keymap 导出→安装为 `~/.xine/keymap`→再导出字节级闭环 | ✅ 通过 |
| `bash test_package/test.sh` | ✅ 27/27 |

### 质量门禁

| 门禁项 | 结果 |
|--------|------|
| G0 预构建风险评估 | ✅ 通过（命中 E566，偏离理由见 notes.md 问题 1b） |
| G1 配方完整性 | ✅ 通过 |
| G2 conan create（干净构建） | ✅ 通过（umask 修复后本机再复验一次 `conan-verify` rc=0，同 profile `ohos-aarch64`、`test_package` 27/27；本次复验的作用是**无回归**，见下方「远端 CI」行） |
| G3 系统同名库隔离 | ✅ 通过（纯可执行包，无 `lib/`） |
| G4 产物完整性 | ⏭️ SKIP（conan-verify 阶段无 cache 路径，报告标题渲染成 PASS 而正文是 "⚠️ 无法找到程序包 ID"；产物完整性实际由 W3 的 L5 承担） |
| W3 本地 CI 模拟 | ✅ 通过（`L0/L1/L5 pass`；`L2 pass` 内含 1 条 warn：不带运行路径直接跑 `xine --version` 失败，等价验证在 test_package A 组；`L4 warn`：补丁安全扫描正则缺左词边界的误报，命中 config.guess 里的普通单词，补丁未新增危险函数调用）。`L0n`（分支名匹配）以 `CI_BRANCH` 为前提、本地不触发，已按 `ci/conan/build_and_test.sh:856-903` 原逻辑用 `pkg_name=xine` 与 `CI_BRANCH=feat/xine-0.99.14` 复算通过（旧分支名 `feat/xine-ui-0.99.14` 复算结果为 `branch_name_r40` 硬失败），远端 CI 为最终实测 |
| 远端 CI（PR #16499） | ❌ 前两轮 build `#97241`（SHA `10831c00`，CI-030）与 `#97272`（SHA `06016b90`，CI-001）**红**（同一崩溃行同一签名）→ ✅ 修复后 build **`#97351`**（SHA `57eae489`，worker `OpenHarmonyPCDeveloper-CI-040`）**校验通过**（`test_package` 通过、L0/L1 门禁通过、7 个步骤全绿，日志 https://ohpcd.atomgit.com/ci?id=97351）。红的那轮其余门禁全绿（含 `L0n` 分支名精确匹配、KC/JC 零错），只在 `conan create` 的 `autotools.configure()` 里死于 `./config.status: line 655: ./confhGIGfN/subs1.awk: Permission denied`（知识图谱 E129：HMDFS 上 `umask 077` 建出的 `mktemp -d` 目录在 worker 上不可写）；已按 E129 rec 1 在 `0003-configure.patch` 加第二个 hunk（`umask 077` → `umask 022`，与同族依赖 `xine-lib/1.2.13` 对同一 autoconf 站点的补丁同形）后转绿。**本机全绿从来不是该修复有效的证据**（本机 conan home 在应用私有挂载，同一命令得到 `drwx------`；而本机在自己 HMDFS 挂载上能复现出 `drwx--S---` 这个 mode 却复现不出拒写），两轮之间只多这一个 hunk，故远端的红/绿对比即有效性回执；传导证据取自生成物 `config.status`（`umask 077` 归零、`:626/:631` 均为 `umask 022`）。落实第四轮审计意见后又重跑两次 → build **`#97427`**（`c0e15e69`，CI-021）与 **`#97445`**（`63d216c8`，CI-026）均校验通过，用于保证每笔提交都有对应的绿构建。五次构建落在五台不同 worker（CI-030/001/040/021/026），「红由单机抖动造成」的替代解释随之排除；修复轮按错误签名计为 1 轮（预算 2 轮）。详见 `0.99.14/notes.md` 问题 15 与「验证结果」新增表 |
| W4 提交前独立审计 | ✅ 四轮独立审计（上下文隔离子任务）均 `verdict=pass`、P0=P1=0；随 PR 提交的报告 `0.99.14/reports/audit-result.json` 是**第 1 轮 CI 修复之后**那一轮（第四轮，34 文件快照，实测覆盖 0003 的第二个 hunk、回填后的 `patch_classification`、新增的第 6 条知识草稿），其前一轮为改名后 32 文件快照；第四轮的 5 项 P2 / 6 项 P3 全部为文档口径项，处置见 notes.md 注意事项 19，第三轮项见注意事项 14–17 |

### 未验证面（R40，需人工在有 X display 的环境确认）

核心播放链——X11/Xv 视频输出、`xitk` GUI、皮肤渲染、DVD/流媒体播放——在无显示环境的构建/CI 机器上不可验证。
27 条断言覆盖的是**显示无关的消费者面**（keymap 发射与再序列化闭环、lirc 跨格式一致性、`xine-check` 诊断、
desktop/mime/man/皮肤数据完整性）。鸿蒙侧的实质适配证据在补丁与配方侧：三元组识别、`XINE_MIME` 三级回落、
`pthread_cancel` 门控、依赖运行路径修复，均非空壳实现。

## 源码信息

- **源码地址**: https://downloads.sourceforge.net/project/xine/xine-ui/0.99.14/xine-ui-0.99.14.tar.xz
- **官方主页**: https://sourceforge.net/projects/xine/
- **许可证**: GPL-2.0-or-later
- **上游版本注意**: 0.99.14 是 SourceForge 上 xine 项目发布的 xine-ui 版本，源码 tarball 内不含
  可用的自动化测试套件——测试口径按"程序级入口清点"给出，逐项证据见 `0.99.14/reports/test-report.md`

## 相关资源

- [编译详情](./0.99.14/notes.md)
- [测试报告](./0.99.14/reports/test-report.md)
- [验证报告](./0.99.14/reports/conan-verify-report.md)
- [Conan 配方](./0.99.14/conanfile.py)
- [xine-lib（引擎依赖，本仓库同族包）](../xine-lib/)
