# dynamorio 11.91.20676 — OHOS PC adaptation notes

> 适配路径：**路径 C（高难度挑战）** — 动态二进制插桩（DBI）引擎：运行时代码重写、代码缓存、
> 碎片调度，自带 client API 与大型套件；复杂架构硬命中（DBI/代码缓存，与 binutils 同族且更集中于运行期）。

## 1. 版本与源码

- 上游版本语义：`<major.minor>.<commit 距 epoch 天数>`（`CMakeLists.txt`：`daycount = committer-date / 86400`）。
  故 **11.91.20676 不是 release tag**，而是 **master @ 2026-08-11**（commit `e2b756de6eb4da2dd8f3c1535cd51754708dcc12`，
  daycount 20676）。最近的两个 cronbuild tag 为 `cronbuild-11.91.20672`（2026-08-07）与 `cronbuild-11.91.20679`（2026-08-14）。
- 源码 sha256（三源一致：codeload / github archive / 镜像）：
  `b4b375236823590f3f02faa3f40446791f40e5efef89d33ea1759c52dcb60629`
- 子模块：源码归档不含子模块内容。
  - `third_party/elfutils`（DynamoRIO/elfutils fork @ `3022523`，sha256 `0340ec69…`）**必需**（ext/drsyms 在 64 位 Linux 类目标上使用 elfutils 做符号服务）。
  - `third_party/libipt`（x86 Intel-PT）**故意省略**：CMake 仅当 `third_party/libipt/.git` 存在时才构建 drpt2ir/drpt2trace，aarch64 无关。

## 2. 构建矩阵（OHOS PC aarch64 / clang 15.0.4 / musl）

| 项 | 值 |
|---|---|
| `CMAKE_SYSTEM_NAME` | `OHOS`（跨到 `Platform/OHOS.cmake` → `include(Platform/Linux)`） |
| `DR_TARGET_MUSL` | `ON` |
| `SPLIT_SYMBOLS` | **`OFF`**（关键，见 §3-A） |
| `BUILD_TESTS` | `OFF`（配方不构建上游套件以适配 CI 预算；57/417 为**本地** `BUILD_TESTS=ON` 实测证据） |
| `VERSION_NUMBER` | `11.91.20676`（无 `.git` 时 DR 自算 patchlevel 会退化为 0） |
| 依赖 | `zlib/1.3.1.1`（elfutils 需要；也可用 sysroot 的 libz.so） |
| **不要设** `CMAKE_SYSROOT` | clang 自带 sysroot；一旦设置，CMake 会给 GNU as 注入它不认的 `--sysroot=` |

## 3. 适配问题目录（13 个补丁）

### A. 平台执行/签名约束（决定性）

- **OHOS 会拒绝执行 `.codesign` 记录与文件不一致的 ELF**（`execve` → EPERM / "Operation not permitted"）。
  实测判据：`.codesign` 段 `+0x10` 处的 8 字节长度 **必须等于文件大小**；摘要带密钥，不可离线复现。
- DR 默认在链接后做 `objcopy --only-keep-debug` + `--add-gnu-debuglink` + `strip` 分离调试信息，**破坏该记录**
  → 全部产物不可执行。修复：`SPLIT_SYMBOLS=OFF`。
- 平台侧遗留现象（**需评审委员会确认的问题**）：OHOS 版 `ld.lld --code-sign` 在「链接大型静态库」时会写出
  与自身输出不一致的长度字段（对 `libdynamorio_static.a` 的链接恒为 `15460992`，与 app 无关）。
  受控实验：逐项去掉 `--dependency-file` / `-rdynamic` / `--as-needed` / `-S` / `--hash-style=both` 均无效；
  `--no-code-sign` 亦不可执行（签名是必需的）。
  **工程处置**：配方在 `package()` 内建**签名救援**（`ohos_resign.py`：`llvm-objcopy --remove-section=.codesign`
  → `binary-sign-tool sign -selfSign 1` → 原子替换），对包内 ELF 自动补签；非 OHOS 主机自动跳过。

### B. OHOS seccomp：以 **SIGSYS 杀进程** 而非返回 errno

DR 对若干系统调用做「可用性探测」，期望拿到 `-ENOSYS`/`-EPERM`；OHOS 的 seccomp 直接发 **SIGSYS 终结进程**：

| 系统调用 | DR 位置 | 补丁 |
|---|---|---|
| `clone3` (435) | `core/unix/os.c` 探测 | `0002`：**运行时判定**——存在 seccomp 过滤器时跳过探测（`is_seccomp_enforcing()` 读 `/proc/self/status`），视为不可用 |
| `rseq` (293) | `core/unix/rseq_linux.c` 探测/注销 | `0012`：**运行时判定**——seccomp 过滤器生效时 `rseq_is_registered_for_current_thread()` 直接 false（DR 原本已假设 seccomp 返回 `-EPERM`，部分沙箱却是致命 SIGSYS）；判定函数声明见 `0014` |

其余实测的平台约束（未在本库触发，但同族）：`ptrace` → EACCES（gdb 不可用）；`memfd` + `PROT_EXEC` 被拒（匿名 `mmap`/`mprotect` 可用）。

### C. musl 装载器语义（与 glibc 不同）

| 现象 | 位置 | 补丁 |
|---|---|---|
| 装载器**不调用 `DT_INIT`**（只跑 `.init_array`）→ `_init` 从不执行 → 注入静默 no-op | `core/unix/os_public.h` | `0013`（在补丁内注明 R8 豁免依据：loader 能力、构建期不可探测、上游 macOS ARM64 同款）+ `0002`/`0015` 为两处入口加**幂等守卫**，消除「双路径调用→二次初始化」风险 |
| 部分装载器**不向 `DT_INIT`/`.init_array` 传可用的 argc/argv/envp** → 野 `envp` → `os_page_size_init` 越界读 auxv 崩 | `core/unix/os.c` `our_init` | `0002`：**运行时探测**——优先用 `/proc/self/environ` 快照（原始 syscall 读取），并以运行时标志禁止对快照做 auxv 扫描；页大小回退到 `os_find_page_size()` 实测探测 |
| `MAP_FIXED_NOREPLACE` 返回 **ENOSYS**（DR 只处理 EINVAL） | `core/unix/os.c:3603` | `0002` |
| `struct user_fpsimd_struct` 只出现在 `<bits/user.h>`，`<linux/ptrace.h>` 不含 | `core/unix/ptrace_lib.h` | `0004` |
| `elf.h` 无 `R_AARCH64_IRELATIVE` | `core/unix/elf_defines.h` | `0003` |
| `libintl.h` 是空壳（无 `dgettext` 声明） | `third_party/elfutils/lib/eu-config.h` | `0011` |
| 预编译 demangler 归档是 glibc 产物（引 `__ctype_b_loc`） | `ext/drsyms/` | `0005` + `0006`（新增 glibc-ABI `__ctype_b_loc()` shim，**文件自身不带平台宏**；仅在构建系统加入 srcs 时编译） |
| sysroot 无 `libm/libdl/libpthread.so`（只有空 stub `.a`），且 `find_library` 会把裸名归一成路径 | `CMakeLists.txt` | `0001` |

### D. 工具链差异

| 现象 | 补丁 |
|---|---|
| `/usr/bin/patch` 是 **toybox 0.8.12**：无 GNU `-o`、无上下文容错 → 上游 elfutils 补丁无法应用 | `0005`：失败时改走 `git apply --recount -C1`（镜像暂存） |
| clang 对 `.templatex` 里 `2's` 报 `-Winvalid-pp-token`，而 template2expect 把 stderr 当硬错 | `0007` |
| `-Wno-trampolines` 是 GCC-only，clang 在 `-Werror` 下报未知选项 | `0007` |
| clang 不认 AArch64 SIMD clobber `"q0"`（须 `"v0"`）；`"=g"` 约束会被选成内存 | `0009` |
| musl `struct sigevent` 无 `_tid` / 无 `SIGEV_THREAD_ID` | `0008`、`0010` |

## 4. 验证结果（截至本版）

- **本地全量编译 rc=0**（configure rc=0，`ninja` 全绿；`-DSPLIT_SYMBOLS=OFF`）。
- **引擎实跑**：standalone 客户端 `api.static_startstop` **rc=0**，输出
  `pre-DR init / in dr_client_main / pre-DR start / Saw some bb events / all done`
  —— BB 事件与代码缓存真实工作（进程 maps 中可见 `rwxp` 段）。
- **上游套件**：`ctest -N` = 417；全量基线与失败分类见 `reports/全量基线统计.md`。

## 5. 需评审委员会确认的问题

1. **注入执行模式**：OHOS 上 DR 的 `early-inject`（ARM 平台上上游套件默认走的路径）崩溃；`late` 注入在补齐
   `0013` 后引擎初始化已通过，但目标应用未正常跑完。当前可用形态为**静态（standalone）形态**
   （`dr_app_setup`/`dr_app_start`），已被上游用例与 test_package 实证。
2. **平台 `lld --code-sign` 大静态库签名不一致**（§3-A），建议由平台侧核实；本包以补签工程化绕过。
3. **DR 在控制期间丢失应用 stdout**：上游用例的判定谓词因此失效（例：`api.static_startstop` 单独运行 rc=0，
   但谓词要求的 `pre-DR stop` 行未出现）。属跨层问题，待与委员会确认口径。

## 6. CI 复现（本地等价命令）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight dynamorio 11.91.20676 --src <src>
conan create archives/d/dynamorio/11.91.20676 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 上游套件实测（配方默认不构建套件：CI 预算；下列为本地 BUILD_TESTS=ON 口径）
cmake -S . -B build -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
      -DDR_TARGET_MUSL=ON -DSPLIT_SYMBOLS=OFF -DBUILD_TESTS=ON
ninja -C build && ctest --output-on-failure
```

## 7. 评审意见闭环（2026-10-06）

- **P1（0002/0012 平台宏）** → 已改为**运行时能力探测**（`/proc/self/environ` 快照 + 运行时标志；`is_seccomp_enforcing()` 网关 clone3/rseq），补丁内无平台宏。
- **P2（0006 平台宏 + 适用范围）** → 删除 `#if defined(__OHOS__)` 守卫；文件更名 `drsyms_libc_compat.c`、标识符中性化（`ctype_compat_*`），其适用面是「非 glibc libc 链接预编译 demangler 归档」，非 OHOS 本身。
- **P2（0013 平台宏）** → 按 R8 走豁免并在**补丁内注明依据**（loader 能力不可构建期探测；上游 macOS ARM64 同款 workaround）；同时以 `0002`/`0015` 的幂等守卫消除二次初始化失效模式。
- **P2/P3（`ohos_resign.py`）** → 补签失败不再静默：`resign_tree()` 返回未解决清单，配方 `package()` 检出即抛 `ConanException`；`readelf` 探测失败与「无 `.codesign`」区分上报；安装改为**原子替换**（`os.replace` + 兜底）。
- 复验：15 个补丁 `git apply --check` 全过；本地 `conan create` **rc=0**（test_package 真跑）；`api.static_startstop` rc=0（含 BB 事件）。
