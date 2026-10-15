# DRAFT — OHOS 上 go test 的嵌套 go build 产物需签名；PATH wrapper 与 toolexec 均不可靠

状态：草稿（OpenDesk 落稿，2026-10-13）；Exxx 编号由知识库主编定稿时分配。
案例库：two-ms 5.2.4（Checkmarx/2ms，纯 Go CLI；上游 `tests/e2e_test.go` 自行 `go build` 被测 CLI）。

## 可复现症状与稳定错误签名

- 嵌套产物未签名：
  `fork/exec /…/go-buildXXXX/b001/2ms: permission denied`
  （e2e 内部 `exec.Command("go","build","-o",<tmp>/2ms,…)` 构建出的 CLI 未被签名）
- 测试 ELF 未签名（E318 同族）：
  `go-test-exec.sh: …/cmd.test: Permission denied`（exit 126）
- `-toolexec` 即时签名后的次生症状：
  `…/probe.test: operation not permitted`（有 `.codesign` 却仍被拒）

触发条件：OHOS/HarmonyOS aarch64 上执行 `go test ./...`，且被测项目（或上游测试）
会自行构建并执行 ELF。

## 根因（机理链）

1. 鸿蒙 `execve` 要求 ELF 携带 `.codesign` 段（E128）；Go 链接产物默认无该段。
2. `go test` 运行测试二进制时，**会把 `$GOROOT/bin` 前置到测试进程的 PATH**
   （实测 `LookPath("go")` = `$GOROOT/bin/go`）。因此“在 PATH 上放 go wrapper”这一
   常见拦截手段对上游测试内部的 `exec.Command("go", …)` **无效**。
3. `go -toolexec=<signer>` 虽能拦截 link，但对 link **刚写出**的文件即时签名后，
   鸿蒙仍拒绝 execve（`operation not permitted`）；对**最终文件**重新
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign` 才有效。
4. ELF magic 判定若用 `head -c3` 只得 `\x7fEL`（magic 为 4 字节 `\x7fELF`），
   比较恒假 → 签名分支被静默跳过。

## 方案（两层签名）

1. `go test -exec=<sign-wrapper>`：execve 测试 ELF 前就地签名（E318 标准做法）。
   wrapper 内用 `od -An -tx1 -N4` 比较 `7f454c46` 判定 ELF。
2. 把自举 Go 工具链的 `bin/go` 换成 shell shim，真 go 改名 `bin/go.real`；
   shim 在 `"$REAL" "$@"` 成功且参数含 `-o <out>` 且输出为 ELF 时执行
   `objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1` → `chmod 755`。

因 `go test` 前置 `$GOROOT/bin`，测试进程解析到的 `go` 必然是 shim，从而覆盖
上游测试内部的嵌套 `go build`。

## 验证（two-ms 5.2.4 实测）

- 修复前：`go test ./...` 全部 17 个含测试的包 `Permission denied`。
- 修复后：23 个包、1139 个用例（356 顶层 + 783 子用例）全部执行，**失败 0**。

## 关联

E128（ELF 签名）、E166（HMDFS 限制 Go link）、E250（自举 Go 工具链）、E318（go test ELF 签名）。
