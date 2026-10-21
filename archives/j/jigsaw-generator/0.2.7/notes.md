# jigsaw-generator 0.2.7 适配笔记

## 上游来源（已验证）

- 仓库：https://github.com/juliangilbey/jigsaw-generator（作者 Julian Gilbey，Debian 维护者）
- 源码：tag `upstream/0.2.7` 的官方归档
  https://github.com/juliangilbey/jigsaw-generator/archive/refs/tags/upstream/0.2.7.tar.gz
- 验证（2026-10-13）：HTTP 200（302 → codeload.github.com），107819 字节，
  sha256 `f9c2644f719cef1ea89caebb86f17536192f90f7d7aeb4a4c61e987932b664f1`
- 佐证：Debian 以 `jigsaw-generator_0.2.7.orig.tar.gz` 发行同一 tag 内容
  （https://deb.debian.org/debian/pool/main/j/jigsaw-generator/jigsaw-generator_0.2.7.orig.tar.gz，
  亦 HTTP 200；两者仅 tarball 顶层目录名不同）
- 语言构成：纯 Python 3（jigsaw/generate.py 约 7.7 万字节 + 自带的 appdirs.py），
  外层是 autoconf 脚手架（configure/Makefile.in），**无任何 C/C++ 编译**
- 许可证：主体 GPL-3.0-or-later（appdirs.py 独立许可证、goose.png 公有领域，见 COPYING）

## 构建方式

上游 `Makefile.in` 的 build 目标只有一条 sed 替换：

```
sed -e 's|@pkgdatadir[@]|$(pkgdatadir)|; s|@PACKAGE_VERSION[@]|$(PACKAGE_VERSION)|;' \
    jigsaw-generate.in > jigsaw-generate
```

配方在 `package()` 中直接复现该替换（pkgdatadir 写死为 conan 包内
`lib/jigsaw-generator`，与上游 `make install --prefix` 的绝对路径行为一致），
不做 `./configure`（它只探测 MKDIR_P/prefix 等变量，对交叉环境无意义）。
`build()` 做源码布局校验 + 宿主有 python3 时的 py_compile 预检。

## 与上游 make install 的刻意差异

1. **不构建 doc PDF**：上游 `make -C doc build` 调用 pdflatex 生成
   doc/jigsaw-generator.pdf。构建环境不含 LaTeX，也不应把 LaTeX 变成编译依赖
   （否则每个 CI worker 都要装 TeX Live），包内只带 .tex 源码。
2. **不安装 `filters/` 目录**：0.2.7 源码中不存在该目录（Makefile 中为条件安装）。

## 运行环境依赖（设备端，非 conan 依赖）

- python3 + PyYAML：入口脚本 shebang 为 `#!/usr/bin/env python3`，generate.py
  `import yaml`。ohpcd 制品仓未收录 PyYAML（`conan search pyyaml -r=ohpcd` →
  not found），属设备端运行环境前提，故不声明为 conan 依赖（与 procdump
  对 zconf.h 的口径一致：非链接依赖不声明）。
- pdflatex（仅出 PDF）：源码中 `tabletex` 判定为 `if makepdf and bodytablefile:`，
  即 **`--nomakepdf` 时不写 .tex、不发起任何 LaTeX 调用、只产 .md**；默认模式
  则 tex 输出依赖 pdflatex 存在（缺失时 subprocess 抛 FileNotFoundError，
  属上游行为，不在本适配范围内改）。设备端建议默认走 `--nomakepdf`。

## 上游行为备忘（实测于 0.2.7 源码 + 插桩验证）

- `runlatex()` 在 pdflatex 成功后会执行清理：`doclean = getopt(..., 'clean', True)`
  （默认 True），删除 `basename.{aux,log,tex,ind,idx,out,tex.filter}` ——
  **即中间 .tex 会被删除，真实环境下保留的是 .pdf**。因此 test_package 的运行
  层第 13 断言用"会创建 .pdf 的 stub pdflatex"验证完整管线：断言 .pdf 存在、
  中间 .tex 已被上游清理（0 个残留）。
- `getopt()` 的查找顺序为 options(命令行) → data → layout → config，
  与文档字符串描述一致；`makepdf`/`makemd`/`clean` 走 `getboolean` 解析。
- 模板查找目录（`templatedirs`）：当前目录、用户配置目录 filters 同级、
  包内 `lib/jigsaw-generator/templates`；0.2.7 的 templates/ 目录含全部 36 个
  模板文件（7 版式 yaml + 1 ini + 19 tex + 9 md），打包完整。

## 测试

- `test_package/test.sh`：静态层 9 断言恒执行（布局/shebang/替换完整性/
  pkgdatadir 指向包内/python 包与模板齐全/man 页/语法检查/YAML 全量解析）；
  运行层 4 断言仅在宿主有 python3+yaml 时执行（-v 版本、--help 用法、
  --nomakepdf 真实样例生成、默认模式对 stub pdflatex 生成 .tex）；其中后 2 条（真实样例生成、makepdf 管线）为鸿蒙特有
  端到端消费者用例（PC 鸿蒙化 PR 审查 rule12：完整跑通功能/流程的消费者用例，非纯断言）。
- OHOS worker（aarch64，无 python3）上运行层显式 defer，静态层全量生效。
- 详见 test_package/MANIFEST.yml（上游测试 0 个，如实申报）。

## 本地构建记录（WSL /root/ohpcd-work，2026-10-13）

- 命令：`conan create archives/j/jigsaw-generator/0.2.7 -pr:h=ohos-aarch64-lkyz -pr:b=ohos-aarch64-lkyz --build=missing`
- 结果：待回填（conan create 输出摘要 / package id / 测试断言结果）
