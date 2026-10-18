# Conan 2 配方加补丁时必须把 `patches/*` 写进 `exports_sources`

> Draft: `DRAFT-VCF-SPLIT-PATCH-EXPORT-SOURCES`
> Stem: `vcf-split-0.1.5-10-patch-export-sources-conan2` — pairs with the same-stem `.kv`

## 一句话

`apply_conandata_patches()` 解析 `patch_file` 时用的是 **`export_sources_folder`**，不是 `source_folder`；
所以只要 `conandata.yml` 里有 `patches:` 段，`exports_sources` 就必须覆盖补丁文件，否则 `conan create`
在 `build()` 阶段抛 `FileNotFoundError`。

## 实测现场

2026-10-15，OHOS aarch64 + clang 15.0.4，Conan 2.29.1，`vcf-split/0.1.5-10`。

`conandata.yml`：

```yaml
sources:
  url: "https://codeload.github.com/auerlab/vcf-split/tar.gz/0f2fd0a"
  sha256: "a1e9d22ac85721e248c60ed8ca09b9ee26d7dccbf2c7c8b01d441231ab77e083"
patches:
  - patch_file: "patches/0001-Makefile.depend.patch"
    patch_description: "..."
    patch_type: "portability"
```

`conanfile.py`（有问题的写法）：

```python
exports_sources = "conandata.yml"          # ← 缺 patches/*

def build(self):
    apply_conandata_patches(self)          # ← 在这里炸
```

`conan create` 输出：

```
vcf-split/0.1.5-10: Calling build()
vcf-split/0.1.5-10: Apply patch (portability): ... Makefile.depend ...
vcf-split/0.1.5-10: ERROR:
Package '0b78a14a2a5be5230f73cf0d866b255d6e70c10e' build failed
ERROR: vcf-split/0.1.5-10: Error in build() method, line 137
	apply_conandata_patches(self)
	FileNotFoundError: [Errno 2] No such file or directory:
	'/storage/Users/currentUser/.conan2/p/vcf-s77b1b6e2a5451/s/patches/0001-Makefile.depend.patch'
```

注意报错路径里的 `/s/patches/...`——`s` 是 source 目录。这个路径极易把人引向"去 source_folder 里找文件"
或"补丁内容写错了"，而真正的原因在 `exports_sources`。

## 根因（Conan 2.29.1 源码）

```python
# conan/tools/files/patches.py
def apply_conandata_patches(conanfile):
    ...
    for it in entries:
        if "patch_file" in it:
            entry = it.copy()
            patch_file = entry.pop("patch_file")
            patch_file_path = os.path.join(conanfile.export_sources_folder, patch_file)   # ← 基准是 export_sources_folder
            ...
            patch(conanfile, patch_file=patch_file_path, **entry)
```

## 修复

```python
exports_sources = "conandata.yml", "patches/*"
```

改后同一条 `conan create` 通过，导出日志会多出一行：

```
vcf-split/0.1.5-10: Copied 1 '.patch' file: 0001-Makefile.depend.patch
```

## 更快的定位手段

不要先读 `build()` 的异常，先看 `conan create` 的**导出阶段日志**：

```
======== Exporting recipe to the cache ========
vcf-split/0.1.5-10: exports: File 'conandata.yml' found. Exporting it...
vcf-split/0.1.5-10: Copied 1 '.py' file: conanfile.py
vcf-split/0.1.5-10: Copied 1 '.patch' file: 0001-Makefile.depend.patch   ← 有这行才算导出成功
```

没有 `.patch` 行 ⇒ 补丁没进 recipe 包 ⇒ `apply_conandata_patches` 必定找不到。

## 为什么容易漏

- 缺陷在 `conan export` 阶段**静默通过**，只在 `build()` 才爆发；
- 从"原本无补丁"的配方新增补丁时，改动点看起来只有 `conandata.yml` + `patches/` 两处，
  `exports_sources` 容易被当成与补丁无关的一行；
- 不本地跑 `conan create`（只做静态审查）就到不了这一步——CI 才会第一次暴露。

因此本条的处置纪律与 R51/R42 一致：**新增补丁后必须本地重跑一次 `conan create`**。
