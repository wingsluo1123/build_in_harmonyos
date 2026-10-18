# raptor2

Raptor RDF Syntax Library：高性能 C 库，用于解析与序列化 RDF。

## 功能概述

- **解析器**：RDF/XML、N-Triples、Turtle、TriG、N-Quads、RSS tag soup、RDFa、RDF/JSON、GRDDL、自动识别（guess）
- **序列化器**：RDF/XML、RDF/XML-abbrev、Turtle、mKR、N-Triples、N-Quads、RSS 1.0、Atom 1.0、JSON、GraphViz DOT、HTML
- **命令行工具**：`rapper`（解析/转换/校验 RDF 文档），随包安装到 `bin/`
- **API**：`raptor2.h` 提供 world/parser/serializer/URI/statement 等完整 C API

上游同时提供 autotools 与 CMake 两套构建，但 CMake 路径没有注册任何测试（无 `enable_testing()`/`add_test()`），上游完整测试套件只在 autotools 的 `make check` 下，因此本配方使用 autotools。

## OHOS 适配

要点（详见 `2.0.16/notes.md`）：

1. `config.guess`/`config.sub` 增加 HarmonyOS 与 `linux-ohos` 三元组识别——否则 `configure` 在 build type 阶段即失败。
2. autoconf 生成的 `configure`/`config.status` 用 `umask 077 && mktemp -d` 创建临时目录；本机文件系统把该目录落成 `drwx--S---`(2700)，属主也无法写入，必须去掉 `umask 077`。
3. libxml2 兼容：`xmlEntity.checked` 私有字段在 2.11.0 被移除（守卫需补上界），nanohttp 声明在 2.13+ 被 `LIBXML_HTTP_STUBS_ENABLED` 包住（OHPCD libxml2 未开启 HTTP stubs，因此 WWW 后端必须走 libcurl）。
4. ICU 是 C++ 静态库，C 链接驱动需显式 `-lc++`；静态 `libraptor2.a` 的消费者同样需要链接 libc++（配方已在 `package_info()` 声明）。
5. `make check` 运行的二进制需要把本图依赖的 libdir 前置到 `LD_LIBRARY_PATH`。

全部 10 个解析器与 11 个序列化器均保持启用（configure 摘要 + 上游 `tests/` 套件共同佐证）；配方中的 `_assert_full_feature_set()` 另对 19 个条件特性宏（10 个解析器 + 6 个序列化器 + WWW/NFC/XML 后端）做构建期断言，任一缺失即直接失败，防止日后再次静默退化。

## 依赖关系

编译/运行依赖（Conan）：`libxml2/2.15.3.1`、`libxslt/1.1.45.2`、`yajl/2.1.0`、`curl/8.22.0`、`icu4c/78.3`。

## 参考资料

- 官网：https://librdf.org/raptor/
- 源码：https://download.librdf.org/source/
- 文档：https://librdf.org/raptor/api/
