# midi-parser 3.6 适配笔记

## 上游来源与版本核验

- 上游仓库: https://github.com/abique/midi-parser
- 官方标签: 无任何 tag（git ls-remote 仅有 master 与 pull refs）
- 版本核验: 取 master HEAD `ddc815b44c0cb05fa133f9630355f715daabb380`（2024-04-01 最后提交）为唯一 release commit，任务版本 3.6 据此固定
- 源码 tarball: https://github.com/abique/midi-parser/archive/ddc815b44c0cb05fa133f9630355f715daabb380.tar.gz
- SHA-256: `31df7caa9593f1f05f77da48415bd2e8f218686074c29f9d74a52d81db210cc1`

## 库特性

- 纯 C（C99）MIDI 文件解析器，无运行时分配、无文件 I/O、零依赖
- 产物: 静态库 `libmidi-parser.a` + 演示工具 `midi-dump`
- 构建系统: CMake（上游 CMakeLists.txt **无 install 规则**，配方 package() 手动复制头文件/静态库/工具）

## 适配要点

- 配方从 Autotools 模板重写为 CMakeToolchain；package() 手动打包：
  - `include/midi-parser.h` → include/
  - `*.a` → lib/
  - `midi-dump` → bin/
- `commands.json`（软件级，R38）：midi-dump 为命令行工具，声明 type=tool
- 无任何依赖 → W0/R36 依赖检查通过（requirements 为空）

## 上游测试清点（R51）

- 上游无 `tests/` 目录、无 ctest 注册、无 make check 目标
- 唯一可执行演示: `example/midi-dump.c`（midi-dump）
- 实测: 构造最小合法 SMF（MThd format0 + 单轨 MTrk: Note On/Off + EOT），
  `./midi-dump smoke.mid` 正确输出 header/track/Note On/Note Off/EOT/EOB，退出码 0

## 本地验证

- 真机 CMake 构建通过（clang 15, aarch64, OHOS）
- test_package/test.c: 真实调用库 API，内嵌最小 SMF 断言 header/track/note-on/note-off/EOT/EOB
- 鸿蒙特有测试: 同一 test 二进制在本机（鸿蒙 PC 真机, HongMeng Kernel）实际运行验证 OHOS 行为
---

**编译结束**: 2026-09-28 17:31
**最终状态**: built
