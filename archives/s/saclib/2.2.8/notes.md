# saclib 2.2.8 适配笔记

## 结论摘要

- **状态**：✅ **真机 `conan create` 通过（exit 0）**，`test_package` 15/15 断言全过。
  设备：HarmonyOS / aarch64 / clang 15，隔离 job `$HOME/ohos-users/saclib/2.2.8-first`，
  runner RUN_ID `saclib-saclib-saclib-2.2.8-conan-create-20261014-180718-49053`。
- 产物：`lib/saclibo.a` + `lib/libsaclib.a`（各 1987208 字节，1069 个成员，含 `GC.o`）+
  7 个头文件（含 `sysdep.h`），settings `os=OHOS arch=armv8 compiler=clang
  compiler.version=15 build_type=Release`。
- **适配中真正困难的一点**：AArch64 版 `GC()`。第一版按上游 x86_64 的“哑参数落栈”写法，
  在 `-O0` 下 6/6 通过、在 `-O1/-O2/-Os` 下 18/18 全部段错误；改用 `setjmp()` 强制溢出
  被调用者保存寄存器后 **24/24 全通过**（-O0/-O1/-O2/-Os 各 6 次）。详见 §6.2。
- **下游**：本包是 `qepcad/1.74` 的硬依赖，qepcad 的 PR 正等它发布（R36）。

## 1. 上游与源码

上游主页 `https://www.usna.edu/Users/cs/wcbrown/saclib/`（Christopher W. Brown，USNA）。
上游**不通过任何代码托管平台发布源码包**；该 release tar 包由 SageMath 上游镜像与 Debian
源码归档共同再分发，Debian/Fedora 的 `saclib` 包也用它构建。

```
https://deb.debian.org/debian/pool/main/s/saclib/saclib_2.2.8.orig.tar.gz
sha256 E8E3ACB253C64394F35C8E17942F764CAE34DF731F3FE3D749B6A2AE1FB8203B   3060308 字节
```

**溯源证据（镜像等价，三重一致）**：

1. 三个独立官方来源分别下载并比对完整 sha256，全部为 `E8E3ACB2...203B`、同一大小、同一版本：
   `files.sagemath.org`、`mirrors.mit.edu`、`deb.debian.org`；
2. 实际使用 `deb.debian.org`：它是 **CI Worker 已知可达**的镜像 —— main 上 563 个配方在用，
   也是 `ftp.gnu.org` 等不可达主机的既有兜底；`mirrors.mit.edu` 仅 4 例。
   本轮首个 CI 运行在 `checkout-pr` 阶段因 Worker 下载 PR diff 失败而中止，故按同一网络约束
   复核了源码主机（详见 §6.5）；
3. **不涉及版本替换或重新打包**：同一份上游 tarball 由三个镜像提供；
4. 解包顶层目录 `saclib2.2.8/`，含 `src/`（1068 个 `.c`）、`include/`、`bin/`（生成器）、
   `sysdep/`（平台端口）、`doc/`。

> 任务页版本号 `2.2.8` 即上游 `SACLIB 2.2.8`，与 tar 包版本一致，无版本推断。

## 2. W0 依赖发布检查

| 依赖 | 需求来源 | 状态 |
|------|----------|------|
| 无 | SACLIB 是纯 C 库，只使用 libc + libm，不链接任何第三方库 | ✅ 无依赖阻塞 |

- 配方**不声明任何 `requires()` / `tool_requires()`**，所以不存在“依赖未发布”的拆库问题。
- 本机 `conan download/list -r=ohpcd` 不可用（`system acceleration policy not enabled`，
  本机对 conan.cnb.cool 不可达），**远端结论必须在真机复核**（命令见 §7）。
- SACLIB 自身是依赖链的**最底层**：`qepcad/1.74 → saclib/2.2.8`，按拓扑序应先发布本包。

### 2.1 下游契约（必须保持，否则 qepcad 会断）

`qepcad/1.74` 的 `qesource/source/Makefile` 与 `qesource/cad2d/Makefile` 直接使用：

```make
INCLUDES = -I${saclib}/include ...
EXTLIBS  = ... ${saclib}/lib/saclibo.a -lreadline ...
```

因此本包必须提供：

1. `include/` 下全部头文件；
2. **`lib/saclibo.a` 这个确切路径**；
3. 必须是**静态库** —— qepcad 在 `qesource/source/saclib/` 下重定义了 `CREAD`、`GCSI`
   等同名符号，动态库无法满足扩展归档的重定位需求（Debian 打包同样只提供 `.a`）。

配方同时安装 `lib/saclibo.a`（上游命名，qepcad 用）与 `lib/libsaclib.a`（常规命名，
支持 `-lsaclib` 与 CMake target），`cpp_info.libs = ["saclib"]`。

## 3. 构建系统分析

SACLIB **没有** `configure` / `CMakeLists.txt` / `meson.build`，只有自己的生成器：

```
bin/sconf <port>       bash 包装：perl $saclib/bin/mksysdep.pl <port>
bin/mksysdep.pl        诊断 CPU/OS 或接受显式端口名，调用 sysdep/<port>/install
sysdep/<port>/install  实际只做两件拷贝：GC.c -> src/，sysdep.h -> include/
bin/mkproto            由 src/*.c 重新生成 include/sacproto.h（跳过 FAIL.c 与 main.c）
bin/mkmake             生成 lib/objo/makefile（对象列表 + 依赖规则）
bin/mklib opt          在 lib/objo 里 make CC=$CC SACFLAG= EXTENSION=o 并归档为 lib/saclibo.a
```

上游 README 的安装流程是 `sconf → mkproto → mkmake → mklib all`。

### 3.1 平台相关性只集中在两处

在整个 `src/` + `include/` 中检索平台宏，只有 `include/hfloats.h` 使用
`_SPARC_SOLARIS_` / `_X86_LINUX_` / `_MAC_OSX_`，且只用来决定 `#include <ieee754.h>`
与 `rounddown()/roundup()` 的实现。其余平台差异全部由 `sysdep/<port>` 提供：

| 文件 | 作用 | 是否随 tarball 提供 |
|------|------|---------------------|
| `sysdep.h` | 端序 / 字长 / 平台宏 | 否，由端口提供 |
| `GC.c` | `GC()`：把活跃寄存器落栈后调用 `GCSI()` | 否，由端口提供 |
| `src/CLOCK.c` | `getrusage(RUSAGE_SELF)` | 是（上游通用 POSIX 实现） |
| `src/DPR.c` / `DQR.c` / `FAIL.c` / `FPCATCH.c` | 通用实现 | 是 |

已核对：`GC.c` 是**唯一**缺失的源文件（`src/` 下没有），`FPHAND.c`/`flush.s` 只在
`solarisSparc` 端口出现，其他端口不需要。

### 3.2 为什么不能直接复用 `sysdep/linuxX86_64`

1. **`sysdep.h`**：它定义 `_X86_LINUX_`，于是 `hfloats.h` 会 `#include <ieee754.h>`。
   该头文件是 glibc 专有；OHOS 的 libc 是 musl 系，没有它。而且它承载的
   `ieee_rep` 位域布局是 x86 的，AArch64 上也不成立。
2. **`GC.c`**：它声明 16 个 `register int` 并一次性传给 `gc_dummy()`，靠
   System V AMD64 的 16 个参数寄存器把值落到栈上。AArch64/AAPCS64 只有 8 个参数寄存器
   （x0–x7）加 x8–x18 临时寄存器，同一构造必须重新推导。
3. **`mksysdep.pl` 根本不认识 AArch64/OHOS**：`uname -mp` 返回 `aarch64`、
   `uname -s` 返回 `OpenHarmony`，两个判断都落到 `unknown`，于是**静默不安装任何端口文件**，
   表现为后面链接时报 `GC` 未定义（`GCSI` 由 `GCSI.c` 提供，但 `LIST1`/`LIST2`/`ISUM`
   等都会调用 `GC`）。

### 3.3 新增端口 `sysdep/ohosAarch64`

按上游 `sysdep/README` 指定的移植方式新增（该 README 明确写着：新增端口就是加一个
`sysdep/<target>` 目录并让 `sconf` 认识它）：

- `sysdep/ohosAarch64/sysdep.h`
  ```
  #define _LITTLE_ENDIAN_
  #undef  _BIG_ENDIAN_
  #define _OHOS_AARCH64_      /* 不定义 _X86_LINUX_ => 不引入 ieee754.h */
  #define __WORDSIZE 64
  ```
- `sysdep/ohosAarch64/GC.c`：AAPCS64 版 `GC()`。**用 `setjmp()` 强制把被调用者保存寄存器
  （x19–x28）写进栈帧**，再把 `GC()` 自身局部变量的地址作为 `EACSTACK` 交给 `GCSI()`，
  使其扫描范围覆盖调用者的 red zone。为什么不能用上游 x86_64 的“哑参数落栈”写法，
  见 §6.2 的真机实测数据。
- `install` / `cleanup`：与上游其他端口同构的拷贝/清理脚本。
- `bin/mksysdep.pl`：新增 `aarch64` 处理器识别、`OpenHarmony|OHOS` 系统识别，
  并接受显式参数 `ohosAarch64`。

### 3.4 `AFLAGS` 的 `-P` 与 `AR`/`RANLIB`（第二个补丁点）

`bin/mkmake` 生成的 makefile 里 `AFLAGS = -I${saclib}/include -P`。`-P` 是 GNU as 的
预处理选项，**AArch64 的 `as` 没有 `-P`**。SACLIB 2.2.8 的 `src/` 已无任何 `.s`
（`sysdep/linuxX86` 时代的遗产），Debian 打包也直接去掉了该选项。

补丁把 `AFLAGS` 参数化（`${AFLAG}`），并让 `bin/mklib` 像传 `SACFLAG` 一样传 `AFLAG=-ansi`，
这样任一端口的汇编源仍可编译（`-ansi` 只跳过 C 预处理），同时保留了可覆盖性。

同一处还把 `AR`/`RANLIB` 变成可传入：生成的 makefile 硬编码 `AR = ar` / `RANLIB = ranlib`，
而 **OHOS 的 clang 工具链根本没有 `ranlib`**（只有 `llvm-ranlib`，`ar` 也不是工具链归档器）。
`mklib` 原本只把 `CC` 转发给 make，现在把 `AR`/`RANLIB` 一并转发；配方再从 profile 的
`tools.build:compiler_executables` 取绝对路径传入（见 §6.3）。

### 3.5 `sacMain` 弱符号（第三个补丁点）

`src/main.c` 定义强符号 `main()`，其唯一职责是调用可选钩子 `sacMain()`。全库没有其他
目标文件引用 `main` 或 `sacMain`，所以归档成员通常不会被拉入；但只要消费者**自己引用
了 `main`**（例如 `--whole-archive`，或使用 SACLIB 自带 `main()` + 自定义 `sacMain()`），
就会出现「重复定义 `main`」或「`sacMain` 未定义」两种断链。

补丁给 `include/sacsys.h` 加上 `__weak` 宏，并把 `main.c` 里的
`extern int sacMain P__((int ac, char **av));` 改为弱声明。这也正是
Debian/Fedora `saclib` 包所做的处理（`debian/patches/saclib-attr.patch` 的 `__weak` 部分）。

### 3.6 配方相对上游 README 的两处精简（均有证据）

| 上游步骤 | 本配方 | 证据 |
|----------|--------|------|
| `bin/sconf` | 直接 `perl bin/mksysdep.pl ohosAarch64` + `sh sysdep/ohosAarch64/install` | `sconf` 全部内容就是 `perl $saclib/bin/mksysdep.pl "$1"`。`mksysdep.pl` 内部用 `system("bash -c ...")` 执行 install，**PATH 里没有 `bash` 时会静默什么也不做**；本机复现了这一静默失败，故改为显式执行 install，并在 `build()` 中断言 `src/GC.c`、`include/sysdep.h` 存在，让缺失端口直接构建失败而不是产生缺 `GC()` 的库 |
| `bin/mkproto` | 不执行 | tarball 自带 `include/sacproto.h`，用上游 `bin/mkproto` 从同一份源码重新生成后**逐字节一致**（sha256 `A637432FB97094C8036050B11D46ED5BAADD6B501C0D00B725BCF68A07E578CA`，1063 行）。重新生成不可能改变结果，跳过它可让构建环境不必依赖 awk |

另外补充一个上游流程事实：`mkproto` 会跳过 `FAIL.c` 与 `main.c`，所以 `sacMain` 的前向
声明只存在于 `main.c` 内部（这也是 §3.5 的补丁只能改 `main.c` 的原因）。

### 3.7 `package_type` 与 R26

本包为静态库（`package_type = "static-library"`），不产出 `.so`，不存在 R26
「系统同名库静态化」的风险面。

## 4. 测试设计

### 4.1 上游测试清点（结论：**零测试设施**）

按四类入口逐一清点，全部为空；这不是"没找到"，而是上游确实没有：

| 清点项 | 命令/范围 | 结果 |
|--------|-----------|------|
| `check` / `test` / `tests` / `unittest` 目标 | 全树 `Makefile`、`makefile`、`*.mk` | **0 条** |
| `tests/`、`test/`、`spec/`、`unittest/` 目录 | 全树 | **0 个** |
| CTest / `add_test` / `AC_INIT` / `pytest` / `assert(` 痕迹 | 全树 | **0 处** |
| `src/` 下除默认入口外的测试驱动 | `int main(` | **0 处**（仅 `src/main.c` 的默认 `main`） |

`bin/` 下 27 个文件全部是代码生成器与文档工具（`mkmake`/`mklib`/`mkproto`/
`mktexkwic`/…），没有测试运行器；`doc/user_guide/Makefile` 只构建 LaTeX 文档。

因此 `upstream_test_in_build: false`、`upstream_tests: []`，**不虚报上游测试通过率**
（口径：上游测试 `0/0`，N/A）。

**唯一可运行的上游产物**是 `doc/user_guide/sample.c`（32 行，读入两个整数做乘法循环），
它也是上游唯一使用 `sacMain()` 钩子的代码。已真机实跑并核验数值：

```
输入 12345678901234567890 × 98765432109876543210，循环 5 次
输出 1219326311370217952237463801111263526900
```
与 `python3` 独立计算逐位一致（20 位 × 20 位精确乘积）。该产物现已纳入 `test_package`
（`test_package/sample.c` 为逐字节副本，`test.sh` 断言乘积与循环计数），因此顺带验证了
`patches/0002` 的 `sacMain` 弱符号链。

### 4.2 新增的消费者测试

`test_package` 现在包含三个二进制，覆盖三个层次（`test.sh` 依次驱动）：

| 二进制 | 层次 | 内容 |
|--------|------|------|
| `consumer_flow` | **完整消费者用例（端到端）** | 一个程序消费已安装的库完成一整件事：读问题 → 精确阶乘 → 精确有理数四则 → 精确十进制展开与循环节检测 → 闭合恒等式校验，输出与外部独立计算的值比对 |
| `saclib_test` | 断言套件 | 15 条精确不变量（见下表） |
| `sample_test` | 上游样例 | 上游唯一可运行产物 `doc/user_guide/sample.c`，验证 `sacMain` 钩子链 |

审查口径要求「鸿蒙特有测试」必须包含**完整消费者用例**（真正跑通功能/流程的端到端用例），
不能只是断言，故 `consumer_flow.c` 按此设计：它不是一个断言列表，而是**一个程序做完一件事**，
其输出与外部计算结果核对（期望值由 `python3 math.factorial` 与 `fractions.Fraction` 独立算出）：

```
problem: 11! , fractions 100/3 and 7/13
[1] 11! = 39916800          10! * 11 == 11! == 39916800  (ok)
[2] x=100/3  y=7/13  x+y=1321/39  x-y=1279/39  x*y=700/39  x/y=1300/21
[3] identity x-y == (b1*c2-b2*c1)/(c1*c2):  lhs = 1279/39  rhs = 1279/39  equal: yes
[4] 1/3 = 0.3 (cycle of length 1)   1/7 = 0.142857 (cycle of length 6)
    1/2 = 0.5 (terminating)          22/7 = 3.142857 (cycle of length 6)
    1/3 = 33.3 (cycle of length 1)   sum = 33.871794 (cycle of length 6)
PASS - consumer workflow finished
```

它同时也是一次**真实负载下的收集器验证**：阶乘与十进制展开循环会分配/释放大量中间大整数，
`test.c` 的 `GC()` 断言只覆盖收集器本身，这个用例覆盖它在实际工作负载下的表现。

> 实现备注（踩坑）：`ILWRITE` 打印的是**整数列表**，其参数会被当作堆索引 `SPACEB1[L]`。
> 当 `11! = 39916800 < BETA(2^29)` 时这是**立即数而非列表索引**，`ILWRITE(fact)` 会越界
> 解引用并段错误（真机实测）。打印整数一律用 `IWRITE`；`GWRITE` 只用于单字值。

`test.c` 的 15 条断言全部是**精确不变量**：

| 断言组 | 内容 | 为什么能挡住“能链接但算错” |
|--------|------|---------------------------|
| 多精度基础 | `2^100`、`3^60` 均为正、且占用多于 1 个 `BETA`(=2^29) 位 | 单字运算无法通过 |
| 恒等式 | `(A+B)(A-B) == A^2 - B^2`，用 `IEQ` 对完整大整数比较 | 两条不同计算路径必须完全一致（`ISUM`/`IDIF`/`IPROD` 都走多精度分支） |
| 独立定量 | `MDHOM(1000003, lhs) == 956067` | 模素数同态与恒等式互相印证；返回值错但“看起来合理”无法同时满足两条 |
| 垃圾回收 | 运算之间显式 `GC()`，再校验 `ISUM`/`IDIF` 结果不变 | SACLIB 的收集器沿栈扫描 GC roots，只有端口的 `GC()` 正确捕获**寄存器根与调用者 red zone 内的活跃对象**才可能通过 —— 这条断言**直接覆盖 `sysdep/ohosAarch64/GC.c`**，且是本轮唯一暴露真实缺陷的断言（见 §6.2） |
| 堆与列表 | `LIST1`/`LIST2`/`LENGTH`/`FIRST`/`SECOND` | 覆盖 `SPACE`/`SPACEB1` 寻址、`NIL == BETA` 约定与 `AVAIL` 单元分配 |

`956067` 由 `python3 -c "(2**100+3**60)*(2**100-3**60) % 1000003"` 独立算出，
不是从 SACLIB 自己的输出抄来的。

`test_package/conanfile.py` 的 `build()` 用包自己的 `cpp_info`
（`includedirs`/`libdirs`/`libs`/`system_libs`）编译 `test.c` 与上游 `sample.c`，
`test()` 通过 `$CONFIG_SHELL bash test.sh` 运行二进制（设备 `/bin/sh` 是 mksh，
不能执行 ELF）。两个二进制都固定用 **`-O2`** 编译 —— 这既是常规选择，也是一个**回归位**：
旧版 `GC()` 在 `-O1` 起必崩（§6.2），若日后有人改回哑参数写法，`-O2` 会立刻暴露。

### 4.3 可复用的复现与检出工具（B 类沉淀）

`knowledge/drafts/ohos-aarch64-conservative-gc-register-roots/`：

| 文件 | 用途 |
|------|------|
| `gc_root_test.c` | 通用复现负载：14 个独立大整数 + 2 个列表全部跨收集存活，收集后逐个重新推导比对；与 SACLIB 断言解耦，可移植到其他自带 GC 的库 |
| `reproduce.sh` | `-O0/-O1/-O2/-Os` 各跑 N 次并统计通过数；失败时打印诊断与修复模式 |
| `detect_conservative_gc.py` | 静态检出「哑参数落栈且无 `setjmp`」的 RISK 文件与行号（对旧版报 RISK、新版报 OK，已双向自测） |

## 5. 补丁清单

| 文件 | 内容 |
|------|------|
| `patches/0001-sysdep-ohos-aarch64-port.patch` | 新增 `sysdep/ohosAarch64/{install,cleanup,sysdep.h,GC.c}`；`bin/mksysdep.pl` 识别 aarch64/OpenHarmony 并接受 `ohosAarch64` 参数；`bin/mkmake`/`bin/mklib` 让 `AFLAGS` 可覆盖 |
| `patches/0002-weak-sacmain-hook.patch` | `include/sacsys.h` 增加 `__weak` 宏；`src/main.c` 把 `sacMain` 声明改为弱引用 |

两个补丁都是**单一职责**，按字节替换生成（保留原文件换行），并已通过：
`git apply --check -p1` clean、Conan 实际使用的 `patch_ng` + `strip=0` 应用成功
（`conan_patch_sim.py` 复刻 `apply_conandata_patches()` 的调用方式）。

> 踩坑记录：上游 tarball 内部换行不一致（文本文件 CRLF），若用「读入 → 规整换行 → 写出」
> 的方式生成修改版，`difflib` 会把整个文件判为改动，补丁变成全文重写；必须按字节替换。
> 另一个坑：补丁块必须带 `index`/`new file mode` 行，`patch_ng` 才会把该文件判为 GIT 类型
> 并剥离 `a/`、`b/` 前缀；否则报 `source/target file does not exist`。

## 6. 验证记录

### 6.1 真机 `conan create`（HarmonyOS / aarch64）

设备：`uname -s` = `HarmonyOS`，`uname -mp` = `aarch64`，clang 15.0.4，
Conan 2.29.1（OHOS 适配版），Python 3.12.9，GNU Make 4.4.1，bash 5.3。

隔离环境：`$HOME/ohos-users/saclib/2.2.8-first`（独立 `CONAN_HOME`、独立 repo 克隆到
`origin/main` 的 `b6fd9ca0ac`），由 `bin/ohos-test-runner.sh --try-lock --mode heavy` 执行，
RUN_ID `saclib-saclib-saclib-2.2.8-conan-create-20261014-180718-49053`。

| 项目 | 结果 |
|------|------|
| 源码下载 | ✅ `Sources correctly downloaded from deb.debian.org/...` |
| 两个补丁应用 | ✅ 均 `Apply patch (portability): ...` 成功 |
| 端口安装 | ✅ 直接执行 `sysdep/ohosAarch64/install`（不再经 `mksysdep.pl`，见 §6.5），随后断言 `src/GC.c`、`include/sysdep.h` 存在 |
| 编译 | ✅ **1069 个 `.c` 全部编译通过**（clang 15，`-Wall` 级告警均为上游 K&R 风格声明） |
| 归档 | ✅ `lib/saclibo.a` 1987208 字节，`llvm-ar t` 共 **1069** 个成员，含 `GC.o` |
| `test_package` | ✅ **15/15 断言通过**（`test.c`）+ 上游样例 2 条（`test.sh`）：`PASS - saclib arithmetic/list/GC functional test`、`ok: exact 20x20-digit product, sacMain hook used` |
| `conan create` 退出码 | ✅ **0** |
| 包内容 | ✅ `include/{saclib,sacsys,sactypes,hfloats,sacmacros,sacproto,sysdep}.h`、`lib/saclibo.a`、`lib/libsaclib.a`、`licenses/LICENSE` |
| package_id settings | ✅ `os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.version=15 build_type=Release` |
| ELF 架构 | ✅ 归档成员 `GC.o`/`IDPR.o` 均为 ELF64（`\177ELF\002`） |

> ⚠️ 未走 `ci/conan/build_and_test.sh`：该脚本的 JC 门禁把整棵 `archives/` 与 PR diff 基线比对，
> 而设备上的 checkout 没有 PR 基线，于是 JC6 判定 9019 个包“全部变更”，JC1/JC5 另外报出 8 个
> **`origin/main` 自带并被 git 跟踪**的隐藏状态文件（`archives/*/*/.staging-verified` 等），
> 与本包无关（已用 `git ls-files --error-unmatch` 逐个确认）。因此真机验证用等价的
> `conan create` 直接执行；L0 各门禁另行单点复核（L0j 版本未占用 ✅、L0k 库包无需
> `commands.json` ✅、L0m 目录结构 ✅）。正式 PR 走平台 CI 时由平台提供 diff 基线，不受此影响。

### 6.2 适配过程中真正卡住的一点：AArch64 版 `GC()`

第一版 `GC()` 照搬上游 x86_64 的“哑参数落栈”写法（12 个 `register int` 经 `gc_dummy()` 调用）。
真机上 `test_package` 在第 8 条断言——即**第一次 `GC()`**——稳定段错误（Signal 11，exit 139）。

定位与验证（全部在真机、用同一份 `libsaclib.a`，只替换归档里的 `GC.o`）：

| 实验 | 结果 | 结论 |
|------|------|------|
| 官方 `test.c` × `-O0/-O1/-O2` | `-O0` 6/6 通过；`-O1`、`-O2` 各 0/6 | 与优化级别强相关 |
| 把 `test.c` 里三处 `GC();` 注释掉后再跑 | `-O0/-O1/-O2` 各 6/6 通过 | **失败 100% 来自收集器**，与算术/列表/链接无关 |
| 放大 `+N`（20000 / 5000000 个单元，使收集不发生） | 仍 0/3 | 不是「回收太频繁」，而是 `GC()` 本身 |
| baseline `GC.c`，test.c × `-O0/-O1/-O2/-Os` 各 6 次 | `-O0` 6/6，其余 **0/18** | 复现基线缺陷 |
| `setjmp()` 版 `GC.c`，同样矩阵 | **24/24** | 修复生效 |

**根因**：`GCSI()` 的根发现方式是「把 `[EACSTACK, BACSTACK]` 区间内每个对齐字都当成可能的
SACLIB 对象」，因此 `GC()` 必须保证所有活跃对象此刻都在栈上。x86_64 端口靠 System V AMD64
的 16 个参数寄存器把哑参数挤到栈上；**AAPCS64 下调用者可以（也确实会）把活跃的 `Word`
留在被调用者保存寄存器 x19–x28 里跨过这次调用**，栈扫描看不见它们，于是活跃的大整数被回收，
下一次使用即段错误。`-O0` 下所有局部变量都在栈上，所以恰好掩盖了这个缺陷。

**修复**：用 `setjmp()` 强制溢出。ABI 要求 `setjmp()` 返回后所有被调用者保存寄存器保持不变，
因此编译器必须把**它实际用到的每一个** x19–x28 先写进栈帧——恰好就是仍可能持有活跃 `Word`
的那组寄存器（经典保守式收集器获取寄存器根用的也是这一手法）。同时把 `GC()` 自身局部变量的
地址作为 `EACSTACK`：AAPCS64 给叶子函数 16 字节 red zone 且编译器会把溢出槽放在那里，
从上游 x86_64 版那样以「GCSI 自己的帧」为起点会漏掉这块（实测确认：`test.c` 的断点恰好落在
刚调用过 `printf` 的断言辅助函数之后，其溢出槽就在 red zone 内）。

### 6.3 设备环境带来的其他必要适配（都不是"凑适配"，缺一即构建失败）

| 设备事实 | 影响 | 配方处理 |
|----------|------|----------|
| **没有 `perl`** | 上游 `bin/sconf` → `mksysdep.pl` 走不通 | 配方检测 `perl`，缺失时执行等价的两次拷贝（`sysdep/ohosAarch64/{GC.c,sysdep.h}`），随后断言文件已就位 |
| **没有 `/bin/bash`**（bash 在 `$HOME/usr/local/bin`）| SACLIB 构建脚本 shebang 是 `#!/bin/bash`，直接执行 → `bad interpreter` | 一律显式 `bash <绝对脚本路径>`；且**不能用 `bash -c "<绝对路径>"`**——那样会重新走 shebang 查找 |
| profile 的 `CONFIG_SHELL=/data/service/hnp/bin/bash` **在该设备不存在** | 照抄 profile 会直接失败 | `_bash` 按「`$CONFIG_SHELL` 存在才用，否则依次找 `/bin/bash`、`/usr/bin/bash`、`$PATH` 里的 bash」解析，找不到才报错 |
| **没有 `ranlib`**（只有 `llvm-ranlib`），`ar` 也非工具链归档器 | 生成的 makefile 硬编码 `AR = ar`/`RANLIB = ranlib`，make 报 `ranlib: No such file or directory` | `mklib` 补丁转发 `AR`/`RANLIB`；配方再按 `tools.build:compiler_executables` 取绝对路径，并在 `mkmake` 之后对生成的 makefile 做**断言过的文本替换**，使真正执行的 makefile 可读可查 |
| `/bin/sh` 是 mksh（无 `pushd`/`popd`） | `mkmake`/`mklib` 的 recipe 依赖这两个内建 | 通过 `SHELL=<bash>` 传给 make（同时也导出让 mklib 读取） |
| Conan 的 `run(env=...)` 接收的是**环境文件名**而非 `KEY=VALUE` 映射 | 传 dict 报 `env argument ... should be a list`；传 `KEY=VALUE` 列表会当成不存在的 env 脚本 | `$saclib` 与 `CC/AR/RANLIB/SHELL` 一律写成命令行前置赋值 |
| `mklib` 从**环境**读 `CC`（不接受参数），且只把 `CC` 转发给 make | 把 `CC=...` 当参数传会被静默忽略，make 回落到 `cc` → `make: cc: No such file or directory` | 以环境/前置赋值方式导出 |
| `/tmp` 只读（hmdfs） | `clang` 无法创建临时文件、`mksymake` 类工具失败 | 依赖 profile 的 `[buildenv] TMPDIR`；另在验证脚本中显式设置 |

### 6.4 开发期本机验证（无 OHOS 工具链时的前置证据）

| 项目 | 方法 | 结果 |
|------|------|------|
| 源码 sha256 | 两个官方 SageMath 镜像分别下载比对 | ✅ 一致（3060308 字节） |
| `include/sacproto.h` 与 `mkproto` 重新生成结果 | bash + perl + awk 实跑 `mkproto`，sha256 对比 | ✅ 逐字节一致 |
| 补丁可应用性 | `git apply --check -p1`；`patch_ng.fromfile(...).apply(strip=0, root=...)`（即 `apply_conandata_patches()` 的真实调用） | ✅ 均 clean，`errors=0` |
| 生成器流程 | 实跑 `mksysdep.pl` → `install` → `mkmake` → `mklib opt` | ✅ 2138 条对象规则、含 `GC.o` |
| 全量编译（宿主交叉近似） | MinGW gcc 12.2 编译 1069 个 `.c` 并归档 | ✅ 证明源码不依赖 `_X86_LINUX_`/`ieee754.h` |

> 宿主验证时 `src/CLOCK.c` 用了一个返回 0 的替身（Windows libc 无 `getrusage`），
> 该替身**不在配方内**；真机用的是上游原始 `CLOCK.c`，无需改动。

### 6.5 平台 CI 结果与端口安装方式的修正

| 轮次 | Worker / build | SHA | 结果 |
|------|----------------|-----|------|
| 1 | `OpenHarmonyPCDeveloper-CI-001` #91591 | `55e81dcb` | ❌ **`checkout-pr` 阶段中止，未进入构建**：Worker 取不到 PR diff（`Unable to download ... /pull/15789.diff`），诊断为「网络问题」，与本包无关；平台随后自动重试 |
| 2 | `OpenHarmonyPCDeveloper-CI-034` #91676 | `12ad49d5` | ❌ **`conan-build-test` 真失败**：端口安装被静默跳过、缺 `src/GC.c`，见下 |
| 3 | `OpenHarmonyPCDeveloper-CI-031` #91794（log `build-105497`） | **`9c316f08`** | ✅ **CI 校验通过**：L0（结构完整性）通过、L1（测试执行验证）通过、Conan `test_package` 通过；7 个步骤（worker_preparation / worker-prep / git-clone / checkout-pr / conan-setup / conan-build-test / cleanup）全部 ✅，`conan-build-test` 耗时 6m58s，整轮 9m24s |

**第 3 轮验证对象的确认方式**（通过构建的评论本身不带 SHA）：其 `cleanup` 日志里的配方修订号是
`saclib/2.2.8#036680d0282f6835b84659e5059eeaa4`；在本地用同一 Conan 2.29.x 从两个候选提交分别
导出配方，`9c316f08e2` 得到**同一修订号**（`12ad49d5ea` 得到 `#3fe5976b…`，即第 2 轮失败版本），
因此通过的就是修复提交，而不是旧提交。

> 自动 AI 审查（atomgit-bot）共 3 次，均为「✅ 未发现问题」；**无人工审查意见**。

第 2 轮的关键日志：

```
saclib/2.2.8: Sources correctly downloaded from https://deb.debian.org/.../saclib_2.2.8.orig.tar.gz
saclib/2.2.8: Apply patch (portability): Add an OHOS/aarch64 system-dependent port ...   ← 两个补丁都应用成功
saclib/2.2.8: RUN: saclib=".../b" "/data/service/hnp/bin/perl" bin/mksysdep.pl ohosAarch64
saclib/2.2.8: ERROR: Error in build() method, line 244  self._install_port()
               ConanException: the ohosAarch64 port did not install src/GC.c
```

**真因**：配方原先按「**本机是否有 perl**」二分——有 perl 就调 `perl bin/mksysdep.pl ohosAarch64`，
没有就自己拷贝两个文件。这隐含假设了「perl 存在 ⇒ mksysdep.pl 的安装副作用可信」，而事实并非如此：

`mksysdep.pl` 执行端口安装的语句是

```perl
system("bash -c \"pushd >/dev/null $ENV{'saclib'}/sysdep/ohosAarch64 ; ./install ; popd >/dev/null\"");
```

它**不检查 system() 的返回值**。只要被 spawn 的 bash 跑不起来（PATH 里没有 bash、pushd 不可用等），
安装就被静默跳过，`mksysdep.pl` 仍然 exit 0，构建随后死在缺 `GC.c` 上。

这也解释了两台机器的分叉：本机设备**没有 perl**，走的是自拷贝分支，因而一直是绿的；
CI Worker **有 perl**（`/data/service/hnp/bin/perl`），走进了这条静默失败路径。

**修正**：不再调用 `mksysdep.pl`，一律直接执行端口自带的 `install` 脚本（仍由 `patches/0001`
新增、仍以上游脚本为准），并显式以 bash 执行（OHOS 的 POSIX `sh` 是 mksh，无 `pushd`/`popd`）：

```python
self.run('%s "%s" "%s"' % (self._saclib_var, self._bash,
                           os.path.join(self.source_folder, port, "install")),
         cwd=os.path.join(self.source_folder, port), env=self._env)
```

这样端口安装不再依赖 perl、不再依赖 `system()` 是否成功、也不再依赖 PATH 里有没有 bash；
其后仍保留「`src/GC.c` 与 `include/sysdep.h` 必须存在」的断言，端口缺失或不完整依然会硬失败。
`perl` 检测逻辑随之删除（配方现在完全不需要 perl）。

> 第 2 轮日志里还有一处与本次失败无关但值得记录的环境现象：JC 段出现 15 次
> `[fail] [Errno 2] No such file or directory: 'curl'` —— 该 Worker 的 PATH 中没有 curl
> （`PATH=/data/app/bin:/system/bin:/system/sbin:/vendor/bin:...`），JC 段仍判为
> `JC_ERRORS=0` 并通过，说明这些 fail 是检查项降级而非门禁失败。`notes.md` 里留档，供后续
> 排查「CI 输出里有 fail 但整体通过」时对照。

### 6.6 源码主机复核（配合 6.5 第 1 轮）

第 1 轮的 Worker 诊断明示**出网受限**（已知不可达 `ftp.gnu.org`），而当时的源码地址
`mirrors.mit.edu` 在 main 上仅 4 个配方使用。因此按同一约束复核源码主机并调整：

| 主机 | main 上使用它的配方数 | 结论 |
|------|----------------------|------|
| `github.com` / `codeload.github.com` | 5372 / 582 | 最主流，但 SACLIB 不在 GitHub 发布 |
| **`deb.debian.org`** | **563** | ✅ **采用**：既有主流镜像，也是 `ftp.gnu.org` 等不可达主机的兜底 |
| `mirrors.tuna.tsinghua.edu.cn` / `mirrors.ustc.edu.cn` | 301 / 260 | 国内镜像，未使用 |
| `ftp.gnu.org` | 226 | 已知 Worker 不可达 |
| `mirrors.mit.edu` | 4 | 少数派，弃用 |

三个独立官方来源逐字节相同（sha256 `E8E3ACB2...203B`、3060308 字节）：
`files.sagemath.org`、`mirrors.mit.edu`、`deb.debian.org`，属**纯镜像切换、无内容变化**；
第 2 轮日志已确认 `Sources correctly downloaded from https://deb.debian.org/...`。

## 7. 已完成 / 剩余事项

已完成：真机 `conan create`（exit 0）、`test_package` 17/17、产物落盘、PR #15789 已创建
（标题前缀 `【知识库扩展】`，17 个文件变更）。

剩余（按序）：

```sh
# 1) 等平台 CI 出结果（首轮为 Worker 取 PR diff 失败，已自动重试；非本包问题）
python scripts/gitcode_pr.py ci-status --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 15789

# 2) 本包合入并发布到 ohpcd 后，回到下游
CI_PACKAGES="archives/q/qepcad/1.74" zsh ci/conan/build_and_test.sh
```

若后续 CI 真的卡在源码下载（而非 checkout），说明 `deb.debian.org` 在该 Worker 上
也不可达，此时按《MIGRATION_GUIDE》的源码获取策略处理：把 tarball 预缓存到 conan 的
`s/` 目录，或改用 Worker 可达的镜像——**但必须保持 sha256 不变**，并在
`conandata.yml`/`manifest.yaml` 同步记录新的来源与等价证据。

真机复跑时的排查顺序（对照《适配共性问题与首次真机启动避坑指南》）：

- 报 `GC` 未定义 → 端口 install 没生效，检查 `src/GC.c` 是否被拷贝、`build()` 的断言是否被绕过；
- 报 `ieee754.h: No such file` → `include/sysdep.h` 被 x86 端口覆盖，检查 `mksysdep.pl` 的补丁；
- 报 `as: unrecognized option '-P'` → `AFLAG` 未生效，检查 `mklib` 补丁；
- 报 `ranlib: No such file or directory` → 生成的 makefile 未被修正，检查 `_fix_generated_makefile()`；
- 报 `bad interpreter: /bin/bash` → 用了 `bash -c "<路径>"`，应改为 `bash <路径>`；
- 报 `env argument to ConanFile.run() should be a list` → 给 `run()` 传了 dict，应改为命令行前置赋值；
- `GC()` 相关段错误 → 确认 `sysdep/ohosAarch64/GC.c` 是 `setjmp()` 版本（`-O0` 能过、`-O2` 崩
  正是旧版哑参数写法的特征）。

> 设备 `/bin/sh` 是 mksh（无 `pushd`/`popd`），上游脚本一律经 `bash` 执行；
> 若 bash 路径在该设备变化，配方会自动在 `$CONFIG_SHELL`、`/bin/bash`、`/usr/bin/bash`、
> `$PATH` 中依次解析，无需改配方。
