# DRAFT — 纯数据包的 conan 配方怎么满足上游 `dependency('hwdata', native: true)`

**来源**：libdisplay-info 0.4.0 适配（`archives/l/libdisplay-info/0.4.0`）
**日期**：2026-10-16
**状态**：DRAFT（待复审）
**关联**：[DRAFT-libdisplay-info-tools-0.3.0-build-time-data-dependency-hwdata](DRAFT-libdisplay-info-tools-0.3.0-build-time-data-dependency-hwdata.md)
——那条的结论是"没有配方时代把数据文件随配方携带"；这一条是它的后续：**制品仓已有 `hwdata/0.411` 之后，正确的接法是什么。**

## 现象

```
Run-time dependency hwdata found: NO  (tried pkg-config and cmake)
libdisplay-info-0.4.0/meson.build:24:11: ERROR: File /usr/share/hwdata/pnp.ids does not exist.
```

即使 `self.requires("hwdata/0.411")` 已解析成功，上游的 found 分支也拿不到 `pkgdatadir`。

## 三个叠加的坑

1. **conan 合成的 `.pc` 没有 `pkgdatadir`**
   `PkgConfigDeps` 生成物只有 `prefix` / `bindir` / `libdir` / `includedir` 一类变量：

   ```
   prefix=/storage/.../.conan2/p/hwdat4772d70d4893f/p
   bindir=${prefix}/bin

   Name: hwdata
   ```

   而上游要的是 `dep_hwdata.get_variable(pkgconfig: 'pkgdatadir')`。

2. **数据包自带的那份 `.pc` 不可迁移**
   `hwdata` 在 `package()` 里写了 `share/pkgconfig/hwdata.pc`，但 `pkgdatadir` 是打包时的
   绝对路径（`.../.cache/conan2/p/b/hwdatXXXX/p/share/hwdata`），conan 不做 `.pc` 重定位，
   换机器/换 `CONAN_HOME` 即指向不存在的目录。

3. **meson 的两个隐藏前提**
   - `pkg_config_path` 是 meson 的 **built-in option**，必须写在 native/cross 文件的
     `[built-in options]` 段；写进 `[properties]` 会被静默忽略（实测：configure 日志里
     `env[PKG_CONFIG_PATH]` 为空，依赖直接 not found）。
   - 上游把数据依赖写成 `native: true`（构建机依赖）。**交叉构建**时 meson 读的是
     `build.pkg_config_path`，而 `MesonToolchain` 默认把它置 `None`（见其源码注释里的
     conan issue 链接）。

## 推荐做法

```python
def requirements(self):
    self.requires("hwdata/0.411")          # 构建期数据依赖，进 PF4/L0i 依赖闸门

def generate(self):
    tc = MesonToolchain(self)
    tc.project_options["wrap_mode"] = "nodownload"
    tc.build_pkg_config_path = self.generators_folder.replace("\\", "/")   # 交叉构建也能命中
    tc.generate()
    self._write_hwdata_pc()

def _write_hwdata_pc(self):
    pkgdatadir = os.path.join(self.dependencies["hwdata"].package_folder,
                              "share", "hwdata").replace("\\", "/")
    pnp_ids = os.path.join(pkgdatadir, "pnp.ids")
    if not os.path.isfile(pnp_ids):         # 缺数据文件要显式失败，别让 custom_target 生成空表
        raise ConanException(f"hwdata/0.411 does not provide pnp.ids: {pnp_ids} missing")
    with open(os.path.join(self.generators_folder, "hwdata.pc"), "w") as fh:
        fh.write(f"prefix={pkgdatadir}\ndatadir=${{prefix}}\npkgdatadir=${{prefix}}\n\n"
                 "Name: hwdata\nDescription: ...\nVersion: 0.411\n")
```

要点：

- 用 `requires` 而不是 `tool_requires`：CI 的 host/build profile 相同，`generators` 目录一份即可；
  用 `requires` 还能被 PF4/L0i 依赖闸门覆盖到。
- **不要**复制数据文件进配方、**不要**在 `build()` 里联网下载（旧做法的两个副作用：
  每个配方各带一份数据 + 构建由离线变联网）。
- 断言数据文件存在，避免"生成的表是空的"这种静默失败。

## 验证

```bash
grep -n "pkgdatadir" hwdata.pc                      # 合成物：没有该变量
grep -n "pkgdatadir" <pkg>/share/pkgconfig/hwdata.pc # 包内：打包机绝对路径
# 配方修好后
conan create . -pr:h=<ohos> -pr:b=<ohos>            # 上游 found 分支命中，configure 通过
```
