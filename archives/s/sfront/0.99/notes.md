# sfront 0.99 适配 HarmonyOS PC 记录

- 三方库：sfront 0.99（MPEG-4 Structured Audio，MP4-SA → C 翻译器）
- 上游：<https://john-lazzaro.github.io/sa/>（John Lazzaro, UC Berkeley）
- 源码：`https://john-lazzaro.github.io/sa/sfront0.99.tar.gz`
  sha256 `97296d8308ad7fabc8944a44592bbb996293ee66975b3c07c4022a548ef68862`（顶层目录 `sfront/`）
- 语言预检（R47）：`detected_language=c`，主体占比 100%（`src/` 下 93 个 .c，tarball 根下 99 个），任务语言 cpp 属兼容族
- 依赖：无 Conan 依赖（仅 libm），未使用 `tool_requires`

## 上游构建系统

sfront 0.99（2011 年发布）是纯 C89，没有 configure / autotools / CMake：

| 入口 | 作用 |
|------|------|
| `src/lib/Makefile` | 编译 `libmaker` 代码生成器，用 `src/lib/{csrc,asys,csys,nsys,psys}/*.c` 模板重建 `src/{csrclib,asyslib,csyslib,psyslib,nsyslib}.[ch]`，然后 `cd .. ; make` 回落到 `src/Makefile` |
| `src/Makefile` | 编译 44 个 .o，链接出 `bin/sfront`；`install` 把可执行文件拷到 `$(BINDIR)` |

Debian 的 `debian/rules` 走的也是这条路径（先 `make parser.tab.c`，再
`cd src/lib && make`，再 `cd src && make sfront`），本配方与之一致。

## OHOS 适配决策

1. **`MODEL=-m32` 必须去掉。** 上游 `src/Makefile` 写死
   `CFLAGS = $(MODEL) $(OPT) $(DBUG) $(ECHECK)`，其中 `MODEL = -m32`、
   `ECHECK = -ansi -Wall`。AArch64 上没有 32 位 ABI，因此配方整体覆盖 `CFLAGS`：
   `-O2 -Wall -Werror=implicit-function-declaration -static`。
   - `-ansi`（= `-std=c89`，定义 `__STRICT_ANSI__`）**实测不需要**：用 clang 默认
     方言与 `-ansi` 各构建一次，产出的 `sfront` BuildID 完全相同
     （`6fb455b989f3264e`），两者都编译出 0 条 implicit-function-declaration。
     去掉 `-ansi` 顺带规避 tal 1.9 记录的「`__STRICT_ANSI__` 让 musl 隐藏
     `strdup()`/`strcasecmp()` 声明、C89 隐式 int 把 64 位指针截断」的坑。
   - `-Werror=implicit-function-declaration` 把这类回归拦在编译期。实测 0 命中，
     也没有 tal 1.9 里的 `-Wint-to-pointer-cast` 告警——sfront 的翻译器自己不用
     POSIX 扩展函数（`src/symbols.c:538` 明确写着 "strdup not ANSI -- rewritten
     with different name"），`strdup`/`strcasecmp`/`fileno` 只出现在 `*lib.c` 的
     字符串字面量里，那是给**生成出来的程序**用的模板文本。
2. **`SLOWSCHED=-fno-schedule-insns` 清空。** GCC 专有调度开关，clang 15 只打印
   `warning: optimization flag '-fno-schedule-insns' is not supported`。
3. **`-j1`。** `src/lib/Makefile` 的 `all` 会嵌套调用子 make，HMDFS 上 jobserver 的
   FIFO 不可用，子 make 只能退回 `-j1`（E074/E525）。与其让子 make 静默降级，不如
   整体串行。
4. **`touch src/parser.tab.c src/parser.tab.h`。** `src/Makefile` 里有
   `parser.tab.c: parsehelp.c parser.y tree.h`，recipe 是 `-bison -d parser.y`
   （前导 `-` 让 make 忽略失败）。官方 tarball 已自带 bison 2.3 的产物，但
   `conan get()` 不保留 mtime，解压顺序决定它会不会被判定过期——构建结果会随
   「机器上有没有 bison」漂移。显式 touch 让预生成解析器成为唯一权威，构建不再
   隐式依赖 bison。
   交叉核对：用 bison 3.8.2 重新生成 `parser.y` 无任何错误/警告，且与随包版本
   产出的翻译结果一致（同一示例的 `-orc` 输出仅有内嵌 sfront argv 与输出文件名
   之差）。
5. **`-static`。** OHOS SDK 没有 `rcrt1.o`，`-static-pie` 直接
   `ld.lld-15: error: cannot open rcrt1.o`；`-static` 可用（2.7 MB 静态可执行文件）。
   静态链接让交付物在 CI 的 AArch64 worker 上原生可跑，在本地 x86_64 构建机上经
   `qemu-aarch64` 也能直接运行，不需要 `QEMU_LD_PREFIX` 或 guest rootfs。
6. **`SAOLLIBDIR` 与 `-cpp`。** `src/tree.h:667` 把 `#define SAOLLIBDIR
   "/usr/share/sfront"` 编译进二进制，`src/sfmain.c:cppsystemcall` 在 `-cpp` 模式下
   拼出 `gcc -nostdinc -x c++ -E -o <x>.tpp ... -I /usr/share/sfront` 并用
   `system()` 执行。OHOS 工具链没有 `gcc`，安装前缀也不是 `/usr/share/sfront`，
   所以 **`-cpp` 模式在 OHOS 上不可用**。这直接导致 26 个上游示例里唯一的
   `examples/rtime/linbuzz`（唯一 `#include <Slib/ssm.hs>` / `<Slib/std.hs>` 的示例）
   在 OHOS 上无法翻译。这是上游对外部工具名与固定安装前缀的硬编码依赖，不是本次
   适配裁剪；其余 25 个示例与 `-cin` 控制驱动模式均不受影响。包的
   `share/sfront/lib/` 仍然完整交付 Slib 与 reson 库，供用户自建 SAOL 工程使用。
7. **`system(NULL)` 探测。** `src/sfmain.c:148` 用 `system(NULL)` 检查 shell 是否可用，
   不可用时打印 "No shell available for system() command."。这条路径与平台无关：
   OHOS 设备有 `/bin/sh`，qemu 用户态下走宿主 `/bin/sh`，两条路径都满足
   `system(NULL) != NULL`。本次本地实测走的是 qemu 用户态这一条。

## 打包内容

| 路径 | 内容 |
|------|------|
| `bin/sfront` | 静态 AArch64 可执行文件（R38 → 软件级 `archives/s/sfront/commands.json`） |
| `share/sfront/lib/{Slib,reson}` | 上游 SAOL 标准库 10 个文件（`Slib/*.hs` 4 个 + `reson/*.hs` 5 个 + `reson/README`） |
| `share/sfront/examples/` | 26 个示例乐谱 + 20 个 SASL 乐谱 + 样例音频/MIDI/AIF |
| `share/doc/sfront/html/` | `README.HTML`、`index.html`、`sfman/`、`book/`（*The MPEG-4 Structured Audio Book*）、`copyright/` |
| `licenses/` | `bsd.html`（3-clause BSD）、`gfdl.html`（GNU 文档许可）、`index.html` |

未收录 Debian 的 `debian/sfront.1`：那是 Debian 打包者新写的 manpage，不属于上游
tarball，不应由本仓库代为分发。

## 测试

上游**没有任何自动化测试**：无 `tests/` 目录，`src/Makefile` 与
`src/lib/Makefile` 都没有 `check`/`test` 目标（`make -n` 已确认）。可执行的规格
只有 `examples/`（26 个 SAOL 乐谱，每个配 Makefile 的 `audio`/`mp4test`/`compare`
规则）与 `-help` 里记录的命令行面——Debian 的 autopkgtest 也只有
`sfront -help | grep "Usage: sfront"` 一条。本配方交付的 68 条断言逐条执行真实交付物，
分组为 A 2 + B 5 + C 29 + D 7 + E 1 + F 21 + G 3 = 68。

`test_package/test_sfront.sh` 共 68 条断言，全部执行真实交付物：

- **A 交付物（2）**：`bin/sfront` 可执行；`e_machine == EM_AARCH64`。
- **B 命令行面（5）**：`-help` banner + usage；`-help` 记录
  `-orc/-bit/-bitout/-o/-ain/-aout/-cin`；`-license` 的 UC Berkeley BSD 三条款；
  无参数时打 usage 并以非零码退出（rc=255）；非法选项被拒绝并给出诊断（rc=255）。
- **C 上游示例（29）**：25 个可翻译示例全部翻译成功并含 `int main`（min 72 KB、
  elpelele 760 KB、pc 392 KB…），每行的选项都照该示例自己的 Makefile 首行
  `$(SFRONT)` 调用（只去掉需要声卡或对端的 `-aout/-ain <声卡>`、`-session/-passphrase`）；
  加上「25/25 全部成功」的汇总断言、`-cin ascii` / `-cin linmidi` 的控制驱动确实
  进入生成程序（`ascii control driver` / `linmidi control driver`）2 条，以及一个手写的
  inline-instrument 乐谱也能翻译。
- **D 位流往返（7）**：min 编出 892 字节、bach 编出 6302 字节的 MP4-SA 位流，
  首字节是 `0x80` BIFS 起始码；两者都能用 `-bit` 解回等价程序；`-symtab` 让位流
  从 892 涨到 1003 字节且仍可解码。
- **E 诊断（1）**：畸形 SAOL 以非零码退出并给出 `Error occured near line`。
- **F 鸿蒙特有端到端（21）**：三组，每组都包含「用 OHOS 工具链编译生成程序 →
  断言 `e_machine == EM_AARCH64` → 运行 → 校验 WAV」（min 8 条、torvalds 8 条、
  upstream `mp4test` 5 条）。
  1. `examples/min`：渲染 176841 帧 44.1 kHz / 16 bit 单声道 PCM，167195 个非零样本。
  2. `examples/torvalds`：读入真实 8 kHz `english.wav`（41461 帧）做人声清理，
     渲染 41464 帧 8 kHz / 16 bit 立体声 PCM——输出覆盖全部输入，证明 WAV 解码与
     信号链在 OHOS 上真的跑了。
  3. upstream `mp4test` 流程：min 的 `-bitout` 位流解回的程序与 `-orc` 直译出的
     程序渲染出**逐字节相同**的 WAV。
- **G 载荷完整性（3）**：Slib/reson 10 个文件齐全；26 个 `.saol` + 20 个 `.sasl`
  齐全；手册、`book/`、两份许可证齐全。

关于位流往返的一个坑：**不能在文本层比较 `-orc` 与 `-bit` 的输出**。`-bit` 解出来的
程序会把 SAOL 标识符重命名成 `a7_*` 之类的自动名（`-symtab` 也保留不了原名），浮点
字面量从 `1.95F` 变成 `1.950000e+00F`——值相同、写法不同。有意义的等价性判据在音频
样本层：min 两条路径逐字节相同；bach 的乐器求和顺序会变，2976792 个采样里 2868555 个
（96.4%）不同、最大偏差 13755，因此 bach 只做「解回等价程序」的结构断言，不做采样级
比对。

## 打包时的清理

上游 `examples/` 与 `book/` 里带 macOS 资源派生残留（6 个 `.DS_Store` + 32 个 `._*`）。
它们不属于软件本体，`package()` 用 `excludes=["*.DS_Store", "._*"]` 排除。

## 未采纳的做法

- 不 `patch` `-m32`：整体覆盖 `CFLAGS` 即可，不需要改上游源码。
- 不引入 `tool_requires bison/3.8.2`：官方 tarball 自带 bison 2.3 的解析器产物，
  重新生成只会让构建多一个依赖，且产物与随包版本无功能差异。
- 不为了「能过测试」而删掉 `examples/rtime/linbuzz` 的说明：如实记录该示例在 OHOS
  上不可翻译的原因（上游硬编码 `gcc` + `/usr/share/sfront`）。
