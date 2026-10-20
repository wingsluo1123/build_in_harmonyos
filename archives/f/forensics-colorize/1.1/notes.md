# forensics-colorize 1.1 — OpenHarmony PC 适配说明

## 一、这是什么

上游 `jessek/colorize`，提供两个命令行程序：

| 程序 | 作用 |
|---|---|
| `colorize` | 把任意文件的可视化字节流渲染成 24 位 BMP 图片（取证可视化） |
| `filecompare` | 按块逐字节比对两个文件，输出每块「相同/不同/补齐」的标记字节流 |

产物：`bin/colorize`、`bin/filecompare`，`package_type = "application"`。

## 二、适配路径

**路径 A（基础适配，1 分）**：改动只落在 `archives/f/forensics-colorize/`。
**上游源码零修改** —— 没有任何 patch，所有平台差异都由 `ohos-compat/` 下的两个头文件
和编译参数吸收。

## 三、上游构建体系与我们的做法

上游是 autotools 工程，但只有 `configure.ac`，**仓库里没有 `configure`、没有 `Makefile.in`**
（要 `bootstrap.sh` 现跑 autoreconf）。本机与 CI worker 都不保证具备 autoconf/automake，
所以**不跑 autotools**，改为用 profile 注入的 OHOS clang 逐 TU 编译再链接，
与 autotools 产物等价（同样的源文件集合、同样的 `-DVERSION="1.1"` 语义）。

```bash
$CC -I src -D__progname=__fc_progname__ \
    -include ohos-compat/config-defs.h \
    -include src/main.h \
    -include ohos-compat/config-shim.h \
    src/ui.c src/helpers.c src/colorize.c -o bin/colorize
```

其中 `helpers.c` 额外带 `-DFORENSICS_COLORIZE_PROGNAME_TU`。

## 四、三处必须处理的平台差异

### 1. `__progname` 重复定义（链接期硬错）

上游 `src/main.h`：

```c
#ifdef __GLIBC__
extern char *__progname;
#else
char *__progname;      /* 强定义 */
#endif
```

OHOS 不是 glibc，于是 `ui.c` / `helpers.c` / `colorize.c` **每个 TU 各定一个强符号**，
`ld.lld` 直接报 `duplicate symbol: __progname`。

解法（源码零修改）：
1. `-D__progname=__fc_progname__` 把那条定义改名（形态不变，仍是 TU 内强定义），
   同时也避开与 libc 内部同名符号的纠葛；
2. `config-shim.h` 用 `-include` 注入**所有** TU，把「非 helpers.c」的那些定义
   降级为 `__attribute__((weak))`，只保留 `helpers.c` 一个强定义。
   链接期强定义优先、弱定义被丢弃，与 glibc 下「libc 定义 + extern 声明」的符号结构一致
   （实测 `llvm-nm` 只有一个 `__fc_progname__`）。

### 2. `HAVE_FSEEKO` 必须定义

未定义时上游 `main.h` 会走：

```c
#define fseeko _fseeki64
#define ftello _ftelli64
```

这是 **Windows/MSVC** 的 64 位替换，OHOS 上不存在这两个符号 → 隐式声明 + 链接失败。
`configure.ac` 的 `AC_FUNC_FSEEKO` 只在 libc **没有** `fseeko` 时把它定义成 0，
OHOS musl 有 `fseeko`，所以这里定义 `HAVE_FSEEKO=1` 与 configure 的结论一致。

### 3. `HAVE_INTTYPES_H` / `HAVE_LIBGEN_H`

`configure.ac` 缺 `inttypes.h` 会直接 `AC_MSG_ERROR`；OHOS sysroot 两个头都有。
本文件用 `config-defs.h` 等价代偿 autoconf 生成的 `config.h`（`HAVE_CONFIG_H` 刻意不定义）。

## 五、测试

### 上游测试套件：**无**

- `src/Makefile.am` 只有 `bin_PROGRAMS`，**没有 `TESTS` / `check` 目标**；
- 根目录只有 `bootstrap.sh` / `configure.ac`，没有 `tests/` 目录；
- `src/test.c` 不是测试，是一个「把 0x00..0xFF 各打印 27 次」的**样本数据生成器**。

所以上游自动化用例数 = **0**；测试覆盖全部来自本配方的消费者端到端用例。

### 消费者用例：`test_package/test_forensics_colorize.c`（216 条断言）

在真机（OHOS PC，aarch64）上直接跑被测二进制，分 5 组：

| 组 | 覆盖内容 |
|---|---|
| `test_cli` | `-V`/`-h` 输出、无参/未知参数的退出码与 stderr、`-v` 的 Processing/Image will be W x H x 24/Done 三段 |
| `test_colorize_vertical` | 默认纵向方向：`-w 100` / `-w 7` / `-w 10` / `-d` / `-d -w 7` 的 BMP 头字段、文件长度、行距与逐像素颜色 |
| `test_colorize_orientation` | `-o` / `-o -d` 横向方向：宽高对调、`bfSize` 与文件长度不等（补齐字节落盘） |
| `test_filecompare` | 等长/不等长、`-b` 块大小、逐块标记字节 `0x80/0xFE/0xFF` |
| `test_fail_closed` | 不存在的输入、不可写输出等错误路径 |

输出一行机器可判读的结论：

```
RESULT: PASS (216 checks, 0 failures)
```

`test_package/conanfile.py` 会正则解析这一行，解析不到或 `failures != 0` 都直接抛
`ConanException`（fail-closed）。

## 六、上游若干行为要点（写测试时踩过的坑，供后续维护参考）

1. **像素字节序**：每像素 3 字节按 `RGBQUAD` 结构体声明顺序 `(rgbBlue, rgbGreen, rgbRed)`
   写出，值分别是 `lookup_color(c+128)` / `lookup_color(c)` / `lookup_color(c-128)`。
   `c=0x00` 与 `c=0xFF` 是两个特判（整条写 `0` / 整条写 `0xFF`）。
2. **行尾补齐字节数是 `val % 4`，不是 `(val%4)*3`**（`pad_image` 的落空 switch 每个 case
   只 `fputc` 一个字节）。所以行距 = `3*W + (W%4)`；`W=7` 时补齐 3 字节、行距 24。
3. **只有 `direction == TRUE` 才补行**：`-d -w 7` 的文件是 810 字节（行距 21），
   而默认 `-w 7` 是 918 字节（行距 24）。
4. **`-d` 是把行序翻转，不是把图变白**：`direction=FALSE` 支走的是
   「顺序读取」路径（`location = i*W + j`），第一行取的是**数据开头**。
5. **`bfSize` / `biSizeImage` 只按 `w*h*3` 算，不含补齐字节**，所以 `-w 7` 的文件长
   (918) 与 `bfSize` (810) 本来就不相等 —— 这是上游既有布局，不是适配缺陷。
6. `-o`（横向）会把 `image_width`/`image_height` 对调写进信息头，且仍旧每「组」补
   `image_height % 4` 个字节。

## 七、验证结果（真机/交叉编译实测）

| 项目 | 结果 |
|---|---|
| `conan create`（ohos-aarch64-run） | 退出码 0 |
| 产物格式 | `ELF 64-bit LSB pie executable, ARM aarch64`（`readelf -h`：`Class: ELF64` / `Machine: AArch64`） |
| 动态依赖 | 仅 `libc.so`（OHOS musl） |
| `colorize -V` / `filecompare -V` | `1.1` / `1.1` |
| 消费者用例 | `RESULT: PASS (216 checks, 0 failures)`，连跑 2 次均通过 |
