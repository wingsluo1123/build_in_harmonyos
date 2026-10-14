# tm-align 20190822 适配笔记

## 编译环境
- 构建系统: 无（4 个源文件，直接调用编译器；配方内 `self.run` 编译）
- 编译日期: 2026-10-08
- 编译器: OHOS NDK clang++ 15（`/data/service/hnp/bin/clang++`），目标 aarch64-linux-ohos
- 状态: built（W3 `conan create` 通过后由 finish 置位；published 由发布流水线置位）
- 语言预检: `detect_language` 判 `cpp`（`*.cpp` 2 个，主体占比 100%，build_system=none）→ `lang-preflight` 默认口径放行。
  tarball 同时含 Fortran 版 `*.f`；本包只构建 C++ 版，不引入 gfortran。

## 源码
- 上游 TM-align / TM-score（Zhang Lab, University of Michigan），Debian orig 包 `tm-align_20190822+dfsg.orig.tar.xz`
- URL: `https://deb.debian.org/debian/pool/main/t/tm-align/tm-align_20190822+dfsg.orig.tar.xz`
- sha256: `b124e9056024e170462b61b01865dc65abad7f41b933a955ba5d84ebaddcac56`
- 内容：`TMalign.cpp` / `TMalign.f` / `TMscore.cpp` / `TMscore.f`，压缩包**无顶层目录**（`get()` 不能 `strip_root`）。
- 为什么不用上游官方站：`https://zhanggroup.org/TM-align/` 只提供**不带版本号的最新文件**（`TMalign.cpp`，2025-11 更新），
  无法复现 20190822 版本；Debian pool 是该版本唯一可校验、可复现的发布源。

## 编译步骤
1. W0：无 Conan 依赖（C++ 标准库 + libm）；`conan download tm-align/20190822 -r=ohpcd --only-recipe` 未命中，新包。
2. 上游官方构建行：`g++ -static -O3 -ffast-math -lm -o TMalign TMalign.cpp`。
3. `build()`：编译器取自 Conan conf `tools.build:compiler_executables`（R33），
   `clang++ -O3 -ffast-math -o TMalign TMalign.cpp -lm`，`TMscore` 同；Debug 构建用 `-O0 -g`。不加 `-static`（对 musl 动态产物无必要，E544 只影响本机验证）。
4. `package()`：`bin/TMalign`、`bin/TMscore`。无头文件 / 库，`package_type=application`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` / `conan-init` 把项目判成 autotools，生成 `package_type = "library"` 与 `cpp_info.libs` 的骨架 | 无构建系统文件时检测器回退默认 autotools | 手写配方：直接编译，`package_type=application`、`libdirs/includedirs=[]`、`bindirs=["bin"]` |
| 2 | 压缩包无顶层目录 | Debian 重打包把 4 个文件直接放在根 | `get()` 不传 `strip_root` |
| 3 | 本机 x86 无法运行动态 OHOS 产物；binfmt 也没有，驱动程序 `exec` 子进程失败（rc 127） | E544；qemu-user 无 binfmt 注册 | 同源码 `-static` 重链副本 + `qemu-aarch64` 实跑；测试驱动支持可选 `TM_TEST_RUNNER=qemu-aarch64` 前缀 |
| 4 | 上游缺陷：`TMalign nonexist.pdb x.pdb` 段错误（不是适配引入） | 上游未检查文件打开失败 | 不修补（超出适配范围）；测试不覆盖此路径 |

## 源码修改
无（`patches/` 为空，`conandata.yml` 无 patches 节）。

## 依赖版本
无 Conan 依赖；运行时仅 libc / libc++ / libm（NDK sysroot）。

## 上游测试清点（R51）
- 源码包仅 `TMalign.cpp` / `TMalign.f` / `TMscore.cpp` / `TMscore.f`：**无 `tests/` 目录、无 ctest / pytest、无构建系统故无 `check`/`test` 目标** → 上游测试 N=0，N′=0。
- 由 `test_package` 补真实功能测试（见下）。

## 验证结果
- 鸿蒙特有测试（rule12）：`test_package/test_tmalign.cpp`（CMake 构建的 C++ 消费者程序）生成 3 个合成 PDB（α 螺旋 `a`、其绕 Y 轴 40° 并平移 (10,-5,3) 的副本 `b`、伸展链 `c`），
  fork/exec 被测包安装的 `bin/TMalign` 与 `bin/TMscore`（不经 shell），共 7 个场景 17 项断言：
  `-v` 版本、a↔b 解析 60 残基 / 比对长度 60 / RMSD≈0 / 双 TM-score≈1、`-m` 矩阵文件反解出构造的平移与旋转、a↔c TM-score<0.5、
  `-fast -u 60`、TMscore 公共残基 60 / TM-score≈1 / GDT-HA≈1、TMscore a↔c <0.5。
- 本地实跑证据（x86 runner，E544）：同源 `TMalign.cpp` / `TMscore.cpp` 经 NDK `aarch64-unknown-linux-ohos-clang++ -O3 -ffast-math -static` 重链，
  测试驱动同样 `-static` 编译，`TM_TEST_RUNNER=qemu-aarch64 qemu-aarch64 ./test_tmalign ./TMalign ./TMscore` → `TM-align consumer test PASSED`，退出码 0（17/17）。
  **这不等于交付产物（动态链接）已实跑**；交付产物的运行时用例接入 `test_package`，由 aarch64 主机在 `conan create` 中执行，
  非 aarch64 主机（x86 W3 runner）上 `test()` 仅校验构建并告警跳过。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/TMalign` | 蛋白质结构比对（commands.json 已声明） |
| `bin/TMscore` | TM-score 评分 |

## 注意事项
- 源 URL 使用 Debian 官方 pool 的 `+dfsg` orig 包：上游官方站只发布不带版本号的最新文件，无法复现 20190822。
  本地 PF 闸 PF7（Debian 下游重打包源）命中，属官方托管例外——任务书已明确指定该 URL，在 PR 正文登记，建 PR 时使用 `--no-preflight`；同形态先例：`archives/o/oggfwd`、`archives/a/a52dec` 等。
- 任务书条件「仅在任务接受同版本 cpp 实现时选择」：本任务书明确 cpp 路线，故选 `*.cpp`，不沿用 Fortran 配方。
- 许可：源码头部为宽松许可声明（允许带声明地使用、复制、修改、分发；按「原样」提供），SPDX 无对应标识，配方写 `LicenseRef-TM-align-permissive`；包内无独立 LICENSE 文件。
---

**编译结束**: 2026-10-08 23:50
**最终状态**: built
