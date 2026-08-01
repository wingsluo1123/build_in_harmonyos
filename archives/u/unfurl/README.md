# unfurl - HarmonyOS 适配记录

## 概述

unfurl 是 TomNomNom 编写的 Go 命令行工具，从 stdin 读取 URL 并提取其组成部分
（scheme、domain、apex、path、query keys/values 等），并提供 printf 风格的
自定义格式化输出。它是独立可执行程序，不产出可链接库。

- 上游: https://github.com/tomnomnom/unfurl
- 许可证: MIT
- 类型: 命令行工具（`package_type = "application"`，见 `commands.json`）

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.4.3 | built | 2026-07-31 |

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC aarch64 |
| 构建系统 | custom（Go 工具链） |
| Go | 1.26.3（`~/usr/local/go1263`；1.26.0 二进制在 HarmonyOS 上损坏） |
| 目标 | `GOOS=linux GOARCH=arm64 CGO_ENABLED=0`（静态 ELF） |

## 适配要点

1. **不存在 `GOOS=ohos`**：标准 Go 工具链没有 ohos 目标。HarmonyOS 基于 Linux
   内核，仓库内 15+ 个 Go 包统一走 `GOOS=linux GOARCH=arm64` + `CGO_ENABLED=0`
   静态链接这条已验证路径。
2. **必须 chdir 到源码目录**：配方使用 `basic_layout` 且 `no_copy_source = True`，
   `build()` 的 CWD 默认是 `build_folder`，而 `go.mod` / `*.go` 位于
   `source_folder`，不切目录会报 `no Go files in ...`。
3. **Go 环境变量注入方式**：`self.run(env=...)` 的 `env` 形参接收的是环境脚本名，
   传 `dict` 会抛 TypeError；应使用 `conan.tools.env.Environment` 注入。
4. **依赖拉取**：`GOPROXY=https://goproxy.cn,direct` 规避 proxy.golang.org 不可达。
5. **上游单测**：`format_test.go` 的 `TestFormat`（32 条用例）已接入 `build()`，
   由 `go test ./...` 在 CI 中真实执行。

## 测试

- L1（上游）：`go test ./...` → `TestFormat` 32 条用例。
- L1（消费者）：`test_package/test.sh` 以上游 README 官方示例为输入，逐条断言
  `domains` / `--unique` 去重 / `apexes` / `paths` / `keys` / `values` 的实际输出。
