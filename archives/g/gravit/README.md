# gravit

Gravit 是一个自由、视觉效果出色的**重力模拟器**（N 体引力仿真）：用户可以在其中不断尝试各种宇宙构型，
观察星系、尘埃云、碰撞等场景的演化。渲染基于 OpenGL 固定管线（`glBegin`/`glEnd`、点精灵、
`gluPerspective`），窗口与输入来自 SDL 1.2，初始条件由 Lua 脚本（`spawn/*.gravitspawn`）描述。

- 上游：https://github.com/gak/gravit
- 许可：GPL-2.0-or-later

## OHOS 适配

- **离屏 GL**：鸿蒙 PC 没有窗口系统（X11/Wayland/EGL），制品仓的 mesa 是 OSMesa-only
  （只有 `libOSMesa.so`，没有 `libGL`/`libEGL`）。因此 SDL 表面退化为软件表面，GL 上下文由 OSMesa
  离屏软件渲染器提供（`softpipe`），每帧渲染完拷贝到 SDL 表面取代 `SDL_GL_SwapBuffers()`。
  运行只需 `SDL_VIDEODRIVER=dummy`。
- **SDL 1.2**：由 `sdl12-compat` 提供（`sdl-image`/`sdl_ttf` 亦链接它），避免进程内同时存在两份
  SDL 实现。
- **可重定位数据**：包安装在任意前缀下，`//share/gravit`、`/etc/gravit` 这类编译期绝对路径并不存在，
  查找时增加"可执行文件所在前缀"与当前目录两条路径。
- **autotools 重建**：0.5.1 发行包只带 `configure.in`/`Makefile.am`，构建前需 regenerated。

## 构建

```bash
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
```

## 运行

```bash
export SDL_VIDEODRIVER=dummy      # 无窗口系统，使用 SDL 软件视频驱动
gravit                            # 交互式（离屏渲染，本机无显示输出）
gravit -n "timeradd shot 5 1 screenshot" "timeradd bye 8 1 quit"   # 无头渲染并截图
```

命令行上的 `COMMAND` 会在视频初始化**之前**执行，需要"运行中"执行的命令请用内置定时器
（`timeradd <名字> <间隔秒> <次数> <命令>`）调度；`screenshot` 结果写入
`$HOME/.gravit/screenshots/`。

## 依赖

`sdl12-compat`、`sdl-image`、`sdl_ttf`、`lua/5.2.4`、`libpng`、`glu`、`mesa`（OSMesa）。

## 参考

- 上游源码：https://github.com/gak/gravit
- 文档：http://gravit.slowchop.com/（上游站点，历史资料）
