# tenacity 1.3.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-14
- 编译器: clang/clang++（OHOS SDK，profile `ci/conan/profiles/ohos-aarch64`，os=OHOS 6.0 / armv8 / clang 15 / libc++ / cppstd 17 / Release）
- 状态: built
- 适配路径: **路径 B** —— 仅交付 17 个非 GUI 核心库（`libraries/lib-*`），与 `archives/a/aegisub/3.4.2`（libaegisub 核心库 + 禁用 GUI 前端）同构

## 编译步骤

```bash
# 依赖（ohpcd 制品仓，W0 三证探针核验：全新空 CONAN_HOME + conan download -r=ohpcd）：
#   wxwidgets/3.3.3.2 portaudio/19.7.0 libsoxr/0.1.3 expat/2.8.2 zlib/1.3.1.1
#   lame/3.100 libsndfile/1.2.2 sqlite3/3.49.1

conan create archives/t/tenacity/1.3.5 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd

# 内部实际 CMake 变量（conanfile.py _configure_variables()）：
#   -DBUILD_STATIC_LIBS=ON                    # 仅静态核心库（上游默认 shared）
#   -DCMAKE_POLICY_VERSION_MINIMUM=3.5       # 宿主 cmake 4.1.2 不再兼容 min_required(<3.5)
#   -DCMAKE_DISABLE_FIND_PACKAGE_Python3=ON   # 消息编目用，交叉环境避免误拾宿主 python
#   -DVCPKG=OFF
```

构建流程：`source()`（下载官方 tarball 并校验 sha256）→ `build()`（应用 9 个补丁 → CMake configure → 编译 17 个静态库）→ `package()`（17 个 `.a` + 113 个头文件 + `LICENSE.txt`）→ `test_package`（消费者真实链接 + 真实运行 + 归档 AArch64 ELF 校验）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(wxWidgets 3.1 REQUIRED COMPONENTS base core html net)` 致命失败 | ohpcd 全部 wxWidgets 制品均以 `wxUSE_GUI=OFF` 构建（仅 wxBase，无 core/html/net 组件）；REQUIRED 无降级路径 | 补丁 0001：去掉 COMPONENTS 与版本要求；被跳过的 GUI 前端才是这些组件的唯一消费者 |
| 2 | `find_package(GLIB REQUIRED)` / `find_package(GTK 3.0 REQUIRED)` 失败且引入版本冲突 | GLIB/GTK 仅服务 GUI 前端；且 glib→fontconfig→expat/2.8.2.1 与 wxwidgets→expat/2.8.2 互斥 | 补丁 0002：注释掉两个 REQUIRED 探测 |
| 3 | GUI 前端（src/ 346 文件）无法编译 | 直接使用 wxWindow 等 GUI 类，制品无 GUI 组件 | 补丁 0003：只 `add_subdirectory("libraries")`；跳过 src/、modules/、plug-ins/、nyquist/、help/images/locale/scripts |
| 4 | `libraries/` 无安装规则 → `package()` 无产物 | 上游安装规则在已跳过的 `src/CMakeLists.txt` | 补丁 0004：为 17 个库补 `install(TARGETS ...)` + 头文件按 `libraries/<lib>/` 结构装到 `include/tenacity/<lib>/` |
| 5 | `Project.cpp` 找不到 `<wx/display.h>` | `wxDisplay` 属 GUI 组件，制品头文件树不含；该文件全程未使用（全树核验零命中），属 Audacity 时代残留 | 补丁 0005：删除该未使用的 include |
| 6 | `Could NOT find FLAC (missing: FLAC_LIBRARY FLAC_INCLUDE_DIR)` 中止 configure | 上游顶层对 FLAC 的探测是**可选**的，但 `cmake-modules/FindFLAC++.cmake` 内部写死 `find_package(FLAC REQUIRED)` | 补丁 0006：改为 `QUIET`，与其余可选编解码器（id3tag/MAD/twolame…）行为一致 |
| 7 | `Target "lib-xml" links to: EXPAT::EXPAT but the target was not found` | `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON` → `find_package(EXPAT)` 走 config 模式得到小写 `expat::expat`，而 `lib-xml` 链接 CMake 内建模块命名 `EXPAT::EXPAT` | 补丁 0007：加 `EXPAT::EXPAT` → `expat::expat` 的 INTERFACE 桥接目标 |
| 8 | `Internat.cpp:99: use of undeclared identifier 'format'` | `wxPathFormat format` 仅在 `__WXMAC__`/`__WXGTK__`/`__WXMSW__` 三个 GUI 端口宏分支下声明；wxBase 制品三者皆未定义 | 补丁 0008：补 `#else wxPathFormat format = wxPATH_UNIX;`（与上游 `lib-files/FileNames.cpp` 既有 `#else` 写法一致） |
| 9 | `FileNames.cpp:730: fatal error: '/usr/include/linux/magic.h' file not found` | 上游写死绝对路径，仅在宿主 sysroot 恰为 `/usr/include` 时成立；交叉编译 sysroot 在 SDK 内部 | 补丁 0009：改为 `#include <linux/magic.h>`（OHOS sysroot 同样提供 `MSDOS_SUPER_MAGIC`） |
| 10 | `package_info(): The direct dependency 'lame' is not used by any '(cpp_info/components).requires'` | 反汇编 conan `cpp_info.pyc` 还原算法：`cpp_info.requires` 一旦出现 `pkg::comp` 形式，**所有 visible 直接依赖都必须列出**；本包 8 个直接依赖只列了 4 个 | `lame`/`libsndfile`/`sqlite3` → `visible=False`（已实证仍生成 config，`find_package` 照常解析）；`zlib` 保持可见并列入 requires（它同时是 wxwidgets 的可见依赖，标私有会触发 `required both with visible=True and visible=False` 告警）。同构先例 `archives/a/accountsservice/26.27.3` |
| 11 | 消费者 configure 报 `Library 'lib-project-rate' not found` | 上游 `TenacityFunctions.cmake` 对库目标设 `PREFIX ""`，而目标名本身已含 `lib-` → 归档名 `lib-<name>.a`；Conan CMakeDeps 用 `find_library(NAMES <cpp_info.libs 条目>)`，CMake 强制拼 `lib` 前缀 → 实际查 `liblib-project-rate.a` | `cpp_info.libs = ["-" + m[len("lib-"):] for m in modules]`（去掉 `lib` 前缀保留连字符）；归档保持上游原名不重命名。`cmake -P` 实测三种写法后定案 |
| 12 | 消费者编译报 `fatal error: 'wx/string.h' file not found` | `package_type="library"` 使 Conan 对依赖边默认 `transitive_headers=False` → 消费者不继承本包依赖的 include 目录。本包公开头文件 `#include <wx/...>` 42 处、`<portaudio.h>` 1 处 | `wxwidgets`、`portaudio` 两条边显式 `transitive_headers=True`（`expat`/`soxr`/`zlib` 0 处，无需打开）。同构先例 `knowledge/drafts/DRAFT-cpp-rotor-0.35-boost-trimmed-recipe-missing-components` |
| 13 | 消费者**链接**报 52 个 wx 平台符号未定义（`wxDir::*` / `wxAppTraits::*` / `wxStandardPaths::*` / `wxMutex` / `wxThread` / `wxGetEnv` / `wxUILocaleImpl::*`） | **R36 依赖阻塞**：`wxwidgets/3.2.10` 已发布制品缺全部平台源——`libwx_baseu-3.2.a` 的 93 个成员中 `unix/msw/osx` 零命中。根因：上游 `build/cmake/lib/base/CMakeLists.txt` 用 `elseif(UNIX)` 选平台源，交叉编译 `CMAKE_SYSTEM_NAME=HarmonyOS` 时 CMake 的 `UNIX` 为假；同仓 `wxwidgets/3.2.6` 配方有正解 `tc.cache_variables["UNIX"]="ON"`，3.2.10 回归丢失 | 改用 `wxwidgets/3.3.3.2`（ohpcd 有完整二进制，6 个归档齐全，配方自带 `includedirs`）。证据：`reports/r36-wxwidgets-3.2.10-link-undefined-symbols.log` |
| 14 | `conan create` 末尾 `SAFE_DELETE_BULK_CONFIRM_REQUIRED` → `ERROR: Exiting with code: 1`（伪装成构建失败） | 沙箱批量删除防护（conan 清理上轮 `test_package/build/`，106 文件 > 阈值 50） | 依 `ohos-conan-gate-env` SKILL 判定规则 4：`CODEBUDDY_SAFE_DELETE_ENABLED=0` + `unset -f rm unlink rmdir`（防护亦经 bash 函数与 `sitecustomize` 生效，仅净化 PATH 不够） |
| 15 | `AttributeError: 'CMake' object has no attribute 'configure_variables'` | 配方误用 Conan 1.x API | 改为 `_configure_variables()` 返回 dict + `cmake.configure(variables=...)` |

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001 | CMakeLists.txt | wxWidgets 降为 base-only（去掉 COMPONENTS/版本要求）；`include(${wxWidgets_USE_FILE})` 加空值保护；CMakeDeps 目标名兼容桥接（3.2.10 小写 `wxwidgets::wxwidgets` ↔ 上游 `wxWidgets::wxWidgets`；3.3.x 由 Conan 直接提供驼峰同名目标，桥接自动跳过） |
| 0002 | CMakeLists.txt | 注释掉 GLIB/GTK 的 REQUIRED 探测 |
| 0003 | CMakeLists.txt | 只保留 `add_subdirectory("libraries")` + `include(lib-src/libnyquist)` |
| 0004 | libraries/CMakeLists.txt | 为 17 个 lib-* 补 install(TARGETS) 与头文件安装规则 |
| 0005 | libraries/lib-project/Project.cpp | 删除未使用的 `#include <wx/display.h>` |
| 0006 | cmake-modules/FindFLAC++.cmake | `find_package(FLAC REQUIRED)` → `QUIET` |
| 0007 | CMakeLists.txt | 加 `EXPAT::EXPAT` → `expat::expat` INTERFACE 桥接 |
| 0008 | libraries/lib-strings/Internat.cpp | `wxPathFormat format` 补 `#else` 兜底分支（`wxPATH_UNIX`） |
| 0009 | libraries/lib-files/FileNames.cpp | `#include "/usr/include/linux/magic.h"` → `#include <linux/magic.h>` |

## 依赖版本

- wxwidgets/3.3.3.2（wxBase，GUI=OFF；6 归档：baseu / baseu_net / baseu_xml / wxregexu / wxzlib / wxexpat）
- portaudio/19.7.0、libsoxr/0.1.3、expat/2.8.2、zlib/1.3.1.1
- lame/3.100、libsndfile/1.2.2、sqlite3/3.49.1（仅服务上游顶层 REQUIRED 探针，标 `visible=False`）
- 全部来自 ohpcd 制品仓，`conan download` 实测可获取

## 验证结果

```bash
# 上游测试入口清点（R51，如实申报）：
grep -rn "add_test\|enable_testing\|include(CTest)\|add_custom_target(check" <src>   # → 0 命中
# tests/ 目录存在但不构成构建/测试目标：仅 scripts/CMakeLists.txt:43-44 在传给
# add_custom_target 的「源码 tarball 打包清单」里列出 tests/ProjectCheckTests 与
# tests/samples（配合 set( TLD "tenacity-minsrc-…" ) 与 tar.xz），属打包数据清单而非测试入口；
# 且 SequenceTest.cpp / SimpleBlockFileTest.cpp
# 引用 1.3.5 中已不存在的 DirManager.h / blockfile/SimpleBlockFile.h → 无法编译
# 结论：上游自动化测试 0/0，附技术原因

# 补丁集复验（Conan 同款 patch_ng）：
python3 validate-patches.py <pristine_src>   # → 9/9 [OK]，RESULT: ALL-OK

# 真实构建与打包：
conan create ...                             # configure 通过；17/17 静态库；0 编译错误
# package()：17 .a + 113 .h + LICENSE.txt

# 消费者验证（test_package，本包新增的 HarmonyOS 用例）：
#   真实链接 17 个归档 → 真实运行 test_tenacity --selftest（API 断言）
#   + elf_check（17 个归档的 AArch64 ELF 成员校验，EM_AARCH64=183）
#   + no-display fail-closed 断言
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | 完整可复现配方（官方源 URL + sha256 + 9 个补丁） |
| patches/ | 9 个源码级补丁 |
| test_package/ | HarmonyOS 消费者用例（test_tenacity）+ 归档 ELF 校验（elf_check） |
| reports/ | conan-create.log、r36 阻塞证据、W3 本地 CI 日志、审计结果 |

## 注意事项

- **R36 教训**：`wxwidgets/3.2.10` 已发布制品缺全部 `src/unix/*` 平台源，任何真实消费者都链不上；`wxwidgets/3.3.3.2` 制品完整。判定方法见 `r36-wxwidgets-3.2.10-link-undefined-symbols.log`（`ar t` 数平台成员 + `-Wl,--error-limit=0` 取完整缺失符号清单）。
- `cpp_info.libs` 条目必须写成 `-project-rate` 形式（去掉 `lib` 前缀保留连字符），不能写 `lib-project-rate`。
- `wxwidgets`/`portaudio` 两条依赖边必须 `transitive_headers=True`，否则消费者找不到 `wx/string.h`。
- 本包只交付静态核心库（`-DBUILD_STATIC_LIBS=ON`）；`shared=True` 会显式抛 `ConanInvalidConfiguration`（未验证形态，避免静默产出错架构）。

---

### 对话 #1 — 编译协作者 (implementer)

**请求**: 加载 openharmony 编译 SKILL，将 tenacity 1.3.5 适配到 OHOS PC（aarch64），分支 `feat/tenacity-1.3.5`；依赖须先经 `conan download` 验证可消费（不可消费即停机上报 R36）；上游测试须真实执行并单独报告；须新增 ≥1 个 HarmonyOS 消费者测试用例；每一步给出真实命令/原始输出/退出码/日志路径/首个错误/根因/修复/复验；commit / push / PR 前 STOP 等确认。

**执行摘要**:
1. **环境与依赖预检**：8 个依赖（wxwidgets/portaudio/libsoxr/expat/zlib/lame/libsndfile/sqlite3）全部在 ohpcd，三证探针实测可下载可消费，无 R36 阻塞。
2. **路径判定**：上游顶层 `find_package(wxWidgets 3.1 REQUIRED COMPONENTS base core html net)` 中的 core/html/net 均为 GUI 组件，而 ohpcd 全部 wxWidgets 制品以 `wxUSE_GUI=OFF` 构建 → 按路径 B 仅构建 17 个非 GUI 核心库，与 `archives/a/aegisub/3.4.2` 同构（该先例同为 wxBase-only 上游）。
3. **上游测试清点（R51）**：全仓 `add_test`/`enable_testing`/`include(CTest)` 零命中；`tests/` 仅出现在 `scripts/CMakeLists.txt:43-44` 的源码 tarball 打包清单（不构成测试目标），且其测试源引用 1.3.5 中已不存在的头文件 → 上游自动化测试 0/0，如实申报并附技术原因；可行性验证由本包新增的 HarmonyOS 消费者用例承担。
4. **适配补丁**：9 个补丁覆盖 wxBase-only、跳过 GLIB/GTK、仅构建 libraries/、补 install 规则、GUI 残留头、FLAC 可选化、EXPAT 目标桥接、wxPathFormat 兜底、magic.h 相对引入；全部经 `patch_ng`（Conan 同款）复验 `ALL-OK`。
5. **真实构建**：configure 通过，17/17 静态库，0 编译错误；`package()` 产出 17 `.a` + 113 `.h` + `LICENSE.txt`。
6. **消费者链路四项根因修复**（均由本轮真实构建/链接反向验证）：`package_info()` 完整性校验（`visible=False` 分组）、`cpp_info.libs` 与上游 `PREFIX ""` 命名冲突（`-project-rate` 写法）、`package_type="library"` 致传递头文件丢失（`transitive_headers=True`）、以及 R36 依赖阻塞（wxwidgets 3.2.10 → 3.3.3.2）。
7. **R36 阻塞与处置**：`wxwidgets/3.2.10` 已发布制品缺全部平台源（`ar t` 93 成员零平台成员；真实链接器报 52 个未定义 wx 符号、0 个 tenacity 符号），根因是上游 `elseif(UNIX)` 在 `CMAKE_SYSTEM_NAME=HarmonyOS` 下为假、而同仓 3.2.6 配方本有 `UNIX=ON` 正解。按用户裁决走方案 b，改用 `wxwidgets/3.3.3.2`（ohpcd 制品完整）。
8. **质量门禁**：conan-verify / finish / W2 PR 原子性 / W3 本地 CI 于构建完成后执行并留档 `reports/`。

**产出文件**: conanfile.py、conandata.yml（官方源 + sha256 + 9 补丁）、patches/（9 个）、test_package/（test_tenacity.cpp + elf_check.c + CMakeLists.txt + conanfile.py）、manifest.yaml、notes.md、reports/

**编译结束**: 2026-10-14
**最终状态**: built
---

**编译结束**: 2026-10-14 22:41
**最终状态**: built
