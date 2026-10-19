# E429 — conan-init 按包名生成 cpp_info.libs 与库名不一致时的配方修正

> Draft by 28FE | Source: newuoa-cpp 0.1.2 R01 适配 | 2026-09-29

## 错误特征

`ohc-run.py conan-init` 生成的 `conanfile.py` 中：

```python
self.cpp_info.libs = ["newuoa-cpp"]   # 按包名推断，错误
```

而上游 CMake 项目的实际产物是 `libnewuoa.a`、导出目标 `newuoa::newuoa`。
下游 `test_package` 若按默认 `newuoa-cpp::newuoa-cpp` 链接，会因目标/库名不存在而失败
（`No rule to make target` / `cannot find -l<包名>` 类报错）。

## 触发条件

- 构建系统: CMake（conan-init 的 CMake 模板）
- 阶段: conan-init 生成配方 → 下游消费（linking / find_package）
- 场景：仓库/包名带 `-cpp`、`-c`、`-hpp` 等后缀（如 `newuoa-cpp`），或包名与上游
  `project()` / `add_library()` 目标名不一致（如 `libnewuoa.a` / `newuoa::newuoa`）

## 根因分析

`conan-init` 的 CMake 模板按包名 `{name}` 推断 `cpp_info.libs` 与默认 CMake target 名，
没有读取上游 `add_library()` / `project()` 的实际目标名。当包名 ≠ 库名时生成错误配方，
若不修正，下游消费者按错误库名链接失败。

## 解决方案

### 推荐方案

在 `package_info()` 中按实际 CMake 产物修正，同时保持 find_package 名与包名一致：

```python
def package_info(self):
    self.cpp_info.libs = ["newuoa"]                      # 实际产物库名 (libnewuoa.a)
    self.cpp_info.set_property("cmake_file_name", "newuoa-cpp")   # find_package(newuoa-cpp)
    self.cpp_info.set_property("cmake_target_name", "newuoa::newuoa")  # 实际 CMake target
    self.cpp_info.set_property("pkg_config_name", "newuoa")
```

### 禁止做法

- ❌ 保持模板默认 `cpp_info.libs = ["<包名>"]` 不做核对（下游链接必然失败）
- ❌ 为迁就错误库名而改上游 CMake target 名（污染上游）

## 验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# test_package 消费者实际链接 newuoa::newuoa 并运行：
#   ctest: 2/2 tests passed (test_newuoa_c + test_newuoa_ohos)
# 检查产物: lib/libnewuoa.a, lib/cmake/newuoa/newuoaTargets.cmake 导出 newuoa::newuoa
```

## 查重与关系

四范围查重（正式图 index.tsv / knowledge/graph / knowledge/doc / knowledge/drafts）：
- E092（CMake 不识别 HarmonyOS 平台）：平台层，非本模式 → 不覆盖
- E321（header-only lite 包 cmake_file_name/cmake_target_name 迁移）：方案机制相似
  （set_property 修正 target 名），但触发场景不同（E321 是多包同名 clash / 头文件库迁移）
  → `similar_to: E321`
- DRAFT-400（CMakeDeps 多包同名 cmake_file_name 互覆盖）：文件冲突场景，非本模式
- 无条目覆盖"conan-init 模板按包名生成 cpp_info.libs 与实际库名不一致"→ **new_draft**

七轴查重：
- exact_duplicate: false
- causal_duplicate: false
- trigger_overlap: partial（E321 同用 set_property 修正 target，但触发入口不同）
- solution_overlap: partial（修正方法涉及 cmake_target_name，机制相似于 E321）
- combination_novelty: true（conan-init 模板生成缺陷 × 包名≠库名 的组合未被既有条目覆盖）
- boundary_novelty: true（边界 = repo 名带 -cpp/-c 后缀或与 project() 目标名不一致的 CMake 库）
- test_migration_novelty: false（非测试迁移类）

## 关联条目

- 相关: [E321]
