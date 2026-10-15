# plib 1.8.5 适配笔记

## 编译环境
- 构建系统: autotools (tarball 自带 configure/Makefile.in)
- 编译日期: 2026-10-12
- 编译器: clang/clang++ (OHOS aarch64, profile ci/conan/profiles/ohos-aarch64)
- 状态: built

## 上游信息
- 官方主页: http://plib.sourceforge.net
- 源码包: 上游官方 dist 目录
  https://plib.sourceforge.net/dist/plib-1.8.5.tar.gz
  sha256 485b22bf6fdc0da067e34ead5e26f002b76326f6371e2ae006415dea6a380a32
- 许可证: LGPL-2.0-or-later (COPYING)
- 内容: 便携游戏编程库，按模块拆分为多个静态库：
  ul(工具) pw(可移植) sg(3D 数学) psl(着色语言前端) net(缓冲 TCP) js(摇杆)
  + OpenGL 模块 fnt/pui/libplibpu/puAux/libplibpuaux/ssg/ssgAux + 音频 sl/sm

## 依赖分析
| 类型 | 名称 | 说明 |
|------|------|------|
| 系统 | pthread/dl | configure AC_CHECK_LIB 探测，OHOS libc 内置 |
| 禁用 | OpenGL/GLUT | fnt/pui/puAux/ssg/ssgAux 模块，OHOS 无 GL 工具链 |
| 禁用 | 音频(ALSA/OSS) | sl/sm 模块 |

- configure 参数: `--disable-fnt --disable-pui --disable-puaux --disable-ssg --disable-ssgaux --disable-sl --disable-pw`
- configure 会把 includedir 自动追加 `/plib`，故头文件装到 `include/plib/`

## 上游测试审计 (R51)
- plib-1.8.5 tar（Debian pristine orig，sha256 485b22bf…a32）清点：无 tests/ 目录、任何 Makefile.am 无 TESTS/check_PROGRAMS、顶层 Makefile.am 无 check 目标。
- 结论：上游无测试套件，无可运行的上游检查命令；功能覆盖由 test_package 消费者用例承担（详见 test_package/MANIFEST.yml）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type; you must specify one`（job plib-1.8.5-verify-20261012-1） | plib 1.8.5 自带 `config.guess`(2006-05-13)/`config.sub` 太旧：**不认识 aarch64（config.sub aarch64 命中 0），也没有 HarmonyOS/ohos**，config.guess 判断不出 build triplet | 随配方 `export_sources` 导出并 `build()` 覆盖源码根：现代 GNU `config.guess`(2023-08-22)/`config.sub`(2023-09-19)（含 aarch64 + HarmonyOS + linux-ohos，取自 afflib 3.7.22 先例）。遵循 iron-rule #0，不用 `--build/--host` 绕过。**注：此"随仓库携带整文件"方案已于 2026-10-14 被"构建期从 automake 取得"方案取代（原因见文末「PR 体积收缩」节），保留本条仅作历史** |
| 2 | configure 通过后 `make` 报 `No targets specified and no makefile found`（job -2）：模块选择正确但 build-release 目录无 Makefile | plib 只支持 **in-source** 构建；配方只设了 `src_folder="."`，未设 `folders.build="."`，Autotools.make 在独立的 build-release 目录执行 | layout() 增 `self.folders.build = "."`（in-source，gnubatch/ripmime 同款先例） |
| 3 | （#2 后）`make` 仍 `No makefile found`；手工跑 `config.status` 报 `./confXXXXXX/out: Permission denied`，未生成任何 Makefile（job -3，E118） | **HMDFS 对 `umask 077 && mktemp -d` 产生的目录强制 setgid（drwx--S---），属主也写不进**；`configure:9272/9277` 的 `umask 077 &&` 包装触发 | `_patch_configure_umask()` 在 configure 前把 `"umask 077 && "` 直接替换为空（旧/新 autoconf 均适用；gnubatch 同款） |
| 4 | pw 模块编译报 `pwX11.cxx:17: fatal error: 'X11/Xlib.h' file not found`（job -4） | plib 的 pw（可移植性）模块在 *nix 上的唯一后端是 X11（pwX11.cxx），OHOS 无 X11 头/库 | 追加 `--disable-pw`（同 GL/audio 的处理），package_info 移除 plibpw；保留核心 ul/sg/psl/net/js |
| 5 | 建 PR 前置 preflight（正确 base `gitcode/main`）报 **PF7 源URL闸(R39)**：conandata.yml:6 与 manifest.yaml:8 为「Debian 下游重打包源」（2026-10-13） | 早期只发现 SourceForge 的 **files 下载页** 404，误判 1.8.5 无上游官方源，改用 Debian pool 的 pristine orig tar；实际上游项目自身的 dist 目录一直可用 | 设备实测 `https://plib.sourceforge.net/dist/plib-1.8.5.tar.gz` HTTP 200（779133B，Content-Type application/octet-stream，gzip），**sha256 与 Debian pristine orig 逐字节相同**（485b22bf…a32），故两处 URL 改回上游官方源，sha256 不变；源码字节未变，既有 conan-verify 证据仍覆盖同一源码（构建侧零影响）。R39：conandata/manifest 只写上游官方 URL，镜像回退由 CI 处理 |

## test_package (鸿蒙消费者功能用例)
| # | 用例 | 验证点 |
|---|------|--------|
| 1 | sg 向量运算 | sgSetVec3/sgAddVec3/sgLengthVec3 真实调用与数值断言 |

## 验证结果
- 真机 conan-verify（job plib-1.8.5-verify-20261012-5）：PASS。conan create 源码构建成功（libplibul/sg/psl/net/js.a + licenses/COPYING），test_package 编译并运行，sg 4 项断言全 ok（PLIB_SG_TESTS failures=0）。
- CI 同构 build_and_test.sh（job plib-1.8.5-ci-gate-20261012-2）：100%。JC pass（incremental 10 文件）、L0/L1/L4/L5 pass、L2 skip（库无 bin/），test_package 执行。
- W4 独立审查：P0=0/P1=0 通过。
- 构建提交：feat/plib-1.8.5。

## PR 体积收缩：config.guess/config.sub 改构建期取得（2026-10-14）

**为何改**：PR #15535 的 AI 检视被平台跳过，原文「本次变更过大（5 个可审文件、3861 行，预估需 4 轮分片审查），已超出 AI 代码评审的处理范围，本次跳过」。人工审查 rule6 依赖 AI 检视结论，体积不降则无法提审。
逐文件统计（`GET /pulls/15535/files`）：`build-aux/config.guess` +1823 行、`build-aux/config.sub` +1966 行，两个 GNU 官方脚本合计 **3789 行（占 4131 行的 92%）**，真正配方工作仅约 342 行。因此不是"拆 PR"（一库一 PR + L0/L1 需完整配方），而是把这两个脚本从"随仓库携带"改为"构建期取得"。

**改法（相对原方案零行为变化）**：
- 删除 `export_sources` 中的 `build-aux/*` 导出与随仓库携带的两个脚本（`git rm archives/p/plib/1.8.5/build-aux/{config.guess,config.sub}`）。
- `build_requirements()` 增 `tool_requires("automake/1.18")`（E007 先例，proxyknife 1.7 同款）；`build()` 新增 `_install_config_helpers()`，从 automake 工具包 `share/automake-1.18/config.{guess,sub}` 覆盖 plib 自带的 2006 年版。
- 取得来源与版本：automake/1.18 包内为 GNU `config.guess`（timestamp 2024-07-27）/`config.sub`（2024-05-27）。config.sub 该版**已原生支持** `ohos*`（OS 白名单）与 `linux-ohos*`（kernel-os 配对），无需改动；config.guess 该版**尚无 HarmonyOS** 分支，`_add_harmonyos_branch()` 在 `*:NetBSD:*:*)` 前插入 `*:HarmonyOS:*:*` 分支（与 `scripts/patch-autotools-ohos.pl` 的插入内容逐字一致），设备 `uname -s` = HarmonyOS 命中该分支，早于 config.guess 的 libc 编译探测（HMDFS 下 `dummy.c: Permission denied`）就解析出三元组。
- **铁律 #0 遵守**：全程未用 `--build/--host=`；configure 日志 `checking build system type... aarch64-unknown-linux-ohos`、`checking host system type... aarch64-unknown-linux-ohos` 由 config.guess 直接得出（日志中 `--host=`/`--build=` 出现 0 次）。
- 本改动目的：把 PR 可审行数压到 AI 可检视范围。

**改后体积对比**（`git diff --stat origin/main -- archives/p/plib/1.8.5/`）：
- 改前：10 文件、**4131** 行（含 config.guess 1823 + config.sub 1966）。
- 改后：8 文件、**424** 行（conandata 11 + conanfile 179 + manifest 34 + notes 75 + test_package 125）。

**验证**（CI 同构门禁 job `plib-1.8.5-cigate-20261014-3`，验证对象为最终 HEAD `327199c4c`，exit 0；`plib-1.8.5-cigate-20261014-2` 为改前的未提交态首次门禁，两者同构）：
- `checking build/host system type... aarch64-unknown-linux-ohos`（config.guess 生效）；日志内 `--host=`/`--build=` 计数为 0。
- 5 个静态库全部生成：libplibul/sg/psl/net/js.a（与原方案一致）。
- test_package 运行通过：sg 4 项断言全 ok，`PLIB_SG_TESTS failures=0`。
- L0 pass / L1 pass（test_package executed）/ L2 skip（库无 bin/）/ L4 pass / L5 pass；L1e 破坏性负测确认消费者真实依赖 plib；Pass rate 100%。
- 功能等价：三元组、库清单、消费者断言与改前 `plib-1.8.5-ci-gate-20261012-2` 结果一致。

