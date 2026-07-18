# chezscheme 10.4.1 适配笔记

## 编译环境
- 构建系统: custom (zuo - Chez Scheme 自带构建系统)
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 源码目录
cd /storage/Users/currentUser/tmp/builds/chezscheme-10.4.1.work

# 配置 (--pbarch 构建 portable bytecode 版本，避免平台特定汇编)
./configure --pbarch --disable-curses --disable-x11 --disable-iconv --as-is \
  --installprefix=/storage/Users/currentUser/usr/local \
  CC=clang CFLAGS="-fPIC -O2" LDFLAGS="-fPIC"

# 编译 (自举编译系统，需要 -j1)
make -j1

# 安装
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 硬链接失败 | HMDFS 文件系统不支持 `ln -f` 硬链接 | 修改 `makefiles/install.zuo`，将 `ln -f` 和 `ln -s` 替换为 `cp` |
| 2 | 无平台特定汇编 | OHOS 不是标准平台 | 使用 `--pbarch` 构建 portable bytecode 版本 |
| 3 | 机器类型不识别 | OHOS 不在已知平台列表 | `tpb64l` (threaded pb 64-bit LE on unknown OS) 自动选择 |

## 源码修改

- `makefiles/install.zuo`: 将 `ln -f` 和 `ln -s` 替换为 `cp`，解决 HMDFS 文件系统不支持硬链接/相对符号链接的问题

## 依赖版本

- 无外部依赖。Chez Scheme 自带所有子模块:
  - zlib (内嵌)
  - lz4 (内嵌)
  - zuo (内嵌构建系统)
  - nanopass (内嵌编译器框架)
  - stex (内嵌文档系统)

## 验证结果

```bash
# 版本输出
$ scheme --version
10.4.1

# 算术测试
$ scheme --script <(echo '(display (* (+ 1 2 3) (- 10 3)))(newline)')
42

# 列表操作
$ scheme --script <(echo '(display (length (quote (a b c d e))))(newline)')
5

# 字符串操作
$ scheme --script <(echo '(display (string-append "Hello, " "Scheme!"))(newline)')
Hello, Scheme!

# 递归 (factorial 10)
$ scheme --script <(echo '(define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1)))))(display (factorial 10))(newline)')
3628800

# 宏 (swap!)
$ scheme --script <(echo '(define-syntax swap! (syntax-rules () ((_ a b) (let ((tmp a)) (set! a b) (set! b tmp)))))(define x 1)(define y 2)(swap! x y)(display (list x y))(newline)')
(2 1)

# 文件 IO
$ scheme --script test_fileio.ss
hello from file

# compile-file
$ scheme --script <(echo '(compile-file "test_compile.ss")(display "done")(newline)')
compiling test_compile.ss with output to test_compile.so
done
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (自定义构建系统) |
| conandata.yml | 源码 + 补丁声明 |
| test_package/ | L1 测试 (运行 scheme 二进制) |
| patches/0001-makefiles-install.zuo.patch | HMDFS 硬链接修复补丁 |
| commands.json | 命令行工具声明 (R38) |

## 注意事项

- Chez Scheme 使用自举编译系统，需要多轮编译 + fixpoint 验证，构建时间约 6-7 分钟
- 必须使用 `make -j1`，并行编译会因自举依赖导致失败
- `--pbarch` 是关键选项，避免平台特定汇编代码
- 机器类型 `tpb64l` 表示 "threaded pb 64-bit LE on unknown OS"
---

**编译结束**: 2026-07-18 12:53
**最终状态**: built
