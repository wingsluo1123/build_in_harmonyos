# astroterm 1.0.9 — 适配笔记

## 基本信息

- **适配状态**: `ready` / `built` / `verified` / `released`
- **适配版本**: 1.0.9
- **对应 Issue**: #49
- **队伍**: 10086
- **构建系统**: Meson
- **语言**: C

## 编译步骤与关键注意事项

### 1. 依赖说明

astroterm 依赖以下库：
- `argtable3` (>= 3.0) — 命令行参数解析
- `ncurses` (>= 6.0) — 终端 UI
- `math` — 标准 C 数学库（libc 的一部分）

Conan 配方下载并静态编译 argtable3 3.3.1 源码，ncurses 由 OHOS 构建环境提供。

### 2. 构建步骤

```bash
conan create . --profile:host <OHOS-profile> --profile:build <native-profile>
```

Meson 构建流程：
1. `source()`: 下载 `v1.0.9.tar.gz`
2. `generate()`: 生成 MesonToolchain（注入 ar/ranlib 路径）
3. `build()`: 应用补丁，执行 `meson setup` + `meson compile`
4. `package()`: `meson install`，并清理 `.so`/`.la` 文件（R26）

### 3. OHOS 适配补丁

#### 补丁 1: `0001-add-stddef.h-before-string.h.patch`

在 `include/parse_BSC5.h` 中 `string.h` 前添加 `#include <stddef.h>`，解决部分目标平台 `size_t` 未定义的问题。

#### 补丁 2: `0002-fix-embed-sh-for-toybox.patch`

OHOS 使用 toybox 工具链，其 `xxd` 不支持 `-i` 选项。补丁在 `scripts/embed.sh` 中检测 `xxd -i` 是否可用，不可用时自动回退到项目自带的 `scripts/embed.py`（CLI 接口一致），确保 `meson.build` 中的 `custom_target('bsc5_embed')` 能正常生成 `bsc5_embed.h`。

#### 补丁 3: `0003-fix-curses-for-ohos.patch`

OHOS CI worker 在 `/storage/Users/currentUser/usr/local/{include,lib}` 预装了 ncurses 静态库（`libncursesw.a`）和头文件，但未安装 `curses.pc` pkg-config 文件。meson 的 `dependency('curses')` 走 pkg-config 查找必然失败。

**第一版方案（已废弃）**：用 `cc.find_library('ncursesw', dirs: [...])` 替代。但 meson 1.11.1 的 `compiler.find_library` 会编译链接测试程序验证库可用，而 Conan MesonToolchain 隔离环境下 OHOS clang 默认搜索路径不含 `/storage/Users/currentUser/usr/local/{include,lib}`，导致 probe 失败（`-I`/`-L` 均缺失），报错：

```
../meson.build:150:21: ERROR: C shared or static library 'ncursesw' not found
```

**最终方案**：用 `declare_dependency(link_args: ['-L...', '-lncursesw'], include_directories: include_directories('...'))` 完全跳过 meson 的库查找逻辑，直接注入 `-I`/`-L`/`-l`。等价于 hexcurse / fdclone / frotz / aamath 等配方的 autotools `-I/-L` 注入方式。

- `declare_dependency()` 返回 `found() == true`，后续 `if curses.found()` 头文件检测块继续执行。
- `cc.has_header()` 不带 args 时无法找到 ncurses 头文件，所有 `HAVE_NCURSES*` 宏不定义。
- 但源代码（`src/*.c`、`include/*.h`）不引用任何 `HAVE_NCURSES*` / `HAVE_CURSES*` 宏，仅 meson.build 内部 `if` 块用，缺失仅触发 warning，不阻塞 configure/compile。
- 实际编译时 `static_library(..., dependencies: [curses, math])` 会自动应用 `curses` 的 include_directories，`#include <curses.h>` 能找到。

### 4. 静态链接（R26）

astroterm 是终端工具，通过 `MesonToolchain` 默认关闭共享库构建，并在 `package()` 阶段删除任何意外生成的 `.so` / `.la` 文件，确保 DevBox 部署兼容性。

### 5. 已知问题与待办

- **系统依赖**: ncurses 由 OHOS 构建环境提供；argtable3 3.3.1 随配方下载并静态编译。
- **ncurses 宽字符**: 确保 ncurses 启用了 wide-char 支持（`ncursesw`），否则中文字符或特殊符号可能显示异常。
- **上游测试**: 上游包含 7 个 Unity 测试程序，当前配方未在 CI 中执行；test_package 执行二进制烟雾测试（`--version` / `--help`）。

### 6. 文件清单

- `conanfile.py` — Conan 配方
- `conandata.yml` — 源码与补丁元数据
- `manifest.yaml` — 软件包元数据
- `test_package/conanfile.py` — 测试入口
- `test_package/MANIFEST.yml` — 测试清单
- `patches/0001-*.patch` — stddef.h 修复
- `patches/0002-*.patch` — embed.sh toybox 兼容
- `patches/0003-*.patch` — curses pkg-config 绕过（OHOS 专用）
