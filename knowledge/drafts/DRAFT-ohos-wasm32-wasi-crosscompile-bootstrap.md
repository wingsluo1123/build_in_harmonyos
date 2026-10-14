# DRAFT: OHOS 上编译到 wasm32-wasi 目标——自举静态交叉工具链

## 现象（错误面）

在 OHOS PC 上构建任何以 `wasm32-wasi/wasip1` 为目标的库（如 wasi-libc）时：

1. `clang --target=wasm32-wasip1 ...` →
   `error: unable to create target: 'No available targets are compatible with
   triple "wasm32-unknown-wasip1"'` —— OHOS 全系编译器（harmonybrew clang
   23.1.1、OHOS SDK clang 15.0.4）都**没有编入 WebAssembly 后端**
   （`clang --print-targets` 列表无 wasm）。
2. 换官方 wasi-sdk `arm64-linux` 发行版 → 无法执行：其 ELF interp 为
   `/lib/ld-linux-aarch64.so.1`（glibc 动态链接），OHOS 为 musl 用户态。
3. 借用 zig（内嵌 clang+LLVM 19）编译后，链接报
   `__heap_end: undefined symbol` —— SDK 自带 LLD **15.0.4** 缺该链接器
   伪符号（上游 dlmalloc 与 `linker-provided-symbols.txt` 依赖，
   `>=15.0.7` 才合成）。
4. `-shared` 链接 `libc.so` 报
   `relocation R_WASM_MEMORY_ADDR_SLEB cannot be used against symbol __heap_end`
   或 `entry symbol not defined (pass --no-entry)`：LLVM 15 驱动对 wasm
   共享库仍用 command 模型 crt，把静态 dlmalloc 拖进共享对象。

## 根因

OHOS 工具链按宿主目标裁剪后端与链接器能力；wasm 交叉编译的三个前提
（编译器 wasm 后端、可执行的 wasm 工具链发行版、现代 wasm-ld）在平台上
均不存在，须整套自举。

## 推荐做法（已在 wasi-libc 0.0-git20260129.ec0effd 验证）

1. **自举静态 Zig 0.14**（官方 tarball 静态链接、内嵌全目标
   clang+LLVM 19）：下载后用 SDK `binary-sign-tool sign ... -selfSign 1`
   自签名方可在 OHOS 执行（签名族知识见
   DRAFT-below-ohos-unsigned-rust-toolchain / E318）。
2. **双面 clang 包装器**（作 CMAKE_C_COMPILER）：
   - 编译作业（`-c/-E/-S`）→ `zig cc`：
     - `--target=wasm32-wasip1` → `-target wasm32-wasi -D__wasip1__`
       （zig 的 target 查询只认 "wasi" OS 名；LLVM 19 把 `wasm32-wasi`
       规范化为同一 `wasm32-wasip1` triple；`__wasip1__` 宏须显式补回，
       否则上游源里 `#if defined(__wasip1__)` 分支全灭）；
     - **剪除** zig 自带 `lib/libc/include/{wasm-wasi-musl,generic-musl,
       wasm32-wasi-any,any-wasi-any}`：zig 注入的 isystem 先于用户
       `-isystem`，会遮蔽目标 sysroot（现象：`sched.h` 解析到 zig 旧版、
       `struct sched_param` 不完整）。**不要**用 `-isystem→-I` 提升来
       赢顺序（见禁则 2）；
     - `-mllvm -wasm-enable-sjlj`（setjmp/longjmp 对象）附加
       `-mexception-handling`：`__builtin_wasm_throw` 编译期要求该
       target feature；
     - argv 必须逐字保留（计数 shift/append 队列）——
       `-D__wasilibc_printscan_full_support_option="add ... to the link
       command"` 这类带空格定义被字符串重组拆碎后，碎片 `to` 会被当
       输入文件：`error: to: unrecognized file extension`。
   - 链接作业（纯 .o/.a 输入）→ **OHOS SDK clang 15 驱动** +
     `-B<wrapper-bin>` 提供 `wasm-ld` shim（`exec zig wasm-ld`，
     LLD 19.1.7）：驱动按 `--sysroot` 解析 crt1.o/libc.a（wasi-sdk 同款
     流程），代码生成永不发生；`-shared` 时加 `-mexec-model=reactor`
     对齐 LLVM 19 驱动行为（reactor crt 不引用 `__main_void` 链，
     静态 dlmalloc 不被拖入，`__heap_end` 数据引用不再出现）。
   - 应答 `--print-libgcc-file-name` / `-print-resource-dir` 查询时给
     **一致的绝对路径对**（如 `/__res` + `/__res/lib/wasip1/
     libclang_rt.builtins-wasm32.a`）：cmake 的 `cmake_path(RELATIVE_PATH)`
     据此把 compiler-rt builtins 拷到构建期临时 resource-dir 下驱动
     查找的 `lib/wasip1/` 子路径。
3. **测试引擎**：上游默认下载的 wasmtime 为 glibc 二进制不可执行 →
   Node.js 内建 WASI（preview1）写 wasmtime 兼容 CLI
   （`--dir HOST::GUEST`、`--env K=V`）作 `ENGINE` 传给 ctest。
4. cmake 参数：`-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`
   （交叉工具链，编译期探测不链接）、`-DBUILTINS_LIB=<官方 builtins>`、
   `-DFETCHCONTENT_SOURCE_DIR_LIBC-TEST=<预取>`、
   `-DENGINE="node;<runner>"`（分号列表让 CMake 展开为程序+参数）。

## 验证

真机 `conan create` rc=0；上游套件 152/167（91%，15 项失败均为
Node-WASI 引擎缺口、逐条 errno 分类）；消费者对产物 sysroot 编译 wasm
并执行输出 `CONSUMER_PASS`。完整配方：
`archives/w/wasi-libc/0.0-git20260129.ec0effd/conanfile.py`。

## 禁则

1. 禁止 `-Wl,--allow-undefined` 吞 `__heap_end`：掩盖 LLD 版本缺口并让
   真实未解析符号静默通过（升级 wasm-ld 才是正解）。
2. 禁止 `-isystem`→`-I` 提升赢头文件顺序：系统头警告抑制被取消，
   dlmalloc 与 `__errno_values.h` 的上游合法宏交互会被 `-Werror` 打爆。

## 与相邻条目的边界

- `DRAFT-odiff-4.5.0-zig-ohos-libc-probe-...`：zig 以 OHOS **原生**目标
  编译时的宿主 sysroot 探测问题（反向场景：注入的 SDK sysroot 不完备，
  用 `-Dtarget=aarch64-linux-musl` 绕过）；本条是 **wasm 交叉**目标下
  zig 自带 wasm 头遮蔽目标 sysroot（剪枝/隔离解决）。
- `DRAFT-below-ohos-unsigned-rust-toolchain` / E318：ELF 自签名族
  （本条把签名作为自举的前置步骤引用）。
- `wasi` / `wasm-ld` / `heap_end` 在 `knowledge/graph`+`doc` 全量
  0 命中（E400 为 Bun 运行时测试条目，非 wasm 编译族）。
