# lagan 2.0 — OHOS PC (aarch64) 适配笔记

## 1. 源码

| 项 | 值 |
| --- | --- |
| 上游 | Stanford LAGAN — http://lagan.stanford.edu/lagan_web |
| 归档 URL | `http://lagan.stanford.edu/lagan_web/lagan20.tar.gz` |
| HTTP | **200**（2026-10-14 实测，`curl -fsSL -o lagan20.tar.gz` 退出码 0） |
| 大小 | 589115 字节 |
| sha256 | `a65e61ed4fd6608f4e5ad5b11a1b77f4fec1a207d822c5885b3e86727496e1fe` |
| 归档根目录 | `lagan20/`（配方 `get(..., strip_root=True)`） |

未使用任何镜像站：URL 就是 Stanford 官方分发地址，实测直连 HTTP 200。

LAGAN（Local, Global, Multiple Alignment）是 DNA 序列比对工具集，2.0 版包含：

* `anchors` `chaos` `order` `mlagan` `prolagan` `glocal` —— 6 个主程序
* `utils/` 下 17 个小工具（bin2mf、cextract、scorealign、fa2xfa、dotplot …）
* `lagan.pl` `slagan.pl` `slagan-mfa.pl` `rechaos.pl` `anal_gloc.pl`
  `xmfa2mfa.pl` + `Utils.pm` —— perl 包装脚本
* `nucmatrix.txt` `blosum62.txt` `blosum62s.txt` —— 打分矩阵
* `sample.fasta` `sample.params` —— 官方演示数据

构建系统是**普通 Makefile**（不是 autotools/CMake）：顶层 `make` 递归到 `src/`，
`glocal/` 再各自 make 一次。**无第三方依赖**，只链接 `-lm`。

> 任务池注解提到 Boost —— 实测源码树没有任何 Boost 引用，只有 `-lm`。

## 2. 本地交叉编译

构建目录位于 WSL 原生盘（ext4），不在 `/mnt/*` 上：

```
buildPath : /root/ohpcd-work/build/lagan-2.0
host  profile : ohos-aarch64-wsl   (os=OHOS, arch=armv8, clang 15, libc++)
build profile : default            (x86_64 Linux)
```

命令与结果：

```
$ cd /root/ohpcd-work/wt-lagan-8005/archives/l/lagan/2.0
$ conan create . -pr:h ohos-aarch64-wsl -pr:b default
...
lagan/2.0: Package '6b129b068851896169fae42d399fa922d239ce8a' created
lagan/2.0: Full package reference:
  lagan/2.0#2ab2fd0c939955cf9d4a48ba962e43a3:6b129b068851896169fae42d399fa922d239ce8a
======== Launching test_package ========
lagan/2.0 (test package): Running test()
CREATE_EXIT=0
```

产物类型确认：

```
$ file <pkg>/bin/chaos
<...>/bin/chaos: ELF 64-bit LSB pie executable, ARM aarch64, dynamically linked,
                 interpreter /lib/ld-linux-aarch64.so.1, with debug_info, not stripped
```

## 3. 4 个可移植性补丁（2006 年代码 + 现代 clang/glibc）

| 补丁 | 症状 | 修法 |
| --- | --- | --- |
| `0001-rename-getline-glibc-collision.patch` | `anchors.c` / `glocal/io.cpp` 自定义 `getline(FILE*, hll*)` 与 glibc 2.10+ 的 `ssize_t getline(char**, size_t*, FILE*)` 冲突（`conflicting types for 'getline'`） | 重命名为 `lagan_getline()` / `glocal_getline()` |
| `0002-static-inline-definitions.patch` | C99 裸 `inline` 定义（`fchaos.c` / `multial.c` / `order.c`）不产出外部符号，编译器未内联的调用点（如 `connectToPrev`/`doAlgo` 里的 `findPrev`）链接期 `undefined symbol` | 改为 `static inline` |
| `0003-rename-global-end-variable.patch` | `glocal/structs.h` 有 `using namespace std;`，全局变量 `end` 在 C++11 下与 `std::end` 二义（7 处 `reference to 'end' is ambiguous`） | 全局变量改名 `endFrag` |
| `0004-fstream-h-to-fstream.patch` | `glocal/score.cpp` 用预标准 `<fstream.h>`，现代标准库已移除 | 改为 `<fstream>` |

另有一处**不改源码**的处理：`src/thrtrie.h` 的 tentative definition
`int indeces[256];` 被 `fchaos.c` 与 `thrtrie.c` 同时包含，现代 clang 默认
`-fno-common` 会导致重复符号；配方在 C 编译参数上加 `-fcommon` 恢复旧合并语义
（与各发行版在 GCC 10 改默认值后的处理一致）。

## 4. 配方要点

* `src/Makefile` 把 `CC`/`CPP` 写死成 `gcc`/`g++`，且 `all` 目标会递归进
  `glocal/` 再硬编码一次 `g++`。因此**不跑 `make all`**，而是显式列出各二进制
  目标，从 make 命令行覆盖 `CC`/`CPP`（命令行变量优先于 Makefile 内赋值）；
  `glocal/` 单独再 `make` 一次并覆盖 `CC`/`CLINKER`。
* 编译器路径取自 `self.conf.get("tools.build:compiler_executables")`，
  不依赖 `${CC}` 之类未定义的 shell 变量（R33）。
* 打包把二进制、perl 脚本、打分矩阵都放在同一个 `bin/` 根下，因为 LAGAN 的
  perl 包装脚本用 `$LAGAN_DIR` 找数据；`package_info()` 用
  `runenv_info.define("LAGAN_DIR", <pkg>/bin)` 并把它加进 `PATH`。
* 上游 tarball 根目录带一个预编译的 **Mach-O** `prolagan`；`make ../prolagan`
  会用新编的 ELF 覆盖它，打包取构建目录里的那份，不会误打包预编译二进制。
* `package_type = "application"` → 按 R38/L0k 提供软件级 `commands.json`。

## 5. 功能验证（binfmt qemu-aarch64 + OHOS guest sysroot）

本机已注册 `binfmt_misc` 的 `qemu-aarch64`（`QEMU_LD_PREFIX=/opt/ohos-guest`），
可直接执行打包出来的 aarch64 ELF：

```
$ LAGAN_DIR=<pkg>/bin qemu-aarch64 -L /opt/ohos-guest <pkg>/bin/chaos
usage:
chaos queryfile dbasefile [options]
...

$ LAGAN_DIR=<pkg>/bin qemu-aarch64 -L /opt/ohos-guest <pkg>/bin/mlagan
mlagan seqfile_1 seqfile_2 [... seqfile_63] [-parameters]
-nested : runs improvement in a nested fashion
...
```

> 注意：**`mlagan` 必须先有 `$LAGAN_DIR`**，否则只打印
> `Environment variable LAGAN_DIR not set` 就退出 —— 这是 LAGAN 的数据定位
> 机制，不是 bug。配方 `package_info()` 已在 runenv 里导出该变量。

test_package（`test_lagan.py`）两阶段实测：

```
$ python3 test_lagan.py --bin-dir <pkg>/bin
test_lagan: 56 assertions passed, 0 failed          # 阶段一：文件齐备 + 可执行位

$ python3 test_lagan.py --bin-dir <pkg>/bin --run
test_lagan: 58 assertions passed, 0 failed          # 阶段二：真实执行 chaos/mlagan
```

交叉构建（CI 场景）下 `can_run()` 为 False，只跑阶段一 —— 56 项断言仍然会
因为包内缺少任何二进制/工具/脚本/矩阵而失败，不是空壳。

## 6. 踩坑与结论

1. **老代码的 `getline` 撞名是必现的**，不是偶发；只要能编到 `anchors.c` 就会触发。
2. **C99 裸 `inline` 在 clang 上不产外部符号**这一点很隐蔽：编译期无警告，
   只有链接期在"编译器选择不内联"的调用点报 `undefined symbol`，
   且随优化等级变化（`-O0` 可能看不见）。用 `static inline` 一次解决。
3. **`using namespace std;` + C++11 的 `end`** 会让一个普通全局变量变成二义名，
   与该全局变量本身无关。
4. `src/Makefile` 硬编码编译器 → 交叉编译必须绕过 `all` 目标、显式给目标并
   在命令行覆盖 `CC`/`CPP`/`CLINKER`。
5. 上游无测试套件：`Makefile` 无 `check`/`test` 目标，tarball 内也没有用例，
   所以 `test_package/MANIFEST.yml` 的 `upstream_tests` 为空，
   由消费者侧 `test_lagan.py` 承担真实断言（56 项常跑 + 2 项可运行时）。