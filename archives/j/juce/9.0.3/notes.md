# juce 9.0.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-18
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, target=aarch64-linux-ohos)
- 状态: built
- 目标平台: HarmonyOS PC (aarch64, os=OHOS, armv8, libc++)
- C++ 标准: C++17 (JUCE 9 minimumCppStandard)

## 编译步骤

JUCE 9.x 的模块是 INTERFACE 库（header + module-source 模型），框架本体安装 headers +
模块源码 + CMake 支持文件；消费者把所用模块的源文件编译进自己的目标（官方使用模型，
`juce_add_*` 宏）。Conan 配方不编译默认目标（避免拉入 juceaide 需 freetype）：

```bash
# 配方验证 (conan-verify 全部门禁通过 G1-G4/L2/L4/L5)
python3 scripts/ohc-run.py conan-verify juce 9.0.3
# → conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing

# 消费者验证 (编译链接运行 juce_core 公开 API)
/data/service/hnp/bin/clang++ --target=aarch64-linux-ohos -std=c++17 \
  -I modules -DJUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1 -DJUCE_STANDALONE_APPLICATION=1 \
  -DJUCE_USE_CURL=0 test_package/main.cpp modules/juce_core/juce_core.cpp \
  modules/juce_core/juce_core_zlib.c modules/juce_core/juce_core_CompilationTime.cpp \
  -o test_juce && ./test_juce   # 输出: HELLO, HARMONYOS JUCE! (rc=0)

# 上游测试 (juce_core 完整运行)
clang++ ... -DJUCE_UNIT_TESTS=1 juce-test-runner.cpp modules/juce_core/*.cpp -o runner
./runner   # PASSED: 401  FAILED: 8 (详见测试台账)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pthread_cancel` undeclared identifier | OHOS musl 无 pthread_cancel (E127)，JUCE Linux 分支 Thread::killThread() 调用它 | 补丁 0001：与 Android 分支同构，`#if defined(__ANDROID__)||defined(__OHOS__)` 时 killThread 退化 jassertfalse |
| 2 | `curl/curl.h` not found | OHOS sysroot 无 libcurl 头文件，JUCE_USE_CURL 默认 1 | 配方 cpp_info.defines 强制 `JUCE_USE_CURL=0`（OHOS 无 curl 网络后端） |
| 3 | 链接期 `deflate/inflate/crc32` 符号缺失 | juce_core 自带 zlib 源码在独立编译单元 `juce_core_zlib.c`，需一并编译 | test_package/CMakeLists 启用 C 语言并加入 `juce_core_zlib.c` |
| 4 | `juce_compilationDate/Time` 符号缺失 | JUCE 时间戳在独立编译单元 `juce_core_CompilationTime.cpp` | test_package/CMakeLists 加入该编译单元 |
| 5 | conan create 报 "Package type is 'library', but no 'shared' option" | library 包类型必须声明 shared 选项 | 配方补齐 `options={shared:[True,False]}` |
| 6 | refresh-patch dry-run 失败 | 工具生成 hunk 行数与实际不符 | 用 `diff -u` 直接从 .orig/.work 生成标准 unified diff，`patch --dry-run -p1` 验证通过 |
| 7 | conan patch 应用报 "patch stream is incomplete" | 手写补丁 hunk 计数错误 | 补丁改为真实 diff 生成（-60,7 +60,11），归档内补丁 dry-run rc=0 |
| 8 | GitHub 源码下载超时 | 本机 GitHub 直连不可达 | 经 gh-proxy/ghfast 镜像拉取官方 tag tarball（sha256 与官方一致），conandata 只写官方 URL（R39/PF7），CI/G2 自动镜像 fallback |
| 9 | `/tmp` 只读 (E002) | 本机 /tmp 挂载只读文件系统 | 全部构建/下载改用 `$TMPDIR=/storage/Users/currentUser/tmp` |

## 源码修改

- `patches/0001-modules-juce_core-native-juce_Threads_linux.cpp.patch`
  - Thread::killThread()：OHOS/musl 无 pthread_cancel，与 Android 分支同构退化为 jassertfalse（E127 方案）

## 适配平台裁剪（如实声明）

- `JUCE_USE_CURL=0`：OHOS sysroot 无 libcurl（juce_core 网络后端不可用，编译器探针已证实）
- `JUCE_USE_OGGVORBIS=0` / `JUCE_USE_OPUS=0` / `JUCE_USE_FLAC=0` / `JUCE_USE_MP3AUDIOFORMAT=0`：OHOS sysroot 无 vorbis/ogg/opus/FLAC/mp3 系统库（仅用于本地测试 runner 编译，配方与 test_package 不受影响——juce_core/libjuce 本身无此依赖）
- juce_graphics/gui_basics/gui_extra/audio_devices/video/opengl 及其依赖模块：依赖 freetype2/fontconfig/EGL/GL/ALSA 等系统包（OHOS sysroot 缺失），头文件照常安装，其测试无法在当前 OHOS 配置实例化（R51 台账详列）

## 依赖版本

- 无第三方 conan 依赖（juce_core 自带 zlib 源码；其余可选模块系统库 OHOS 无）
- 工具链: clang 15.0.4 / OHOS SDK 26.0.0.18 sysroot / conan 2.29.1 (ohos-aarch64 profile)

## 测试台账（R51 双口径）

**源码声明总数 (source_declared_total)**：168 个独立 UnitTest 测试类
- 枚举规则（可复制）：`grep -rE '^\s*(class|struct)\s+[A-Za-z0-9_]+\s*(final)?\s*:\s*public\s+UnitTest' modules/`
- 独立 `*_test.cpp` 文件 35 个；测试类声明分布于 19 个模块：
  juce_core 55 / juce_graphics 25 / juce_audio_basics 23 / juce_osc 11 / juce_dsp 10 /
  juce_gui_basics 7 / juce_audio_formats 7 / juce_midi_ci 5 / juce_audio_processors_headless 5 /
  juce_audio_processors 5 / juce_cryptography 4 / juce_data_structures 3 / juce_audio_devices 2 /
  juce_javascript 1 / juce_gui_extra 1 / juce_events 1 / juce_audio_utils 1 / juce_animation 1 / juce_analytics 1
- 框架本体 `unit_tests/juce_UnitTest.cpp` 不计入用户用例（框架内部，台账单列）

**当前 OHOS 配置实际实例化可执行 (configured_executable_total)**：juce_core 55 个测试类
- 经 `-DJUCE_UNIT_TESTS=1` 编译入模块源码并实际注册运行
- 其余 113 个测试类所在模块因系统依赖（freetype2/fontconfig/EGL/GL/ALSA/system-audio-codecs，见"适配平台裁剪"）未实例化——编译期真实缺头文件首错：`juce_graphics: ft2build.h not found`，`audio_formats: vorbis/ogg/opus/FLAC/mp3 系统符号缺失`

**实际运行 (executed/registered 单元)**：409 个测试单元（UnitTest 注册项）
- 通过：401 / 失败：8（全部为处于不允许修改范围的平台文件系统语义测试，见下）

**juce_core 失败单元明细（8 个，均计入分母不计通过）**：

| 失败单元 | 失败数 | 根因 | 恢复条件 |
|---|---|---|---|
| Files / Writing | 1 | HMDFS chmod 不生效（E046）：`setReadOnly(true)` 后 hasWriteAccess 断言失败；唯一可写挂载点 stat 为 drwxrws--x (2771)，无 POSIX 0700 语义 | 设备提供 ext4/tmpfs 且保留 POSIX 权限位的可写挂载点 |
| NamedPipe / Pre test cleanup | 1 | /tmp 只读 (E002)：NamedPipe 相对名硬编码 `/tmp/` | 设备提供可写 /tmp 或 JUCE 支持绝对路径 pipe |
| NamedPipe / Create pipe | 4 | 同上（mkfifo /tmp 失败） | 同上 |
| NamedPipe / Existing pipe | 3 | 同上 | 同上 |
| NamedPipe / Receive message created pipe | 4 | 同上 | 同上 |
| NamedPipe / Receive message existing pipe | 4 | 同上 | 同上 |
| NamedPipe / Send message created pipe | 4 | 同上 | 同上 |
| NamedPipe / Send message existing pipe | 4 | 同上 | 同上 |

- 已按恢复规则尝试：设置 `TMPDIR/TMP/TEMP` 至专用目录重跑（`PASSED: 401 FAILED: 8` 不变）；逐挂载点验证 0700（`/storage/Users/currentUser/tmp` → 2771，其余候选 mkdir 失败）→ 满足"仅在所有可用候选挂载点都无法满足真实 0700 语义，或合格目录下仍复现同一首错时记录平台阻塞"条件，判定为 HMDFS/平台阻塞，非库缺陷
- 扩展 runner（11 个无系统依赖模块并入，-DJUCE_UNIT_TESTS=1）编译成功但运行在 Files/Writing 后挂起（HMDFS 文件系统语义与并发行为），已停止并按 juce_core 独立运行数据如实上报

**双口径汇总**：
- 全量通过率：`401/409 (98.0%)`（juce_core 实例化单元口径）
- 源码声明口径：juce_core `55/168` 可实例化；`executed_passed/source_declared` 不做比例替代，缺失模块如实列于台账

## 验证结果

```bash
# 1. conan-verify 全部门禁
G0 ✅ / G1 ✅ / G2 conan create ✅ / G3 ✅ / G4 ✅ / L2/L4/L5 ✅ → PASS
# 2. 消费者程序（鸿蒙专项，test_package）
./test_juce → HELLO, HARMONYOS JUCE! (rc=0)
# 3. 上游测试 juce_core
./juce-test-runner.bin → PASSED: 401, FAILED: 8（平台限制，见台账）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（框架 header+module-source 分发，OHOS 适配） |
| conandata.yml | 官方 URL + sha256 + 补丁声明 |
| patches/0001-*.patch | pthread_cancel OHOS 守卫（E127） |
| test_package/ | 消费者验证（鸿蒙专项，juce::String 公开 API） |

## 注意事项

- JUCE 是模块化框架：本包安装全部模块头+源码+CMake 支持文件，消费者按需编译模块源
- 包级 cpp_info 带 `JUCE_USE_CURL=0`（OHOS 无 libcurl），消费者无需额外配置
- 消费者必须定义 `JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1`（JUCE 对消费者的标准要求）
- 任务类型为【知识库扩展】：候选知识为 OHOS musl 无 pthread_cancel 时 C++ 框架线程强制终止的通用适配模式（E127 已有先例，见知识候选台账以确认复用/新增）

## 知识候选台账（knowledge_candidate_ledger）

**候选 1：OHOS musl 无 pthread_cancel → C++ 框架线程强制终止适配**

- 真实错误：`juce_Threads_linux.cpp:63: error: use of undeclared identifier 'pthread_cancel'`
- 根因：OHOS musl libc 无 pthread_cancel（与 Android 同），JUCE Linux 分支 Thread::killThread() 调用之
- 修复：补丁 0001 与 Android 分支同构，`#if defined(__ANDROID__)||defined(__OHOS__)` 时 killThread 退化 jassertfalse
- 验证：消费者程序编译链接运行成功；补丁 dry-run rc=0
- 适用范围：任何在 OHOS 上编译、Linux 分支调用 pthread_cancel 的 C/C++ 多线程库
- 四范围查重：正式知识 **E127 命中**（pthread_cancel undeclared identifier, HarmonyOS, 方案=条件编译守卫）、E085（musl pthread_cancel 检测）、草稿 E407（portaudio HAVE_PTHREAD_CANCEL configure 探针）
- **七轴查重**：
  - exact_duplicate: true（E127 完整覆盖：同类错误、同类根因、同类方案——条件编译守卫）
  - causal_duplicate: true（E127 根因=OHOS 无 pthread_cancel，完全相同）
  - trigger_overlap: true（编译期 undeclared identifier 触发面重合）
  - solution_overlap: true（E127 推荐 #ifdef __OHOS__ 守卫，本次补丁同构）
  - combination_novelty: false（无新组合）
  - boundary_novelty: false（无新边界）
  - test_migration_novelty: false
- 既有条目覆盖：E127 已覆盖错误面+根因+方案
- **路径决定：reuse_existing（复用 E127），不建新草稿**

**候选 2：OHOS sysroot 无 libcurl → C++ 框架网络后端裁剪（JUCE_USE_CURL=0 配方级传播）**

- 真实错误：`fatal error: 'curl/curl.h' file not found`（juce_core.cpp:105）
- 根因：OHOS sysroot（ohos-sdk native sysroot）不含 libcurl 头与库，JUCE_USE_CURL 默认 1
- 修复：配方 `cpp_info.defines = ["JUCE_USE_CURL=0"]` 随 CMakeDeps `juce::juce` 目标传播；test_package 链接目标继承
- 验证：conan-verify G2 conan create PASS；消费者编译链接运行 `HELLO, HARMONYOS JUCE!` rc=0；`find sysroot -name curl.h` 无输出
- 适用范围：OHOS 上默认启用 libcurl 网络后端的 C/C++ 框架（JUCE 类），网络后端可整体裁剪、不影响核心 API
- 四范围查重：正式知识**未命中**（grep curl/curl.h/JUCE_USE_CURL 无对应条目）；E017 是下载镜像（不同问题）、E299 是 conan 源下载（不同问题）；草稿无同类
- **七轴查重**：
  - exact_duplicate: false
  - causal_duplicate: false
  - trigger_overlap: false
  - solution_overlap: false（cpp_info.defines 配方级传播 + CMakeDeps 目标继承是新增方案形态）
  - combination_novelty: true（"OHOS 无系统库 → 配方级裁剪宏 + 目标级传播"组合）
  - boundary_novelty: true（明确了仅链接目标才传播 defines 的边界——仅 include_directories 不够）
  - test_migration_novelty: false
- 既有条目覆盖：无
- **路径决定：new_draft → 草稿 E999-draft-BC6C（.kv/.md 配对，同 stem）**
- 关系字段：similar_to E127（同为 OHOS sysroot 缺系统能力→源码/配方级裁剪）、similar_to E321/E322（INTERFACE 库 conan 打包/CMakeDeps）；caused_by OHOS sysroot 无 libcurl（平台事实）；prerequisite_of 消费者在 OHOS 编译 juce_core

**候选 3：JUCE 模块源消费者编译模型（header+module-source conan 分发）**

- 真实错误：test_package 仅 include 头不编模块源 → 链接期 zlib/CompilationTime 符号缺失
- 根因：JUCE 模块是 INTERFACE 库，源由消费者编译；需加入 juce_core.cpp + juce_core_zlib.c（C 语言）+ juce_core_CompilationTime.cpp
- 修复：test_package CMakeLists `project(... C CXX)` + target_sources 三编译单元
- 验证：conan create PASS
- 适用范围：JUCE 类 header+module-source 框架的 conan 消费者验证
- 四范围查重：E321/E322 覆盖 header-only INTERFACE 打包（部分相关），但"模块源含独立 C 编译单元(zlib)+时间戳单元"的消费者验证形态未覆盖
- **七轴查重**：exact=false, causal=false, trigger_overlap=true(消费者链接失败), solution_overlap=true(目标编译单元), combination_novelty=true（C 语言启用 + 附带编译单元清单）, boundary_novelty=true, test_migration_novelty=false
- **路径决定：并入候选 2 草稿（E999 适用边界补充），不另建草稿（与候选2同库同修复面）**

**汇总决定**：reuse_existing（E127 覆盖候选1）+ new_draft（E999 覆盖候选2/3，可跨库复用，真实日志验证）→ **路径 B 成立**（【知识库扩展】）
---

**编译结束**: 2026-10-18 04:19
**最终状态**: built
