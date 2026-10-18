# Conan CMake helper 与 Ninja 的双层并发参数优先级

## 错误特征与触发条件

资源受限的 OHOS 原生构建中，配方指定 `CMake.build(cli_args=["-j4"])`，
但实际日志为 `cmake --build <build> -j4 -- -j20`。前面的 4 不是实际并发上限。
本次发现于 Viskores 1.1.1 的完整标准库与测试构建，先停止本人探索进程，再限制并发重跑。
初始参数排查与独立 zlib 对照未观察到 OOM/EAGAIN，不将它们作为该参数机制的因果证据。
后续官方 W3 在 Viskores 第755步启动SDK链接进程时实际报 Out of memory，随后无关环境
命令也 fork 失败、SSH exec 失败；该中断单独保留在软件报告，不据此反推前置-j覆盖必然导致OOM。
同一显式parallel4配置的独立完整native create此前已RC0、371/371与消费者13/13。

## 根因

Conan 的 CMake helper 把 `cli_args` 交给 CMake，同时由 `tools.build:jobs` 生成
`-- -jN` 交给原生构建器。Ninja 收到重复的 `-j` 时，最后一个生效。
`CMAKE_BUILD_PARALLEL_LEVEL` 也只是默认值，不能覆盖显式原生 `-jN`。
这不是一个只能靠观察 CPU 占用猜测的问题：完整命令和有时间戳的编译 launcher 可直接判定。

## 独立上游对照

使用官方 [zlib v1.3.1](https://github.com/madler/zlib/tree/v1.3.1) 的原始 CMake 项目，
归档 SHA256 `17e88863f3600672ab49182f217281b6fc4d3c762bde361935e436a95214d05c`。
四组均继承 `tools.build:jobs=2`，分别使用全新构建目录。每组执行 34 次翻译单元编译，
记录的是启动器并发，不是线程总数。启动器在真实编译前增加 100ms 观测延迟，
保持所有编译参数、真实编译和退出码；该延迟不是性能基准。

| 配方方法 | 真实构建命令末段 | 实测最大 launcher 并发 | zlib 上游 CTest |
|---|---|---:|---|
| `build(cli_args=["-j1"])` | `-j1 -- -j2` | 2 | 2/2 |
| 环境变量设 1 后 `build()` | `-- -j2` | 2 | 2/2 |
| `build(build_tool_args=["-j1"])` | `-- -j2 -j1` | 1 | 2/2 |
| 显式 `cmake --build . --parallel 1` | 无 helper 追加的参数 | 1 | 2/2 |

四次运行是同一套 zlib 测试的对照，不能相加宣称新增 8 个逻辑用例。
被测工具版本为 Conan 2.29.1、CMake 4.4.3、Ninja 1.13.2。
四份原始构建输出、轨迹、退出码和复跑脚本保存在[固定历史提交](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/parallel)。
当前PR保留 `1.1.1/reports/parallel/results.json` 摘要；全量证据的84文件SHA索引与取回方法见
`archives/v/viskores/1.1.1/reports/evidence.md`，可据原始事件重新计算并发。
无需修改共享Conan cache、profile、系统Ninja或其他配方。

## 推荐方法与验证

使用 helper 时把资源上限放到原生构建器参数末端：

```python
cmake.build(build_tool_args=["-j1"])
```

也可在真实构建目录显式执行：

```python
self.run("cmake --build . --parallel 1", env="conanbuild")
```

本次 Viskores 主库用显式命令限制为 4，消费者限制为 1；并行上限是构建资源策略，
不改变库运行时设备后端，也不关闭上游测试或修改断言。

```sh
python3 archives/v/viskores/1.1.1/reports/verify-evidence.py --extract <新绝对证据目录>
sh <新绝对证据目录>/parallel/run-repro.sh <独立工作目录> <OHOS-profile>
```

脚本下载原始 zlib 并验证哈希；四组各自构建、执行上游 CTest，保留原始日志和并发轨迹。
`results.json` 应为 `cli=2, environment=2, native=1, explicit=1`，且四组退出码均为 0。

## 查重与适用边界

在初始基线 `d11b98060eb650273d167f4404a9ad3ae1f0e711`，并于最终基线
`6e803c422afe521b71b50c7f0ed117f391461b6d` 复核正式 graph/doc/index 检索
`cli_args|build_tool_args|cmake --build.*-- -j|CMAKE_BUILD_PARALLEL_LEVEL` 等，
均命中 25 个文件（包含 index 与 graph/doc 重复）；不是声称关键词零命中。
逐条检查后，相关边界如下：

| 已有条目 | 其已有覆盖 | 本稿增量与可执行反证 |
|---|---|---|
| E301 | `CMake.test` 的参数传给构建器而非 CTest | 这里 `CMake.build` 接受参数且成功，问题是两层并发值的覆盖。四组 zlib 均测试成功，仍观测到 2 与 1 的区别。 |
| E426 | pico-sdk 的 host 子项目选择，示例使用 `build_tool_args` | 已有正确用法，但未解释资源限制失效的触发条件与反例。本稿补识别机制、坏方法对照和独立原始语料。 |
| E1988 | Fortran 模块依赖下的串行要求，建议环境变量 | 不否定原 Fortran/生成器场景；本稿限定 Conan+Ninja 已显式注入 `-jN` 时，环境变量不足。zlib environment 组即反证。 |
| E695 | GNU make 的 HMDFS jobserver FIFO 非致命告警 | 本稿是 Ninja 参数优先级，不涉及 FIFO，不以 make 告警作为失败判据。 |
| E092/E1655 | CMake 不认识 HarmonyOS、SONAME 规则缺失 | 本次直接复用这些既有知识，不将 Linux 平台规则另报新知识。 |

适用范围限于具有相同 helper 命令结构与 Ninja 参数语义的版本。其他生成器、
上游内部二级构建、测试自身启动的子进程需独立验证；将编译限制为 1 也不能保证整机
没有 EAGAIN/OOM。修复资源上限不等于已经解决所有编译或运行错误。

## 元信息

`authors: frj__`；`contributor_id: frj__`；`draft: true`；日期 2026-10-17。
申请知识扩展评审，是否入库与获分由委员会认定。
