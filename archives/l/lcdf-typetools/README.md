# lcdf-typetools

LCDF Typetools 是一组用于操作 PostScript Type 1 和 OpenType 字体的工具程序。

## 版本

- 当前编译版本：2.110
- 上游源码：https://www.lcdf.org/type/lcdf-typetools-2.110.tar.gz
- 源码 SHA256：517f9ee879208679d3224a14d5e6eb20598fc648d5c3562708083d003088a934

## 编译平台

- 目标架构：OpenHarmony aarch64
- 编译器：clang/clang++
- 构建系统：autotools
- configure 选项：`--prefix=$DEFAULT_PREFIX --without-kpathsea`
- 许可证：GPL-2.0-or-later

## 包含的工具

| 工具 | 功能描述 |
|------|----------|
| **cfftot1** | 将 PostScript CFF (Compact Font Format) 字体转换为 Type 1 格式 |
| **mmafm** | 从 AMFM 文件创建多主 Type 1 字体的 AFM 实例 |
| **mmpfb** | 从 AMFM 文件创建多主 Type 1 字体的 PFB 实例 |
| **otfinfo** | 打印 OpenType 字体的信息 |
| **otftotfm** | 从 OpenType 字体生成 TeX 字体度量文件和编码文件 |
| **t1dotlessj** | 创建带无点 j 的 Type 1 字体 |
| **t1lint** | 检查 Type 1 字体的错误 |
| **t1rawafm** | 从原始 Type 1 字体生成 AFM 字体度量文件 |
| **t1reencode** | 重编码 Type 1 字体 |
| **t1testpage** | 为 Type 1 字体创建测试页 |
| **ttftotype42** | 将 TrueType 字体转换为 Type 42 格式 |

## 编译说明

- kpathsea 依赖已通过 `--without-kpathsea` 禁用（可选 TeX 功能，不影响核心工具）
- 需要应用 1 个补丁（0001-configure.patch）：移除 configure 中的 `umask 077`，修复 HMDFS 平台兼容性

## 主页

https://www.lcdf.org/type/
