# DRAFT：meson 的 `glib_compile_schemas: true` 不等于安装产物里有 `gschemas.compiled`——消费者首次用 GSettings 就 SIGTRAP

> Draft: `DRAFT-LIBGWEATHER4-444-GSETTINGS-SCHEMA-NOT-COMPILED-IN-PACKAGE`
> Stem: `libgweather4-4.4.4-gsettings-schema-not-compiled-in-package` — pairs with the same-stem `.kv`

## 错误特征

消费者测试（或下游应用）第一次创建使用 schema 的对象时当场死掉：

```
GLib-GIO-FATAL-ERROR: No GSettings schemas are installed on the system
Trace/breakpoint trap (SIGTRAP)
```

包里 schema 目录**只有源 XML，没有编译产物**：

```
$ ls <package>/share/glib-2.0/schemas/
org.gnome.GWeather4.enums.xml
org.gnome.GWeather4.gschema.xml
gschemas.compiled        ← 不存在
```

而同一次构建**源码树内**跑 `meson test` 一切正常 —— 这是本条最容易骗人的地方：
配方全绿、CI 绿、源码树测试绿，坏包只有在被**安装后消费**时才炸。

## 根因

1. meson 的 `glib_compile_schemas: true` 是**源码树内**的开关：它把编译产物生成在
   **构建目录**里，供同一次构建的测试通过 `GSETTINGS_SCHEMA_DIR` 使用。
2. 上游（libgweather 4.4.4 `data/meson.build`）用 `install_data()` 把
   `org.gnome.GWeather4.gschema.xml` / `.enums.xml` 装进
   `${datadir}/glib-2.0/schemas/`，`meson.install()` 复制的**只是这两个源文件**；
   meson 不会追着「安装目录」再编译一次。
3. GSettings 只认 `gschemas.compiled`：`g_settings_new()` → 后端初始化 →
   找不到编译产物 → `g_error()` → `abort()`。

**为什么算平台/打包坑而不是库的 bug**：源码树里能过、包形态必炸，症状出现在
消费者进程里，与库的编译选项无关；不补这一步，交付的包就是坏包。

实测（libgweather4 4.4.4，设备 3QC0124C11000071，clang 15 aarch64-ohos）：
补编译前消费侧首帧 SIGTRAP；补编译后 `test_package` 的 `# failures: 0`。

## 解决方案

在 `package()` 的**最后**（schema 源文件已拷进包之后）显式编译并**校验产物**：

```python
def _compile_gsettings(self):
    schema_dir = os.path.join(self.package_folder, "share", "glib-2.0", "schemas")
    if not os.path.isdir(schema_dir):
        return
    if not any(f.endswith(".gschema.xml") for f in os.listdir(schema_dir)):
        return
    compiler = shutil.which("glib-compile-schemas")   # 由 _inject_glib_tools 放上 PATH
    if not compiler:
        raise ConanException("glib-compile-schemas not found — the package would "
                             "ship uncompiled GSettings schemas and abort every "
                             "consumer at runtime")
    self.run(f'"{compiler}" "{schema_dir}"')
    if not os.path.isfile(os.path.join(schema_dir, "gschemas.compiled")):
        raise ConanException("glib-compile-schemas produced no gschemas.compiled")
```

四个容易漏的点：

1. **工具来源**：目标机/CI worker 通常没有系统 glib 开发工具；`glib-compile-schemas`
   随 glib 的 conan 包一起发布，靠 `generate()` 里把 glib 包的 bin 目录
   `buildenv_info` 注入 PATH（本配方 `_inject_glib_tools()`，同批注入
   `glib-mkenums` / `gio-querymodules` / `glib-mkenums` 等 gnome 模块工具）。
2. **顺序**：必须先 `meson.install()` 拷源 XML、再编译；反了等于白编。
3. **失败要 raise**：缺 `gschemas.compiled` 的包是坏包，用 `warning` 放行会把
   SIGTRAP 推迟到消费者/下游应用现场，定位成本高得多。
4. **验收要落在安装后的包上**：在 `test_package` 里真实创建一个使用 schema 的
   对象（本包是 `gweather_info_new()` → 库内设置读取路径），源码树内的测试
   永远复现不了这个问题。

## 验证命令

```bash
PKG=<conan package folder>
find "$PKG/share/glib-2.0/schemas" -name '*.gschema.xml' | head
test -f "$PKG/share/glib-2.0/schemas/gschemas.compiled" \
  && echo SCHEMA_COMPILED_OK || echo SCHEMA_MISSING      # 修之前是 SCHEMA_MISSING
# 手工补编译（诊断用，正式修复放 package() 里）
glib-compile-schemas "$PKG/share/glib-2.0/schemas" && echo COMPILE_OK
# 消费侧真机验证：创建使用 schema 的对象，观察不再 SIGTRAP
```

## 禁止策略

- ❌ 以为 meson 的 `glib_compile_schemas: true` 会作用于安装目录
- ❌ 只 `warning` 不 `raise` —— 坏包会以 SIGTRAP 形式在下游现场炸
- ❌ 用源码树内的 `meson test` 绿灯证明「包里的 schema 没问题」
- ❌ 去目标机找系统 `glib-compile-schemas`（多半没有）——用 glib conan 包自带的

## 关联条目

- 相关但不同：`DRAFT-ohos-glib-test-framework-cmake-inject`
  （CMake 侧注入 `COMPILE_SCHEMA_EXECUTABLE` 来**在构建期生成**测试用 schema，
  解决的是「测试框架怎么拿到编译器」，不是「安装产物缺编译」）
- 同一包的相邻坑：`.codesign` 缺失导致 loader 拒载共享库、OHOS musl 忽略
  `LD_LIBRARY_PATH`（见 `DRAFT-xauth-1.1.4-in-tree-check-binary-loader-cannot-find-conan-shared-deps`）
- 本条由 libgweather4 4.4.4 移植实测产出（PR #13996，配方 `package()` →
  `_compile_gsettings()`，`conanfile.py` 中已实现并校验产物）
