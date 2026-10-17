# konclude

Konclude 是一个面向大规模本体、以并行 tableau 算法为核心的高性能推理机，形式化支撑的描述逻辑为
**SROIQV(D)**，即几乎完整的 OWL 2 DL（含绝大多数数据类型），并额外支持 nominal schema
（可在 OWL 语法中直接书写 DL-safe 规则）。Konclude 由 Ulm 大学开发，以 LGPL-3.0 发布。

## 功能概述

- **推理任务**：`classification`（类分类）、`consistency`（一致性）、`satisfiability`
  （类可满足性，需 `-x IRI`）、`realization`（个体实现）
- **本体格式**：原生支持 OWL 2 XML 与 OWL 2 Functional-Style（`configification`）
- **SPARQL**：内置简易解析器，支持 `SELECT` / `ASK` / `LOAD`（`sparqlfile` / `sparqlserver`），
  复杂查询的 Redland Rasqal 路径不在此构建内
- **OWLlink**：OWLlink XML binding（`owllinkfile` 文件模式与 `owllinkserver` HTTP 模式）
- **并发**：`-w N|AUTO` 配置处理线程数；`-c FILEPATH` 加载配置；`-a` 打印进度

## HarmonyOS PC 适配

- 上游构建系统为 **qmake**（`Konclude.pro` / `KoncludeWithoutRedland.pro` / `KoncludeLIB.pro`
  + 378 KB 的 `Konclude.pri` 源文件清单），无 CMakeLists.txt / Autotools / Meson；
  本适配沿用上游 qmake 路线，qmake/moc/rcc 与 Qt5 运行时由 Conan 包 `qt5-qtbase` 提供。
- **Qt5 可重定位性修复**（配方级，不改上游源码）：`qt5-qtbase` 包内的 `bin/qt.conf` 与
  `mkspecs/{modules,modules-inst}/*.pri` 仍指向其构建目录，重下载后 `qmake` 会报
  `Unknown module(s) in QT`；配方在 `build()` 中把这些路径重写为包目录（与仓库内
  `archives/q/qt5-qtdeclarative` 对同一依赖的既有做法一致）。
- **Redland 可选集成未启用**：上游 `Konclude.pro` 链接的是树内自带的 **x86_64 预编译**
  Redland 栈（`External/librdf/Linux/x64/lib/release/*.a`）与 jemalloc，aarch64 无法使用；
  其源码不在树内，`raptor2`/`rasqal` 在本仓库与 OHOS 制品仓均不存在（属独立依赖任务，R36）。
  因此使用上游官方变体 `KoncludeWithoutRedland.pro`。**功能边界（实测）**：
  - 可用：OWL 2 XML / Functional-Style 解析、全部推理任务、OWLlink（文件 + HTTP）、
    基于 OWL/XML 本体的 SPARQL 查询（实测 roberts 查询返回 331 个答案）
  - 不可用：RDF 非 XML 序列化（Turtle 等）解析——实测加载 `Tests/lubm-univ-bench-data-1.ttl`
    得到**空知识库**（2 个类 / 0 条边），而非报错；因此 `.ttl` 数据驱动的用例结果为空
- **上游快照缺陷修复**（1 个 bugfix 补丁，平台无关）：`applyATLEASTRule()` 中作者的空值守卫
  写在 `hasIdenticalConceptOperands()` 调用之后，短路求值使其失效，导致无显式 operand 列表的
  基数限制触发 NULL 解引用（`Tests/roberts-family-full-D.owl.xml` 的 classification /
  realization 稳定 SIGSEGV）。修复仅把同一守卫提前（纯 `||` 操作数互换，非空语义不变）。
  详证见版本目录 `conandata.yml`（补丁证据段）与 `notes.md` §9.3（`reports/` 为本地工作副本，按 `review-memory §19` 与 `.gitignore` 的 `reports/` 规则不入库）。

## 依赖关系

| 类型 | 依赖 |
|---|---|
| 构建（Conan） | `qt5-qtbase/5.15.2.2`（提供 qmake/moc/rcc + Qt5 Core/Xml/Network/Concurrent） |
| 传递（制品仓已发布） | `dbus/1.14.10`、`expat/2.8.2`、`zlib/1.3.1` |
| 运行 | Qt5 共享库（Conan 依赖链 + RPATH 提供） |
| 未启用（可选） | Redland RDF Libraries（raptor2 / rasqal）——见上文功能边界 |

## 参考资料

- 上游仓库：<https://github.com/konclude/Konclude>
- 产品页 / 文档：<https://www.derivo.de/products/konclude/>
- 本仓库版本目录：`archives/k/konclude/0.7.0-1138-git20220514-dfsg/`
