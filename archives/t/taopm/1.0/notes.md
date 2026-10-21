# taopm 1.0 OHOS 适配记录

## 1. 结论

- 上游 Tao（`taopm`）1.0-beta 是 1999–2006 年的 C++ 物理建模声音合成包：`libtao`
  合成引擎 + `taoparse`（`.tao` 脚本 → C++ 翻译器）+ `tao2wav`/`tao2aiff`
  （`.dat` → WAVE/AIFF，依赖 libaudiofile）+ OpenGL/GLUT 乐器可视化器。
- OHOS 没有桌面 GL/GLUT（只有 EGL + GLES），**图形可视化器无法通过链接解决**，
  需要把整个 `TaoGraphicsEngine.cc`（立即模式 GL + GLUT 事件循环）重写为
  GLES3/EGL 离屏渲染才有意义；本 PR 采用**无图形（headless）**适配，
  保留全部发声功能。
- 配方不再运行上游 2006 年的 `configure`（其 GL/GLUT/X11 检查必然失败，且
  autoconf 2.13 / libtool 1.3 / `config.guess` 均不支持 aarch64/OHOS），改为
  按上游 `Makefile.am` 的源码清单显式编译，编译器取自 Conan profile（R33）。
- 源码级适配 3 个补丁：图形可选化、C++11+ 语言级修复、`TaoPitch` 名字缓冲区
  越界修复。其中第 3 个是本次用 AddressSanitizer 实测发现的真实内存越界
  （上游 20 年来一直靠 `exit(0)` 提前结束进程而未被触发）。
- 依赖（W0）全部已发布：`audiofile/0.3.6`、`bison/3.8.2`、`flex/2.6.4.2`、
  `m4/1.4.19`；`conan graph info` 解析结果为 `binary: Download`。
  真机复验时又发现 OHOS 的 bison/flex **运行期**还需要各自的数据目录与 m4
  （见 8.3），已在配方里修好。
- 本机验证（Windows 宿主，C++17 / MSVC 与 AddressSanitizer）通过：
  17 个 `libtao` 编译单元 + `tao2wav`/`tao2aiff` 全部编译成功、ASAN 无报错、
  API 测试渲染 220 Hz 弦（实测 216.5 Hz）11000 帧。
- **真机单包验证已完成**（`conan create` + test_package 全绿，exit 0）：
  libtao/taoparse/tao2wav/tao2aiff 构建通过，API 测试 11/11、
  `.tao` 脚本流水线（taoparse → 编译 → 运行 → 落盘）通过、
  tao2wav/taosf 产出的 WAVE 各 14/14 断言通过、产物 PIE+Full RELRO。
  另外把**上游 20 个示例乐谱**全部跑通（20/20 parse→build→run，14 个输出流）。
  详见第 8 节；状态 `built`（尚未 `conan upload`）。


## 2. 上游与源码

| 项 | 值 |
|----|----|
| 版本 | `1.0`（上游发布名 `tao-1.0-beta-10May2006`） |
| 官方源 | <https://sourceforge.net/projects/taopm/files/Tao/tao-1.0-beta-10May2006.tar.gz>（943.6 kB） |
| 配方使用 URL | <https://deb.debian.org/debian/pool/main/t/taopm/taopm_1.0.orig.tar.gz> |
| sha256 | `ff0af736ba991d7965be2ab6441c6f5010618f5de648d05ca3f4d56adef0d794` |
| 大小 | 943577 字节 |
| 顶层目录 | `tao-1.0-beta-10May2006/` |
| 许可 | GPL-2.0-or-later |

SourceForge 对本构建宿主返回 HTTP 403（直连和 `/download` 端点均如此），
因此改用 Debian 源码镜像的 quilt `orig` 包。二者等价性有据：

- Debian `taopm_1.0-7.dsc` 记录 `ff0af736ba99…d794 943577 taopm_1.0.orig.tar.gz`，
  与本地下载文件字节一致；quilt 3.0 的 `orig.tar.gz` 按规范必须是**未修改**的
  上游原始包。
- 包内顶层目录仍是上游的 `tao-1.0-beta-10May2006/`，文件数与 SourceForge
  release 页面标注的 943.6 kB 一致。

R39 允许在证明等价后使用权威镜像；主源（SourceForge）已在
`conandata.yml` 注释中记录，后续若需要在 CI 中切换只需改 URL。

## 3. 构建系统分析

上游为 autotools（autoconf 2.13 / automake 1.4 / libtool 1.3），
`configure` 与 `Makefile.in` 都是预生成并随包发布的。

`configure.in` 的硬性检查（缺一即 `AC_ERROR` 退出）：

| 检查 | 作用 | OHOS 现状 |
|------|------|-----------|
| `AC_CHECK_LIB(audiofile, afInitFileFormat)` | `.dat` → WAV/AIFF | 已发布 `audiofile/0.3.6` ✔ |
| `AC_CHECK_LIB(m, sin)` | 数学库 | libc/libm ✔ |
| `AC_CHECK_LIB(MesaGL/GL, glBegin)` | 桌面 GL | **不存在** ✘ |
| `AC_CHECK_LIB(MesaGLU/GLU, gluNewQuadric)` | GLU | 需要桌面 GL 实现 ✘ |
| `AC_CHECK_LIB(glut, glutInitDisplayMode)` | GLUT 窗口 | 仅有 EGL-pbuffer/GLES2 版 freeglut ✘ |
| `AC_PATH_X` / `AC_PATH_XTRA` | X11（GUI 用） | 本适配不链接 ✘ |
| `AC_CHECK_LIB(pthread, …)` | 可选 | 非必需 |
| `AM_PROG_LEX` / `AC_PROG_YACC` | taoparse | bison/flex 已发布 ✔ |

构建产物（`Makefile.am`）：

- `libtao`：18 个编译单元，其中 `TaoGraphicsEngine.cc` 是唯一引用 GL/GLUT 的文件；
  `Tao.h`/`taodefs.h` 无条件 `#include "TaoGraphicsEngine.h"`，`class Tao` 里也有
  `TaoGraphicsEngine graphicsEngine;` 成员——所以"不要图形"必须改头文件，不能只改链接。
- `taoparse`：`taoparser.yy`（bison）+ `taoscanner.ll`（flex）在构建期生成代码。
- `tao2wav` / `tao2aiff`：各带一份私有的 `audiofile.h`/`aupvlist.h`（上游就是这样，
  链接 `-laudiofile`）。
- `user-scripts/tao`、`tao-config`：由 `configure` 替换 `@TAODIR@`/`@CXX@` 等占位符
  生成的**运行期编译脚本**；`taosf` 是静态 shell 脚本（无需替换）。
- 上游没有测试套件：没有任何 `Makefile.am` 声明 `TESTS`，`make check` 为空，
  源码包内也没有 `tests/` 目录。

**为什么不用 `./configure`**

1. 上述 GL/GLU/GLUT/X11 检查在 OHOS 上必然 `AC_ERROR` 退出；
2. 想加 `--disable-graphics` 就要重新生成 `configure`，而 `configure.in` 使用了
   `AM_PROG_LIBTOOL`、`AC_DIVERT_PUSH`、`AM_SANITY_CHECK`、单参数 `AC_INIT`，
   现代 autoconf/automake 已移除这些宏；libtool-1.3 的 `config.guess` 也不认识
   aarch64/ohos；
3. 上游 `Makefile.am` 只是 `lib_LTLIBRARIES` / `bin_PROGRAMS` 声明，没有额外的
   安装逻辑或测试钩子，显式编译与上游构建等价且可控。

## 4. OHOS 平台约束与取舍

- OHOS SDK 只提供 EGL + GLES（`libEGL.so` / `libGLESv2.so`），没有 `libGL.so`、
  没有 GLX。
- 仓库已发布 `freeglut/3.6.0`，但它是 **EGL pbuffer 离屏 + GLES2** 适配版，
  GL 调用经 `eglGetProcAddress()` 派发；而 OHOS GLES 驱动**不导出立即模式入口**
  （`mupdf-gl` 适配记录中实测 `eglGetProcAddress("glBegin") == NULL`、
  `"glEnd"`、`"glVertex2f"` 均为 NULL）。
- `TaoGraphicsEngine.cc`（19 KB）通篇是 `glBegin/glEnd/glVertex3f/glColor3f` +
  `glu*` + GLUT 回调/主循环，属于"必须重写"而不是"必须适配"的范畴。
- 因此本包**关闭图形**（`-DTAO_NO_GRAPHICS`），保留：
  `libtao` 合成引擎、`taoparse` 脚本翻译器、`tao2wav`/`tao2aiff`/`taosf`、示例乐谱。
  程序仍接受 `-g`（`tao` 启动脚本会传），但只打印一行提示并继续无图形合成。

## 5. 依赖（W0 检查结果）

`conan download <ref> -r=ohpcd --only-recipe`（R35：不用 `conan list` 判断），
本机与真机各验证一次：

| 依赖 | 版本 | 用途 | 结论 |
|------|------|------|------|
| `audiofile` | 0.3.6 | tao2wav/tao2aiff 链接 | PUBLISHED |
| `bison` | 3.8.2 | taoparse 构建期生成 parser | PUBLISHED |
| `flex` | 2.6.4.2 | taoparse 构建期生成 scanner | PUBLISHED |
| `m4` | 1.4.19 | bison/flex 运行期外部工具 | PUBLISHED |

`m4` 最初是 audiofile 的 autotools 链带进来的传递依赖，真机验证时发现
**flex 依赖它**，于是改为本包显式 `tool_requires("m4/1.4.19")`（见 8.1）。

`conan graph info archives/t/taopm/1.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`
解析结果（exit 0）：

```
label: conanfile.py (taopm/1.0)      binary: None (本地配方)
label: audiofile/0.3.6               binary: Download
label: bison/3.8.2                   binary: Download
label: flex/2.6.4.2                  binary: Download
label: m4/1.4.19                     binary: Download
```

无缺失依赖 → 不需要拆依赖 PR。

## 6. 补丁

### 0001-ohos-build-without-gl-graphics.patch

把可视化器变成编译期可选项（`TAO_NO_GRAPHICS`），共 10 个文件：

- `include/Tao.h`：`TaoGraphicsEngine.h` 的 include 与 `graphicsEngine` 成员加 guard；
- `include/taodefs.h`：同上 include guard；
- `libtao/Tao.cc`：`masterTick()` 两处每 tick 的视图更新、`main()` 的
  `graphicsEngine.init()` / `mainLoop()` 分支加 guard；`-g` 改为打印
  “this build has no graphics support; ignoring -g and synthesising headless”；
- `libtao/TaoAccessPoint.cc`、`TaoInstrument.cc`：访问点标记的显示调用加 guard；
- `libtao/TaoBow.cc`、`TaoConnector.cc`、`TaoHammer.cc`、`TaoStop.cc`、
  `TaoOutput.cc`：`display()` 整体加 guard；`TaoOutput` 构造函数里两个
  C++98 专属的 `ostringstream(char*, openmode)` 初始化也加 guard（置 `NULL`）。
- `taoparse/taoparser.yy`：脚本里的 `Label(...)` 是纯显示语句，生成代码为
  `tao.graphicsEngine.label(...)`；生成时用 `#ifndef TAO_NO_GRAPHICS` 包住，
  否则带 Label 的脚本（`examples/pitches.tao`）在无图形构建下无法编译。

`TaoGraphicsEngine.cc` 不参与编译（配方源码清单中已去掉）。

### 0002-cxx11-and-later.patch

让 1999 年的 C++ 能在 C++11+ 下编译：

| 位置 | 问题 | 处理 |
|------|------|------|
| 6 个 `libtao/*.cc` | `register` 存储类说明符（24 处）在 C++17 被移除 | 删除关键字 |
| `libtao/TaoDevice.cc` | `strcpy` 无 `<cstring>`（新 libc++ 不再传递包含） | 加 `#include <cstring>` |
| `libtao/TaoInstrument.cc` | `resetDamping()` 声明返回 `TaoInstrument&` 却无 return（UB，新编译器直接报错） | 返回链式调用结果 |
| `taoparse/taoparser.yy` | 生成的程序模板输出 `main(...)`（无返回类型，C++11 起非法） | 输出 `int main(...)` |
| `taoparse/taoparser.yy` | taoparse 自身 `main(...)` 同样缺返回类型 | `int main(...)` |
| `taoparse/taoparser.yy` | `yyerror(char *s)` 被文法自身和 bison 3.x 生成代码用字符串字面量调用，C++11 起不允许字面量转 `char*` | 声明与定义都改为 `const char *` |
| `taoparse/taoparser.yy`/`taoscanner.ll` | 使用 `strcat/strlen/strcpy` 无 `<cstring>` | 加 include |
| `taoparse/taoparser.yy` | 生成的程序先 include `taodefs.h`（其中 `min`/`samples`/`secs` 等
  单位宏）再 include 标准库头；现代标准库头里出现同名标识符（MSVC `<vector>` 用
  `(_STD min)`）会被宏改写导致编译失败 | 生成的程序先 include `<cmath>`/`<iostream>` |
| `tao2wav/tao2wav.cc`、`tao2aiff/tao2aiff.cc` | `main(...)` 无返回类型 | `int main(...)` + 显式 `return 0;` |

### 0003-taoPitch-name-buffers.patch

`TaoPitch` 的名字缓冲区有 3 个真实缺陷，C++11 之前被旧流构造函数"掩盖"：

1. `createName()` 先 `name=new char[12]`，再用 **C++98 才有的**
   `std::ostringstream(char*, openmode)` 写入。C++11 起同名调用会匹配
   `ostringstream(const std::string&)`，于是对**未初始化的 12 字节缓冲区**做
   `strlen`（堆越界读），并且流写进自己的内部缓冲、`name` 里留下未终止的垃圾，
   之后还会被 `strlen`/`delete[]`。改为先在 `std::string` 里拼好再按长度拷贝。
2. `TaoPitch(const char*)` 里 `new char[nameLength]` 却 `strcpy` 了
   `nameLength+1` 字节（堆写越界 +1）。改为 `+1`。
3. 默认构造函数不初始化 `name`，而 `~TaoPitch()` 会 `delete[] name`；`operator=`
   不释放旧值也不自赋值安全。一并修复。

AddressSanitizer 实测证据（修复前，仅构造一个 `TaoString`）：

```
ERROR: AddressSanitizer: heap-buffer-overflow
READ of size 13 at 0x... (12-byte region)
  #0 __asan_wrap_strlen
  #1 std::basic_string<...>::{ctor}
  #2 TaoPitch::createName() libtao/TaoPitch.cc:262
  #3 TaoPitch::TaoPitch(float) libtao/TaoPitch.cc:172
  #5 main (TaoString 构造)
```

修复后同一用例 ASAN 干净。

## 7. 本机验证证据（Windows 宿主，非 OHOS 工具链）

本轮没有占用真机，做了能在宿主上做的全部验证。

### 7.1 编译（C++17）

- 补丁对原始 tarball 的应用：`git apply --check` 与 `patch -p1 --dry-run` 三个补丁
  全部 OK；`patch -p1` 实际应用后与本地比对，除 `TaoPitch.cc` 中一处上游残留
  的混合换行被规范化外，字节一致。
- MSVC 19.40（`/std:c++17 /O2 /Zc:strictStrings`）编译 `libtao` 全部 17 个编译单元：
  0 error；`tao2wav.cc`、`tao2aiff.cc` 单独编译 0 error。`/Zc:strictStrings` 用来
  模拟 clang/gcc 对"字符串字面量 → `char *`"的严格检查（MSVC 默认放行）。
- 最后一轮用**仓库里提交的补丁文件**（而非本地工作副本）重新解包 → 应用 → 编译 →
  链接 → 运行，结果与下面 7.3 完全一致，确保"提交的就是验证过的"。
- 这说明：C++17 语言层面、头文件依赖、`TaoGraphicsEngine` 摘除后的 API 一致性
  都成立（用 `-DTAO_NO_GRAPHICS` 与包 `cpp_info.defines` 一致）。

### 7.2 运行（AddressSanitizer）

- 修复 0003 之前：`TaoString(TaoPitch(220, frq), 10)` 构造即触发
  `heap-buffer-overflow`（见第 6 节）。
- 修复之后：同一路径（构造 → 锁定两端 → 每 tick 读取访问点 → `TaoOutput` 落盘）
  ASAN 无任何报错，进程正常退出。

### 7.3 功能测试（test_package 的 test_tao_api，宿主实跑）

```
ticks=22051 samples=11000 rate=44100 channels=1
peak=6.99454 rms=3.94828 mean=0.0287717 est_hz=216.491
[ ok ] TaoOutput created the .dat stream
[ ok ] stream starts with the TAO OUTPUT FILE magic
[ ok ] stream records the configured 44100 Hz rate
[ ok ] stream records a single mono channel
[ ok ] stream holds the expected number of samples
[ ok ] stream is written in whole 500-sample buffers
[ ok ] every rendered sample is finite
[ ok ] the plucked string produced an audible signal
[ ok ] rendered signal carries energy above the noise floor
[ ok ] rendered samples stay in a sane physical range
[ ok ] zero-crossing estimate is within an octave of the 220 Hz string
tao synthesis API test passed
```

Release 与 ASAN 两次运行结果完全一致（引擎用 `srand(0)`，确定性）。
零穿越估计 216.5 Hz 对 220 Hz 定弦，说明物理模型确实在振动而不是噪声。

### 7.4 过程中发现的上游行为（已记录，未改）

- `TaoOutput` 写 `.dat` 用的 `std::ofstream` **没有**以 `binary` 打开，因此在有
  CRLF 文本转换的宿主（Windows）上，payload 里每个 `0x0A` 会变成 `0x0D 0x0A`，
  文件长度不再是 4 字节对齐。OHOS/Linux 文本模式与二进制一致，**不受影响**；
  `test_tao.cpp` 读取时按"写入方式"做了对称还原，两端都成立。
- `TaoSynthEngine::currentInstrument/currentDevice` 未在构造函数初始化（首次
  `addInstrument/addDevice` 才赋值）；当前路径不会读到未初始化值，未改。

## 8. 真机验证（已完成，2026-10-18）

### 8.1 环境与隔离

- 设备：HarmonyOS PC（aarch64，HongMeng 1.12.0），clang 15.0.4、CMake 4.1.2、
  conan 2.29.1/2.31.1（shadow python）、git 在 `/data/service/hnp/bin`。
- 单包排队：通过 `~/bin/ohos-test-runner.sh --mode heavy --try-lock`
  （锁忙时 75 直接退出）执行，运行目录
  `~/ohos-test-runs/taopm-taopm-conan-create-r7-20261018-145152-58550`，
  `logs/exit-code.txt` = **0**。
- 隔离：`~/taopm-dev/1.0-r1/{repo,conan-home,work}`，`CONAN_HOME` 指向
  `conan-home`，其中预置了设备的 `settings.yml`（含 `OHOS`）、`remotes.json`
  （`ohpcd`）与 `profiles/ohos-aarch64`（避坑指南第 10 条）。
  设备仓库 `~/build_in_harmonyos` 是**另一个会话的工作区**（main、34 个未提交
  改动、且没有 `ci/` 目录），所以没有在其中切分支，而是把本包 16 个文件打成
  tar 传到隔离目录后再 `conan create`。
- 命令（r7 实际执行）：

  ```sh
  conan create archives/t/taopm/1.0 --user=ohpcd --channel=stable \
      -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
  ```

### 8.2 结果

构建与打包：

- `libtao` 17 个编译单元用 clang 15、`-std=c++17 -O2 -DTAO_NO_GRAPHICS` 编译通过；
  `llvm-ar` + `llvm-ranlib` 归档出 `lib/libtao.a`（17 个成员）。
- `bison`/`flex` 生成 `taoparser.cc`/`taoscanner.cc` → 编译链接出 `bin/taoparse`。
- `bin/tao2wav`、`bin/tao2aiff` 链接 `audiofile/0.3.6` 成功。
- 包内容：`bin/{taoparse,tao2wav,tao2aiff,taosf}`、`include/`（20 个头文件，
  已剔除 `TaoGraphicsEngine.h`）、`lib/libtao.a`、`licenses/COPYING`、
  `share/tao/examples`（20 个 `.tao` 示例）。

`test_package` 三阶段（真机实际运行）：

1. `test_tao_api` —— 库 API 合成，11/11 断言通过：

   ```
   ticks=22051 samples=11000 rate=44100 channels=1
   peak=6.99466 rms=3.94833 mean=0.0287713 est_hz=216.491
   [ ok ] ...（11 项全部 ok）
   tao synthesis API test passed
   ```

   与本机 MSVC 结果（peak 6.99454 / est 216.491 Hz）一致，差异仅来自编译器浮点。
2. `test_tao_script` —— `taoparse` 在构建期把 `test_script.tao` 翻成 C++ 并编译，
   运行时 `tao.main()` 无图形跑完 1 秒乐谱，打印 `Sample rate=44100 Hz`、
   `Score duration=1 seconds`，写出 `test_script_out1.dat`（stereo）与
   `test_script_out2.dat`（mono）。
3. `tao2wav` + `check_wav`：立体声 176044 字节 WAV，
   `channels=2 rate=44100 bits=16 peak=32700 distinct=87983`，14/14 断言通过；
   `taosf`（shell 助手，经 PATH 找 `tao2wav`）转出单声道 88044 字节 WAV，
   14/14 断言通过。

L4 加固（`llvm-readobj`）：三个可执行文件均为 `SharedObject (PIE)` +
`PT_GNU_RELRO` + `PT_GNU_STACK` + `BIND_NOW`（Full RELRO）。
L2 等价的冒烟：`taoparse` 无参打印 `usage: taoparse <tao_script_file>`，
`tao2wav` 无参打印 `usage: taosf <infile> <outfile>`。

### 8.2b 上游示例乐谱全量（20/20）

上游没有测试框架，其"可执行资产"就是 `examples/` 里的 20 个 `.tao` 乐谱。
除了 test_package 里的缩短版脚本，另在真机把**全部 20 个上游示例**跑了一遍
（`taoparse` → 用打包的 `libtao` 编译 → 运行）：

```
total=20 parse_ok=20 build_ok=20 run_ok=20      # 14 个 .dat 输出流
accesspoint1/2, bow, circle, circle2, connector, damp, diffraction,
ellipse, ellipse2, hammer, lock, outputarray, outputs, pitches,
rectangle, rectangle2, stop, string, test        # 全部 RUN rc=0
```

- 运行目录：`~/ohos-test-runs/taopm-taopm-upstream-examples-r2-20261018-150709-583`
  （`--mode smoke --try-lock`，exit 0）。
- 首轮（r1）时 `pitches` 失败：它用了 `Label(...)` 显示语句，生成代码
  `tao.graphicsEngine.label(...)` 在无图形构建下编译不过 → 已在 patch 0001 里
  给生成模板加 `#ifndef TAO_NO_GRAPHICS` 守卫，第二轮 20/20。
- 各示例得分较长（5–30 秒），全量跑一次约 2–3 分钟；未放进 CI 的
  test_package（CI 只用 1 秒的缩短脚本 + 0.25 秒 API 测试保持快而确定性）。

### 8.3 真机首次运行踩到的坑（已修进配方/测试，勿回退）

1. **bison 数据目录**：OHOS 的 bison 包 prefix=`/`，运行期去
   `/share/bison/m4sugar/m4sugar.m4` 找数据 → `cannot open`。修法：
   `BISON_PKGDATADIR` 指向 **bison 包内**的 `share/bison`。
   ⚠️ **不要从 PATH 反推**（CI #98634 教训）：CI worker 预装了
   `/data/service/hnp/bin/bison`（prefix=`/data/service/hnp`），它比 Conan
   `tool_requires` 的副本更早命中 PATH，反推得到
   `/data/service/hnp/share/bison`（不存在）→ 同一份配方在本机通过、在 CI 失败。
   现在从 `self.dependencies.build` 取 bison **包目录**，并用包内
   `bin/bison` 的绝对路径调用，二进制与数据目录必然一致。
2. **flex 的 m4**：flex 二进制里写死了构建期的 m4 绝对路径
   （`~/.cache/conan2/p/m42d.../p/bin/m4`），消费端不存在 →
   `fatal internal error, exec of ... failed`。修法：显式
   `tool_requires("m4/1.4.19")`，并把 `M4` 指向 **m4 包内**的 `bin/m4`
   （同样不依赖 PATH，理由同上）。
3. **`taoparse` 的输出流命名**：实现是 `strtok(argv[0], ".")`，只保留第一个
   `.` 之前的部分。若传绝对路径（`.../1.0/test_script.tao`），流名会变成
   `.../1_out1` 并落到奇怪位置。修法：**必须用裸相对文件名**调用
   （`cd <dir> && taoparse test_script.tao`），test_package 的 CMake 已按此写。
4. **Conan 会缩短绝对命令路径**：`self.run('cd X && /abs/test_tao_script')`
   实际执行成 `./test_tao_script` → 127。修法：把要执行的二进制**复制到运行
   目录**，再用 `./name` 调用。
5. **`taosf` 需要 `tao2wav` 在 PATH 上**（脚本里是裸命令名），测试里显式把包的
   `bin/` 加到 PATH。
6. `test_package` 里 `self.cpp.build.bindirs[0]` 可能是相对路径（`"."`），需
   `os.path.abspath` 归一，否则构造出的绝对路径会变成自指软链接。
7. `make: jobserver mkfifo ... Operation not permitted` 是 HMDFS 不允许 mkfifo
   的**告警**，CMake 构建照常完成，可忽略。
8. **带 `Label(...)` 的脚本**：`Label` 是可视化注记，生成代码调用
   `tao.graphicsEngine.label(...)`；无图形构建必须在生成模板里用
   `#ifndef TAO_NO_GRAPHICS` 包住（`examples/pitches.tao` 是唯一命中的示例）。

### 8.4 CI 首轮失败与修复（PR #16744 / 构建 #98634）

CI（worker `OpenHarmonyPCDeveloper-CI-038`）在 `conan-build-test` 阶段失败：

```
taopm/1.0: BISON_PKGDATADIR="$(dirname "$(dirname "$(command -v bison)")")/share/bison"; ...; bison -d -o taoparser.cc ...
bison: /data/service/hnp/share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory
ERROR: taopm/1.0: Error in build() method, line 279
```

根因：当时用 `command -v bison` **从 PATH 反推**数据目录。CI worker 预装了
`/data/service/hnp/bin/bison`（prefix=`/data/service/hnp`，无 `share/bison`），
它比 Conan `tool_requires` 的副本更早命中 PATH；同一份配方在本机隔离环境通过、
到 CI 才失败（路径依赖环境，属"不可复现"型缺陷）。

修复：不再依赖 PATH。

- `_build_tool_folder()` 从 `self.dependencies.build` 取 tool_requires 的包目录；
- `_build_tool()` 用包内 `bin/<tool>` 的绝对路径调用 bison/flex/m4；
- `BISON_PKGDATADIR` 固定为 `<bison 包>/share/bison`，`M4` 固定为
  `<m4 包>/bin/m4`；两者缺失时直接抛 `ConanException`，不再静默回退 PATH。

回归验证（模拟 CI 环境）：在隔离 job 里把三个**假的** `bison/flex/m4` 放到
`PATH` 最前面（内容就是 CI 里那条 `cannot open` 报错），再跑 `conan create`：

```
RUN=taopm-taopm-cipath-test-r1-20261018-190712-43101  exit-code = 0
using bison: <cache>/p/bison.../p/bin/bison (BISON_PKGDATADIR=<cache>/p/bison.../p/share/bison)
using flex : <cache>/p/flex.../p/bin/flex  (M4=<cache>/p/m4.../p/bin/m4)
taoparse: test_script.tao -> tao_script_generated.cc
tao synthesis API test passed
CONAN_CREATE_EXIT=0
```

即：PATH 上的假工具完全没被使用，CI 的失败模式已被覆盖。

### 8.5 仍未做的验证

- 仓库 CI 门禁脚本（`ci/conan/build_and_test.sh` 的 L0a–L0k / L1 / L2 / L4 / L5）
  只在平台 CI 上跑过（首轮失败已修，复跑结果以 PR 评论为准）；本机没有 `ci/`
  目录，只用等价的单包 `conan create` + 手工 L2/L4/L5 检查替代。
- `conan upload` / release 未做（合并后由发布流水线完成）。
- `shared=True` 分支未在真机验证（默认静态；共享分支带 OHOS 签名逻辑）。

## 9. 命令

已在真机执行并通过：

```sh
# 单包构建 + test_package（隔离 CONAN_HOME + runner 全局锁）
bash ~/bin/ohos-test-runner.sh --user taopm --lib taopm --task conan-create-r7 \
    --mode heavy --try-lock --workdir ~/taopm-dev/1.0-r1/repo -- \
    bash ~/taopm-conan-create.sh      # 内部：conan create ... --build=missing
```

仍待执行（需要带 `ci/` 的仓库与 CI 账号）：

```sh
# 提交前单包 CI（只跑目标包，禁止无参扫描全仓）
CI_PACKAGES="archives/t/taopm/1.0" zsh ci/conan/build_and_test.sh
# shadow CI 运行器
/path/to/run-ohos-shadow-ci.sh archives/t/taopm/1.0
```

检查点：`Build Summary` 为 `Total: 1`；L0/L1 pass；L2 用无参 usage 兜底；
L4 已手工确认 PIE/RELRO/NX；L5 产物 `bin/*`、`lib/libtao.a`、`include/*.h`
（真机已核对存在）。

## 10. 状态

- 分支 `feat/taopm-1.0`，worktree `D:\harmonyos\worktrees\taopm`（本记录所在提交即
  该分支最新 commit）。该 worktree 用 sparse-checkout（只落地 `archives/t/taopm/`），
  因为完整工作树有 13.5 万个文件、`git worktree add` 在本机会在 `reset index`
  阶段失败；需要完整树时 `git sparse-checkout disable` 或按需追加目录。
- 状态 **built**：真机 `conan create` + test_package 全绿（`conan-create-r7`、
  加 Label 守卫后 `conan-create-r8`），上游 20 个示例 20/20（`upstream-examples-r2`）；
  尚未 `conan upload`。
- 已知限制：无图形可视化器（`tao -g`）；`user-scripts/tao`、`tao-config` 这两个
  configure 生成脚本未安装（依赖运行期 C++ 编译器与 configure 模板），
  使用者用 `taoparse x.tao > x.cc` + 手工编译（test_package 演示了完整流程）。
