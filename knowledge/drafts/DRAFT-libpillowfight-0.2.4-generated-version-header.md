# DRAFT — 上游构建要求生成式版本头 `_version.h` 而官方归档不含（INTERNAL_PILLOWFIGHT_VERSION）

- **软件**：libpillowfight 0.2.4
- **任务**：`libpillowfight-0.2.4-r02-full-adaptation-and-contract-bound-evidence-pc1-35-20260928T035500Z`
- **状态**：DRAFT（配对 `DRAFT-libpillowfight-0.2.4-generated-version-header.kv`）
- **编号**：`DRAFT-libpillowfight-0.2.4-generated-version-header`（待人工审核后分配正式 E 编号）

## 1. 现象

OHOS aarch64 上 `conan create` libpillowfight 0.2.4 时，`_version.c` 编译失败：

```
fatal error: '_version.h' file not found
```

（或 `INTERNAL_PILLOWFIGHT_VERSION` undeclared）。形态像缺头文件/工具链问题，
但改 profile、装包都不解决。

## 2. 根因

1. `src/pillowfight/_version.c:4` 为 `#include "_version.h"`，并返回
   `INTERNAL_PILLOWFIGHT_VERSION` 宏。
2. 该宏由 `src/pillowfight/_version.h` 定义；上游通过顶层 `Makefile` 的
   `make version` 目标（第 26 行 `echo -n "#define INTERNAL_PILLOWFIGHT_VERSION \"" >| $@`）
   在构建前生成，**未提交 git，也不在官方 release tarball 中**（实测
   `tar tzf` 无任何 version.h；源码树无 `_version.h`）。
3. `setup.py` 读不到 `_version.h` 时直接退出（"Please run 'make version' first"），
   说明生成步骤是上游构建的既定前置。

## 3. 设备可执行复现

```sh
SRC=/storage/Users/currentUser/builds/libpillowfight-0.2.4.work
find "$SRC" -name '_version.h'          # 无输出（源码树无该头）
tar tzf libpillowfight-0.2.4.tar.gz | grep -i version.h   # 无输出（归档无该头）
grep -n '#include "_version.h"' "$SRC/src/pillowfight/_version.c"
grep -n 'INTERNAL_PILLOWFIGHT_VERSION' "$SRC/src/pillowfight/_version.c"
sed -n '20,30p' "$SRC/Makefile"          # make version 目标原文
```

## 4. 处置（libpillowfight 0.2.4 实测有效）

在 `conanfile.py` 的 `build()` 中、`cmake.configure()` 之前动态生成该头：

```python
version_content = ('#ifndef __VERSION_H\n#define __VERSION_H\n'
                   f'#define INTERNAL_PILLOWFIGHT_VERSION "{self.version}"\n#endif\n')
version_dir = os.path.join(self.source_folder, "src", "pillowfight")
os.makedirs(version_dir, exist_ok=True)
save(self, os.path.join(version_dir, "_version.h"), version_content)
```

判据：`conan create` 通过；消费者测试 `pf_get_version()` 返回 `0.2.4`。

## 5. 边界与反例

- **与 E103 的区别**：E103 是 CMake 策略版本（`cmake_minimum_required 3.0–3.4` 被移除），
  用 `CMAKE_POLICY_VERSION_MINIMUM` 处理；本条是**生成物未分发**，用 build() 生成。
- **与 E284 的区别**：E284 是交叉编译缺少 target config header；本条是上游设计上
  就要求构建期生成版本头。
- **反例**：版本头已随源码/归档分发的库不需要生成；autotools `config.h.in` 由
  configure 生成的库走另一机制。
- **限制**：生成内容必须与上游 Makefile 目标格式一致（宏名、引号、版本串），
  避免"生成了但格式不对"。

## 6. 复用提示

凡 CMake/其他构建直编引用"构建期生成、未分发版本头/配置头"的 C/C++ 库，
（`make version`、手工生成的 `_version.h` 等）均适用：先在源码/归档里确认生成物
确实缺失，再在配方 `build()` 中按上游格式动态生成，配消费者测试验证版本 API。

## 7. 复现证据（本任务）

| 项 | 值 |
|---|---|
| 归档 | `libpillowfight-0.2.4.tar.gz`，sha256 `32933926d9e16c9575c262188eec98c264c4a9505b6674754fff85d1e59cd8dd` |
| 源码引用 | `_version.c:4 #include "_version.h"`、`_version.c:12 return INTERNAL_PILLOWFIGHT_VERSION` |
| 归档缺失 | `tar tzf` 无 version.h；源码树无 `_version.h` |
| 正解判据 | `conan create` 通过；`pf_get_version()` 返回 `0.2.4`（test_consumer PASSED） |
