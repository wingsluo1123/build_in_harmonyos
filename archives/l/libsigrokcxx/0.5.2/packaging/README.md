# packaging/

本目录遵循 ARCHIVE-SPEC v3.0 的目录占位约定。

> 依据 `references/iron-rules.md` R20（v3.0 废弃清单）：`package_builder.py`、
> `sign_elf.py` 与 `packaging/` 下的 tar.gz 产物均已废弃，改为
> `conanfile.py → conan create → conan upload → conan install`。
> 因此本目录**不生成** `*-ohos-aarch64.tar.gz` / `*-debug.tar.gz`。

libsigrokcxx 0.5.2 为库包（`package_type=library`），产物是
`lib/libsigrokcxx.so.0.5.2` 加 SONAME/开发用符号链接 `libsigrokcxx.so.0`、
`libsigrokcxx.so`，二进制分发由 Conan 全流程管理，本目录不放发布 tar 包。

- 产物获取：`conan install --requires=libsigrokcxx/0.5.2 -r=ohpcd`
- 产物验证：见 `../reports/test-report.md` 与 `../reports/conan-verify-report.md`
- OHOS 发行 ELF 带 `.codesign` 段（`binary-sign-tool` 自签），未签名 ELF 在设备上
  无法加载；签名细节见 `../notes.md`
