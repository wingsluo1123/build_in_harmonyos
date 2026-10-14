# pseudo 1.9.2-git20250711-d1db9c219abf 适配笔记

## 构建配置
- 构建系统: upstream custom configure + Makefile
- SQLite: `sqlite3/3.53.4` 静态库（使用已发布制品，避免依赖未发布的 3.49.1）
- xattr: 显式关闭（OHOS 设备镜像不提供上游要求的 getfattr/setfattr）
- 状态: built after OpenDesk verification

## 上游测试

源码包含 25 个 `test/test*.sh` 脚本。配方逐个执行，并根据设备能力记录：
- ACL / xattr 测试：缺少 `setfacl`、`getfacl`、`getfattr`、`setfattr` 时如实跳过。
- tclsh fork 测试：缺少 `tclsh` 时如实跳过。
- 其余脚本全部实际执行。

测试脚本仅调整 shebang 到 OHOS 实际存在的
`/data/service/hnp/bin/bash`，不修改断言或测试逻辑。

所有源码兼容性改写均可在同一 Conan 源码缓存上重复执行，已应用后不会再次改写或报错。

## 产物

- `bin/pseudo`
- `bin/pseudodb`
- `bin/pseudolog`
- `lib/libpseudo.so`

## 验证命令

```bash
CI_PACKAGES=archives/p/pseudo/1.9.2-git20250711-d1db9c219abf \
  zsh ci/conan/build_and_test.sh
```
