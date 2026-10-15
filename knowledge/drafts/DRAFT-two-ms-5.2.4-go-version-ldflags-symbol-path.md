# DRAFT — Go 版本串注入：`-X` 的符号路径必须与 module path 完全一致

状态：草稿（OpenDesk 落稿，2026-10-13）；Exxx 编号由知识库主编定稿时分配。
案例库：two-ms 5.2.4（module `github.com/checkmarx/2ms/v5`）。

## 可复现症状

- 构建成功，但 `2ms --version` 输出 `2ms version 0.0.0`（源码默认值）。
- 无任何编译告警 —— `-X` 目标符号不存在时 go 静默忽略。

## 根因

`go build -ldflags "-X <importpath>.<Var>=<value>"` 只能改写**已存在**的字符串变量，
且 `<importpath>` 必须是完整正确的 import path。

two-ms 的 module path 是 `github.com/checkmarx/2ms/v5`（v5 主版本后缀），
而上游 `.github/workflows/release.yml` 写的是
`-X github.com/checkmarx/2ms/cmd.Version=$VERSION` —— **缺 `/v5`**，因此对该 v5 module
无效；版本串始终为 `cmd/main.go:16` 的默认值 `0.0.0`。

## 方案

1. 在 conanfile.py 中以 module path 拼接符号路径（读 `go.mod` 首行 `module` 得到）：
   ```bash
   go build -trimpath -ldflags "-s -w -X github.com/checkmarx/2ms/v5/cmd.Version=5.2.4" -o 2ms .
   ```
2. 交付前用 `--version` 断言真实版本串（test_package 中作为 C1 用例）。

## 验证（two-ms 5.2.4 实测）

```
$ 2ms --version
2ms version 5.2.4
```

## 关联

E250（自举 Go 工具链）。
