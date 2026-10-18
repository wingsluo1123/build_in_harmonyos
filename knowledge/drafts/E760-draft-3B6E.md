# E760 — Conan 静态包里混进 .so 导致的运行期加载失败

> Contributor: swupdate-2026.05.1 适配 | Status: Draft | 2026-10-16
> Source: swupdate 2026.05.1 + libarchive/3.8.7（OHOS 制品仓）

## 错误特征

交叉编译产物本身链接成功，但运行/加载时报：

```
Error loading shared library libarchive.so.13: (needed by .../bin/swupdate)
Error relocating .../bin/swupdate: archive_read_new: symbol not found
Error relocating .../bin/swupdate: archive_write_disk_new: symbol not found
...
```

`readelf -d` 确认产物带 `NEEDED libarchive.so.13`，而 conan 生成的
`conanrunenv-*.sh` 的 `LD_LIBRARY_PATH` 里**没有** libarchive 的目录
（只有 libconfig / json-c / libcurl 三个 shared=True 的包）。

同一条链上还有两个带欺骗性的次生现象：

1. **测试假通过**：凡是「期望命令失败」的断言
   （`if <cmd>; then false; fi`）都会因为二进制根本起不来（rc=126/127）
   而通过——本任务实测：未修时 `test.sh` 的
   `missing image rejected (rc=127)` 报 PASS，只有 `--version` 的
   退出码检查能暴露问题。因此 test_package 应先断言
   `<binary> --version` rc=0，并在失败时**直接退出**。
2. 如果同时把该目录从 `-L` 里去掉，报的是
   `ld.lld: error: unable to find library -larchive`。

## 触发条件

- 构建系统: 任意（本仓为 Kbuild/raw make）；关键在 conan 依赖接法
- 阶段: linking（`DT_NEEDED` 生成）→ runtime（加载失败）
- 依赖包: `shared=False` 但 `lib/` 下 `.a` 与 `.so` 并存（OHOS 制品仓实测
  `libarchive/3.8.7`）

## 根因分析

- Conan 2 的 `VirtualRunEnv` 只导出 `require.run=True` 的依赖目录
  （`conan/tools/env/virtualrunenv.py`：`if require.run:`）；`run` 由包的
  shared/application 属性推出，`shared=False` 的包被视为"链接期吸收"，
  其 libdir 永不进入 `conanrun`。
- OHOS 制品仓里存在 `shared=False` 但 `lib/` 下 `.a` 与 `.so` 并存的包：
  `conan list -r=ohpcd "libarchive/3.8.7:*"` 显示 package options
  `shared: False`，而 `p/<pkg>/p/lib` 同时有 `libarchive.a` 与
  `libarchive.so.13`。
- 链接器在同一目录里优先 `.so`，于是产物带上 `DT_NEEDED`，与 Conan 的
  运行期模型直接矛盾。
- 在消费方 `test_package` 里再显式 `self.requires("libarchive/3.8.7")`
  **也无效**：实测 `conan install` 后 `conanrunenv-*.sh` 仍然只有三个
  shared 包的目录（`require.run` 依旧是 False）。

## 解决方案

### 推荐方案：影子目录（只在本地复制，不动共享缓存）

在 `generate()` 里为所有 `shared=False` 的依赖造一个只放 `lib*.a` 的影子
目录，并放在 `-L` 列表最前（链接器按目录顺序取首个匹配）：

```python
shadow = os.path.join(self.generators_folder, "conan-static-libs")
os.makedirs(shadow, exist_ok=True)
for dep in self.dependencies.host.values():
    shared = dep.options.get_safe("shared") if dep.options else None
    if shared is None or bool(shared):     # _PackageOption 的 __bool__ 才是真值
        continue
    for libdir in dep.cpp_info.aggregated_components().libdirs or []:
        for name in os.listdir(libdir):
            if name.startswith("lib") and name.endswith(".a"):
                shutil.copy2(os.path.join(libdir, name), os.path.join(shadow, name))
libdirs = [shadow] + libdirs               # 用于 -L 与 LD_LIBRARY_PATH
```

实测（swupdate 2026.05.1）：修前 `readelf -d bin/swupdate | grep -c libarchive`
= 1（`libarchive.so.13`），修后 = 0；`test_package` 13/13 通过，运行期只剩
`libjson-c.so.5` / `libcurl.so` / `libconfig++.so`（三者 shared=True，
`conanrun` 里都在）。

### 回退方案

消费侧额外 env 脚本：`Environment().append("LD_LIBRARY_PATH", libdir)` →
`save_script(...)`，运行时 `env=["conanrun", "<script>"]`。适用于不便改链接面
的场景。

### 禁止做法

- ❌ 删/移动共享 conan 缓存里的 `.so`（`rm .../conan2/p/*/lib*.so`）：
  本设备 conan 缓存是全设备共用，会静默影响其他任务并被 conan 判为缓存损坏。

## 验证

```bash
# 产物是否带该包的 DT_NEEDED（修后应为 0）
readelf -d <build>/bin/<binary> | grep NEEDED
readelf -d <build>/bin/<binary> | grep -c libarchive
# 该包是否 shared=False 且 .a/.so 并存
conan list -r=ohpcd "libarchive/3.8.7:*" | grep shared
ls "$(conan cache path libarchive/3.8.7:<pid>)/lib"
```

## 关联条目

- 症状相近但根因不同：**E274**（配方只装 `lib.so` 未建版本化 SONAME 链接 →
  运行期找不到 `lib.so.X.Y`）。E274 的修法是补 SONAME 文件/链接，对本场景
  无效（本场景文件都在，是"不该被选中的 .so 被选中"）。
- 反例：`shared=True` 的包其目录一定进 `conanrun`，即使它同样同时装
  `.a` 与 `.so`（如 json-c）。
