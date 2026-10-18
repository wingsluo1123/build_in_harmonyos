# slcfitsio 0.4.7-pre.19 适配笔记（HarmonyOS PC / aarch64 / OHOS）

## 1. 上游与源码

- 上游：S-Lang 的 CFITSIO 模块（作者 John E. Davis），手册页
  <https://space.mit.edu/cxc/software/slang/modules/cfitsio/>
- 官方归档：<https://www.jedsoft.org/snapshots/slcfitsio-pre0.4.7-19.tar.gz>
  - 2026-10-14 实测 `curl -w '%{http_code}'` → **HTTP 200**，177895 字节
  - `sha256 = 913cf288070c36629bdae9d9695d6f2ced6af488c669b8bcb5316a2de8d7ea2c`
  - Debian 的 `slcfitsio_0.4.7~pre.19.orig.tar.gz` 与该文件 **逐字节相同**
    （`cmp` 无差异，sha256 一致）——即再分发镜像没有换包
- 版本号：上游 tarball 名 `slcfitsio-pre0.4.7-19.tar.gz`，`src/version.h`
  中 `MODULE_VERSION_STRING "pre0.4.7-19"`；Debian/Ubuntu 记作
  `0.4.7~pre.19`，本仓平台版本即 `0.4.7-pre.19`
  （Debian `watch` 的 `uversionmangle=s/-/~pre./` 反推得到）

## 2. 这个包是什么

slcfitsio 是 **S-Lang 语言的 CFITSIO 绑定**：把 FITS 读写库包装成 S-Lang
模块，供 slsh / jed 等解释器直接读写 FITS 文件。上游产物是一个可加载模块
`cfitsio-module.so` + 三个 `.sl` 封装脚本 + 一个帮助文件，Debian 包名
`slang-cfitsio`。

因此它 **不是可链接库**：libslang 通过 `SLANG_MODULE_PATH` 把
`import ("cfitsio")` 解析成 `<name>-module.so`（`strings libslang.so.2.3.3`
可见模板 `%s-module.%s` 与默认目录 `//lib/slang/v2/modules`）。包类型取
`shared-library`，`package_info().libs` 留空。

## 3. 构建矩阵

| 项 | 值 |
|---|---|
| 构建系统 | autotools（tarball 自带 autoconf 2.69 预生成 `configure`，无需 autoreconf） |
| host settings | `os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libc++ cppstd=17 build_type=Release` |
| 依赖 | `cfitsio/4.6.4`（静态 `libcfitsio.a`）、`slang/2.3.3`（`libslang.so.2` + `slsh`）、`zlib/1.3.1.1`（经 cfitsio 传递，静态 `libz.a`） |
| 工具链 | OHOS clang（`/opt/lpk-fixed/clang`，`--target=aarch64-linux-ohos`） |
| 产物 | `lib/slang/v2/modules/cfitsio-module.so`(+`.so.0.4.7`)、`share/slsh/local-packages/{cfitsio,fits,fitswcs}.sl`、`.../help/cfitsio.hlp` |

依赖按 W0/R36 预检（`conan download <pkg> -r=ohpcd --only-recipe` 全部成功）：

```
cfitsio/4.6.4    revisions bdb328c067160a83fd5ee435b8642e47
slang/2.3.3      revisions 0b6e1ab3550d45f4bd9d9ab46685a0f6
zlib/1.3.1.1     revisions 9a23e7d51311d0440b6e4d36cf44e4d9
```

三个依赖都有预编译包（`conan install --build=missing` 未触发源码重编）。

## 4. 适配点（逐条对应 conanfile.py 里的说明）

### 4.1 显式 GNU triplet（不 patch config.sub）

tarball 自带的 `config.sub`/`config.guess` 是 2007 年版，**不认 `ohos`**：

```
$ autoconf/config.sub aarch64-linux-ohos
Invalid configuration `aarch64-linux-ohos': system `ohos' not recognized
```

本仓既有两条路线：整文件替换 config.sub（spectools/judy 等），或显式传
`--build=/--host=`（jlog 2.6.0 注释明确写了同款场景）。这里走后者：

```
--build=x86_64-linux-gnu --host=aarch64-unknown-linux-gnu
```

效果：

- `config.sub` 接受该 triplet（会归一化成 `aarch64-unknown-linux-gnu`）；
- `JD_ELF_COMPILER` 的 `case "$host_os"` 命中 `*linux*` 分支 →
  `CC_SHARED = $(CC) -shared -fPIC ...`，正是本项目需要的；
- `JD_CHECK_FOR_LIBRARY` 的扩展名列表命中 `*` 分支（`so a`）；
- build ≠ host → autoconf 判定交叉编译，`AC_CHECK_SIZEOF` 用编译期方法
  求值而**不运行**目标程序（实测 short=2 int=4 long=8 float=4 double=8）。

### 4.2 关键卡点：`cfitsio-version.h` 需要「运行」目标程序

`src/Makefile.in` 里：

```make
cfitsio-version.h: cfitsio-version.c
	$(CC) ... cfitsio-version.c -o cfitsio-version $(LIBS)
	./cfitsio-version > cfitsio-version.h
```

即上游先编译一个 helper 再**执行**它，输出
`#define COMPILED_CFITSIO_VERSION <fits_get_version()>`。
第一次交叉编译就死在这里（r2 日志）：

```
Error relocating .../libslang.so.2: __fd_chk: symbol not found
make[1]: *** [Makefile:72: cfitsio-version.h] Error 127
```

helper 只调用 `fits_get_version()`，但上游的链接行把整个 `$(LIBS)`（含
`-lslang`）都给了它。**解法：这一条单独用 `SLANG_LIB=` 链接（slang-free）**，
helper 的运行期依赖只剩 libc.so，交叉编译产物即可执行：

```make
make -C src SHELL=/bin/sh SLANG_LIB= OTHER_LIBS='-L<zlib>/lib -lz' cfitsio-version.h
```

实测输出真实值（不是伪造/写死）：

```
#define COMPILED_CFITSIO_VERSION 4.060400
```

> 本机 `limits`：WSL 侧的 aarch64 OHOS 模拟根 `opt/ohos-guest` 里 libslang.so.2
> 因缺 `__fd_chk` 无法装载（该符号是真实 OHOS libc 的 fortify 族，stock musl
> 没有），所以 **运行期**功能测试只能在 OHOS worker 上做（见第 6 节）。

### 4.3 剥离构建机 RPATH

`JD_SET_RPATH` 会把依赖目录写进链接行，生成的 `src/Makefile` 里是：

```
RPATH = -Wl,-R/root/.conan2/p/slang6ddf1701bd8b9/p/lib:/root/.conan2/p/cfits5973b7c2f5a64/p/lib
```

构建机 conan 缓存路径不能进制品，故模块链接时用 `RPATH=`（make 命令行变量
覆盖）清空。运行期 `libslang.so.2` 由消费者运行环境（conanrun /
`LD_LIBRARY_PATH`）提供，和其它 slang 消费者一致。校验：

```
readelf -d cfitsio-module.so | grep -E 'NEEDED|RPATH|RUNPATH'
  (NEEDED)  Shared library: [libslang.so.2]
  (NEEDED)  Shared library: [libc.so]
```

### 4.4 zlib 走 OTHER_LIBS 且静态链接

`libcfitsio.a` 引用 zlib 的 `inflate/deflate`（`nm -u libcfitsio.a` 实测），
而上游 Makefile 没有 zlib 的位置——但它有 `OTHER_LIBS` 扩展点：

```
OTHER_LIBS='-L<zlib package>/lib -lz'
```

ohpcd 的 zlib 包**只有 `libz.a`**（无 libz.so），把 `-L` 指向它就静态链入，
模块最终只有 `libslang.so.2` 一个非 libc 运行期依赖。

> 反例留档：若只写 `-lz` 不给 `-L`，clang 会拿到 OHOS sysroot 的 `libz.so`，
> 模块就多一个运行时依赖（r1 日志里可见 `NEEDED libz.so`）。

### 4.5 SHELL/CONFIG_SHELL 固定 /bin/sh

沿用 jlog / spectools 的 HMFS-HMDFS `shell_getcwd` 加固：configure 用
`exec sh ./configure` 驱动，`SHELL`/`CONFIG_SHELL` 置 `/bin/sh`，make 也带
`SHELL=/bin/sh`（生成的 Makefile 自己的 `mkversion.sh` 会走 `$(SHELL)`）。

## 5. 本地交叉编译结果

```
$ conan create . -pr:h=ohos-aarch64-wsl-xbuild -pr:b=default --build=missing
slcfitsio/0.4.7-pre.19: Package '5bdd7dabf3dae65d28824ddf130908680168ac52' created
Full package reference: slcfitsio/0.4.7-pre.19#471adc272c64005a6dd9a1f1650f5f2e:5bdd7dabf3dae65d28824ddf130908680168ac52
```

包内容：

```
lib/slang/v2/modules/cfitsio-module.so -> cfitsio-module.so.0.4.7
lib/slang/v2/modules/cfitsio-module.so.0.4.7    1379032 B
share/slsh/local-packages/{cfitsio.sl,fits.sl,fitswcs.sl}
share/slsh/local-packages/help/cfitsio.hlp
licenses/COPYRIGHT
```

模块属性：

```
ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked
Type: DYN (Shared object file)  Machine: AArch64
NEEDED: libslang.so.2, libc.so   （无 RPATH/RUNPATH）
导出入口: init_cfitsio_module_ns
```

`init_cfitsio_module_ns` 与 libslang 2.3.3 内期望的模板 `init_%s_module_ns`
一致 → 模块入口点匹配。

**可复现性**：另在 WSL 原生盘 `/root/ohpcd-work/build/slcfitsio-0.4.7-pre.19`
用同一套命令 in-place 重编（`conan install -of` + configure/make），产出的
`src/cfitsio-module.so` 与包内模块 **sha256 完全相同**：

```
6293627d80f72fc6cf2d68cf803f298470a3b735be3169cda0256137be090a93
```

## 6. 测试：上游 2 个用例，均已真实执行

上游只有一套回归测试。`src/Makefile` 的 `test:` 目标是：

```make
test:
	@for X in tests/test_*.sl; do slsh $$X; done
```

即 `src/tests/test_fits.sl`（图像 + 二进制表写读回环）与
`src/tests/test_wcs.sl`（fitswcs bin/rebin 的 CRPIX/CDELT 断言），共 **2 个**。
注意该目标**不检查执行结果**：脚本结尾只 `message("Passed"/"Failed")`、退出码
恒为 0，所以只看 `make test` 的退出码发现不了失败（本仓库的驱动层补上了这一层）。

`test_package/` 侧：

- `run_test.sh`：消费者驱动。先断言包内
  `lib/slang/v2/modules/cfitsio-module.so` 与
  `share/slsh/local-packages/{fits,fitswcs}.sl` 存在（缺任一即 FAIL），再用真实
  `slsh` 依次执行**两个**上游脚本的包内适配版，逐条打印
  `UPSTREAM_CASE PASS|FAIL <file> (rc=N)`，末尾打印 `UPSTREAM_SUMMARY <n>/2`；
  任一非零退出即整体失败。
- `test_fits.sl` / `test_wcs.sl`：上游两个脚本的包内适配版。相对上游原文只有
  两处改动：(a) 装载路径指到**已安装的包目录**（上游指构建目录 `.`）；
  (b) 结尾由只打印改为 `exit(0)/exit(1)`，让失败能被 conan 捕获。
  `diff -w` 核对：忽略空白后相对上游原文**只**有这两处差异，断言逻辑
  （关键字写读、图像回环、二进制表三列、按行读列、CRPIX/CDELT 比较）逐行相同，
  没有被删改或放宽。
  上游原文 sha256：
  `test_fits.sl = 8e454551da7dafd4c80d90340b559b402dc341848b6c4c2433c78853315dfb6b`、
  `test_wcs.sl = a23548c244873dfc33824c261f0d7b856018d98f8969cf3365097e1d24192556`。

### 6.1 执行模型（两种都是真执行，不是 skip）

| 环境 | 是否执行 | 说明 |
|---|---|---|
| OHOS worker（CI） | ✅ 原生执行 | CI 的 host/build 同为 `ci/conan/profiles/ohos-aarch64`，conan 判定非交叉，`can_run()` 为真 |
| WSL 交叉构建机 | ✅ qemu 执行 | 本机有 `binfmt_misc` + `qemu-aarch64` 与 `/opt/ohos-guest` guest 库；需 `-c tools.build.cross_building:can_run=true` 才会进入 `test()` |
| 纯交叉且 `can_run=false` | ⏭ 显式 skip | `test()` 打印 skip 理由，不伪装通过 |

guest 侧 stock musl 缺 OHOS 硬化符号 `__fd_chk`（`libslang.so.2` 需要它），故在
`/opt/ohos-guest/lib/libfdchkshim.so` 存在时用 `LD_PRELOAD` 注入。真机 OHOS libc
自带该符号、shim 不存在 ⇒ PRELOAD 为空、行为不变（仓库先例：
`archives/x/xhk/1.2`、`archives/m/musicpc/0.35`）。

### 6.2 实测证据

**OHOS worker 原生执行** —— CI build `#93516`（commit `c36615f0`，PR #15810）的
`conan-build-test` 步骤日志：

```
slcfitsio/0.4.7-pre.19 (test package): RUN: sh ".../test_package/run_test.sh" ".../p"
--- slsh test_fits.sl
slcfitsio-test: Passed
--- test_fits.sl rc=0
--- slsh test_wcs.sl
slcfitsio-test-wcs: Passed
--- test_wcs.sl rc=0
ALL_UPSTREAM_REGRESSIONS_PASSED
```

（该次构建用的是本次驱动改动之前的版本；改动后同一路径会额外输出
`UPSTREAM_CASE PASS ...` 与 `UPSTREAM_SUMMARY 2/2`，便于在 CI 日志里直接核对
「实测 N」而不是靠人读；最新一次构建的完整日志行见 PR 描述的
「上游测试用例真实执行记录」。）

**WSL 交叉构建机（qemu-aarch64 + guest shim）** —— 本机实测（命令与输出）：

```bash
cd archives/s/slcfitsio/0.4.7-pre.19
conan create . -pr:h=ohos-aarch64-wsl-xbuild -pr:b=default \
  -c tools.build.cross_building:can_run=true --build='slcfitsio/*'
```

```
guest shims: /opt/ohos-guest/lib/libfdchkshim.so:/opt/ohos-guest/lib/libarc4shim.so
--- slsh test_fits.sl
slcfitsio-test: Passed
--- test_fits.sl rc=0
UPSTREAM_CASE PASS test_fits.sl (rc=0)
--- slsh test_wcs.sl
slcfitsio-test-wcs: Passed
--- test_wcs.sl rc=0
UPSTREAM_CASE PASS test_wcs.sl (rc=0)
UPSTREAM_SUMMARY 2/2
ALL_UPSTREAM_REGRESSIONS_PASSED
```

反证（避免空壳测试）：把包内 `cfitsio-module.so` 清空后重跑驱动 →
`UPSTREAM_CASE FAIL test_fits.sl (rc=7)` / `UPSTREAM_CASE FAIL test_wcs.sl (rc=7)`、
`UPSTREAM_SUMMARY 0/2`、整体 `rc=1`；删掉 `fitswcs.sl` →
`FAIL: the S-Lang wrapper fitswcs.sl is missing`、`rc=1`；`slsh` 不在 PATH →
`FAIL: slsh not found on PATH (the slang runtime is required)`、`rc=1`。

## 7. 遗留 / 人工确认

- 版本号如后续需要适配修复，按 R37 递增为 `0.4.7-pre.19.1`。
