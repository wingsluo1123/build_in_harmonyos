# m17n-lib

GNU M-text multilingualization library (core)

## 描述

m17n-lib 是 GNU 多语言文本处理库，提供 M-text 数据结构和相关 API，
用于处理包含多种语言和字符集的文本。

## 组件

- **libm17n-core**: 核心库，基础 M-text 操作
- **libm17n**: 主库，完整的 M-text API
- **libm17n-flt**: 过滤器库，文本转换功能
- **libm17n-gui**: GUI 库，图形界面支持（需要 X11）

## 工具程序

- **m17n-conv**: 字符编码转换工具
- **m17n-dump**: PNG 图像输出工具（需要 freetype + gd）
- **m17n-date**: 多语言日期格式化（需要 locale）
- **m17n-edit/view**: GUI 编辑器（需要 X11）

## OpenHarmony 适配

### 已适配版本
- 1.8.6 ✅

### 已知限制
- m17n-edit/view: X11 在 OHOS 上不可用
- m17n-date: musl libc 无 locale 命令

### 补丁
- 0001-configure-umask-fix.patch (E011)
- 0002-config-guess-harmonyos.patch (E007)

## 依赖

- libxml2 (必需)
- freetype2 (可选，用于 m17n-dump)
- gdlib (可选，用于 m17n-dump)

## 相关软件

- **m17n-db**: 语言数据包（独立安装）
- **m17n-contrib**: 社区贡献输入法（独立安装）

## 官方链接

- 源码: https://download.savannah.nongnu.org/releases/m17n/
- 文档: https://www.nongnu.org/m17n/