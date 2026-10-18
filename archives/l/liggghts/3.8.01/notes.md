# liggghts 3.8.01 适配笔记

## 编译环境

- 构建系统：手写 Makefile（LAMMPS 风格 `src/Makefile` → `src/MAKE/Makefile.mpi`）
- 编译日期：2026-10-15
- 目标：HarmonyOS PC / OHOS 6.0 / aarch64 / clang 15 / libc++（CI worker 上 build = target 原生构建）
- 本机验证：**鸿蒙 PC 原生构建 + 原生执行**（本机 `conan create`，2026-10-15，用时 1142s；
  另有一轮 Windows 侧交叉编译 + WSL/QEMU 执行的早期验证，见下方「本机验证」）
- 状态：built（本机 `conan create` 已完成 补丁→编译→打包 + test_package 通过；制品发布由 CI 流水线完成）

## 版本号说明

平台任务（id 8465）指定版本 **3.8.01**，但上游公开版本是 **3.8.0**：

- `src/version_liggghts.txt` = `3.8.0`
- `release-notes.txt` 标题 = `Release notes for LIGGGHTS-PUBLIC, version 3.8.0`
- GitHub 标签最高为 `3.8.0`，不存在 `3.8.01` 标签

因此按 R37「上游版本 + 适配修订」把上游 3.8.0 的适配版本发布为 `liggghts/3.8.01`，
`conandata.yml` 中的源码 URL 指向上游官方 3.8.0 发布归档。

## 编译步骤（配方实际执行）

```bash
make -j1 mpi \
  SHELL="$CONFIG_SHELL" \
  CC="<tools.build:compiler_executables:cpp>" LINK="<同上>" \
  CCFLAGS="-O2 -fPIC -Wall -Wno-unused-result -I<boost/include>" \
  LINKFLAGS="-O2 -fPIC" LIB="" SIZE="<llvm-size 或 :>" \
  LMP_INC="-DLAMMPS_GZIP -DSUPERQUADRIC_ACTIVE_FLAG -DNONSPHERICAL_ACTIVE_FLAG" \
  VTK_INC="" VTK_PATH="" VTK_LIB="" \
  PKG_INC="-I<zlib/include>" PKG_PATH="-L<zlib/lib>" PKG_LIB="-lz" \
  MPI_INC="-I<mpich/include>" MPI_PATH="-L<mpich/lib>" MPI_LIB="-lmpi …"
```

关键点：

| 变量 | 为什么必须显式传 |
|---|---|
| `SHELL` | `src/Makefile` 顶部写死 `SHELL = /bin/bash`，OHOS 镜像没有该路径；用 `CONFIG_SHELL` 覆盖 |
| `LIB=""` | `Makefile.mpi` 默认 `LIB = -lstdc++`，OHOS 用 libc++，会导致链接失败 |
| `VTK_INC/PATH/LIB` | `Makefile.mpi` 默认带上 VTK 6.2 的 `-I/usr/include/vtk-6.2` 与一串 `-lvtk*`，本目标不启用 VTK（见下文） |
| `LMP_INC` | LIGGGHTS 的「模型包」不是 Makefile target，而是编译宏；此处对齐上游 `Makefile.auto` 对 `USE_SUPERQUADRICS="ON"` 的默认配置 |
| `PKG_*` | `-DLAMMPS_GZIP` 打开 gz 输入/输出支持——**其实现是 `popen("gunzip -c …")` / `popen("gzip > …")`，运行期需要镜像提供 `gzip`/`gunzip`**，而不是 zlib。zlib 按上游 `Makefile.mpi` 的 `PKG_*` 传入；本库只在 `image.cpp` 的 `#ifdef LAMMPS_PNG` 分支里引用 zlib（本构建未启用），因此**产物既不引用 zlib 符号、也不链 libz**（`DT_NEEDED` 无 `libz.so`，R26 的"系统同名库不得动态链接"自然满足） |
| `SIZE` | 上游链接后执行 `size <exe>`；优先取与编译器同目录的 `llvm-size`，找不到时用 shell 内建 `:` 跳过打印（不影响产物） |

## 依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| mpich | 5.0.1 | MPI 并行（`make mpi` 必需） |
| zlib | 1.3.2.1 | 上游 `Makefile.mpi` 的 gz 支持参数。实测产物**未引用 zlib**（`-DLAMMPS_GZIP` 走 `popen(gunzip)`；zlib 只在未启用的 `LAMMPS_PNG` 分支被引用），`DT_NEEDED` 里没有 `libz.so` |
| boost | 1.91.0.1.4 | 超二次曲面接触几何需要 beta 函数 |

`boost` 的必要性有实测依据：OHOS libc++ 15 不提供 C++17 特殊数学函数——
`probe.cpp` 用 `-std=c++17` 编译 `std::beta(2.,3.)` 报 `no member named 'beta' in namespace 'std'`，
预处理宏里也没有 `__STDCPP_MATH_SPEC_FUNCS__`，于是 `math_extra_liggghts_superquadric.cpp`
会落到上游代码里的 boost 分支（这正是上游注释「requires boost」的含义）。

## 未启用 VTK 输出（重要，含证据）

上游 `Makefile.mpi` 默认 `LMP_INC = -DLAMMPS_GZIP -DLAMMPS_VTK`，本适配**没有**启用 `-DLAMMPS_VTK`，原因不是规避难度，而是依赖能力缺口：

1. LIGGGHTS 的 VTK 输出样式（`dump custom/vtk`、`dump vtk`、`dump mesh/vtk` 等）
   依赖 VTK 的 **ParallelMPI 模块**：`dump_vtk.h` 无条件 `#include <vtkMPIController.h>`，
   `dump_vtk.cpp/custom_vtm.cpp/local_gran_vtk.cpp/mesh.cpp` 里使用
   `vtkMPIController::New()`、`vtkMultiProcessController::PartitionController()`。
2. 已发布的 OHOS 制品 `vtk/9.4.1` 未启用 MPI：
   - `include/vtk-9.4/` 下没有 `vtkMPIController.h`（只有 vtkXMLP*、vtkParallelCore 等）
   - `lib/` 下没有 `libvtkParallelMPI-9.4.so`
   - 直接用该包编译 `dump_vtk.cpp` 的实测报错：`fatal error: 'vtkMPIController.h' file not found`（8/10 个 VTK 源文件同一原因）
3. 影响范围：`examples/LIGGGHTS/Tutorials_public` 的 **28 个教程算例全部**使用
   `dump … custom/vtk` 等样式输出后处理文件，因此在本目标上原样运行时会在该命令处报
   `ERROR: Invalid dump style`。

**结论**：要启用 VTK 输出，需要制品仓提供一个「启用 MPI 的 VTK」修订版本
（`-DVTK_MODULE_ENABLE_VTK_ParallelMPI=YES` 且 MPI 可用）。这属于依赖侧工作，
不在本库适配范围内；本适配因此按「DEM 求解器 + MPI + 全部接触模型 + 内置
`dump custom` / `dump mesh/stl`」交付，并在 R51 测试清点中逐项说明。

> 补充：LIGGGHTS 自带的 `dump custom`（文本）与 `dump mesh/stl` 不依赖 VTK 库，
> 可正常使用；`test_package` 的功能测试即跑完整 DEM 求解流程（接触力积分）。

## 源码修改（4 个补丁）

| # | 文件 | 类型 | 内容 |
|---|---|---|---|
| 0001 | `src/dump_mesh_vtk.{h,cpp}` | portability | 这是全库唯一未受上游 `LAMMPS_VTK` 开关保护的 VTK 源文件（同族 `dump_mesh_vtm.*`、`dump_vtk.*` 都有保护）。补上同样的 `#if defined(LAMMPS_VTK)` 守卫后，不启用 VTK 时才能编译 |
| 0002 | `src/utils.h` | portability | `Utils::int_to_string()` 把 `std::ostringstream() << …` 的临时流绑定到非 const 左值引用，libc++/clang 直接报错。改为与紧邻的 `double_to_string()` 相同的具名流写法 |
| 0003 | `src/finish.cpp` | portability | `neighbor->lists[m]->numneigh > 0` 中 `numneigh` 是 `int *`，指针与 0 的有序比较在 clang 下是错误。按当前 LAMMPS 的写法改为真值判断 |
| 0004 | `src/region.cpp` | bugfix | `Region::reset_random()` 里 `fprintf(screen, …)` 未判空；用 `-screen none`（screen == NULL）运行时，任何触发区域随机数重置的插入类 fix 都会空指针崩溃（ASan 栈：`reset_random → fix_insert_pack.cpp:204 → FixInsert::setup`）。按全库统一写法补 `&& screen` 判空 |

补丁均为机器生成的 unified diff（`diff -u`，`-p1` 可干净应用），非手工编写；
不含 `__OHOS__` 之类平台分支，对上游其他平台保持透明。

> `conandata.yml` 里 0001–0003 标 `portability`、0004 标 `bugfix`：0004 修的是上游在 `-screen none`
> 下的真实空指针缺陷（带 ASan 栈与反向验证），语义上属 bugfix 而非可移植性改动，故有意区分；
> 若评审要求完全统一为 `portability`，可一并调整（不影响补丁内容）。

## 上游测试清点（R51）

**清点**：LIGGGHTS-PUBLIC 3.8.0 不含 `tests/` 目录，Makefile 也没有 `check` 目标
（可用 target：machine/clean/stubs/makelib/makeshlib/…）。上游自带的验证资产是

```
examples/LIGGGHTS/Tutorials_public/**/in.*     -> 28 个公开教程算例
```

**运行**：在鸿蒙 PC 上**原生**逐个执行（共享机器、串行；逐条结果与每例原始 stdout 均留档）。
两轮复核：

- 第一轮（`sh/deck-census.sh`）：所有算例统一 `lmp_mpi -in <deck>`，**每例 300s 上限**；
- 第二轮（`sh/deck-refix.sh`）：对"可能是复核方法问题"的算例，改用**上游自己文档化的调用方式**重跑。

| 口径 | 通过 | 说明 |
|---|---|---|
| 原样运行（上游算例一字不改） | **1/28** | 其中 19 个在 `dump … custom/vtk` 处报 `Invalid dump style`（VTK 依赖缺口，见上） |
| 仅去掉 VTK dump 请求行，统一 `-in` 调用、300s 上限 | 18/28 | 第一轮结果 |
| 同上 + 按上游文档化方式调用、长算例给足时间 | **22/28（78.6%）** | 第二轮把 3 个"失败"转 PASS（见下），第三轮长算例跑完（3444s）；其余 6 项终判不可修 |

去掉输出请求行后通过的名单（18 个，第一轮）：`in.liggghts_init`、`in.chute_wear`、
`in.cohesion`、`in.noCohesion`、`in.newModels`、`in.conveyor`、`in.heatGran`（heatTransfer_1/2 各一次）、
`in.hydrogel_default`、`in.hysteresis`、`in.noHysteresis`、`in.sph_2`、`in.meshGran`、`in.packing`、
`in.insert_stream`、`in.mesh_tet`、`in.movingMeshGran`、`in.multisphere`

第二轮**额外转 PASS 的 3 个**（都未修改任何算例，改的只是"按上游文档的方式去跑"）：

| 算例 | 第一轮为何失败 | 修正后的调用（依据来自上游文件本身） | 结果 |
|---|---|---|---|
| `insert_stream/in.insert_stream_reset_timestep` | 缺前置 restart | `insert_stream/` 是**两段式教程**：`in.insert_stream:62` 写 `post/liggghts.restart`，本算例 `:13` 读它；需先跑第一段 | **PASS**（阶段1 6s 写出 restart → 阶段2 40s 通过） |
| `superquadric/in.particle_particle` | 未传 `-var` | 算例头部注释原文要求用 `-var` 定义 `blockiness1`/`blockiness2`/`angle` | **PASS**（0s） |
| `sph_1/in.sph_1` | 300s 上限把 20 万步级算例截断 | 放大单例上限 | **PASS（1285s）** |

配方 `build()` 内执行其中 10 个（覆盖 restart/初始化、网格磨损、黏结、新接触模型、运动网格、
热传导、多接触、网格壁面、堆积插入），本机 `conan create` 实测 **10/10 通过**；
其余通过项因 CI 时间预算未纳入。

**长算例（跑完即通过）**：`hydrogel_multicontact/in.hydrogel_multicontact` 本体为 4×`run 30000`
+ init（约 12 万步），本机实测速率约 33 步/s；**给足预算单独长跑后 rc=0 通过（用时 3444s）**。
前两轮 300s / 3600s 上限被截断时，它均**捕获 SIGTERM 并正常写出 forced restart**
（`SIGINT/SIGTERM caught - Writing restart on next occasion and quitting after that`），
说明前两轮的"未通过"只是本地预算不足，不是失败。

**终判不可修（6 项，上游/耦合侧原因，逐条给证据）**：

| 算例 | 原因 | 证据 |
|---|---|---|
| `ParScale/…/in.DEM` | **不是可运行算例**：CFD 侧参数文件（只有 `variable … equal …`，无 `run` 段） | 输出仅版本横幅，rc=0 |
| `ParScale/…/in.liggghts_run` | **需 CFDEM/PASCAL 耦合工作流** | 该 deck 声明 `processors 2 1 *`（`:23`）而 init 写 restart 时是 `processors 1 1 *`（`:19`）→ 单 rank 报 `Could not create 3d grid of processors`；**用 `mpiexec -n 2` 复测该报错消失**，随即停在 `Invalid fix style: "couple/pascal"`——该 fix 仅定义于可选包 `src/PASCAL/fix_pascal_couple.h:29`（上游默认 `MAKE/Makefile.user_default` 未启用该包），且该 deck 目录自带 `pascal/`（`in.pascal`/`settings/`/`genPascalInput.m`）即 CFD 侧求解器，**不在本仓库内** |
| `ParScale/…/pascal/in.pascal`（2 个） | 同上（PASCAL 耦合侧输入） | 使用 `particle_mesh nGridPoints …`；`particle_mesh` 在 LIGGGHTS 源码中 **0 命中**，非本库命令集 |
| `ParScale/heatTransferBed_paScal/in.liggghts` | 教程与源码版本不匹配（且属耦合侧目录） | `fix_template_sphere.cpp:199` 只接受 `constant` 分支，`random` 直接报 `invalid radius random style` |
| `contactModels/in.oldModels` | 上游已移除该样式 | deck `:18` 请求 `pair_style gran/hertz/history`；该样式在 3.8.0 源码中 **0 命中** |

> 结论：**不存在"因为适配不成功"而未通过的算例**。未通过项全部是
> ①复核方法（已修正 3 项，全部转 PASS）、②算例耗时（1 项，已量化）、
> ③上游自身或 CFDEM/PASCAL 耦合侧（6 项，证据见上）。

## 本机验证（鸿蒙 PC 原生，2026-10-15）

本机 `conan create` 全流程（补丁 → 编译 → 打包 → test_package），rc=0，用时 1142s：

- 产物 `bin/lmp_mpi`：`ELF 64-bit LSB pie executable, ARM aarch64`，
  `interpreter /lib/ld-musl-aarch64.so.1`；`NEEDED` = `libmpi.so.12`、`libpmi.so.0`、
  `libc++_shared.so`、`libc.so`（**无 `libz.so`**：产物不引用 zlib）；`BIND_NOW` + PIE
- 320 个源文件编译通过；包内 `LICENSE` + `bin/lmp_mpi`
- `build()` 内上游算例回归 **10/10 通过**（见上「上游测试清点」）
- `test_package` **通过**（消费者测试）：`step=1000 atoms=125 ke=0.0018542278`
  （与下方早期 WSL/QEMU 轮结果**逐位一致**，确定性算例可跨环境复现）
- `test_package/check_ohos.py` **通过**（**鸿蒙特有测试·产物属性**，16 项断言，0 失败）：
  产物为 AArch64 ELF、`ET_DYN`(PIE)、`PT_INTERP=/lib/ld-musl-aarch64.so.1`；
  `DT_NEEDED` 全部是裸 SONAME（无绝对路径）且**不含 libz**（产物不引用 zlib；系统同名库未被动态链接，R26）；
  `BIND_NOW` 已置；包内 `bin/lmp_mpi` 与 `licenses/LICENSE` 对 group/other 可读；
  `lmp_mpi -h` 在 OHOS 加载器下真实启动并打印横幅与用法
  （注：LIGGGHTS 的 `-h` 按上游约定 `exit(1)`——`src/error.cpp` 的 `Error::done()` 结尾即 `exit(1)`；
  `--help`/`--version` 不是它的选项，这也是 CI L2 冒烟用 `--help` 报 WARN 的原因）
- `test_package/test_ohos_runtime.sh` **通过**（**鸿蒙特有测试·真实运行时行为**，5/5，不是静态检查）：
  ① **gz 压缩数据文件**：同一个算例跑两遍——一遍读明文数据、一遍读 gzip 后的数据（`read_data *.gz`），
     断言两次的**最终热力学行逐位相同**（`step=1000 atoms=125 ke=0.0018542278`），即 gz 通路产出的物理量
     与明文完全一致（T1a 明文跑通 / T1b gz 跑通 / T1c 两行相同）。`-DLAMMPS_GZIP` 的实现是
     `popen("gunzip -c …")`（`src/read_data.cpp`），因此本项同时验证"编译期打开了 gz 支持"与"镜像运行期提供 `gunzip`"；
  ② **`-screen none` 下 insert/pack 回归（补丁 0004）**：自包含算例 `test_ohos_insert_none.in`
     （`fix insert/pack` + 6 面墙，120 颗粒 100 步）用 `-screen none` 运行通过。
     该算例触发 `Region::reset_random()`；**反向验证**：在 scratch 副本里撤销补丁 0004 重建的对照产物
     在同一算例上 **rc=134 中止（无任何输出、无完成横幅）**——即向 NULL `FILE*` 写入的典型死法；
     打补丁的产物 rc=0 并打印完成横幅。补丁 0004 由此有了自动化覆盖（此前 W4 审计曾指出它无随包用例）；
  ③ **两个 MPI 进程**：`mpiexec -n 2` 跑同一确定性算例，日志出现 `on 2 procs`——
     本包就是 MPI 构建，并行通路在目标机上真实可用。
- 28 个上游教程算例复核：原样 **1/28**；仅去掉 VTK dump 请求行 **22/28**
  （第一轮统一 `-in` + 300s 上限得 18/28；第二轮按上游文档化调用方式再转 3 个；
  第三轮长算例给足预算跑完 1 个。其余 6 项为上游/耦合侧不可修项，逐条见上「上游测试清点」。
  复核脚本与逐条结果见本机 `sh/deck-census.sh`、`sh/deck-refix.sh`，不随 PR 入仓）

### 接触模型组合数（说明，避免被误判为适配裁剪）

上游 `src/Makefile` 的 `.DEFAULT` 规则（任何 `make <machine>` 都走它）固定调用
`Make.sh style` + `Make.sh models`（**不带** `models_full`）。`Make.sh:215-257` 在
组合数 3240 > 上限 1200 时按 `res < 30 && 切向模型 != OFF` 过滤，因此本机构建日志出现
`You have 3240 model combinations. (limit = 1200)`，生成的 `src/style_contact_model.h`
含 **119** 条 `GRAN_MODEL(...)`。这是**上游默认行为**，适配侧未做任何裁剪
（未改 whitelist、未打补丁触碰该生成逻辑）；模型包本身通过
`-DSUPERQUADRIC_ACTIVE_FLAG -DNONSPHERICAL_ACTIVE_FLAG` 全开
（产物含 154 个 superquadric 符号，`lmp_mpi -h` 列出 `superquadric`/`granular_superquadric`）。

## 早期验证记录（Windows 交叉编译 + WSL/QEMU）

### 1. 交叉编译 + 产物检查

- `lmp_mpi` 7.29 MB，`ELF 64-bit LSB pie executable, ARM aarch64`，
  `interpreter /lib/ld-musl-aarch64.so.1`
- `NEEDED`：`libmpi.so.12`、`libc++_shared.so`、`libc.so`（**无 `libz.so`**：产物不引用 zlib）；
  `BIND_NOW` + PIE（RELRO/NX 属性满足 L4 安全扫描）
- 320 个源文件全部编译通过；全库 `-fsyntax-only` 扫描 320/320 通过

### 2. QEMU 实际运行

本机 QEMU（aarch64 用户态）实际执行 OHOS 产物，需要两点环境补充（均为本机环境问题，与产物无关）：

1. **可执行位**：Windows 侧工具链写出的文件没有 `+x`，QEMU 会静默失败（rc=1）。`chmod +x` 后正常。
2. **OHOS libc 扩展符号**：本机用 Alpine musl 作为动态加载器（`ohos-musl-setup`），
   它不导出 OHOS libc 的 `mallinfo`/`backtrace`/`backtrace_symbols`。
   本机验证时额外链接了一个仅含这三个空实现的本地 shim（`work/local-shim/`，
   **不进入交付物**，真机由系统 libc 提供真实实现），并因此单独生成
   `lmp_mpi_qemu` 测试副本——交付的 `bin/lmp_mpi` 不含该 shim。

验证命令与结果：

```bash
# test_package 功能测试（等价于 CI 中 conan create 的 L2）
$ bash test_liggghts.sh
[test] engine      : /home/dev/task14-liggghts/ohos-testpkg/bin/lmp_mpi
[test] final thermo: step=1000 atoms=125 ke=0.0018542278
[pass] lmp_mpi ran the granular deck to step 1000 with 125 particles
```

```bash
# 上游教程算例（VTK dump 行已按上文说明处理）
见完成报告中的实测通过率表
```

### 3. 本地 `conan create`

本机在 WSL 内跑通了 `conan create`（源码 URL 换成本地已下载 tar 包，因为 WSL 无法访问 GitHub；
`-j1` 临时放宽为 `-j8` 仅为本机提速）：补丁应用、编译、打包全部通过。
该过程暴露并修复了两个只在真实 conan 流程中出现的问题：

1. `self.conf.get("tools.build:compiler_executables:cpp", …)` —— 该 conf 是 dict 型，
   必须整体读取后取 `cpp` 键；
2. 用 conan 的 `copy()` 复制目录名的写法不会复制目录内容（改用就地构建）。

## 注意事项

- `-screen none` 会走到上游若干「未判空的 `fprintf(screen, …)`」路径。补丁 0004 修的是
  `Region::reset_random()` 这一处：ASan 栈显示它由**插入类 fix**（`fix insert/pack`）触发。
  **该补丁现有随包自动化用例覆盖**：`test_ohos_runtime.sh` 的 T2 用自包含算例
  `test_ohos_insert_none.in`（`fix insert/pack` + 6 面墙）配 `-screen none` 运行；
  **反向验证**过——撤销该补丁重建的对照产物在同一算例上 rc=134 中止、无完成横幅，
  打补丁的产物 rc=0 并打印完成横幅。其余同类调用点保持上游原样。
- `test_package` 以 `-screen none` 运行引擎，并读取 `-log` 指定的日志文件做断言
  （不是捕获 stdout）。
- `make -j1`（R9）在 32 核本机上单线程编译约 20 分钟；CI worker 上会更快。
- 云/CI 侧若后续要跑含 VTK 输出的算例，需要先发布「启用 MPI 的 VTK」依赖。

## 需要真机确认的事项

本机为**原生 OHOS/aarch64**，`conan create`、产物执行、上游算例复核均在本机真实跑通；
以下属平台语义，只能在真机/CI worker 侧确认（与本库配方无关）：

- 依赖扫描：产物只依赖 `libmpi.so.12`/`libpmi.so.0`/`libc++_shared.so`/`libc.so`（无 `libz.so`），
  未依赖图形/硬件/系统服务库；只安装 `bin/lmp_mpi`，不产出 `.so`，系统同名库冲突（R26）风险低
- ELF 签名：真机执行需系统签名，本机不涉及签名流程
- HMDFS 语义与沙箱限制：chmod 被忽略、权限固定、不支持硬链接/符号链接、AF_UNIX pathname bind 受限
  —— 只影响「往共享目录写文件」类用例，不影响求解本体
- CI 构建预算：本包为 320 个 TU 的**单线程**构建（R9 要求 `make -j1`）+ 10 个算例回归。
  本机实测 `conan create` 用时 **1142s**（负载较高的共享机器上），低于默认 3600s 预算；
  若 CI worker 上机器规格不同导致超时，需维护方在 `ci/config/build_timeouts.txt` 增加
  `liggghts/3.8.01 <秒>` 条目（该文件属 `ci/`，按规范贡献者不得修改，故本 PR 未改动）
---

**编译结束**: 2026-10-17 01:47
**最终状态**: built
