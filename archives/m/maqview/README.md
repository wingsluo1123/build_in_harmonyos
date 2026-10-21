# maqview

MAQ 比对结果可视化查看器（MAQ alignment viewer），C++/OpenGL/GLUT。

- 上游：<https://maq.sourceforge.net/maqview.shtml>（SourceForge）
- 许可证：GPL-2.0-only
- 构建系统：autotools（tarball 只带 `configure.ac`，需 `autoreconf -fi`）

## 产物

`bin/` 下四个可执行文件（`Makefile.am` 的 `bin_PROGRAMS`）：

| 程序 | 说明 |
|---|---|
| `maqview` | OpenGL/GLUT 图形查看器（链接 GL/GLUT） |
| `maqindex` | 为 `.map` 建索引 / 导出 mapview 文本 / dump `.map` |
| `zrio` | 随机访问 gzip 流（`make` 建索引，`use` 读取） |
| `maqindex_socks` | 基于 socket 的前端（链接 GL/GLUT） |

## OHOS 适配要点

- **桌面 GL**：OHOS 只交付 OpenGL ES，不导出立即模式/选择模式入口。maqview 渲染层
  依赖这些入口，故链接 `mesa/24.3.4.1`（桌面 GL 入口在 `libOSMesa.so`+`libglapi.so`；
  该版本包无独立 `libGL.so`），`glu/9.0.3`（`gluPickMatrix`），
  `freeglut/3.6.0`（OHOS 制品 `libfreeglut-gles.so`）。
- **无 X display**：构建只编译+链接；验证走 OSMesa 离屏渲染 + 直接执行打包二进制。
- **签名**：OHOS 下每个打包 ELF 自签并断言恰 1 个 `.codesign` 段。

详细过程与证据见 `0.2.5/notes.md`。
