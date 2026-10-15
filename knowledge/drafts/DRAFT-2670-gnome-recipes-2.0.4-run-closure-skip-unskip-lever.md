# DRAFT-2670 — conan 2 运行闭包跳过传递共享库：Skip 判定与 un-skip 的唯一实测杠杆（被依赖方显式 requires）

> 状态：草稿（来自 gnome-recipes 2.0.4 适配，task_id=2670）
> 与已有条目关系：`E669`（lnav 0.13.2）已覆盖主干现象与修法推荐；本条为
> 其增量实证——"配方侧访问 package_folder 即拉回运行闭包"这一兜底通道
> 在 conan 2.29.1 上**不成立**，并给出两通道并用的落地代码与证据。

## 问题

应用消费者 test_package 真跑自产二进制即失败（未改配方前）：

```console
Error relocating .../p/b/gnome4bac88868f61b/p/bin/gnome-recipes:
archive_write_add_filter_gzip: symbol not found
ConanException: Error 127
```

图的 Requirements 里 `libarchive/3.8.7` 明明在（gnome-autoar 的 pin，
配方又加了显式直依赖），test 阶段却仍在 `Skipped binaries` 列表里。

## 根因（conan 2.29.1 实测钉深）

运行闭包的 skip 判定看「该依赖对消费者贡献了什么」（libs/runenv），
传递依赖默认被 `Skipped binaries`。被 skip 的直接后果：

1. **`package_folder` 为 None**。配方 `package_info()` 里常见的守卫型写法
   `la = self.dependencies["libarchive"]; if la.package_folder: runenv_info.
   prepend_path(...)` 会**静默失效**——不报错、不警告、不落任何目录。
2. **配方侧"访问 package_folder 即拉回运行闭包"的兜底不成立**（本条
   增量核心）：实测 gnome-recipes 的 `package_info()` 在测试图里确实被
   执行（无条件 `PATH` 前置落在 conanrunenv 的 `export PATH=` 行、包目录
   出现 2 次；profile `os=OHOS` 与守卫一致），libarchive 却依旧留在
   `Skipped binaries`、生成的 `conanrunenv-release-armv8.sh` 里
   `grep -c libara` = 0——仅"访问"不足以把 Skip 转 Cache。
3. **唯一实测有效杠杆 = 被依赖图根侧消费者显式声明**：
   test_package 的 `requirements()` 直接 `self.requires("libarchive/3.8.7")`
   （与配方同版去重无冲突）。之后：`Skip → Cache`、`Already installed`、
   `package_folder` 可用、进入依赖表——此时**两个通道同时落实**：
   配方侧 runenv 发布（package_folder 已可用）+ test() 侧枚举注入。

## 方案（gnome-recipes 2.0.4 落地形态）

test_package 显式直依赖（un-skip 杠杆）：

```python
def requirements(self):
    self.requires(self.tested_reference_str)
    # DT_NEEDED 传递共享库必须是直依赖，否则被 Skipped → 不进依赖表（E669）
    self.requires("libarchive/3.8.7")
```

test() 侧枚举注入（组件化包 cpp_info.libdirs 可能为空，不能只读 cpp_info；
经脚本参数传入，脚本内前置进 LD_LIBRARY_PATH）：

```python
ld_dirs = []
for dep in self.dependencies.host.values():
    if not dep.package_folder:
        continue
    for sub in ("lib", "lib64"):
        _dir = os.path.join(dep.package_folder, sub)
        if os.path.isdir(_dir) and _dir not in ld_dirs:
            ld_dirs.append(_dir)
```

配方侧 runenv 发布保留（真实消费者图的"入闭包即受益"通道；见 E669 兜底）。
**修法排序**：先让包入闭包（显式 requires），再谈环境注入——顺序反了
两个通道都不落实。

## 验证

- gnome-recipes 2.0.4（task 2670，2026-10-14，conan 2.29.1）：
  - 反例（仅配方侧直依赖 + 守卫型 runenv 发布）：test 图
    `libarchive` 在 Skipped binaries；conanrunenv 无其目录；test rc=127；
  - 正例（test_package 显式 requires）：`libarchive/3.8.7 - Cache`、
    `Already installed! (17 of 34)`；conanrunenv 出现其 libdir；test()
    注入的 RUN 行含 `.../p/libara07f23a76465c/p/lib`；冒烟测试
    `gnome-recipes package smoke test: OK`，rc=0。

## 适用边界

- conan 2.x 应用/工具类配方，其二进制 DT_NEEDED 指向传递依赖的共享库；
- 现象是"构建/链接全绿、真跑 rc=127 且符号看似毫不相干"（符号 provider
  可能来自静态链入对象的再导出，如 autoar→libarchive）；
- 若设备系统库存在同名减配版，会静默回落成功一半——必须先确认符号
  缺失清单而非随手改链接。

## 查重差异

- 与 E669 不重复：E669 侧重建"显式 requires→Skip 转 Cache→枚举注入"
  主干（其验证环境为 lnav 任务）；本条给出 2.29.1 上的**管道行为实证**
  （runenv 聚合对被测包成立、skip 不因 package_folder 访问而转变、
  package_folder=None 的静默性）与两通道并用的最小落地形态；
- 与「消费已发布 soname-less 包」类草稿（链接期代理）不同面：本条是
  运行期加载闭包，不是链接期名字解析。

## 关联交付

- 本草稿与 `archives/g/gnome-recipes/2.0.4/**` 同属一次交付
  （test_package/conanfile.py + test_package/test_gnome_recipes.sh +
  conanfile.py package_info 段）。
- 正式 E 编号由知识库主编审核后分配。
