# krb5-auth-dialog-43.0：meson gnome 模块的 pc 变量定位注入——glib-compile-* 工具链三件套

## 命中场景

GNOME/meson 系软件在 OHOS conan 环境构建时调用 `gnome.compile_resources()` /
`gnome.compile_schemas()`（凡 Kbuild 用到 gresource 编译或 gsettings 编译的件：
GNOME app 全家、GTK 系应用）。

## 症状链（实测，krb5-auth-dialog 43.0 / meson 1.11 / glib 2.84.0.1）

1. `data/meson.build:21: ERROR: Could not get pkg-config variable and no default provided for <PkgConfigDependency gio-2.0>`（compile_schemas 处）
2. 修复后同型报错移到 `src/meson.build:31`（compile_resources 处）
3. wrapper 落地后运行时报 `operation not permitted`（缓存 ELF 被拒执）
4. `ERROR: Could not detect Ninja v1.8.2 or newer`（PATH 重置）

## 根因

| 层 | 问题 |
|----|------|
| 工具定位 | gnome 模块从 **pc 变量**读工具路径，不查 PATH；conan 生成的 pc 无该变量 |
| 查询路径 | 实测 compile_schemas 与 compile_resources **都从 gio-2.0.pc 查**（与 meson 文档声明的 glib-2.0.pc 不一致）——单文件注入必漏 |
| 工具执行 | glib 包 bin/ 是无 RPATH ELF（库找不到）+ cache 只读 + 下载件签名被 XPM 拒（EPERM） |
| ninja | VirtualBuildEnv 重置 PATH；registry ninja 包缓存无可用二进制 |

## 方案（实证通过）

三件套：

```python
# (a)+(b) staging 副本重签 + LD_LIBRARY_PATH wrapper
staged = os.path.join(wrapdir, tool + ".bin")
shutil.copy2(real, staged); self._self_sign(staged, force=True)
# wrapper: #!/bin/sh
#          LD_LIBRARY_PATH="<glib包lib>:$LD_LIBRARY_PATH" exec "<staged>" "$@"

# (c) pc 双文件双变量注入
for pc_name in ("glib-2.0.pc", "gio-2.0.pc"):
    with open(os.path.join(generators_folder, pc_name), "a") as handle:
        for variable, tool in (
            ("glib_compile_resources", "glib-compile-resources"),
            ("glib_compile_schemas", "glib-compile-schemas"),
        ):
            handle.write("%s=%s\n" % (variable, os.path.join(wrapdir, tool)))
```

ninja：同 toolbin 目录放宿主 ninja wrapper（`exec /usr/local/bin/ninja "$@"`），
与 glib wrapper 同通道注入 PATH（meson setup 实测可见）。

**验证**：meson configure 全过（40 目标枚举）→ 52/52 编译链接 → conan create
三层消费者测试全绿（产物层/签名闭包 154 物化/CLI 合同 `krb5-auth-dialog 43.0`）。

## 查重对照（knowledge/graph/index.tsv，766 条）

- `glib_compile_resources` / `glib_compile_schemas` / `pc.*inject` / `gnome.*compile`：**零命中**
- E075（pkg-config 环境变量陷阱）：讲 C_INCLUDE_PATH/PKG_CONFIG_PATH 污染，是**环境变量层**，本条是**pc 文件变量缺失层**，不重叠
- E307（compiler_executables 直编）：profile conf 层，不同问题
- glib 工具 launcher（libnma-gtk4 `_glib_tool_launcher`）：仅 PATH wrapper 无 pc 注入、无 staging 重签——本条是其升级完备版（增加 (b)(c) 两层 + 实测查询路径修正）

## 关联

- PR：!14776（krb5-auth-dialog 43.0，feat/krb5-auth-dialog-43.0 @7e4175df4b）
- 复现：`conan create archives/k/krb5-auth-dialog/43.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`
