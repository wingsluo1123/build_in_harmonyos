# mesa 24.3.4.1.1 适配笔记（上游 Mesa 24.3.4，HarmonyOS PC）

## 版本说明

- Conan 包版本：`24.3.4.1.1`
- 上游源码版本：`24.3.4`
- 递增原因（r21-r22）：`mesa/24.3.4.1` 已在 ohpcd registry 发布（OSMesa-only recipe，revision c2271de0）；本轮交付需在同一上游 Mesa 24.3.4 上启用 GBM/EGL/GLES 制品，按 R37 递增为 `mesa/24.3.4.1.1`，避免与已发布 24.3.4.1 recipe 冲突（already-published-different-recipe）。上游源码仍为官方 Mesa 24.3.4 tarball。
- 当前目标：在无 X11/Wayland/DRM 的 HarmonyOS PC 上提供 `libOSMesa`，覆盖 Coin3 所需的 desktop OpenGL 固定管线入口。
- 构建策略：只编译 Meson 的 `OSMesa` 目标，安装时使用 `--no-rebuild`，降低真机有限账户空间下的中间文件峰值。
- GBM 修复增量（r17-r20）：`gbm=enabled` + `libdrm/2.4.133` requires + PkgConfigDeps，交付 `gbm.pc`/`gbm.h`/`libgbm.so`（含版本链接链），补丁 0007（harmonyos 按 DRM/KMS 平台识别）与 0008（libdrm 纯静态时 `--exclude-libs,ALL` 保持 libgbm 导出表仅 gbm_*，通过上游 gbm-symbols-check）。

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-10
- 编译器: clang/clang++（llvm 15.0.4，aarch64）
- 状态: built，Shadow CI r8 已通过（2026-09-11）

## 编译步骤

mesa 使用 Meson 构建。最小软件渲染（softpipe）配置，无窗口系统依赖：

```bash
# 依赖：expat（OHOS 制品仓 expat/2.8.2.1.1，需修正 expat.pc 的 prefix 指向 conan 缓存包）
meson setup build \
  --buildtype=release \
  -Dplatforms= \
  -Dgallium-drivers=softpipe \
  -Dvulkan-drivers= \
  -Dgbm=disabled -Degl=disabled -Dglx=disabled \
  -Dopengl=true -Dosmesa=true \
  -Dgles1=disabled -Dgles2=disabled \
  -Dllvm=disabled -Dlibunwind=disabled -Dvalgrind=disabled -Dzstd=disabled \
  -Dbuild-tests=false -Dtools=
ninja -C build OSMesa -j2
meson test -C build      # 待构建工具依赖补齐后执行
```

## Shadow CI 结果

- Shadow 任务：`mesa-24.3.4.1-shadow-20260910-r8-conan-r8`
- Runner：`rc=0`，设备全局锁等待 `0s`。
- 源码下载、SHA256 校验、解包、补丁应用和 Meson 配置均通过。
- `expat/2.8.2.1.1`、`bison/3.8.2`、`flex/2.6.4.2`、`m4/1.4.19` 均从 ohpcd 解析并复用成功。
- Mesa OSMesa/softpipe 编译完成 `881/881`，成功打包。
- `test_package` 真实编译并运行固定管线离屏渲染，输出：
  `OSMesa GL_VERSION: 3.3 (Compatibility Profile) Mesa 24.3.4`
  和 `test_mesa: ALL PASS`。
- Shadow L0/L1/L1e 全通过；L2 因本包没有 `bin/` 按规则跳过。
- L4 对 `0005-src-util-tests-cache_test.cpp.patch` 给出危险函数扫描告警；该项为非阻塞 warning，配方中的 `sprintf` 已替换为带长度限制的 `snprintf`。
- 远端证据日志：历史 shadow CI runner 日志（r8 运行，位于执行机 logs/stdout.log，具体绝对路径为基线遗留引用，按提交前扫描规则已从笔记中移除）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `clock_gettime` 未声明（strict C11） | meson.build 的 `_GNU_SOURCE` 注入列表不含 `harmonyos`（host_machine.system()=="harmonyos"） | meson.build 平台列表加入 `harmonyos`（patch 0002） |
| 2 | glapi 导出 `__emutls_*` 符号致 ABI-check 失败 | OHOS 工具链默认 emutls（模拟 TLS），mesa 仅对 Android NDK 加 `-fno-emulated-tls` | 对 `harmonyos` 同样注入 `-fno-emulated-tls`（patch 0002） |
| 3 | `util_get_process_name()` 返回空串 | OHOS 无 `program_invocation_name`/`getprogname`，落入返回 `""` 的兜底分支 | u_process.c 增 OHOS 分支，读 `/proc/self/exe`（patch 0006） |
| 4 | symbols-check/ABI-check 报额外导出 | Python `platform.system()` 在 OHOS 返回 `HarmonyOS`，白名单分支未覆盖；且 OHOS 运行库导出 `__at_fini`/`__cxa_finalize`/`_init`/`_fini` 等 | symbols-check.py 平台判断含 `HarmonyOS`，白名单补 OHOS 运行库符号（patch 0001） |
| 5 | u_printf 测试全部失败（输出为空） | OHOS `open_memstream()` 只在 `fflush()` 同步调用方缓冲区，`fclose()` 不更新 | u_memstream_close() 在 fclose 前显式 `fflush()`（patch 0004） |
| 6 | 磁盘缓存测试失败 | OHOS `/tmp` 只读（E002），测试硬编码 `/tmp/tmpdir.XXXXXX` | cache_test.cpp 改用 `$TMPDIR`（patch 0005） |
| 7 | 上游 meson test 2 组失败（已记录） | ①util_tests Cache.*：磁盘缓存 foz db 在 OHOS hmdfs 上 put/get 往返失败；②general_ir_test gl_nir_lower_mediump：GLSL IR 与编译器行为差异 | 非硬阻塞，如实记录为上游测试环境差异；不影响库交付 |
| 8 | `nm` 未找到导致 OSMesa 配置失败 | Mesa 24.3.4 在 `build-tests=false` 时仍无条件查找 `nm` | patch 0002 已改为仅在启用测试时查找 `nm` |
| 9 | test_package 运行时找不到 `libOSMesa.so.8` 并报告符号缺失 | OHOS loader 对 Conan 缓存中的未签名 `.so` 不装载；仅设置 `LD_LIBRARY_PATH` 不足 | `package()` 对安装后的 `.so` 和 OHOS 别名执行 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`；测试显式补齐 Mesa、SDK libc++ 和 libz 路径 |

## 源码修改

- `meson.build`（patch 0002）：harmonyos 平台注入 `_GNU_SOURCE` + `-fno-emulated-tls`
- `bin/symbols-check.py`（patch 0001）：HarmonyOS 平台识别 + OHOS 运行库符号白名单
- `src/util/u_process.c`（patch 0006）：OHOS 进程名（/proc/self/exe）
- `src/util/memstream.c`（patch 0004）：OHOS open_memstream close 前 fflush
- `src/util/tests/cache_test.cpp`（patch 0005）：mkdtemp 用 $TMPDIR
- `src/gallium/tests/trivial/meson.build` + `ohos_adapt_test.c`（patch 0003）：新增鸿蒙专项测试
- `src/gallium/targets/osmesa`（上游目标）：构建无窗口系统依赖的 `libOSMesa`，提供 desktop OpenGL 固定管线入口

## 依赖版本

- expat/2.8.2.1.1（OHOS 制品仓 ohpcd 预编译包）
- bison/3.8.2 / flex/2.6.4.2 / m4/1.4.19 / python3 3.12.9 / mako 1.4.1

## 验证结果

本版本已完成真机 Shadow CI，`conan create`、Mesa 共享库打包和消费者运行验证均通过。包内共享库产物包括：

- `lib/libOSMesa.so.8.0.0`、`lib/libOSMesa.so.8`、`lib/libOSMesa.so`
- `lib/libglapi.so.0.0.0`、`lib/libglapi.so.0`、`lib/libglapi.so`

```bash
# Shadow CI 已执行：
conan create archives/m/mesa/24.3.4.1.1 --build=missing
# test_package 输出：
# OSMesa GL_VERSION: 3.3 (Compatibility Profile) Mesa 24.3.4
# colored pixels: 1152
# test_mesa: ALL PASS
```
---

**最后更新**: 2026-09-11
**最终状态**: built（Shadow CI r8 通过）
## r23 全量测试复验（2026-09-19）

- 按官方 Mesa 24.3.4 源码 + patches 0001-0010 副本，OSMesa/softpipe 适用配置（osmesa=true/egl=enabled/gles1+gles2 enabled/build-tests=true）完整枚举测试声明：source_declared_total=49（r15 build-test 仅 45，缺 osmesa-render/osmesa-symbols-check/egl-symbols-check/egl-entrypoint-check）。
- 全量执行 meson test：修复前 45 OK/3 FAIL/1 SKIP；新增 patches/0010（osmesa-symbols-check 对 libc weak-UND pthread_mutexattr_* 的 --ignore-symbol，llvm-nm -gP 四字段 'w 0 0' 被 symbols-check.py 误判为导出，GNU nm 两字段 'w' 本会跳过）后 osmesa-symbols-check FAIL→PASS，终态 46/49 (93.9%)。
- 剩余 2 FAIL：util_tests（HMDFS 平台限制，Cache.* 7 例，候选挂载点全部无法满足真实 0700 语义，恢复条件已列）；general_ir_test（上游 GLSL IR 行为差异，r15 R12#7 同源）。1 SKIP：egl-symbols-check（静态 EGL 所致，上游脚本对 .a 返回 GNU skip 77）。
- OHOS 专项 ohos_adapt_test ALL PASS；test_package test_mesa ALL PASS；libdrm/2.4.133 + pciutils/3.13.0 消费编译链接运行 exit 0；conan create RC=0。
---

**编译结束**: 2026-09-19 20:27
**最终状态**: built
## r38 修订（24.3.4.1.1.1，2026-10-09）：X11 window 平台/GLX 启用

### 修订目标
- gtk4/4.22.4-r1 gsk-gl 2450 项真实平台条件失败：mesa/24.3.4.1.1 无 x11 平台变体（EGL 在 X11 display 仅 PBUFFER 配置、WINDOW_BIT=0、无 EGL_EXT_platform_x11/KHR_platform_x11）+ Xvfb 无 GLX + mesa 无 libGL.so.1。
- 恢复条件 = mesa 修订提供 x11 window 平台（EGL WINDOW_BIT 配置）或 GLX/libGL。

### 修订内容（R37 版本递增 24.3.4.1.1 → 24.3.4.1.1.1）
- `platforms="x11"`：新增 x11 平台变体 → EGL `EGL_MESA_platform_x11`/`KHR_platform_x11` 扩展与 WINDOW_BIT 配置可用。mesa 24.3.4 的 platforms 选项只接受窗口系统平台（x11/wayland/haiku/android/windows/macos）；surfaceless 是 EGL 在无窗口平台时内建自动启用（platforms 不含 surfaceless 值也始终可用），drm 路径由 gbm=enabled/dri 提供而非 platforms 值——首次尝试 `platforms=surfaceless,drm,x11` 被 meson 以 allowed-choices 拒绝（ValueError: Values "surfaceless, drm" ... not in allowed choices），按真实构建约束修正为 `platforms="x11"`。
- `glx="dri"`：启用 GLX 目标产出 libGL.so.1/libGLX（meson 目标 GL），供 GLX 路径与 libepoxy 上游测试恢复。mesa 24.3.4 的 glx 选项只接受 auto/disabled/dri/xlib（不接受 enabled——首跑 `glx=enabled` 被 meson 以 allowed-choices 拒绝），dri 配合既有 gbm/libdrm 软件路径。
- 补齐 X11 客户端依赖：libx11/6.4.0（Xlib/X11-xcb 头与库）、libxcb/1.16（X protocol 绑定，EXTENSION_LIBS 组件提供 xcb-glx/xcb-shm/xcb-dri2/xcb-dri3/xcb-present/xcb-sync 的 xcb-*.pc）、xorgproto/2025.1（协议/扩展头 + glproto/dri2proto pc 模块）、libxext/6.4.0（mesa meson dependency('xext')）、libxfixes/6.1.0（dependency('xfixes')，glx=dri 必需）、libxshmfence/1.3.3（with_dri_platform='drm' 必需）、libxxf86vm/1.1.5（with_glx_direct）、glproto/1.4.17（dependency('glproto')——xorgproto share/pkgconfig 的 glproto.pc 在 conanbuild 环境探测不到，改显式 requires），全部 transitive headers；仅客户端库，禁止 Xvfb 服务器端依赖混入。构建迭代实证：前 7 次 configure 分别在 platforms（不合法值）、glx（不合法值 enabled）、xext 缺失、xfixes 缺失、glproto 缺失、dri2proto 缺失处中断，逐次修正/补齐；dri2proto 由 generate() 显式把 xorgproto 的 share/pkgconfig 追加进 buildenv PKG_CONFIG_PATH 解决（第七次实证 PkgConfigDeps 不生成 xorgproto 协议 pc）。
- build 目标列表加入 `GL`（mesa src/glx 的 shared_library('GL')），package() 补 libGL.so/libGL.so.1 链接名（SONAME libGL.so.1.2.0→1.2.0 实际版本以构建产物 glob 兜底）。
- 依赖可用性（W0）：libx11/6.4.0、libxcb/1.16、xorgproto/2025.1、xtrans/1.6.0、libxau/1.0.11/1.0.12、libxdmcp/1.1.5、xcb-proto/1.17.0 全部已在 ohpcd 制品仓发布（conan download --only-recipe 均解析到 revisions）。

### 验证（核心）
- conan create 成功后核对：eglChooseConfig 返回 WINDOW_BIT 配置（>0，对照 24.3.4.1.1 WINDOW_BIT=0）；EGL_EXT_platform_x11/KHR_platform_x11 扩展存在于 eglQueryString(EGL_EXTENSIONS)；libGL.so.1 产出（nm -D）;Xvfb :199 进程级 EGL x11 窗口上下文验证（eglGetPlatformDisplay(EGL_PLATFORM_X11) + eglCreateWindowSurface + eglMakeCurrent + 渲染 exit 0）。

### 处置记录
- 本修订新增 patch 0013（src/gallium/frontends/dri/meson.build）：r38 x11 平台使 loader_dri3_helper.c 进入 libdri 编译集，其 include X11/Xlib-xcb.h（libx11 x11-xcb 组件）但 libdri 目标 drm 分支未挂 dep_x11_xcb（第十次构建编译阶段 fatal error: 'X11/Xlib-xcb.h' file not found），补依赖后 x11-xcb include 到达该目标。
- 新增 patch 0014（src/gbm/backends/dri/meson.build）：with_platform_x11 使 HAVE_X11_PLATFORM 生效后 loader_dri_helper.h include xcb/xcb.h、xcb/dri3.h、xcb/present.h，dri_gbm 目标编译需 xcb include 路径（第十三次构建 fatal error: 'xcb/xcb.h' file not found），with_platform_x11 时补 dep_xcb。
- platforms/glx 是 Meson option 级变更，补丁集 0001-0012 沿用 24.3.4.1.1。

## r38 上游测试台账（双口径，2026-10-09）

- 上游源码与 r23 相同（官方 mesa-24.3.4.tar.xz，SHA-256 e641ae27…），测试声明集合不变：**source_declared_total=49**（r23 已按可复制枚举规则清点：util_tests 分项、gallium 各 driver 测试、egl-symbols-check/egl-entrypoint-check、osmesa-render/osmesa-symbols-check、gbm-abi-check、glsl/nir 编译器测试等）。
- 本修订交付配方 `build-tests=false`（与 24.3.4.1.1 交付一致），conan create 产物未实例化 meson test 套件；本轮实际运行的本修订相关检查项：
  - `egl-symbols-check`（symbols-check.py --lib libEGL.so.1.0.0）exit 0
  - `egl-entrypoint-check`（eglentrypoint.h 对照 GLVND entrypoints）exit 0（All good）
  - `osmesa-symbols-check`（--lib libOSMesa.so.8.0.0 + pthread_mutexattr ignore）exit 0
  - `gbm-symbols-check`（--lib libgbm.so.1.0.0）exit 0
  - `test_package test_mesa`（conan create 内嵌）：OSMesa GL_VERSION 4.5 + 渲染像素 1152，ALL PASS
  - 鸿蒙专项进程级 EGL x11 窗口验证（oh-runner-tmp/egl-x11-window-probe.c）：WINDOW_BIT 配置 16 个、EGL_EXT_platform_x11/KHR_platform_x11 YES、eglGetPlatformDisplay(X11) OK、eglCreateWindowSurface+eglMakeCurrent+渲染 readback exit 0
- 统计口径：上游声明 49 项（基线 r23 实测 46/49，2 FAIL 为 HMDFS 平台限制 util_tests Cache.* 与 general_ir_test 上游 GLSL IR 差异、1 SKIP 为静态 EGL 时代 egl-symbols-check，均已在 r27/r29 共享 EGL + r38 修订后处置）；本轮配置可执行集合通过率以实际运行检查为准，未实例化项不虚报为通过/失败。

## r38 知识候选台账（2026-10-09）

- 候选：OHOS PC gtk4 gsk-gl 需要 mesa EGL x11 window 平台（WINDOW_BIT 配置 + EGL_EXT_platform_x11/KHR_platform_x11 + libGL.so.1），通过 mesa `platforms=x11` + `glx=dri` + X11 客户端依赖（libx11/libxcb/xorgproto/libxext/libxfixes/libxshmfence/libxxf86vm/glproto/libxrandr）启用。
- 根因：mesa 24.3.4 默认无窗口平台（platforms= 空），EGL 仅 surfaceless/PBUFFER，无 WINDOW_BIT 配置与 X11 平台扩展，gtk4 gsk-gl 在 X11 display 全灭（2450 项）。
- 修复：platforms=x11 + glx=dri + X11 客户端依赖链 + 2 个 meson 依赖补丁（0013/0014），libGL.so.1 交付。
- 验证：eglChooseConfig WINDOW_BIT>0（16 个配置）、EGL_EXT_platform_x11/KHR_platform_x11 客户端扩展、libGL.so.1 SONAME、Xvfb :199 进程级 eglGetPlatformDisplay(X11)+eglCreateWindowSurface+eglMakeCurrent+渲染 exit 0。
- 适用范围：任何依赖 GL/EGL/GLX 的 OHOS PC 库（gtk4、libepoxy、cairo-gl、webkitgtk 等）；约束：仅客户端依赖，禁止 Xvfb 服务器端依赖混入；mesa 24.3.4 的 platforms/glx 选项合法值约束（x11/wayland…与 auto/disabled/dri/xlib）。
- 查重（对照 knowledge/graph/index.tsv 与既有条目）：未命中既有完整等价条目——24.3.4 适配（GBM/EGL/GLES）与 24.3.4.1（共享 EGL）均未覆盖 x11 window 平台启用；libXext/libx11 等条目为 X11 客户端链适配，不含 mesa 平台变体启用。此候选为既有 mesa 适配的增量组合（platforms=x11+glx=dri），判定：**combination_novelty 成立、boundary_novelty 成立（mesa x11 变体 + X11 客户端依赖链 + meson 依赖补丁组合）**。
- 七轴查重明细：exact_duplicate=否（无同主题 mesa x11 平台条目，index.tsv 无 mesa/EGL/GLX 条目）；causal_duplicate=否（根因是不同的：本候选根因=mesa 无窗口平台变体，既有条目根因=platforms= 空与 GBM/EGL 交付，非同一因果链）；trigger_overlap=部分（与 24.3.4 适配共享 meson 平台检测类触发，但触发点是 EGL x11 扩展/WINDOW_BIT 缺失，差异明确）；solution_overlap=部分（复用 24.3.4 的 PkgConfigDeps/generate() 骨架，新增 x11 平台选项与 X11 依赖链、2 个 meson 依赖补丁）；combination_novelty=成立（platforms=x11+glx=dri+X11 客户端依赖链+patch 0013/0014 的组合为既有无）；boundary_novelty=成立（适用范围扩展到任何 GL/EGL/GLX 消费库，边界含 mesa 24.3.4 的 platforms/glx 选项合法值约束与"禁止 Xvfb 服务器端依赖"）；test_migration_novelty=不适用（无既有测试迁移）。similar_to=24.3.4 GBM/EGL 适配知识；caused_by=24.3.4 platforms= 空（无窗口平台）；prerequisite_of=gtk4 gsk-gl EGL x11 window 路径、libepoxy GLX 上游测试；conflicts_with=无。
- 路径决定：**路径 B（new_draft）**——combination_novelty/boundary_novelty 成立且已由本轮真实日志验证（WINDOW_BIT>0 + 扩展 + libGL.so.1 + Xvfb 进程级 exit 0），可跨库复用（任何依赖 GL/EGL/GLX 的库）；按任务规则建立同 stem 的 .md/.kv 成对草稿（knowledge/drafts/DRAFT-mesa-x11-platform-glx-ohos.*）。

## R02 上游测试双口径台账（build-tests=true 全量实测，2026-10-09/10）

### 门禁 1：build-tests=true 全量实例化
- 交付配方 build-tests 由 false 改为 **true**（消除 PR #15158 正文 0/49 与基线 #11116 2983/3264 少报不一致，rule4 先例）；
- 构建：`conan create archives/m/mesa/24.3.4.1.1.1 --build=missing -pr:h=ohos -pr:b=default`，第 3 次构建成功（前 2 次定位并修复：source() 复制 ohos_adapt_test.c 缺 src_additions 路径段、meson install 需 pipe_swrast 目标），test_package ALL PASS；
- meson 注册 55 项（44 exitcode + 11 gtest 协议），其中 gtest 协议在运行时按用例展开并逐用例执行；非 0、已全量实例化。

### 门禁 2/3：全量实测与通过率（Xvfb :199 + x11 环境，TMPDIR=oh-runner-tmp）
- **source_declared_total = 3264**（基线 #11116 同源枚举口径，官方 tag 源码声明的可复制枚举总数）；
- **configured_executable_total = 55 注册项**（meson test --list），gtest 协议用例运行时展开实测（详见下）；
- **executed_passed_total = 3060**：
  - gtest 用例逐项运行 3030 个（11 个 gtest 二进制含 LLVM/conanrun 环境），**3016 PASS / 14 FAIL**；
  - exitcode 协议 44 项全部 PASS（drirc/xmlconfig/process/vma/format/glcpp/glsl/lp_*/osmesa-symbols/gbm-abi+symbols/egl-symbols+entrypoint/es1/es2-ABI/shared-glapi symbols 等）；
  - 合计 3016 + 44 = **3060 PASS**；
- **failed = 14**：util_tests Cache.* 7 项（HMDFS 磁盘缓存平台限制）+ general_ir_test gl_nir_lower_mediump 7 项（上游 GLSL IR 行为差异），均为基线 r23 已知同源失败，恢复条件已列；
- **skipped/uninstantiated = 3264 − 3074 = 190 项**（3264 − (3030 ran + 44 exitcode)）：为当前 softpipe/llvmpipe+x11 配置下未实例化的驱动 GTest（如 valhall 反汇编、freedreno/etnaviv/r600 等非本配置驱动的用例）与参数化/条件宏排除项，按规则计入分母不计通过，逐项恢复条件见下；
- **通过率 = 3060/source_declared 3264 = 93.8% ≥ 基线 2983/3264 = 91.4%，不倒退**；当前配置可执行集合通过率 = 3060/3074 = 99.5%（另列）。

### 逐项映射（源码声明/注册项 → 构建目标 → 实际执行日志）
- meson 注册项 ↔ gtest 用例展开映射：util(process/clear/collision/hash/vma 等 exitcode) + xmlconfig_test(15)/util_tests(176)/shared-glapi-test(2)/nir_tests(2659)/spirv_tests(19)/general_ir_test(61)/sampler_types_test(41)/list_iterators(30)/gallium-aux(1)/osmesa-render(10)/main_test(16) 等 11 个 gtest 二进制逐用例；
- 执行日志（绝对路径 + SHA-256）：
  - `~/.oh-runner/logs/mesa-24.3.4.1.1.1-r02-conan-create3.log`（构建+test_package，SHA-256 见 R02 result）
  - `~/oh-runner-tmp/r02-meson-test-full.log` sha256 04526ba46d91708a3c787be6898eeaa5f0b13b23a23cf27c545577fdf79b932b
  - `~/oh-runner-tmp/r02-gtest-cases.log`（xmlconfig 15/15）sha256 97c67809f7bc800357943b7518bba985e22a00d5fbc54ebef8b59eb7c16d1f85
  - `~/oh-runner-tmp/r02-gtest-batch1.log`（util 169/7、shared-glapi 2、nir 2659、spirv 19）sha256 2b5445be06884bc87c28e9eef3bf4f022051f18443c49acc510a94e7ed870519
  - `~/oh-runner-tmp/r02-gtest-batch2.log`（general_ir 54/7、sampler 41、list 30、gallium-aux 1、osmesa-render 10、main 16）sha256 aa2f9706cb7a25ea75f47fb32adeddb0f331b9aee7acf19ec9fd3d4e28391e89
- 未实例化 190 项恢复条件：属非当前驱动的 GTest/参数化条件项，需启用相应 gallium/vulkan 驱动（如 valhall 需 panfrost 构建）或对应硬/依赖后才可实例化；当前交付配置（softpipe/llvmpipe+x11/GLX 恢复目标）不产生该等条件。

### 门禁 4：PR #15158 正文同步
- 按 3264 口径更新 PR 正文测试统计（3060/3264 = 93.8%，另列当前配置集合 3060/3074 = 99.5%），消除 0/49 少报（见 #7 执行）。
