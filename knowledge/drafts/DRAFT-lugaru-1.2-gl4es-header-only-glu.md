# OHOS/gl4es 的 GLU 只有头没有符号：`gluPerspective` 未定义，必须补 glu/9.0.3 并显式接进链接行

- **ID**: `DRAFT-lugaru-1.2-gl4es-header-only-glu`
- **触发工具/阶段**: cmake / clang / ld — configure（假绿）+ linking（真炸）
- **严重度**: 2（🟡 中等；头文件在、库在，唯独符号不在，排障成本高）
- **类别**: platform, compat, ohos, opengl, linking
- **来源**: lugaru 1.2 适配（`gitlab.com/osslugaru/lugaru` tag 1.2，OHOS PC aarch64，2026-10-18）

## 错误特征

```
# configure 期一切正常（假绿）：
-- Found OpenGL: <CONAN_HOME>/p/gl4es82aba3af04fd6/p/lib/libGL.so

# 链接期才出现（本轮 gluPerspective 来自 Source/GameInitDispose.cpp:163）：
undefined reference to `gluPerspective'
```

```
# 判据：gl4es 的头在、实现不在
$ llvm-nm -D --defined-only <gl4es>/lib/libGL.so.1 | grep -ci 'glu'
45                       # 全部是 glUniform*，不是 GLU
$ llvm-nm -D --defined-only <gl4es>/lib/libGL.so.1 | grep -c 'gluPerspective'
0
$ ls <gl4es>/include/GL/
gl.h  glext.h  glu.h  glx.h  ...        # ← glu.h 确实在，所以「头能编」
```

## 场景

任何**固定管线 / 桌面 GL + GLU** 的工程在 OHOS 上适配：上游 `#include <GL/glu.h>`
并使用 `gluPerspective` / `gluLookAt` / `gluErrorString` / `gluProject` 等。
本包是 2017 年代的 3D 游戏（lugaru 1.2），`Source/Graphic/gamegl.hpp` 直接
`#include <GL/gl.h> <GL/glext.h> <GL/glu.h>`，全工程只用到一个 GLU 调用
（`GameInitDispose.cpp:163` 的 `gluPerspective`）。

## 根因（两层）

1. **gl4es 打包了 GLU 的头、却没有 GLU 的实现**：`gl4es/1.1.6` 的 `package()`
   把上游 `include/` 整目录拷进包（含 `GL/glu.h`），而它构建出的 `libGL.so.1`
   里 `glu*` 命中全是 `glUniform*`。⇒ 编译期无恙，链接期必炸。
2. **CMake 自带 `FindOpenGL` 不会顺手找 GLU**：只有
   `find_package(OpenGL REQUIRED GLU)`（显式组件）才会去 `find_library(OPENGL_glu_LIBRARY ...)`；
   不请求 GLU 时 `OPENGL_LIBRARIES` 只含 GL 一项。上游写的是
   `find_package(OpenGL REQUIRED)` + `${OPENGL_LIBRARIES}`，因此**即使制品仓里
   有 libGLU 也不会被链上**——症状看起来像「缺 GLU 包」，其实是缺链接项。

## 推荐方案（本包实测形态）

```python
# conanfile.py
self.requires("glu/9.0.3")                       # ohpcd 有 recipe + 本 profile 预编译
...
f"-DOPENGL_glu_LIBRARY={glu_lib}",               # 播种 FindOpenGL 的 GLU 变量
```

```diff
# patches/0001-cmake-ohos-compat.patch —— 把它真的接进链接行
-set(LUGARU_LIBS ... ${OPENGL_LIBRARIES} ${VORBISFILE_LIBRARY} ...)
+set(LUGARU_LIBS ... ${OPENGL_LIBRARIES} ${OPENGL_glu_LIBRARY} ${VORBISFILE_LIBRARY} ...)
```

等价写法：`find_package(OpenGL REQUIRED GLU)`（组件式请求）、或
`target_link_libraries(<target> ${OPENGL_glu_LIBRARY})`。运行期还需
`libGLU.so.1` 在 loader 路径（Conan 的 `cpp_info.libdirs` / VirtualRunEnv 已覆盖）。

验证（可复制）：

```bash
GL=$(find $CONAN_HOME/p -path '*gl4es*/p/lib/libGL.so.1' | head -1)
llvm-nm -D --defined-only "$GL" | grep -c gluPerspective          # → 0（gl4es 不管 GLU）
GLU=$(find $CONAN_HOME/p -path '*glu*/p/lib/libGLU.so' | head -1)
llvm-nm -D --defined-only "$GLU" | grep -E 'gluPerspective'       # → T gluPerspective
readelf -d <pkg>/bin/lugaru | grep NEEDED                         # → libGL.so.1 与 libGLU.so.1 都在
```

## 兜底与边界

- 只用到 1–2 个 GLU 函数时，可改为配方内自造等价实现（`gluPerspective` ≈
  `f = 1/tan(fovy/2); glFrustum(-f*aspect, f*aspect, -f, f, zNear, zFar)`），
  但这属于"自造依赖"，只在制品仓确实没有 glu 时使用。
- **正交条目**：本条是**符号缺失（链接期）**；`E1622` 是 gl4es 头文件
  `GL_GLEXT_PROTOTYPES` 条件裁剪导致的**原型缺失（编译期）**。两者可同时命中
  一个包——lugaru 没有命中 E1622，因为它在 `gamegl.hpp:380` 自己先
  `#define GL_GLEXT_PROTOTYPES 1` 再 include `<GL/gl.h>`。
- **正交条目**：`E1493`（OHOS 桌面 GL over GLES 兼容层的整体路线，即"该用 gl4es"）
  与本条互补——本条假设已经选了 gl4es，处理它的 GLU 缺口；`E693`
  （relax-required-opengl-lookup / desktop GL 名与 EGL procaddr 兜底）是
  "找不到 GL"的另一侧。
- 反例边界：纯 GLES2/3 工程**不要**引入 glu（GLES 没有 GLU，引了也只是死链）。
