# picotts 0.1_git20210505 适配笔记

## 1. 版本与源码

- 上游：`https://github.com/naggety/picotts`（`ihuguet/picotts` 的 fork，即 Android
  AOSP `platform/external/svox` 的独立化副本）。**上游不打 tag**。
- 版本号与固定提交沿袭 Alpine `community/picotts`：
  `pkgver=0.1_git20210505`，`_commit=21089d223e177ba3cb7e385db8613a093dff74b5`。
  本包 `conandata.yml` 用的就是该提交的官方归档，与 Alpine 逐字一致，可复现。
- 源归档：
  `https://github.com/naggety/picotts/archive/21089d223e177ba3cb7e385db8613a093dff74b5.tar.gz`
  SHA256 `f9556495fd56b96160cdae873ca2dbb0f0a578259c74f4ca939effa3fa1cb101`。
- 真实 autotools 工程在上游源的 **`pico/` 子目录**内（`pico/configure.in` +
  `pico/Makefile.am` + `pico/autogen.sh`），其余（`PicoLangInstaller*`、
  `picolanginstaller/`、`Android.mk`、`pico/src/com/svox/pico/*.java`）是
  Android 应用层与 Windows 打包脚本，**不参与本构建**。

## 2. 上游测试清点（R51 申报）

**结论：上游注册用例 0 个。** 证据：

- `pico/Makefile.am` 全文只声明 `lib_LTLIBRARIES=libttspico.la`（29 个 `lib/*.c`）、
  `bin_PROGRAMS=pico2wave`、`picolang_DATA`（12 个语音资源）与
  `libttspico_la_LIBADD=-lm`；**无 `TESTS` / `check_PROGRAMS` / `check-local` /
  `XFAIL_TESTS`**，故 automake 生成的 `check` 目标零注册用例。
- 全树无 `*test*.c`、`*_test*.c`、`tests/*.sh`、`ctest`/`pytest` 注册文件；
  `pico/tests/` 只有一个 `data/` 目录，内含 8 个手工语料文本
  （`tests_regressions_es-ES.txt` 与 7 个 `xsampa_pico_man_*.txt`），不是可执行的
  测试套件。
- 因此 `make check` 以 rc=0 空跑；本包 `build()` **仍保留该调用**
  （TEST_QUALITY_SPEC §3.3：不得删除 make check）。

按 R51 第 2 步，无上游用例可运行；生效测试为本包补全的两条消费者测试，
见第 6 节与 `test_package/MANIFEST.yml`。

## 3. 构建系统与自举

上游**不提供预生成的 `configure`**，必须自举。CI worker 自带 `autoconf`，
但 **无 `automake` / `libtool` / `aclocal` / `libtoolize`**（真机实测），因此：

```
build_requirements:
  tool_requires("autoconf/2.72")   # 真机已有，但显式声明保证版本一致
  tool_requires("automake/1.18")
  tool_requires("libtool/2.5.4")
```

### 3.1 必须命令行内联覆盖自举环境（关键坑）

首次 W3 失败，报错链为：

```
Can't load '.../perl/5.42.2/.../auto/Cwd/Cwd.so' for module Cwd:
  Error relocating ... Cwd.so: Perl_my_cxt_init: symbol not found
  ... at .../automake/1.18/bin/.aclocal-real line 31
BEGIN failed--compilation aborted at /data/service/hnp/bin/autoconf line 44
```

根因：Conan 的 `perl/5.42.2` 包在真机 ABI 不兼容（其自带 `Cwd.so` 找不到
`Perl_my_cxt_init`），而 `automake`/`autoconf` 包装器 shebang 的是**系统 perl**；
`conanbuild` 又会在每个 `self.run` 时**重新注入** `PERL`/`PERL5LIB` 指向 conan
perl，因此用 Conan 的 `Environment`/`env=` 覆盖**无效**。

修法（与 `archives/a/apertium/3.9.12` 的 DRAFT-6049 成熟模式一致）：把覆盖写成
**命令的一部分**——

```
PERL=perl \
PERL5LIB="<automake>/share/automake-1.18:<autoconf>/share/autoconf" \
TMPDIR/BMP/TEMP="<build_folder>/tmp" \
CONFIG_SHELL/SHELL="/data/service/hnp/bin/bash" \
sh ./autogen.sh
```

`PERL5LIB` 收敛为两个**纯 Perl 模块**目录，XS 扩展（Cwd 等）自然回落到系统
perl 自带的 `@INC`。`TMPDIR/TMP/TEMP` 必须指向可写目录（OHOS `/tmp` 只读，
E002/E011——真机实测 stock `config.guess` 在只读 tmp 下报
`can't create .../dummy.c: Permission denied`）。

## 4. 知识 E007：config.guess / config.sub

**错误签名**（首轮 configure 直接中断）：

```
configure: error: cannot guess build type; you must specify one
（config.log: UNAME_SYSTEM = "HarmonyOS"）
```

**为什么不能用 `--build/--host` 绕过**：E007 明确禁止——会让 configure 误判为
交叉编译（`cross_compiling=yes`），跳过 `AC_RUN_IFELSE` 等运行时探测，按
Linux/glibc 硬编码平台能力。本包按 E007 推荐方案补齐 GNU 脚本。

**施加时机（真机实测结论）**：补丁必须在 `autogen.sh` **之后**施加。原因是
上游 `autogen.sh` 内含

```sh
rm -f install-sh missing depcomp Makefile.in config.guess config.sub
```

随后 `automake --add-missing --copy` 从 `automake/1.18` 复制 GNU 副本
（`config.guess` timestamp=2024-07-27、`config.sub`=2024-05-27）。实测在
autogen **之前**预置 OHOS 版副本会被该 `rm -f` 删除（probe 结果：
`OVERWRITTEN-BY-AUTOMAKE`），故只能在后替换。配方实现见
`conanfile.py::_apply_gnu_config_patches()`：先移除 automake 副本，再
`apply_conandata_patches()` 以"新建文件"形式落回 OHOS 版。

**补丁内容**（由 `scripts/patch-autotools-ohos.pl` 生成，工具自检 Score 4/5）：

| 文件 | 改动 | 校验 |
|---|---|---|
| `patches/0001-pico-config.guess.patch` | LIBC 探针加 `#elif defined(__OHOS__) LIBC=ohos`；系统识别加 `*:HarmonyOS:*:*` 分支 | `__OHOS__=1`、`HarmonyOS=1` |
| `patches/0002-pico-config.sub.patch` | 加 `ohos-linux` 三元组（`basic_os=linux-ohos`）与 OS/内核白名单 | `ohos-linux=1`、`linux-ohos=1` |

**生效验证**（conan 构建日志原文）：

```
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking whether we are cross compiling... no
```

即拿到真实本机三元组且仍为 native 构建（未走 `--build/--host`）。

**R8 合规说明**：补丁中唯一的 `__OHOS__` 出现在 `config.guess` 的 **LIBC 探针**
分支内（与上游既有 `#if defined(__ANDROID__)` 分支同形），属 R8/PF5 明文允许的
"识别 libc 的探针程序"例外；PR 中已说明理由。

## 5. 产物与链接形态（真机实测）

| 产物 | 路径 | 说明 |
|---|---|---|
| 共享库 | `lib/libttspico.so.0.0.0`（+ `.so.0` / `.so` 软链） | 29 个 `lib/*.c`，`-lm` |
| 命令行 | `bin/pico2wave` | 编译期宏 `-Dpicolangdir="//share/pico/lang"` |
| 头文件 | `include/pico*.h` | 公共 API |
| 语音资源 | `share/pico/lang/*.bin` | 12 个（6 语种 × ta/sg） |

- **R26 判定**：`/lib`、`/lib64`、`/usr/lib` 下无 `libttspico*`，**非系统同名库**
  → 按 Conan 默认动态链接（`--enable-shared --disable-static`），不污染系统库。
- **popt 为静态链入**：制品仓 `popt/1.19` 是静态包（`shared=False`），libtool 把
  `libpopt.a` 链入，因此 `pico2wave` 的 `NEEDED` **不含 libpopt**：

  ```
  NEEDED  libttspico.so.0
  NEEDED  libc.so
  （llvm-nm 统计到 51 个 popt 符号 —— 静态链入的证据）
  ```

  `test_package/cli_test.sh` 据此改为校验 popt **符号存在**，而非查 `NEEDED`。

## 6. W3 本地验证结果

`zsh ci/conan/build_and_test.sh archives/p/picotts/0.1_git20210505`

门禁：`G0_RESULT=pass`（546 条知识条目）、`L0_RESULT=pass`（L0i/L0j/L0k/L0m 全过）、
`KC_RESULT=pass`、`JC_RESULT=pass`（prdiff 模式，单软件原子性合规）。

`conan create`（`-pr:h/-pr:b=ohos-aarch64`）：

- `Package '2832559a05a69c5c800f67f8a0fe6194d62b9f29' created`
- 库 API 端到端契约测试：**`CONTRACT: 26 assertions, 0 failed` / `CONTRACT-OK`**，
  真实合成出 **139008 字节** 16-bit PCM
- 已安装 CLI 真实行为测试：**`CLI-TEST: 17/17 assertions passed`** /
  `CLI-TEST-OK`
- 上游 `make check`：rc=0（零注册用例，见第 2 节）

> 说明：本地 W3 需绕过两个本机环境问题——① 本 worktree 的 `origin/main`
> （fork `Inception662`）落后 HEAD 5199 个提交，导致 JC6 把整仓 2485 个软件包
> 误判为"本 PR 变更"，故用 `JUNK_PR_DIFF`（CI `checkout-pr` 同语义）传入只含本包
> 的 diff；② 本机 `github.com` 主站超时，由 W3 内置的镜像预下载改写为 `file://`
> 后构建（脚本退出时已还原为官方 URL）。两者都与本包内容无关。

## 7. 已知限制

`pico2wave` 的语音资源目录是**编译期常量**（`picolangdir = $(datadir)/pico/lang`；
本包 `--prefix=/` 下展开为 `//share/pico/lang`，POSIX 等价于 `/share/pico/lang`），
上游未提供任何运行期覆盖选项（CLI 只有 `-w`/`-l`，且 `-l` 只接受语种名）。
因此从 Conan 包直接调用该 CLI 需把包内 `share/pico/lang` 部署到该路径；
否则应改用库 API 并显式传入资源目录——消费者测试即采用后者，故 TTS 引擎功能
本身已被完整验证。

## 8. 知识沉淀候选

- **L2 候选**：上游 `autogen.sh` 含 `rm -f config.guess config.sub` 的 autotools
  库，E007 补丁必须施加于 autogen 之后（预置会被删除）。可作为 E007 的补充条目。
- **L1 候选**：`perl/5.42.2`（Conan 包）在 OHOS 真机 ABI 不兼容
  （`Perl_my_cxt_init: symbol not found`），且 `conanbuild` 会重新注入
  `PERL`/`PERL5LIB`——覆盖必须内联在命令内。已有 DRAFT-6049 记录（apertium），
  本条为其在"上游不发布 configure"场景下的复现证据。
---

**编译结束**: 2026-10-14 17:01
**最终状态**: built
