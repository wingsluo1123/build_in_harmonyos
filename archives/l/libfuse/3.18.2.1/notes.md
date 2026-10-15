# libfuse 3.18.2.1 适配笔记

## 这个版本为什么存在

**只为发布 `shared=True` 的动态库变体。**

`libfuse/3.18.2` 在 ohpcd 上**是有制品的**，但只有一个变体：

| conan 选项 | package_id | 制品仓 |
|---|---|---|
| `shared=False`（3.18.2 的默认，也是唯一已发布） | `21b17f8b2bc0e9511e276e3d57a23893067cefe5` | ✓ 有 |
| `shared=True`（消费方如 saunafs 显式要求） | `0726937e17000c634ad5fc029642008575bda6b0` | ✗ 没有 |

conan 的兼容性回退**只放宽 settings（如 cppstd），不放宽 options**，所以消费方匹配不到静态那个、只能从源码重编 libfuse——每轮 CI 都编一次，其中一轮撞上
`ninja: fatal: posix_spawn: Resource temporarily unavailable`（机器资源耗尽）才红。
发布该变体的唯一合规途径是换版本号（R37），故有 3.18.2.1。

## 与 3.18.2 的差异

- 上游源码**完全相同**（同一个 `fuse-3.18.2.tar.gz`，sha256 未变）
- 4 个可移植性补丁**完全相同**（0001-meson-build / 0002-lib-meson-build /
  0003-lib-fuse-loop-mt / 0004-lib-fuse）
- **唯一差别**：`default_options = {"shared": True, "fPIC": True}`

## 本机实测（2026-10-14）

- `conan create` 端到端 rc=0；4 个补丁正常应用
- 产出的 package_id = `0726937e17000c634ad5fc029642008575bda6b0`
  —— **正是 CI #14023 报缺失的那一个**
- test_package：CMake 消费测试 `test_libfuse` 链接并运行成功，
  `100% tests passed, 0 tests failed out of 1`

## 消费方后续

saunafs 等消费方把 require 从 `libfuse/3.18.2` 改为 `libfuse/3.18.2.1`
（继续保持 `shared=True`）即可命中已发布制品，免去每轮的 libfuse 源码编译。

---
*编译笔记 · 2026-10-14*
