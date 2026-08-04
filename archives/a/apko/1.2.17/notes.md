# apko 1.2.17 适配笔记

## 编译环境
- 构建系统: custom (Go build)
- 编译日期: 2026-08-05
- 编译器: Go 1.26.0 (from golang.google.cn mirror, installed at /data/storage/...)
- Go工具链: GOTOOLCHAIN=local
- 状态: built

## 编译步骤

1. 设置编译环境变量:
   ```
   export GOROOT=<go-sdk-path>
   export GOPATH=<gopath-path>
   export GOCACHE=<gocache-path>
   export GOOS=linux GOARCH=arm64
   export CGO_ENABLED=0
   export GOTOOLCHAIN=local
   export GOPROXY=https://goproxy.cn,direct
   ```

2. 下载 Go 模块依赖:
   ```
   go mod download
   ```

3. 编译 release 版本:
   ```
   go build -buildmode=pie -trimpath -ldflags "-buildid= -X sigs.k8s.io/release-utils/version.gitVersion=1.2.17 -X sigs.k8s.io/release-utils/version.gitCommit=unknown -X sigs.k8s.io/release-utils/version.gitTreeState=clean -X sigs.k8s.io/release-utils/version.buildDate=2026-08-05" -o apko ./
   ```

4. 签名 (HarmonyOS ELF 签名):
   ```
   binary-sign-tool sign -selfSign 1 -inFile apko -outFile apko.signed -signAlg SHA256withECDSA
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | go.mod requires Go >= 1.26.0 | apko项目依赖新版Go | 从 golang.google.cn 下载 Go 1.26.0 SDK |
| 2 | Go toolchain binaries permission denied | HarmonyOS 需要ELF签名 | 使用 binary-sign-tool 签名所有 Go 工具链二进制 |
| 3 | Go module download timeout | proxy.golang.org 在国内不可达 | 使用 GOPROXY=https://goproxy.cn,direct |
| 4 | go build link mapping output failed | HMDFS 权限限制写入 | 使用 /data/storage 路径作为 GOCACHE/GOTMPDIR |
| 5 | HMDFS 无法执行 static ET_EXEC | Go 默认生成静态二进制 | 使用 -buildmode=pie 生成 PIE (ET_DYN) 二进制 |

## 依赖版本

- Go: 1.26.0 (linux/arm64)
- 目标: HarmonyOS NEXT (aarch64)
- CGO_ENABLED=0 (纯Go静态编译)
- 无 Conan 级别依赖: Go 通过 module proxy 自行解析依赖

## 验证结果

```bash
$ apko version
GitVersion:    1.2.17
GitCommit:     unknown
GitTreeState:  clean
BuildDate:      2026-08-05
GoVersion:     go1.26.0
Compiler:      gc
Platform:      linux/arm64
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| apko | 38MB | release版本 (PIE, arm64) |

## 注意事项

- apko是Chainguard的APK-based OCI image builder，纯Go项目
- CGO_ENABLED=0编译，不依赖musl libc
- -buildmode=pie 生成 ET_DYN 二进制，HMDFS 可执行
- 版本信息通过ldflags注入sigs.k8s.io/release-utils/version包
- 无Conan依赖声明，Go module依赖在build时从proxy下载
---

**编译结束**: 2026-08-05 02:05
**最终状态**: built
