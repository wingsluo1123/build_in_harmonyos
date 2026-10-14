# uefitool

UEFI 固件镜像的**解析与提取**工具集。上游
[LongSoft/UEFITool](https://github.com/LongSoft/UEFITool) 是 UEFI 固件分析领域最常用的
开源工具，提供固件卷（Firmware Volume）、FFS 文件、段（Section）三级结构的完整解析，
并覆盖多家 OEM 的私有格式。

上游构建三个可执行文件，本包只适配其中**零 Qt 依赖**的两个：

- **`uefiextract`** —— 批量解包。把固件镜像整棵树按结构落盘为目录树，并产出可读的
  文本报告（`.report.txt`）、GUID 数据库（`.guids.csv`）与完整 dump
- **`uefifind`** —— 检索。按 GUID 或十六进制 pattern 在镜像内查找，支持
  `header` / `body` / `all` 三种范围和 `list` / `count` 两种输出
- ~~`UEFITool`（GUI）~~ —— Qt6 Widgets 程序，OHOS PC 侧 Qt 为 5.15，不构建（见下）

- 上游：https://github.com/LongSoft/UEFITool
- 构建：CMake（上游根 `CMakeLists.txt`；本包改用适配侧薄 `cmake/CMakeLists.txt`）
- 依赖：无外部依赖。Brotli、LZMA、zlib、SHA-1/256/512/SM3 全部以源码内嵌在
  `common/` 下，与 38 个 C++ 源一起编成单一可执行文件
- 许可证：BSD-2-Clause
- 测试：上游**零测试**（全树无 `enable_testing()`/`add_test()`，唯一的
  `fuzzing/ffsparser_fuzzer.cpp` 是无种子语料的 libFuzzer harness）⇒
  本包自建消费者测试，用纯标准库手搓一个最小合法 FFS2 卷做真实解析

解析器覆盖面（`common/generated/` 下的专用解析器）：Intel FV/FFS 与 FIT/ACM/KEYM/ACBP、
AMI NVAR、Apple SysF、Dell DVAR、EDK2 VSS/VSS2/FTW、Insyde FDC/FDM、Phoenix FLM/EVSA、
Microsoft SLIC marker/pubkey、Tiano 与 LZMA 与 Brotli 压缩段。

## OHOS 适配

- **剥离 Qt6 GUI 是适配的前提**。上游根 `CMakeLists.txt` 只有五行，其中
  `ADD_SUBDIRECTORY(UEFITool)` 是**无条件**的，而 `UEFITool/CMakeLists.txt` 第 9 行是
  `FIND_PACKAGE(Qt6 REQUIRED COMPONENTS Widgets)`。OHOS PC 侧只有 qt5-qtbase
  （Qt 5.15），没有 Qt6 ⇒ 直接配置上游根工程必然 `FATAL_ERROR`，连两个纯 CLI 也
  编不出来。本包**新增**一个薄 `cmake/CMakeLists.txt`，只拉 `UEFIExtract` 与
  `UEFIFind` 两个子目录，`cmake.configure(build_script_folder="cmake")` 指向它；
  上游文件一个字节都不改（R34），同时把产物名钉成小写的 `uefiextract`/`uefifind`
  （上游只在 `IF(UNIX)` 分支里改名）。
- **`guids.csv` 必须随包安装**。固件卷/文件的 GUID 到可读名映射表只通过
  `UEFITool/uefitool.qrc` 的 Qt 资源打进 GUI，上游 `INSTALL()` 里没有它；而
  `UEFIExtract/uefiextract_main.cpp` 在 `main()` 首行调用
  `initGuidDatabase("guids.csv")`——相对路径，按 **CWD** 解析。剥掉 GUI 后，
  `common/guiddatabase.cpp` 在文件读失败时**静默**返回空名表：退出码不变、报告
  照样生成，只是所有可读名退化成裸十六进制 GUID 串。本包在 `package()` 里把
  `common/guids.csv` 装到 `share/uefitool/guids.csv`。
- **工具链**：`CMAKE_SYSTEM_NAME` 沿用 `Linux` 而非新造 `OHOS`，OHOS 侧由 conan
  toolchain 提供 sysroot；`CMAKE_SKIP_RPATH` 与 `CMAKE_SKIP_INSTALL_RPATH` 打开，
  避免安装期重写 RUNPATH 破坏 ELF 的 `.codesign` 签名段（E077）。
- **构建自检**：`cmake/CMakeLists.txt` 注册 3 条 `add_test`（两个 `-v`、一个
  无参数 usage 并置 `WILL_FAIL`），让 `ctest` 在零测试的上游之上至少有真实可跑的
  回归网；消费者层的 **28 条**断言在 `test_package/test.sh`（脚本末尾带
  `EXPECTED_CHECKS=28` 计数自校验，条数漂移会直接 Bail out）。
- **零告警**：真机 `conan create` 的完整日志中 `warning` 行数为 **0** —— 上游源码
  在 OHOS 的 clang 15 + libc++ 上本身不需要任何 `-Werror` 豁免；本包零补丁、
  不改任何编译 flag，也就没有靠 CFLAGS 级绕过把构建"擦干净"的余地（P007）。

## References

- https://github.com/LongSoft/UEFITool
- https://github.com/LongSoft/UEFITool/blob/new_engine/README.md — 上游对
  `new_engine` 分支与 `A*` 快照 tag 的说明
- https://uefi.org/specs — UEFI 规范（固件卷 / FFS / 段结构定义）
