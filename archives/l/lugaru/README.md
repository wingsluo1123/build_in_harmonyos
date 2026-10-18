# lugaru

> 3D 动作游戏（低多边形狼兔格斗 + ragdoll 物理），1.2（GPL-2.0-or-later，游戏资产 CC-BY-SA）。

## 简介

Lugaru 由 Wolfire Games 开发，2010 年以 GPL 开源；本归档跟踪社区续作
**osslugaru**（`https://gitlab.com/osslugaru/lugaru`）的稳定 tag **1.2**
（2017-02-11，commit `c7b99378439735c60f84869b05c6ebde53083667`）。上游为 CMake
工程，窗口/输入走 SDL2，渲染走**固定管线 OpenGL 1.x**（`glBegin/glEnd/glMatrixMode/
glVertex3f/glOrtho…`，见 `Source/Graphic/gamegl.hpp`），音频走 OpenAL + Ogg/Vorbis，
贴图/存档走 libpng、libjpeg。

> **与 `WolfireGames/lugaru` 的关系**：`osslugaru` 是同一开源代码库在 GitLab 上的
> 社区主仓（Debian 的 `lugaru` 源码包 watch 也指向它）。GitHub 上 `WolfireGames/lugaru`
> 没有 `1.2` tag，直链 404（实测）；本任务上游以 `git ls-remote --tags
> https://gitlab.com/osslugaru/lugaru.git` 的 `refs/tags/1.2` 为准。

## OHOS 适配要点

- **GL 栈选型**：OHOS 无桌面 GL/GLX，`opengl/4.6` 不在 ohpcd 远端；而本包是纯固定管线
  渲染器（GLESv2 无这些入口）+ 一处 GLU（`gluPerspective`）⇒ 走 **gl4es/1.1.6**
  （`libGL.so`，GL 1.x over GLES；同 `critter/2.0.4`、`logstalgia/1.1.4`）+
  **glu/9.0.3**。`FindOpenGL` 通过播种 `OPENGL_gl_LIBRARY`/`OPENGL_INCLUDE_DIR` 钉在
  gl4es 上，`OPENGL_glu_LIBRARY` 由 patch 0001 显式接进链接行。
- **上游两处 CMake 兼容问题**（patch 0001）：`cmake_minimum_required(VERSION 3.0)`
  被 CMake 4.x 拒绝；`set(CMAKE_CXX_FLAGS "… --std=gnu++11 ${CMAKE_CXX_FLAGS}")` 的
  前置拼接会被 profile 的 `-std=gnu++17` 覆盖，而 `Source/Math/XYZ.hpp` 用了 C++17
  已删除的 `register`（clang 硬错）。
- **遗留变量播种**：上游消费 `Find*` 模块的 `${OPENAL_LIBRARY}`/`${PNG_LIBRARY}`/
  `${JPEG_LIBRARY}`/`${ZLIB_LIBRARIES}`/`${SDL2_LIBRARIES}`/`${OPENGL_LIBRARIES}`/
  `${OGG_LIBRARY}`/`${VORBIS*_LIBRARY}`，而 CMakeDeps 只产出现代 IMPORTED target。
- **SDL2** 由 `pkg_check_modules(SDL2 sdl2 REQUIRED)` 定位 ⇒ PkgConfigDeps 输出进
  `PKG_CONFIG_PATH`，`pkgconf` 走 `tool_requires`。
- **资源与可执行文件同目录**：`DATA_DIR "Data"` 相对工作目录解析 ⇒ `bin/lugaru` 与
  `bin/Data/`（542 个资源文件）同放 `bin/`；上游 `SYSTEM_INSTALL=OFF` 的 install 规则
  把可执行文件落到 prefix 根，故 `package()` 手工摆布局。
- **运行时**：gl4es 以 `dlopen` 加载 EGL/GLES 后端 ⇒ `package_info()` 导出
  `LIBGL_GLES=/system/lib64/libGLESv3.so`、`LIBGL_EGL=/system/lib64/libEGL.so`。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/lugaru` | 游戏主程序（AArch64 PIE，`PT_INTERP=/lib/ld-musl-aarch64.so.1`） |
| `bin/Data/` | 游戏资源（Animations/Campaigns/Dialogues/Maps/Models/Skeleton/Sounds/Textures） |
| `share/man/man6/lugaru.6` | 用户手册 |
| `licenses/` | `COPYING.txt`（GPL-2.0）、`CONTENT-LICENSE.txt`（CC-BY-SA）、`AUTHORS` |

## 测试

上游无自动化测试（`N_static=0`：无 `enable_testing()/add_test()`、全仓无 `*test*`
文件、`.gitlab-ci.yml` 只有构建 stage）。适配后由 `test_package` 补消费者测试
**6 用例 / 24 项断言**并真实执行（`--version`/`--help`/未知选项三条 CLI 路径 + ELF/
布局/runenv 静态校验）；真实渲染与输入需带显示的设备，属未覆盖面，已在
`test_package/MANIFEST.yml` 逐条申报。
