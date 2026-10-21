# packaging/

本目录遵循 ARCHIVE-SPEC v3.0 的目录占位约定。

pizzly 0.37.3 为应用型工具包（`package_type=application`，产物为单个可执行文件
`bin/pizzly`），由 Conan 全流程管理二进制分发，本目录不放发布 tar 包
（R19：禁止手动打包，必须用 `conan create`）。

- 产物获取：`conan install --requires=pizzly/0.37.3 -r=ohpcd`
- 产物验证：见 `reports/test-report.md` 与 `reports/conan-verify-report.md`
- 本包当前状态为 `built`（尚未经 release 流水线发布到制品仓，`commands.json` 的
  `binary` 字段保持 `false`）
