# alda 2.4.3 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-08-08
- 编译器: Go 1.26.5 (harmonybrew), CGO_ENABLED=0 静态编译
- 状态: built

## 编译步骤

1. 下载源码：从 GitHub release-2.4.3 tag 获取 tar.gz
2. 进入 client/ 目录（Go module）
3. 运行 `go generate ./...` 生成 `generated/version.go`（ClientVersion = "2.4.3"）
4. 运行 `CGO_ENABLED=0 GOPROXY=https://goproxy.cn,direct go build -ldflags="-s -w" -o alda .`
5. 产物：10.4MB 静态 ELF arm64 二进制，stripped
6. 安装到 staging：`cp alda $TEST_PREFIX/bin/alda`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `go: inaccessible or not found` | Conan 构建沙箱剥离 PATH，Go 工具链不可达 | 在 build() 中显式注入 `PATH=~/.harmonybrew/bin:$PATH` |
| 2 | `env argument to ConanFile.run() should be a list` | Conan 2.x 的 run() 不接受 dict 作为 env | 改为命令字符串内联环境变量（env_prefix） |
| 3 | test_package `self.deps_cpp_info` AttributeError | Conan 2.x API 变更 | 改用 `self.dependencies["alda"].package_folder` |

## 源码修改

无补丁，源码未修改。Go generate 生成的 `client/generated/version.go` 是构建时产物，非源码修改。

## 依赖版本

- Go 1.26.5 (harmonybrew, `~/.harmonybrew/bin/go`)
- 无 Conan C/C++ 依赖（纯 Go CLI）

## 验证结果

```bash
$ ALDA_TELEMETRY_DISABLED=1 alda version
alda 2.4.3

$ alda --help
alda: a text-based language for music composition
Usage:
  alda [command]
Available Commands:
  completion  doctor  export  help  import  instruments  parse  play  ps  repl  shutdown  stop  telemetry  update
```

conan-verify 全 8 道门禁通过（G0-G4 + L2/L4/L5）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/alda | 10,396,736 字节 | 静态 ELF arm64 二进制，stripped |

## 注意事项

1. **player 未构建**：alda-player 是 Java/Gradle 应用，需要 JVM，不在本次适配范围。client CLI 功能完整，但 play 命令需要 alda-player。
2. **telemetry 弹窗**：首次运行 alda 会弹遥测同意框，测试时用 `ALDA_TELEMETRY_DISABLED=1` 跳过。
3. **Go 工具链路径**：Conan 沙箱剥离 PATH，conanfile.py 中硬编码 `~/.harmonybrew/bin` 注入 Go 工具链。

---

**编译结束**: 2026-08-08
**最终状态**: built
