# musicpc 0.35 适配笔记（HarmonyOS PC / WSL 交叉）

## 编译环境
- 构建系统: meson（上游 meson.build，project('mpc','c', version 0.35, c_std=c99)）
- 语言: C
- 编译器: clang（取自 profile 的 tools.build:compiler_executables，R33）
- 构建机: WSL x86_64，交叉 profile ohos-aarch64-wsl（os=OHOS arch=armv8）
- 状态: built（conan create rc=0，**上游测试用例 1/1 PASS —— 鸿蒙 PC worker 与 WSL 交叉机均实测通过**，test_package 4/4 PASS）

## 编译步骤
1. `get()` 解包官方发布件（strip_root=True，顶层目录 mpc-0.35）；
2. `PkgConfigDeps` 生成 libmpdclient.pc，meson 的
   `dependency('libmpdclient', version: '>= 2.18', fallback: [...])` 经
   pkg-config 解析到 conan 的 libmpdclient/2.23；`wrap_mode=nodownload`
   确保不回退包内 subprojects/ wrap 文件（上游自带 libmpdclient.wrap）；
3. `meson compile`（-j1）；`-Dtest=true` 时同时构建上游测试目标 test_format；
4. `package()` 走 `meson install()`，bin/mpc + share/doc/mpc 就位。

## 依赖（W0）
- libmpdclient/2.23：`conan list "libmpdclient/*" -r=ohpcd` → 唯一版本 2.23，
  与任务池声明一致。注意：`conan search` 对 ohpcd 远端会误报
  "Recipe not found"（本机实测），`conan list` 为准。
- check/0.15.2：**仅测试期依赖**（`build_requirements()` 里的 `self.test_requires`），
  用于链接上游唯一的测试目标；消费者图里不会出现，也不参与 package_id。
  ohpcd 已发布 settings 与 `ci/conan/profiles/ohos-aarch64` 完全一致的
  OHOS/armv8/clang-15/Release/fPIC=True/shared=False 二进制，
  CI 直接取制品（CI 用 `--build="musicpc/*"`，本来也不会重建它）。

## 上游测试用例（rule4）

### 上游 N=1 到底是哪一个
上游用 meson 的 `test()` 注册的测试目标**只有 1 个**，在 `test/meson.build`：

```meson
test('test_format', executable('test_format',
  'test_format.c', '../src/format.c', '../src/song_format.c',
  '../src/audio_format.c', iconv_sources,
  include_directories: inc,
  dependencies: [libmpdclient_dep, check_dep]))
```

由 `meson_options.txt` 的 `option('test', type: 'boolean', value: false)` 启用，
依赖 libcheck（`check_dep = dependency('check')`，见根 `meson.build` 第 136-139 行）。
`test/test_format.c` 内含 6 个 `START_TEST`（test_empty / test_basic / test_group /
test_fallback / test_default / test_escape），全部断言 `format_song()` 的格式化输出；
歌单对象由 libmpdclient 的 `mpd_song_begin` / `mpd_song_feed` 在**进程内**构造。
**因此该用例完全不需要 MPD 服务器、不需要网络、不需要音频设备** —— 纯字符串
格式化逻辑，这是它能在这里被真实执行的前提（不是"平台限制"的托词）。

### 本配方怎么让它真跑
`build()` 末尾调用 `_run_upstream_tests()`：`meson compile` 时 `-Dtest=true`
已把 `test/test_format` 编出来，随后直接交给上游自己的测试驱动执行：

```
meson test -C "<build>" -v --print-errorlogs [--wrapper "qemu-aarch64 -L ... -E LD_PRELOAD=..."]
```

用 `meson test` 而不是手写 exec，是为了让**上游的测试定义本身**驱动这次运行，
并让日志里带上 meson 自己的统计（`Ok: 1` / `Fail: 0`）。

执行模型按**被测 ELF 的 ELF 头**判定（不看 conan 的 `cross_building()`：OHOS
profile 对 -pr:h/-pr:b 传同一个文件，conan 会认定 host == build，而 ELF 其实是 aarch64）：

| 执行机 | ELF 架构 | 执行方式 |
|---|---|---|
| CI 鸿蒙 PC worker（aarch64） | aarch64 | 原生，meson 直接 exec，`--wrapper` 不加 |
| WSL x86_64 交叉机 | aarch64 | `--wrapper "qemu-aarch64 -L /opt/ohos-guest -E LD_PRELOAD=/opt/ohos-guest/lib/libfdchkshim.so"` |

qemu 那条与 test_package 同模型（先例 tasksh 1.2.0、array-hash 0.7.2）：libmpdclient
是**动态**库（ohpcd 的 libmpdclient/2.23 为 shared=True），其 OHOS 构建调用
`__fd_chk()`，模拟 guest libc 不实现该符号，故在 guest 侧预载 shim。
另：worker 的 HMDFS 会拒执行**未签名** ELF（`bin/mpc` 在 CI #93705 就是这么挂的，
退出码 126），所以测试二进制在运行前也走一遍同样的自签名；交叉机上没有
binary-sign-tool，只告警跳过。

**上游测试源文件未做任何修改**（`test/test_format.c` 与上游 tarball 逐字节一致，
`patches: []`），本配方只是在它外面加了交叉执行包装与签名。

### 实测证据（WSL 交叉机，本 PR 提交内容）
```
$ conan create archives/m/musicpc/0.35 -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
...
[33/33] Linking target test/test_format
musicpc/0.35: upstream test executed through: /usr/bin/qemu-aarch64 -L /opt/ohos-guest -E LD_PRELOAD=/opt/ohos-guest/lib/libfdchkshim.so
musicpc/0.35: RUN: meson test -C "..." -v --print-errorlogs --wrapper "..."
1/1 mpc:test_format RUNNING
>>> ... /usr/bin/qemu-aarch64 -L /opt/ohos-guest -E LD_PRELOAD=... /root/.conan2/p/b/.../build/test/test_format
――――――――――――――――――――――
Running suite(s): format
100%: Checks: 6, Failures: 0, Errors: 0
――――――――――――――――――――――
1/1 mpc:test_format OK              0.10s

Ok:                1
Fail:              0
musicpc/0.35: upstream test suite passed: mpc:test_format 1/1
...
RC=0
```

**上游测试用例通过率：1/1（100%）**（1 个上游测试目标；其内部 libcheck 断言 6/6 全过）。

### 反空壳反证（negative control）
为证明这 1/1 不是"必然通过"的空壳，把上游 `test/test_format.c` 里
`assert_format(song, "%artist%", default_artist)` 的期望值临时改成 `"MUTANT"`
（**只在 conan 缓存构建目录里改，仓库与上游源文件保持原样，改完即还原、缓存目录已删除**）：

```
83%: Checks: 6, Failures: 1, Errors: 0
../test/test_format.c:60:F:Core:test_basic:0: Assertion 'p == expected' failed: p == "Foo", expected == "MUTANT"
1/1 mpc:test_format FAIL            0.10s   exit status 1

Ok:                0
Fail:              1
AFTER_RC=1
```

即断言真实生效、失败会被 meson 记为 FAIL 且退出码非 0，配方层面
`self.run(..., ignore_errors=True)` 拿到非 0 会 raise
`ConanException("upstream test suite failed ...")`，构建随之失败。

### worker 上的 libcheck 临时文件问题（CI #94829，已修）

第一轮 CI（build **#94829**，worker CI-023）编译、链接、签名全部成功，`meson test` 也真的
执行了测试二进制，但 **libcheck 连一条断言都没跑到就退出 2**：

```
1/1 mpc:test_format RUNNING
>>> ... /storage/.../build/test/test_format
/storage/Users/currentUser/.conan2/p/b/check01f6875eb3aa2/b/src/check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so
1/1 mpc:test_format FAIL            0.05s   exit status 2
Ok: 0   Fail: 1
```

**根因**：libcheck 用 fork 跑用例，父进程与子进程之间靠一个临时文件回传结果
（`src/check_msg.c` 的 `open_tmp_file()`）。它选目录的顺序是
**`TEMP` → `P_tmpdir` → `TMPDIR` → `"."`**（该分支为 `#if HAVE_MKSTEMP`，非 Windows 走这条），
而 `P_tmpdir` 是**编译期宏**，glibc/musl 都把它定义成 `"/tmp"`，**优先级高于 `TMPDIR`** ——
所以只设 `TMPDIR` 根本不会被读到。OHOS worker 的 `/tmp` 是只读的（本仓自己就写明了：
`ci/conan/build_and_test.sh` 里「OHOS /tmp is read-only, use build directory instead」），
`mkstemp("/tmp/check_XXXXXX")` 失败 → 报上面这句 → 退出码 2。

**修法**：给 `meson test` 传一个本构建自己拥有的可写目录作为 `TEMP`（优先级最高，同时把
`TMPDIR` 一并指向它），即

```
TEMP="<build>/upstream-test-tmp" TMPDIR="<build>/upstream-test-tmp" meson test -C <build> -v --print-errorlogs
```

**本机逐字节复现 + 修复验证**（同一个已构建好的 aarch64 测试二进制，qemu 执行）：

| 场景 | 输出 | 退出码 |
|---|---|---|
| A 环境默认（本机 `/tmp` 可写，走 `P_tmpdir`） | `100%: Checks: 6, Failures: 0, Errors: 0` | 0 |
| B `TEMP` 指向不存在的目录（模拟 worker 只读 `/tmp`） | `check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so` | **2**（与 CI #94829 完全一致） |
| C `TEMP` 指向构建自有目录（本次修复） | `100%: Checks: 6, Failures: 0, Errors: 0` | 0 |

场景 B 复现出的报错文本与退出码与 CI 日志逐字节一致，可确认根因判断成立；场景 C 即本次修复。

### worker 实测：上游用例在鸿蒙 PC worker 上真的通过（CI #94968 / CI-028）

修掉上面的临时目录问题后，第二轮 CI（build **#94968**，worker CI-028）里上游用例**在鸿蒙 PC
worker 上原生执行并通过**：

```
musicpc/0.35: RUN: TEMP="/storage/.../musicdbcab9c1a92d5/b/build/upstream-test-tmp" TMPDIR="..." \
    meson test -C "/storage/.../b/build" -v --print-errorlogs
1/1 mpc:test_format RUNNING
100%: Checks: 6, Failures: 0, Errors: 0
1/1 mpc:test_format OK              0.08s
Ok:                1
musicpc/0.35: upstream test suite passed: mpc:test_format 1/1
```

即 **上游测试用例通过率 1/1（100%）**，且是在真实鸿蒙 PC worker 上跑出来的（不再是只有交叉机
qemu 的旁证）。该轮 build 最终仍红，但**红的不是测试**，而是紧接着 `package()` 里的
`meson install` 触发的多余重链接死在 worker 进程预算上 —— 见问题 10，已修。

## 适配后消费者断言（新增，4 条）

`test_package/test.sh` 的 4 条断言，每条真实执行已安装的 mpc 二进制
（stdout/stderr + 退出码双重判定），且均无需 MPD 服务器：

| # | 断言 | 判据 |
|---|------|------|
| 1 | `mpc nosuchcommand` | exit=1，stderr 含 `unknown command "nosuchcommand"` 与 `mpc version: 0.35`（VERSION 宏编入，src/main.c print_help/print_usage） |
| 2 | `mpc help` | exit=0，stdout 含 `Usage: mpc [options] <command>` 与 `Display status`（命令表渲染） |
| 3 | `mpc status` | exit=1，stderr 含 `MPD error: Connection refused`（src/util.c printErrorAndExit，证明走到 libmpdclient 连接层） |
| 4 | `mpc -h 127.0.0.1 -p 6600 status` | exit=1，`MPD error: Connection refused`（-h/-p 全局选项被解析并传给 libmpdclient；mpc 选项风格特殊：-h=host、-p=port、-P=password，见 src/options.c） |

构建机无 MPD server 是事实前提：连接路径的预期终态就是 libmpdclient 层的
干净连接失败，scrobble 之外的协议行为未验证（与 mpdas 第 5 条断言同口径）。

## 问题与处置
| # | 问题 | 处置 |
|---|------|------|
| 1 | 上游 meson 自带 subprojects/libmpdclient wrap 文件（缺依赖时会尝试拉取子工程） | `wrap_mode=nodownload` 禁回退，依赖一律走 conan 依赖图 |
| 2 | manpage 依赖 sphinx（documentation 选项 auto） | `documentation=disabled`；manpage 不打包，命令用法以 `mpc help` 为准 |
| 3 | 上游单测依赖 `check` 库，而任务池声明的依赖只有 libmpdclient/2.23 一项 | 用 `self.test_requires("check/0.15.2")` 声明**仅测试期**依赖：只在 `conan create`/`conan test` 展开，消费者图不受影响、不参与 package_id；ohpcd 已有匹配 profile 的 OHOS/armv8 二进制，CI 不触发源码重建 |
| 4 | 仓内 conan 2.29.1 的 Meson helper 无 `compile()` 方法（模板写法 `meson.compile()` 直接 AttributeError） | 用 `meson.build()`（与仓内 json-glib 配方一致） |
| 5 | WSL 交叉机执行 aarch64 测试件：guest libc 缺 glibc fortify 符号 `__fd_chk`，ohpcd 的 libmpdclient.so.2 重定位失败（`Error relocating ... __fd_chk: symbol not found`） | 按 ELF 头判定 native/emulated（同 tasksh 1.2.0 先例）：emulated 模型走 `qemu-aarch64 -L /opt/ohos-guest -E LD_PRELOAD=/opt/ohos-guest/lib/libfdchkshim.so`，shim 只在 guest 环境提供 `__fd_chk`（passthrough 语义，与 glibc 实现对有效 fd 行为等价）；CI 真机 native 模型不触发该路径。test_package 4/4 断言与上游 test_format 1/1 均在此模型下实测通过 |
| 6 | CI `meson setup` 报 `ERROR: Unknown linker(s): [['llvm-ar']]`（#92723 CI-026 / #93102 CI-014 / #93136 CI-028） | worker profile 的 `[buildenv]` 提供**裸名** `AR=llvm-ar`，conan 把它原样写进 `conan_meson_native.ini` 的 `[binaries] ar`；meson 探测归档器的子进程不按 PATH 解析裸名（本机实测 ENOENT）→ 探测失败；改 PATH 无效。修复：`generate()` 的 `_pin_meson_archiver()` 把**绝对路径**归档器写进 `tc.binaries["ar"]`（conf `ar` → `which llvm-ar` → C 编译器同目录 → `/data/service/hnp/bin/llvm-ar` → `which ar`） |
| 7 | CI #93152（CI-010）`ConanException: Error -11 while executing`，且 meson **一行输出都没有** | 修复尝试中的 `Environment().vars(self).save_script("conanbuild")` 占用了 conan 保留的聚合脚本名：`EnvVars.save_script` 会把该文件注册进 `env_scripts["build"]`，`generate_aggregated_env()` 随后写出的 `conanbuild.sh` 变成 `. "<dir>/conanbuild.sh" && . "<dir>/conanbuildenv-*.sh"` —— **脚本 source 自身 → shell 无限递归 → SIGSEGV**；conan `run()` 默认 `env="conanbuild"`，先 source 该脚本再执行 meson，故 meson 从未启动（无 banner、无报错）。本地逐字节复现：直接 `. conanbuild.sh` 用 `/bin/sh`、`bash` 均 exit 139 |
| 8 | 真机/HMDFS 拒绝执行未签名 ELF（CI #93705：`exec <pkg>/bin/mpc: Operation not permitted`，退出码 126） | `package()` 里 `_sign_ohos_binary()`（先例 archives/t/termdebug/2.2）：llvm-objcopy 去旧 `.codesign` 段 + `binary-sign-tool -selfSign 1`；构建目录里的上游测试二进制运行前同样处理 |
| 9 | worker 上 libcheck 起不来：`check_msg.c:317: Unable to create temporary file for communication`，`1/1 mpc:test_format FAIL ... exit status 2`（CI #94829 / CI-023） | libcheck 的临时目录顺序是 `TEMP` → **`P_tmpdir`（编译期宏，glibc/musl 均为 `"/tmp"`）** → `TMPDIR` → `"."`，`P_tmpdir` 压过 `TMPDIR`，而 worker 的 `/tmp` 只读。修法：`meson test` 前缀 `TEMP=<build>/upstream-test-tmp TMPDIR=<同一个目录>`。本机已逐字节复现（`TEMP` 指向不存在目录即复现同样报错与退出码 2）并验证修复 |
| 10 | `package()` 的 `meson install` 重新进 ninja 重链接两个二进制，死在 worker 进程预算上：`clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable`、`FAILED: [code=1] mpc` / `[code=1] test/test_format`、`ConanException: Error 255`（CI #94968 / CI-028） | 前一步 `meson compile -j1` 明明报了 `ninja: no work to do`，install 却又认为输出过期（构建目录是 FUSE/HMDFS 挂载，时间戳会让 ninja 反复把输出判脏）→ 多余的两次链接撞上 worker 进程枯竭（与 #93538/#93684 同因）。修法：`meson.install(cli_args=["--no-rebuild"])` —— build() 已经编译完毕，安装阶段不再重复构建。本机强制重建验证：`bin/mpc` 等照常打包、消费者 4/4、上游 1/1、rc=0 |

## CI 归档器（llvm-ar）失败链与修复（2026-10-15 补充）

CI worker 上 `meson setup` 的归档器探测是本题真正的拦路虎，完整链条（均有日志/本地复现证据）：

1. **裸名 AR 进 native file**：worker profile 的 `[buildenv]` 带 `AR=llvm-ar`，conan 的
   `MesonToolchain` 经 `build_env.get("AR")` 把它原样写成 `[binaries] ar = 'llvm-ar'`
   （本地把 `AR=llvm-ar` 加进 profile 后，生成的 native file 与此逐字节一致）。
2. **裸名探测失败**：meson 先 `env.lookup_binary_entry('ar')` → 命中该裸名 → `trials = [['llvm-ar']]`
   → 子进程 spawn 报 `[Errno 2] No such file or directory: 'llvm-ar'`（探测子进程不按 PATH 解析
   裸名；仓内 mobile-broadband-provider-info/20240407、mpd/0.24.12 已记录同现象）→
   `ERROR: Unknown linker(s): [['llvm-ar']]` + `Error 1`。**因此把目录塞进 PATH 无效**——
   分支上两次 PATH 尝试（4876e6733、55991173f）报错与此完全一致。
3. **正确修法**：把绝对路径归档器钉进 native file（`tc.binaries["ar"]`），绕开裸名解析。
   先例：coeurl 0.3.2、qbootctl 0.2.2、mesa、babl-tools、wtmpdb、turnstile、c-stdaux、
   hexagonrpcd、json-glib（其中 coeurl 与本包同为 meson + `AR` 裸名场景）。

本地验证（本机 `/data/service/hnp/bin/` 已有 hnp 布局 mock，与本仓 worker 同构）：

| 场景 | meson | profile | 修前 | 修后 |
|---|---|---|---|---|
| A worker 仿真 | 1.11.1 | `ohos-aarch64-wsl-emular`（`[buildenv] AR=llvm-ar`，c=`/opt/lpk-fixed/clang`） | `Unknown linker(s): [['llvm-ar']]` + `Error 1`（与 CI #92723 逐字节一致） | `rc=0`，`test_package 4/4 PASS`，`[binaries] ar = '/data/service/hnp/bin/llvm-ar'` |
| B 本机默认 | 1.12.1 | `ohos-aarch64-wsl` | —（本机无裸名 AR，meson 自行回退 `ar`） | `rc=0`，`4/4 PASS` |
| C CI 同构 | 1.11.1 | `ohos-aarch64-wsl-ciLike`（c=`/data/service/hnp/bin/clang`） | — | `rc=0`，`4/4 PASS`，`ar` 由 C 编译器同目录推导 |

> meson 1.11.1（worker）与 1.12.1（本机）的 `detect_static_linker` 逻辑**相同**
> （clang 的 trials = `llvm-ar-15` / `llvm-ar` / `ar` / `gar`），差异不在 meson 版本，
> 而在 native file 里是否给了裸名 `ar`；给出裸名时 trials 退化成单元素 `[['llvm-ar']]`，
> 与 CI 日志中「只列一个 linker」的现象吻合。
>
> 分支上三次 hack 提交（`4876e6733` PATH 注入 / `55991173f` 改从编译器推导 / `d98e54fb93`
> `save_script("conanbuild")`）应整体丢弃：前两次无效，第三次引入问题 7 的 SIGSEGV。
>
> 第三处已知同类（conan 保留名 `conanbuild`）：qqwing 1.3.4 递归 source → `printenv` E2BIG；
> mydumper 覆盖聚合环境 → `self.run` SIGSEGV（见
> `knowledge/drafts/DRAFT-qqwing-1.3.4-*.md` 查重结论）。

## 依赖版本
| 依赖 | 引用 | 用途 |
|---|---|---|
| libmpdclient | `libmpdclient/2.23`（plain，ohpcd 已发布） | MPD 协议客户端（运行期） |
| check | `check/0.15.2`（`test_requires`，仅测试期） | 链接上游唯一的测试目标 test_format |

**编译结束**: 2026-10-15（上游测试用例接入：2026-10-16）
**最终状态**: built
