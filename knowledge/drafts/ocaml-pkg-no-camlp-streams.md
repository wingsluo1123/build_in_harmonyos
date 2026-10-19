# E-DRAFT: 制品仓 ocaml 包不含 camlp-streams findlib 库

## 错误签名

- dune 构建 OCaml 库时报 `Library camlp-streams not found`（dune findlib 解析失败）
- 或 camlp5 生成规则触发时 `Error: Program camlp5o not found`

## 根因

camlp-streams（Stream/Genlex 从 stdlib 拆出的独立 opam 包，github.com/ocaml/camlp-streams）**不随** OCaml 编译器 tarball 安装。制品仓 `ocaml/4.14.1.1.4` 包实测：

```
lib/ocaml/ 下：
  ✅ stdlib__Stream.cmi/.cmx   ← stdlib 废弃遗留的 Stream 模块
  ✅ libcamlstr.a              ← str 库
  ❌ lib/ocaml/camlp-streams/  ← 无目录、无 camlp_streams.cma、无 META
```

dune 的 findlib 解析只认独立的 camlp-streams 包 → 任何 `(libraries camlp-streams)` 声明都无法解析。

## 触发案例：lablgtk3 3.1.5

- `tools/dune`：varcc/propcc 代码生成器 `(libraries camlp-streams)`
- `src/dune-enum.sexp` / `src/dune-prop.sexp`：内嵌 `varcc`/`propcc` 调用规则（gobject_tags/gtk_tags/pango_tags 等枚举头 + 全部 Props ML 生成）
- → `dune build -p lablgtk3` 的硬构建路径必经 varcc/propcc → 必需 camlp-streams

## 处方

独立适配 camlp-streams >= 5.0（纯 OCaml、无 C 代码），范式照抄 `archives/o/ocaml-syntax-shims/1.0.0`：
`requires ocaml + dune` → `dune build -p camlp-streams` → `package()` 手工 copy `_build/install/default/lib`（HMDFS 上 dune install 会失败）。

注意：stdlib 的 `Stream` 与 camlp-streams 的 `Stream` 是两个不同 findlib 提供者，dune 只认后者。

## 关联

- lablgtk3 3.1.5 W0 预检（dependency_missing 证据链）
- pdfsandwich 0.1.7（OCaml 工具链 tool_requires 先例，archives/p/pdfsandwich）
