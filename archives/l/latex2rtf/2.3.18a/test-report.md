# latex2rtf 2.3.18a 测试报告

## 测试环境
- 构建系统: makefile（纯 Makefile 项目，无 configure 脚本）
- 编译日期: 2026-07-16
- 编译器: clang 15.0.4
- 目标平台: OpenHarmony aarch64 (musl libc)

## 编译测试

```bash
# 编译
make CC=clang PREFIX=$DEFAULT_PREFIX -j1
# 结果: 成功 (1 warning: convert.c:57 pointer-compare, 非阻塞)

# 安装到 staging
make install CC=clang PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
# 结果: 成功

# 本地安装
make install CC=clang PREFIX=$DEFAULT_PREFIX
# 结果: 成功
```

## 功能测试

### 二进制类型
```
$ file ~/usr/local/bin/latex2rtf
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

### 动态依赖
```
$ llvm-readelf -d ~/usr/local/bin/latex2rtf | grep NEEDED
NEEDED: libc.so
```
仅依赖系统 musl libc，无外部库依赖。

### 文档转换测试
```bash
# 创建测试文档
$ cat > $TMPDIR/test-simple.tex << 'EOF'
\documentclass{article}
\begin{document}
Hello World
\end{document}
EOF

# 转换
$ latex2rtf $TMPDIR/test-simple.tex
# Exit code: 0

# 验证输出
$ ls -la $TMPDIR/test-simple.rtf
-rw-rw---- 4505 bytes

# 验证 RTF 头部
$ head -1 $TMPDIR/test-simple.rtf
{\rtf1\ansi\uc1\deff0\deflang1024
```

### make check 测试
```bash
$ make check
# 基本转换测试通过 (align.tex, array.tex, box.tex 等)
# 部分测试失败 (dblspace.rtf) - 需要 latex 命令，系统未安装
# 失败原因: /bin/sh: latex: inaccessible or not found
# 这不是适配问题，而是缺少 LaTeX 编译器环境
```

## 结论
- 编译: PASS
- 功能验证: PASS (RTF 输出有效)
- 依赖检查: PASS (仅 libc.so)
- 二进制类型: PASS (ELF aarch64)
