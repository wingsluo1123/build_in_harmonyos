# yamcha 0.33 适配笔记

## 上游概况

yamcha 0.33（2005-09-05，Taku Kudo，LGPL-2.1）是基于 TinySVM 的监督式
分块（chunking）标注器，官方包采用 Autotools/libtool 老式构建，产物为：

- `libyamcha` 库（`src/Makefile.am`，`LTVERSION 3:0:2`，上游 soname
  `libyamcha.so.1`）；OHOS 上 2005 版 libtool 探测将 shared 判定为不可用
  （`checking if libtool supports shared libraries... no`），与
  `tinysvm/0.09` 先例一致，OHOS 包为 `static-library`；
- `yamcha` 命令行标注器（`bin_PROGRAMS`）；
- libexec 训练工具与脚本：`mkdarts`、`mktrie`、`pkemine`（C++）以及
  `mkmodel`、`mksvmdata`、`svm_learn_wrapper`、`mkparam`、`showse`、
  `zipmodel`、`selecttag`、`PKI.pm`、`PKE.pm`（.in 生成的 perl 脚本）。

官方 chasen.org 下载点已失效（返回 18KB 错误页），采用 macports 镜像
`https://distfiles.macports.org/yamcha/yamcha-0.33.tar.gz`，SHA256 为
`413d4fc0a4c13895f5eb1468e15c9d2828151882f27aea4daf2399c876be27d5`。

## OHOS AArch64 适配

### 1. 原生构建三元组识别（补丁 0001/0002）

2005 年版 `config.guess`/`config.sub` 无法识别 `aarch64:HarmonyOS` 三元组，
`config.sub` 甚至不识别现代 macOS（`-apple-darwin24.6.0`，本地宿主实证）。
补丁 0001 增加 `aarch64:HarmonyOS:*:*` 探测分支与 Darwin arm64 分支；
补丁 0002 在 `config.sub` 增加 `linux-ohos*` 内核-OS 组合、`aarch64` CPU
类型（含带厂商列表）与 `-linux-ohos*` OS 后缀。configure 最终得到
`aarch64-unknown-linux-ohos`（CI worker 本机构建）或
`aarch64-apple-darwin24.6.0`（本地宿主）；配方经 `conan.tools.gnu.
Autotools` 透传**真实**的 `--build`/`--host` 三元组（本地交叉构建为
build=darwin、host=linux-ohos），不做任何伪造/覆盖三元组。

### 2. libc++ C++11 make_pair 兼容（补丁 0003）

上游多处使用显式模板参数的 `std::make_pair<int,int>(左值, 左值)` 调用
（`feature_index.cpp`、`chunkersub.h`、`pkemine.cpp`）。libc++ 的 C++11
`make_pair(T1&&, T2&&)` 在显式指定模板实参后无法把左值绑定到右值引用，
编译报 `no matching function for call to 'make_pair'`。补丁移除显式模板
实参，交由模板推导生成相同类型，C++98 与 C++11+ 标准下均成立。宿主
macOS clang 与 OHOS clang 15 均验证通过。

## 依赖

- `tinysvm/0.09`（制品仓 ohpcd 已发布，2026-09-23）：configure 的
  `AC_PATH_PROGS(svm_learn, ...)` 硬检查 + `AC_MSG_ERROR`，训练与
  `make check` 均需真实 `svm_learn`；tinysvm 提供 `bin/svm_learn`。
  conan 2 的 host 上下文 requires 不会把 `bindirs` 注入构建环境
  （`VirtualBuildEnv` 仅遍历 build context 依赖），因此配方在
  `generate()` 用 `prepend_path` 显式把 tinysvm 的 `bin/` 加入
  conanbuild 的 PATH（保持系统 PATH 完整）。
- `perl`（>=5.004）：configure 硬检查；CI worker 有先例（openssl 配方
  经 perl Configure 构建通过）。
- `gzip`：configure 硬检查且训练管线用于压缩模型。制品仓无 gzip 配方，
  CI worker 是否预装未实证——若缺失，训练链路需改用环境内替代（留待
  CI 试跑确认，不阻塞本配方）。

## 构建布局（in-source）

`libexec/Makefile.am` 硬编码相对包含路径 `INCLUDES = -I../src`，只有
`srcdir == builddir` 时成立；`basic_layout` 的 out-of-source 目录
（build-release/）会在 libexec 子目录编译时把 `-I../src` 解析到
`build-release/src`（不存在）导致 `darts.h file not found`（本地实证，
CI worker 同样会触发）。配方 `layout()` 显式设置
`folders.source == folders.build == "."` 强制 in-source 构建，与上游及
宿主验证形态一致。

## 测试

上游 `tests/Makefile.am` 列出 4 个脚本（`TESTS = test1.sh test2.sh
test3.sh test4.sh`），`make check` 触发；每脚本执行：
训练（`training/Makefile` 调 svm_learn）→ `yamcha -m` 标注 test.data →
`conlleval.pl` 评分 → `mkmodel` 压缩模型 → 再标注评分。test2/4 使用
`DIRECTION=-B`，test3/4 使用 `MULTI_CLASS=2`。

配方在可运行目标上强制执行 `make check`（4/4 必须通过）；交叉构建时
跳过并记录。宿主原生验证（macOS clang 17，真实 svm_learn 取自本地编译
的 TinySVM-0.09）：`make check` 4/4 全部通过（test4.sh 示例输出
`accuracy 92.85%, precision 87.12%, recall 82.12%, FB1 84.55`），训练
→标注→conlleval 评分→mkmodel 压缩→再标注的完整链路实证成立。test_
package 额外覆盖安装后场景：

1. CLI 冒烟：`yamcha --version`（含 "0.33"）与 `--help`（含 usage）；
2. C API 消费者（C++）：链接安装后的 `libyamcha`，调用
   `yamcha_svm_new()`（错误路径）+ `yamcha_svm_strerror()` 验证库
   加载、符号解析与真实代码执行（C API 6 个断言 + CLI 3 个断言，共 9）。

最终验证命令：

```bash
conan create archives/y/yamcha/0.33 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 构建注意

- HarmonyOS HMDFS 不支持 GNU make jobserver FIFO，目标端固定
  `make -j1`；其他系统按可用 CPU 数并行。
- 宿主验证（macOS clang）：configure + make + `yamcha --version/--help`
  冒烟全部通过（见 0001/0002 的必要性实证）。
- `configure` 会检测 `-lm`（`AC_CHECK_LIB(m, pow, M_LIBS="-lm")`），
  配方 package_info 声明 `system_libs = ["m"]`。
- 本地交叉构建（macOS → OHOS）：`conan create . -pr:h=/tmp/ohos-local
  -pr:b=/tmp/macos-build`，本地 profile 将
  `tools.build:compiler_executables` 指向
  `/Users/metyierzhen/ohos-toolchain/clang(.++)`（包装脚本已带
  `--target=aarch64-linux-ohos --sysroot`）；build profile 需在
  buildenv 加 `LD_LIBRARY_PATH=+(path)<SDK>/native/llvm/lib`（lld 依赖
  libxml2.so.16）。configure+make+package+test_package 编译全绿，交叉
  运行类测试按 `can_run()` 跳过。

**编译结束**: 2026-09-30

## 知识草稿（路径 B，与本次适配同 PR）

本次适配沉淀两对可复用知识草稿（`knowledge/drafts/`，均成对 .kv + .md）：

1. **DRAFT-yamcha-0.33-legacy-libtool-shared-probe-no** —— 2000s 老 libtool
   在 OHOS 交叉下共享库能力探测确定性失败（config.log `result: no` 三连），
   conan 配方须按 static-library 定型；撞车判定：E236/E457 均为消费侧、
   cdcd E688 为探测名失配族，未覆盖本机制。
2. **DRAFT-yamcha-0.33-conan-buildenv-path-injection** —— conan 2
   VirtualBuildEnv 不注入 host 依赖 bin（configure AC_PATH_PROGS 找不到
   svm_learn 实证），须 generate() `prepend_path` 注入；`define_path`
   覆盖语义清空系统 PATH（sed/chmod not found 实证）、`run=True` 无效
   均写入 forbid；similar_to cdcd E688 / E232。

两条的 error_signature 均来自真实日志（config.log 与 create 迭代日志），
verification_cmd 可复算，适用于后续任何老 autotools + OHOS 交叉适配。

## CI 原生构建修复（confstat umask，PR #14172）

CI worker（OHOS 原生 host==build）在 `conan-build-test` 失败：configure
通过（libtool shared 探测在原生环境为 yes、perl/svm_learn/gzip 均找到），
但 **config.status 创建 `confstatXXXXXX` 临时目录时 `umask 077` 落成
`drwx--S---`（HMDFS 组位不可遍历），写入 `subs.sed`/`out` 全部
`Permission denied`** → 各 Makefile 未生成 → `make: No targets specified
and no makefile found`。本地 macOS 交叉构建因宿主文件系统不触发此问题，
CI 原生 OHOS 才暴露（cdcd 0.6.6 同款，E011/E206 族）。

修复：新增 `0004-umask-000.patch`，把 configure 中创建 confstat 临时目录
的两处 `umask 077` 改为 `umask 000`（`mktemp` 分支与 `mkdir` 回退分支），
与 cdcd 0002 补丁同模式。补丁在干净 tarball 树 `git apply --check` 通过，
两处行号（22315/22320）均实证替换。

验证命令（CI 重跑即可复算）：

```bash
# 干净源码树
tar xzf yamcha-0.33.tar.gz
git apply --check archives/y/yamcha/0.33/patches/0004-umask-000.patch
# 应用后确认
grep -n "umask" configure   # 两处均为 umask 000
```

**修复提交**: 2026-10-10（0004 补丁 + conandata/manifest/notes 同步）

## C API 异常穿透修复（0005，PR #14172）

0004 行号修正（bfd7d3e325，hunk 22315→22312，diff 重新生成）后 CI 走通
configure + make + **make check 4/4（accuracy 93.70/93.50/93.05/92.88%）**
+ package，卡在 test_package 运行时：

```
RUN: "./yamcha_api_test"
libc++abi: terminating due to uncaught exception of type std::runtime_error:
SVM::open(): Mmap::open(): definitely-not-a-yamcha-model : open() failed
Signal 6 (core dumped)
```

根因是**上游 C API 契约违背**：`yamcha_svm_new` 文档/头文件语义是"打开失败
返回 NULL 并可通过 `yamcha_svm_strerror` 取错误"，但 `SVM::Impl::open` 在
`Mmap::open` 失败时 catch 后 **rethrow `std::runtime_error`**（svm.cpp
`throw std::runtime_error(_what)`），异常越过 `if (!ptr->open(file))` 的
bool 检查、穿透 `extern "C"` 边界 → libc++abi terminate 直接崩进程。
本地 macOS 交叉构建 `can_run()=False` 跳过运行时断言所以未暴露；CI 原生
OHOS 环境首跑即复现——这正说明 test_package 运行时断言的价值。

修复：新增 `0005-c-api-try-catch.patch`，把 `ptr->open(file)` 包进
`try/catch (std::exception&)`，异常路径与既有失败路径一致：设置
`errorStr = "yamcha_new(): " + e.what()`、释放资源、返回 NULL。
行为与上游失败契约完全对齐（错误串含 `yamcha_new` 与 `open`，test_package
断言 1/3/4 均覆盖）。

验证：干净 tarball 树 5 补丁串行 `patch -p1 --dry-run` 全过；补丁后
`clang++ -fsyntax-only src/libyamcha.cpp` 通过。语义级运行验证由 CI
原生 test_package（yamcha_api_test 9 断言）承担——本机 macOS 无 OHOS
运行环境且宿主 TinySVM 老 configure 无法在本机重建（segfault），不重复
宿主链路。

**修复提交**: 2026-10-11（0005 补丁 + conandata/manifest 同步）
