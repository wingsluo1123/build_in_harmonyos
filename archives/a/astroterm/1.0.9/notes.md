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

Conan 配方将 argtable3 和 ncurses 声明为 system_libs（不通过 Conan 依赖解析），构建环境中必须已安装这两个库的开发包。

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

### 4. 静态链接（R26）

astroterm 是终端工具，通过 `MesonToolchain` 默认关闭共享库构建，并在 `package()` 阶段删除任何意外生成的 `.so` / `.la` 文件，确保 DevBox 部署兼容性。

### 5. 已知问题与待办

- **系统依赖**: argtable3 与 ncurses 作为系统库使用，CI worker 上需预装开发包。
- **ncurses 宽字符**: 确保 ncurses 启用了 wide-char 支持（`ncursesw`），否则中文字符或特殊符号可能显示异常。
- **上游测试缺失**: astroterm 上游未提供自动化单元测试，test_package 仅做二进制烟雾测试（`--version` / `--help`）。

### 6. 文件清单

- `conanfile.py` — Conan 配方
- `conandata.yml` — 源码与补丁元数据
- `manifest.yaml` — 软件包元数据
- `test_package/conanfile.py` — 测试入口
- `test_package/MANIFEST.yml` — 测试清单
- `patches/0001-*.patch` — stddef.h 修复
- `patches/0002-*.patch` — embed.sh toybox 兼容
