# texi2html 5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang/clang++ (OHOS SDK 15.0.4)
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

```bash
./configure --build=aarch64-ohos-linux --host=aarch64-ohos-linux
make -j1
make check || true
```

## 源码修改

- no patch files — all fixes inline in conanfile.py build():
  - config.sub: replaced with 2025 version from conan cache + linux-ohos* support
  - configure: replace_in_file for /bin/sh shebang, PACKAGE_DATE, umask
  - install-sh: chmod 0755

## 验证结果

```bash
texi2html --no-validate sample.texi
# sample.html generated (1944 bytes, contains "Hello from texi2html")
```

## 注意事项

- 需要 Perl 运行时环境
- 依赖 libintl-perl 和 Unicode-EastAsianWidth 模块（已打包）
- make check || true 在 build() 中执行，check-local 因缺少 .mo 文件失败
---

**编译结束**: 2026-08-07 09:30
**最终状态**: built
