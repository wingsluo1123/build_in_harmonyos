# gcc-probe

GNU GCC 14.2.0 for HarmonyOS PC（aarch64），启用 `--enable-plugin` 与 `--enable-shared` 的完整多语言构建。

- 与仓内 `archives/g/gcc-14/14.2.0` 同源（同一 `gcc-14.2.0.tar.xz`），差异对照见 `14.2.0/notes.md` §5；
  本包安装面额外包含 `plugin/include` 插件头（实测 475 个 `.h`，含 `gcc-plugin.h`、`plugin-version.h`）。
- 下游用途：为 `odb/2.4.0` 提供带插件支持的 GCC 工具链（`tool_requires`）——上游 `m4/gcc-plugin.m4`
  对非 GNU 编译器直接 `AC_MSG_ERROR`，仓内其余 GCC 家族包均为 `--disable-plugin`。
- 构建系统：`autotools-custom`（GCC 自带 configure + 分步 make，见 `14.2.0/conanfile.py`）。
- 版本：`14.2.0`（状态见 `14.2.0/manifest.yaml`）。
