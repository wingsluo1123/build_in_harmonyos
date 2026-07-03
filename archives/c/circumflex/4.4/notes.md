# circumflex 4.4 适配笔记

## 编译环境
- **构建系统**: Go (纯 Go 项目)
- **编译日期**: 2026-07-03
- **Go 版本**: go1.26.4 linux/arm64
- **平台**: OpenHarmony (鸿蒙) aarch64
- **状态**: built

## 编译步骤

1. **下载源码**
   ```bash
   curl -L -o circumflex-4.4.tar.gz https://github.com/bensadeh/circumflex/archive/refs/tags/4.4.tar.gz
   tar xzf circumflex-4.4.tar.gz
   cd circumflex-4.4
   ```

2. **设置 Go 编译环境**
   ```bash
   export CGO_ENABLED=0
   export GOOS=linux
   export GOARCH=arm64
   export GOPROXY=https://goproxy.cn,direct
   export TMPDIR=/storage/Users/currentUser/tmp
   ```

3. **编译**
   ```bash
   go build -ldflags="-s -w" -o clx ./cmd/clx
   ```

4. **验证**
   ```bash
   ./clx version  # 输出: clx version 4.4
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 (404) | GitHub tag 是 `4.4` 而非 `v4.4` | 手动下载 `https://github.com/bensadeh/circumflex/archive/refs/tags/4.4.tar.gz` |
| 2 | Go 依赖下载慢 | 默认 GOPROXY 访问 GitHub 较慢 | 设置 `GOPROXY=https://goproxy.cn,direct` |

## 编译特点

- **纯 Go 项目**: 无 CGO 依赖，无需交叉编译工具链
- **静态编译**: `CGO_ENABLED=0` 生成完全静态的二进制
- **体积优化**: `-ldflags="-s -w"` 去除符号表和调试信息
- **最终体积**: 19.6MB (arm64 静态二进制)

## 依赖版本

无外部依赖（Go 标准库 + 第三方库均通过 go.mod 管理）

## 验证结果

```bash
$ file clx
clx: ELF executable, 64-bit LSB arm64, static, BuildID=12ddf793512c77555e698ca731f72f76c66fd240, stripped

$ ./clx version
clx version 4.4
```

## 注意事项

1. **TMPDIR 设置**: 鸿蒙 `/tmp` 只读 (E002)，必须设置 `TMPDIR` 到可写目录
2. **GOPROXY**: 建议使用 `goproxy.cn` 加速依赖下载
3. **ELF 签名**: CI 流水线会自动签名，本地编译的二进制可能无法直接执行
4. **Conan 配方**: Go 项目使用 `GoBuild` 工具，不需要传统的 configure/make 流程
