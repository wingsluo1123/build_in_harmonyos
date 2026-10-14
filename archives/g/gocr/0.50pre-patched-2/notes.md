# gocr 0.50pre-patched-2 适配笔记

> 适配对象：OSRA 项目发布的上游 patched GOCR 快照 `gocr-0.50pre-patched-2.tgz`
> （<https://sourceforge.net/projects/osra/files/gocr-patched/>）。
> 适配动机：OSRA 2.2.4 的 `configure.ac` 无条件要求 `libPgm2asc`（`AX_TRY_LINK([Pgm2asc], ...)`），
> 而制品仓与仓库中均无该库；本包先把该依赖补齐（W0/R36 拓扑序：gocr → graphicsmagick → osra）。

## 编译环境
- 构建系统: autotools（上游自带生成的 configure，autoconf 2.57）
- 编译日期: 2026-10-13
- 编译器: clang/clang++ 15.0.4（`/data/service/hnp/bin/clang`，target aarch64-unknown-linux-ohos）
- 平台: HarmonyOS PC (aarch64)，Conan 2.29.1，profile `ohos-aarch64`（ohos-sdk 26.0.0.18）
- 状态: built（conan-verify G0-G4 + L2/L4/L5 全通过，未 upload）

## 上游测试清点与实跑（R51）

上游没有 ctest/make check 套件；测试资产是 `examples/` 下的样例图 + 同名 `.txt` 期望输出，
驱动脚本为 `bin/gocr_chk.sh`（shell 脚本，PNG/JPEG 样例需 netpbm 的 `pngtopnm`/`djpeg`，
本镜像刻意不装 netpbm）。清点结果：**7 组**样例（6 个 PNG + 1 个 JPG）。

实跑方式（等价、可复现）：用纯 Python 解码 PNG 为 PGM（本镜像无任何图像转换工具），
再用**打包后的** `bin/gocr` 逐个识别并与期望文本逐字符比对：

| # | 样例（上游 examples/） | 期望文件 | 结果 | 期望字符数 | 逐字符错误 |
|---|---|---|---|---|---|
| 1 | 4x6.png → 4x6.pgm | 4x6.txt | 非全等 | 81 | 22 |
| 2 | 5x7.png → 5x7.pgm | 5x7.png.txt | **全等** | 81 | 0 |
| 3 | 5x8.png → 5x8.pgm | 5x8.png.txt | **全等** | 81 | 0 |
| 4 | ocr-a.png → ocr-a.pgm | ocr-a.txt | 非全等 | 92 | 2 |
| 5 | ocr-a-subset.png → ocr-a-subset.pgm | ocr-a-subset.png.txt | **全等** | 88 | 0 |
| 6 | ocr-b.png → ocr-b.pgm | ocr-b.png.txt | **全等** | 96 | 0 |
| 7 | handwrt1.jpg | handwrt1.jpg.txt | 未运行（本镜像无 JPEG 解码器） | — | — |

**实测：6/7 组可运行，4/6 全等（66.7%），字符准确率 95.38%（24 bad / 519 chars）。**
未全等的两组是上游公认的难例：`4x6`（最小字号）与 `ocr-a`（整幅字母表末尾多出 `_` 标记）。

## 编译步骤

```bash
# conan create 内部（配方 build()）实际执行的等价命令：
sh configure --without-netpbm ac_cv_func_setvbuf_reversed=no \
    --prefix=/ --bindir=/bin --libdir=/lib --includedir=/include \
    CC=clang CXX=clang++
make -j1          # 上游 default target：只编 gocr CLI
make -j1 libs     # ← OSRA 真正需要的 libPgm2asc.a
```

要点：
1. `make` **不**构建库；必须显式 `make libs`（`src/Makefile.in` 里 `all: $(PROGRAM)`，`libs: libPgm2asc.a`）。
2. `--without-netpbm`：netpbm 只被 CLI 用来把 PNG/JPEG 转成 PNM；OSRA 用库 API 直接喂位图，故可关掉且不产生依赖。
3. `ac_cv_func_setvbuf_reversed=no`：configure.in 用 `AC_FUNC_SETVBUF_REVERSED`（`AC_TRY_RUN`），交叉构建下不能跑目标程序，预置该 cache 变量。
4. **in-source 构建**：上游手写 `Makefile.in` 无 VPATH 支持，out-of-source 时 make 报
   `No rule to make target 'Makefile.in', needed by 'Makefile'` → `basic_layout(self, build_folder=".")`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 退出码 0，但 Makefile/config.h 只写出一半；日志 `can't create ./confstatXXXXXX/subs.sed: Permission denied` | autoconf 的 config.status 先 `umask 077` 再 `mktemp -d ./confstatXXXXXX`；HMDFS 的 UID 映射/挂载语义使 0700 临时目录对写入进程不可写（E011） | `patches/0001-configure.patch` 把 configure 里两处 `umask 077` 改为 `umask 022`（与 potrace/libx11/libmtd 同法） |
| 2 | `make` 报 `No rule to make target 'Makefile.in', needed by 'Makefile'` | conan 的 `basic_layout()` 默认 build 目录是 `build-<build_type>`；gocr 手写 Makefile.in 的规则用相对路径引用 `Makefile.in`，不支持 out-of-source | 配方改用 in-source 构建：`basic_layout(self, build_folder=".")` |
| 3 | `conan download/get` 报 `BadZipFile: File is not a zip file` | SourceForge 的 `/…/download` 跳转 URL 无扩展名，conan 无法据此判断压缩格式，按 zip 解压 | conandata.yml 改用官方直链 `https://downloads.sourceforge.net/project/osra/gocr-patched/gocr-0.50pre-patched-2.tgz`（保留 `.tgz` 扩展名，sha256 不变） |
| 4 | 上游 Makefile 的 `ln -s libPgm2asc.0.50.so libPgm2asc.so` 失败（Permission denied） | HMDFS 拒绝创建软链接（E018）；上游该步已用 `-` 前缀忽略 | 静态库默认（shared=False）；shared=True 时由 `package()` 复制一份实体 `libPgm2asc.so` 而不是软链接 |
| 5 | 真机内核拒绝 execve 任何 shebang 脚本（`/bin/sh: …/configure: Permission denied`） | 本机（OHOS hmmac）只允许执行 ELF，脚本必须以「解释器 + 脚本」形式调用 | 环境侧 shim 把 conan/Autotools 的 `".../configure" args` 重写为 `/bin/sh ".../configure" args`；配方本身保持标准写法（CI 在 Linux 上不受影响）——见「注意事项」 |

## 源码修改

- `patches/0001-configure.patch`：`configure` 中两处 `umask 077` → `umask 022`（2 行，portability/platform-only），
  由 `refresh-patch --auto` 依据 .work/.orig 差分生成。

## 依赖版本

无外部依赖（`requirements()` 为空）：
- netpbm 关闭（`--without-netpbm`），故不引入 netpbm/png/jpeg。
- libm/libpthread 由 OHOS libc 提供，链接 make 未产生额外 `-l`。

## 验证结果

```bash
$ conan create archives/g/gocr/0.50pre-patched-2 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
======== Testing the package: Executing test ========
  [PASS] job_init() sets src.fname to "-"
  [PASS] job_init() sets cfg.certainty to 95
  [PASS] job_init() defaults cfg.out_format to UTF8
  [PASS] job_init_image() leaves the box list empty
  [info] pgm2asc(): 1 text line(s), 1 box(es)
  [PASS] pgm2asc() segmented and recognized the bitmap
  [info] first recognized line: "H"
  [PASS] getTextLine() returns the recognized character "H"
  [PASS] decode(L'A', UTF8) returns "A"
  [PASS] PGM pattern file can be created
libPgm2asc consumer test: PASSED
gocr wrote gocr_test_pattern.pgm.txt           # CLI 端到端：识别出同一个 "H"

# 上游样例实跑（打包后的 bin/gocr）
TOTAL 4/6 exact-match, char accuracy 95.38% (24 bad / 519)
```

conan-verify 8 道门禁：G0 PASS / G1 PASS / G2 PASS（干净构建 + test_package）/ G3 系统同名库隔离 PASS /
G4 产物完整性 PASS / L2 smoke PASS / L4 checksec PASS / L5 产物基线 PASS。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/gocr | 432576 B | OCR 命令行工具（上游 default target 产物） |
| lib/libPgm2asc.a | 592678 B | OSRA 链接所需的静态库（`-lPgm2asc`） |
| include/pgm2asc.h, gocr.h, list.h, output.h, pnm.h, unicode.h, config.h | — | 平铺安装，供 OSRA 以 `<pgm2asc.h>` / `<gocr.h>` 直接包含 |

## 两个变体都实测过

```bash
# 默认（静态）
$ conan create archives/g/gocr/0.50pre-patched-2 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
libPgm2asc consumer test: PASSED        # 8/8 断言

# 动态
$ conan create archives/g/gocr/0.50pre-patched-2 … -o "gocr/*:shared=True" …
gocr/0.50pre-patched-2: RUN: make -C src libPgm2asc.0.50.so -j1
libPgm2asc consumer test: PASSED
```

> `.so` 规则只存在于 `src/Makefile`（顶层 Makefile 无该 target），故 shared 分支用
> `make -C src libPgm2asc.<ver>.so`；上游该规则末尾的 `ln -s` 在 HMDFS 上失败，但已用 `-`
> 前缀忽略（E018），因此在 `package()` 里复制一份实体 `libPgm2asc.so` 作为链接名。

## 注意事项

1. **头文件平铺**：上游 `make install` 会把头装到 `include/gocr/`，但 OSRA 的 `configure.ac`
   以 `#include <pgm2asc.h>`/`<gocr.h>` 探测并要求 C++ 侧自己 `extern "C"` 包裹；本配方
   `package()` 手动把头文件平铺进 `include/`，以满足该消费约定。
2. **位图所有权**：`job_free_image(job)` 会 `free(job->src.p.p)`。调用方必须用 `malloc`
   分配位图（OSRA 亦如此）；传栈/静态数组会 SIGSEGV。test_package 里刻意用 `malloc` 复现该契约。
3. **脚本执行限制（本机特有，不入 PR）**：本 HarmonyOS 镜像内核拒绝 `execve` 任何 shebang 脚本，
   而 conan/Autotools 会直接执行 `configure`/`config.status`/`libtool`/`install-sh`。本地
   `finish`/`conan create` 需在 `PYTHONPATH` 前置会话 shim（把「脚本首 token」重写为
   「解释器 + 脚本」）才能跑通；CI 在 Linux worker 上不存在该限制，配方本身保持标准写法。
4. 本包是 OSRA 的**前置依赖**，需先合入并发布 `gocr/0.50pre-patched-2`，OSRA 的 PR 才能通过 R36/PF4 依赖闸。
---

**编译结束**: 2026-10-13 17:55
**最终状态**: built
