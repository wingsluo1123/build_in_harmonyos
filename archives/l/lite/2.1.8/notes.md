# lite (lite-xl) 2.1.8 适配笔记

## 上游信息

| 项 | 值 |
|----|-----|
| 软件 | Lite XL —— 用 Lua + C 编写的轻量级文本编辑器 |
| 上游仓库 | https://github.com/lite-xl/lite-xl |
| 版本 | 2.1.8（Git tag: `v2.1.8`） |
| 官网 | https://lite-xl.com/ |
| 许可证 | MIT |
| 构建系统 | meson |
| 源码 URL（R39 官方源） | https://github.com/lite-xl/lite-xl/archive/refs/tags/v2.1.8.tar.gz |
| sha256 | **【环境阻塞待验证】** 沙箱无法 spawn shell 计算，待环境可用后：`curl -fsSL <URL> | sha256sum` 并回填 conandata.yml 与 manifest.yaml |

## 构建系统与产物

- Meson 项目，C 语言（上游默认 `c_std=gnu11`），本配方显式钉死 `-Dc_std=gnu11`（musl 上避免 POSIX 检测误判，dav1d 教训）。
- 产物：`bin/lite-xl`（可执行文件，GUI 应用）+ `share/lite-xl/`（运行时数据/字体/插件）。
- 应用包 → **R38**：需 software 级 `commands.json`（已生成，`binary: false` 未发布）。

## 依赖（W0 依赖检查）

lite-xl 2.1.8 的 meson 依赖（经 pkg-config 查找）：

| 依赖 | 本仓配方 | pkg-config 名 | 状态 |
|------|---------|--------------|------|
| SDL3（上游优先，`prefer_sdl3`） | sdl3/3.4.8（仅归档，**无 conan 配方**） | sdl3 | ⚠️ 归档在、配方无 → 暂用 SDL2，切换路径见下方 |
| SDL2（上游回退） | sdl2/2.30.10 ✅ | sdl2 | ✅ |
| FreeType2 | freetype/2.14.3 ✅ | freetype2 | ✅ |
| Lua 5.4 | lua/5.4.8 ✅ | lua-5.4（非 `lua`） | ⚠️ 见下方 pkg-config 别名 |
| PCRE2（8 位码元） | pcre2/10.45.1 ✅ | libpcre2-8 | ✅ |
| agg（AGG 渲染库） | 无 agg 配方 | 无（仅 meson subproject） | ❌ **W0/R36 阻塞** |

- **SDL3**：上游 meson 优先探测 SDL3（`prefer_sdl3`），找不到再回退 SDL2。
  本仓**有 sdl3/3.4.8 OHOS 适配归档**（`archives/s/sdl3/3.4.8/`：manifest 显示
  `status: built`、platform ohos-aarch64、G0-G4 全 pass、4 个 OHOS 补丁），
  **但无 conan 配方**（无 conanfile.py/conandata.yml）→ 无法被
  `requires("sdl3/...")` 引用，也不会生成 sdl3.pc，故本配方暂用 SDL2。
  **SDK3 切换路径（R36）**：
  1) 把 sdl3/3.4.8 归档补全为 conan 配方并发布（conan create + conan upload）；
  2) 将本配方 `requirements()` 换成 `sdl3/3.4.8`；
  3) 按上游 `prefer_sdl3` 逻辑构建（meson 探测 sdl3.pc 命中 SDL3，自动优先）；
  4) 复用归档 4 个 OHOS 补丁知识：定义 `SDL_PLATFORM_OHOS` 并取消
     `SDL_PLATFORM_LINUX`（0002）、禁用 `pthread_setcanceltype`（0004）、
     禁用 `SDL_TRAY` 并排除 `SDL_Gtk_Quit`（0001/0003）。
- **lua pkg-config 名**：上游 meson 用 `dependency('lua')`，本仓 lua/5.4.8 配方
  的 pkg_config_name 是 `lua-5.4`。配方 `generate()` 里 `_ensure_lua_pkgconfig_alias()`
  在 generators 目录补 `lua.pc`/`lua5.4.pc` 别名（`Requires: lua-5.4`）覆盖最可能的
  两个请求名。**【环境阻塞待验证】** 若上游实际请求名都不命中，按实况调整。
- **agg（阻塞）**：lite-xl 的 meson.build 以 `subproject('agg')` 引入 AGG 渲染库，
  无 pkg-config，且**本仓暂无 agg 配方**。按 W0/R36，必须先适配并发布 agg 包，
  再回到本包构建。若上游 tarball 未内嵌 agg 子项目源码，还需要：
  1. 发布 `agg` conan 配方（pkg_config_name 设为 agg）；
  2. 给 lite-xl 的 meson.build 打补丁，优先 `dependency('agg')` 再回退 subproject。
  conandata.yml 的 patches 段已留注释占位。
- **luajit**：上游主线 2.x 用 Lua 5.4；LuaJIT 属可选分支，未纳入本配方。本仓存在
  `archives/l/luajit/2.1.rolling/` 适配归档（status built，4 个 OHOS 补丁），但同样
  **无 conan 配方**，未被引用；如后续需要 LuaJIT 后端再补全配方（R36）。

## 已执行步骤

1. 读取 SKILL.md 与 references/iron-rules.md（流程与铁律）。
2. 参考 archives 中 Meson 配方实例：dav1d/1.5.0、fontconfig/2.18.1（meson + PkgConfigDeps +
   MesonToolchain + ar/ranlib 注入 + 签名）。
3. 查 archives 确认可用依赖：sdl2/2.30.10、freetype/2.14.3、lua/5.4.8、pcre2/10.45.1
   （均含完整 conan 配方）。确认 sdl3/3.4.8 与 luajit/2.1.rolling 仅有 OHOS 适配归档
   （**无 conan 配方**），agg 本仓**不存在**（`archives/a/agg` 目录缺失）。
4. 生成配方三件套 + 元数据：
   - `conanfile.py`（application / meson / PkgConfigDeps / wrap_mode=nodownload /
     ar-ranlib 注入 / ELF 签名 / R32 `in ("Linux","OHOS")` / R33 无裸 shell 环境变量 /
     lua pkg-config 别名）
   - `conandata.yml`（R39 官方 URL + sha256 占位符 + patches 注释）
   - `test_package/`（meson.build + test_litexl.c + conanfile.py + MANIFEST.yml，
     实质运行 lite-xl 二进制 + 内嵌 Lua API，R34）
   - 版本级 `manifest.yaml`、软件级 `manifest.yaml` + `README.md`、`commands.json`（R38）
5. 记录 W0 依赖检查结论（见上表）与分支约定。

## 被环境阻塞的步骤（明确清单）

| # | 步骤 | 阻塞原因 | 待办 |
|---|------|---------|------|
| 1 | 源码下载与解压 | bash 无法 spawn shell（Permission denied, os error 13） | 环境可用后 `conan create` 自动下载 |
| 2 | sha256 计算 | 同上 | 计算后回填 conandata.yml + manifest.yaml |
| 3 | W0 `conan download` 依赖发布验证（R35） | 同上 | 环境可用后对 sdl2/freetype/lua/pcre2 逐一 `conan download --only-recipe`；agg 需先发布 |
| 4 | `conan create` 编译验证（W3/G2） | 同上 | 环境可用后执行 `conan create` + test_package |
| 5 | conan-verify 8 道门禁（G0-G4/L2/L4/L5） | 同上 | 环境可用后执行 |
| 6 | `.ci-result.json` 写入 | 禁止伪造；且由 finish step [5/9] 写入 | 由 finish 流程生成，本次**未创建** |
| 7 | git 分支/提交（feat/lite-2.1.8） | 同上 | 见「分支约定」 |
| 8 | 上游源码核实（meson.build 依赖名、meson_options、子项目是否内嵌） | 无法下载源码 | 解压源码后核实并修正配方假设 |

> 本任务所有真实执行类操作（下载、configure/make、conan create 验证、sha256、
> git 操作）均被环境阻塞，**未伪造任何验证结果**，也未创建 `.ci-result.json`。

## W0 — 依赖发布检查（SKILL §0.2）

按 SKILL W0，适配前必须先检查依赖是否已发布到制品仓（R35：用 `conan download` 验证，
禁用 `conan list`）。本环境无法 spawn shell，`conan download` 无法执行：
- 已在本仓库确认存在的**配方**：sdl2/2.30.10、freetype/2.14.3、lua/5.4.8、pcre2/10.45.1
  （配方存在 ≠ 已发布 binary，发布状态须环境可用后 `conan download --only-recipe` 核实）。
- **有归档但无 conan 配方（无法被 conan requires）**：
  - sdl3/3.4.8（`archives/s/sdl3/3.4.8/`，OHOS 适配齐全：status built、G0-G4 pass、
    4 个 OHOS 补丁，但无 conanfile.py/conandata.yml）→ 本配方暂用 SDL2，切换路径见上方；
  - luajit/2.1.rolling（`archives/l/luajit/2.1.rolling/`，同况，未纳入本配方）。
- **确认缺失（无归档也无配方）**：agg（`archives/a/agg` 目录不存在）。
- **结论**：agg 是 lite-xl 构建的硬依赖且无配方 → 按 R36，应先适配并发布 agg，
  再回来构建 lite。本任务产出配方时已把此依赖与处理路径写入 conanfile.py 注释、
  manifest 与 notes；**未在本环境执行 `conan download` 验证**。

## 分支约定

- 目标分支：`feat/lite-2.1.8`
- git 操作被环境阻塞（无法 spawn shell），本任务**未执行任何 git 命令**，仅在 notes 记录约定。
- 提交时遵守协作者铁律：不推 main，走 GitCode PR；不碰 SKILL/references/templates/scripts/ci/index.tsv/SUMMARY.md。

## 质量门禁自评（环境阻塞，结论为“配方静态合规，编译验证待真实环境”）

| 门禁 | 本任务状态 |
|------|-----------|
| W2 结构完整性（L0a-L0e） | ✅ conanfile.py / conandata.yml / test_package(conanfile+源文件) / MANIFEST.yml 齐全 |
| R32 settings.os | ✅ `in ("Linux", "OHOS")`（package() 签名守卫、package_info system_libs） |
| R33 无裸 shell 环境变量 | ✅ build() 走 MesonToolchain；test_package build 走 MesonToolchain；无 `${CC}` |
| R34 实质测试 | ✅ test_litexl.c 真实运行 lite-xl 二进制并校验内嵌 Lua 输出（非空壳） |
| R38 commands.json | ✅ 已生成（应用包，bin/lite-xl） |
| R39 官方源 | ✅ github.com/lite-xl/lite-xl release tarball |
| W3 conan create 编译验证 | ❌ **环境阻塞**，待真实环境执行，未伪造 `.ci-result.json` |
| R29 published 判定 | ✅ 未标 published（保守标 built） |

## 注意事项 / 待真实环境核实清单

1. 解压源码后核对 `meson.build` 的依赖名：`dependency('lua'|'lua5.4'|'lua-5.4')`、
   `dependency('libpcre2-8')`、`dependency('freetype2')`、`dependency('sdl3')`/`('sdl2')`，
   与 conan 生成的 .pc 名逐一对应；不匹配处调整 `_ensure_lua_pkgconfig_alias()` 或加补丁。
2. `meson_options.txt` 是否有 `prefer_sdl3` 选项；若 CI 环境存在网络且允许 meson 下载
   subproject，可考虑 `wrap_mode=default` 缓解 agg 阻塞（不推荐长期方案，优先发布 agg 配方）。
3. lite-xl 数据目录查找机制（SDL_GetBasePath 相对 `../share/lite-xl`）：test 运行二进制
   时数据必须随包安装到位，否则字体加载失败可能提前退出。
4. 若 OHOS 上 SDL dummy video 驱动初始化或字体加载异常导致 test 非 0 退出，属平台行为，
   需按实况调整 test（可退化为 `--version` 式轻量校验 + dlopen 依赖检查），但**禁止空壳化**。
