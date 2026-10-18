# E429 — OHOS 制品仓 vtk 未启用 ParallelMPI，依赖 vtkMPIController 的库无法编译该模块

- **来源**：liggghts 3.8.01 适配（2026-10-15，平台任务 id 8465，HarmonyOS PC / OHOS 6.0 / aarch64）
- **领域**：OHOS 依赖侧能力缺口（制品仓包功能不完整）→ 下游库编译/运行受损
- **同类但不同**：本条不是「库自身不可移植」，也不是「musl 差异」；根因在已发布依赖包的构建选项上

## 现象

两条看起来无关的日志，实际同一根因，且分别在**编译期**与**运行期**出现：

1. 编译期（库把 VTK 输出放在开关后，默认打开时）：

   ```text
   src/dump_vtk.cpp:xx:10: fatal error: 'vtkMPIController.h' file not found
   ```

   LIGGGHTS-PUBLIC 3.8.0 的 10 个 VTK 源文件中 **8 个**如此失败；
   打开该开关的默认构建（`Makefile.mpi` 里 `LMP_INC = -DLAMMPS_GZIP -DLAMMPS_VTK`）在 OHOS 上直接不可编译。

2. 运行期（把开关关掉、库其余功能全部编译通过之后）：

   ```text
   ERROR: Invalid dump style (../output.cpp:634)
   ```

   上游 `examples/LIGGGHTS/Tutorials_public` 的 28 个教程算例，**原样运行只有 1 个通过，其中 19 个卡在
   `dump … custom/vtk` / `mesh/vtk`**（其余 8 个为上游其它原因，逐条见 liggghts 配方 notes.md）。这一步最容易被误判成「适配没做好」——实际上是样式未被
   注册（编译期该模块没进来），与仿真本体、接触模型、积分器全部无关。

## 根因

VTK 的并行能力来自 **ParallelMPI 模块**，它只在构建期 `VTK_MODULE_ENABLE_VTK_ParallelMPI=YES`
且 MPI 可用时才产出，落到包上就是两样东西：

- 头文件 `include/vtk-9.4/vtkMPIController.h`
- 库文件 `lib/libvtkParallelMPI-9.4.so`

OHOS 制品仓（ohpcd）已发布的 `vtk/9.4.1`**两者皆无** —— 即该包构建时未启用 MPI。
下游凡是直接引用 `vtkMPIController` / `vtkMultiProcessController::PartitionController`
的代码（VTK 的并行收集与分区语义都在这），在 OHOS 上就编译不过。
这是依赖侧能力缺口，**与下游库的可移植性无关**，也无法在配方层面合法修复。

## 判定方法（先探测，再决定）

```sh
VTK_P=$(conan cache path vtk/9.4.1)
ls "$VTK_P"/include/vtk-9.4/vtkMPIController.h   # 无 => ParallelMPI 未启用
ls "$VTK_P"/lib/libvtkParallelMPI*               # 无 => 同上
```

两条都缺时：**不要**尝试打开下游库的 VTK 开关，直接走推荐方案。

## 解决方案

### 推荐方案：关闭可选的 VTK 输出，其余功能全开，并把原因写进测试口径

库自带开关时（LIGGGHTS/LAMMPS 的 `-DLAMMPS_VTK`），按「最小可验证改动」处理：

1. 关闭该开关，保留全部其余功能（MPI 并行、全部接触模型、网格、插入、SPH、热传导等）。
2. 上游测试按 R51 三步法如实清点，并**逐条**区分失败原因：
   依赖该输出样式的算例单列「依赖能力缺口」，不混进「适配问题」。
3. 只去掉输出请求行（`dump … custom/vtk|mesh/vtk|mesh/gran/VTK`），**仿真本体一字不改**，
   作为「去掉该输出后功能完好」的证据口径另行统计。
4. 在 PR 正文与 notes.md 写明：这是依赖侧缺口 + 复现命令 + 后续补齐路径。

### 回退方案：先把依赖补上，再打开开关

需要该功能真实可用时，必须由依赖侧发布一个**启用 MPI 的 vtk 修订版本**
（`VTK_MODULE_ENABLE_VTK_ParallelMPI=YES` + MPI 可用，按 R37 加版本后缀），
再重新打开下游库的 VTK 开关。这是依赖链上游的任务，属于正常的拓扑序（先 A 后 B），
不是本库配方能绕过的东西。

### 禁止做法

- ❌ 自造一个同名 `vtkMPIController` 类或空头文件顶替 VTK 的 MPI 控制器；
- ❌ 用 `ifdef` 把 VTK 输出整个 stub 掉却声称「功能完整」；
- ❌ 把 27/28 的失败算例写成「环境问题」一笔带过，不给出逐条原因。

前两者会静默产出并行语义错误的产物（评审按 R40 判伪适配）；第三者触碰赛事诚信红线
（虚报适配状态/测试通过率 → 抽验不实单条积分清零）。

## 验证

liggghts 3.8.01（HarmonyOS PC / aarch64，原生构建）：

- 关闭 `-DLAMMPS_VTK` 后：320/320 源文件编译通过；`conan create` 全流程通过（含 test_package）；
- 上游 28 个教程算例，**原样运行 1/28**（27 个失败中 19 个报 `Invalid dump style`）；
- 仅去掉 VTK dump 请求行后重跑，通过数显著上升，剩余失败项均为明确的上游原因
  （已从 3.8.0 源码删除的旧 `pair_style`、需 `-var` 传参、PASCAL/CFDEM 专用命令、需前置 restart），
  与适配无关；
- 复现：`lmp_mpi -in <deck>`，观察 `ERROR: Invalid dump style` 是否消失。

## 通用性说明

任何「依赖 VTK 并行/MPI 能力」的库都命中这一条，包括 LAMMPS 本体、其它以
`vtkMPIController` 做并行收集的仿真/后处理程序；判定与处理方式完全一致
（先探测包内容 → 库有开关就关闭并如实说明 → 需要就补依赖），
与具体库名、构建系统（手写 Makefile / CMake）无关。
