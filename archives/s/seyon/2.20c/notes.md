# seyon 2.20c 适配笔记

## 源码

- 来源：Debian main pool orig tarball（未施加 Debian delta）
  `https://deb.debian.org/debian/pool/main/s/seyon/seyon_2.20c.orig.tar.gz`
- sha256：`f221699ac420e55f0d769d4c50699a7e1552132cafe2a65192c3f3f090ca9048`
  （与 `seyon_2.20c-37.dsc` 中记录的校验和一致）
- 解包目录：`seyon-2.20c/`（`strip_root=True`）
- 上游构建系统：仅 `Imakefile`（imake/X11R5）

## 编译环境

- 构建系统：makefile（配方生成 `Makefile.ohos`）
- 编译器：clang 15.0.4（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- Profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / clang 15）
- 状态：built

## 编译步骤（配方内实际命令）

1. `sh makever.sh` → 生成 `version.h`（上游脚本，VERSION=2 / REVISION=20c）
2. `sh ad2c Seyon.ad > Seyon.ad.h` → 生成 app-defaults 的 C 字符串声明
   （上游 sed 过滤器；配方用 subprocess 捕获 stdout 写文件）
3. `yacc -d SeParse.y` → 生成 `y.tab.c` / `y.tab.h`；`mv y.tab.c SeParse.c`
4. 生成 `Makefile.ohos`：
   - `CC = <tools.build:compiler_executables.c>`（profile 给出
     `/data/service/hnp/bin/clang`）
   - `CFLAGS = -fcommon -O2 -I<各依赖 include> -I. -DHELPFILE=\"/usr/share/seyon/seyon.help\"`
   - `LDFLAGS = -L<各依赖 lib> -lXaw -lXmu -lXt -lXext -lX11 -lXpm -lICE -lSM -lxcb -lXau -lXdmcp`
   - 目标：`seyon`（全部 22 个 TU）、`libseyon.a`（除 `Seyon.o` 外的 21 个 TU）
5. `make -f Makefile.ohos -j1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `yacc`（bison 3.8.2）报 `SeParse.y:84: missing '"' at end of line`，不生成 `y.tab.c` | bison >= 3.0 会解析 yacc 文件尾声；`#ifdef TEST` 尾声里的 `input_str[]` 是多行字符串字面量 | 补丁 0001：用 `\n\` 续行把多行字符串拼成合法 C 字面量（与 Debian 01-debian-diff 同款修法） |
| 2 | `SeDecl.h:69: conflicting types for 'usleep'` | OHOS `<unistd.h>` 已声明 `int usleep(unsigned)`，SeDecl.h 又 K&R 声明 `usleep()` | 补丁 0002：删除 SeDecl.h 中的 `usleep()` 原型 |
| 3 | `SeDecl.h:126 / SeSupp.c:201: conflicting types for 'getline'` | OHOS `<stdio.h>` 声明 POSIX `ssize_t getline(char**,size_t*,FILE*)`；SeDecl.h 声明 K&R `getline()`，SeSupp.c 又定义 `getline(fp)` | 补丁 0002：本地 `getline` 重命名为 `seyon_getline`（声明 + `SeScript.c` 两处调用 + `SeSupp.c` 定义） |
| 4 | 链接报 `duplicate symbol: mlw` | `SeDial.c` 与 `SeTrans.c` 都对全局 `XfwfMultiListWidget mlw` 有暂定定义；现代 clang 默认 `-fno-common` | CFLAGS 加 `-fcommon`（1993 年代码依赖传统 common 符号合并） |
| 5 | `X11/SM/SMlib.h: No such file`（SeWin.c 经 libXt `X11/Shell.h`） | libXt 的 Shell.h 需要 libsm 的头文件 | 配方从**全部**依赖（含传递依赖 libsm/libice/libxcb/...）收集 include 路径 |
| 6 | test_package 编译报 `seyon/SeParse.h: No such file`；CMakeDeps 生成的 `seyon_INCLUDE_DIRS` 为空 | `package_type="application"` 时 Conan 把 require 默认 traits 设为 `headers=False/libs=False`（`requires.py::process_package_type`），消费者拿不到 include/lib | test_package 用 `self.requires(tested_reference_str, headers=True, libs=True)` 显式索取 |

## 源码修改（补丁）

- `patches/0001-separse-y-bison-multiline-strings.patch` — `SeParse.y` 尾声多行字符串（bison 兼容）
- `patches/0002-getline-rename-and-usleep-decl.patch` — `SeDecl.h`（删 `usleep()`、`getline`→`seyon_getline`）、`SeScript.c`（2 处调用重命名）、`SeSupp.c`（定义重命名）

未采用的改动：Debian 还补了 `SeGeneric.c`/`SeSubs.c` 的 `<time.h>`，本环境实测
clang15 无需（编译无错误），为最小化改动未纳入。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| libx11 | 1.8.13 | X11 核心 |
| libxaw | 1.0.14 | Athena 部件（主 UI，传递引入 libxmu/libxt/libxext/libxpm） |
| libxmu | 1.3.1.1 | X 杂项工具库 |
| libxt | 1.3.1 | X Toolkit Intrinsics |
| libxext | 6.4.0.1 | X 扩展库 |

## 测试

- **上游测试**：无。`Imakefile` 只有 `all/version/version.h/install/clean` 目标，
  无 `check`/`test`，源码树无 `tests/`、无测试脚本 → 上游用例 N=0
  （见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`）。
- **消费者测试（test_package）**：
  1. `test_seyon.c` — 链接包内静态库 `libseyon.a`，调用 seyon 的 yacc 脚本
     解析器 `ParseThis()`，断言解析出的函数名 `dial`、参数数 2、完成调用数 1
     （无头，无需 X display）。
  2. `test_seyon.sh` — 运行包内 `bin/seyon`（`-noemulator` + 空 DISPLAY），
     断言走到 libXt 打不开显示的错误路径（`Can't open display`，exit 1），
     即完整动态链接/运行冒烟；并检查包内产物（`libseyon.a`、头文件、
     `seyon.help`）、`DT_NEEDED`（libXaw/libXt/libX11）、以及对每个包内 ELF
     断言恰有 1 个 `.codesign` 段（fail-closed）。

## 验证结果

门禁命令（porting run，worktree 自带 `ci/conan/build_and_test.sh`）：

```sh
porting run --workspace $HOME/worktrees/deliver-seyon-2.20c \
  --expect-branch feat/seyon-2.20c --job-id seyon-verify-20261019-2 \
  --task-id t_seyon10518 -- \
  env CI_PACKAGES=archives/s/seyon/2.20c CI_REPO_ROOT=<worktree> \
  CONAN_PROFILE=$HOME/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  JUNK_PR_DIFF=<base...HEAD diff> zsh <worktree>/ci/conan/build_and_test.sh
```

`job.json`：`head_before == head_after`（同一提交），`exit_code=0`，`status=passed`。

门禁逐行结果：

```
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: seyon version/help failed        # non-blocking（seyon 无 --version/--help）
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Build Summary: Total 1, Success 1, Failed 0, Pass rate 100.0%
```

- `conan create` 通过：package revision `6cffc0a468e1be8b6bdbb3329eac35b9`，
  package_id `85b666b369f85d1e12dffd09f67543d888ff503d`。
- L1e 破坏性反向验证：移走 `bin/`/`lib/`/`include/` 后 `conan test` 失败 →
  “Negative test confirmed — test genuinely depends on seyon”（测试真依赖包产物）。
- 消费者测试：`test_seyon`（C）PASS —— `ParseThis` 解析 `dial(5551234, 9600);`
  → func=dial args=2 calls=1；`test_seyon.sh` 8/8 PASS
  （`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":8,"passedCount":8}`）。
- 上游测试：N=0（无测试套件）。

## 注意事项

- `-fcommon` 为必需项，不是可选优化。
- `bin/seyon` 无 `--version`/`--help` 选项；L2 冒烟按门禁逻辑走
  `--version`/`--help` 会失败（non-blocking），真实可执行性由 test_package 覆盖。
- 消费者测试的 `ParseThis()` 输入必须是**可变缓冲区**（扫描器 `scUngetChar`
  会回写），传字符串字面量会段错误。
