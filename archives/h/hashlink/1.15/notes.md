# hashlink 1.15 — 适配笔记

**软件名**：hashlink
**版本**：1.15
**适配日期**：2026-07-22
**适配者**：Claude (MiniMax-M3)
**目标平台**：OpenHarmony PC (aarch64-linux-ohos, bionic libc)
**构建系统**：CMake 4.1.2（host）/ 编译目标 cmake 4.x policy floor
**License**：MIT（最宽松）

## 一、构建/适配要点

### 1. 路径决策（Path A）
- 只打包 `libhl`（hashlink 的核心 VM 库 + PCRE2 + std 全套，686 KB 共享库）
- 关闭所有 `WITH_*` hdll 插件模块（uv / sdl / ssl / sqlite / ui / openal / fmt / heaps / video）
- 关闭 `WITH_VM`（不打包 `hl` VM 可执行；aarch64 上游默认即 OFF）
- 不打包可执行 → 无需 `commands.json`（R38 不适用）

### 2. 唯一 patch（0001-src-hl.h.patch）
- 上游 `src/hl.h` 在 `#elif defined(HL_LINUX)` + `HL_64` 分支硬编码 x86 `int3` 指令作为软件断点
- aarch64 没有 `int3`，改用 `brk #0`
- 守护宏：`#if defined(__aarch64__)`（不破坏 x86_64 路径；OHOS aarch64 clang 必然预定义 `__aarch64__`）
- 影响 1 个源文件，+7/-6 行

### 3. 关键适配技巧
- cmake 4.x 拒绝 `cmake_minimum_required(VERSION 3.1)`：用 `cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])` 显式注入；不能用 `tc.variables`（CACHE 设置太晚）
- conan 系统同名库隔离（R26）：`libhl.so` 不是系统库名，**不**强制静态；`m` / `dl` / `pthread` 列在 `system_libs` 让 OHOS hnp 自动链接
- `package_id()` 显式 `del self.info.settings.compiler.libcxx`（bionic libc++ ABI 跨工具链不稳定）
- `cpp_info.libs = ["hl"]`（实际库名是 `hl`，不是 `hashlink`；CMakeLists.txt:164 `OUTPUT_NAME hl`）
- `cpp_info.set_property("pkg_config_name", "hashlink")` 让 pkg-config find_package 用 `hashlink` 而非 `hl`

### 4. init-build 误判修复
- `_guess_build_system(URL)` 只看 URL 字符串 → hashlink URL 不含 "cmake" → 误判 autotools
- 手动改 `.build-context-hashlink-1.15` 的 `BUILD_SYSTEM="cmake"` + manifest.yaml 的 `build_system: cmake`
- 工具 bug，建议在 init_build.py 中加 `if src/CMakeLists.txt exists and not src/configure: return "cmake"` 兜底（driver.py:687 已有这逻辑，init_build.py:78 缺）

### 5. refresh_patch.py CRLF 问题（工具 bug — 待修复 + 临时应急）
- **现象**：hashlink 1.15 tarball 内 `src/*.c` `src/*.h` 是 CRLF 行尾（^M$），Python `read_text()` 剥掉 \r 后 difflib 生成的 patch context 与 orig 文件失配 → `refresh_patch.py --auto` dry-run FAILED
- **工具 bug 待修**：`refresh_patch.py` 应该在 `read_text` 后加 `.replace('\r\n', '\n')` 标准化行尾后再生成 patch；apply 时由 conan 内部 patch 工具自动处理 CRLF。这是上游工具 bug，非适配者责任
- **临时应急**（仅本次会话使用，不应成为标准做法）：手工 `diff -u` 命令生成 patch（diff 内部保留 CRLF），再 `sed` 替换绝对路径为 `a/` `b/`。修复工具后必须用 `refresh_patch.py --auto` 重新生成所有 patch

## 二、踩坑清单（已知问题）

| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | `_guess_build_system` 误判 hashlink 为 autotools | init_build.py:78 只看 URL | 手动改 BUILD_SYSTEM="cmake" |
| 2 | `hl_debug_break` 硬编码 `int3` 在 aarch64 失败 | src/hl.h:290 x86-only | 加 patch 用 `brk #0` |
| 3 | cmake 4.x 拒绝 1.15 tarball 的 `cmake_minimum_required(VERSION 3.1)` | cmake 4.x 移除了 < 3.5 兼容 | `cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])` |
| 4 | refresh_patch.py dry-run FAILED | tarball 是 CRLF，Python read_text 剥 \r | 手工 `diff -u` 生成 patch |
| 5 | `/tmp` 只读 | HMDFS 挂载 | 用 `$HOME/tmp` |
| 6 | test.c 中 `hlt_void.kind != 0` 误判 | `HVOID` 定义为 0（hl.h:330） | 改为 `&hlt_void != NULL` 校验地址 |

## 三、test_package 真实 API 覆盖

6 个测试函数 / 22 个 `HL_ASSERT` 断言：

| 测试 | API | 断言数 |
|------|-----|--------|
| `test_global_init` | `hl_global_init()` + `hl_thread_current()` | 1 |
| `test_alloc_init` | `hl_alloc_init()` 校验 `a.cur == NULL` | 1 |
| `test_buffer` | `hl_alloc_buffer` / `hl_buffer_str` / `hl_buffer_char` / `hl_buffer_cstr` / `hl_buffer_length` / `hl_buffer_content` | 4 |
| `test_utf8_roundtrip` | `hl_to_utf8` + `hl_from_utf8` ASCII round-trip | 3 |
| `test_alloc_bytes` | `hl_alloc_bytes(256)` + 字节读写校验和 | 2 |
| `test_type_singletons` | `hlt_i32` / `hlt_i64` / `hlt_f64` / `hlt_array` / `hlt_bytes` / `hlt_void` 地址 + `hl_type_size` | 4 |

## 四、知识沉淀（建议 E 条目）

1. **新 E 条目**：hashlink `hl_debug_break` 在 aarch64 Linux 缺失分支（用 `brk #0` 替代 `int3`）
2. **新 E 条目**：CMake 4.x 与上游 `cmake_minimum_required(VERSION < 3.5)` 不兼容，必须显式 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
3. **新 E 条目**：refresh_patch.py 对 CRLF 行尾文件生成 patch 失败（difflib context 失配）
4. **新 E 条目**：init_build.py `_guess_build_system` 误判：URL-only 检测 vs 实际源文件扫描的鸿沟

## 五、后续可改进项

- hashlink 上游 `cmake_minimum_required(VERSION 3.1)` → 提交上游 patch 升级到 3.15
- hashlink `hl_debug_break` aarch64 支持 → 提交上游 patch
- refresh_patch.py 加 CRLF 标准化逻辑
- init_build.py 加源文件检测兜底

---

**写于**：2026-07-22
**基于**：ola 0.10.9 + tracy 0.13.1 迁移经验复用（特别是 R26/R32/R34/R36 铁律）
**目标库**：hashlink 1.15（HaxeFoundation 的 VM 运行时）
---

**编译结束**: 2026-07-22 18:22
**最终状态**: built
