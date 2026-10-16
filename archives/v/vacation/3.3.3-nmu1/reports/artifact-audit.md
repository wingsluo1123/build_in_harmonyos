# vacation 3.3.3-nmu1 产物审计

## 审计对象

对 HarmonyOS PC 真机上干净 `conan create` 生成的安装后
`bin/vacation` 执行审计，不使用构建树中的中间文件。

## 结果

- SHA256：`ab51785c928c9f7ffca40d56404f90984f7080be133e7ce244fc553cb4ed7281`
- 格式：64 位 little-endian AArch64 动态 ELF，解释器为
  `/lib/ld-musl-aarch64.so.1`。
- `NEEDED`：仅 `libdb.so` 和 `libc.so`，与配方声明的
  `db1-compat/2.1.3` 依赖一致。
- `RPATH`/`RUNPATH`：无。
- `.codesign`：恰好 1 节。
- 路径泄漏：`strings` 扫描未发现 `/storage/`、`/home/`、
  `.conan2` 或 `/.cache/` 字符串。

审计结论：产物架构、动态依赖、签名节与可迁移性均符合
HarmonyOS PC 交付要求。
