# sox_ng

SoX next generation —— SoX（Sound eXchange）音频转换库的重写版本。

- 上游仓库：https://codeberg.org/sox_ng/sox_ng
- 许可证：LGPL-2.1-or-later
- 构建系统：autotools（configure/make/make check）
- 产物：`libsox_ng`（音频转换库）+ CLI 工具（`sox_ng`、`soxi_ng`、`play_ng`、`rec_ng`）

## 版本索引

| 版本 | 状态 | 适配日期 | 备注 |
|------|------|---------|------|
| 14.8.0.1 | built | 2026-10-13 | OHOS arm64 适配，5 补丁（config.guess/config.sub OHOS triplet、configure/config.guess umask 077→007、musl tmpfile 截断修复、check.sh TMPDIR）；上游测试 243/245 通过（2 上游 VOID，0 失败） |
