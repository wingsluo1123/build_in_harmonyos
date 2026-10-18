# DRAFT-10100: 上游 PREFIX "" 的无 lib 前缀 `.so` 与 `cpp_info.libs` 的死锁

> Draft: DRAFT-10100-prefixless-so-cpp-info-libs-dlopen-plugin
> 来源：ktx 1.45 适配（QW-Group/ktx, QuakeWorld 服务器 mod），2026-10-04
> 关联：与 `DRAFT-E641-conan-baked-paths-relocatable-dlopen-plugins` 互补
> （那条讲插件的**路径**可重定位，这条讲插件的**命名**与 `cpp_info` 声明）

## 现象

`conan create` 的**主包与 package() 全部成功**，却在 **test_package 阶段**炸掉：

```text
CMake Error at build/.../generators/cmakedeps_macros.cmake:81 (message):
  Library 'qwprogs' not found in package.  If 'qwprogs' is a system library,
  declare it with 'cpp_info.system_libs' property
Call Stack (most recent call first):
  ktx-Target-release.cmake:23 (conan_package_library_targets)
  ktxTargets.cmake:24 (include)
  ktx-config.cmake:16 (include)
  CMakeLists.txt:7 (find_package)
```

失败点在 `find_package(ktx)`，看起来像「测试工程写错了」，实际是配方缺陷。

## 根因

### 第 (1) 层：CMakeDeps 只认 `lib` 前缀

Conan CMakeDeps 解析 `cpp_info.libs` 的实现在
`conan/tools/cmake/cmakedeps/templates/macros.py`：

```cmake
find_library(CONAN_FOUND_LIBRARY NAMES ${_LIBRARY_NAME} PATHS ${package_libdir}
            NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)
```

而 ktx 上游刻意去掉了 lib 前缀：

```cmake
add_library(qwprogs SHARED ${SRC_COMMON} ${SRC_NATIVE})
set_target_properties(qwprogs PROPERTIES PREFIX "")   # -> qwprogs.so
```

本工具链的 CMake `CMAKE_FIND_LIBRARY_PREFIXES == "lib"`，**不会尝试无前缀文件名**。
单独在空 project 里验证也成立：

```text
-- PROBE_P1=[P1-NOTFOUND]
-- PREFIXES=[lib]
-- SUFFIXES=[.so;.a]
```

即「上游 `PREFIX ""` + 标准 `cpp_info.libs`」这个组合在 Conan 里**根本无法被任何
CMake 消费者消费**。

### 第 (2) 层：改名并不能救，只把错误推迟到运行期

试过把产物装成 `lib/libqwprogs.so` —— `find_library` 过了、`find_package` 过了，
但 DT_SONAME 仍是上游推导出的 `qwprogs.so`，与安装文件名不一致。**任何链接该库的
可执行文件在运行期立刻失败**（实测复现）：

```text
Error loading shared library qwprogs.so: No such file or directory (needed by ./ktx_module_test)
Error relocating ./ktx_module_test: dllEntry: symbol not found
→ exit 127
```

想把 SONAME 改成 `libqwprogs.so` 只有两条路：

| 办法 | 结果 |
|------|------|
| 改上游 `CMakeLists.txt`（加 `set_target_properties(... SONAME ...)` 或 `NO_SONAME`） | 有效，但要一次 source patch |
| `CMAKE_SHARED_LINKER_FLAGS = -Wl,-soname,libqwprogs.so` | **无效**：CMake 在链接命令**末尾**追加由 `OUTPUT_NAME` 推导的 `-Wl,-soname,qwprogs.so`，lld 取后者；实测 `readelf -d` 仍是 `SONAME=qwprogs.so` |

## 处置：承认它不是可链接库

最终方案**零 patch、零 hack**：

1. **判定插件类型** —— 读 `.dynsym`。若 defined & GLOBAL 只剩「宿主入口 +
   `_init`/`_fini`」，就是 dlopen 型插件。ktx 靠上游
   `C_VISIBILITY_PRESET hidden` + `include/q_shared.h` 的 `VISIBILITY_VISIBLE`
   强制出这个面：`dllEntry`（服务器 mod 入口）、`vmMain`、`_init`、`_fini`。
2. **保留上游文件名与 SONAME**，原样装成 `lib/qwprogs.so`（两者天然一致，
   也正是服务器按裸名加载所需的形式）。**不要**为迎合 `find_library` 而改名。
3. **故意留空 `cpp_info.libs`**，只保留 `includedirs` / `libdirs` / `system_libs` /
   `cmake_target_name`。这不是漏填：dlopen 型插件没有可链接 API；声明一个
   CMakeDeps 解析不到的 `libs`，会让**所有**消费者 `find_package` 直接
   FATAL_ERROR，比没有 libs 严重得多。在 `package_info()` 注释里写清「为什么空」
   与实测报错原文，避免后续维护者当 bug「补上」。
4. **测试随之改为 dlopen 型**：`dlopen(<pkg>/lib/qwprogs.so, RTLD_NOW|RTLD_LOCAL)`
   + `dlsym` 宿主入口 + 调用入口完成握手——这正是宿主做的事，也是 CI L1e
   反向破坏（移走 `lib/` 后 `conan test` 必须失败）能成立的前提。
   但**仍保留** `find_package(ktx REQUIRED)`，用来验证配方生成的 CMake 配置可被
   消费，防止第 (1) 层缺陷复发。

## 验证（ktx 1.45 实测）

| 写法 | 结果 |
|------|------|
| (a) `libs=["qwprogs"]` + 产物名 `qwprogs.so` | 包成功；test_package `find_package` **FATAL_ERROR**「Library 'qwprogs' not found」 |
| (b) 改名 `lib/libqwprogs.so` | `find_package` 通过；运行 exit 127「Error loading shared library qwprogs.so / Error relocating: dllEntry: symbol not found」 |
| (c) (b) + `CMAKE_SHARED_LINKER_FLAGS=-Wl,-soname,libqwprogs.so` | `readelf -d` 仍 `SONAME=qwprogs.so`（CMake 末尾的 `-soname` 胜出） |
| (d) **最终方案**（保留 `qwprogs.so` + `libs` 留空 + dlopen 型 test_package） | `conan create` rc=0，test_package **34/34 断言 PASS**（16 项鸿蒙特有 ELF 断言） |

反向验证：把配方改回 (a)，test_package configure 必红 —— 确认测试与该缺陷相关，
不是空壳。

## 额外注意：CI L5a 对本包 skip

CI 的 `L5a` 用 `"$LIBS"/lib*.so(N)` 通配，只匹配带 `lib` 前缀的 `.so`。本包产物是
`qwprogs.so`，因此 L5a 对本包**不生效**（skip）；L5 的「`lib/` has content」照常 pass。
这不是缺陷，但要让 reviewer 知道：**L5a 没有替本包把关**，SONAME 的一致性由
test_package 里的 `DT_SONAME == qwprogs.so` 断言兜住。

## 适用范围

- 宿主以 `dlopen` + `dlsym` 加载的插件型共享库（Quake/Q3 引擎 mod、
  MVDSV/FTEQW 类服务器 mod）
- 上游 CMake 使用 `set_target_properties(<t> PROPERTIES PREFIX "" / SUFFIX "")`
- 任何导出符号面只剩「一个宿主入口 + `_init`/`_fini`」的 `.so`
- 解释器扩展（Python/Lua/Perl）、固件与协议插件、busybox 风格 applet 集合

## 关联文件

- `archives/k/ktx/1.45/notes.md`（5.1 节完整记录四种写法的实测对比）
- `archives/k/ktx/1.45/test_package/ktx_module_test.c`（34 项断言，含 16 项鸿蒙 ELF 断言）
- `archives/k/ktx/1.45/test_package/CMakeLists.txt`（保留 `find_package` 但不链接，附理由注释）
- `conan/tools/cmake/cmakedeps/templates/macros.py:59`（`find_library` 调用点）