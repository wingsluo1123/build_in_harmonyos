# dma 0.14 适配笔记

## 编译环境

- 构建系统: **makefile**（上游裸 BSD 风格 `Makefile`，非 autotools）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（`aarch64-linux-ohos`），`cc`/`c++`/`gcc` 在本机均**不存在**
- 状态: built

### 构建系统判定证据（init-build 曾按 URL 误猜为 autotools）

对 v0.14 tag 逐个做文件在场检查，结果：

| 标记文件 | 在场 |
|---|---|
| `configure` / `configure.ac` / `configure.in` | 无 |
| `Makefile.am` / `Makefile.in` | 无 |
| `CMakeLists.txt` | 无 |
| `meson.build` | 无 |
| `autogen.sh` / `bootstrap.sh` / `setup.py` | 无 |
| **`Makefile`** | **有**（BSD 风格：`SH?=` / `CC?=` / `YACC?=` / `LEX?=`、`.SUFFIXES` + `.c.o` suffix rule） |

⇒ 纯 `makefile`。`.build-context-dma-0.14` 的 `BUILD_SYSTEM` 由 `autotools` 更正为 `makefile`，
`manifest.yaml` 的 `build.system` 同步更正，再跑 `conan-init` 才拿到 `conanfile-makefile.py.tmpl` 与
可执行型 `test_package`。

## 货源（**非 Debian 池**，官方 tag）

登记表原备注的替代读数 `Debian pool dma_0.14.orig.tar.gz`
（`http://deb.debian.org/debian/pool/main/d/dma/`）是 PF7 黑名单域
（`scripts/ohc/preflight.py:361` `_PF7_DEBIAN_HOSTS = ("deb.debian.org", "snapshot.debian.org",
"security.debian.org", "archive.debian.org")`），**不得作为交货货源**，已弃用。

改用官方 GitHub tag，三个来源 sha256 完全一致：

| # | 来源 | http | size | sha256 |
|---|---|---|---|---|
| ① | `https://github.com/corecode/dma/archive/refs/tags/v0.14.tar.gz`（curl，302→codeload） | 200 | 37572 | `a36e77a59dd288a582dbeed7166ac4212e39120323bac75c74d7923e1d7b63e8` |
| ② | `https://codeload.github.com/corecode/dma/tar.gz/refs/tags/v0.14`（curl 直连） | 200 | 37572 | 同上 |
| ③ | `init_build.py:_verify_checksum` 机校（`EXPECTED_SHA256` 不符即 `unlink` + rc=3） | — | — | 校验通过才继续 |

magic = `1f8b0800`（gzip）✅，`tar tzf` 解压 rc=0 ✅。④ = `conandata.yml` 的 `sha256:` 字段（同值）。
落地文件 `~/tmp/builds/dma-0.14.tar.gz`（**未写 `/tmp`**，规避 E002）。

**下载通道实测故障与绕法**（可复用手法）：python `urlopen` 对
`github.com/.../archive/refs/tags/v0.14.tar.gz` 的 **302 重定向段 45s 超时**
（`<urlopen error [Errno 110] Operation timed out>`），而直连 `codeload.github.com` **0.6s 返回 200/37572**；
`curl` 两条皆通（1.803s / 0.509s）。`init-build` 首轮因此 `INIT_RC=3`。
处置 = **预置已验证 tarball 到 `build_dir`（`init_build.py:380` = `$TMPDIR/builds`）**
—— `init_build.py:441 if not tarball.exists()` 命中即**跳过下载**，再由
`EXPECTED_SHA256` 走真实 sha 校验。**URL 仍锁官方 `github.com/corecode/dma` tag**，未换镜像、未用 Debian 池。
⚠ 本机 `TMPDIR` 默认指向家根，已显式改为 `$HOME/tmp` 再跑（家目录分区表：临时产物只落 `~/tmp/`）。

### ★ 取源端点换到官方 `codeload` 直连（2026-10-08，R39 取源规范化 · 有出处）

**背景（G2 三轮同根因红的第一手根因）**：`conan-verify` 的 E017 预防会把 conandata 里
字面 `https://github.com` 注入为镜像前缀 `https://ghfast.top/https://github.com`
（`scripts/ohc/conan_verify.py:571-574`，`finally:629-631` 回滚），而本机到 **`ghfast.top` 不可达**
⇒ `source()` 挂在 `Error in source() method, line 94`，`make` 一次未执行（三轮同错）。

**逐端点实测读数**（2026-10-08 同一轮 curl，`--max-time 60`，`sha256` 与 `tar tzf` 同刻核）：

| # | 端点 | HTTP | 字节 | sha256（前 8…尾 8） | 解包 | 备注 |
|---|---|---|---|---|---|---|
| ① | `https://codeload.github.com/corecode/dma/tar.gz/refs/tags/v0.14` | **200** | 37572 | `a36e77a5…63e8` | ✅ `dma-0.14/` | **采用**（0.64s） |
| ② | `https://github.com/corecode/dma/archive/refs/tags/v0.14.tar.gz` | `000` | 0 | — | — | **超时 ≠ 不可达**：curl rc=28、60s 零字节（302 段） |
| ③ | `https://ghfast.top/https://github.com/…v0.14.tar.gz`（E017 注入形态） | `000` | 0 | — | — | curl rc=28，**connect 阶段超时 60s** |
| ④ | `http(s)://deb.debian.org/debian/pool/main/d/dma/dma_0.14.orig.tar.gz` | 200 | 37572 | `a36e77a5…63e8` | ✅ `dma-0.14/` | 字节一致但 **PF7 `_PF7_DEBIAN_HOSTS` 黑名单 ⇒ 禁用** |
| ⑤ | `https://distcache.FreeBSD.org/ports-distfiles/dma-0.14.tar.gz` | `000` | — | — | — | curl rc=60 **SSL 证书主机名不匹配**（非超时） |

⇒ **判据**：上游官方非 github 归档端点里，Debian 池可用但被 PF7 禁用、FreeBSD distfiles 证书不匹配
⇒ **换可达端点 = 官方 `codeload.github.com` 直链**（GitHub 自有归档端点、同 tag 同字节同 sha256）。
**⛔ 换源这一动作：未加任何镜像前缀、未改动任何上游取源相关代码、未用 Debian 池**
（AGENTS §2 ①「实际端点实测」+ 手册/07 §12.3：
「GitHub archive 在 worker 超时可试官方 `codeload.github.com`；必须核对内容与 SHA；无 `.tar.gz` 后缀时显式指定 `filename`」）。
本包唯一的上游改动是后文「源码修改」节登记的 1 个编译期补丁（`getprogname` shim，中性能力宏 `HAVE_BSD_PROGNAME`，补丁零平台宏）。

**落点（配方侧改动，两处同源）**：
- `conandata.yml`：`url` → codeload 直链 + **`filename: "dma-0.14.tar.gz"`**（codeload 路径尾段是 `v0.14`，
  `conan.tools.files.get` 按 URL basename 推文件名、`unzip` 只按扩展名分派 —— 不给 `filename` 会掉进
  zipfile 分支；仓内先例 549 份 conandata 用 codeload，如 `a/abbtr/1.0.4` 同款三行）。`sha256` 不变。
- `manifest.yaml`：`source.url` 同步（与 conandata 同源，`适配检查清单` 通用 §5）。
- 本地 PF7 复跑：`check_source_urls(…, [conandata.yml, manifest.yaml])` → **findings 为空**；
  `grep -Ec 'ghfast|gh-proxy|file://'` 两文件 → **0 / 0**。

**E017 交互（源码级核过，非猜测）**：换源后 conandata 不再含字面 `https://github.com`
（`codeload.github.com` 不匹配 `replace` 的字面串）⇒ `:573` 替换为 no-op、**镜像不注入**；
`.ghfast-bak` 残留件按 `适配检查清单` 通用 §2 在提交前删除。

## 编译步骤

```bash
# W0 依赖发布检查（真实版本）
bash ci/scripts/preflight_check.sh dma/0.14
python3 scripts/ohc-run.py recipe-search dma          # 语料 8244 条无相似配方 ⇒ 走 conan-init 模板
# build 一条龙撞 init_build_failed(Step1) ⇒ 按 §12.60① 跳过，改：
python3 scripts/ohc-run.py init-build dma 0.14 --url=https://github.com/corecode/dma/archive/refs/tags/v0.14.tar.gz --auto
python3 scripts/ohc-run.py conan-init dma 0.14        # BUILD_SYSTEM=makefile
python3 scripts/ohc-run.py conan-verify dma 0.14      # G2 conan create = 正式带依赖注入的编译
```

配方 `build()` 实际执行（R33/R9 合规，编译器取自 conan conf 而非 shell 变量）：

```python
make CC="<conf: tools.build:compiler_executables:c>" YACC=bison LEX=flex \
     CPPFLAGS="-I<openssl includedirs>" LDFLAGS="-L<openssl libdirs>" LDADD="-lssl -lcrypto" -j1
```

要点：
- **`LDADD` 在命令行覆盖**，去掉上游默认的 `-lresolv`（`Makefile:18`）—— musl/OHOS 把 resolver 内置进
  libc，链 `-lresolv` 必失败（`经验文档/适配检查清单.md` → Makefile/无构建系统 §2）。
  命令行变量优先级高于 Makefile 的 `LDADD?=`，**未改任何上游文件**。
- **`CFLAGS` 故意不覆盖**：Makefile 会向其追加 `-DDMA_VERSION` / `-DLIBEXEC_PATH` / `-DCONF_PATH`，
  覆盖即触发 `dma.h:76 #error Please define CONF_PATH`。OpenSSL 头改走 `CPPFLAGS`
  （`.c.o` suffix rule 本身消费 `${CPPFLAGS}`）。
- **`-j1`**（R9）：本机 `make -j2` 报 `jobserver mkfifo: .../GMfifo62276: Operation not permitted`（HMDFS 限制），
  不致命但 `-j1` 规避。
- `YACC=bison LEX=flex`：本机 `lex` **不存在**（`lex=` 空），只有 `flex`；`yacc`/`bison`/`flex` 通过
  `tool_requires` 固定，保证 CI 侧也有。

### 裸 make 探测轮（非正式构建链，供对照）

首轮**不经 conan 依赖注入**的裸 `make -j2 CC=clang LEX=flex`，第一条真实错误逐字：

```
In file included from base64.c:37:
./dma.h:45:10: fatal error: 'openssl/ssl.h' file not found
#include <openssl/ssl.h>
         ^~~~~~~~~~~~~~~
make: *** [Makefile:96: base64.o] Error 1
MAKE_RC=2
```

根因是**缺依赖注入而非包编不了**：本机三处路径全无 OpenSSL 头且 `pkg-config --exists openssl` 为否
（`/usr/include`、`/usr/local/include`、`~/usr/local/include` 逐个探过），而依赖在制品仓**已发布**。
带依赖注入的正式编译以 `conan-verify` 的 G2 `conan create` 为准。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `build` 一条龙停在 `init_build_failed` | registry 无 dma 条目；搜索引擎给出 6 个 URL 全为**无关域**（`download.savannah.nongnu.org/releases/dma/`、`www.dma.org`、`dma.org`） | 按 `§12.60①` 跳 `build`，改 `init-build --url=<官方 github tag>`；6 个搜索 URL 一个未用 |
| 2 | `init-build` 下载 `Errno 110 Operation timed out` | python `urlopen` 对 `github.com/.../archive/...` 的 302 段超时（codeload 直连 0.6s 正常） | 预置已验证 tarball 到 `$TMPDIR/builds`（`init_build.py:441` 命中即跳过下载）+ `EXPECTED_SHA256` 真校验 |
| 3 | `init-build` 把构建系统猜成 `autotools`，三件模板全跳过 | `_guess_build_system(download_url)` 只看 URL，registry 无条目可查 | 逐文件事实核（见上表）后把 `BUILD_SYSTEM` 改 `makefile`（改工作区状态文件，⛔ 不碰 `scripts/`）再跑 `conan-init` |
| 4 | `conanfile.py 模板不可用（autotools）` / `test_package` 生成成 CMake 版 | `conan_recipe.py:347` 用 `"cpp_info.libs" in content` 判库类型，字符串包含即真 | 改 `BUILD_SYSTEM` 走 makefile 模板；手写可执行型 `test_package`（删 CMake 版误生成件） |
| 5 | `manifest.yaml` 两处模板占位符未展开 | init-build 的模板替换只覆盖部分字段 | `software: "dma"`、`build_system: "makefile"` 手工展开；`source.sha256` 填入四方法 |
| 6 | 裸 make 报 `'openssl/ssl.h' file not found` | 未走 conan 依赖注入（见上） | 配方 `requires("openssl/1.1.1w")` + `CPPFLAGS`/`LDFLAGS`/`LDADD` 注入 |
| 7 | 上游 `LDADD` 含 `-lresolv` | musl/OHOS 内置 resolver | 命令行覆盖 `LDADD="-lssl -lcrypto"`（不动上游 Makefile） |
| 8 | 本机无 `lex` | 只装了 `flex` | `tool_requires flex/2.6.4` + `LEX=flex`；`tool_requires bison/3.8.2` + `YACC=bison` |
| 9 | `make -j2` jobserver FIFO 被拒 | HMDFS 不允许建 `/tmp` 系 mkfifo | `-j1` |
| 10 | G2 `source()` 三轮红（`Error in source() method, line 94`，`make` 未执行） | E017 把 conandata 的 github URL 注入 `ghfast.top` 镜像，本机不可达（curl 60s/000） | **换官方 `codeload.github.com` 直链**（见上「取源端点换到官方 codeload 直连」节），换源后 E017 replace 变 no-op、镜像不再注入 |
| 11 | `dfcompat.c:119:2: error: "no getprogname implementation available"`（换源后 `make` 首次执行的第一条真实错误） | 上游只在 `__GLIBC__` 分支给 `getprogname()` shim；OHOS 是 musl、既无该函数也非 glibc | 补丁 `patches/0001-ohos-getprogname.patch`（知识库 E203 方案，见下节） |

## ★ 编译期修复：musl 无 `getprogname()` ⇒ 按 E203 补中性能力宏 `HAVE_BSD_PROGNAME` 分支（补丁零平台宏）

**症状（第一条真实错误，逐字）**

```
dfcompat.c:119:2: error: "no getprogname implementation available"
#error "no getprogname implementation available"
 ^
make: *** [Makefile:96: dfcompat.o] Error 1
ERROR: dma/0.14@ohpcd/stable: Error in build() method, line 119
```

（`conan-verify` G2 r9 日志 `reports/conan-create.log:149-158`；此前三轮全停在 `source()`，
本轮 `source()` 已通过、`make` 首次真正执行。）

**根因（逐条实测，非推测）**

| # | 事实 | 读数 |
|---|---|---|
| 1 | 上游只在 glibc 分支提供实现 | `dfcompat.c:105-121`：`#ifndef HAVE_GETPROGNAME` → `#ifdef __GLIBC__` 给 shim → `#else #error "no getprogname implementation available"` |
| 2 | OHOS musl **不提供** `getprogname()` | `/data/service/hnp/bin/clang` 编译 `getprogname()` 调用 → `warning: call to undeclared function` + `ld.lld: error: undefined symbol: getprogname` |
| 3 | OHOS musl **导出** `__progname` | `extern char *__progname;` + clang 编译 + 运行 → 打印真实 argv0（`prog=t2`）；但 `<errno.h>` **不声明**它（`t4.c` → `use of undeclared identifier '__progname'`），故补丁内自带 `extern` |
| 4 | 不能走上游 `HAVE_*` 旁路 | `Makefile:1-9` 自述：「Define HAVE_* if your system **already provides**: reallocf / strlcpy / **getprogname**」—— OHOS 未提供 ⇒ 定义 `HAVE_GETPROGNAME` 是撒谎，会留下未定义符号 |
| 5 | 编译器宏（只作实测记录） | `clang -dM -E` → `#define __OHOS__ 1`（另有 `__OHOS_FAMILY__`/`__linux__`）—— 平台宏确实存在，但按 R8/PF5 **补丁内不得使用**，故最终方案改走中性能力宏（见下） |

**已试/已排除的方案**

- ❌ `-DHAVE_GETPROGNAME`：系统并不提供该函数，`util.c` 的调用会变成未定义符号（事实 2、4）。
- ❌ conanfile 内联注入 `-D__OHOS__` 或 `-include` 头文件：**PF5 平台宏闸（R8）明确禁止**
  （「绕开 patches/ 禁令的等价违规（语料 64+27 例）⇒ 改走 POSIX 兼容写法或规范 `patches/`」）。
- ❌ **在补丁里直接写 `#elif defined(__OHOS__)`（本包第一版形态，已返修）**：
  2026-10-08 14:42:33 AI 审查计数逐字「P0 = 0，P1 = 1，P2 = 0，P3 = 0」、判 **P1 需要修改**
  （行级意见 `discussion=561d0dd3094b`、`resolved=false`），意见逐字「移除补丁中的 `#elif defined(__OHOS__)`
  平台宏分支，改用不带 OS 条件宏的 POSIX/构建期探测适配路径」；依据 `SKILL.md:338` R6-R10
  「patches/ 补丁文件中默认禁止平台宏」与 `references/iron-rules.md` R8
  「patches/ 补丁文件中不应引入 `#ifdef __OHOS__`，应通过 POSIX 兼容方式修复」。
  知识库 `E203` 推荐形态与该条规则**相互冲突**，以 **R8 / PF5 为准**（E203 只保留为
  `__progname` 替代方案的出处），故按**路 A** 改写（见下「最终方案」）。
- ❌ 依赖知识图谱给的 E540（`runner-path-prepend`）：那是 shadow-ci 的 PATH 问题，
  与本错误无因果（本轮日志里 G2 仍提示 `参考 E540`，**不采信**）。

**最终方案（P1 返修后形态）**：`archives/d/dma/0.14/patches/0001-ohos-getprogname.patch`

- **出处**：知识库 `knowledge/doc/E203.md`（类别 `source-patch`，严重度 2）给出的替代方案
  「使用 `__progname` 替代 `getprogname()`」—— **`__progname` 这一手段不是自造**；
  其原推荐的 `#ifdef __OHOS__` 守卫形态按 R8/PF5 放弃，改以中性能力宏落地。
- **形态（路 A：补丁零平台宏）**：
  ① 补丁只加 `#elif defined(HAVE_BSD_PROGNAME)` 分支（宏名不含 `OHOS` 字样、对齐
  `Makefile:1-9` 的 `HAVE_*` 语义），补丁文件内 `__OHOS__` **0 命中**（`grep -c` 实测 rc=1）；
  ② 该宏由 `conanfile.py` `build()` 的**构建期链接探测** `_have_bsd_progname()` 注入：
  写一个只引用 `extern char *__progname;` 的探针 TU，用与 `make` 同一个 `cc`
  （R33 取自 `tools.build:compiler_executables`）编译+链接，**rc=0 才追加
  `-DHAVE_BSD_PROGNAME`**，否则返回空串 ⇒ 落到上游原 `#error`，非鸿蒙平台行为与上游完全一致；
  ③ 宏经 **`CPPFLAGS`** 传入（`Makefile:95-96` 的 `.c.o` 规则同吃 `CFLAGS`+`CPPFLAGS`；
  **不能走 CFLAGS** —— `Makefile:17` 自己往 CFLAGS 上 `+= -DDMA_VERSION/-DLIBEXEC_PATH/-DCONF_PATH`，
  命令行覆盖会丢宏、触发 `dma.h` 的 `#error Please define CONF_PATH`）。
- **形态（conandata/登记）**：`conandata.yml` `patches:` 段登记（`patch_type: portability`，
  `patch_description` 已改为中性能力宏口径），`conanfile.py` 用既有的
  `export_sources()`→`export_conandata_patches` + `build()`→`apply_conandata_patches` 应用；
- **规模**：只动 `dfcompat.c` 的非 glibc 分支，**+12 行（实现 7 行 + 注释 3 行 + 空行 2 行）**，
  零其它上游文件改动、零补丁外的源码改动；`patch --dry-run -p0` 实测干净通过；
- **归属**：本条 `getprogname` 机制在知识池**已有 E203** ⇒ 本包对它是 **`hit`（复用）**，
  ⛔ 不作为本 PR 的知识位（一 PR 一知识；本 PR 的知识位见 B 判定 note）。

## ★ 能力面披露：setuid 投递面 / 队列路径 / 特权降权（**逐字实测读数**）

> 本节是本包的核心能力面证据。所有读数 2026-10-08 在 B 机实测，探针一律用 `errno` 方式
> （⛔ 未使用 `os.path.exists`，规避 EACCES 假阴性）。

### A. 上游 `make install` 目标的四重墙（`Makefile:53-54` 原文）

```make
${INSTALL} -m 2755 -o root -g mail dma ${DESTDIR}${SBIN}
${INSTALL} -m 4754 -o root -g mail dma-mbox-create ${DESTDIR}${LIBEXEC}
```

| # | 墙 | 实测读数 |
|---|---|---|
| 1 | `install` 命令**不在 PATH** | `install --version` → `bash: line 1: install: command not found`；`install -m 4754 ... ` → **`rc=127`**；`/usr/bin/install`、`/system/bin/install` 均不存在（后者 `Permission denied`） |
| 2 | `-o root` | 运行身份 **`uid=20020084 gid=20020084`**（`id` 输出：`cannot find name for user ID 20020084`），**非 root** |
| 3 | `-g mail` | `getent group mail` → `getent: command not found`；`grp.getgrnam('mail')` → **`KeyError "getgrnam(): name not found: 'mail'"`** —— **`mail` 组不存在** |
| 4 | `-m 4754`（setuid）/ `-m 2755`（setgid）位不被保留 | `chmod u+s <临时文件>` → **返回 `ok`**，随后 `stat` → **`setuid=False setgid=False`**，且 mode 实得 **`0o770`**（连请求的 `0o755` 都没保住） |

⇒ **四重叠加：上游 `install` 目标在 OHOS 完全不可用。**

### B. 文件系统可写性（errno 方式）

| 路径 | 探针结果 |
|---|---|
| `/` | `write` → **`errno=13(EACCES) Permission denied`** |
| `/usr` | `write` → **`errno=13(EACCES) Permission denied`** |
| `/etc` | `write` → **`errno=30(EROFS) Read-only file system`**（**只读**） |
| `/var` | `stat` → **`errno=2(ENOENT)`** —— **`/var` 目录根本不存在** |
| `/var/queue` | `stat` → `errno=2(ENOENT)` |
| `/var/spool/dma` | `stat` → `errno=2(ENOENT)`；`mkdir(/var/spool/dma)` → **`errno=2(ENOENT)`**（父目录缺失，**无法创建**） |
| `/var/run`、`/usr/libexec` | `stat` → `errno=2(ENOENT)` |
| `/usr/lib` | `stat` → `mode=0o755 uid=0`，存在 |

⇒ **上游默认队列路径 `DMASPOOL=${VAR}/spool/dma`（`Makefile:31-32`，`VAR?=/var`）在 OHOS 无处安放**：
`/var` 不存在且其父 `/` 为 `EACCES`，`install-spool-dirs` 目标（`Makefile:63-65`）与
`permissions` 目标（`Makefile:67-70`，`chgrp mail`）**均不可执行**。
`install-spool-dirs` 用的 `chgrp` 命令本机也**不存在**（`chgrp => MISSING`）。

### C. 运行期特权降权语义

- `dma.c:464` `if (geteuid() == 0 || getuid() == 0)` → 才进入降权块；`dma.c:468` `getpwnam(DMA_ROOT_USER)`；
  `dma.c:476` `if (setuid(pw->pw_uid) != 0) err(EX_OSERR, "cannot drop root privileges")`；
  `dma.c:479` 复检 `geteuid()==0 || getuid()==0` 仍真则 `errx`。
- **当前 uid=20020084（非 root）⇒ 该降权块整体不进入**，`setuid()` 调用**不发生**。
- 上游依赖 setuid 位生效的投递路径（`dma-mbox-create` 以 `-m 4754` 安装、
  以 root 身份建 mailbox）在 OHOS **既装不上位（A-4）、运行期也不触发（本节）**。

### D. 处置口径

按 `appres` / `ddccontrol` 模式：**编译照交**，`test_package` 只打参数期断言、
**不碰真投递、不碰 spool**（两条断言的失败点均在 `dma.c:606 parse_conf` 之前，见 test_package 注释中的行号链），
能力面**在本节逐字披露**。

**触发停报的条件**（主理裁决）：`conan-verify` 的 G2 `conan create`（带依赖注入的正式编译）失败
⇒ 编译阶段真撞墙，立即停下逐字上报。上游 `make install` 的四重墙**不算我方撞墙**——
配方走 `self.copy()` 从 build folder 取产物自装（`适配检查清单` Makefile §3 的文档化做法），
**⛔ 未修改上游任何 Makefile、未 mock 任何环节**。

## 源码修改

**补丁 1 个**（`patches/0001-ohos-getprogname.patch`，**R8/PF5 合规：补丁零平台宏**，理由见下）：

| 补丁 | 目标文件 | 规模 | 内容 |
|---|---|---|---|
| `0001-ohos-getprogname.patch` | 上游 `dfcompat.c` 的非 glibc 分支（唯一改动点） | **+12 行**（实现 7 行 + 注释 3 行 + 空行 2 行），零其它上游文件改动 | `#elif defined(HAVE_BSD_PROGNAME)` 提供 `getprogname()`，返回 musl 导出的 `__progname`；宏由配方构建期链接探测注入；补丁文件 `grep -c __OHOS__` = **0 命中（rc=1）**；`patch --dry-run -p0` 实测干净通过 |

**其余差异全部经 make 命令行变量与 conan 配方表达，不改任何上游文件**：
`LDADD` 覆盖（去 `-lresolv`）、`CPPFLAGS`/`LDFLAGS` 注入 OpenSSL 与能力宏、`YACC`/`LEX` 指定工具、
`package()` 手工 `copy()` + `os.chmod(0o755)`。

**R8/PF5 合规声明（原「平台宏例外」三条理由已随 P1 返修整段撤下，不再援引例外）**：

- **规则原文（逐字）**：`references/iron-rules.md` R8 ——「**源码中可以使用 `#ifdef __OHOS__` 守卫（允许），但
  patches/ 补丁文件中不应引入 `#ifdef __OHOS__`，应通过 POSIX 兼容方式修复**」；`SKILL.md:338`（R6-R10）——
  「`#ifdef __OHOS__` 守卫可用但须有实质逻辑（禁止空壳 stub），**patches/ 补丁文件中默认禁止平台宏，
  例外（如 libc 探针）须在 PR 说明理由（口径以 iron-rules.md R8 为准）**」。
- **本包不走例外**：补丁改用中性能力宏 `HAVE_BSD_PROGNAME`（宏名不含 `OHOS` 字样），由 `conanfile.py`
  `build()` 的 `_have_bsd_progname()` **构建期链接探测**注入 ⇒ 平台宏一处都不落在 `patches/`，
  PF5 天然通过（该闸逐字：「PR 变更的 `patches/*.patch` 新增行（`+` 开头）含 `__OHOS__` 即 fail-closed，
  上下文行与历史存量豁免；例外场景需 PR 说明理由后 `--no-preflight` 显式跳过（留痕可审计）」——本包未使用该跳过口）。
- **能力语义 ≠ 平台语义**：宏表示「libc 导出 BSD 风格 `__progname` 符号」，由链接探测的 rc 裁决；
  探测失败 ⇒ 不注入 ⇒ 落到上游原 `#error`。glibc 上 `#ifdef __GLIBC__` 分支先命中，注入与否都不改变
  上游行为 ⇒ 对非鸿蒙平台透明（R8 核心原则：「你的修改对非鸿蒙平台必须是透明的」）。
- **与知识库 E203 的冲突处置**：E203 推荐形态含 `#ifdef __OHOS__` 守卫，与 R8/PF5 冲突；
  按 `SKILL.md:338` 的「口径以 iron-rules.md R8 为准」以 **R8 为准**，E203 降为 `__progname` 手段的
  出处（`hit` / cross-ref），⛔ 不作为平台宏豁免依据；知识库本身属平台侧，未改动。

## 依赖版本

| 依赖 | 版本 | 类型 | 制品仓发布核验（`conan download --only-recipe`，R35 合规） |
|---|---|---|---|
| `openssl` | **1.1.1w** | `requires` | ✅ rrev `a29b10b89b32a0410043b40c1d7db4fc` |
| `bison` | 3.8.2 | `tool_requires` | ✅ rrev `27704878ab972a7b7a0a560e22360cbb` |
| `flex` | 2.6.4 | `tool_requires` | ✅ rrev `dae8938545a70afe5596b280fc4ad124` |

**选 `openssl/1.1.1w` 的理由**：
1. `crypto.c:126` `#if (OPENSSL_VERSION_NUMBER >= 0x10100000L)` → `meth = TLS_client_method()`
   （`crypto.c:127`），1.1.1w 正中该分支；`else` 分支才是 `SSLv23_client_method()`（`crypto.c:129`）。
   所用 API（`SSL_library_init`/`SSL_CTX_new`/`X509_digest`/`EVP_sha256`/`SSL_get0_param`/
   `X509_VERIFY_PARAM_set1_host`）1.1.x 与 3.x 皆可用，1.1.1w 无兼容风险。
2. 仓内同族 sendmail 模拟器 **`ssmtp/2.64` 同样 `requires("openssl/1.1.1w")`**，与本包定位最接近。
3. 仓内归档 10 个版本可选（1.1.1w, 3.0.16, 3.0.21, 3.5.6, 3.5.6.1, 3.5.6.1.1, 3.5.6.1.2, 3.5.7, 3.5.8.1, 4.0.1），
   1.1.1w 已被大量他包引用；体积与 W3 预算优于 3.x。
   （对照：制品仓探 `openssl/3.5.4`、`3.4.1`、`3.3.2`、`1.1.1t` 远端回
   `system acceleration policy not enabled`，未选用。）

## 测试与验证结果（五维，三处同源）

**五维数值**（与 `test_package/MANIFEST.yml`、`manifest.yaml` 同源）：

| 维度 | 值 | 依据 |
|---|---|---|
| `N_static`（上游静态声明） | **0** | 见 test_package/MANIFEST.yml 顶部清点证据 |
| `N_registered`（构建系统注册/可执行测试目标） | **0** | 顶层 Makefile 无 `check`/`test` 目标 |
| `N_executed`（实际上游测试执行数） | **0** | 无上游测试可执行 |
| 未执行分类数 | **0** | 不存在被跳过的上游用例；`N_executed=0` 源于 `N_static=0`，非"跑了没过" |
| `N_consumer`（新增消费者测试） | **2** | `test_package/test.sh` 两条断言 |
| `N_runner` | **0** | 无 runner 层 |
| `assertion_count` | **2** | 同上 |

> 上游确无自动化测试套件，**不声称跑过不存在的 `make check`**（手册/04 §10 口径）。
> 消费者测试按赛道二硬门禁真实驱动被测二进制并以断言决定退出码（R34/PF3）。

**消费者断言（2 条，均在参数期、零副作用）**：

| # | 命令 | 断言 | 源码位置 |
|---|---|---|---|
| 1 | `dma -Z` | stderr 含 `invalid argument` 且回显 `-Z`，退出码非 0（实测 `rc=64`） | `dma.c:581` `fprintf` → `dma.c:582` `exit(EX_USAGE)` |
| 2 | `dma -bp -q` | stderr 含 `sending mail and queue operations are mutually exclusive`，退出码非 0（实测 `rc=64`） | `dma.c:585` `argc -= optind` → `dma.c:588-590` `if (argc != 0 && (showq \|\| doqueue))` → `errx(EX_USAGE)` |

**断言 2 的真实触发链（2026-10-08 对打包二进制逐条实测，含与原设计的差异披露）**：

- `-bp` → `showq=1`（`dma.c:513-515`）；`-q` → `doqueue=1`。
  注意 `dma.c:503` 的 optstring 是 `...O:q:r:...` ⇒ **`q` 是带参选项**（缺参时走 `dma.c:573-577`
  `case ':'` → `optopt == 'q'` → `doqueue = 1`）。
- **`-q` 后面没有操作数时，musl 的 getopt 缺参分支把 `optind` 推到 `argc+1`**（最小复现
  `gopt.c` 同 optstring 实测：`init_argc=3 → final optind=4`）⇒ `dma.c:585 argc -= optind` 得 **-1 ≠ 0**
  ⇒ **`dma.c:588` 的操作数护栏先触发** → `dma.c:590 errx("sending mail and queue operations are mutually exclusive")`。
- **与原设计的差异（如实记录）**：原设计预期走 `dma.c:592-593`（`showq+doqueue > 1` →
  `conflicting queue operations`）；实测该分支需要 `-q` 真的吃到一个参数（如 `dma -bp -q x`，
  `x` 被 `q` 当作 optarg 吃掉 ⇒ `argc=0` ⇒ 592 触发），裸 `dma -bp -q` 走不到它。
  **命令一字未改（仍是主理裁定的 ⓐ），只把期望串改成上游该路径的真实输出**，
  行号链与触发条件已按上文逐条更正（`gopt.c` 复现脚本留档 `~/tmp/uc2/dma-0.14-src/probe/`）。
- 两条断言的失败点都在 **`dma.c:606 parse_conf` 之前**，不读配置、不碰 spool、不碰投递路径。
- 备用 ⓑ `dma -q nosuch@host` **实测不可用**（逐字读数）：`rc=66`、`stderr=[dma: reading queue: No such file or directory]`
  —— 因 `q` 带参，`nosuch@host` 被吃成 optarg ⇒ `argc=0`、护栏不触发 ⇒ 下落到 `parse_conf → load_queue`，
  正是要避开的 spool 路径（`EX_NOINPUT=66`）。
- **`-bq` 单独也不可用**：`dma.c:516-518` 把它映射为 `queue_only`（既非 showq 也非 doqueue），
  护栏不触发，会下落到 `dma.c:618 doqueue → dma.c:620 load_queue`（原判断成立）。

**为什么不写 `-h`/`-V`/`--help` 断言**：`dma.c:503` 的 getopt 串为
`:A:b:B:C:d:Df:F:h:iL:N:no:O:q:r:R:tUV:vX:`，`dma.c:563-577` 的
`case 'h'` / `'U'` / `'V'` / `'v'` / `'X'` **全部落在 "Ignored options" 段纯 `break`**——
不打印 usage、不退出（`grep -n 'usage' dma.c` **零命中**，全程序无 usage 输出路径），
且无 long options（不支持 `--help`）。跑 `dma -h`/`-V` 会继续下落到配置解析与投递流程，
既无可比对文本、也不安全。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | makefile 配方：`requires openssl/1.1.1w`、`tool_requires bison/flex`、`self.copy` 自装、OHOS 签名、`_have_bsd_progname()` 构建期链接探测注入能力宏 |
| `conandata.yml` | 官方 `codeload` 归档端点 URL + `filename` + sha256（三方一致）；`patches:` 段登记 0001 补丁 |
| `patches/0001-ohos-getprogname.patch` | `dfcompat.c` 非 glibc 分支 +12 行（`getprogname` shim，中性能力宏 `HAVE_BSD_PROGNAME`，零平台宏；出处 E203） |
| `test_package/` | `conanfile.py` + `test.sh`（2 条参数期断言）+ `MANIFEST.yml`（五维） |
| `../commands.json` | 软件级 CLI 声明（R38/PF8：`type=tool`、`versions.ref=dma/0.14`） |
| `manifest.yaml` / `notes.md` | 元数据与本笔记 |

## 注意事项

1. **setuid 投递面在 OHOS 不可用**（四重墙 + 非 root + 位被剥离 + `/var` 不存在），**核心投递路径未纳入断言**。
2. `dma-mbox-create` 的运行期寻址由编译期宏 `LIBEXEC_PATH` 决定（Makefile 传 `-DLIBEXEC_PATH`，
   默认 `${PREFIX}/lib`）。本配方把它装到 `package_folder/lib/`，`cpp_info.bindirs` 同时暴露 `bin` 与 `lib`；
   **该二进制面向 root 建 mailbox 的场景，不纳入本包断言**（与第 1 条同源）。
3. `/etc` 只读 ⇒ 配方把 `dma.conf`/`auth.conf` 装进 `package_folder/etc/dma/`，
   **不触碰真实 `/etc/dma.conf`**；两条断言在 `dma.c:606 parse_conf` 之前，也不读配置。
4. `sendmail`/`mailq` 软链接（`Makefile:57-61`）**未创建** —— 它们依赖 `${SBIN}` 真实路径，
   而 `ln` 在 HMDFS 上有软链限制（`rm -f && ln -s` 语义），且本包断言面不涉及。
5. 上游 `install-spool-dirs`（`Makefile:63-65`，`-m 2775 -o root -g mail`）与
   `permissions`（`Makefile:67-70`，`chgrp mail`）**均不可执行**（`/var` ENOENT + `mail` 组缺失 +
   `chgrp` 命令不存在），已随 A/B 节一并披露。
## 路径 B 判定（create）与知识位归属

- **判定：`B判定=create`** —— 本 PR 的知识位 = **「setuid 投递型包在 OHOS 的四重安装墙 + 运行期不触发」**。
- **Issue：`#3837`**（标题 `【知识库扩展】dma 0.14：setuid 投递型包在 OHOS 的四重安装墙…（dma 0.14 实证）`，
  `https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3837`）。
- **草稿对（同 stem 成对）**：`knowledge/drafts/DRAFT-dma-0.14-setuid-install-four-wall.kv` +
  同名 `.md`（kv 内含四范围查重读数与全部 errno/行号证据）。
- **四范围查重（2026-10-08 实测）**：
  ① `经验文档/适配经验汇总.md` —— `setuid|setgid|suid|chown` **0 命中**；
  ② 知识图谱 `knowledge/graph/index.tsv` + `knowledge/doc/` —— word `setuid` 仅 `E453`（HMDFS mode 投影）、
  `setgid` 仅 `E011/E129/E533`（umask 临时目录），`mail|MTA|投递` 关键词行 **0**，均非本机制；
  ③ `经验文档/经验库/*.md` —— 命中是 `setgid` + `mktemp`/HMDFS 目录树语境（`05`/`12d`），非本机制；
  ④ `经验文档/OHOS行为探针清单.md`（43 行）+ `经验库/14-最终防错清单.md` —— `setuid|setgid|suid|chown|特权` **0 命中**。
- **一 PR 一知识**：本包另一处适配复用的 `E203`（OHOS musl 无 `getprogname()` → 用 `__progname`）
  **已是在册条目 ⇒ 对它只判 `hit`、仅作 cross-ref，⛔ 不占本 PR 知识位、不另写重复草稿**
  （补丁出处见上「编译期修复」节）。
---

**编译结束**: 2026-10-08 17:31
**最终状态**: built
