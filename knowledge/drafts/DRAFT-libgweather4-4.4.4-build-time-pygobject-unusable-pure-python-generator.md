# DRAFT：OHOS 上 PyGObject 是**构建期不可用**而非「没装」——meson `find_installation(modules:['gi'])` 与数据生成器 `import gi` 双双致命，装包救不了

> Draft: `DRAFT-LIBGWEATHER4-444-BUILDTIME-PYGOBJECT-UNUSABLE-GENERATOR-FALLBACK`
> Stem: `libgweather4-4.4.4-build-time-pygobject-unusable-pure-python-generator` — pairs with the same-stem `.kv`

## 错误特征

**失败点 1 —— meson setup（连配置都过不去）：**

```
meson.build:NN:0: ERROR: Could not find valid Python installation
```

对应源码行（libgweather 4.4.4）：

```meson
py = import('python').find_installation('python3', modules: ['gi'])
```

meson 会真的执行 `python3 -c "import gi"` 做探测，探测失败即 setup 失败。

**失败点 2 —— 数据生成器（配置过了、编译到一半才炸）：**

```
build-aux/meson/gen_locations_variant.py:7: ModuleNotFoundError: No module named 'gi'
FAILED: data/Locations.bin
ninja: build stopped: subcommand failed.
```

**「装包也修不好」的证据：**

```
$ python3 -c "import gi"
ImportError: Error relocating .../gi/_gi.cpython-312-aarch64-linux-ohos.so:
PyType_Ready: symbol not found
$ python3 -c "import ctypes, ctypes.util; print(ctypes.util.find_library('glib-2.0'))"
libglib-2.0.so.0          ← ctypes 正常，只有 Python C 扩展加载不了
```

制品仓里**有** `pygobject/3.58.0` 且能装上，但它的 `_gi` 扩展与目标机
CPython 3.12.9 ABI 不匹配 —— 加包、换解释器、pin 版本都改变不了，所以这是
**平台能力缺失**，不是依赖未安装。

## 根因

- `find_installation(modules:['gi'])` 把「确认 python3 存在」写成了「必须有
  PyGObject」。在 libgweather 里绑定变量 `py` **全树从未被引用**，因此
  `required: false` 是语义等价修复，不是绕过门禁。
- 生成器用 `gi.repository.GLib` 只为构造 `GLib.Variant`（序列化 Locations 数据）。
  这是**构建期**对 Python C 扩展的硬依赖，与目标运行时无关——但它跑在构建机上，
  而构建机的解释器同样装不了这个扩展。

## 解决方案

1. **解除硬依赖**（patch 0001）：

   ```meson
   -py = import('python').find_installation('python3', modules: ['gi'])
   +py = import('python').find_installation('python3', modules: ['gi'], required: false)
   ```

   改前先确认绑定变量未被引用：`grep -rn "py\." --include=meson.build .`。

2. **生成器改写成不依赖 PyGObject**（patch 0002）：把生成目标指向
   `tools/gvariant_pure.py` —— **纯标准库**自行序列化 GVariant normal form
   （无 gi、无 ctypes、无 dlopen，可复现且不受构建镜像状态影响）；
   `tools/gvariant_ctypes.py`（`ctypes` 直连被测库自己链接的那份
   `libglib-2.0.so.0`）保留为交叉验证开关 `GW_GVARIANT_BACKEND=ctypes`。

   两个实现上的硬坑（不写下来一定会再踩）：
   - **不能用 `GVariantBuilder`**：它遇 tuple 内含 `y`(byte) 槽位即返回 NULL，
     而 location 记录的 `level` 字段正是 byte。要用
     `g_variant_new_tuple` / `g_variant_new_array` 分族构造。
   - `g_variant_new_dict_entry` 的原型是两个**独立指针**
     `(GVariant *key, GVariant *value)`，不接受 children 数组；传错会在 GLib
     内部 abort 成 `g_variant_type_info_check: (0 <= index && index < 24)`。
     `{...}` 若用 tuple 构造，外层 `a{sq}` 会报
     `g_variant_new_array: assertion 'is_of_child_type' failed`。

3. **为什么不默认走 ctypes**：构建期 `dlopen("libglib-2.0.so.0")` 能否成功取决于
   **构建机镜像状态**（CI worker 上 conan 的 glib 副本可能没 `.codesign`，
   OHOS loader 校验哈希后拒载 → shim 候选路径耗尽）——表现为**设备绿、CI 红**。
   这类「CI 与设备结论不一致」要先怀疑构建期动态链接，再怀疑配方本身。

## 验证命令

```bash
grep -rn "find_installation" --include=meson.build .        # 找到 modules:['gi']
grep -rn "from gi.repository" --include=*.py .               # 找到生成器依赖
python3 -c "import gi" || echo PYGOBJECT_UNUSABLE            # 平台能力实测
python3 -c "import ctypes, ctypes.util; print(ctypes.util.find_library('glib-2.0'))"

# 生成结果必须与上游生成器逐字节一致（本包）
#   magic 3031444274684757 = 0x5747687442443130，与 gweather-private.c 的
#   db_world_get_magic 断言一致；8868 条记录逐字段 diff 全同
# 两路后端在**构建期**产出同一份 Locations.bin（GW_GVARIANT_BACKEND 由补丁后的
# gen_locations_variant.py 读取，默认 pure）
GW_GVARIANT_BACKEND=pure   meson compile -C builddir && cp builddir/data/Locations.bin /tmp/by-pure.bin
GW_GVARIANT_BACKEND=ctypes meson compile -C builddir && cp builddir/data/Locations.bin /tmp/by-ctypes.bin
cmp /tmp/by-pure.bin /tmp/by-ctypes.bin && echo CROSSCHECK_OK
```

自测要按**族**分开覆盖 tuple / array / dict-entry：只测前两个会漏掉 dict-entry
的原型错误（我第一次就是这么漏的）。

## 禁止策略

- ❌ 把 `find_installation(modules:['gi'])` 删掉或删变量——先看变量是否被引用，
  未引用才允许 `required: false`
- ❌ 靠「装 pygobject 包 / 换解释器」解决 ABI 不匹配（实测无效）
- ❌ 构建期 `dlopen` 依赖库作为**默认**路径（CI 与设备会给出不同结论）
- ❌ 只用 tuple/array 自测就宣布生成器正确（dict-entry 的错误会被漏掉）

## 关联条目

- 运行时方向：`E429-draft-B1AB`（OHOS 制品生态无 `.typelib`，依赖 GIRepository
  的**运行时**程序必然失败）、`E552-draft-9AD5`（GIR 选项化）
- 构建期 dlopen 方向：`DRAFT-E641-conan-baked-paths-relocatable-dlopen-plugins`
- 本条由 libgweather4 4.4.4 移植实测产出（PR #13996，patch 0001 / 0002 +
  `tools/gvariant_pure.py`、`tools/gvariant_ctypes.py`）
