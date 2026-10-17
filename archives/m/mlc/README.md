# mlc

- **上游**：https://git.macaw.me/blue/mlc （Media Library Compiler；**Gitea 自建站，不是 GitHub**）
- **版本**：**1.2.0**（与平台清单一致）
- **形态**：C++ / CMake（命令行工具，把无损音轨批量转成有损格式）
- **许可证**：GPL-3.0-or-later（**上游仓库未附许可证文件**，按 AUR/README 标注）
- **依赖**：flac 1.4.3、lame 4.0、taglib 2.3、libjpeg-turbo 3.2.0 —— **全部已在仓库归档**

## 归档内容

```
mlc/
  commands.json            软件级命令声明（R38：本包产出真编译的 ELF 可执行文件）
  1.2.0/
    conandata.yml          源（git.macaw.me 的 1.2.0 归档 + sha256，本地实测值）
    conanfile.py           配方（CMake + PkgConfigDeps + 四处 conan 适配 + 补的测试）
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（四处坑 + 实测输出 + 许可证说明）
    test_package/          消费者校验（6 项，全部离线）
```

## 构建要点（四处，详见 notes.md）

1. **`CMAKE_POLICY_VERSION_MINIMUM=3.5`**：CMake ≥4 移除了对 `cmake_minimum_required(<3.5)` 的兼容
2. **改写两处链接目标**：上游用模块式 `FLAC::FLAC`/`JPEG::JPEG`，conan 给的是 `flac::flac` /
   `libjpeg-turbo::libjpeg-turbo`
3. **`find_package(JPEG)` → `find_package(libjpeg-turbo)`**：conan 的 config 按包名命名，否则目标未定义
4. **在 `add_executable()` 之前注入依赖 include**，且 LAME 的头是嵌套目录（`include/lame/lame.h`），
   而上游写 `#include <lame.h>` → 需要把 `<lame>/include/lame` 也加进搜索路径

## 上游测试

**上游测试数 = 0**（仓库无 `test/`，CMake 无 `enable_testing`/`add_test`）→ 配方里补一条功能级断言：
`mlc --help`（上游 `main.cpp:20` 支持）→ 断言打印用法 ✓。

## 消费者校验

`test_package/check_mlc.py` **6 项，全部离线**：产物齐备 / ELF 头自检（ELF64、machine=0xB7）/
`--help` 真跑 / 无参调用有输出 / 许可证（上游未附 → 如实记录）/ 证据。
实测 `checks=6 fails=0` / `RESULT: PASS`。
