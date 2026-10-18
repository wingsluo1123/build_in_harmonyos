# DRAFT-blur-effect-1.1.3-gbm-drm-offscreen-to-egl-pbuffer — GBM+DRM 离屏路径迁到 EGL pbuffer

> Status: **Draft**（待主编 promote） | severity: `2` | category: `platform, ohos, graphics, egl, cmake, portability` | Updated: 2026-10-18
> 源文件：`knowledge/drafts/DRAFT-blur-effect-1.1.3-gbm-drm-offscreen-to-egl-pbuffer.kv`
> 来源：blur-effect 1.1.3 适配（`feat/blur-effect-1.1.3`，PR #16672）

---

> ## ⚠ 重复源披露（必读）
>
> 同一上游、同一份源码（sha256 `80baead168e117cdbd7dd915dac94b8055e63dc05ec5797f3030acfaf19e5654`）
> 已由**已合入的姊妹配方** `archives/b/blur/1.1.3` 覆盖，该配方已发布到制品仓
> （revision `9addfb36f648f708107c9e8f716765a6`）。本包 `blur-effect/1.1.3` 是
> **同一份源码的第二个归档实例**，补丁 0001/0002 与消费者测试与姊妹配方同源。
>
> 但该机制**从未进过 `knowledge/graph`**：本条目是它的**图谱首次收录**，
> 并且是首次把「离屏路径从 GBM+DRM 迁到 EGL pbuffer」写成可复用处方
> （含 pkg-config 必需项手术、pbuffer 尺寸与图像尺寸一致、GLES 严格性两处）。
> ⇒ **请勿仅凭"源码重复"判本条重复**；重复的是归档实例，不是知识条目。

**关键词**：gbm, gbm_create_device, gbm_surface_create, libgbm, libdrm, /dev/dri, card0, eglGetDisplay, EGL_DEFAULT_DISPLAY, EGL_PBUFFER_BIT, eglCreatePbufferSurface, 离屏渲染, pkg_check_modules 必需项, GLES3 严格性

## 现象（error_signature）

构建期：

```text
fatal error: 'gbm.h' file not found
Package 'gbm' was not found in the pkg-config search path
Package 'libdrm' was not found in the pkg-config search path
```

或链接期 `undefined reference to 'gbm_create_device'` / `'gbm_surface_create'`。

而**即使把构建期凑过去**，运行期还是：

```text
no card found
cannot create gbm surface
```

## 根因

入口不是"链路里少了一个包"，而是**上游把离屏渲染绑死在 Linux 的 GBM + DRM 上**。
典型的 Linux 离屏 GL 写法分三步：

1. 探测并打开 DRM 渲染节点：扫 `/sys/class/drm/card*`、`open("/dev/dri/cardN")`；
2. `gbm_create_device(fd)` 建 GBM 设备；
3. `gbm_surface_create(gbm, w, h, GBM_FORMAT_XRGB8888, GBM_BO_USE_SCANOUT|GBM_BO_USE_RENDERING)`
   建缓冲，再 `eglGetDisplay(gbm)` + `eglCreateWindowSurface(..., gbm_surface, ...)`
   把这个 GBM 表面当作 EGL 的原生窗口。

构建侧对应地把 libdrm/gbm/egl/glesv2 全列为 `pkg_check_modules(... REQUIRED ...)`。

到了 OHOS：

- **没有 `/dev/dri` 渲染节点**（`/sys/class/drm/card*` 也不存在）⇒ 步骤 1 走不下去，
  运行期表现为 `no card found`；
- **没有 libgbm** ⇒ 构建期 `gbm.h: No such file or directory`、pkg-config 报
  `Package 'gbm' was not found`；步骤 2、3 无解；
- 系统 EGL/GLESv3 **不提供 `.pc` 描述文件**（是平台库，不是 pkg-config 模块）
  ⇒ 即便 `.pc` 齐备也拿不到模块名，"照抄 Linux 的依赖清单"这条路本身就不通。

### 三个不显然的判断

1. **不要坚持原生 GBM/DRM 路线。** OHOS 无渲染节点，即使凑齐 `gbm.pc`/`libdrm.pc`，
   运行时也必挂；把预算花在"补齐 `.pc`"上是结构性沉没成本。
   实测该路线不可行：`conan install --requires=mesa/24.3.4.1.1.1 --build=never` 首错
   `ERROR: Missing prebuilt package for 'libxrender/0.9.12'` ⇒ 缓存内检不到
   `gbm.pc`/`glesv2.pc`/`egl.pc`/`libdrm.pc`。
2. **EGL 默认显示在普通原生进程里可用**（`EGL_DEFAULT_DISPLAY` 可初始化），
   但要 **pbuffer** 表面（不是 window surface），配置必须选
   `EGL_SURFACE_TYPE = EGL_PBUFFER_BIT`。
3. **pbuffer 尺寸必须是图像尺寸。** 最终回读（`glReadPixels`）在全图尺寸的默认
   帧缓冲上做，pbuffer 写死一个小尺寸会越界读 —— 小图恰好过、大图才炸。

### 同批的 GLES 严格性摩擦（与 GBM 无关，换 pbuffer 后立刻暴露）

- `#version 300 es` **必须是着色器源码第一行**，前面不能有换行；
- GLSL ES 3.00 已移除 `texture2D`，须用 `texture`。

## 处方（rec_approach）

`replace-gbm-drm-offscreen-path-with-egl-default-display-pbuffer`

### 构建侧

```cmake
- pkg_check_modules(DEPS2 REQUIRED gdk-pixbuf-2.0 libdrm gbm egl glesv2)
+ pkg_check_modules(DEPS2 REQUIRED gdk-pixbuf-2.0)   # 平台不提供其余四个 .pc
+ link_directories(${DEPS2_LIBRARY_DIRS})            # 其余模块的 -L 要进链接搜索路径
- target_link_libraries(blur_image ${DEPS2_LIBRARIES})
+ target_link_libraries(blur_image ${DEPS2_LIBRARIES} EGL GLESv3)   # 直链平台库
```

### 源码侧

删掉 DRM 设备探测（`/sys/class/drm/card*` 扫描、`open("/dev/dri/cardN")`、
`choose_best_card`）与 GBM 设备/表面字段，`setup_context()` 改为：

```c
ctx.display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
if (ctx.display == EGL_NO_DISPLAY) err_quit("eglGetDisplay failed\n");
eglInitialize(ctx.display, &major, &minor);
eglBindAPI(EGL_OPENGL_ES_API);
/* 配置属性里： EGL_SURFACE_TYPE, EGL_PBUFFER_BIT */
const EGLint pb_att[] = { EGL_WIDTH, ctx.width, EGL_HEIGHT, ctx.height, EGL_NONE };
ctx.surface = eglCreatePbufferSurface(ctx.display, conf, pb_att);   /* ← 按图像尺寸 */
eglMakeCurrent(ctx.display, ctx.surface, ctx.surface, ctx.gl_context);
```

随之失效的 CLI 选项（`-d drmdev`）一并移除，`usage()` 同步。

## 边界（applicability / counterexamples）

**适用**：上游把**离屏**渲染/计算绑死在 GBM+DRM 上的命令行工具或库（图像处理、
无窗口 GPU 计算、批处理渲染），且该程序**不需要窗口系统**。
判据 = 源码出现 `gbm_create_device` / `gbm_surface_create` / `/dev/dri/card`，
或构建系统把 libdrm/gbm 列为硬依赖。

**不适用 / 代价**：

- **窗口系统 + GL 上下文**型库/框架（freeglut、GLUT 系、GUI 工具包）→ 属 **E2090**
  的适用面（需新写平台后端 + 清点平台层契约函数）。本条只换离屏表面，
  不解决窗口/事件/光标语义。
- 需要 DRM 的 buffer 导出或显式设备选择 → 本条主动放弃该能力。
- 纯 GLES2 且用**直连导出符号**渲染 → 见 **E2089**（直连符号是调度空桩，
  真函数须经 `eglGetProcAddress`），本条不覆盖该失败面。

## 查重差异表

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| **E2090**（OHOS 无 X11/Wayland/Android-glue，但普通原生进程可用 EGL 离屏；窗口工具库可据此移植） | 都落到 `eglGetDisplay(EGL_DEFAULT_DISPLAY)` + pbuffer | E2090 讲的是**平台能力可行性**与**窗口型框架须新写平台后端**：入口是编译期 `X11/Xlib.h file not found`，判据是平台层契约函数清点（freeglut 契约 46 个 vs EGL 层 3 个），并**明确把「纯 shader/GLES2 且不自建窗口的应用」排除在自己的适用面之外**。本条讲的正是被它排除的那一侧：入口是 `gbm_create_device`/`gbm_surface_create`/`/dev/dri` 缺失，处方是「整条离屏路径换成 pbuffer + pkg-config 必需项手术」，不涉及窗口/事件/光标。**E2090 是"能不能用 EGL 离屏"的判据；本条是"已经用着 GBM 的离屏程序怎么迁"的处方 —— 互补而非重复** |
| **E2089**（`libGLESv2.so` 直连导出符号是调度空桩，真函数须经 `eglGetProcAddress`） | 都涉及 OHOS GLES | 本条被测程序用 GLES**3** 且经正常 EGL 上下文取函数；E2089 是「直连导出符号取到空桩」这一独立失败面 |
| E754（libepoxy 的 EGL 启用修订） | 都涉及 EGL | E754 是**分发库的构建选项**（`egl=no` → `egl=yes`）+ mesa 头注入，不涉及离屏表面替换 |
| E1493（gl4es 补桌面 OpenGL） | 都涉及 GL/EGL 适配 | E1493 是**固定管线兼容层**（桌面 GL over GLES），与离屏表面无关 |

`dedup_notes` 记录的图谱实测命中数：`gbm_create_device` = 0、`gbm_surface` = 0、
`libgbm` = 0、`/dev/dri` = 0（**GBM/DRM 离屏入口侧图谱完全无先例**）；
`eglGetDisplay` = 3、`PbufferSurface` = 3、`EGL_DEFAULT_DISPLAY` = 2、`pbuffer` = 4。

## 验证

消费者测试 **2 个用例 × 5 条断言 = 10 条断言全部通过**（真 PNG → 真渲染 → 输出校验）：

- 32×32 用例：输出 342 B PNG，合法、尺寸不变、内容确已模糊；
- 256×256 用例：输出 15855 B PNG，同上（该用例正是为抓"pbuffer 写死小尺寸导致
  大图回读越界"而加）。

原生 GBM/DRM 路线探针实测不可行（首错见"根因"节），故本包不保留该路线。

## 来源

- 上游任务：`archives/b/blur-effect/1.1.3`（PR #16672）；姊妹配方 `archives/b/blur/1.1.3`
- 落地位置：`patches/0001-CMakeLists.txt.patch`（pkg-config 必需项 + 直链 EGL/GLESv3）、
  `patches/0002-src-blur_image.cc.patch`（EGL pbuffer 替代 GBM/DRM + GLES 严格性）
- 关键首错原文：`gbm.h: No such file or directory`、
  `Package 'gbm' was not found in the pkg-config search path`、
  `ERROR: Missing prebuilt package for 'libxrender/0.9.12'`

---

*本条目为草稿。正式化请用 `ohc-run.py graph promote` 提升到 `knowledge/graph/`。*
