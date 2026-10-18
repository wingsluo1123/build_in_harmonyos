# KB-NO-OPENGL：Qt6 无 OpenGL 构建下的下游 GL 代码门控

**编号**：KB-NO-OPENGL  **类型**：平台配置类共性问题（Qt6 交叉/裁剪构建）  **处理策略**：②补丁模板（源码门控）

## 1. 触发场景（什么时候会遇到）

目标 Qt6 是**裁剪构建**、未编出 OpenGL 模块（`QtOpenGL` / `QtOpenGLWidgets`），而下游库/应用代码里
直接使用了 `QOpenGLContext` / `QOpenGLFunctions` / `QOpenGLWidget` 等 API。典型现场：

* 鸿蒙 PC（OHOS）制品仓的 `qtbase/6.11.1`：`qtgui-config.h` 里 `QT_FEATURE_opengl` 为 `-1`，
  `QT_NO_OPENGL` 被定义 —— 该 Qt 从不提供 OpenGL 模块；包内也没有 `QtOpenGL` 头目录、没有 `Qt6OpenGL` 的
  cmake 配置文件。
* 上游代码为「桌面全功能 Qt」写的：GL 调用可能只是**可选优化**（如探测 `GL_ARB_texture_non_power_of_two`
  决定是否缩放瓦片），并非核心功能。

判断要点：**报错发生在「头文件平白可用、符号却不存在」时**，几乎必然是这一类问题
（`QT_NO_OPENGL` 把整个头内容屏蔽，但转发头 `QtGui/QOpenGLContext` 仍在，include 不报错）。

## 2. 症状与识别特征

```
/path/to/renderer.cpp:19:35: error: use of undeclared identifier 'QOpenGLContext'
  if (QOpenGLContext *glContext = QOpenGLContext::currentContext();
                                  ^
/path/to/renderer.cpp:22:51: error: use of undeclared identifier 'QOpenGLFunctions'
      && glContext->functions()->hasOpenGLFeature(QOpenGLFunctions::NPOTTextures)) {
```

识别三件套（`detect.sh` 自动完成）：

| 判据 | 期望值 | 取证方式 |
|---|---|---|
| 目标 Qt 无 OpenGL | `QT_FEATURE_opengl -1`、`QT_NO_OPENGL 1`（`QtGui/qtgui-config.h`） | 读 `qt-prefix/include/QtGui/qtgui-config.h` |
| 无 OpenGL 模块产物 | 无 `QtGui/QOpenGLWidget`、无 `lib/cmake/Qt6OpenGL*` | 目录探测 |
| 源码使用 GL API | `QOpenGL*` 出现在源码 include 或调用点 | 扫源码 |
| （构建日志）报错形态 | `use of undeclared identifier 'QOpenGL…'` 且**同一编译单元里 include 未报错** | 扫日志 |

关键区分：如果报的是 `fatal error: 'QOpenGLContext' file not found`（找不到头），那是 Qt 安装不完整或
`Qt6::OpenGL` 未链接，**不是**本条目场景。

## 3. 根因机理

1. OHOS 版 qtbase 的构建配置里 OpenGL feature 为关闭（`QT_FEATURE_opengl = -1`），
   `qtgui-config.h` 因此 `#define QT_NO_OPENGL 1`。
2. QtGui 的 `QtGui/qopenglcontext.h`、`qopenglfunctions.h` **全文**被 `#ifndef QT_NO_OPENGL … #endif`
   包住（已逐字节核实）；但 `QtGui/QOpenGLContext` 这类**转发头**（`#include "qopenglcontext.h"`）
   本身不受门控。
3. 于是下游 `#include <QOpenGLContext>` **成功**，其内容却为空 → 编译期
   `use of undeclared identifier 'QOpenGLContext'`。
4. 该报错信息具有误导性（像是「没 include」或「拼错名」），实际是**平台裁剪**导致的语义空洞。

## 4. 处理策略（② 补丁模板：源码门控）

用上游自己的门控宏，把 GL 使用点包进 `#ifndef QT_NO_OPENGL`：

* **include 区**：把 `#include <QOpenGLContext>`、`#include <QOpenGLFunctions>` 一起包住 —
  无 GL 时不再引入空壳头，也避免后续 `QT_NO_OPENGL` 未定义时的歧义。
* **使用点**：
  * 自包含语句/单行块 → 直接在其前后插 `#ifndef QT_NO_OPENGL` / `#endif`；
  * 多行 `if (...)` 块（含**首行以 `;` 结尾的条件**，如 `if (X *p = X::currentContext();` +
    后续 `&& …)` 跨行条件）→ 整块缓冲后统一加门控，**不能**只看第一行就判定块已结束。
* 门控后无 GL 环境的行为必须与「从未编译过 GL 代码」一致 —— 这正是样例库断言的性质。

`fix.sh` 已实现上述策略（幂等、自动备份、可导出补丁）：

```sh
sh fix.sh --src <源码目录> --emit-patch /tmp/kb-no-opengl.patch
```

已与人工补丁做**逐字节保真校验**：在真实上游文件（`libosmscout-client-qt/src/osmscoutclientqt/TiledMapRenderer.cpp`）
上，`fix.sh` 的产物与人工编写的门控补丁结果完全一致（`MATCH_MANUAL_PATCH=YES`，导出补丁可干净套用）。

**为什么可以安全跳过 GL 分支**（以真实库为例）：`TiledMapRenderer::RenderMap` 里的 GL 块只做一件事——
探测 `GL_ARB_texture_non_power_of_two` 并把 `glPowerOfTwoTexture` 从 `Upscaling` 改成 `NoScaling`，
即**性能优化开关**；无 GL 时保持默认缩放策略，渲染路径本身（Qt 光栅绘制）不依赖它。
判定口径：**先确认 GL 块是否只是可选优化/能力探测**；若 GL 是功能必需（真正的 OpenGL 渲染、
QOpenGLWidget 宿主），本策略不适用（见 §7），应改判 `env_unsupported`。

## 5. 适用范围

* **不限单一库**：任何消费 Qt6（或 Qt5 同理，宏名一致）且代码里直用 GL API 的下游库/应用；
  已实测：`libosmscout-client-qt`（`TiledMapRenderer.cpp`）、KB 样例库。
* **构建系统无关**：CMake / qmake / autotools 均可，补丁只动源码文本。
* **平台不限**：任何未提供 OpenGL 的 Qt 构建（嵌入式裁剪、无 GLES 的 OHOS/容器环境）都会遇到。
* 不适用：源码里 GL 是必需功能、或需要 Qt 提供 `Qt6::OpenGL` 目标链接（此时是缺模块，应申请适配
  `qt6-opengl` 或改判 `env_unsupported`）。

## 6. 工具与样例

| 文件 | 作用 |
|---|---|
| `detect.sh` | 只读检测：扫源码 GL 使用 + 目标 Qt 的 OpenGL 能力 + 构建日志报错特征 |
| `fix.sh` | 处理策略实现：给 GL 使用点加 `#ifndef QT_NO_OPENGL` 门控，可导出补丁 |
| `reproduce.sh` | 两阶段复现：阶段 OFF（关 SKILL）复现原报错 → 阶段 ON（开 SKILL）加门控后通过 |
| `sample/` | 样例演示库 `qt6-noopengl-demo/1.0.0`：复刻真实故障形态 + 真调用 API 的消费者测试 |
| `notes.md` | 取证记录、踩坑与验证证据（含实测命令与输出） |

```sh
# 检测（退出码位或：1=源码使用 GL 2=目标 Qt 无 OpenGL 4=日志命中特征）
sh detect.sh --src .

# 修复（幂等；--emit-patch 导出补丁）
sh fix.sh --src .

# 端到端复现（默认两阶段；--json 输出机器可读摘要）
sh reproduce.sh --json --keep
```

样例库阶段结果（本机实测）：

* 阶段 OFF：`conan create` 失败，报 `use of undeclared identifier 'QOpenGLContext'`（6 errors）。
* 阶段 ON：`detect.sh` rc=1（源码使用 GL）、`fix.sh` rc=0（1 file guarded）、`conan create` rc=0，
  且集成的消费者测试运行通过并输出 `OK: no-GL build keeps the default scaling strategy (GL path skipped)`。

## 7. 限制与反例

* **不是万能兜底**：只适用于「GL 分支可安全跳过」。若跳过会改变功能语义（例如 GL 是唯一渲染后端），
  禁止用本策略掩盖，应如实判 `env_unsupported`。
* **不要用 `#ifdef __OHOS__` 之类平台宏代替**：本策略用的是**上游既有能力宏**（Qt 自己定义的
  `QT_NO_OPENGL`），因此补丁在非 OHOS 平台同样正确（有 GL 的构建照常编译原逻辑）。
* **门控位置必须覆盖全部引用**：包括类型出现在后续语句（如 `glContext->functions()`）的情况；
  `fix.sh` 对「GL 出现在自包含语句之外且无法整块判定」的形态会**拒绝修改并提示人工处理**，不猜。
* 若源码中 GL 使用分布在大量文件且逻辑交织，逐点门控可能不可维护；此时更应考虑让上游做
  `QT_CONFIG(opengl)` 全局门控，或把该库的可选 GL 功能做成构建开关。

## 8. 关联

* 同族问题：Qt 裁剪构建导致的可选模块缺失（`Qt6::Sensors` 未发布、`Qt6::SerialPort` 未编入等）——
  都可能表现为「include 正常、符号缺失」，处理策略类似（补丁门控 / 桩 / env_unsupported）。
* 知识库方法论：`knowledge/tools/kb-atboot`（同类四件套形态参照）。
