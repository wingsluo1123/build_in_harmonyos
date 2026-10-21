# KB-NO-OPENGL 工作笔记（取证 · 踩坑 · 验证证据）

## A. 选题依据（为什么是 OpenGL，而不是别的）

1. 现场命中：适配 `osmin/1.15.1` 时，vendored 的 `libosmscout-client-qt` 在 OHOS qtbase 上编译失败，
   报 `use of undeclared identifier 'QOpenGLContext'`；同批候选问题里另有一个 C++20 `std::views`
   报错（`-D_LIBCPP_ENABLE_EXPERIMENTAL` 可解）。
2. 知识图谱覆盖核查：
   * `QT_NO_OPENGL` / Qt OpenGL 模块缺失：**0 条覆盖**（`knowledge/graph/index.tsv` 全文无相关条目）。
   * libc++ `ranges/views`：**已 113 处覆盖** → 不具备「知识库拓展」价值，仅作为本包适配手段。
3. 共性判定：该问题由「Qt 裁剪构建 + 下游直用可选模块 API」引起，与具体库无关，
   凡消费 Qt6 的包都可能命中 → 属于**一类共性问题**，可提炼为通用检测 + 通用处理策略。

## B. 现场取证（真实库，非样例）

证据均在 conan 缓存内的 qtbase/6.11.1 包目录与 libosmscout 源码树上实测：

| # | 事实 | 取证命令（口径） | 结果 |
|---|---|---|---|
| B1 | 目标 Qt 无 OpenGL 能力 | 读 `include/QtGui/qtgui-config.h` | `QT_FEATURE_opengl -1`、`QT_NO_OPENGL 1`（:124） |
| B2 | 包内无 OpenGL 头目录 | 列 `include/Qt*` | `QT6GL_DIRS=0`、`NO_QtOpenGL_DIR` |
| B3 | 无 `QOpenGLWidget` 头 | 探测 `include/QtOpenGLWidgets/QOpenGLWidget` | `NO_QOpenGLWidget_header` |
| B4 | 无 OpenGL 的 cmake 配置 | 列 `lib/cmake/Qt6OpenGL*` | `NO_Qt6OpenGL_cmake` |
| B5 | 转发头 + 整体门控 | 读 `include/QtGui/QOpenGLContext` 与 `qopenglcontext.h` | 转发头不受门控；`qopenglcontext.h` / `qopenglfunctions.h` **全文**被 `#ifndef QT_NO_OPENGL` 包住 |
| B6 | 下游使用点 | 读 `libosmscout-client-qt/src/osmscoutclientqt/TiledMapRenderer.cpp`（575 行） | include 在 32-35 行；调用点 `:208-209` `QOpenGLContext::currentContext()` / `glContext->functions()->hasOpenGLFeature(QOpenGLFunctions::NPOTTextures)` |
| B7 | GL 块语义 | 同上 | 仅把 `glPowerOfTwoTexture` 由 `Upscaling` 改为 `NoScaling`（NPOT 扩展探测，**可选优化**） |
| B8 | 全树 GL 使用面 | 全树扫 `QOpenGL` / `QtOpenGL` / `libGL` | 仅 `TiledMapRenderer.cpp` 一处（osmin 自身零使用） |
| B9 | 修复后链接成功 | 预验证构建 `OSMScoutClientQt` 目标 | `libosmscout_client_qt.a`（7.3 MB）产出，0 编译错误 |

结论：B5 解释了报错「反直觉」的原因（include 成功但内容空），B7 决定修复安全（跳过等价于无 GL），
B8 决定补丁面只有 1 个文件、3 个 hunk。

## C. 修复设计决策

* **用上游既有宏 `QT_NO_OPENGL`，不引入平台宏**（如 `__OHOS__`）：Qt 自己定义该宏，
  因此补丁在任何平台都语义正确（有 GL 的构建编译原逻辑），也天然满足 R8/PF5 的平台宏闸。
* **门控范围**：include 区（2 行）+ 使用点（跨行 `if` 条件块）。使用点首行以 `;` 结尾
  （`if (QOpenGLContext *glContext = QOpenGLContext::currentContext();`），
  后续还有两行 `&& ...` 条件——**逐行判定会在第一行就收尾，导致 `#endif` 插进条件中间**，
  必须做花括号/条件续行缓冲。`fix.sh` 的 FIX-B 分支即为该形态。
* **与上游补丁叠加性**：本包另有上游 `libosmscout_4.patch`（445 行 hunk）改同一文件，
  但其 hunk 起点在 445 行附近，与门控目标行（29 / 205）**无重叠**，可叠加。
* **补丁 root**：走 osmin 源码根（补丁头 `a/backend/libosmscout/...`），
  `export_conandata_patches` + `apply_conandata_patches` 默认 `strip=0`，
  patch_ng 对 GIT 格式补丁自动剥 `a/ b/`（与仓库既有惯例一致）。

## D. 工具实现踩坑（都是实测 bug，已修）

1. **awk 函数内变量未声明为局部 → 污染全局计数器（严重）**
   现象：FIX-B 分支产出的门控块只剩 `#ifndef`/`#endif` 空壳，块内代码行**全部丢失**。
   根因：`brace_delta()` 里 `nb`/`nc` 未列入函数参数列表，awk 把它们当全局变量写入，
   循环结束后 `nb` 归零，随后 `for (k = 1; k <= nb; ...)` 一行也输出不了。
   定位手段：最小样本 + 打点（`DBG nb=0 pd=1`）区分「脚本缺陷」与「awk 实现差异」。
   修复：把 `nb`/`nc`/`t`/`p` 声明为函数局部参数。**教训：awk 没有块级作用域，函数参数即局部变量声明。**
2. **非 POSIX 转义**：脚本里用 `\x27` 表示单引号，在非 gawk 实现下不可移植 → 改 `sprintf("%c", 39)`。
3. **`awk -v` 参数顺序**：`-v` 必须写在程序文本之前，否则被当成文件名（`cannot open file '-v'`）。
4. **门控指令缩进**：早期按被门控代码缩进输出，与人工补丁（第 0 列）不一致；
   统一为第 0 列后与人工补丁**逐字节一致**。
5. **本机 awk 实现**：`/usr/bin/awk` 是 toybox 符号链接（`--version` 却自称 gawk），
   PATH 首位另有 `/data/service/hnp/bin/awk`。最小样本下两实现输出一致 → 差异不来自实现，来自脚本自身缺陷。
6. **本机 `patch` 不可信**：`/usr/bin/patch` 是 toybox（对补丁静默 no-op 且 rc=0），
   校验补丁必须用 `git apply --check`（本条目全部补丁均以此校验）。

## E. 保真校验方法（脚本产物 ≡ 人工补丁）

流程（`MATCH_MANUAL_PATCH=YES` 即通过）：

1. 取**真实上游文件**（纯净 tarball 版）与「已知加过门控」的副本；
2. 用反向套用补丁的方式还原出「上游原样」基准 → 与 tarball 版比对确认基准正确；
3. 在基准上跑 `fix.sh`，与人工补丁结果 `cmp` → **逐字节相同**；
4. 由 `fix.sh --emit-patch` 导出的补丁，在干净树上 `apply → 反向还原` 往返一致（幂等）。

实测结论：`MATCH_MANUAL_PATCH=YES`、幂等成立、导出补丁可干净套用。

## F. 样例库踩坑（Qt6 + Conan 2 特有）

1. **CMakeDeps 与 `cmake_find_mode=none` 的冲突**：`qtbase/6.11.1` 的 `cpp_info` 设了
   `cmake_find_mode=none`（不产出 `qtbase-config.cmake`），但 CMakeDeps 为消费者生成的
   `noopengldemo-config.cmake` 仍带一条 `find_dependency(qtbase)` → 必然失败。
   处理：样例的 test_package 不走 CMakeDeps 的 config，改为**显式路径链接**
   （`NOOPENGLDEMO_INCLUDE_DIR` / `NOOPENGLDEMO_LIB_DIR` 由 test_package 的 `generate()` 注入），
   Qt6 侧仍用 `<组件>_DIR` 注入（沿用 `qtbase` 包内 `lib/cmake/<组件>/<组件>Config.cmake` 探测）。
2. **`self.run(exe, env=...)` 只能传字符串**：传 `VirtualRunEnv(self).environment()` 得到的对象会报
   `AttributeError: 'str' object has no attribute '_values'`；正确写法 `self.run(exe, env="conanrun")`
   （配合 `generate()` 里的 `VirtualRunEnv(self).generate()`）。
3. **`conan cache path qtbase/6.11.1` 返回的是导出目录（`.../p/<hash>/e`），不是包目录**
   → 需要包目录时扫 `${CONAN_HOME:-$HOME/.conan2}/p/*/p`（判据：`include/QtGui/qtgui-config.h` + `lib/cmake`）。

## G. 环境事实（W0b 环境语义可迁移性）

* 本机 `uname -m` = **aarch64**（OHOS PC），host 与 host 工具同为 aarch64，**无需 qemu/binfmt**。
* 交叉/异构场景下 Qt 的构建期 host 工具（`moc`/`rcc`/`repc`…）需要**运行期**依赖可见：
  排雷构建中 `repc` 曾报 `Error relocating .../repc: _ZN10QByteArray6_emptyE: symbol not found`
  （make 报 Error 127，看似「工具跨架构不可用」）。实测根因是 **`LD_LIBRARY_PATH` 未包含 Qt6 库目录**
  （手工 cmake 未 source `conanrun.sh`）——带上后 `repc --help` 正常（`repc tool v1.0.0 (Qt 6.11.1)`，rc=0）。
  即：**该报错不是上游代码/配方缺陷，而是缺 `VirtualRunEnv`**；配方中保留 `VirtualRunEnv(self).generate()`
  即可让 CI/本地一致通过。

## H. 验证证据（本机实测，日志落盘）

| 验证项 | 命令 | 结果 |
|---|---|---|
| 阶段 OFF（关 SKILL） | `conan create .`（样例库原样） | rc=1，`renderer.cpp:19: use of undeclared identifier 'QOpenGLContext'`（含 `glContext` 连锁报错） |
| 检测命中 | `detect.sh --src <sample> --qt-prefix <qtbase 包> --log <off.log>` | rc=7（位或：1 源码使用 GL + 2 目标 Qt 无 OpenGL + 4 日志特征） |
| 处理策略 | `fix.sh --src <sample> --emit-patch kb-no-opengl.patch` | rc=0，1 文件 0 跳过，补丁已导出 |
| 阶段 ON（开 SKILL） | `conan create .`（门控后） | rc=0，消费者测试运行输出 `OK: no-GL build keeps the default scaling strategy (GL path skipped)` |
| 端到端脚本 | `reproduce.sh --json --keep` | `verdict=PASS`（两阶段均符合预期，`phase_on_test_hit=1`） |
| 保真校验 | `kbtest_fidelity.sh`（真实上游文件） | `MATCH_MANUAL_PATCH=YES`、幂等成立、导出补丁可套用 |
| 真实库受益 | 预验证构建 `OSMScoutClientQt` | `libosmscout_client_qt.a` 7.3 MB 产出（此前编译即失败） |

## I. 限制

* 仅在「GL 分支可安全跳过」时成立（见 README §7）；GL 为功能必需时本策略会掩盖缺陷，应判 `env_unsupported`。
* `detect.sh` 的源码判定基于 `QOpenGL*` 字面量，宏拼装（如 `QT_OPENGL_NAMESPACE::Foo`、
  宏展开后形成的类型名）可能漏报——漏报只影响检测灵敏度，不影响 `fix.sh` 的确定性处理。
* 样例库依赖 `qtbase/6.11.1` 二进制（含 OHOS 平台），离线环境需预热该包。
