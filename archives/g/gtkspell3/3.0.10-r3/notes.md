# gtkspell3 3.0.10-r3 — HarmonyOS PC 适配说明

## 基本信息
- **软件**: gtkspell3（GTK 文本拼写检查库）
- **版本**: 3.0.10-r3
- **构建系统**: Autotools（预生成 configure）
- **包类型**: library（`package_type=library`）
- **License**: LGPL-2.1-or-later

## 源码
- Debian orig：`https://ftp.debian.org/debian/pool/main/g/gtkspell3/gtkspell3_3.0.10.orig.tar.xz`
- 避免 SourceForge 在 CI 返回 HTML 导致 BadZipFile

## OHOS 适配要点
1. `--host/--build=aarch64-unknown-linux-ohos`
2. CI 无 intltool：提供 `intltool-*` stub（`--version` → 0.51.0）+ 最小 `XML::Parser`
3. HMDFS：`umask 077→022`，`mktemp` 改用 `$TMPDIR`
4. 仅构建 `gtkspell/` 子目录，跳过 examples/po/docs
5. 系统依赖：`gtk+-3.0` / `enchant-2` / `glib-2.0`（`PKG_CONFIG_PATH` 指向 `DEFAULT_PREFIX`）
6. 安装后对 `.so` 做 `llvm-objcopy` 去旧签名 + `binary-sign-tool` 自签（XPM dlopen）

## 测试
- `test_package/test.sh`：检查 `libgtkspell3-3.so` 与 `gtkspell3-3.0.pc`
