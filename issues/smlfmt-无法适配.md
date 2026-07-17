## 软件信息
- **软件名称**：smlfmt
- **版本**：v1.3.0
- **上游仓库**：https://github.com/shwestrick/smlfmt
- **来源**：🍎 Homebrew #3232 (260 installs/90d)
- **分类**：其他工具 / 长尾工具

## 无法适配原因

smlfmt 是一个 Standard ML 代码格式化工具，使用 Standard ML 编写，需要 **mlton**（Standard ML 编译器）才能从源码编译。

### 依赖链
- smlfmt → mlton (build-only) → 无替代
- smlfmt → gmp (runtime) → 已在 archives 中 ✅

### 阻塞点
1. **mlton 不可用**：OHOS 平台上没有 mlton 编译器，conancenter 也无 mlton 配方
2. **无预编译二进制**：Homebrew 提供 Linux ARM64 bottle，但基于 glibc，与 OHOS (musl libc) 不兼容
3. **无法交叉编译**：需要先适配 mlton 到 OHOS，但 mlton 本身也是用 Standard ML 编写的，形成鸡生蛋问题

## 建议
- 如果未来 mlton 被适配到 OHOS，可以重新尝试编译 smlfmt
- 或者在其他有 mlton 的环境中编译出静态链接的 smlfmt 二进制，再通过 cmd-pkgs 分发

## 参考
- Homebrew formula: https://github.com/Homebrew/homebrew-core/blob/master/Formula/s/smlfmt.rb
- Nix package: https://github.com/NixOS/nixpkgs/blob/release-26.05/pkgs/by-name/sm/smlfmt/package.nix