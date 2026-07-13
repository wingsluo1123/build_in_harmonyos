# gofumpt

**gofumpt** 是一个增强版的 `gofmt`，提供更严格的 Go 代码格式化规则。由 Go 语言实现，静态编译。

## 特性

- 完全兼容 gofmt，可作为 gofmt 的直接替代
- 更严格的格式化规则（移除多余空行、统一声明格式等）
- 支持 `-d`（diff）、`-l`（列出需格式化的文件）、`-w`（原地写入）等标准 flag
- 零外部依赖（纯 Go 静态编译）

## 主页

https://github.com/mvdan/gofumpt

## 许可证

MIT
