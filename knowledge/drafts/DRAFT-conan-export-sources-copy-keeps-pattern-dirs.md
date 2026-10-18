# DRAFT — conan `export_sources()` 内的 `copy()` 保留 pattern 相对目录结构

> Status: DRAFT | Source: lru-dict/1.5.0 adaptation（G2/W3 干净构建失败）
> Environment: Conan 2.29.1（OHOS 适配版），HarmonyOS PC aarch64

## 1. 问题现象

配方里把随包新增的鸿蒙用例从 `test_package/` 导出，供 `build()` 并进上游
`test/` 目录一起跑：

```python
def export_sources(self):
    export_conandata_patches(self)
    copy(self, "test_package/test_ohos_lru_dict.py",
         src=self.recipe_folder,
         dst=os.path.join(self.export_sources_folder, "ohos-tests"))
```

`build()` 里按「扁平落点」读取：

```python
ohos_dir = os.path.join(self.export_sources_folder, "ohos-tests")
glob.glob(os.path.join(ohos_dir, "test_*.py"))     # → []
```

结果 `conan create` 直接在 `build()` 抛异常：

```
ConanException: HarmonyOS test case missing under
  .../_conan_home/p/lru-<hash>/s/ohos-tests — the adapted run must include
  at least one OHOS case
```

## 2. 根因

conan 的 `copy()` **保留 pattern 中的相对目录层级**，`dst` 只是前缀根，
不会把 pattern 的目录拍平。缓存目录一眼可见：

```
_conan_home/p/lru-<hash>/
  es/ohos-tests/test_package/test_ohos_lru_dict.py     ← 实际落点
  s/ohos-tests/test_package/test_ohos_lru_dict.py      ← source() 后同样带层级
```

所以 `es/ohos-tests/` 下并没有 `test_*.py`，glob 为空集。注意 `export_sources()`
本身是**成功**的（文件确实导出并进了 cache），失败发生在读取侧——
排查时容易误判为「导出没生效」。

## 3. 处置

两条等价修法，任选其一：

**①（本仓采用）保持 `dst=export_sources_folder`，读取时按 pattern 完整相对路径：**

```python
def export_sources(self):
    export_conandata_patches(self)
    # conan 的 copy() 会保留 pattern 里的相对目录结构，故落点是
    # export_sources_folder/test_package/（实测确认，不是扁平落点）
    copy(self, "test_package/test_ohos_lru_dict.py",
         src=self.recipe_folder, dst=self.export_sources_folder)

# build()
ohos_dir = os.path.join(self.export_sources_folder, "test_package")
glob.glob(os.path.join(ohos_dir, "test_ohos_*.py"))
```

**② 或让 `src` 指到子目录、`pattern` 收窄为文件名，得到扁平落点：**

```python
copy(self, "test_ohos_lru_dict.py",
     src=os.path.join(self.recipe_folder, "test_package"),
     dst=os.path.join(self.export_sources_folder, "ohos-tests"))
```

## 4. 适用边界

- **适用**：`export_sources()` / `export()` 中任何带目录的 `copy()` pattern。
- **反例**：pattern 为 `"*"` 且 `src` 已指向目标子目录时，落点就是
  `dst/<文件名>`（不引入额外层级）——此时按扁平路径读取是正确的。
- **不得**为了绕开该机制而把测试内容写成配方内的内联字符串常量：测试资产会
  失去独立执行与审阅能力，`test_package` 也无法复用同一份断言。

## 5. 查重差异

正式知识 / 图谱 / 草稿四范围检索 `export_sources` / `export_sources_folder` /
`copy()`：无既有条目覆盖 conan `copy()` 的 pattern 路径语义，故非重复。
