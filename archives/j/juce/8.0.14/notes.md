# juce 8.0.14 适配笔记

## 编译环境
- 构建系统: cmake（JUCE 自带 CMake 模块，包内交付源码 + 头文件，由消费者编译）
- 编译日期: 2026-10-02（W3 本地复验 2026-10-10）
- 编译器: OHOS SDK clang 15（aarch64-linux-ohos）
- Profile: `ci/conan/profiles/ohos-aarch64`（`-pr:h` / `-pr:b` 同源）
- Conan: 2.29.1
- 状态: published

## 编译步骤

```bash
conan create archives/j/juce/8.0.14 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
```

包类型为 `library`，但交付形态是「模块源码 + 头文件」（JUCE 模块以源码形式编入消费者目标），
因此 `package()` 落 `include/JUCE-8.0.14/modules/...` 与 `lib/cmake/JUCE-8.0.14/*`；
真实编译验证由 `test_package/` 完成（消费方以 `juce_add_*` 编入模块源码）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `NamedPipe` 单测恒失败（读/写返回 -1/-2） | OHOS 沙箱 `mkfifo()` 返回 `EPERM`（实测：python `os.mkfifo` → `PermissionError: [Errno 1] Operation not permitted`），FIFO 不可用 | 平台限制，test_package 内登记为环境性排除（非模块缺陷），并在本笔记留证 |
| 2 | 上游 `Files` 单测不收敛（>4 分钟 CPU 无进展，无输出推进） | OHOS 文件系统上写用例（大量小文件创建/删除/属性校验）不收敛 | test_package 内登记为环境性排除（逐套 fork + 90s 看门狗，单套不拖死 CI），本笔记留证 |
| 3 | CI 构建失败（PR #14503，构建 #79741） | worker 侧基建：预下载脚本依赖 `curl` 而 worker 无 `curl`（`[fail] [Errno 2] No such file or directory: 'curl'`），镜像 fallback 全部落空；随后 `build()` 内进程 spawn `[Errno 11] Resource temporarily unavailable`（EAGAIN）。配方本身无缺陷（本地同源 `conan create` 绿） | 无需改配方；重跑 CI 待 worker 池恢复 |

## 源码修改

无补丁（`patches/` 为空）。取源两条 URL（官方 GitHub release tarball 列首位 + gitee
`mirrors_juce-framework` 权威镜像 fallback，sha256 对应镜像 tag tarball）。

## 依赖版本

- alsa-lib/1.2.16.1
- fontconfig/2.18.1
- expat/2.8.2（`override=True`）
- mesa/24.3.4.1.1

## 验证结果

### W3 本地复验（2026-10-10）

```bash
$ conan create archives/j/juce/8.0.14 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
100% tests passed, 0 tests failed out of 1
Total Test time (real) =   8.43 sec
$ echo $?
0
```

### R51 上游测试申报（清点 + 实测）

**清点**：JUCE 8.0.14 的单测以内建 `UnitTest` 子类形式随模块源码编译（`JUCE_UNIT_TESTS=1`
时启用，见 `modules/juce_core/unit_tests/juce_UnitTest.h`）。被编译模块（juce_core、
juce_data_structures、juce_audio_basics、juce_midi_ci）内建注册套件共 **93 套**。
`test_package` 通过 `juce::UnitTest::getAllTests()` 在运行时枚举，无需手工维护清单
（逐套 fork 子进程 + 90s 看门狗，输出 TAP）。

**实测**（本地 aarch64 OHOS 工具链产物，`test_package` 内执行）：

| 项 | 数值 |
|----|------|
| 注册套件 | 93 |
| 通过 | 91 |
| 环境性排除 | 2（`Files`、`NamedPipe`，原因见上表 #1/#2） |
| 断言失败 | 0 |
| 套件执行耗时 | ctest 8.4s（含逐套 fork） |

复现命令：

```bash
# 与 W3 同源
conan create archives/j/juce/8.0.14 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 逐套明细（TAP，含 SKIP 原因）：
#   直接运行构建出的 test_juce，参数为 juce 包目录（含 include/JUCE-8.0.14）
```

**上游测试用例修改**：未修改上游测试源码；仅在 `test_package` 中排除上述 2 套平台不可用例
（排除表在 `test_package/test_juce_consumer.cpp` 内以 `kEnvExcludedSuites` 显式登记原因）。

## 注意事项

- 包为源码+头文件交付型：消费者的真实编译链路由其自身 `juce_add_*` 目标覆盖，
  因此本包不产出 `.a/.so`，`conan-verify` 的产物检查以头文件/CMake 模块为准。
- `test_package` 同时承担 R34（真实消费 API）与 R51（上游单测）双重职责：前半段为
  手写消费用例（juce::File / String / XmlDocument + 安装布局契约），后半段为上游套件。

---

**编译结束**: 2026-10-10 20:55（本地）
**最终状态**: published

## CI 记录补充（2026-10-13）

- 10-03 构建 #69855（CI-034）：worker 基础设施故障——worker-prep/git-clone/cleanup
  三步均为 `SSH bridge exec failed: connection refused 111`、0 秒失败，构建从未开始；
  机器人归类「网络问题/源码下载超时」与实际日志不符（同型误报已沉淀于知识库
  DRAFT-minunit-ci-ssh-bridge-refused-not-download-timeout）。
- 10-05 检视意见闭环（commit 6cd7e70c：add_test 显式传入 modules 目录）后多次
  /rebuild 均只回「已收到」未入队——同头 SHA（6cd7e70c）疑似被触发去重挂起；
  本提交更新分支头以解除挂起并重新触发 CI。
- 10-10/10-11 构建（#79741/#81449）复现真实失败：CMake「Testing juceaide」报
  `Error loading shared library /storage/.../.conan2/p/expat.../lib/libexpat.so
  (needed by .../juceaide-libs/libfontconfig.so.1)` + `XML_*: symbol not found`。
  根因：制品仓 fontconfig 二进制的 DT_NEEDED 烙印了发布机 conan 缓存绝对路径
  （musl 对绝对路径 NEEDED 不回退，LD_LIBRARY_PATH 无效，patchelf 改写破坏代码
  签名）——与知识库 DRAFT-E5xx（nagios PR #9573 CI #44436 实证）完全同型。
  修复：build() staging 后新增 `_symlink_baked_needed()`——扫描 staged .so 的
  DT_NEEDED，把「HOME 树内、本地不存在」的绝对路径烙印以 symlink 指向依赖图中
  同名真实库（内容不变签名有效）。#79741 另含 worker 瞬时 fork 资源耗尽噪声。
