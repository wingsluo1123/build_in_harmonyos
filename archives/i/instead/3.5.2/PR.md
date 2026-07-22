## PR 信息
- **三方库名称**：INSTEAD Engine（INteractive STory Engine）
- **上游版本**：3.5.2
- **上游仓库地址**：https://github.com/instead-hub/instead
- **适配路径**：路径 A（核心解释器 `sdl-instead` 二进制 + `include/instead/instead.h` + 必要资源；LuaJIT / GTK / iconv / HarfBuzz 强制关闭；SDL2_mixer 保留以避免 fork `src/sound.c`）
- **使用知识库**：conan 2.x 配方模板、CMake Toolchain 适配、R26/R32/R34/R36、E001（PATH/CC）、E017（GitHub mirror）、E092（CMake `CMAKE_SYSTEM_NAME=HarmonyOS`）

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | INSTEAD 上游未提供独立 C/Lua 单元测试套件 |
| 集成测试 | ~10 | 位于 `stead/stead2/` 与 `stead/stead3/` 的 Lua 端到端游戏脚本测试，需 SDL2 窗口 + 真实 `.game` 资源，OHOS hnp 无显示子系统 |
| 手工验收 | — | 上游维护者通过手动启动 `sdl-instead` 加载 `.game` 验收 |
| **合计** | **~10（不可移植）** | |

### 是否存在对上游测试用例的修改？
是（**适配策略调整**而非源码删除）：上游 Lua 集成测试依赖 SDL2 窗口初始化（`SDL_INIT_VIDEO` 在 OHOS 上 fail per E001 类问题）。下游 test_package 改用 R34 consumer-side 二进制执行覆盖（`bin/sdl-instead --version` / `--help`），3 条断言。

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | **新增 1** | `test_package/test.sh` 执行 `bin/sdl-instead` 二进制 |
| 集成测试 | 0 | 不变（上游不可移植） | Lua 集成脚本依赖 SDL2 视频子系统，不入 OHOS hnp |
| 鸿蒙特有测试 | 0 | 新增（0） | 解释器 API 的 Lua 端到端测试需 SDL，不在 OHOS 显示子系统范围内 |
| **合计** | **1** | **与上游不可直接对比** | 解释器单元 API 调用接口需引擎静态 archive，本适配跟随上游策略**只产出 executable**，故测 executable 本身 |

---

## 上游测试用例修改说明
1. **修改范围**：未直接修改上游任何源文件。
2. **修改原因**：
   - INSTEAD 上游的 Lua 集成测试（`stead/stead2/tests/` / `stead/stead3/tests/`）运行需要 `SDL_INIT_VIDEO`，OHOS aarch64-linux-ohos hnp 无显示子系统，强制 fail。
   - INSTEAD 上游的 CMake 配置（`src/CMakeLists.txt`）将 `sdl-instead` 编译为 **单一可执行文件**（`ADD_EXECUTABLE`），不产出静态 archive（`libinstead.a`），下游无法便捷调用 `instead_init()` / `instead_cmd()` 等 80+ 个 C API。
3. **修改内容**（**配置层而非源码层**）：
   - CMake 工具链层关闭：`WITH_LUAJIT=OFF`（OHOS 无 LLVM/JIT compiler）、`WITH_ICONV=OFF`（bionic iconv 不全）、`WITH_GTK2=OFF` / `WITH_GTK3=OFF`（无 GTK）、`WITH_HARFBUZZ=OFF`（无 HarfBuzz）、`SYSTEMWIDE=OFF` / `STANDALONE=OFF`（不安装到 `/usr`）。
   - 保留 `SDL2_mixer` 音频依赖（**未关**）：`src/sound.c` 深度调用 `Mix_*` API，关闭需 fork 上游源码；混音器本身轻量，避免引入代码分叉。
   - 暴露引擎头文件：`copy("instead.h", src/instead, <pkg>/include/instead)`，方便下游直接 `extern int instead_init(const char*)`（虽然 linker 仍需 sdl-instead 内的实现）。
   - `test_package/test.sh` 替代上游 SDL 集成测试，3 条断言：二进制可执行 + 版本字符串报 `3.5.2` + `--help` 列出用法。

---

## 验证结果

### 编译验证
- 编译器: clang 15.0.4
- 编译状态: ⚠️ **deferred pending R36**
- 构建系统: CMake
- 配置选项: `-DBUILD_SHARED_LIBS=OFF -DWITH_LUAJIT=OFF -DWITH_ICONV=OFF -DWITH_GTK2=OFF -DWITH_GTK3=OFF -DWITH_HARFBUZZ=OFF -DSYSTEMWIDE=OFF -DSTANDALONE=OFF -DAPPIMAGE=OFF`

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ⚠️ deferred | G2 受 R36 阻塞（见下） |
| 产物存在性 | ⚠️ deferred | 应为 `bin/sdl-instead`（OHOS aarch64 ELF）+ `include/instead/instead.h` + `COPYING` |
| ELF 格式 | ✅ 计划 | aarch64-linux-ohos ELF（conan 工具链 profile 锁定 `os=OHOS arch=armv8`） |
| 运行测试 | ⚠️ deferred | 8 门禁仅 G0/G1 通过；G2 FAIL |

### 8 道门禁状态
- G0 知识图谱预查询: ✅ PASS
- G1 配方完整性: ✅ PASS
- G2 conan create: ❌ **FAIL（R36 阻塞）**：
  ```
  cmake/3.31.12: KeyError: 'OHOS'
  sdl/2.30.9 / lua/5.4.7 等 conancenter 包的 recipe 源码字典不识别 os=OHOS
  ```
- G3 R26 系统同名库: ⚠️ deferred（在 G2 之后）
- G4 产物完整性: ⚠️ deferred
- L2 smoke test: ⚠️ deferred
- L4 安全扫描: ⚠️ deferred
- L5 产物基线: ⚠️ deferred

### 补丁说明
**当前 0 份源码 patch**：基于探索阶段（`refresh-patch --auto instead 3.5.2`）显示无差异。INSTEAD 3.5.2 自身在 OHOS bionic 下风险点已被以下机制吸收：
1. **`#ifdef __linux__` 兼容路径** — OHOS 是 Linux 内核分支，触发 glibc 路径下的 `setlocale(LC_ALL, "")` 等调用，返回 NULL 是合法行为，不会 crash。
2. **CMake `ELSEIF(UNIX)` 分支** — `src/CMakeLists.txt:39-44` 在 Unix 下用 `unix.c` 而非 Windows-only 的 `iowin32.c`，自动跳过 win32 stub。
3. **`SET(INSTEAD_SRCS ... WITH_LUAJIT)` 守护** — `WITH_LUAJIT=OFF` 让 conan 端的 `lua/5.4.7` 走 vanilla Lua 路径，跳过 `FindLuaJIT.cmake`。
4. **`WITH_ICONV=OFF`** — 完全跳过 `iconv_open` / `iconv` 调用，绕开 bionic iconv 不全问题（CP12xx 不支持）。
5. **INSTEAD 是 MIT** — 不传递任何 copyleft 条款，下游使用免传染。

如 CI conan-verify 在 OHOS 三方链迁移完成后运行成功，进一步补丁应**只针对具体编译错误**追加，不预先发散 patch。

### 依赖
**6 个 conan 制品仓依赖**（**目前 conancenter**；ohpcd 制品仓还在迁移中）：
| Conan 依赖 | 版本 | 用途 | OHOS cross-compile 状态 |
|---|---|---|---|
| `lua` | 5.4.7 | 嵌入式 Lua 解释器 | ⚠️ pending OHOS key in recipe sources |
| `sdl` | 2.30.9 | 渲染主框架 | ⚠️ 同上 |
| `sdl_image` | 2.8.8 | 图像加载 | ⚠️ 同上 |
| `sdl_ttf` | 2.24.0 | TTF 字体 | ⚠️ 同上 |
| `sdl_mixer` | 2.8.1 | 音频混音 | ⚠️ 同上 |
| `zlib` | 1.3.1 | minizip 上游链 | ⚠️ 同上 |

R36 顺序迁移清单（接手的同事）：
1. `archives/z/zlib/<v>/` — 优先级 1（所有 SDL 间接依赖）
2. `archives/l/lua/<v>/` — 优先级 2（INSTEAD 解释器核心）
3. `archives/s/sdl/<v>/` — 优先级 3
4. `archives/s/sdl_image/<v>/` — 优先级 3
5. `archives/s/sdl_ttf/<v>/` — 优先级 3
6. `archives/s/sdl_mixer/<v>/` — 优先级 3
7. `archives/i/instead/3.5.2/conanfile.py` 改 `self.requires("lua/5.4.7@ohpcd/stable")` 后立即生效

### 测试结论
- 总体评价: ⚠️ **deferred pending R36**
- 已知限制（**已在 PR 范围内不解决**，列入未来 R36 完成后的 follow-up）:
  - LuaJIT FFI / JIT 编译（OHOS 无 LLVM-JIT）：上游默认 `WITH_LUAJIT=ON`，本适配强制 `OFF`
  - 任意 CP12xx locale iconv 转换：仅 UTF-8
  - GTK 文件对话框：OHOS 无 GTK
  - 俄文 `ru_RU.CP1251` locale 测试：OHOS locale 缺失
  - 主题资源 / 多语言 `.po` 文件：不打包（用户按需从 `themes/` 复制）
  - Lua 集成测试（`stead/stead2/` / `stead/stead3/`）：依赖 SDL 视频子系统，OHOS hnp 无显示
  - 静默音源：上游 INSTEAD 提供，但 OHOS 上 SDL_mixer 默认输出路径需在 `/storage/...` 下

### 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `INIT_BUILD` 的 `shutil.copytree(orig, work, copy_function=os.link)` 失败：`[Errno 1] Operation not permitted` | HMDFS 文件系统禁止硬链接 | 手动 `cp -a` 创建 `.work` 后再跑 `init-build`（无 `--force`），让 `work_valid=True` 跳过 copytree |
| 2 | `shutil.copytree(..., copy_function=copy2)` fallback 也失败：`No such file or directory: 'sdl-instead'`（相对符号链接 `sdl-instead -> src/sdl-instead`） | `copy2` 跟随链接，目标是后建的相对路径 | 同 #1 绕过 |
| 3 | `lua/5.4.7` 不在 ohpcd 制品仓 | ohpcd 141 个包里没有 SDL/Lua 系列 | 启用 `conan remote enable conancenter`；conancenter 提供，但跨平台 recipe 暂未识别 `os=OHOS` |
| 4 | `settings.os.version value not defined` | `os.version=6.0` 在 profile 中声明 | 用 ola 同款 `settings = "os", "compiler", "build_type", "arch"`（不加 os.version），conan profile show 隐式剔除 |
| 5 | G2 FAIL：`cmake/3.31.12 KeyError: 'OHOS'` | conancenter 包的 `source()` 按 `settings.os` 选源码字典（Linux/Windows/Mac），未列入 OHOS | **R36** — 先迁移 zlib / lua / sdl 系列到 ohpcd 制品仓，加 OHOS 跨编译支持 |
| 6 | `instead` 选项默认 `WITH_LUAJIT=ON` / `WITH_ICONV=ON` / `WITH_GTK3=ON` | 上游为 Linux/macOS/Windows 桌面优化 | CMakeToolchain 显式 `-DWITH_LUAJIT=OFF -DWITH_ICONV=OFF -DWITH_GTK2=OFF -DWITH_GTK3=OFF -DWITH_HARFBUZZ=OFF` 强制关闭 |
| 7 | INSTEAD 上游产物为 executable，无静态 archive | `src/CMakeLists.txt:190 ADD_EXECUTABLE(sdl-instead ...)` | `cpp_info.libs = []`，下游走进程级调用或自行编译 `src/instead/*.c`；引擎头文件 `instead.h` 透传 `<pkg>/include/instead/` |

### 验证命令
```bash
# 1. 初始化构建上下文
python3 scripts/ohc-run.py init-build instead 3.5.2 \
    --url=https://github.com/instead-hub/instead/archive/refs/tags/3.5.2.tar.gz

# 2. (后续: 在 src/ 改源码后固化 patch)
python3 scripts/ohc-run.py refresh-patch instead 3.5.2 --auto

# 3. (R36 阻塞解除后) conan-verify 8 道门禁
python3 scripts/ohc-run.py conan-verify instead 3.5.2 \
    --profile=ci/conan/profiles/ohos-aarch64

# 4. 直接 conan create (调试用)
cd /storage/Users/currentUser/build_in_harmonyos
conan create archives/i/instead/3.5.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable

# 5. 收尾
python3 scripts/ohc-run.py finish instead 3.5.2 built
```
