# IGMPlot 3.17 适配笔记

## 上游信息

- 官方下载：http://igmplot.univ-reims.fr/download/IGMPlot-3.17.zip
- 官方样例：`samples/01_example` ~ `samples/24_example`，共 35 组输入
- 官方运行脚本：`source/scripts/IGMPLOT_test_samples.py`
- 构建系统：`source/Makefile`
- 主产物：`source/IGMPLOT`

## OHOS 适配点

1. 上游 Makefile 把 `CppCompilerExec` 写死为 `g++`。补丁改为 `?=`，使
   Conan profile 的 `tools.build:compiler_executables.cpp` 可以注入 OHOS
   clang++。
2. 上游默认启用 OpenMP。OHOS 基础工具链不提供 OpenMP 运行库，因此配方调用
   `make OpenMP=NO`，源码本身已有 `No_OpenMP` 条件分支。
3. 上游默认 `-Werror`。新版 clang 会把历史代码中的 misleading-indentation
   等格式告警升级为错误；补丁只移除 `-Werror`，没有关闭普通 `-Wall`，也不
   修改算法逻辑。
4. `NCISolver.h` 在 OHOS clang 下需要显式包含 `<sys/time.h>`，否则
   `struct timeval` 类型不完整。

## 验证

上游没有 `make check`，但提供覆盖 35 组输入的官方运行脚本。配方在
`build()` 中先按 CI 档把 20 组秒级样例复制到 `samples-ci/`，再把该目录交给
官方脚本（脚本与样例内容均未修改），最后自行校验输出：必须恰好 20 行以
`OK` 结尾且 0 行 `KO see`——官方脚本自身不会在样例失败时返回非零，因此不能
只依赖其退出码。

未纳入 CI 的 15 组样例属于分钟~小时级网格计算，实测数据（x86-64 基线）：
`test08/09/10/16` ≈ 88s，`test23` ≈ 100s，`test11/12/14/17/20/21/22/24/34/35`
> 120s（`test11` 单样例约 1 小时）。`conan create` 在 CI 上的预算是 3600s，
而协作者不得修改 `ci/config/build_timeouts.txt`（审查规则 21），所以这些样例
保留在 `samples/` 中供手动执行，实测数据在 PR 描述中逐条列出。

消费者测试再用官方最小样例（水二聚体）验证安装后的可执行文件、`Done` 日志
与 `igm.vmd`/`mol-dgInter.cube`/`mol-dgIntra.cube`/`mol-igm.dat` 四类输出。

## 已知边界

- CI 覆盖的是官方样例的秒级档（20/35）；重计算样例（配体-蛋白、多肽、
  SELF/SELFATOMIC 等）需要单独的长时任务验证，未纳入本次 CI 通过条件。
- 上游样例默认串行执行，配方未引入并行，避免 CI worker 上出现内存峰值。
