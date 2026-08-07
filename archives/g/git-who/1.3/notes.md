# git-who 1.3 适配笔记

## 编译环境
- 构建系统: go (go build)
- 编译日期: 2026-07-30（本地 CI 模拟复验 2026-08-07）
- 编译器: Go
- 状态: failed  # R9: CI 实际结果——go 工具链 cmd-pkgs 装载超时+系统 go 缺，conan-build-test 阶段 build() 失败。修复后待重跑 CI 验证。

## 本地 CI 模拟验证（2026-08-07）

### 已实证通过项
1. **go SDK ELF 签名修复（E128）**：本地实证 `binary-sign-tool sign` 成功写入 `.codesign` 段。
   根因：Go 官方 SDK 二进制为非标准 ELF（SHT_STRTAB 未 null-terminated，`file` 报 `bad shdr 12?`），
   `llvm-strip`/`llvm-objcopy` 直接拒绝（`SHT_STRTAB ... non-null terminated`），
   只有 GNU `strip` 能容忍并修复（rc=0 输出 stripped）→ conanfile.py 改为 **GNU strip 优先，llvm-strip 兜底**。
2. **go SDK 版本升级 1.21.13 → 1.23.0**：go.mod 声明 `go 1.23`，1.21.13 SDK 触发 go 自动下载
   toolchain（GOPROXY 超时失败）→ 直接升级 SDK 匹配 go.mod（sha256 取自 go.dev 官方），实证 `go version` 通过。
3. **GOTMPDIR 指向 build_folder**：go link 需要可写临时目录（本地 `/tmp` 只读）。
4. **go vet ./... 通过**：上游静态检查（编译阶段，不依赖 link）全部通过。

### 本地无法运行项及详细原因
- **`go build`/`go test` 的 link 阶段在本地沙箱被拒**：
  `go tool link` 报 `mapping output file failed: permission denied`。
  根因：本地 OHOS 沙箱（hmfs/tmpfs + hmmac seccomp）对 `fallocate()` 系统调用统一返回
  `EACCES`（errno 13，C 程序实证所有可写路径均被拒，mmap 本身正常），
  而 go link 的 `outbuf_mmap.go` 只容忍 `ENOTSUP`/`EOPNOTSUPP`/`EPERM`（go1.26 才加 EOPNOTSUPP，仍未容忍 EACCES）。
  属**本地模拟环境限制**，非配方缺陷：git-town 16.4.1 同方案（下载 go SDK + go build）在真 CI 上 status: built，
  证明真 CI 环境无此 fallocate 拦截。
- **上游 `go test ./...`**（internal/cache、internal/git 等 10 个测试文件）需 link 测试二进制，同样被上述沙箱限制挡住。

## 编译步骤

```bash
go build -o git-who .
```

## 遇到的问题与解决方案

### CI 编译失败（status: failed）

CI worker 无 go 工具链支持，`go version` 检测失败：
- `cmd-pkgs Download failed`（CI 网络受限，下载 go 预编译包超时）
- `system go not found`（CI worker 不预装 go）

**根因**：非配方缺陷，CI worker 环境限制（E154: go 不预装，go/1.21.13 制品仓无 conanfile 配方不能 requires）。

**当前状态**：如实标记 `status: failed`，与版本级 manifest、顶层 manifest 对齐。后续 CI worker 升级支持 go 工具链后可重试。

## 依赖版本

运行时依赖: git

## 验证结果

```bash
./git-who --version
```
