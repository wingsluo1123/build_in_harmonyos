# unfurl test_package 说明

本 test_package 针对 unfurl 0.4.3 Go CLI 工具做实质校验：

1. **产物校验（无条件执行）**：检查包内 `bin/unfurl` 存在且具可执行位。
   这一步刻意放在 `can_run()` 守卫**之外** —— 它只是文件系统检查，与能否
   执行目标架构二进制无关；若被守卫包住，交叉编译场景下 `test()` 会退化为
   空壳测试。
2. **功能校验（`test.sh`）**：以上游 `README.mkd` 的官方示例 `urls.txt` 为输入，
   逐条断言六种模式的实际输出：

   | 模式 | 预期输出（排序后） |
   |------|--------------------|
   | `domains` | `example.net, sub.example.com, sub.example.com` |
   | `--unique domains` | `example.net, sub.example.com` |
   | `-u apexes` | `example.com, example.net` |
   | `paths` | `/about, /orgs, /users` |
   | `keys` | `id, name, org` |
   | `values` | `123, ExCo, Sam` |

3. **无编译步骤**（`build()` 为空）—— unfurl 为 Go 工具，CI 通过
   `conan create` 自动调用本 test_package 完成 L1 级校验。

## 为什么必须断言输出

上游 `main.go` 在 mode 无法识别时，仅向 stderr 打印 `unknown mode` 后直接
`return`，**进程退出码依然是 0**。因此只执行命令、依赖退出码判定的写法是恒真的，
属于假阳性测试。`test.sh` 对每种模式比对 stdout 实际内容，才能真正验证 URL
解析能力。

`keys` / `values` 的输出源自 Go map（`u.Query()`），迭代顺序不确定，因此
`test.sh` 统一按字节序排序后再比对。

说明：unfurl 无 C/C++ 库产物，测试只校验可执行文件与其运行时行为。
上游单测 `TestFormat`（32 条用例）不在此处，而是由主配方 `build()` 中的
`go test ./...` 执行。
