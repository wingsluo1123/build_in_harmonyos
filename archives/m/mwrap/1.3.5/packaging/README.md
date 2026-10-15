# packaging/

本目录遵循 ARCHIVE-SPEC v3.0 的目录占位约定。

mwrap 1.3.5 为应用型工具包（package_type=application，产物为单个可执行文件
`bin/mwrap`），由 Conan 全流程管理二进制分发，本目录不放发布 tar 包。

- 产物获取：`conan install --requires=mwrap/1.3.5 -r=ohpcd`
- 产物验证：见 `reports/test-report.md` 与 `reports/conan-verify-report.md`
