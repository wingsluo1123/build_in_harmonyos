# t-coffee 13.45.0.484626413.41.0.28bdc39 适配笔记

## 上游构成

T-COFFEE 是 CRG Barcelona（Cedric Notredame 组）的渐进式多序列比对程序，
上游官网 <https://www.tcoffee.org>。发行归档
`T-COFFEE_distribution_Version_13.45.0.4846264.tar.gz`
（sha256 `c8e5ba17de11ddf07cf2ed37f077d81c1432d55b77761f115f9374de6f8d0d03`，
14 857 925 字节，官方 S3 桶 `tcoffee-packages` 的 `Archives/` 前缀，HTTP 200 实测）
解压后顶层：

```
README  license.txt  install(perl, 半交互)  t_clinkdb.txt
bin/linux/t_coffee          <- 上游自带的 x86_64 预编译参考实现（4.6 MB）
bin/macosx/(空)
doc/{html,misc}
example/                    <- 372 个样本（PDB / fasta）
mcoffee/                    <- 27 个 .pl + 参考库数据
reference_test/             <- 空目录
t_coffee_source/            <- 唯一的 C 源码树
```

`t_coffee_source/` 里是 **58 个 `.c`**，分布在
`util_lib/ io_lib/ dp_lib/ fastal/ km_coffee/ dev_lib/ t_coffee_lib/`，
加各级头文件与编译期矩阵 `matrices.h`，还有一个 Fortran 文件 `TMalign.f`。
构建入口只有 23 行的 `makefile`：

```make
CC=g++
CFLAGS=-O3 -Wno-write-strings
SOURCES := $(shell find . -type f -name *.c)
t_coffee: $(OBJECTS)
	@echo " Linking..."; $(CC) $^ -o t_coffee -lm
```

`all` 目标里还有一个 `TMalign` target，驱动变量是 makefile 里**从未定义**的
`$(FCC)`（Debian 在 rules 里显式传 `FCC="gfortran ..."`）。它是 Fortran 程序，
OHOS NDK 不提供 gfortran，所以本包只构建 `t_coffee`。

外部依赖：**零**。只有 libc + libm，残基矩阵编译在 `matrices.h` 里，
运行期不需要任何外部矩阵文件或数据文件。

## 三个卡点（按发现顺序）

### 卡点 1：`.c` 必须按 C++ 编

上游 `CC=g++`，即把 `.c` 当 C++ 编。但 clang 与 clang++ **都按扩展名**决定语言，
`clang++ foo.c` 仍然是 C，于是整棵树按 C 编时有 3 处硬错误：

```
io_lib/io_structures.h:299:7: error: must use 'struct' tag to refer to type 'Alignment'
    Alignment *Tree;                 <- 在 struct Alignment { ... } 内部用了注入类名
                                        而 typedef struct Alignment Alignment; 在第 330 行
dp_lib/evaluate_dirichlet.h:59:10: error: conflicting types for 'aln2prf'
    double **aln2prf (Alignment*, int, int*, int, double**);   vs
dp_lib/util_dp_gotoh_nw.h:57:7:        int    **aln2prf (Alignment*, char*);
dp_lib/util_dp_drivers.c:940:12: error: conflicting types for 'seq2msa'
    Alignment *seq2msa (char *method, Sequence *S);   vs
dp_lib/util_dp_drivers.h:66:12:        Alignment *seq2msa (Sequence *S);
```

前者在 C 里合法（C++ 不合法），后两者在 C++ 里合法（同名不同签名 → 重载）。
两种语言各挂一半，只有 C++ 能全过。配方因此在 CFLAGS 里加 `-x c++`，
而不是靠换编译器解决。

### 卡点 2：`-O0` 与 `-fsigned-char` 是必需的，不是保守选择

Debian 的 `debian/rules` 对**同一份源码**写着：

```make
# Force -O0 to avoid crash in test suite (see debian/tests/run-unit-test)
export DEB_CFLAGS_MAINT_APPEND+=-O0
# Force signed char for architectures such as arm; no changes for the others.
export DEB_CFLAGS_MAINT_APPEND+=-fsigned-char
```

本次独立复验（不是照抄）：

| 编译器 | 目标 | 优化 | 结果 |
|--------|------|------|------|
| g++（宿主） | x86_64 Linux | `-O0 -fsigned-char` | rc=0，输出正确 |
| g++（宿主） | x86_64 Linux | `-O3 -fsigned-char` | **rc=11（SIGSEGV）** |
| clang++ + OHOS sysroot | aarch64 OHOS | `-O0 -fsigned-char` | rc=0，输出正确（补卡点 3 的补丁后） |
| clang++ + OHOS sysroot | aarch64 OHOS | `-O1/-O2/-O3 -fsigned-char` | **COREDUMP（SIGSEGV），崩在 `proba_pair` 库** |
| clang++ + OHOS sysroot | aarch64 OHOS | 任意 `-O*` **无** `-fsigned-char` | **挂死**（OHOS clang 默认 `-fno-signed-char`） |

g++ `-O3` 在 x86_64 上同样 SIGSEGV ⇒ 这是**上游对优化器敏感的缺陷**，
不是 OHOS 平台问题，所以配方不试图修它，而是照 Debian 的做法钉死 `-O0`，
并把证据写进 manifest 与本文件。

`-fsigned-char` 同理：OHOS NDK 的 clang 默认 `-fno-signed-char`，而 T-COFFEE
大量用 `char` 存残基并做比较运算，字符符号性变了行为就变了。

### 卡点 3：clang 在 AArch64 上把 C++ UB 变成 `brk #1`（SIGTRAP）

打上 `-O0 -fsigned-char` 后 `-O0` 产物仍然立刻死，退出码 133。strace 显示
崩之前没有任何系统调用（纯用户态），顺着 `qemu-aarch64 -d in_asm` 找到最后
一条执行块：

```
IN: _Z9set_nproci
0x00000055001d88ec:  sub  sp, sp, #16
0x00000055001d88f0:  str  w0, [sp, #12]
0x00000055001d88f4:  ldr  w8, [sp, #12]
0x00000055001d88f8:  adrp x9, ...
0x00000055001d88fc:  str  w8, [x9, #200]
0x00000055001d8900:  brk  #0x1          <- 没有 ret
```

`set_nproc()` 的源码是：

```c
int set_nproc(int np)
{
  nproc=np;                 /* non-void，没有 return —— C++ UB */
}
```

clang 把「控制流到达非 void 函数末尾」降成 llvm `unreachable`，AArch64 后端把
`unreachable` 降成 `brk #1` 指令（SIGTRAP），于是**函数体的最后一条指令就是
陷阱**，根本没有 `ret`。gcc 在同一位置只发一个普通 epilogue，所以上游的 x86_64
产物、以及发行包里那份预编译 `bin/linux/t_coffee` 都跑得好好的。

`llvm-objdump -d | grep -c brk` 在未打补丁的 `-O0` 产物上是 **31**，散布在 30 个
函数里（`set_nproc` / `get_pwd` / `cherry` / `km_coffee` / `phylotrim` / …）。
`batch_main()` 打印参数表时就会调 `set_nproc()`，所以 `-version` 之外的任何调用
都活不下来。

补丁 `patches/0001-missing-return-in-non-void-functions.patch` 只在 30 个函数
末尾各追加一句 `return <零值>;`，不改任何算法。这 30 个函数全是 non-void 且
所有调用点都丢弃返回值（否则上游自己早就崩了），所以补零值与上游行为等价。

打完补丁：

- `brk #1` 由 **31 处降到 1 处**，剩下那 1 处是 libc++abi 的
  `__cxxabiv116__shim_type_info::~shim_type_info()` 桩（删除不完整类型用的
  占位实现，运行期不可达）；
- 3 条蛋白 + 2 条 DNA 的比对结果与 `g++ -O0 -fsigned-char` 的 x86_64 参考构建
  **逐字节一致**（`example/proteases_small.fasta` 那组 3008 字节完全相同）。

## 产物与验证

- 产物：`bin/t_coffee`，aarch64 OHOS ELF（`e_machine=183`、`ET_DYN` PIE、
  解释器 `/lib/ld-linux-aarch64.so.1`），`NEEDED` 只有 `libc.so`（`-lm` 在
  OHOS 已并入 libc）。
- 不打包上游那份 x86_64 预编译 `bin/linux/t_coffee`（测试 T5-3 断言 `bin/`
  里只有本次交叉编译产物）。
- `t_coffee -version` 报 `PROGRAM: T-COFFEE Version_13.45.0.4846264
  (2020-10-15 17:52:11 - Revision 5becd5d - Build 620)`。
- 运行期会在 `HOME_4_TCOFFEE` / `DIR_4_TCOFFEE` 下自建
  `tco/ mcoffee/ methods/ plugins/`。OHOS 上安装目录只读，测试把它指到临时
  目录并断言安装目录零落盘。
- T-Coffee 无参运行与比对过程都会交互式提问（例如
  `Identify Master Sequences [no]:`），测试与任何 CI 调用都必须喂 `</dev/null`。

## 上游测试清点

上游**没有**自动化测试（N = 0）：没有 `tests/`、没有 `make check`、没有
ctest/pytest 注册、没有 CI 配置；`reference_test/` 是空目录；
`./install` 是半交互式 Perl 安装器，还会去装 SOAP::Lite 并下载编译
expresso / 3dcoffee / mcoffee / rcoffee 等伴生包，不是可用的 CI 入口。
证据与结论见 `test_package/MANIFEST.yml` 的 `upstream_test_inventory`。

因此全部验证由 `test_package/test_t_coffee.sh` 补齐，29 条断言全部真实执行
产物或真实读 ELF 字节，详见 MANIFEST.yml。

## 同源门禁本地跑分

`CI_PACKAGES="archives/t/t-coffee/13.45.0.484626413.41.0.28bdc39"
CONAN_PROFILE=ohos-aarch64-wsl CI_BRANCH=feat/t-coffee-13.45.0.484626413.41.0.28bdc39
zsh ci/conan/build_and_test.sh`：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: t_coffee --help OK
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content
消费者测试: 29 passed, 0 skipped, 0 failed  (断言计数 29/29)
Pass rate: 100.0% (1/1)
```

L4 那条 warn 是**误报**，可以自行复核：L4 扫的是
`grep -rlE '(strcpy|sprintf|gets|strcat)\b' patches/`，本补丁的 `+` 行里
一条都没有（`grep -E '^\+' … | grep -E '(strcpy|sprintf|gets|strcat)\b'` 为空），
命中的两处都在 unified diff 的**上下文行**里：

- `return csprintf (name, "%s", cwd);` —— `csprintf` 里含 `sprintf` 子串；
- `sprintf (file, "%s%s", s, ext);` —— `get_pwd()` 附近的上游原有代码，
  只是补丁 hunk 的上下文。

补丁本身只新增 30 行 `return 0;` / `return NULL;`，没有引入任何危险函数。

> 顺带记一条与本包无关的仓库现状：`origin/main` 上已有 5 个被 git 跟踪的
> 运行时状态文件（`archives/c/cloog/0.21.1/.build-closed`、
> `archives/{c/cloog/0.21.1,k/kics/2.1.20,l/libbfio/20260623,t/thc/3.8}/.staging-verified`），
> 在 origin/main 的干净 worktree 上直接跑 `ci/scripts/junk_check.sh` 也是
> `JC_RESULT=fail`。所以本地跑门禁时要用 `JUNK_PR_DIFF=<本包 pr.diff>`
> 走 prdiff 模式（这正是 CI 的做法），否则整仓扫描会被这 5 个既有文件拦下。
> 本 PR 不动它们。

## 已知限制

1. `TMalign` 不在本包内（需要 gfortran），因此 Expresso / 3D-Coffee 等依赖它
   的上层模式不可用。
2. 上游对优化等级敏感（见卡点 2）。本包钉死 `-O0`，产物体积与速度都不如
   `-O3`，这是为了功能正确性做的取舍；速度敏感的场景应等上游修复。
3. 上游发行归档里的 27 个 `.pl` 辅助脚本依赖完整 Perl 环境与网络下载伴生包，
   打包价值有限，本包只装 `bin/t_coffee` 与许可证。

## CI 整改（2026-10-12，构建 #85480）

CI 的 `conan-build-test` 里消费者测试 27 通过 / 2 失败，失败的两条都是**断言写错**、
不是产物缺陷；同时按 R26 补上 C++ 运行时的静态链接。

### 1. `FAIL: 存在非 libc.so 动态依赖: 'libc++_shared.so'` → 改为静态链接 C++ 运行时

上游那份手写 makefile 的链接行是 `$(CC) $^ -o t_coffee -lm`，**从不展开 LDFLAGS**，
而 clang++ 默认动态链接 libc++，于是 `libc++_shared.so` 进了 `DT_NEEDED`。
这与 R26（不污染/不依赖平台外的 shared C++ 运行时）冲突，也与本仓既有做法不符
（`archives/f/fairy-stockfish/14`、`archives/g/graphviz/12.2.1` 都是
`-static-libstdc++`）。

处置：新增 `patches/0002-makefile-honour-LDFLAGS.patch`，只在链接行插入 `$(LDFLAGS)`
（LDFLAGS 为空时与上游逐字节等价），配方传 `LDFLAGS=-static-libstdc++`。

实测（本地 `conan create`，profile `ohos-aarch64-wsl`）：
`OK: 动态依赖仅 libc.so（NEEDED='libc.so '），libm 已并入 OHOS libc`。

### 2. `FAIL: 产物中找不到 /lib/ld-linux-aarch64.so.1 解释器字符串` → 断言认错了加载器名字

OHOS/HarmonyOS 的动态加载器是 musl 的 `/lib/ld-musl-aarch64.so.1`，不是 glibc 习惯的
`ld-linux-aarch64.so.1`。**制品仓里由 CI worker 构建发布的包实测**：

| 包 | 二进制 | `.interp` |
|----|--------|-----------|
| puredata/0.54.1 | `bin/pd` / `bin/pdreceive` / `bin/pdsend` | `ld-musl-aarch64.so.1` |
| emacs/29.1 | `bin/emacs-29.1` | `ld-musl-aarch64.so.1` |

而本地 WSL 交叉工具链 `/opt/lpk-fixed/clang` 仍按 glibc 习惯写
`ld-linux-aarch64.so.1` —— 作者当初是在本地看着这个名字写的断言，到 CI 上必然失败。

处置：断言改为「解释器是 aarch64 加载器且既非宿主 x86-64 加载器」，两个 aarch64 名字
都接受，**两个都找不到仍然判失败**；「产物是 aarch64」由同组已有的
`e_machine=183 (AArch64)`（读 ELF 头 18-19 字节）独立保证，判据没有被削弱。

### 3. 顺带：抬高上游的 `MAX_N_PID` 上限，让测试跨环境可复现

本地复跑 T3 时 T-Coffee 直接失败退出 1：

```
--ERROR: MAX_N_PID exceded -- Recompile changing the value of MAX_N_PID
        (current: 260000 Requested: 330563) OR setenv MAX_N_PID_4_TCOFFEE=330563
```

上游拿 PID 构造锁文件名，硬上限 260000。本地 WSL 的 `pid_max` 让 PID 到 33 万，
必然触发；CI worker 上 PID 只有几万（rstatd 日志里 `pid=48490`）所以侥幸没踩。
按上游给的 `MAX_N_PID_4_TCOFFEE` 显式抬高（只影响锁名空间，不参与任何比对计算），
测试因此不再依赖宿主的 PID 水位。

整改后本地实测：`t-coffee ... 消费者测试: 29 passed, 0 skipped, 0 failed (断言计数 29/29)`，
`conan create` rc=0。
