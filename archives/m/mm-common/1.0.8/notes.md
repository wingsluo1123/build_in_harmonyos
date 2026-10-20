# mm-common 1.0.8 适配笔记（OHOS）

## 1. 结论速览

| 项 | 结果 |
|----|------|
| 构建系统 | Meson（唯一可用路线），`-Duse-network=false` 离线构建 |
| 依赖（W0） | 无 conan `requires`；只依赖 worker 的 meson(≥0.62)/ninja/python3 |
| 补丁 | 1 个 portability 补丁：安装脚本文档目录改为从自身位置推导 |
| 本机验证 | 真实 Meson 1.11.1 + Ninja + gcc 12.2 复现 `--prefix=/` + `DESTDIR` 安装：34 个文件；test_package 14/14 |
| **真机验证** | **shadow CI 全绿**（`G0/KC/JC/L0/L1/L2/L4/L5` 全 pass，L1e 反向验证通过，test_package 14/14，Total 1 / Success 1），commit `f2d58bf1a7` |
| 配方状态 | `built`（真机 conan create + test_package 通过；未上传制品仓） |
| 阻塞点 | 无。真机上发现并修复 1 个配方问题（Meson combo 选项必须是字符串），记录 2 个环境坑 |

## 0. 真机验证结果（2026-10-19）

```text
runner : /storage/Users/currentUser/validation/run-ohos-shadow-ci-local.sh
repo   : /storage/Users/currentUser/validation/worktrees/mm-common (feat/mm-common-1.0.8)
commit : f2d58bf1a79e27845e27bb08710efbcd6aa35c6d
run    : $HOME/ohpc-ci-shadow/runs/f2d58bf1a79e-20261019T065234Z-41991
profile: ohos-local (os=OHOS 6.0 / armv8 / clang 15 / libc++ / cppstd17 / Release)
工具链 : conan 2.31.1、meson 1.12.1（见 §8.1）、ninja 1.12.1、python3 3.12.9、clang wrapper(15.0.4 + sysroot + --code-sign)
```

```text
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass: empty
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: mm-common-get --version OK, mm-common-prepare --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Total: 1  Success: 1  Failed: 0
```

真机侧的实质证据（原始日志见 `reports/device-shadow-ci-build.log`、`reports/device-ci-metadata.json`）：

| 检查 | 真机结果 |
|------|----------|
| `meson setup --native-file … --prefix=/` | 通过（`Use network: false`） |
| `libstdc++.tag` 离线生成 | `Warning: … does not exist in the build directory. Copying from the source directory.` → 3.6 MB |
| `skeletonmm.tar.xz` | `[2/2] Generating skeletonmm.tar.xz`，36 条目 |
| build() 产物校验 | `[ok] verified skeletonmm.tar.xz (36 entries), libstdc++.tag and 'mm-common-get 1.0.8'` |
| 安装清单 | 34 个 payload 文件（`bin/` 2、`share/aclocal/` 8、`share/man/man1/` 2、`share/mm-common/build/` 9、`doctool/` 7、`doctags/` 1、`share/doc/mm-common/` 3、`share/pkgconfig/` 2），与 meson.build 的 install 列表一致 |
| `.pc` 可重定位 | 包内两个 `.pc` 首行均为 `prefix=${pcfiledir}/../..` |
| shebang 直接执行 | `mm-common-get --version`、`mm-common-prepare --version` 均**直接执行成功**（`/usr/bin/env python3`、`/bin/sh` 在真机可用） |
| 数据目录定位 | `mm-common-get <bs> <dt>` 从包内复制出 5 个 Meson 构建脚本 + 5 个 doctool 文件 |
| test_package | `14/14 checks passed` |
| L1e 破坏性反向验证 | `Negative test confirmed — test genuinely depends on mm-common` |
| L2 smoke | 两个 CLI 的 `--version` 均 OK |
| L4 / L5 | `patches clean` / `bin/ has content` |

## 2. W0 依赖发布检查

```text
# conanfile.py 的 requires / tool_requires 为空
# 本机（ohpcd remote）抽查：
conan download "libsigc/2.12.1" -r=ohpcd --only-recipe      -> OK（registry 可达）
conan download "mm-common/1.0.8" -r=ohpcd --only-recipe     -> 不存在（首次适配，R37 无需递增后缀）
conan download "meson/1.11.1"  -r=ohpcd --only-recipe       -> 不存在（所以不能写 tool_requires("meson/…")）
conan download "ninja/1.12.1"  -r=ohpcd --only-recipe       -> OK
conan download "autoconf/2.72" -r=ohpcd --only-recipe       -> OK
conan download "automake/1.18" -r=ohpcd --only-recipe       -> OK
conan download "libtool/2.5.4" -r=ohpcd --only-recipe       -> OK
```

结论：mm-common 自身没有 conan 依赖，W0 通过。构建工具按仓库既有 meson 配方惯例依赖 worker 系统环境
（bstring/cairo/glib/libsigc 等 meson 配方同样不声明 meson 依赖）。

- 真机侧 meson 历史记录：`meson 1.11.1（预编译包）`、`ninja 1.13.1`，多个配方 notes 记录 meson 从 cmd-pkgs 安装。
- 本包要求 `meson >= 0.62.0`（1.0.8 NEWS 明确写出），1.11.1 满足。
- 若 worker 上 `meson --version` 缺失或过低，先按既有做法用 cmd-pkgs 装预编译 meson，或在 runner 环境
  `python3 -m pip install --user "meson>=0.62"`（不要写进 recipe 的 tool_requires，因为 ohpcd 没有 meson 包）。

## 3. 源码与构建系统分析

上游 `mm-common-1.0.8.tar.xz`（sha256 与 download.gnome.org 的 `.sha256sum` 一致）：

```text
am_include/   4 个 .am 片段（compile-binding/dist-changelog/doc-reference/generate-binding）
doctags/      libstdc++.tag（3.6 MB，离线可用的 doxygen tag 文件）
macros/       mm-*.m4 ×7 + mm-common.m4.in
skeletonmm/   骨架绑定模块（被打包成 skeletonmm.tar.{gz,xz} 安装）
util/         mm-common-get.in / mm-common-prepare.in / 文档工具 / meson_aux 辅助脚本
configure.ac  Makefile.am  meson.build  meson_options.txt
autogen.sh    ← 没有 configure，也没有 Makefile.in
```

关键判断：

1. **tarball 是 `meson dist` 产物**：没有 `configure`。走 Autotools 必须先 `autoreconf`
   （autoconf + automake + libtool + maintainer mode），把一个 0 编译的包变成 autotools 项目，
   只会引入 4 个工具链依赖，收益为负。
2. **Meson 路线是上游一等公民**：`meson.build` 里有 configure_file、install_data、pkgconfig.generate、
   custom_target，1.0.8 的新特性（`-Duse-network=if-no-local-tag-file`）也是 Meson 路线先有。
3. 整个项目 **不编译任何 C/C++ 代码**，`project()` 只因为默认语言是 C 才需要一次编译器探测；
   产物是脚本 + 数据 + 手册页 + 骨架归档。
4. `meson test` 没有测试目标（tarball 里也没有 `tests/`），所以不能用 `meson.test()` 冒充“上游测试通过”。

## 4. 配方设计

```text
package_type = "application"           # 纯工具/数据包，消费方用 tool_requires
settings     = os, arch, compiler, build_type
options      = {"use_network": [True, False]}, default False
generate()   -> MesonToolchain + project_options["use-network"]="false"（字符串，见 5.4）
build()      -> meson.configure() + meson.build() + _verify_build_outputs()
package()    -> meson.install() + _relocate_pkg_config_files()
package_info -> bindirs=["bin"] + buildenv ACLOCAL_PATH=<pkg>/share/aclocal
```

- `use-network=false`：`util/meson_aux/libstdcxx-tag.py` 在 false 分支里从源码树
  `doctags/libstdc++.tag` 复制，不联网。CI/worker 没有外网，必须这么设。
  该选项是 combo，**必须传字符串**（§5.4 是真机暴露的问题）。
- `_verify_build_outputs()`：check 两个 custom_target 产物（`skeletonmm.tar.*` 内有
  `skeletonmm/meson.build` 等条目、`libstdc++.tag` 非空）以及生成的 `mm-common-get --version`。
  这是本项目自身的产物验收，替代不存在的上游测试套件。
- `_relocate_pkg_config_files()`：见第 5.2 节。

## 5. OHOS 适配点

### 5.1 补丁 0001：安装脚本按自身位置找数据

Conan 的 Meson 前端固定用 `--prefix=/` 配置、`meson install --destdir <pkg>` 安装，
于是上游模板里的 `@prefix@`/`@datadir_py@` 会被烤成：

```text
util/mm-common-prepare.in   prefix="@prefix@"  datarootdir="@datarootdir@" datadir="@datadir@"
                            -> prefix="/" datarootdir="${prefix}/share" datadir="${datarootdir}"
util/mm-common-get.in       pkgdatadir = os.path.join('@datadir_py@', 'mm-common')
                            -> pkgdatadir = '/share/mm-common'
```

安装到 Conan cache 后 `/share/mm-common` 并不存在，`mm-common-get` 复制文件、`mm-common-prepare`
复制 `.am` 都会 `No such file or directory`。补丁把两者的数据目录改成从脚本自身位置推导：

```sh
self=$0
case $self in
*/*) ;;
*) self=`command -v "$self"` || self=$0 ;;
esac
prefix=`cd "${self%/*}/.." && pwd`
```

```python
if os.sep in sys.argv[0] or (os.altsep and os.altsep in sys.argv[0]):
  script_path = os.path.realpath(sys.argv[0])
else:
  script_path = os.path.realpath(shutil.which(sys.argv[0]) or sys.argv[0])
pkgdatadir = os.path.join(os.path.dirname(os.path.dirname(script_path)),
                          'share', '@PACKAGE_TARNAME@')
```

对普通（非 staging）安装同样正确：前缀就是脚本所在 `bin/` 的上一级；对 autotools 的
`Makefile.am` 安装（同一份 `.in`）也一样。补丁只改 `.in` 模板，不碰生成物，符合 R6。

### 5.2 `.pc` 文件的可重定位改写

Meson 1.11 的 pkgconfig 模块在没有 `pkgconfig.relocatable` 选项时写死 `prefix=/`：

```text
prefix=/
datadir=${prefix}/share
includedir=${prefix}/include

datarootdir=${datadir}
pkgdatadir=${datadir}/mm-common
doctooldir=${pkgdatadir}/doctool
```

`pkg-config --variable=doctooldir mm-common-util` 会返回 `/share/mm-common/doctool`，指到包外面。
`package()` 里把首行改成 `prefix=${pcfiledir}/../..`（安装位置是 `<pkg>/share/pkgconfig/*.pc`），
所有变量就都落在包内。没有改用 `-Dpkgconfig.relocatable=true`，因为它是 Meson 1.11 新选项，
worker 上的 meson 版本不保证 ≥1.11。

### 5.3 与 OHOS 运行时相关的观察项（**真机已确认**）

| 项 | 真机结果 |
|----|----------|
| `#!/usr/bin/env python3` | ✅ 直接执行成功（`mm-common-get --version` → `mm-common-get 1.0.8`） |
| `#! /bin/sh -e` | ✅ 直接执行成功（`mm-common-prepare --version` → `mm-common-prepare 1.0.8`） |
| `mm-common-prepare` 依赖 `sed`/`mkdir`/`cp` | ✅ test_package 在真机实跑两轮复制流程，全部通过 |
| `MM_CONFIG_DOCTOOL_DIR` 父目录 | ✅ test_package 按真实布局建 `doc/` 后通过 |
| meson 版本 | ✅ 真机 1.12.1（≥0.62；注意 §8.1 的隔离 HOME 坑） |
| 安装权限 | `bin/` 两个脚本为 `-rwxr-x---`，可执行 |

### 5.4 Meson combo 选项必须传字符串（真机暴露的配方 bug）

第一轮真机 shadow CI 在 `meson setup` 处失败：

```text
../src/meson.build:3:0: ERROR: Value "False" (of type "boolean") for option
"use-network" is not one of the choices. Possible choices are (as string):
"false", "if-no-local-tag-file", "true".
```

原因：`MesonToolchain.project_options["use-network"] = True/False` 会被 Conan 写成
machine file 里的裸布尔 `use-network = false`；上游该选项是 `combo`（choices 全是字符串），
Meson ≥ 1.12 对 combo 选项收到布尔值直接报错。修法是传字符串：

```python
tc.project_options["use-network"] = "true" if self.options.use_network else "false"
# 生成的 machine file: use-network = 'false'
```

本机 Meson 1.11.1 不报这个错，所以只有真机（1.12.1）能暴露；修正后两边都通过。

## 6. 本机验证（上真机前的预演）

工具链：Meson 1.11.1 + Ninja 1.11.0 + gcc 12.2.0（Windows 本机），Python 3.12.7，Conan 2.29.1。
这些是本机复现 `--prefix=/` + `DESTDIR` 语义，真机结果见 §0。

1. 补丁用 Conan 同一套 `patch_ng`（`apply_conandata_patches` 的实现）`strip=0` 应用，产物与作者版本逐字节一致。
2. `meson setup --prefix=/ -Duse-network=false` + `meson compile` + `meson install --destdir`：
   34 个文件，路径与 `meson.build` 的 install 列表完全一致；`libstdc++.tag` 3,604,992 字节（离线复制成功）；
   `skeletonmm.tar.xz` 36 个条目。
3. `conan export` 通过；`conan install` 用仓库 `ci/conan/profiles/ohos-aarch64` 跑通 `generate()`。
4. 把 recipe 的 `_verify_build_outputs()` 直接作用在真实 Meson 构建目录上：通过；把 `version` 改成 0.0.0 会失败（负向对照）。
5. `test_package/test_mm_common.py` 在真实 `meson install` 出来的树上 14/14 通过。
6. L1e 破坏性反向验证模拟：把 `<pkg>/bin` 移走后 test_package 必然失败（`mm-common-get/prepare` 不在 PATH），
   说明测试真的依赖被测包产物。
7. 用 Conan 生成的 `conan_meson_native.ini`（把编译器替换成本机 gcc）做 `meson setup`：`Use network: false`，
   证明 machine file 的 `[project options]` 段可用（§5.4 的修复即在此验证）。

详细命令与日志见本目录 `reports/`（`TEST_REPORT.md`、`verification-logs.txt`、真机
`device-shadow-ci-build.log`、`device-ci-metadata.json`；按仓库 `.gitignore` 的 `reports/` 规则不入库）。

## 7. 已执行的命令与后续提交

```sh
# 已执行（真机 shadow CI，单包，全绿）
cd $HOME/validation/worktrees/mm-common            # commit f2d58bf1a7
export TMPDIR=$HOME/xfer/tmp TMPPREFIX=$TMPDIR/zsh  # /tmp 只读，必须设置
sh $HOME/validation/run-ohos-shadow-ci-local.sh archives/m/mm-common/1.0.8
#  G0/KC/JC/L0/L1/L2/L4/L5 pass，L1e confirmed，test_package 14/14，Total 1 / Success 1

# 后续：推分支 + 走 W4/W5 + submit 建 PR（本会话未执行）
git push origin feat/mm-common-1.0.8
python3 $SKILL_ROOT/scripts/pre_pr_audit.py generate --repo-dir <repo> --package mm-common --version 1.0.8
#   → 审计子任务 → pre_pr_audit.py report → ohc-run.py submit mm-common 1.0.8
```

失败时的定位顺序（真机实测有效）：

1. `TMPDIR`/`TMPPREFIX` 是否设置（`/tmp` 只读，heredoc 会直接失败）；
2. 隔离 `HOME`/`PYTHONUSERBASE` 下 `meson` 能否 import `mesonbuild`（§8.1）；
3. profile 里 `tools.build:compiler_executables` 指向的 clang wrapper 是否可执行；
4. Meson 版本（≥0.62）与 combo 选项类型（§5.4）；
5. `/usr/bin/env`、`/bin/sh` 是否可执行（真机已确认可用）。

## 8. 真机环境坑（本轮实测，非配方问题）

### 8.1 隔离 HOME 下 `~/.local/bin/meson` 失效

真机 meson 装在**用户 site**：`~/.local/bin/meson`（pip console script）+
`~/.local/lib/python3.12/site-packages/mesonbuild`。shadow runner 用隔离环境
（`HOME=$RUN_ROOT/home`、`PYTHONUSERBASE=$HOME/ohpc-ci-shadow/python-user`），用户 site 因此
不再包含 `~/.local/lib/python3.12/site-packages`，于是：

```text
File ".../meson", line 3, in <module>
ModuleNotFoundError: No module named 'mesonbuild'
```

修法（环境层，不改仓库）：

```sh
export PYTHONUSERBASE=$HOME/ohpc-ci-shadow/python-user
python3 -m pip install --user "meson>=0.62"    # 装到 runner PATH 的第一位
```

安装后隔离环境里 `meson --version` → 1.12.1，shadow CI 通过。仓库里其它 meson 包如果哪天
在 shadow CI 上报同样的 `No module named 'mesonbuild'`，先看这条。

### 8.2 CI pre-download 的裸 `curl` 在这台机器上 exec 失败

`ci/conan/build_and_test.sh` 的 pre-download 用 `subprocess.run(["curl", ...])`（依赖 execvp 的
PATH 搜索）。本机镜像上：

```text
[try …] [fail] [Errno 2] No such file or directory: 'curl'
```

但 `/usr/bin/curl` 绝对路径可执行、shell 里 `command -v curl` 也能找到 —— 同一环境下
`subprocess.run(["ls"/"sh"/"ninja"])` 也会分别报 ENOENT/EACCES，属该镜像的裸名 exec 限制。
影响面：只是失去 pre-download 加速，conan 自己的下载器仍然工作（本次从 NJU 镜像取回源码）。
不是本包问题，已在提交说明里注明，未改 CI 脚本。

### 8.3 GNOME 源码镜像：只有 NJU 命中

CI 的镜像重写把 `download.gnome.org` 扩成 USTC / TUNA / NJU / 官方四路，实测：

```text
mirrors.ustc.edu.cn/gnome/…            -> 404
mirrors.tuna.tsinghua.edu.cn/gnome/…   -> 404
mirror.nju.edu.cn/gnome/…              -> OK
download.gnome.org（官方）               -> 未尝试（前三路已成功/或 conan 直连）
```

其它 GNOME 包适配时可参考：USTC/TUNA 的 GNOME 镜像路径不是 `/gnome/`。

## 9. 已知限制

- 尚未上传制品仓（`built` 而非 `published`），PR 走 release 流水线后才 upload。
- `ACLOCAL_PATH`（buildenv_info）只在 Autotools 消费方生效；真机未装 aclocal，未实测。
- Meson 的 `pkgconfig.relocatable` 选项（≥1.11）没有采用，`.pc` 改写只在 package() 里做，属于最小改动。
- 源码只有 `download.gnome.org` 一个 URL（官方源，R39）；真机通过 CI 的镜像重写成功取回，
  未在 conandata.yml 里预置镜像，避免无法证明等价性。
