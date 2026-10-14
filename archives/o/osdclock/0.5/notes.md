# osdclock 0.5 — OpenHarmony PC (OHOS aarch64) 适配笔记

## 上游
- 项目：osdclock / `osd_clock`（X On-Screen Display clock），作者 Jon Beckham
  <leftorium@leftorium.net>，GPL-2.0-or-later，最后发布 0.5（2001-04）。
- 语言 **C**（单文件 `osd_clock.c`，~130 行；`lang-preflight` 复核：
  detected=c，源文件 1 个、主体占比 100%）。
- 构建系统 **makefile**：上游自带手写 `Makefile`（无 configure、无 CMake、
  无 Makefile.am），所以走 mode B（探索性编译）而不是 Autotools 路线。
- 源码：2026-10-13 逐一实测上游端点全部不可用——作者主页
  `http://leftorium.net/software.phtml`（403，站点已停）、旧 Savannah 下载区
  `download.savannah.nongnu.org/releases/osdclock/`（404，目录不存在）、
  `sourceforge.net/projects/osdclock/`（404，无此项目）、GitHub
  `fhackenberger/osd_clock`（仅 `0.6` tag，无 0.5）。最终取 Debian pool 的
  `osdclock_0.5.orig.tar.gz`（sha256 `752d08f6…a2c8`，9819 字节），
  逐文件核对为 2001 年原版发布内容（AUTHORS/COPYING/ChangeLog/Makefile/NEWS/
  README/osd_clock.1/osd_clock.c，仅顶层目录被 Debian 改名为
  `osd_clock-0.5.orig`，无 debian/ 目录、无源码改动）。与同一上游家族的
  `libxosd/2.2.14` 先例一致（该 conandata 亦为 deb.debian.org 直链，已在
  main 合并）。

## 真实依赖闭包（实测）
- **libxosd/2.2.14**（`#include <xosd.h>`，调用 `xosd_init` / `xosd_display` /
  `xosd_uninit`）。唯一在发行的 XOSD 实现；其 `cpp_info.requires` 已传递
  libx11/libxext/libxinerama/xorgproto，故消费者只需 `-lxosd`。
- 运行期 `DT_NEEDED` 闭包（test_package 的 conanrun 需要）：
  `libxosd.so.2 → libX11.so.6 / libXext.so.6 / libXinerama.so.1`、
  `libX11.so.6 → libxcb.so.1 + libXau.so.6`、`libxcb.so.1 → libXau/libXdmcp`
  → 配方显式声明 run 依赖 libxcb/1.16 + libxau/1.0.11 + libxdmcp/1.1.5。
- **不需要** libXt / libX11 直接链接：上游 Makefile 里的 `-lX11 -lXext -lXt
  -lpthread` 是 2001 年的复制粘贴残留，`osd_clock.c` 只用 XOSD API
  （grep 全源 0 处 Xt/Xlib 直接调用）；配方保留 `-lX11 -lXext -lXinerama`
  以贴合上游 Makefile，但不引入 libXt。
- **X11 栈统一 6.4.0 线**：与 libxosd/2.2.14 完全一致（避免 libX11/libXext
  两套 SONAME 共存；旧线 1.8.x/1.3.x 带 libxcb/1.17.0 的 R37 债务）。

## 关键适配点
1. **libxosd 2.2.14 API 漂移（必须补丁）**：osd_clock 0.5 针对 xosd 0.7.0
   编写，`xosd_init(font, color, delay, pos, offset, shadow)` 是 6 参；2.2.14
   的头文件要求 7 参（多出 `number_lines`）。不加补丁直接编译失败：
   ```
   osd_clock.c:112:59: error: too few arguments to function call, expected 7, have 6
   ```
   且**只补第 7 参不够**：程序在 `xosd_display(osd, 1, XOSD_string, out)` 的
   **line 1** 上绘制，而 2.2.14 的 `xosd_display()` 有 `0 <= line <
   number_lines` 校验（src/libxosd/xosd.c:926），故 `number_lines` 必须 ≥ 2
   ——补丁取 2（与 Debian 补丁集同值），保留原有 line 1 绘制语义；顺带把
   deprecated 的 `xosd_uninit()` 换成 `xosd_destroy()`。
2. **aarch64 `char` 无符号 → getopt 循环死锁（必须补丁）**：`char c;
   while ((c = getopt_long(...)) != -1)`——aarch64 上 `char` 默认无符号，
   `-1` 赋给 c 变 255，比较时提升为 255 ≠ -1 恒真 → 选项循环永不退出，
   程序在 `xosd_init()` 之前空转。clang 直接给出判据：
   ```
   osd_clock.c:62:27: warning: result of comparison of constant -1 with
     expression of type 'char' is always true
     [-Wtautological-constant-out-of-range-compare]
   ```
   实测证据（本机，同一份源码、仅差这一个补丁）：
   - 打补丁前 `timeout 5 ./osd_clock -c red` → **rc=124（挂死）**
   - 打补丁后 `timeout 5 ./osd_clock -c red` → 打印
     `Error initializing osd`、**rc=1**
   上游与 Debian 补丁集都只面向 x86（char 有符号），故这是 aarch64 特有的
   平台移植修复。
3. **手写 Makefile 无法接受环境变量**：`Makefile` 里 `CC=gcc`、
   `CFLAGS=...`、`LDFLAGS=...`、`XOSDLIBS=-lxosd`、`INSTALL=/usr/bin/install -c`
   都是**赋值**（会覆盖环境变量），因此配方必须把覆盖项放在 make 命令行上：
   ```
   make -j1 CC=<clang> CFLAGS="-O2 -fPIC -Wall -I. -I<deps>" \
        LDFLAGS="-L<deps>" XOSDLIBS="-lxosd -lX11 -lXext -lXinerama"
   ```
   编译器取自 `tools.build:compiler_executables`（R33，不裸用 `${CC}`）。
4. **`make install` 不可用**：上游 install 目标不建目录、且硬编码
   `INSTALL=/usr/bin/install -c`（OHOS 无此路径），故 `package()` 用 Conan
   `copy()` 显式安装 `bin/osd_clock` + `share/man/man1/osd_clock.1` +
   `licenses/COPYING`（不做手工 tar 打包，R19）。
5. **ELF 签名**：产物 `bin/osd_clock` 经
   `/data/service/hnp/bin/binary-sign-tool -selfSign 1` 自签（与
   xgamma/xeyes/xev 同款；OHOS 内核拒绝未签名 ELF）。
6. **构建目录内源**：Makefile 无 VPATH/out-of-tree 支持，`build()` 以
   `cwd=self.source_folder` 直接 make；`basic_layout` 的 build_folder 仅用于
   Conan 记账。
7. **tool_requires 不需要**：无 autoreconf/automake/libtool 依赖
   （上游发布包已含全部构建输入），故配方无 build_requirements。

## 测试
- **上游无测试套件**（R51 第一步清点，证据见 test_package/MANIFEST.yml）：
  `Makefile` 只有 all/osd_clock/%.o/%.o.pic/tar/install/clean 七条规则，无
  check/test/TESTS/check_PROGRAMS；无 tests/ 目录；`osd_clock.c` 行首锚定
  `assert(` 计数 = 0；发布包 8 个文件里无测试夹具。故 `ci/config/no_official_test.txt`
  之外无任何上游用例可执行，R51 第二步以 test_package 真实执行被测二进制补足。
- **test_package：5 条用例 / 9 条断言**（`test_package/test_osdclock.sh`，
  无需 X server、对真机显示零副作用）：
  | # | 用例 | 期望 | 依据 |
  |---|------|------|------|
  | 1 | `-h` | rc 0 + `USAGE:` | osd_clock.c:96-107 usage 分支，早于 xosd_init() |
  | 2 | `--help` | rc 0 + `USAGE:` | 同上的长选项形态 |
  | 3 | `-c red`（无 DISPLAY） | rc 1 + `Error initializing osd` | osd_clock.c:112-117；libxosd xosd.c:715-719 XOpenDisplay 失败 |
  | 4 | `-f fixed -o 5 -t -d 2`（无 DISPLAY） | rc 1 + 同串 | 证明选项被解析而非提前退出 |
  | 5 | `readelf -d` | NEEDED 含 `libxosd.so.2` | 证明链接的是被测包本体 |
  用例 3 同时是补丁 0002 的回归探针（不修则空转挂死，timeout 60 判 FAIL）。
  运行期寻库：conanrun 注入各依赖 libdir 到 `LD_LIBRARY_PATH`。

## 验证结果（实测回填）

```bash
# 探索性编译（mode B，Step 2）
$ source .build-context-osdclock-0.5 && cd $BUILD_SRC_DIR
$ make -j1 CC=/data/service/hnp/bin/clang CFLAGS="-O2 -fPIC -Wall -I. <deps -I>" \
       LDFLAGS="<deps -L>" XOSDLIBS="-lxosd -lX11 -lXext -lXinerama"   # rc=0
$ ./osd_clock -h                        # 打印 usage，rc=0
$ timeout 5 ./osd_clock -c red          # rc=1 "Error initializing osd"（无 X server）
# 补丁前对照：同一命令 rc=124（getopt 循环挂死）

# 配方链路（Step 2.5-2.6 / Step 3）
$ python3 scripts/ohc-run.py conan-verify osdclock 0.5     # G0-G4 + L2/L4/L5
$ python3 scripts/ohc-run.py finish osdclock 0.5 built     # W2 结构 + R36 依赖 + W3 本地 CI
```
- conan-verify：见 `reports/conan-verify-report.md`
- W3 本地 CI：见 `reports/w3-local-ci.log` 与 `.ci-result.json`
- test_package：`HMBS_TEST_PACKAGE_RESULT={"total":9,"passed":9,"failed":0}`
## 收尾链路实测（finish 10 步 / W3）

- `finish osdclock 0.5 built`：step 4 `conan-verify` PASS（G1–G4 + L2/L4/L5）、
  step 5 W3 本地 CI PASS（`build_and_test.sh`：L0 全过、L1 test_package executed、
  L4 patches clean、L5 bin/ 有内容，Success 1/1），step 6 归档关闭为 `built`，
  并写入 `archives/o/osdclock/0.5/.ci-result.json`（exit_code=0，含 log_sha256）。
- **非阻塞告警（已核实，非包缺陷）**：
  1. W3 `L2_RESULT=skip`：该通用 smoke 探针直接执行 `bin/osd_clock --version/--help`
     且**不注入**依赖 `libdir` 到 `LD_LIBRARY_PATH`；动态链接 libxosd 的 CLI 在探针
     环境下必然加载失败（框架标注 non-blocking）。同一次 W3 的 L1 已由 test_package
     真实执行该二进制并 9/9 全绿。
  2. `finish` step 3（G0 clean-verify）按 autotools 约定执行 `configure`，本包上游为
     手写 Makefile（无 configure）→ `configure 失败 (exit 127)`；非阻塞，构建正确性以
     step 4 的 G2（真 `conan create`）与 step 5 的 W3 为准。
  3. `finish` step 6 报 `packaging/` 缺失（框架 v2.0 遗留误报：R19 禁手工 tar 打包、
     JC3 拦压缩包入库），未伪造打包产物；`submit` 的 `packaging_present` 自检同理。
  4. `finish` step 8 `gen_summary` 报 `'str' object has no attribute 'append'`
     （框架自身缺陷，非本包），SUMMARY.md 未刷新，非致命。

## 本机环境要点（复现用）

- **HMDFS 上 shebang 脚本不可 execve**（本会话实测 EACCES）：`conan` 必须做成 ELF
  启动器（编译 C：execv 签名 python3 + `~/.local/bin/conan`）；构建产物脚本一律用
  `sh <脚本>` / `bash <脚本>` 解释器调用。这也是配方 `generate()` 实体化依赖 `.so`
  的原因（ld.lld 与 loader 都不走符号链接链）。
- **zsh heredoc 临时文件走 `TMPPREFIX`**（默认 `/tmp/zsh`），OHOS `/tmp` 只读 → 跑
  `finish`/`submit`（驱动 `ci/conan/*.sh`）时必须导出 `TMPPREFIX=<可写目录>/zsh`，
  只设 `TMPDIR` 无效（首轮实测 `can't create temp file for here document:
  read-only file system`，L0i/L0m 门禁全挂）。
- 本机 `~/.conan2` 为多会话共享，曾出现只有 symlink 的残缺包目录（libxau）；本轮改用
  隔离 `CONAN_HOME=/data/storage/el2/base/cache/conan-home-osdclock`（非 HMDFS 卷）
  后依赖包内为实体 `.so`，构建稳定。
---

**编译结束**: 2026-10-13 17:57
**最终状态**: built
