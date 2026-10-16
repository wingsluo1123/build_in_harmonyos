## 变更摘要

- 新增 `archives/l/libskia/146.20260602-git.3476902/**`：libskia（Skia m146）的 Conan 配方、P1 完整源码包方案（vendored 9 个 DEPS externals + 本机预生成 out/ 构建图）、2 个消费者用例（SkSurface 像素断言 + PNG 编码魔数校验）与 notes.md 适配笔记；`archives/l/libskia/{README.md,manifest.yaml}` 软件级索引。
- 新增知识草稿（路径 B 贡献创新）：`knowledge/DRAFT-libskia-146.20260602-git.3476902-nonprestaged-elf-exec-denied.{md,kv}` —— 归纳"OHOS HMDFS/SELinux 拒绝执行非预置 ELF（Permission denied），工具/代码生成器类依赖应改为本机预生成构建图/产物"这一类问题，含错误签名、对照验证法、host-pregenerated 修复范式、禁止模式与真机验证数据。
- 完整源码包持久化于 GitCode Release（tag `libskia-146.20260602-git.3476902`，附件 84MB，sha256 `a01ea3a20a56bffb226338f89b20e5ff4bdbee6013bd46d4215b4a81600c391e`），conandata.yml 引用该 URL，真机 `conan source` 下载+校验+解包复验通过。
- 不修改任何基础设施目录（SKILL.md、references/、templates/、scripts/、ci/、index.tsv、SUMMARY.md）。

---

## PR 信息
- **三方库名称**：libskia（上游仓库名 skia）
- **上游版本**：146.20260602-git.3476902（chrome/m146 @ `34769028da93df54a2e33ebe8985413924053bc1`，2026-06-02）
- **上游仓库地址**：https://github.com/google/skia （官方 https://skia.googlesource.com/skia）
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：build_in_harmonyos SKILL（W0-W5 流程）+《适配共性问题与首次真机启动避坑指南》+ 知识库 hmdfs 家族条目（DRAFT-libfreenect-0.5.3-hmdfs-shared-lib-versioned-symlink 等）

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0（未运行） | 上游 gtest 套件位于 `tests/`，依赖 GPU/字体/skia_resource 数据与 `out/<dir>/tests` 二进制，OHOS 首轮未构建运行（见"上游测试用例修改说明"） |
| 集成测试 | 0（未运行） | 同上 |
| 其他测试 | N/A | 上游无独立可执行测试框架外的自动断言 |
| **合计** | **N/A（首轮未运行）** | |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 新增 | test_package/test_skia.cpp：SkSurface 画红矩形 → 像素断言 RGBA(255,0,0,255)；test_package/test_skia2.cpp：SkBitmap→SkImage→PNG 编码 → 8 字节魔数校验（bundled libpng 集成） |
| 集成测试 | 0 | 不变（上游亦无独立集成框架） | |
| 鸿蒙特有测试 | 2 | 新增 | 上述 2 个消费者用例均为 OHOS 软件光栅路径实测（无 GPU/字体依赖） |
| **合计** | **2** | **+2** | |

---

## 上游测试用例修改说
### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

> 上游 gtest 套件未修改、亦未在 OHOS 首轮执行：其依赖 GPU 后端、字体/资源数据与专用测试二进制（`ninja -C out/<dir> tests`），OHOS 软件光栅首版不构建该目标；核心 API 可用性以 2 个消费者用例（真实调用 SkSurfaces/SkCanvas/SkPaint/SkImage/PNG 编码）在真机实测替代，记录于 test_package/MANIFEST.yml。

---

## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [x] **是**，上游测试套件依赖 GPU/资源数据无法在 OHOS 软件光栅首版运行，适配后补全了可执行的消费者用例
- [ ] **否**，上游已有测试用例覆盖

> - **补全的测试范围**：2 个消费者用例，均真实调用 Skia 公开 API 并做断言（非空壳）：
>   1. `test_package/test_skia.cpp` — SkSurfaces::Raster 建 8x8 表面 → 白底 + 红矩形 → peekPixels 断言 (2,2) 像素 RGBA(255,0,0,255)，真机通过；
>   2. `test_package/test_skia2.cpp` — SkBitmap 16x16 蓝色 → SkImages::RasterFromBitmap → encodeToData(PNG) → 校验非空且 PNG 8 字节魔数 `89 50 4E 47 0D 0A 1A 0A`，真机通过（验证 bundled libpng 编码器集成）。
> - **补全原因**：上游测试套件不可在 OHOS 首轮（无 GPU/字体数据）自动执行；需要可复现的消费者级验证。
> - **新增测试文件清单**：
>   1. `archives/l/libskia/146.20260602-git.3476902/test_package/test_skia.cpp`
>   2. `archives/l/libskia/146.20260602-git.3476902/test_package/test_skia2.cpp`
>   3. `archives/l/libskia/146.20260602-git.3476902/test_package/MANIFEST.yml`（assertion_count: 2）

---

## 验证结果
- 编译状态：**通过**（真机 frp-tip.com:56267，HarmonyOS Kernel 1.12.0 aarch64，`conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` 全流程：[1213/1213] link libskia.a → package 生成 377 头文件 + libskia.a 21,080,060 B（ar archive））
- **上游测试用例通过率**：**N/A（首轮未运行）**——上游 gtest 套件依赖 GPU/字体/资源数据与专用测试二进制，OHOS 软件光栅首版未构建该目标（未修改上游测试；缺口与原因见上文"上游测试用例修改说明"）
- 新增测试用例通过率：**2/2（100%）**（test_skia.cpp 像素断言 + test_skia2.cpp PNG 魔数断言，真机实测）

---

## 补充说明

### 依赖
- **Conan 层 requires 为空**：Skia 通过 DEPS 内置 third_party（freetype/libpng/libjpeg-turbo/libwebp/zlib/expat/wuffs/dng_sdk/piex 共 9 个被最小软件光栅构建图引用的 externals，均随 P1 完整包 vendor，revision 与 DEPS 目标逐一核对）；`skia_use_system_*=false`，无需先发布下游依赖。

### 源码与构建方案（要点，详见 notes.md）
1. **P1 完整源码包**：真机/CI 无法访问 googlesource 系 → 本机（经 127.0.0.1:7897 代理）同步 9 个 DEPS externals + 官方源码打包（84MB），持久化于 GitCode Release；conandata.yml `url` 指向该 Release 附件，sha256 `a01ea3a2...`，真机 `conan source` 复验通过。
2. **GN 构建图本机预生成（Plan C，核心知识）**：真机 HMDFS/SELinux 拒绝执行非预置 ELF（gn 在真机任何落点 chmod 后仍 `Permission denied`，对照预置 clang-15 可执行）→ 不在真机跑 gn；本机 win gn 以真机 cc/cxx 绝对路径生成 `out/` ninja 图，打包前做真机化 rewrite（cmd.exe stamp→`: >`、`D$:` 转义路径→`../`、freetype `<...>` 宏加引号），配方检测 `out/build.ninja` 跳过 gn gen、直接 `ninja -C out -j2 skia`（-j 按 MemTotal 限流防 OOM）。
3. **m146 GN args 勘误**：`skia_enable_gpu` 拆为 `skia_enable_discrete_gpu`+`skia_enable_graphite`；必须显式 `skia_use_fontconfig=false`、`skia_use_x11=false`、`skia_use_harfbuzz=false`（target_os=linux 默认开，真机无对应系统依赖）。

### 知识草稿（路径 B 贡献创新）
- `knowledge/DRAFT-libskia-146.20260602-git.3476902-nonprestaged-elf-exec-denied.{md,kv}`
- 问题类：OHOS HMDFS/SELinux 执行策略拒绝"非预置 ELF"（st_mode 正确、chmod 无效、任何落点均 `Permission denied`），凡真机构建需运行额外二进制工具（gn、代码生成器 bison/flex/protoc 等）的三方库通用处理范式。
- 内容：错误签名、对照验证法（预置 clang 可执行 vs 用户侧 ELF 拒绝）、host-pregenerated-build-artifacts 修复范式（本机预生成构建图/产物 + 真机只跑预置工具链）、GN 图真机化 rewrite 三步、禁止模式（反复 chmod/真机下载 ELF/#ifdef __OHOS__ 改源码）与真机验证数据。
- 通用性：适用于所有需要"构建期运行额外 ELF 工具"的库（GN/ninja、代码生成器、构建期工具链），非单库 case-by-case。
- 查重：知识库 540+ 条中无"OHOS HMDFS 拒绝执行用户侧 ELF / 本机预生成构建图"先例条目；与 hmdfs 家族（DRAFT-libfreenect symlink）维度不同（exec 策略 vs 软链能力）。

### 上游遗留限制（如实记录，不在本 PR 修复范围）
- 上游 gtest 测试套件（tests/）未在 OHOS 首轮构建运行（GPU/字体/资源数据依赖），核心 API 可用性由 2 个消费者用例替代验证。
- 首版只产静态 `libskia.a`（shared 默认 False）；Vulkan/GL GPU 后端与字体渲染留待后续轮次。
