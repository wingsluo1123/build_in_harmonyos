# VTR — Verilog-to-Routing FPGA CAD 全流程

[VTR](https://github.com/verilog-to-routing/vtr-verilog-to-routing)（Verilog-to-Routing）
是开源 FPGA **完整 CAD 流程**：从 Verilog/SystemVerilog 描述与 FPGA 架构文件出发，
依次完成展开（elaboration）、逻辑综合与技术映射、打包（packing）、布局（placement）、
布线（routing）、时序分析与功耗估计，最终产出可用的 FPGA 实现结果。它是学术与工业界
FPGA 架构研究的标准工具链。

- 上游主仓：https://github.com/verilog-to-routing/vtr-verilog-to-routing
- 许可证：MIT（ABC、部分 benchmark 与第三方库另有各自许可证，见 `LICENSE.md` 内部逐项说明）
- 语言：C++17（CMake 构建系统）+ Python（流程脚本）
- 产物：`bin/{vpr,abc,ace,odin_ii,yosys,genfasm,vqm2blif,route_diag,rtl_number}`、
  parmys Yosys 插件、以及完整的 `vtr_flow/` 流程树（脚本 / 架构 / 基准电路 / 回归任务）

## 工具链组成

| 组件 | 作用 |
|------|------|
| **ODIN II** | Verilog 展开器（经典前端），把行为级 Verilog 展开为 BLIF |
| **Yosys + Parmys** | 新一代展开/综合前端（`WITH_PARMYS`），Yosys 负责 elaboration，parmys 插件做 partial mapping |
| **ABC** | 逻辑优化与技术映射（LUT 映射），由 VTR 的 CMake 树内构建 |
| **VPR** | 打包、布局、布线、时序分析、功耗估计（流程核心） |
| **ACE 2** | 时钟网络与功耗估计 |
| **genfasm / vqm2blif** | 比特流与网表写出工具 |
| **vtr_flow/** | 驱动全流程的 Python 脚本、FPGA 架构库、基准电路与回归任务 |

## 用法

```bash
# 单次流程：Verilog 设计 + FPGA 架构 -> 布局布线结果
python3 $VTR_ROOT/vtr_flow/scripts/run_vtr_flow.py circuit.v arch.xml -temp_dir /tmp/run

# 回归套件
$VTR_ROOT/run_quick_test.py -j4              # 冒烟（vtr_reg_basic）
$VTR_ROOT/run_reg_test.py vtr_reg_strong -j4 # 强回归
```

运行环境需设置 `VTR_ROOT` 指向包目录（`package_info()` 已导出该变量）。

## 上游测试体系

本包的上游测试分两套，彼此独立（详见 `9.0.0/test_package/MANIFEST.yml`）：

1. **C++ 单元测试（CTest）** — 4 个 Catch2 目标，126 个 `TEST_CASE`：
   `test_vpr`(80) / `test_vtrutil`(29) / `test_archfpga`(3) / `test_fasm`(14)。
   上游根 Makefile 无 `test` 目标，`make test` 转发给 CTest。
2. **VTR task 回归套件（独立 Python）** — `vtr_flow/tasks/` 下 342 个 task config，
   分属 23 个套件；`run_reg_test.py` 只认各套件的 `task_list.txt`（共 317 个 task）。
   该套件不注册进 CTest。

## OHOS 适配要点

- **源码必须用官方 release asset，不能用自动 tag tarball**：后者把
  `libs/EXTERNAL/{libcatch2,sockpp}` 两个 submodule 留成空目录（各 1 条目），
  而 Catch2 是所有单元测试目标的链接依赖 —— 用错归档等于静默砍掉整套单元测试。
  官方 release asset 内联了这两个库（639 / 153 条目）。
- **GUI 走上游官方 headless 路径**：`VPR_USE_EZGL=auto` 在 GTK3/X11 缺失时上游自己
  就会关闭 GUI 并打印 `VPR Graphics: Disabled`；上游 CI 也有 `NO_GRAPHICS` 矩阵项。
  本包显式传 `-DVPR_USE_EZGL=off` 使结果确定。**需注意上游的耦合行为**：
  EZGL 关闭时 VPR server 模式一并关闭（`vpr/CMakeLists.txt:38-52`），这是上游设计，
  与综合/打包/布局/布线/时序分析链路无关。
- **打包的是"一棵树"而不是只有 `bin/`**：`vtr_flow/scripts/python_libs/vtr/paths.py`
  从自身位置反推安装根，再按 `root/vpr/vpr`、`root/abc/abc`、`root/ace2/ace`、
  `root/build/bin/yosys` 定位工具。上游靠源码树内提交的软链接满足这些路径，
  包内必须重建同样的相对布局，否则流程起不来。
- **依赖面比看起来小**：VPR 本代**不再依赖 Tcl**（全树 `find_package(TCL)` 为 0）；
  Boost 也**不需要**（Yosys 的 `ENABLE_PYOSYS := 0`，Boost.Python 硬错误不可达）。
  实际需要的是 bison/flex（`libvqm`/`libsdcparse`/`libblifparse`/`libtatumparse` 始终必需）、
  zlib、openssl（capnproto）、Eigen3（解析布局的功能门控）、pkg-config，以及 Yosys 需要的
  tcl / readline / libffi。
- **Eigen3 是功能门控而非普通可选依赖**：找不到时上游只是"Somes features may be
  disabled"，实际会静默关闭解析布局（`-DEIGEN_INSTALLED` 不定义），因此配方显式声明它。
- **CI 构建超时**：本包单次 `conan create` 要独立编译 abc + yosys + parmys + odin_ii +
  vpr + ace2 + libs，再安装含 `vtr_flow/`（约 1.2 GB，含 benchmark 与架构库）的流程树，
  并执行 4 个单元测试目标，默认 3600s 必然在编译中途被 KILL；
  已在 `ci/config/build_timeouts.txt` 申请 `vtr/9.0.0 57600`（上限）。
