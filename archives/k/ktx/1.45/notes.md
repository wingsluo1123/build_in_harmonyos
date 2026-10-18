# ktx 1.45 适配笔记（HarmonyOS PC / OHOS aarch64）

## 1. 这个软件是什么

**KTX = Kombat Teams eXtreme**，[QW-Group/ktx](https://github.com/QW-Group/ktx)
维护的 **QuakeWorld 服务器 mod**（不是独立可执行程序）。Debian sid / trixie 收录为
`ktx` 包（1.45-1），上游同时发布 linux-amd64 / i686 / aarch64 / armhf 预编译二进制。

- 上游 tag：`1.45`（commit `d05d6ca6dae1a8b5a1ea23aa9e33f6d99bcc9102`）
- 源码 URL：`https://github.com/QW-Group/ktx/archive/refs/tags/1.45.tar.gz`
- sha256：`3bf0e78569fa7d352a2e825257ea37d1e2423480c94f0d18fa58dc265f54288c`

运行形态：QuakeWorld 服务器（推荐 MVDSV，FTEQW 未确认）`dlopen()` 加载
`qwprogs.so`，再调 `dllEntry()` 把自己的 syscall trampoline 交给 mod。

## 2. W0 依赖发布检查

`requirements()` 为空 —— **ktx 1.45 无任何第三方依赖**，因此 W0 无需
`conan download` 探测。实测依据：

- `src/` + `include/` 全树 `#include <...>` 只出现标准 C 头：
  `assert.h ctype.h limits.h math.h stdarg.h stdint.h stdio.h stdlib.h string.h time.h`
- 上游 `CMakeLists.txt` 只 `target_link_libraries(qwprogs PRIVATE m)`（libm）

libm 属系统库，不进 `requires()`，在 `package_info()` 里以
`cpp_info.system_libs = ["m"]` 声明。

## 3. W0b 历史经验核验

- `archives/k/ktx/` 在 `origin/main` **无历史归档**，因此没有可继承的历史 notes.md。
  同族先例是 `archives/b/basis_universal/2.1.0`（CMake + 自研 test_package），
  已对齐其结构；dlopen 型插件的测试形态对齐 `archives/a/abiword-plugin-*/3.0.8`。
- **CI 能力矩阵核对**：ktx 只需要 `cmake` + `cc`（gcc/clang ✅）——
  不需要 Rust / OCaml / NASM / 任何冷门工具链，CI 干净环境可逐字复现本地命令。

## 4. 构建产物形态（决定了配方与测试形态）

上游 `CMakeLists.txt` 只声明一个交付物：

```cmake
add_library(qwprogs SHARED ${SRC_COMMON} ${SRC_NATIVE})
set_target_properties(qwprogs PROPERTIES PREFIX ""   # -> qwprogs.so，没有 lib 前缀)
target_link_options(qwprogs PRIVATE "-Wl,--no-undefined")
```

所以本包是**纯库包**（`lib/qwprogs.so`），不是命令行工具 ⇒ 按 **R38 不需要
软件级 `commands.json`**。

上游还有一个 `qvm` 目标（把同样的 C 源码用 id Software `q3lcc` TinyC 编译器
编成 QVM 字节码），以及 `tools/q3asm`（汇编器）。二者都是
`EXCLUDE_FROM_ALL` / 按需依赖，**默认 `all` 目标不构建**。配方显式
`FTESV=OFF` 且只跑默认目标，**不引入 q3lcc**——它在任何 OHOS 工具链里都不存在，
引入即等于 `env_unsupported`。

## 5. OHOS 适配：零补丁

实测（profile `ohos-aarch64-wsl`，clang 15，target `aarch64-linux-ohos`）：

- 配置 + 编译 **零 error**，唯一 warning 是上游自身的
  `src/bot_aim.c:237 variable 'vol_flags' set but not used`（与平台无关）。
- 产物 `lib/qwprogs.so`：`ELF 64-bit LSB shared object, ARM aarch64`
  - `e_type = ET_DYN`、`e_machine = EM_AARCH64 (183)`
  - `DT_SONAME = qwprogs.so`（相对路径，满足 CI **L5a**）
  - `DT_NEEDED = libc.so`（**musl**，无绝对路径 / `../`，满足 CI **L5b**）
- **不需要任何 patch**，因此 `patches/` 目录不存在、`conandata.yml` 无
  `patches` 段 —— 也就不可能触发 PF5（补丁平台宏闸）。R8 无例外需要论证。

### 5.1 打包命名：为什么保留无 `lib` 前缀的 `qwprogs.so`，且不声明 `cpp_info.libs`

这是本包唯一需要解释的设计决定，也是本次适配里**唯一踩到的真问题**。

**现象**：最初按常规把 `cpp_info.libs = ["qwprogs"]` 写进配方（产物保持上游名
`qwprogs.so`），`conan create` 在 **test_package 阶段**直接失败：

```
CMake Error at generators/cmakedeps_macros.cmake:81 (message):
  Library 'qwprogs' not found in package.  If 'qwprogs' is a system library,
  declare it with 'cpp_info.system_libs' property
Call Stack: ktx-Target-release.cmake:23 (conan_package_library_targets)
```

**根因**：Conan CMakeDeps 用
`find_library(NAMES qwprogs PATHS <pkg>/lib NO_DEFAULT_PATH)` 解析
`cpp_info.libs`。本工具链的 CMake `CMAKE_FIND_LIBRARY_PREFIXES=lib`，**不会尝试
无前缀文件名** —— 空 project 里单独验证 `find_library(NAMES qwprogs ...)` 同样
`NOTFOUND`。所以「上游 PREFIX "" + 标准 cpp_info.libs」这个组合在 Conan 里
**根本无法被任何 CMake 消费者消费**。

**为什么不改名成 `libqwprogs.so`**（试过，更差）：

1. `find_library` 确实能过了，`find_package(ktx)` 也过了；
2. 但 DT_SONAME 仍是上游的 `qwprogs.so`，与安装文件名 `libqwprogs.so` **不一致**。
   只要消费者**链接**该库，运行期立刻
   `Error loading shared library qwprogs.so: No such file or directory` +
   `Error relocating ...: dllEntry: symbol not found`（实测复现）。
3. 改 SONAME 只能动上游 `CMakeLists.txt`（那是一次 source patch），或者靠
   `-Wl,-soname` —— 实测**无效**：CMake 自己会在链接命令末尾追加
   `-Wl,-soname,qwprogs.so`（由 `OUTPUT_NAME` 推导），用户
   `CMAKE_SHARED_LINKER_FLAGS` 在它前面，lld 取后者，仍然是 `qwprogs.so`。
   要压过它只能设 `NO_SONAME` 属性，那也要改 `CMakeLists.txt`。

**结论（最终方案，零 hack、零 patch）**：

- 保留上游文件名与 SONAME：`lib/qwprogs.so`（两者天然一致，这也正是服务器按裸名
  加载所需要的形式）；
- **`cpp_info.libs` 故意留空**。这不是「漏填」：ktx 是 **dlopen 型插件**，
  唯一导出符号 `dllEntry` 的语义是「由宿主 `dlsym` 调用」而非「消费者链接」，
  其余符号被上游 `C_VISIBILITY_PRESET hidden` 全部隐藏。声明一个无法被
  CMakeDeps 解析的 `libs` 反而会让**所有** `find_package(ktx)` 直接 FATAL_ERROR，
  那才是真正的缺陷。`includedirs` / `libdirs` / `system_libs` / `ktx::ktx`
  目标照常提供。

### 5.2 导出符号面

`C_VISIBILITY_PRESET hidden` + 只有两处 `VISIBILITY_VISIBLE`
（`include/q_shared.h:77`），实测 `.dynsym` 中 **defined & GLOBAL** 仅 4 个：

| 符号 | 含义 |
|------|------|
| `dllEntry` | QuakeWorld 服务器 mod 入口（服务器把 syscall trampoline 交给它） |
| `vmMain` | QVM 风格入口（1.45 原生构建里同样导出） |
| `_init` / `_fini` | 链接器生成 |

`src/g_syscalls.c` 的 `dllEntry()` 实现只是 `syscall = syscallptr;`——**纯指针
握手，不跑任何游戏代码**，因此可以在测试里安全直接调用。

## 6. 测试设计（R34 真测试 / rule12 鸿蒙特有测试）

上游**完全没有自动化测试**（已核实 tag 1.45 整树无 `tests/` 目录，唯一的
`.github/workflows/main.yml` 只做交叉编译）。因此
`test_package/ktx_module_test.c` 是适配自研，做的事**正是 QuakeWorld 服务器
对这份产物做的事**：

1. `dlopen(lib/qwprogs.so, RTLD_NOW|RTLD_LOCAL)` —— 真实加载真机产物，
   `RTLD_NOW` 强制全部重定位，证明没有解析不了的符号；
2. `dlsym("dllEntry")` / `dlsym("vmMain")` —— 服务器面 ABI 可解析；
3. `dlsym("trap_GetApiVersion")` / `dlsym("G_InitGame")` 必须为 `NULL` ——
   验证 hidden 可见性在 OHOS 构建里真的生效；
4. `dllEntry(stub_syscall)` —— 真实执行服务端握手；
5. `dlclose()` 干净卸载 + 二次 `dlopen` 幂等；
6. 直接解析 ELF 头 / section / dynamic 表，断言**鸿蒙特有属性**：
   `ELFCLASS64`、小端、`ET_DYN`、`EM_AARCH64`、`DT_SONAME == qwprogs.so`、
   `DT_NEEDED == libc.so`(musl) 且无绝对路径或 `../` 逃逸、
   导出符号面恰为 `{dllEntry, vmMain, _init, _fini}`；
7. 产物 > 100 KiB 反「空壳构建」。

`test_package/CMakeLists.txt` 仍然 `find_package(ktx REQUIRED)` 并链接
`ktx::ktx` 的头文件路径 —— 验证配方生成的 CMake 配置确实可被下游消费
（即 5.1 里那个 `Library 'qwprogs' not found` 类缺陷不会复发）。

**L1e 反向破坏可证真**：CI 的 L1e 会把包内 `lib/` 整体移走再 `conan test`。
本测试以 `dep.package_folder/lib/qwprogs.so` 为唯一被测输入，`lib/` 被移走后
`test()` 首个检查即 `RuntimeError` ⇒ L1e 必然判「真测试」。

## 7. 已知限制（如实记录）

- KTX 是 **QuakeWorld 服务器 mod**，需要配套 QuakeWorld 服务器（MVDSV/FTEQW）
  与 QuakeWorld 游戏数据才能真正跑一局比赛；HarmonyOS PC 上目前没有 QuakeWorld
  服务器，因此**无法做端到端对局测试**，本包只保证「模块可在 OHOS 上被
  dlopen 并完成 ABI 握手」。
- QVM 字节码变体**未适配**（需要 id Software `q3lcc`，CI 无此工具链）。
  若后续需要，应作为独立包（`ktx-qvm`）立项，而不是在本配方里加开关。
- `include/ktx/*.h` 是 mod 的内部结构头（`g_local.h` 等互相 include），
  单独编译某个头不保证自洽；随包提供是为了让消费者能拿到 ABI 定义。

## 8. 知识库

本次适配**未命中**已有知识图谱错误模式（构建零错误、零补丁），因此
`knowledge/drafts/` 只登记本次新增的**结构型经验草稿**（dlopen 型 mod 的
包形态与测试形态 + 5.1 的 `cpp_info.libs`/无前缀 `.so` 陷阱），不含伪造的错误条目。
## 9. CI 环境适配：构建并行度钉为 1（2026-10-16）

上游 `qwprogs.so` 单目标由约 40 个 `.c` 编译单元组成，`cmake.build()` 默认按
`tools.build:jobs`（= worker 的 CPU 数）并行展开。OHOS worker 在并发任务多时会出现
**进程/PID 资源枯竭**，`make` 派生的 `/bin/sh` 直接失败：

```
/bin/sh: can't fork - try again
make[2]: *** [CMakeFiles/qwprogs.dir/build.make:106: CMakeFiles/qwprogs.dir/src/arena.c.obj] Error 1
→ ktx/1.45: Error in build() method, line 108 cmake.build() → conan create failed
```

（CI #94773，2026-10-16 14:03；日志里 `can't fork` 成片出现，同批 ktx 构建多次因此失败。）

处置：`cmake.build(cli_args=["--parallel", "1"])`，把编译并行度降为 1，避开 fork 风暴。
仓内同类先例：`julius/1.8.0`（`cmake.build(cli_args=["--parallel","1"])`，R9/HMDFS
jobserver 坑）、`box2d/2.4.1`（`tools.build:jobs=1` + `CMAKE_BUILD_PARALLEL_LEVEL=1`）、
`threadweaver5/5.116.0`（`CMAKE_BUILD_PARALLEL_LEVEL=1`）、`meterec/0.9.3` 与
`musicpc/0.35`（`-j1`）。

**只降低并行度，不改变编译产物内容，也不改变任何测试判定**；本包零补丁、零源码改动的
结论不变。
