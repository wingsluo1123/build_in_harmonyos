# xsd 4.0.0 适配笔记（notes.md）

> 包目录：`archives/x/xsd/4.0.0/`　分支：`feat/xsd-4.0.0`　基线：`upstream/main @ b95978a4750e7aa9a3d49af148bb3bbedf81051d`
> 任务：ohpcd 平台 rawId=12194（开源鸿蒙PC专项积分赛）

## 0. 软件与交付面

Code Synthesis XSD 4.0.0（2014-07-21 发布）是 W3C XML Schema → C++ 的代码生成编译器，
产出两种静态类型 C++ 映射：

| 模式 | xsd 子命令 | 生成物 | 运行期依赖 |
|---|---|---|---|
| C++/Tree（常驻内存树，即 tree 模式） | `xsd cxx-tree` | `schema.hxx/.ixx/.cxx` | `<xsd/cxx/tree/…>`（头文件）+ Xerces-C++ |
| C++/Parser（事件流式映射，即 map 模式） | `xsd cxx-parser` | `schema-pskel.* / -pimpl.* / -driver.cxx` | `<xsd/cxx/parser/…>`（头文件）+ Xerces-C++ |

本包交付 `bin/xsd` + `include/xsd/**`（libxsd 运行期头）+ `share/doc/**`；
**没有 lib/**（libxsd 是头文件库），`package_info()` 因此把 `libdirs`/`libs` 清空。

## 1. W0 立项预检

### 1.1 版本可得性（源四路互证）

无 Git 上游，官方 tarball 是唯一权威发布物。选定
`https://codesynthesis.com/download/xsd/4.0/xsd-4.0.0+dep.tar.bz2`
（1642625 字节），sha256 `eca52a9c8f52cdbe2ae4e364e4a909503493a0d51ea388fc6c9734565a859817`，
四路互证（2026-10-06 实测）：

| 路 | 来源 | 读数 |
|---|---|---|
| ① | conan-center-index `recipes/xsd/config.yml` + `all/conandata.yml` | 版本 `4.0.0` → `folder: all`；sha256 同值 |
| ② | 官方目录随附 `xsd-4.0.0+dep.tar.bz2.sha1` | `ad3de699eb140e747a0a214462d95fc81a21b494`，与本地 `sha1sum` 同值 |
| ③ | Debian `xsdcxx` PGP 签名 dsc `xsd_4.0.0-10.dsc` / `-9.dsc` | Sha256/Sha1/md5 三段同值（orig tar 即同一 tarball 改名） |
| ④ | Yocto `meta-redhawk-sdr/recipes-deps/xsd/xsd_4.0.0.bb` | 同 URL + 同 `sha256sum` + 同 `md5sum` |

本地复算：`sha256sum`/`sha1sum`/`md5sum` = `eca52a9c…a859817` / `ad3de699…1b494` /
`ae64d7fcd258addc9b045fe3f96208bb`。

### 1.2 依赖双源（R35：必须用 conan download，不能只用 conan list）

唯一硬依赖 `xerces-c`（+dep tarball 的 README 原文："all its dependencies (except Xerces-C++)"，
即捆绑包**不**覆盖本依赖）：

1. `conan download "xerces-c/3.2.5" -r=ohpcd --only-recipe` → rc=0，rrev `9086fe3ffea711440f8f71d66d6ca6d0`；
2. `conan install … xerces-c/3.2.5 --build=never` → 命中并下载包
   `21b17f8b2bc0e9511e276e3d57a23893067cefe5`，`os=OHOS/os.version=6.0 arch=armv8 compiler=clang 15
   libc++=libc++ build_type=Release`、`shared=False fPIC=True`（静态）。

补充：`archives/x/xerces-c/3.2.5` 已在本仓库归档，`conan list -r=ohpcd "xerces-c/3.2.5:*"`
实测同一 OHOS armv8 二进制在线。⇒ 依赖面无缺口，不需要前置任务。

### 1.3 W0-3 平台可移植性（ISA / glibc printf 钩子）

对解包后全树（2797 文件）做正则扫描，**零命中**：

```sh
grep -rIl --include=*.c --include=*.cxx --include=*.h --include=*.hxx \
  -E 'altivec\.h|<mmx|3dnow|immintrin\.h|x86intrin\.h|<emmintrin|<xmmintrin|<arm_neon|__vectorcall' .
grep -rIn --include=*.c --include=*.cxx --include=*.h --include=*.hxx \
  -E 'register_printf_function|printf_function|<printf\.h>|__printf_function' .
# 两条均为 0 命中 ⇒ 无需编译探针，非死块档问题
```

架构档（profile `ci/conan/profiles/ohos-aarch64`）：`os=OHOS os.version=6.0 arch=armv8
compiler=clang 15 libc++=libc++ cppstd=17 build_type=Release`，`CC/CXX`
钉在 `/data/service/hnp/bin/clang{,++}`，三元组 `aarch64-unknown-linux-ohos`。

### 1.4 构建系统勘察（非 autotools）

`xsd-4.0.0+dep.tar.bz2` = Code Synthesis 自带 `build-0.3` make 体系 + 预生成配置：

- 根 `makefile` **没有 `configure`**；`xsd/build/configure` 是**交互式**对话脚本
  （zlib/ACE/XDR/boost/XQilla 五连问），但 `xsd/build/configuration-dynamic.make`
  已随包预生成为全 `n` ⇒ README 所称 "pre-configured … non-interactive mode" 成立；
- `build-0.3/system/configure` 走 **2009-09-18 版 `config.guess`**，设备实跑 rc=1
  （`uname -s = HarmonyOS` 不识别 + `$TMPDIR` 下 `cgXXXX/dummy.c` 不可写）——但
  `build-0.3/system.make` **没有任何 makefile include 它**，该路径本包不触发；
- 根 `makefile` 按 `MAKECMDGOALS` 分流：默认目标只 import 编译器子树
  （`xsd/xsd/makefile`），`clean|test|install|dist` 才 import 完整子树。

### 1.5 C++ 标准

`libcutl 1.8.1` / `libxsd-frontend 2.0.0` / xsd 本体是 2014 年代码（`std::auto_ptr` 等）。
profile 的 `compiler.cppstd=17` 会先产出 `-std=c++17`；配方把 `-std=c++11` 放进
`AutotoolsToolchain.extra_cxxflags`（在 `cxxflags` 属性里排在 `cppstd` 之后，clang 取最后一个），
与 CCI 配方一致。实测 c++11 下全量编译 0 error。

## 2. 实际踩到的两个真问题与修法

### 2.1 libc++ `<version>` 被上游 `version` 标记文件遮蔽（补丁 0001）

- **现象**：`libxsd-frontend/.../semantic-graph/elements.cxx` 等编译报
  `libcutl/version:1:1: error: expected unqualified-id`（内容 `1.8.1`）。
- **根因**：OHOS NDK libc++ 的 `<cstddef>` 第 42 行**无条件** `#include <version>`
  （实测 `-std=c++11/14/17/20` 四档全部如此）；而上游把 `libcutl/version`、
  `libxsd-frontend/version` 两个纯文本版本标记文件放在被 `-I` 的目录里
  （编译行实测含 `-I<src>/libcutl -I<src>/libxsd-frontend`）⇒ 标准库 `<version>`
  被同名文件遮蔽。最小复现：`clang++ -std=c++11 -I<含 version 文件的目录> -c t.cxx`
  （`#include <string>`）即报同样错误。libstdc++ 不从 `<cstddef>` 拉 `<version>`，
  所以 Linux/CCI 构建碰不到。
- **修法**：两文件改名 `version.txt`，并同步 `libcutl/makefile`（2 处）与
  `libcutl/cutl/makefile`（1 处）的 `dist` 目标引用——这三处只被 `dist` 目标消费，
  本包不构建 dist，改名对默认/`test`/`install` 目标零影响。`xsd/version` 不在任何
  `-I` 路径上（只有 `-I<src>/xsd/xsd`），无需处理。
- **验证**：三补丁对 pristine tarball `patch -p1` 与 `patch_ng apply(strip=0)` 双引擎全 rc=0。

### 2.2 libc++ 不从传递包含带出 `<ostream>`（补丁 0002）

- **现象**：`libxsd-frontend/xsd-frontend/semantic-graph/elements.cxx:298`
  `error: invalid operands to binary expression ('std::wostream' and 'const char *')`，
  且候选列表里**没有**成员 `operator<<(const void*)`。
- **根因**：该文件只拿到 `<algorithm>`（`elements.hxx` 只 include `<iosfwd>`），
  `basic_ostream` 尚不完整 ⇒ 成员候选不可见。最小复现：
  `clang++ -std=c++11 -fsyntax-only t.cxx`（只 include `<algorithm>`+`<string>`，
  函数体 `os << s.c_str()`）报同一错误；补 `#include <ostream>` 即过。
  libstdc++ 的传递包含会带出 `<ostream>`，libc++ 不会。
- **修法**：与**上游提交 `5029f8665190879285787a9dcdaf5f997cadd2e2`**（Boris Kolpackov，
  2015-10-23，"Add missing #include"）逐字同源，也即 CCI 的 `0002-missing-include.patch`。
  全量构建复核：打上该补丁后 0 error，只此一处。

### 2.3 Xerces-C++ 3.2 测试期望值过期（补丁 0003）

`encoding/char/{iso-8859-1,utf-8}`、`encoding/wchar` 三组用例断言超 BMP 字符引用
（`&#x10000;` 等）的处理结果，而 Xerces-C++ 3.2 起不再支持（Debian bug #881108）。
本包依赖 `xerces-c/3.2.5` ⇒ 必须打上游提交 `400651ba`（= CCI `0110-xerces-c3.2.patch`），
否则这三组必失败。**这是对上游测试期望值的修改**，PR 正文「上游测试用例修改说明」勾「是」并逐条列出。

### 2.4 补丁 strip 层级（工具面，已留 feedback）

`patch_ng.decode_clean()` **无条件**剥掉 `--- a/`、`+++ b/` 的一级前缀，再叠
conandata `strip: 1` 会把 `libcutl/version` 剥成 `version` →
`FileNotFoundError: <src>/version`。本包三个补丁统一 `strip: 0`；
系统 `patch -p1` 走 `-p1` 剥前缀，两面对同一目标文件，互不冲突。

## 2.5 配方 / test_package 层的三个真 bug（2026-10-06 重跑时实测）

上一会话在 `conan create` 的 tests 编译段被 SIGTERM 回收，`package()` **之后**的路径
（`package()` → `test_package` → 消费者断言）一次都没执行过；重跑一遍暴露三个真 bug，
全部修在配方侧，且都与平台无关（Linux/CCI 同样会踩）：

| # | 位置 | 现象（逐字） | 根因 | 修法 |
|---|---|---|---|---|
| 1 | `conanfile.py: package()` | `TypeError: chdir() missing 1 required positional argument: 'newdir'` | `conan.tools.files.chdir` 是 `(conanfile, newdir)` 的 contextmanager，写成了单参 `chdir(self.source_folder)` | 改 `chdir(self, self.source_folder)` |
| 2 | `test_package/conanfile.py: _dep()` | `ConanException: test_package: dependency 'xsd' not found` | `ConanFileInterface` **没有** `.name` 属性（名字在 `.ref.name`）⇒ `getattr(dep, "name", None)` 恒 `None`，每个依赖都被判"不存在" | 判据改 `dep.ref.name` |
| 3 | `test_package/test.sh` 四个断言辅助函数 | 同时出现 `not ok 1 - A1 …` 与 `ok 25 - F2 … (non-zero rc as expected)`（**`nok` 恒假绿**） | `ok()/nok()/out_has()` 的 `"$@"` **把描述字符串也当命令执行**（首词 `A1`/`B1` 全 not found）⇒ `ok` 恒 FAIL、`nok` 恒 PASS；`out_has` 又因错误信息回显整行描述而恒 PASS | 四个辅助函数一律先 `shift` 掉描述再执行命令 |

附带一条 Conan 语义：`xerces-c` 是 xsd 的**传递**依赖，而 Conan 2 只对**直接**依赖暴露
`package_folder`（实测传递依赖 `package_folder is None`、`cpp_info.includedirs` 停在相对形态
`['include']`）。test_package 要把生成代码真编译起来就必须拿绝对路径，故在 test_package 的
`requirements()` 里把同一版本 `xerces-c/3.2.5` 显式提为直接依赖——上游升版会以版本冲突报错，
不会静默用错版本。

修复后 `conan create` 干净全链 **rc=0**，test_package
`HMBS_TEST_SUMMARY discovered=44 passed=44 failed=0 skipped=0`。

## 3. 上游测试清点（§3.5）

入口：根 `makefile` 的 `test` 目标 → `xsd/tests/cxx/{tree,parser}`。

**候选数法（同一单位「上游测试用例」的四种数法，取最大值 79）：**

| 候选口径 | 命令 | 结果 |
|---|---|---|
| 顶层 `tests :=` 组注册数 | `grep -A20 '^tests :=' xsd/tests/cxx/{tree,parser}/makefile` | 33（tree 23 + parser 10） |
| 叶子测试目录（注册树展开） | 上述组递归展开 | 61（tree 32 + parser 29） |
| 测试可执行文件清点 | `find xsd/tests -name driver -o -name '*-driver'` + ELF 魔数 | 64（61 已建 + tree/binary 3 个） |
| **驱动执行次数**（`make test` 日志里每条驱动调用行） | 见 §4 | **79（tree 32 + parser 47）** ⇒ **N = 79** |

差额逐项归因：

1. **79 − 61 = 18**：`parser/validation/**` 下 7 个叶子目录带多份 `test-*.xml`
   （`all` 4 组、`choice` 5 组、`restriction` 6 组、`sequence` 7 组、`any`/`attribute`/
   `built-in/any-type` 各 1 组 = 25 次驱动调用，比"每叶子 1 次"的基线多 18 次）；
   另有 `parser/generated-impl/test-driver` 1 次。tree 侧 32 个叶子目录恰好 32 次
   （其中 `tree/built-in` 的 test 规则带 `cd $(src_base) &&`，在日志里是完整命令行形态，
   其余 31 个走 `$(call message,test …)` 的短形态）。
2. **64 − 61 = 3**：`tree/binary/{cdr,polymorphic,xdr}` 上游按 `xsd_with_ace`
   条件注册，+dep 包预生成 `xsd_with_ace := n` ⇒ **不进 `make test`**，不计入 N
   （需 ACE 库，属上游默认配置，非本包裁剪）。
3. **`xsd/tests/schema/list/driver.cxx` 不计入**：`tests/makefile` 只 import
   `cxx/makefile`，该文件不在注册树内，且是无断言的编译型夹具
   （`main()` 只做类型实例化）。
4. assertion 口径（`grep -c 'return 1'` 全 `tests/cxx` 驱动 = 127）是**另一单位**
   （一条用例含多条断言），按 §3.5「四种口径不得混用」不作 N，此处列出以备复核。

**本次运行：N′ = 79 = N，PASS 79 / FAIL 0 / SKIP 0 / NOT_RUN 0。**

## 4. 构建与验证命令

```sh
# 设备侧手工等价构建（W0 探针，独立于 conan）
make -j4                                   # 默认目标 = xsd/xsd/xsd
make -j4 test                              # 上游测试套件
# 采信轮（干净轮，唯一采信证据）
sh tools/conan_verify_round.sh xsd 4.0.0 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
```

实测（设备，2026-10-06）：默认目标 `PROBE_RC=0`（124 个 .o、0 error，297s）；
`make test` `PROBE_RC=0`（361.6s、61 个测试可执行文件、79 次驱动调用全绿、0 error）。

配方全链（与 conan-verify G2 同形，profile 绝对路径 + `--build=missing`）：

```sh
conan create "$PACKAGE_DIR" \
  -pr:h="$TARGET_REPO/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$TARGET_REPO/ci/conan/profiles/ohos-aarch64" \
  --build=missing --user=ohpcd --channel=stable
```

实测（设备，2026-10-06，干净构建缓存）：rc=0；日志含 `Calling build()` / `Apply patch` /
`RUN: make` 三类干净轮标志 6 行；`XSD_UPSTREAM_TEST_BINARIES=61`；79 次驱动调用全部 rc=0
（口径与取数命令见下）；`Package … built`；test_package
`HMBS_TEST_SUMMARY discovered=44 passed=44 failed=0 skipped=0`。

驱动调用计数用**不锚行首**的匹配（`make -j4` 下 clang 的告警行可能不带换行就把
make 回显的 `test …` 拼在同一行，锚 `^test ` 会少算 1–2 条——两轮干净轮的实测值
分别是 78 与 77，结构值恒为 79）：

```sh
# 1) make 回显的短形态：`test <out_base>/<leaf>/driver`（无参驱动）
#    与 `test <out_base>/<leaf>/NNN`（多 test-*.xml 的 validation 叶子）
grep -oE 'test /[^ ]*/tests/cxx/[^ ]+' reports/conan-create.log | wc -l    # 78
# 2) tree/built-in 的 test 规则带 `cd $(src_base) &&`，回显为完整命令行
grep -cE '^cd /[^ ]+ && /[^ ]*/driver ' reports/conan-create.log           # 1
# 合计 = 79，其中 tree 32（31 + cd 形态 1）、parser 47
```

`^test <dir>/NNN` 是 `$(call message,test …)` 的短形态，一条对应一次
`driver test-00N.xml | diff -u test-00N.std -`；无参驱动的 `test <dir>/driver`
一条对应一次驱动执行（rc 即判据）。

## 5. 已知限制 / 未覆盖

- `tree/binary/*` 三组未运行（上游 `xsd_with_ace=n`，需 ACE 库），见 §3 归因 2。
- `xsd/examples/**` 不在默认构建目标内（根 makefile 默认目标只到编译器）；
  `install` 会把示例**源码**装进 `share/doc/xsd/examples`（不编译）。
- `make dist` 目标未验证（本包不产出 dist；补丁 0001 改名后 `dist` 引用已同步，
  但未实跑 `make dist`）。
- `build-0.3/system/configure`（config.guess 2009 版）在设备上 rc=1，本包不触发该路径；
  若后续包复用同族 build 系统需单独处置（止损先例 #1 族）。
