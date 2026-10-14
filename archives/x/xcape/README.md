# xcape

`xcape` 让你把一个修饰键当作另一个键使用：当它被**单独按下并释放**时产生映射键，
否则仍作为修饰键工作。默认行为是「单击左 Control → 生成 Escape」。

## 功能概述

- 单文件 C 实现（`xcape.c`），通过 XRecord 拦截设备按键事件；
- 用 XTEST 扩展（`XTestFakeKeyEvent`）合成映射后的按键；
- 用 XKB（`XkbKeycodeToKeysym`）解析键码到 keysym 的映射；
- 支持映射表达式 `ModKey=Key[|OtherKey][;NextExpression]`（见 `xcape.1`）；
- 支持 `-d` 前台调试、`-t <ms>` 按住超时、`-e <mapping>` 自定义映射。

## OHOS 适配

- **构建方式改造**：上游 `Makefile` 唯一的 X11 定位手段是 host
  `pkg-config --cflags/--libs xtst x11`。HarmonyOS 设备上没有宿主 X11 开发树，
  `xtst`/`x11` 的 `.pc` 也不存在，直接 `make` 会在
  `xcape.c:29:10: fatal error: 'X11/Xlib.h' file not found` 处停止。
  配方改为对 conan 制品仓中的 X11 包直接编译这同一个翻译单元
  （`clipnotify/1.0.2`、`xbanish/1.8` 先例），include/lib 路径全部取自依赖包的
  私有目录，不注入共享前缀（R49）。
- **源码零改动**：`xcape.c` 对打包的 X11 头文件直接编译通过，无需任何补丁。
- **ELF 签名**：产物为可执行文件，打包前用 `binary-sign-tool` 自签名（E549）。
- **已知限制**：运行时功能需要 X server 以及 XTEST / XRecord / XKB 扩展提供
  事件源与键码查询；HarmonyOS PC 上无 X server，因此无法在此断言「Ctrl 单击生成
  Escape」的行为。消费者测试只覆盖设备上可证的部分：ELF 形态、签名、动态链接、
  以及无 X 环境下的确定性错误路径。

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 编译期 | `libxtst/6.1.0`、`libx11/6.4.0`、`xorgproto/2025.1` |
| 传递 | `libxext/6.4.0`、`libxi/6.1.0`、`libxfixes/6.1.0`、`libxau/1.0.11`、`libxcb/1.16`、`libxdmcp/1.1.5`、`xtrans/1.6.0` |
| 运行期 | 上述 X11 动态库（由 Conan 依赖链提供）+ musl libc |

## 参考资料

- 上游源码：https://github.com/alols/xcape（截至 2026-10-14 已不可访问，见
  `archives/x/xcape/1.2/conandata.yml` 的核验证据；本次适配源码取自上游 1.2 的
  保真镜像，5 个源文件与正式发布版逐字节一致）
- 手册页：`xcape.1`
