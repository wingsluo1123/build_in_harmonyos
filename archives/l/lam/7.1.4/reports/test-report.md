# lam 7.1.4 Test Report

Status: PASS
RC: 0
Date: 2026-10-12

## 上游测试（make check 等价验证，实际执行）

LAM 7.1.4 上游无单一 `make check` 目标；按 README 与各测试目录的实际
设计逐项执行，共 18 项用例（按"用例"口径计）。

| 项目 | 命令（cwd） | 结果 |
|---|---|---|
| hcc --showme | `hcc --showme` | PASS |
| laminfo | `laminfo`（grep LAM/MPI + 架构串） | PASS |
| lamboot | `lamboot -v`（单节点 hostfile） | PASS |
| tping | `mpirun -np 2 ./tping`（examples/tping） | PASS |
| hello | `mpirun -np 2 ./hello`（examples/hello) | PASS |
| ring | `mpirun -np 2 ./ring`（examples/ring） | PASS |
| connect | `mpirun -np 2 ./connect`（examples/connect） | PASS |
| allreduce | `mpirun -np 2 ./allreduce`（examples/allreduce） | PASS |
| spu (C++) | `mpirun -np 2 ./spu`（examples/spu） | PASS |
| mandelbrot master | `mpirun n0 ./master`（cwd 含 ./slave，按设计） | PASS |
| fault master | `mpirun n0 ./master`（fault 目录，按设计） | PASS |
| ezstart | `mpirun -np 4 ./ezstart`（200 工作项 × sleep(2)） | PASS |
| pi | `mpirun -np 2 ./pi`（examples/pi） | PASS |
| lamgrow/lamshrink | `lamgrow -n 1 localhost && lamshrink -n 1 localhost` | PASS |
| lamshrink 后 mpirun | `mpirun -np 1 ./hello`（收缩后单节点复跑） | PASS |
| Fortran (f77 hello) | `mpirun -np 2 ./hello`（examples/hello_f77） | SKIP（--without-fc） |
| Fortran (f77 ring) | 同上（examples/ring_f77） | SKIP（--without-fc） |
| Fortran (f90) | 同上（examples/f90） | SKIP（--without-fc） |

**统计：总数 18 = 通过 15 / 失败 0 / 跳过 3（全部为 Fortran，构建时
显式 `--without-fc`，属设计内跳过）。**

日志目录：`/data/storage/el2/base/cache/lam-tests/`

## 消费者测试（test_package，conan create 实测）

- `test_package/test.c`：MPI_Init/Comm_rank/Comm_size + MPI_Allreduce
  求和校验；**无 assert()**（NDEBUG 下为空操作），失败路径为显式
  fprintf + MPI_Abort。
- 运行链（conan create run17，2026-10-12，退出码 0）：
  1. `laminfo` 输出含 `LAM/MPI 7.1.4` 与 `aarch64-unknown-linux-ohos` ✓
  2. `lamboot`：`booting n0 (localhost)` → `finished` ✓
  3. `mpirun -np 1 ./test_mpi`：`LAM-SMOKE-OK: rank 0 of 1, allreduce sum 1` ✓
  4. `mpirun -np 2 ./test_mpi`：`rank 0 of 2, allreduce sum 3`（=0+1+2）✓
  5. `lamhalt`：干净拆除 ✓ → `LAM-TEST-PACKAGE-PASSED`

日志：`/data/storage/el2/base/cache/lam-conan-create-run17.log`
package_id: `21b17f8b2bc0e9511e276e3d57a23893067cefe5`
