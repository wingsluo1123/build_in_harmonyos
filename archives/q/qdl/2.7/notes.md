# qdl 2.7 — OpenHarmony PC 适配笔记

> 载体：`archives/q/qdl/2.7/`
> 目标平台：OpenHarmony PC（OHOS 6.0 / aarch64 / clang 15 / libc++ / **原生构建**）
> 结论速览：**两个补丁**（都只碰 `tests/`：`uname` 平台判据 + `zip` 工具回退），
> 三条上游测试链路（6 条 meson test：4 单元 35 subtest + 2 集成）在真机全部真实执行
> 并通过（`Ok: 6 / Fail: 0`）；消费者用例 11/11；包内只有 `bin/qdl`、`bin/qdl-ramdump`、
> `bin/qdl-ks` 三个可执行文件。

---

## 1. 上游事实（对 v2.7 tarball 的静态审计）

### 1.1 源码包

| 项 | 值 |
|---|---|
| 官方 URL | `https://github.com/linux-msm/qdl/archive/refs/tags/v2.7.tar.gz` |
| 官方 URL 对应 tag | `v2.7` → commit `f540e59dbeb462242239778ae0993549304f3abb` |
| 大小 | 110260 bytes |
| sha256 | `0eee137badceb8dfc6b2bc43af7223e5770d48be5eeab5c808c08cf1beb1de9a` |
| 顶层目录 | `qdl-2.7/`（单根目录，`strip_root=True` 可用） |
| 许可证 | BSD-3-Clause（仓库根 `LICENSE`） |

三路下载（官方直连 / ghfast.top / gh-proxy.com）**sha256 逐字节一致** —— 这与
上游把 tag 打成 `archive/refs/tags/` 归档一致，可复现性有保障。同仓 GitHub 项目
先例 `archives/2/2048.c/1.0.3` 用的也是这一形态的 URL。

### 1.2 构建定义（`meson.build` 6680 B）

```
project('qdl', 'c',
  default_options : ['warning_level=2', 'optimization=2'],
  license: 'BSD-3-Clause',
  meson_version: '>=1.1.0')

libusb_dep  = dependency('libusb-1.0')
libxml_dep  = dependency('libxml-2.0')
libzip_dep  = dependency('libzip')
help2man    = find_program('help2man', required: false)
cmocka_dep  = dependency('cmocka', required: get_option('tests'))
```

- **三个必需依赖**：`libusb-1.0`、`libxml-2.0`、`libzip`，全部走 pkg-config。
- **两个可选依赖**：
  - `help2man`：`required: false`，找不到就整段跳过 man 页 `custom_target`
    —— 这一条很重要，见 §3.3；
  - `cmocka`：`required: get_option('tests')`，而 `meson.options` 里
    `option('tests', type: 'feature', value: 'auto')` ⇒ **cmocka 在就自动启用**。
- **版本**：`run_command('git','describe','--dirty','--always','--tags', check: false)`，
  且 `env_v = get_option('VERSION')` 优先于 git 结果。上游 `meson.options` 提供了
  `VERSION` 选项正是为 tarball 场景准备的（见 §3.2）。

### 1.3 产物：没有库，只有三个可执行文件

```
shared_lib = static_library('qdl_common', common_sources, dependencies: common_dep)
              ^ 没有 install: true —— 不进包

qdl_exe        = executable('qdl',        ..., install : true)
qdl_ramdump_exe= executable('qdl-ramdump',..., install : true)
qdl_ks_exe     = executable('qdl-ks',     ..., install : true)
```

`install : true` 只出现在这三个 `executable()` 上；`include_directories('.')` 是
内部头（`pathbuf.h`/`contents.h`/`vip.h` …），**没有任何头文件被 install**。

⇒ 这是一个**纯工具包**：包内容 = `bin/{qdl,qdl-ramdump,qdl-ks}`（+ 可能没有的
`share/man/man1/*.1`）。对应 conan `package_type = "application"`，
并按 L0k 在**软件级**目录提供 `commands.json`。

### 1.4 上游测试：meson 注册 6 条

| # | meson test 名 | 源文件 | 类型 |
|---|---|---|---|
| 1 | `VIP table generation` | `tests/test_vip_generation.sh` | 集成（bash，suite: integration） |
| 2 | `Flashmap dry-run` | `tests/test_flashmap.sh` | 集成（bash，protocol: tap） |
| 3 | `program_load_xml path resolution` | `tests/test_program_load_xml.c` | 单元（cmocka） |
| 4 | `pathbuf dirname behavior` | `tests/test_pathbuf.c` | 单元（cmocka） |
| 5 | `contents selector resolution` | `tests/test_contents_selectors.c` | 单元（cmocka） |
| 6 | `contents XML parsing` | `tests/test_contents_xml.c` | 单元（cmocka） |

单元测试里 `cmocka_unit_test[_setup_teardown]` 在源码中共出现 **37 次**，但其中
`test_pathbuf.c` 的 `test_dirname_windows_drive` / `test_dirname_windows_unc`
两个注册包在 `#ifdef _WIN32` 里，POSIX（含 OHOS）不参与 ⇒ **真机实际注册并执行的
是 35 个**（实测 meson 报 `6/8/14/7 subtests passed`，合计 35）。
`assert_*` 出现 **131 次**（含 5 个文件内自定义断言辅助）。

### 1.5 集成测试的三个非显然依赖

`tests/data/generate_flat_build.sh`（被两条集成测试共用）会：

```sh
create_file_with_size prog_firehose_ddr.elf 20     # 全部是稀疏零字节文件：
create_file_with_size efi.bin 8192                 # dd if=/dev/zero bs=1024 count=0 seek=N
... 共 9 个 ...                                     # O(1) 分配，不写 1 GB 数据
cp "$SCRIPT_PATH"/*.xml "$OUTDIR"/                 # 4 个 XML
(cd $OUTDIR ; zip flashmap.zip ...)                # ← 需要 zip 命令
```

即：**需要 `zip`**（只有 flashmap 那条用），需要 `dd` 的 `seek=` 稀疏写，
`test_vip_generation.sh` 还需要 `sha256sum` 或 `shasum`。

⚠️ 这个 `zip` 是**真需求**，不是可有可无：`test_flashmap.sh` 用它产出的
`flashmap.zip` 正是第二条用例的输入（`qdl --dry-run flash flashmap.zip`），
删掉就等于删掉"从 zip 归档刷机"这条被测能力。真机上 `zip` 确实装着
（`/usr/bin/zip`，Info-ZIP 3.0，`-rwxr-xr-x`，`/usr/bin` 共 179 个条目），
但**从 conan 进程里根本取不到**——原因见 §4.2。

`tests/data/*.xml` **本身是 CRLF 行尾**（`patch0.xml` 6247 B 含 32 个 CR）——
消费者用例复制固定装置时必须逐字节照搬，见 §6。

---

## 2. 配方决策表

| # | 决策 | 值 | 理由 |
|---|---|---|---|
| 1 | `package_type` | `application` | 没有任何库/公共头可链接（§1.3） |
| 2 | `options` | 无 | 没有 `default_library` 语义（唯一的库里已写死 `static_library`），也就没有 `shared`/`fPIC` |
| 3 | `requirements` | `libusb/1.0.27`、`libxml2/2.15.3.1`、`libzip/1.11.4` | 制品仓实测存在且**都生成 pkg-config**（§3.1） |
| 4 | `test_requires` | `cmocka/2.0.2` | 只被 4 个单元测试二进制链接，不进包、不传消费者 |
| 5 | `tool_requires` | `meson/1.11.0` | 真机无 meson（§3.2） |
| 6 | `VERSION` 选项 | `2.7` | tarball 无 `.git` ⇒ 不钉会打成 `unknown-version`（§3.2） |
| 7 | `wrap_mode` | `nodownload` | 上游无 subprojects，把"永不下载"显式化（CI 无外网） |
| 8 | `b_ndebug` | `false` | 保持上游（默认 debug）的断言语义（§3.3） |
| 9 | `ar`/`ranlib` | 绝对路径注入 `tc.binaries` | OHOS 上是 `llvm-ar`/`llvm-ranlib`（§3.5） |
| 10 | meson 包装脚本 | 去 shebang（幂等） | 否则 `Error 126`（§3.4） |
| 11 | `patches` | 2 个，只碰 `tests/` | `uname -s` 判据 + `zip` 回退（§4） |
| 12 | `package_info` | 只 `bindirs = ["bin"]` | 无可链接物 |

---

## 3. 移植障碍与解法（逐项）

### 3.1 依赖可得性：先证实，再写配方

配方写死版本号之前，在真机上直接实测了「制品仓有没有、pkg-config 名字对不对」：

```
$ conan list libusb/* -r=ohpcd     → libusb/1.0.27
$ conan list libxml2/* -r=ohpcd    → libxml2/2.15.3, libxml2/2.15.3.1
$ conan list libzip/* -r=ohpcd     → libzip/1.11.4
$ conan list cmocka/* -r=ohpcd     → cmocka/2.0.2
```

再用一个一次性消费者装一遍，检查 meson 真正要找的四个 pkg-config 名：

| meson 写法 | 需要的 .pc | 实测 |
|---|---|---|
| `dependency('libusb-1.0')` | `libusb-1.0.pc` | ✅ `Libs: -lusb-1.0 -lpthread`，`includedir=…/include/libusb-1.0` |
| `dependency('libxml-2.0')` | `libxml-2.0.pc` | ✅ `Libs: -lxml2 -lm`，`includedir=…/include/libxml2` **+** `includedir1=…/include` |
| `dependency('libzip')` | `libzip.pc` | ✅ `Libs: -lzip` |
| `dependency('cmocka')` | `cmocka.pc` | ✅ `Libs: -lcmocka` |

顺带确认了头文件风格对得上：上游 `#include <libusb.h>`、`<libxml/parser.h>`，
而 libusb 的 `includedir` 直接就是 `include/libusb-1.0`、libxml2 同时给了
`include/libxml2` 与 `include` ⇒ **不需要任何补头目录的操作**
（与 vali 那种「上游写扁平兼容头」的情形不同）。

### 3.2 版本号：不钉就是 `unknown-version`

上游用 `git describe` 推版本，而 tarball 解包出来的源码树**没有 `.git`**：

```
git_check_ver = run_command('git','describe','--dirty','--always','--tags', check:false).stdout().strip()
git_v = git_check_ver != '' ? git_check_ver : 'unknown-version'
env_v = get_option('VERSION')
ver   = env_v != '' ? env_v : git_v            # env_v 优先
```

不干预的话 `version.h` 会是 `#define VERSION "unknown-version"`，`qdl --version`
（`util.c:33`：`fprintf(stdout, "%s version %s\n", __progname, VERSION)`）就会打出
假版本。配方写一行 `tc.project_options["VERSION"] = str(self.version)` 即可 ——
这不是"为了让测试通过而 hack"，而是用上游**专门为此提供的选项**。

### 3.3 `b_ndebug`：保持上游的断言语义

- CI profile 是 `build_type=Release` ⇒ MesonToolchain 写 `b_ndebug='true'` ⇒ 定义 `NDEBUG`。
- 上游 `meson.build` 的 `default_options` **没有** buildtype，上游 CI
  （`.github/workflows/build.yml`）用的是 `meson setup build` 的默认 `debug`
  ⇒ 上游从来是在 assert 打开的状态下构建与测试的。
- 上游源码里有一处真实断言：`program.c:366  assert(op->type == FIREHOSE_OP_ERASE);`

⇒ 覆写 `tc.b_ndebug = "false"`，让产物行为与上游一致。（`b_ndebug` 是 meson 的
combo 选项，conan 按字符串写进 native file，直接赋 `"false"` 即可。）

### 3.4 坑：tool_requires 的 meson 包装脚本无法 `execve`（`Error 126`）

这是本包**唯一一个会让 `conan create` 直接崩掉**的坑，值得完整记录。

**症状**（首轮 `conan create`）：

```
/bin/sh: /storage/Users/currentUser/.conan2/p/…/p/bin/meson: Permission denied
ERROR: ConanException: Error 126 while executing … meson …
```

**第一直觉是权限位** —— 但真机实测把它排除了：

| 观测 | 结果 |
|---|---|
| `ls -l` 该文件 | mode `0770`，属主非构建用户，组 `file_manager` **在进程 groups 内** |
| `os.access(path, X_OK)` | `True` |
| `os.chmod(path, 0o775)` | **返回 0，但 mode 纹丝不动**（知识库 E046 的"静默失效"） |
| 同一进程里用 shell 跑它 | ✅ 能跑（`sh script` 也行） |
| 同一进程里用 Python `subprocess` 跑它 | ❌ `EACCES` |

**二分**：把首行 shebang 换成 `#!/bin/sh`、`#!/system/bin/sh`、
`#!/data/service/hnp/bin/bash` —— **三种全部 EACCES**，报
`bad interpreter: Permission denied`；把首行 shebang **删掉**，`execve` 返回
`ENOEXEC`，POSIX shell 回退成"按脚本解释执行" ⇒ `shell=True` 下 **rc=0**。

**结论**：OHOS 上 conan 的 `run()` 走 Python `subprocess`，而**沙箱内带 `#!`
的脚本一律 execve 失败**；判据是**文件有没有 shebang**，与权限位、属主、路径无关。

**解法**（`conanfile.py` 的 `_fix_meson_launcher()`）：把 `bin/meson` 的首行
shebang 去掉、脚本体一字不改，用 `os.replace()` 换文件（目录写权限就够，不需要
属主），然后立刻按 conan 的方式（`shell=True` 调 `/bin/sh -c`）**实跑一次**
`--version` 把 rc 写进日志。幂等：首行已不是 `#!` 时一个字节都不动。

**日志措辞的自我要求**：自检那行写的是
`meson launcher usable via /bin/sh (shebang-free)` —— 因为它在"刚改写过"和
"上一轮已改写过"两条路径上都会执行，只断言"现在可用"才是事实。

**两个别踩的坑**：
1. **别用 chmod 修**：真机上 `chmod` 返回 0 但 mode 不变；
2. **别信"手工能跑"**：shell 能跑、Python 不能跑，正是这个坑的全部特征。

### 3.5 `ar` / `ranlib`：MesonToolchain 不写，需自己注入

conan 的 `MesonToolchain` 只从 buildenv 的 `AR`/`RANLIB` 取值，而 CI profile 的
`tools.build:compiler_executables` 只给了 `c`/`cpp` ⇒ 它写不出 `ar`/`ranlib`，
meson 便按裸名探测。OHOS 的归档器在 `/data/service/hnp/bin`，名字是
`llvm-ar` / `llvm-ranlib`，**裸名在 PATH 上找不到** ⇒ configure 阶段失败。

两件事一起做：
1. `generate()` 开头 `os.environ.pop()` 掉 `AR/AS/STRIP/NM/RANLIB` —— CI 会
   把它们 export 成 `llvm-*` 名字（`ci/conan/build_and_test.sh` 的 `conf_map`），
   一旦被原样写进 native file，meson 会报 `Program 'llvm-ar' not found`；
2. 从 `tools.build:compiler_executables` 的 `c` 编译器路径取同目录，找
   `llvm-ar`/`llvm-ranlib`（退回 `shutil.which`），用**官方 API**
   `tc.binaries["ar"]/["ranlib"]` 写绝对路径。

同款先例：`archives/v/vali/0.1.1`、`archives/a/aml/1.0.0`、`archives/c/cairo/1.18.4`。

### 3.6 可选项为什么都不用管

| 可选点 | 上游写法 | 真机实测 | 影响 |
|---|---|---|---|
| `help2man` | `find_program('help2man', required: false)` | **没有** help2man | man 页 `custom_target` 整段跳过 ⇒ **构建期不会去运行刚编出来的 qdl**（少了"未签名二进制能否 exec"这一风险面） |
| `bash` | `find_program('bash')`（必需） | `/data/service/hnp/bin/bash` 5.3.0，在 PATH 上 | 集成测试可跑（meson 在 configure 期就把它解析成绝对路径写进 test 定义） |
| `zip` | 只在 `generate_flat_build.sh` 里用 | 装着（`/usr/bin/zip`）但 **HMMAC 域读不到**（§4.2） | 必须打补丁回退到 `python3 -m zipfile` |
| `sha256sum` / `shasum` | vip 测试二选一 | 解析到 `/system/bin/sha256sum`（`/usr/bin` 那份取不到，不影响） | 可跑 |
| `dd` 的 `seek=`/`status=none` | 造稀疏 fixture | 实测 rc=0，20 KB 稀疏文件瞬间建好 | 可跑 |
| `mktemp` | flashmap 测试 | 跟随 `TMPDIR`（`/storage/Users/currentUser/tmp`） | 可跑 |

> **`/tmp` 只读这件事**：真机 `/tmp` 存在但 `mkdtemp('/tmp/…')` 报
> `Read-only file system`。上游 `tests/common.c` 的 POSIX 分支确实硬编码
> `snprintf(buf, size, "/tmp/%s-XXXXXX", …)`。但该函数 `test_make_temp_dir()`
> **全仓没有任何调用点**（`grep -rn 'make_temp_dir'` 只有 common.c 的定义与
> common.h 的声明）—— 是死代码，因此**不需要为它打补丁**。
> 这条特意查过，避免"看起来该补"就多打一个补丁。

---

## 4. 两处上游改动（都只碰 `tests/`）

### 4.1 `uname -s` 平台判据

`tests/test_vip_generation.sh:42` 与 `tests/test_flashmap.sh:29` 都有：

```sh
uname_out="$(uname -s)"
case "${uname_out}" in
    Linux*|Darwin*)           QDL=qdl ;;
    CYGWIN*|MINGW*|MSYS*)     QDL=qdl.exe ;;
    *)                        exit 1 ;;      # ← HarmonyOS 掉这里
esac
```

真机 `uname -s` 返回 **`HarmonyOS`**（`uname -s -m` → `HarmonyOS aarch64`）
⇒ 两条集成测试在 `set -e` 下立刻 `exit 1`。而 `meson.test()` 只要有一条 `test()`
失败就返回非 0，`conan create` 整体失败；这两条又恰好是覆盖 qdl 真实功能
（VIP 表生成、flashmap dry-run）的集成测试，**不能裁掉**。

补丁（`patches/0001-tests-accept-harmonyos-uname.patch`，592 B）只做一件事：

```
-    Linux*|Darwin*)
+    Linux*|Darwin*|HarmonyOS*)
```

**这属于上游平台判据缺失的可移植性修复，不是"把测试改到能过"**：
改动只落在 `tests/` 两个 shell 脚本的 case 分支上，产物代码（`*.c`）一行未动，
测试的判据（EXPECTED_DIGEST 比对、TAP 两项）全部保持原样。

### 4.2 `zip` 取不到：HMMAC 域限制 + 回退到 `python3 -m zipfile`

**现象**：修好 §4.1 之后重跑 `conan create`，4 条 cmocka 单元测试全绿
（`6/8/14/7 subtests passed`），但两条集成测试都以 **退出码 127** 失败：

```
/…/build/tests/data/generate_flat_build.sh: line 37: zip: command not found
```

**排查**（真机逐层实测，全部有原文）：

| 检查 | 结果 |
|---|---|
| `/usr/bin/zip` 是否存在 | **存在**：`-rwxr-xr-x root root 182768`，`/usr/bin` 共 179 个条目 |
| 宿主 shell 里能不能跑 | `zip -v` rc=0；照抄第 37 行在临时目录里 `zip test.zip a b` → **成功**，`test.zip` 282 B |
| `PATH` 里有没有 `/usr/bin` | **有**：`/data/service/hnp/bin:…:/system/bin:/usr/bin:/bin:…` |
| 那为什么 `command -v zip` 仍是空 | 因为 **进程域**不对，不是 PATH 不对 |

关键证据是 HMMAC（HarmonyOS 强制访问控制）的**域**对照：

```
宿主交互 shell : exe=/system/bin/sh          domain = u:r:hishell_hap:s0   → ls /usr/bin 正常，179 项
用户目录里的程序: exe=/storage/…/python3      domain = u:r:adhoc_bin:s0     → listdir('/usr/bin') → PermissionError
conan create 里 : exe=/system/bin/toybox      domain = u:r:adhoc_bin:s0     → ls -l /usr/bin/zip → Permission denied
```

两边 `/proc/self/ns/mnt` **完全相同**（`mnt:[4026532300]`），`/usr/bin` 的
mount id 也相同（`4127 3985 … erofs /dev/block/dm-0 ro,hmmac=inherit_parent`）
⇒ **不是缺文件、不是权限位、不是命名空间，纯粹是 MAC 域判定**：
凡是从**用户可写目录**（`/storage/Users/...`）启动的可执行文件，进程都会切进
`u:r:adhoc_bin:s0`，而该域**读不到 `/usr/bin`**。`/system/bin`、
`/data/service/hnp`、`/storage/Users/currentUser` 都正常可读。

这条链之所以致命，是因为 **conan 自己就是
`/storage/Users/currentUser/usr/local/bin/python3`**：`conan create` 一旦启动，
**整棵子进程树**都被锁在 `adhoc_bin` 域里，再也看不到 `/usr/bin/zip`。
配方侧无法自救（除非不去用 `/usr/bin`）。

**解法**（`patches/0002-tests-portable-zip-fallback.patch`，1206 B）：
把 `generate_flat_build.sh` 最后那步归档改成「有 `zip` 就用 `zip`，否则回退
Python 标准库」：

```sh
ZIP_FILES="prog_firehose_ddr.elf efi.bin gpt_backup0.bin gpt_backup1.bin \
	   gpt_main0.bin gpt_main1.bin rootfs.img xbl_config.elf xbl.elf \
	   rawprogram0.xml rawprogram1.xml patch0.xml patch1.xml flashmap.json"

if command -v zip >/dev/null 2>&1; then
	(cd $OUTDIR ; zip flashmap.zip $ZIP_FILES)
elif command -v python3 >/dev/null 2>&1; then
	(cd $OUTDIR ; python3 -m zipfile -c flashmap.zip $ZIP_FILES)
else
	echo "generate_flat_build.sh: neither 'zip' nor 'python3' is available" >&2
	exit 1
fi
```

为什么这是可移植性修复而不是"绕过测试"：

- **Linux / macOS / Cygwin 上行为一个字都没变** —— 那些平台上 `zip` 一定在
  PATH 上，走的仍是原来的 Info-ZIP 分支；
- 回退产出的仍是**标准 zip**（实测 `compress_type=8`，与 Info-ZIP 默认的
  deflate 一致，Python 的 `-m zipfile -c` 就是 `ZIP_DEFLATED`），
  被测能力 `qdl --dry-run flash flashmap.zip`（读 zip 归档刷机，
  走 `zipper.c` + libzip）**原封不动**；
- 断言完全没动：flashmap 的 TAP 两项、vip 的 `EXPECTED_DIGEST` 比对都保持原样；
- 产物代码（`*.c`/`meson.build`）一行未动；
- `python3` 在 conan 环境下必然存在（conan 本体就跑在 Python 3.12.9 上），
  且实测在该域内可用（`command -v python3` →
  `/storage/Users/currentUser/usr/local/bin/python3`）。

补丁本地过 `patch -p1 --dry-run` 与 `sh -n` / `bash -n`，两个补丁叠加后结果与
手改副本逐字节一致。

---

## 5. 上游测试真实执行

`build()` 里 `meson.configure()` → `meson.build()` → `meson.test()`
（等价于 `meson test -v -C <build>`），不裁剪任何测试：

```
self.output.info("Meson upstream test: meson test -v -C {}".format(self.build_folder))
meson.test()
```

那行显式 `output.info` 是给 CI 的 L1c 判据用的（日志里要能看到 `meson test`）。
实测结果见 §10.3（4 条单元 + 2 条集成共 6 条，`Ok: 6 / Fail: 0`）。

---

## 6. 消费者用例设计（工具包语义）

这个包**没有库、没有公共头**，所以 "消费者" 只能是"拿到可执行文件的人"。
`test_package/test.sh` 因此按真实用法验证（共 11 个检查点）：

| # | 检查 | 为什么值得查 |
|---|---|---|
| 1 | `qdl --version` 报 2.7 | 钉住配方 `VERSION` 注入（§3.2）—— 不钉就是 `unknown-version` |
| 2 | `qdl --help` rc=0 | 用法能打印 |
| 3–6 | usage 里含 `--dry-run`/`--create-digests`/`--backend`/`--serial` | 证明拿到的是**真 qdl**，不是同名占位 |
| 7–8 | `qdl-ramdump --help`、`qdl-ks --help` | 三个 install 目标都在包里 |
| 9 | `qdl --dry-run --create-digests=<dir> …` rc=0 | 真实业务：VIP 摘要表生成链路（无需 EDL 设备） |
| 10 | `vip/DigestsToSign.bin` 非空 | 产物真的写出来了 |
| 11 | 它的 sha256 == 上游 `EXPECTED_DIGEST` | **本包产物必须能重现上游参考实现的结果** |

第 9–11 步复现了上游 `test_vip_generation.sh` 的同一命令行，固定装置也逐一对应：

- 4 个 XML 随包放在 `test_package/fixtures/`（**逐字节照搬上游
  `tests/data/*.xml`，含其固有的 CRLF**）；
- 9 个镜像用 `dd if=/dev/zero bs=1024 count=0 seek=N 2>/dev/null` 现场造出
  （名字与大小与上游 `generate_flat_build.sh` 完全一致），不往仓库里塞二进制。

为什么可以跨平台比对同一个常量：`vip.c` 写表时是
`fwrite(vip_gen->hash, SHA256_DIGEST_LENGTH, 1, vip_gen->digest_table_fd)`
—— 表是**纯 32 字节摘要的串接**，不含文件名、不含 XML 原文，所以它的 sha256
只取决于"被摘要的镜像集合与顺序"，与 XML 的行尾风格、绝对路径都无关。

---

## 7. 踩坑清单（速查）

| # | 坑 | 判据 / 症状 | 处置 |
|---|---|---|---|
| 1 | tool_requires 的 meson 是 shebang 包装脚本 | `/bin/sh: …/bin/meson: Permission denied` + `Error 126` | 去掉 shebang（§3.4） |
| 2 | 用 chmod 修上一条 | `chmod` rc=0 但 mode 不变（E046 静默失效） | 别用；只为日志留个 `os.chmod` 无害调用 |
| 3 | 版本退化成 `unknown-version` | `qdl --version` 打出 `unknown-version` | 写 meson `VERSION` 选项（§3.2） |
| 4 | meson 按裸名探测 `ar`/`ranlib` | configure 期 `Program 'ar' not found` | 清 env + `tc.binaries` 写绝对路径（§3.5） |
| 5 | CI export 的 `AR=llvm-ar` 被写进 native file | `Program 'llvm-ar' not found` | 同上，先 `os.environ.pop` |
| 6 | `uname -s` == `HarmonyOS` | 两条集成测试 `exit 1` | 补 `HarmonyOS*`（§4） |
| 7 | 纯工具包没给 `commands.json` | L0k：`package_type=application 但缺 commands.json` | 放**软件级** `archives/q/qdl/commands.json` |
| 8 | 误以为 `/tmp` 只读要打补丁 | `mkdtemp('/tmp/…')` 报 Read-only file system | 先查调用点：`test_make_temp_dir()` 是死代码，**不用补**（§3.6） |
| 9 | 复制 fixture 时做行尾归一 | 上游 XML 本身是 CRLF | 逐字节照搬（§1.5 / §6） |
| 10 | 本地 Windows 的 `core.autocrlf` 把补丁写成 CRLF | `patch` 报 `malformed patch` | 用 Python 显式按 LF 生成补丁，并本地 `patch -p1 --dry-run` 验证 |
| 11 | 认为 help2man 会带来"构建期运行未签名二进制"的风险 | 真机没有 help2man | 实测确认跳过，风险不存在（§3.6） |
| 12 | ★ 上游测试需要 `/usr/bin` 下的命令行工具（本例 `zip`） | `zip: command not found`（rc=127），但宿主 shell 里 `/usr/bin/zip` 明明可执行、PATH 里也有 `/usr/bin` | 是 **HMMAC 进程域**不是 PATH：从用户可写路径启动的程序域为 `adhoc_bin:s0`，**读不到 `/usr/bin`**（§4.2）。判据：`cat /proc/self/attr/current` + 绝对路径 stat 目标文件 + 比 `/proc/self/ns/mnt` 排除命名空间 |
| 13 | ★ meson `install` 后包内产物**无法 exec**（`Operation not permitted`，rc=126） | 构建树里能跑、装进包就跑不动；两份文件大小相同但 sha256 不同 | meson 把 `DT_RUNPATH` 整段改写成 `XXXX…`、`.dynamic` 少 16 字节 ⇒ ELF 不可加载（知识库 E077）。**不要在权限位上打转**（该 FS 上 `chmod` 是 no-op，E046）；处置：`package()` 末尾从构建树 `shutil.copy2` 装回（§10.2 的三行 `kept the linker output`） |

---

## 8. 本地验证记录

| # | 验证项 | 命令 | 结果 |
|---|---|---|---|
| 1 | 补丁可应用且结果确定 | `patch -p1 --dry-run < patches/0001-…patch` / `< 0002` | ✅ 两补丁均 check 通过；叠加应用后与手改副本 `diff -r` **逐字节一致**，`sh -n` / `bash -n` 通过 |
| 2 | 源码 tarball 三源一致 | 官方 / ghfast.top / gh-proxy.com 各下载一次 | ✅ sha256 三者相同（`0eee137b…1de9a`） |
| 3 | 静态门禁（离线模拟 CI） | `verify_archive.py … --version 2.7 --branch feat/qdl-2.7` | ✅ `ok=67 warn=3 fail=0`，见 §10.1 |
| 4 | 真机 `conan create` | 见 §10.2 | ✅ `RC=0`；上游 `Ok: 6 / Fail: 0`；消费者 `11 checks run, 0 failed` |
| 5 | 本地 CI 模拟（W3） | `CI_PACKAGES="archives/q/qdl/2.7" … zsh ci/conan/build_and_test.sh` | ✅ `G0/G0e/L0/L1/L2/L4/L5/KC/JC 全 pass`，`Pass rate: 100.0% (1/1)`，见 §10.6 |

---

## 9. 路径B（知识库扩展）候选素材

本 PR **不提交**这些草稿，仅登记素材来源：

1. **`uname -s` 返回 `HarmonyOS` 而非 `Linux`** —— 凡是"按 `uname -s` 判平台"
   的构建脚本/测试脚本（CMake 的 `CMAKE_SYSTEM_NAME`、autotools 的
   `config.guess`、shell 的 case 分支）在 OHOS 上都会走错分支。可复用判据：
   先 `uname -s` 实测，再决定是补分支还是设置 `CONFIG_SHELL`。
2. **沙箱内带 shebang 的脚本无法被 Python `execve`**（`Error 126` 的真根因）
   —— 与 E046（chmod 静默失效）互为补充：E046 说"改权限没用"，这条说
   "问题根本不在权限"。可写成"排查路径"型条目。
3. **tarball 构建导致 `git describe` 版本退化** —— 一切用 `git describe`
   / `git rev-parse` / `setuptools_scm` 推版本的项目，在 conan 的 source 缓存里
   都会退化。判据：产物 `--version` 打出 `unknown`/`0.0.0`/`dirty`。
4. **纯工具包在 conan 里应取 `package_type="application"`**，且 L0k 要求
   `commands.json` 放在**软件级**目录（`verify_archive.py` 查的是
   `version_dir` 或其父目录），而 `cpp_info` 只设 `bindirs`。
5. **`/tmp` 在 OHOS 上存在但只读** —— 需要 `mkdtemp`/临时文件的库要认 `TMPDIR`。
   有意思的是本包上游的 Windows 分支**已经**优先读 `TMPDIR`，POSIX 分支却硬编码
   `/tmp`；这种"平台分支不对称"是可复用的检查项。
6. **上游可选项缺失反而降低风险**：`help2man` 这类"构建期运行刚编出来的二进制"
   的可选步骤，在 OHOS 上缺失是好事（绕开"未签名二进制能否 exec"整条风险面）。
   判据：`find_program(..., required: false)` 的对象在真机上存不存在。
7. ★ **HMMAC 按进程域限制 `/usr/bin`：从用户可写目录启动的程序都会掉进
   `u:r:adhoc_bin:s0`，读不了 `/usr/bin`**（§4.2）。这是本包最值得沉淀的一条：
   - 症状极具误导性：`PATH` 里明明有 `/usr/bin`，`ls /usr/bin` 却在**同一个
     PATH** 下报 `Permission denied`，很容易误判成"没装 zip"或"PATH 组装错"；
   - 判别方法：`cat /proc/self/attr/current` 看域 + 比对
     `/proc/self/ns/mnt`（本例两边相同，排除命名空间）+ 用绝对路径 stat 目标
     （本例 `/usr/bin/zip` 存在且 755，排除权限位与缺文件）；
   - 触发条件：可执行文件位于 `/storage/Users/**` 等用户可写路径
     （python3、pip 装的脚本、make install 到 `~/.local/bin` 的工具都会中招）；
   - 影响面：**conan 自身就是这种进程** ⇒ `conan create` 的整棵子进程树都受限，
     凡是"上游测试调 `/usr/bin` 下的命令行工具"的包都会在 CI 上失败；
   - 通用对策：在配方里给上游测试提供不依赖 `/usr/bin` 的回退路径
     （本例 `zip` → `python3 -m zipfile`），或在 `/system/bin`、hnp 工具链里
     找同功能替代。

---

## 10. 真机验证原文

> 采集环境：鸿蒙 PC 真机 OpenHarmony 6.0 / aarch64 / clang 15.0.4 / libc++ / 原生构建，
> 仓库 `~/runner002/build_in_harmonyos`，`AGENT_NAME=runner002`。
> 本节全部为**逐字粘贴的原始输出**，未做美化。

### 10.1 离线静态门禁

```
$ python verify_archive.py archives/q/qdl --version 2.7 --branch feat/qdl-2.7
  ...
=== L0n 分支名 ===
  [ok]   L0n 分支 'feat/qdl-2.7' 去前缀后精确等于 'qdl-2.7'

=== PR 正文模板对齐（积分赛事PR模板） ===
  [ok]   2.7\reports\pr-body.md: 官方模板 7 个章节齐全
  [ok]   2.7\reports\pr-body.md: 头部 5 项信息齐全
  [ok]   2.7\reports\pr-body.md: 验证结果 3 项核心指标齐全
  [ok]   2.7\reports\pr-body.md: PR 标题 / commit message 均带关键词前缀

=== G0e 仓库根目录白名单（提醒） ===
  [warn] 未定位到仓库根目录（档案不在 build_in_harmonyos 仓库内？）—— 跳过 G0e 检查

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ok=72  warn=1  fail=0
  警告项:
    ! 未定位到仓库根目录（档案不在 build_in_harmonyos 仓库内？）—— 跳过 G0e 检查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 静态合规校验通过 —— 可以进入 conan create 阶段
```

唯一的 `warn` 是**结构性**的：本档案在交付目录里、不在仓库克隆内，`verify_archive.py`
定位不到仓库根 ⇒ 跳过 G0e；仓库内的真实 G0e 由 §10.6 的 CI 模拟覆盖
（`[ok] G0e: Root directory whitelist passed`）。

### 10.2 `conan create`

```
$ conan create archives/q/qdl/2.7 -pr:h=…/ci/conan/profiles/ohos-aarch64 -pr:b=<同>
…
qdl/2.7: Apply patch (portability): tests: accept HarmonyOS in the `uname -s` platform switch so the VIP/flashmap integration tests run on OpenHarmony PC
qdl/2.7: Apply patch (portability): tests: fall back to `python3 -m zipfile` when the Info-ZIP CLI is unreachable (wrong HMMAC domain cannot read /usr/bin on HarmonyOS PC)
…
qdl/2.7: Found pkg-config: YES (/data/service/hnp/bin/pkg-config) 0.29.2
qdl/2.7: Run-time dependency libusb-1.0 found: YES 1.0.27
qdl/2.7: Run-time dependency libxml-2.0 found: YES 2.15.3.1
qdl/2.7: Run-time dependency libzip found: YES 1.11.4
qdl/2.7: Program help2man found: NO
qdl/2.7: Run-time dependency cmocka found: YES 2.0.2
qdl/2.7: Program bash found: YES (/data/service/hnp/bin/bash)
qdl/2.7: Build targets in project: 13
…
qdl/2.7: meson launcher already shebang-free: …/p/mesonc731ddfc5b264/p/bin/meson
qdl/2.7: meson launcher usable via /bin/sh (shebang-free): …/p/mesonc731ddfc5b264/p/bin/meson -> 1.11.0
…
[53/53] Linking target test_contents_xml
…
qdl/2.7: Meson upstream test: meson test -v -C …/b/build-release
…
qdl/2.7: RUN: meson install -C "…/b/build-release" --destdir "…/p"
  Installing qdl to …/p/bin
  Installing qdl-ramdump to …/p/bin
  Installing qdl-ks to …/p/bin

qdl/2.7: kept the linker output for 'qdl' from …/b/build-release/qdl (works around the OHOS RPATH-rewrite EPERM)
qdl/2.7: kept the linker output for 'qdl-ramdump' from …/b/build-release/qdl-ramdump (works around the OHOS RPATH-rewrite EPERM)
qdl/2.7: kept the linker output for 'qdl-ks' from …/b/build-release/qdl-ks (works around the OHOS RPATH-rewrite EPERM)
qdl/2.7: package(): Packaged 4 files: qdl, qdl-ramdump, qdl-ks, LICENSE
qdl/2.7: Created package revision 0349f19189a483f3b971136316975155
qdl/2.7: Package '75a519b62684dd028a0a6400a7eefc8559d5105f' created
```

**`RC=0`**。日志中无 `error:` / `fatal error:` / `Error N while executing`。
三条 `kept the linker output for …` 就是绕开 RPATH 重写导致 ELF 不可执行的那一步
（§3.4 之后的第五个坑；判据与证据见 `reports/pr-body.md` 的「遇到的问题」第 4 条）。

### 10.3 上游 `meson test` 汇总

```
1/6 integration - qdl:VIP table generation      OK              1.07s
2/6 integration - qdl:Flashmap dry-run          OK              1.02s   2 subtests passed
3/6 unit - qdl:program_load_xml path resolution OK              0.07s   6 subtests passed
4/6 unit - qdl:pathbuf dirname behavior         OK              0.05s   7 subtests passed
5/6 unit - qdl:contents selector resolution     OK              0.04s   14 subtests passed
6/6 unit - qdl:contents XML parsing             OK              0.04s   8 subtests passed

Ok:                6
Fail:              0
```

- subtest 合计 **6+7+14+8 = 35**，与 §1.4 的口径一致（源码注册 37 处，`#ifdef _WIN32` 内 2 处不参与）；
- 集成测试的 TAP 子项（`flashmap.json` / `flashmap.zip` 两条）都跑到，第 2 个子项正是补丁 2 保住的
  「从 zip 归档刷机」能力；
- `1/6` 的收尾输出里能看到真实业务痕迹：`flashed "efi" successfully` / `26 patches applied` /
  `VIP tables are generated successfully and validated`。

### 10.4 消费者用例（test_package）原文

```
qdl/2.7 (test package): Running test()
qdl/2.7 (test package): RUN: /data/service/hnp/bin/bash test.sh
--- qdl 2.7 consumer verification ---
ok 1 - qdl --version -> qdl version 2.7
ok 2 - qdl --help rc=0
ok 3 - qdl --help lists --dry-run
ok 4 - qdl --help lists --create-digests
ok 5 - qdl --help lists --backend
ok 6 - qdl --help lists --serial
ok 7 - qdl-ramdump --help produced usage
ok 8 - qdl-ks --help produced usage
ok 9 - qdl --dry-run --create-digests rc=0
ok 10 - VIP table produced (1728 bytes)
ok 11 - VIP table digest equals upstream EXPECTED_DIGEST (3ca3c745c7bf60d9f51626ad819dce1e14788bc094c258da6656b0a469afbf15)
--- qdl consumer: 11 checks run, 0 failed ---
ALL CHECKS PASSED
```

第 11 项是本用例的核心：用固定装置跑出的 VIP 摘要表 sha256 与上游
`test_vip_generation.sh` 里的常量**逐字节相同** ⇒ 包内产物确实重现了上游参考实现的结果。

### 10.5 包产物与 ELF / 动态依赖

```
package_dir = /storage/Users/currentUser/.conan2/p/b/qdl5097f85c4c54c/p
  ./bin/qdl
  ./bin/qdl-ks
  ./bin/qdl-ramdump
  ./conaninfo.txt
  ./conanmanifest.txt
  ./licenses/LICENSE

--- qdl ---
  -rwxr-x--- 1 20001006 file_manager 149952 … /p/bin/qdl
  d9ccba3baaad6d12a490cac7068be07f3f7cea8bec8fe5d1b9c812dd81efb855  …/p/bin/qdl
  …/p/bin/qdl: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
   0x000000000000001d (RUNPATH)  Library runpath: […/p/libus04e54d4f229a5/p/lib:…/p/libxme5a5c01c709a6/p/lib:…/p/libzi7e1d99a45851d/p/lib]
   0x0000000000000001 (NEEDED)   Shared library: [libusb-1.0.so.0]
   0x0000000000000001 (NEEDED)   Shared library: [libxml2.so.16]
   0x0000000000000001 (NEEDED)   Shared library: [libzip.so.5]
   0x0000000000000001 (NEEDED)   Shared library: [libc.so]

--- qdl-ramdump ---
  63936 B  aee0367e51fdca75456c30acdf916d57c44bd45187cc3ab217eef75651c266c0
  ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
  RUNPATH 同上；NEEDED: libusb-1.0.so.0 / libxml2.so.16 / libzip.so.5 / libc.so

--- qdl-ks ---
  47552 B  07a531d37796611ac131c5158cee8d60542b02bc44dca118bdb7feef2b5ea26d
  ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
  RUNPATH 同上；NEEDED: libxml2.so.16 / libzip.so.5 / libc.so
```

`qdl-ks` 的 `NEEDED` 里没有 `libusb-1.0.so.0`（它不碰 USB），与三个目标各自的功能面吻合。

### 10.6 本地 CI 模拟结果

```
$ JUNK_PR_DIFF=…/qdl-pr.diff CI_PACKAGES=archives/q/qdl/2.7 CI_BRANCH=feat/qdl-2.7 \
    zsh ci/conan/build_and_test.sh          # ci_exit=0, 525 行日志
[ok] G0: Knowledge graph integrity check passed (542 entries)      G0_RESULT=pass
[ok] G0e: Root directory whitelist passed
[ok] dependency in registry: libusb/1.0.27 / libxml2/2.15.3.1 / libzip/1.11.4 / meson/1.11.0
[ok] version not in registry yet (first publish)
[ok] commands.json valid (type=tool)
[ok] L0m: directory structure valid
[ok] L0n: branch 'feat/qdl-2.7' matches 'qdl-2.7' exactly (prefix allowed)
[ok] L0: All quality gate checks passed                          L0_RESULT=pass
[OK] KC1..KC5 全部通过（.kv 542，index.tsv 一致 542 = 542）        KC_RESULT=pass
[OK] 未发现杂项文件（prdiff 模式 16 个文件；JC6 涉及软件数 1，合规）  JC_RESULT=pass
[ok] qdl/2.7 — conan create passed
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L1c: Upstream official tests (make check/ctest) executed in build phase
[ok] L1e: Negative test confirmed — test genuinely depends on qdl   ← [sabotage] bin/ moved away
[ok] L2: qdl --version OK / qdl-ks --version OK / qdl-ramdump --version OK
[ok] L4: patches clean
[ok] L5: bin/ has content
━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
```

- `L1e` 是**破坏性反向验证**（把 `bin/` 移走后重跑，测试必须失败）—— 它由 CI 自己执行并通过，
  证明消费者用例不是假运行；
- 日志中 6 行 `[fail] [Errno 2] No such file or directory: 'curl'` 来自 CI 的**可选**源码预下载
  步骤（失败会自行降级为 `will rely on conan's download`），不在 L0–L5 任何门禁内；
  本包源码最终由 conan 按 `conandata.yml` 的 URL 下载并通过 sha256 校验，不受影响；
- ⚠️ 该脚本是 `#!/usr/bin/zsh`（含 `${+VAR}` / `*.kv(N)` 等 zsh 语法），**必须用 `zsh` 跑**，
  用 bash 会直接 syntax error。

---

## 11. 知识库条目命中对照（路径A 硬性计分条件）

本次适配实际命中 **5 条**知识库条目；另有 1 处**全库无同形态条目**的缺口已登记为路径B素材（§9 第 7 条）。

| 条目 | 判据关键词 | 命中位置与处置 |
|---|---|---|
| **E009** `pipe-bypass` | `adhoc_bin.*hnp_file`、`domain transition`、`hishell_hap` | 两条集成测试在 `conan create` 子进程里报 `zip: command not found`（rc=127）而宿主 shell 里 `/usr/bin/zip` 可用。按 E009 的域转换模型（`hishell_hap:s0` 执行用户二进制 → 域转 `adhoc_bin:s0`）实测 `/proc/self/attr/current`，确认 conan 自身就在 `/storage/Users/currentUser/` 下 ⇒ 整棵子进程树被锁在 `adhoc_bin`，读不到 `/usr/bin`。**最快把排查从"PATH / 权限位"拨到"进程域"的一条**（§4.2 的定位依据） |
| **E077** `post-install-script` | `operation not permitted`、`RPATH`、`RUNPATH`、`permission denied.*ELF` | 消费者用例 10/10 失败（`Error 1 while executing` / rc=126）的真根因：meson `install` 改写 `DT_RUNPATH` ⇒ ELF 不再可加载。处置取**等价替代**（不回写、不重签名，直接把构建树产物按字节装回），比 E077 的四步「去签名→改 ELF→重签名」更省且更安全 |
| **E160** `config-guess-harmonyos-patch` | `uname -s = HarmonyOS` | 补丁 1 的判据来源。形态从 autotools `config.guess` 迁移到上游 shell 测试脚本的 `case "$(uname -s)"`，处置同构（补 `HarmonyOS*` 分支） |
| **E046** `skip-test` | `chmod.*not effective`、`mode unchanged` | 用于**快速排除错误假设**：`Error 126` 的第一直觉是 x 位，而 `chmod` 返回 0 但 mode 不变（750/755/770/777 全 rc=126）与 E046 逐字对应 ⇒ 立刻转向二进制内容比对 |
| **E232** `native-ohos-shell-prefix` | `ConanException: Error 126 while executing`、`Permission denied` | 同症状不同触发点：本次是 `tool_requires` 包里带 shebang 的 `bin/meson` 包装脚本被 Python `subprocess` execve 拒绝（§3.4）。E232 给的是"用原生 shell 包一层"，本包取等价且更彻底的"去 shebang + shell 兜底自检" |
| 附带参考 **E212** | hmmac 按**路径**分配安全标签（`/data/service/hnp/**` → `hnp_file`，`/storage/Users/**` → `hmdfs`） | 用于理解"为何恰好是用户可写路径下的进程被降权"，与 E009 互为印证 |

**未命中说明**：以 `HMMAC`/`adhoc_bin` + `/usr/bin` 可读性、`meson install` + `RPATH` 重写为关键字
检索全库（`doc/` 541 条 + `drafts/`），**没有"域限制只读目录"这一形态的条目**——最接近的 E009 讲的是
执行侧，且其给的 `cmd | cat` 管道绕过技巧对"读目录被拒"无效。该缺口即 §9 第 7 条。
