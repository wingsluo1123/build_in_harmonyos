# packaging 说明 — xmlto 0.0.29

Conan 配方包（`conanfile.py`），交付物由 `conan create` 生成并上传制品仓。

本目录为归档占位说明：打包产物（`*.tar.gz` / `*.sig`）由 CI release 流水线在
PR 合并后生成并上传制品仓，源码仓不入库
（`.gitignore` 规则 `archives/**/packaging/*.tar.gz`）。

## 包内容

- `bin/xmlto` — XSL 工具链前端脚本
- `bin/xmlif` — XML 条件处理工具（OHOS aarch64 ELF）
- `share/xmlto/format/` — 各格式转换的 XSL 样式表
- `share/xmlto/xmlto.mak` — Makefile 规则模板

## 消费方式

```bash
conan install --requires=xmlto/0.0.29@ohpcd/stable -pr=<ohos-aarch64 profile>
```

运行时依赖系统工具：`bash`、`getopt`、`xmllint`、`xsltproc`。
