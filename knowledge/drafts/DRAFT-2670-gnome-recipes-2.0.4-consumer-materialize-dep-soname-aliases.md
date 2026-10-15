# DRAFT-2670 — 消费者侧物化依赖包缺失的 soname 链接名（symlink(2) EPERM 的下游补偿）

> 状态：草稿（来自 gnome-recipes 2.0.4 适配，task_id=2670）
> 与已有条目关系：`E492`（zix，生产侧自我物化）与
> `DRAFT-kea-hook-ping-check-3.0.3-...`（自家构建树/包内物化）同族；
> 本条增量 = **消费侧对依赖包目录**物化，触发点在**构建期链接**。

## 问题

消费者配方构图中，一个节点（libgoa，因 glib 向下统一而源码重编）在
conan `package()` 时只落了实体文件 `libgoa-1.0.so.0.0.0`——
`libgoa-1.0.so.0` / `libgoa-1.0.so` 两个名字根本没进包（conanmanifest
证实，非事后被删）。消费者的 Meson/Ninja 链接随即失败：

```console
[97/125] Linking target tools/recipe-extract
FAILED: ld.lld: error: unable to find library -lgoa-1.0
```

## 根因

1. **OHOS 存储沙箱拒绝 symlink(2)**（`ln -s` → EPERM，全盘）。
2. meson install 的共享库正常形态 = 实体 + 两个链接名
   （`libX.so.<major>` / `libX.so`）；链接器经**无版本名**解析 `-lX`。
3. 制品仓下载包在同盘不显病：归档中的符号链接条目解包时被物化为
   同名实体拷贝——这正是该盘上依赖包的既有形态；而**本图内源码重编
   的节点**（其 package() 在真机上执行）没有这个物化环节。
4. 于是缺口只在"消费者图内有源码重编依赖"时出现，且炸点在下游链接
   命令行（与 E492/kea 的运行期 dlopen 炸点不同）。

## 方案：generate() 预构建物化（消费者侧，幂等）

构建前扫描**全部 host 依赖包**的 libdir，对命中
`^lib.+\.so\.\d+(\.\d+)*$` 的实体，物化缺失的 `libX.so.<major>` 与
`libX.so`（实体拷贝，非符号链接）：

```python
pattern = re.compile(r"^(lib[^/]+\.so)\.(\d+(?:\.\d+)*)$")
for dep in self.dependencies.host.values():
    package_folder = dep.package_folder
    if not package_folder:
        continue
    for subdir in dep.cpp_info.libdirs or ["lib"]:
        libdir = os.path.join(package_folder, subdir)
        ...
        for entry in os.listdir(libdir):
            match = pattern.match(entry)
            if not match:
                continue
            base, major = match.group(1), match.group(2).split(".")[0]
            for name in (base + "." + major, base):
                if not os.path.lexists(os.path.join(libdir, name)):
                    shutil.copy2(full, target)   # 幂等；有 symlink 的宿主零动作
```

要点：

- 位置选 `generate()`（链接之前、依赖包已解包）；对 host 全依赖集
  扫描——重编节点是哪个由图决定，不写死包名；
- 依赖根 `cpp_info.libdirs` 为空的组件化包兜底扫描默认 `lib` 布局
  （与本包 `package_info()` 对 libarchive 的兜底同款）——避免循环体
  零次执行导致物化静默跳过；
- 非 OHOS 直接 return（宿主有正常 symlink，机制零动作）；
- `os.path.lexists` 判在位（含悬空链接）；实体拷贝形态与制品仓包在
  同盘解包后的既有形态一致；
- 名字已齐全的包零写入、零副作用。

## 验证

- gnome-recipes 2.0.4（task 2670，2026-10-14）：
  - 人工物化（对照组）后，原失败链接点 `[97/125] tools/recipe-extract`
    通过；
  - 配方机制真机复验：构建日志出现
    `materialized soname name from libgoa-1.0.so.0.0.0: .../libgoa-1.0.so.0`
    与 `...libgoa-1.0.so`（两名字），全量构建 31/31 打包通过；
  - 幂等性：重跑构建时名字已在位，零新增拷贝。

## 与近邻条目的边界

| 条目 | 面 | 与本条差异 |
|---|---|---|
| E492（zix） | 生产侧自我物化（自家包/安装树；symlink 优先、副本回退） | 本条在**消费侧**、对**依赖包目录**物化；诉求是构建期 `-lX` 可解析 |
| DRAFT-kea-hook-ping-check-3.0.3 | 自家 build()/package() 物化（meson test / dlopen 消费） | 本条触发点是下游链接失败（unable to find library），且范围=host 全依赖集扫描（不写死包名） |
| DRAFT-consumer-soname-less-deps-linktime-proxy | 消费**已发布**的无 SONAME 包（CMake 导入目标绝对路径烙印） | 本条对象是**缺链接名**（文件不在）而非缺 SONAME 属性；修法=副本补名（非 patchelf 代理）；构建系统=meson/PkgConfigDeps |
| DRAFT-14412 / DRAFT-14403 | 生产侧（Makefile 自产库无 soname / registry 包 dynstr 归一重签） | 不同侧、不同修法，互补不重叠 |

## 适用边界

- OHOS 真机（symlink(2) EPERM）上，消费者图内存在源码重编的共享库
  依赖节点；
- 判据：`unable to find library -lX` + 依赖包 libdir 中只有
  `libX.so.<全版本>` 实体；
- 若依赖包还有空文件/落盘异常（kea 条目场景），本机制不覆盖——
  那是生产侧卫生问题。

## 查重差异

- 与 E492 主干不重复：E492 修的是**自己的**产物/安装树；本条修的是
  **别人的**（依赖）包目录，时机在**链接前**；
- 与 kea 条目不重复：kea 的物化发生在自家 build()/package() 内，
  消费方是 meson test/dlopen；本条的消费方是**下游链接器**。

## 关联交付

- 本草稿与 `archives/g/gnome-recipes/2.0.4/**` 同属一次交付
  （conanfile.py generate() `_materialize_dep_sonames()`）。
- 正式 E 编号由知识库主编审核后分配。
