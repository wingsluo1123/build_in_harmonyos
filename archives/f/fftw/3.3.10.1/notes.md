# fftw 3.3.10.1 适配笔记

`3.3.10.1` 是上游 FFTW 3.3.10 的 R37 适配修订版本；源码版本和源码 URL
保持 3.3.10，仅 Conan 包版本递增。

## 编译环境
- 构建系统: cmake（autotools 失败后改用）
- 编译日期: 2026-04-26
- 编译器: clang/clang++
- 状态: built（Conan CMake 配方和消费者测试通过）

## 编译步骤
1. 下载源码 `https://www.fftw.org/fftw-3.3.10.tar.gz`
2. 使用上游 CMake 构建，不修改或替换 `config.guess`/`config.sub`
3. CMake 配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..`
4. `make -j$(nproc)`
5. `make install`
6. 默认 `shared=False` 安装 `libfftw3.a`、头文件、pkg-config 文件和 CMake 配置文件；`shared=True` 时安装共享库

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Autotools configure 失败 | 旧 config.guess/config.sub 无法识别 OHOS | 当前配方改用上游 CMake 构建，不替换源码文件 |
| 2 | CMake policy 警告 | CMake 版本策略不兼容 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | 官方 `bench -s 32x64` 长时间不结束 | OHOS 头文件定义 `CLOCK_SGI_CYCLE`，但运行时 `clock_gettime(CLOCK_SGI_CYCLE, ...)` 返回 `EINVAL`；FFTW 未检查返回值并反复重新计时 | 检查 SGI cycle clock 的运行时返回值，失败时回退到 `CLOCK_MONOTONIC`，保留默认 `FFTW_MEASURE` 语义 |
| 4 | shared 消费者的 `DT_NEEDED` 写入 Conan 缓存绝对路径 | OHOS 的 CMake 通用平台规则缺少 SONAME 参数；直接启用规则又会让上游 `VERSION/SOVERSION` 生成 HMDFS 不支持的版本软链 | 在 OHOS toolchain 补齐 SONAME/runtime linker flags，并让源码同时识别 CMake 的 `OHOS`/`HarmonyOS` 系统名后跳过 `VERSION/SOVERSION`，产出一个带 `SONAME=libfftw3.so` 的真实共享库 |

## 源码修改
当前配方应用两个补丁：

- `patches/0001-use-monotonic-clock-on-ohos.patch`：在
  运行时先尝试 `CLOCK_SGI_CYCLE`，调用失败时回退到 `CLOCK_MONOTONIC`；
  支持 SGI cycle clock 的平台仍沿用原计时源。补丁同时在 OHOS/HarmonyOS
  CMake 构建中跳过会生成版本软链的 `VERSION/SOVERSION` 属性。配方补齐 OHOS CMake 缺失的
  SONAME/runtime linker flags。旧的 Autotools `config.guess`/`config.sub` 补丁仍保留在
  基线版本 `../3.3.10/patches/` 中，作为历史诊断证据。
- `patches/0002-fftw-version.patch`（本轮新增）：上游 3.3.10 tarball 的
  `CMakeLists.txt` 将 `FFTW_VERSION` 写死为 `3.3.9`（Autotools 的
  `configure.ac` 则按 `FFTW_MAJOR_VERSION.FFTW_MINOR_VERSION` 正确推导
  3.3.10），导致 `configure_file(fftw.pc.in)` 生成的 `fftw3.pc` 中
  `Version:` 字段为 3.3.9，`pkg-config --modversion fftw3` 报告错误版本。
  补丁将 `set (FFTW_VERSION 3.3.9)` 改为 `set (FFTW_VERSION 3.3.10)`，
  使 pkg-config 与 CMake config 版本均与真实发布版本一致。

## 测试框架与工具链验证说明（2026-08-01 probe 复核）

- 实际 TMPDIR：`/storage/Users/currentUser/tmp`（probe 根
  `/storage/Users/currentUser/tmp/fftw-probe`）；`/tmp` 为只读文件系统。
- 编译器：clang 15.0.4，target `aarch64-unknown-linux-ohos`；工具链位于
  `/data/service/hnp/bin/{clang,llvm-readelf,llvm-objcopy,llvm-ar,llvm-strip,binary-sign-tool}`。
- 构建系统差异：CMake 路径为本配方采用路线（需
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`）；Autotools 路径在 OHOS 上依赖
  `config.guess`/`config.sub` 补丁，且 `config.status` 内部 `(umask 077;
  mkdir)` 生成的 0700 临时目录在 HMDFS 上会因属主映射（20001006 vs 执行
  uid 20020083）触发 `Permission denied` —— 属于环境权限怪癖，CMake 路径
  不受影响。
- ELF 签名：`python3 -m scripts.ohc.sign_elf <lib>` 成功（生成 `.codesign`
  节），签名后消费者程序仍可正常运行。
- 动态/静态产物：`libfftw3.so`（SONAME 由配方补齐，NEEDED 仅 `libc.so`）
  与 `libfftw3.a` 均验证可用；`shared=False` 为默认，与 manifest 一致。
- 数值验证（自写消费者程序，shared 与 static 各一套，均 ALL_PASS）：
  - C2C forward n=16 vs naive DFT：max_err=3.696e-14
  - C2C forward+backward roundtrip：max_err=3.972e-15
  - R2C n=16 Parseval：3.553e-15
  - R2C→C2R roundtrip：max_err=5.329e-15
  - planner 创建/执行/销毁 ×1000：max_err=9.312e-12
- 上游测试入口：CMake `BUILD_TESTS=ON` 构建 `bench`
  （`tests/fftw-bench.c` + `libbench2/verify-*.c`）成功；`make check`
  （Autotools）入口存在但未在本轮执行（见"注意事项"中的真机入口说明）。

## 依赖版本
无外部依赖

## 注意事项
- 当前 OHOS 配方使用上游 CMake 构建。
- 需要设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
- 真机官方 CTest 入口保持为 `bench -s 32x64` 和 `bench -s ib256`，不得用
  `-oestimate` 改变测试语义。
- shared 消费者必须记录 `NEEDED libfftw3.so`，static 消费者不得包含该项；
  打包的共享库必须只有一个真实文件、无版本软链且 SONAME 与文件名一致。
- fftw3.pc 的 `Version:` 字段经 0002 patch 后为 3.3.10；若未来升级到
  3.3.11+ 需复核上游 CMakeLists.txt 的 FFTW_VERSION 是否同步（见
  knowledge draft E263）。
- 单精度 `fftw3f/3.3.9.1` 不在本 PR 范围；其 ohpcd 发布 404 状态作为独立
  后续依赖项跟踪，不混入本 PR。
---

**编译结束**: 2026-08-01 14:47
**最终状态**: built
