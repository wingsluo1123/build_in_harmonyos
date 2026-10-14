- **三方库名称**：osdclock
- **上游版本**：0.5
- **上游仓库地址**：http://leftorium.net/software.phtml （作者 Jon Beckham 的项目主页，2026-10-13 实测站点已停 / 403；源码为 Debian pool 上的 2001 年原版发布副本 https://deb.debian.org/debian/pool/main/o/osdclock/osdclock_0.5.orig.tar.gz ，sha256 752d08f6bb258e271ef8d015fcdc84f9957ecd5152b057a66eeb085db6bba2c8）
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新 / 知识库扩展）
- **使用知识库**：技能 `openharmony-compile-agent` v12.22 + `adapt-lib-flow` v1.2.0；同上游家族归档 `archives/l/libxosd/2.2.14`（Debian pool 源先例、Conan 2 `cpp_info.requires` 传递写法）；本次新增知识草稿 **E429**（aarch64 `char` 无符号 + getopt_long 返回值 → 选项循环死锁）、**E479**（HMDFS 依赖 `.so` symlink 条目不可读 → lld `unable to find library -lX11` / loader `Error loading shared library`，实体化 `deplibs`/`realdep_libs` 修复）、**E549**（libxosd 2.2.14 `xosd_init()` 7 参 API 漂移 + `xosd_display` 行号上界）、**E550**（zsh heredoc 临时文件走 `TMPPREFIX` 而非 `TMPDIR`，OHOS `/tmp` 只读导致 L0 门禁 heredoc 失败）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：无——`Makefile` 仅有 all/osd_clock/%.o/%.o.pic/tar/install/clean 七条规则，无 `check`/`TESTS`/`check_PROGRAMS` |
| 集成测试 | 0 | 来源：无——发布包无 `tests/` 目录、无 `*_test.c`/`test_*.c` |
| 其他测试 | 0 | `osd_clock.c` 行首锚定 `grep -cE '^[[:space:]]*assert\('` = 0 |
| **合计** | **0** | 上游 0.5（2001）未提供任何自动化测试套件（逐项证据见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变（0） | 上游无单测框架 |
| 集成测试 | 4 | +4 | `test_package/test_osdclock.sh` 真实执行安装后的 `bin/osd_clock` 的 4 条命令行路径：`-h`、`--help`（usage 路径）、`-c red`、`-f fixed -o 5 -t -d 2`（无 X display 时 `xosd_init()` 失败路径） |
| 鸿蒙特有测试 | 1 | 新增 | `readelf -d` 断言 `NEEDED` 含 `libxosd.so.2`（证明链接的是被测包本体）+ HMDFS 依赖 `.so` 实体化后的运行期寻库验证 |
| **合计** | **5** | **+5** | 5 条用例 / **9 条断言**（4 条 CLI 用例各 2 条：退出码 + 输出串；1 条 DT_NEEDED），全部无需 X server、对真机显示状态零副作用；其中用例 3 同时是 aarch64 getopt 死循环的回归探针（`timeout 60` 兜底，不修补丁 0002 则挂死判 FAIL） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 0.5 根本不存在测试用例文件，本次适配未新增/修改任何上游测试文件；两个补丁只改 `osd_clock.c` 的返回类型与 libxosd API 调用。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为 CLI 的全部可无头执行路径新增 5 条集成用例 / 9 条断言：usage（`-h`、`--help`）、无 display 初始化失败（`-c red`、`-f fixed -o 5 -t -d 2`）、ELF `DT_NEEDED` 链接校验（`libxosd.so.2`）。
> - **补全原因**：上游 osdclock 0.5（2001）为单文件手写 Makefile 工程，无测试框架、无测试目录、无断言（R51 第一步清点证据见 `test_package/MANIFEST.yml`）；`osd_clock` 需要可达 X server 才能显示，故断言设计成全部早于/不依赖真实显示（无 DISPLAY 时走 libxosd `XOpenDisplay()` 失败分支），任何分支都不会在真机上留下 OSD 窗口。
> - **新增测试文件清单**：
>   1. `archives/o/osdclock/0.5/test_package/test_osdclock.sh` — 5 条用例 / 9 条断言的 POSIX sh 测试脚本（含 aarch64 getopt 死锁回归探针）
>   2. `archives/o/osdclock/0.5/test_package/conanfile.py` — 驱动脚本执行被测二进制，并把依赖 `.so` 实体化到 `realdep_libs` 前置 `LD_LIBRARY_PATH`（HMDFS 修复）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（0%）
- 新增测试用例通过率：5/5（100%）
- 新增断言通过率：9/9（100%）

## 补充说明

1. **源码 URL（PF7 已披露）**：上游作者站 `leftorium.net`（403）、旧 Savannah 下载目录（404）、SourceForge（无此项目）、GitHub `fhackenberger/osd_clock`（仅 0.6 tag）在 2026-10-13 逐一实测不可用；现取 Debian pool 的 `osdclock_0.5.orig.tar.gz`，逐文件核对为 2001 年原版发布内容（仅顶层目录改名为 `osd_clock-0.5.orig`，无 `debian/` 目录、无源码改动）。该 URL 命中 PF7 的 Debian 域名黑名单，属「官方源已消失」的既定例外；同上游家族的 `archives/l/libxosd/2.2.14/conandata.yml` 已是同一写法且已合入 main。建 PR 时按先例使用 `--no-preflight`，其余 PF1–PF6、PF8 逐项实测通过（本地 `preflight.py origin/main HEAD` 取证：仅 PF7 与 PF9 命中，见第 2 条）。
2. **PF7 命中范围与 PF9 软件级文件（已披露）**：本包为首次入库，按 ARCHIVE-SPEC 与仓内 5183 个先例新增软件级 `README.md`/`manifest.yaml`/`commands.json`（CLI 包 R38 必需），本包 PF7 共命中 3 处（`0.5/conandata.yml` 的 `sources.url` 与两级 `manifest.yaml` 的同一 Debian 源 URL，均为同一条「官方源已消失」例外）；软件级 `README.md`/`manifest.yaml`/`commands.json` 不在 `archives/o/osdclock/0.5/` 内，命中 PF9 的「单一包/版本目录」判据；与 checklist #15 记载的既定冲突一致，故与 PF7 一并 `--no-preflight` 并在此披露。
3. **`packaging/` 缺失为框架遗留误报**：`finish` step 6 与 `submit` 自检要求 `packaging/*.tar.gz`，但 R19 禁止手工 tar 打包、JC3 又拦压缩包入库；本包 status=`built`（conan-verify 通过、未 upload），未伪造打包产物。
4. **W3 本地 CI 结果**：`ci/conan/build_and_test.sh` PASS（1/1、L0 全过、L1 test_package executed、L4 patches clean、L5 bin/ 有内容）；`L2_RESULT=skip` 为该通用探针直接执行 `bin/osd_clock --version/--help` 且不注入依赖 `libdir` 到 `LD_LIBRARY_PATH`（动态链接 libxosd 的 CLI 在探针环境必然加载失败，框架标注 non-blocking）；同一次运行的 L1 已真实执行该二进制并 9/9 全绿。
5. **`finish` step 3（G0 clean-verify）非阻塞告警**：该步骤按 autotools 约定执行 `configure`，而本包上游是手写 Makefile（无 `configure`）→ `configure 失败 (exit 127)`；框架标注非阻塞，构建正确性以 step 4 `conan-verify`（G2 真 `conan create`）与 step 5 W3 为准。
6. **对上游源码的两处修改**（`patches/`，均为 `patch_type: portability`，不含任何平台宏）：① `osd_clock.c` 的 `char c` → `int c`（aarch64 `char` 无符号使 getopt 循环恒真、程序在初始化前挂死；clang 判据 `-Wtautological-constant-out-of-range-compare`，改前 rc=124 挂死 / 改后 rc=1）；② `xosd_init(..., shadow)` → `xosd_init(..., shadow, 2)` 且 `xosd_uninit` → `xosd_destroy`（libxosd 2.2.14 唯一可用 API；`number_lines=2` 是为保留原有 line 1 绘制）。
7. **知识沉淀（路径 B）**：已按 `ohc-run.py graph add --draft` 生成草稿 E429/E479/E549/E550（含 `error_signature`/`root_cause`/`rec_approach` 三字段，W5 校验通过），供主编审核后提升为正式条目。
