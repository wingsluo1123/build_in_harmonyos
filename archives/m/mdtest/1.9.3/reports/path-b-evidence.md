# 路径 B 证据：并行吞吐必须先归约关键路径耗时

## 主张

屏障协调的并行阶段必须先在时间域归约所有执行单元的最大完成时间，再以总操作数除以该关键路径耗时。对 rank 局部吞吐取最大值会选择最快 rank；取算术平均也无法表达必须等待最慢 rank 的阶段吞吐。

## 生产缺陷

mdtest 1.9.3 在每个 rank 上先计算 `items * communicator_size / local_elapsed`，随后 `summarize_results()` 对这些局部速率取最大值。因此，只要各 rank 的计时窗口因调度偏斜或生产工作耗时不同，报告仍跟随最快 rank，系统性高估阶段性能。本次真机实验只把“起始 barrier 后、首个文件操作前的调度偏斜”作为确定性触发条件，不把它扩大表述为已实测慢目录或慢存储。

正确补丁在 `directory_test()` 和 `file_test()` 的正式生产路径中对耗时执行：

```c
MPI_Allreduce(&elapsed, &critical_elapsed, 1, MPI_DOUBLE, MPI_MAX, testcomm);
rate = total_operations / critical_elapsed;
```

无屏障 `-B` 模式保留 rank 局部速率语义。

## 三臂真实目标端实验

共同输入：真实安装后的 `mdtest`，MPICH 2 ranks，文件创建 4 项/rank、1 次迭代。签名 PMPI 延迟探针在 file phase 起始 barrier 已返回、rank 1 采集起始时间并执行首个文件操作之前延迟一秒；探针打印 `rank=1 wtime_call=3 usec=1000000`，三臂使用同一命令、路径与判定标准。rank 0 已开始工作并在结束 barrier 等待 rank 1，因此 rank 0 的本地 elapsed 覆盖该阶段的关键路径，而 rank 1 的采样窗口保持很短。

| 臂 | 聚合策略 | 报告速率 (ops/s) | 判定 |
|---|---|---:|---|
| A 原始实现 | 各 rank 先算局部速率，汇总取最大值 | 11208.406 | 跟随短计时窗口，严重虚高 |
| B 直觉伪修复 | 对各 rank 局部速率取算术平均 | 5291.072 | 仍不代表阶段关键路径，严重虚高 |
| C 正确修复 | 先取所有 rank 最大耗时，再计算 `8 / max_elapsed` | 7.994 | 与约 1 秒墙钟关键路径一致 |

对象 SHA256：

```text
Arm A ELF  14d226b568fcbd65c00757b788363dcc4811c61a054547e6cb9867b9a0b77919
Arm A log  fd35c62f93450a0a7bd3c774be4c12cfbfdec794488d45875e7c4476dba74b33
Arm B ELF  f7696181182a9c80147b7a9bb86cf7f2b1484e8d52a10132ef0143ba2b117cc4
Arm B log  34607d53b54530347776e501927a8d1f7d5125475318274f5a3c1540df32a2e1
Arm C ELF  f0a89a43aea34f76a46e3fe727a87613a8d5a435d9e8d501159dfa373c16e9b4
Arm C log  95bbe1049e0435f525f3f7323bdd5868fe530a496d263e697f4c8928e37f3630
Probe ELF  ccb09bc54329649011615db6df2df9389a2d7a71b023303f57ccf836b1f76076
```

原始日志和实验 ELF 不进入 PR；哈希用于绑定本次证据。Arm B 的精确源码差异保存在 `repro/arm-b-average-rate.patch`，PMPI 延迟探针源码进入 `test_package/mpi_delay.c`。

## 可重建步骤

先将 `SOURCE_TARBALL`、`MPI_ROOT`、`OHOS_TOOL_ROOT`、`ARM_ROOT` 和 `RUN_ROOT` 设为隔离环境中的对应目录。A/B 使用各自的干净源码目录，C 使用 Conan 最终包；三者均在目标端签名后执行：

```sh
# A：官方源码 + 仅 Makefile 平台补丁
mkdir -p "$ARM_ROOT/a-src" "$ARM_ROOT/b-src" "$ARM_ROOT/a" "$ARM_ROOT/b"
tar -xzf "$SOURCE_TARBALL" -C "$ARM_ROOT/a-src"
patch --fuzz=0 -p1 -d "$ARM_ROOT/a-src" < patches/0001-Makefile.patch
make -C "$ARM_ROOT/a-src" MPI_CC="$MPI_ROOT/bin/mpicc" MPICH_CC="$OHOS_TOOL_ROOT/clang"
"$OHOS_TOOL_ROOT/llvm-strip" --strip-debug "$ARM_ROOT/a-src/mdtest"
"$OHOS_TOOL_ROOT/binary-sign-tool" sign -inFile "$ARM_ROOT/a-src/mdtest" \
  -outFile "$ARM_ROOT/a/mdtest" -selfSign 1
chmod 755 "$ARM_ROOT/a/mdtest"

# B：独立官方源码 + 平台补丁 + 仓内伪修复差异
tar -xzf "$SOURCE_TARBALL" -C "$ARM_ROOT/b-src"
patch --fuzz=0 -p1 -d "$ARM_ROOT/b-src" < patches/0001-Makefile.patch
patch --fuzz=0 -p1 -d "$ARM_ROOT/b-src" < reports/repro/arm-b-average-rate.patch
make -C "$ARM_ROOT/b-src" MPI_CC="$MPI_ROOT/bin/mpicc" MPICH_CC="$OHOS_TOOL_ROOT/clang"
"$OHOS_TOOL_ROOT/llvm-strip" --strip-debug "$ARM_ROOT/b-src/mdtest"
"$OHOS_TOOL_ROOT/binary-sign-tool" sign -inFile "$ARM_ROOT/b-src/mdtest" \
  -outFile "$ARM_ROOT/b/mdtest" -selfSign 1
chmod 755 "$ARM_ROOT/b/mdtest"

# C：官方源码按 conandata 顺序应用 0001、0002 后由 Conan 重建
conan create archives/m/mdtest/1.9.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build='mdtest/*'
# 将 ARM_C 设为该次 conan create 输出的 Package folder/bin/mdtest。

# 构建并签名共同的 PMPI 延迟探针
MPICH_CC="$OHOS_TOOL_ROOT/clang" "$MPI_ROOT/bin/mpicc" -shared -fPIC -O2 \
  -o "$ARM_ROOT/libmdtest_delay.unsigned.so" test_package/mpi_delay.c
"$OHOS_TOOL_ROOT/binary-sign-tool" sign \
  -inFile "$ARM_ROOT/libmdtest_delay.unsigned.so" \
  -outFile "$ARM_ROOT/libmdtest_delay.so" -selfSign 1

# 三臂分别令 ARM_BIN 为 a/mdtest、b/mdtest、$ARM_C，并使用独立临时目录
MDTEST_DELAY_RANK=1 MDTEST_DELAY_WTIME_CALL=3 MDTEST_DELAY_USEC=1000000 \
LD_PRELOAD="$ARM_ROOT/libmdtest_delay.so" \
"$MPI_ROOT/bin/mpiexec" -n 2 "$ARM_BIN" -d "$RUN_DIR" -n 4 -i 1 -F -C
```

消费者测试先要求探针输出精确的 rank、调用序号与延迟，再把同一实验收敛为 `0 < File creation rate < 12`。回退 `0002-mdtest.c.patch` 后，安装制品重新采用短计时窗口对应的最快局部速率，同一断言稳定失败。

## 错误修复与边界

- 错误：对局部速率取最大值或算术平均；二者分别选择最快 rank 或平均倒数，不能表示阶段关键路径。共同分子且耗时为正时，局部速率最小值与最大 elapsed 数学等价，但时间域归约更直接表达阶段契约，也能自然扩展到工作量不同的场景。
- 正确：保留每个 phase 的 elapsed，在参与同一阶段的 communicator 内对 elapsed 取 `MPI_MAX`，再统一计算聚合速率。
- 不适用：无屏障且明确报告每 rank 独立吞吐；任务异步完成且产品定义不是阶段 makespan；需要分位数分布而非整体吞吐的遥测。

现代 IOR 的结果归约提供独立源码佐证：它分别对开始时间取 `MPI_MIN`、完成时间取 `MPI_MAX`，再以总操作量除以全局时间跨度，而不是归约局部速率。该证据用于说明跨项目机制，不替代本项目的目标端三臂。

## 查重结果

`draft-review E591-draft-2789` 给出 `create`：最高正式条目相似度为 0.05（E409），签名和关键词重叠均为 0。E409 是测试 ELF 离开 `$ORIGIN` 后的运行时闭包问题；E413 是固定上游测试清单中的不适用项，两者均不覆盖并行速率归约。现有 MPICH 归档只验证 collective API 可运行，也没有“时间域优先于速率域”的统计契约。
