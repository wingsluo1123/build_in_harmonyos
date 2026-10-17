# mlc 1.2.0 适配笔记

## 结论速览
- **上游**：`git.macaw.me/blue/mlc`（**Gitea 自建站，不是 GitHub**）—— Media Library Compiler
- **类型**：C++ / CMake
- **产物**：`bin/mlc`（musl 动态 ELF64/AArch64，707264 字节）
- **依赖**：flac 1.4.3 / lame 4.0 / taglib 2.3 / libjpeg-turbo 3.2.0 —— **全部已在仓库归档**
- **上游测试**：**0 个**（仓库无 test/tests，CMake 无 enable_testing/add_test）→ 配方里补 `mlc --help`
- **状态**：built（本地 conan create 全绿：编译 ✓ + 补的测试 ✓ + 消费者 6/6 ✓）

## 四处必须知道的坑（7 轮 CI 才打通）

### 1) CMake ≥4 不再兼容 `cmake_minimum_required(<3.5)`
上游写的是 `cmake_minimum_required(VERSION 3.0)`：
```
CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
```
→ 按报错提示给策略下限（**不改上游文件**）：
```python
tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
```

### 2) 上游用 CMake 内置模块的目标名，conan 给的是小写目标
上游：`target_link_libraries(mlc FLAC::FLAC PkgConfig::LAME JPEG::JPEG PkgConfig::TAGLIB)`
conan 的 CMakeDeps 生成：`flac::flac` / `libjpeg-turbo::libjpeg-turbo`（`PkgConfig::LAME/TAGLIB`
由 PkgConfigDeps 提供，名字一致 ✓）→ 配方里改写这两处：
```python
new = new.replace("FLAC::FLAC", "flac::flac").replace("JPEG::JPEG", "libjpeg-turbo::libjpeg-turbo")
```

### 3) conan 的 config 按**包名**命名，`find_package(JPEG)` 找不到
生成物是 `libjpeg-turbo-config.cmake`，而上游调 `find_package(JPEG REQUIRED)` → 目标
`libjpeg-turbo::libjpeg-turbo` 未定义（报 "target was not found"）→ 改成：
```python
new = new.replace("find_package(JPEG REQUIRED)", "find_package(libjpeg-turbo REQUIRED)")
```

### 4) 依赖 include 不通过目标传播；且 **LAME 的头是嵌套目录**
实测 `flactomp3.h:4:10: fatal error: 'lame.h' file not found` —— conan 的 lame 包布局是
`include/lame/lame.h`，而上游写 `#include <lame.h>`。两条要点：
- 在 **`add_executable()` 之前**注入 `include_directories(...)`（include_directories 只对之后创建的
  target 生效，放文件末尾等于没用）；
- 除 `<lame>/include` 外，还要把 **`<lame>/include/lame`** 加进搜索路径。
```python
new = new.replace("add_executable(mlc", 'include_directories(%s)\nadd_executable(mlc' % incs, 1)
```

## 实测结果（本地 conan create）
```
[patch] CMakeLists.txt：链接目标改为 conan 名、find_package(JPEG) → libjpeg-turbo、并注入依赖 include 目录
[added tests] 产物 = <build>/Release/mlc（707264 字节）
[added tests] ① `mlc --help` 打印用法 ✓（首行：Insufficient amount of arguments, launch with "--help" argument to see usage）
[ok]   产物齐备：bin/mlc 存在且可执行（707264 字节）
[ok]   ELF 头自检：真 ELF64、machine=0xB7(AArch64) ✓
[ok]   真实运行：`mlc --help` 打印用法（rc=1）
[ok]   无参调用有明确输出（rc=1）——非静默退出
[ok]   上游仓库未附许可证文件（如实记录）
[ok]   证据：bin/mlc sha256=e43036491faad79a…
checks=6 fails=0
RESULT: PASS
```

## 许可证说明（如实）
上游仓库**没有** LICENSE/COPYING 文件 → 配方与清单按 AUR/README 标注 `GPL-3.0-or-later`，但
**未随包许可证文件**（消费者校验里如实记录，不伪造）。
