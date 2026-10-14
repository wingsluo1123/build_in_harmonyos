# 启用 USE_OPENMP 后并行循环仍是单线程：ATen 的 `parallel_for` 是 inline 模板，必须把 OpenMP 标志**导出给消费者**

> Draft: DRAFT-PYTORCH-21301-PARALLEL-FOR-INLINE-TEMPLATE-NEEDS-CONSUMER-OMP-FLAG
> Stem: `pytorch-2.13.0.1-parallel-for-inline-template-needs-consumer-omp-flag` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-PYTORCH-21301-PARALLEL-FOR-INLINE-TEMPLATE-NEEDS-CONSUMER-OMP-FLAG
- **严重度**: 2
- **类别**: build-system|package-info|openmp|performance
- **触发工具**: conan|cmake|clang
- **阶段**: runtime

## 症状

库**自身**报告并行能力正常，但消费者代码里的并行循环实际只有一个线程：

```
at::get_num_threads()      -> 20        # 库说 20 个 worker
omp_get_max_threads()      -> 20
ATen parallel backend      -> OpenMP    # configure 已确认切到 OMP
```

同一段消费者代码：

```cpp
std::set<std::thread::id> ids;
at::parallel_for(0, 10000, 1, [&](int64_t b, int64_t e) {
    std::lock_guard<std::mutex> g(m);
    ids.insert(std::this_thread::get_id());
});
// ids.size() == 1      <-- 期望 20，实际 1
```

而且**加不加 `-fopenmp` 编译消费者，结果完全不同**：加了是 20，不加是 1。

## 根因分析

`at::parallel_for` / `at::parallel_reduce` **不是**库里的普通函数，而是
`aten/src/ATen/Parallel-inl.h`（经 `ParallelOpenMP.h`）里的 **inline 模板**——
每个使用它的翻译单元都会**各自实例化**一份，里面的 `#pragma omp parallel` 也就在
**消费者的 TU** 里展开。若该 TU 编译时没有 OpenMP 标志，编译器不认识这个 pragma，
**静默忽略**（不报错、不警告），循环体便退化为串行。

因此"库里编进 libomp 了"并不够：库内部那些同样用该模板的代码会并行，但**消费者**调用时
不会。官方 libtorch 的 CMake 包在有 OpenMP 时正是靠向消费者传播编译标志解决这一点，
而纯自建 Conan 配方容易漏掉。

## 判定方法

用"同一库、同一调用、只改消费者编译标志"做 A/B：

| 消费者的 TU | `at::parallel_for` 观测到的线程数 |
|---|---|
| 不带 `-fopenmp` | 1 |
| 带 `-fopenmp` | 20 |

两次调用的是**同一个 `libtorch_cpu.so`**（可用 sha256 核对），因此差异只可能来自
消费者 TU 的实例化，而不是库。

## 处置

在配方的 `package_info()` 里把编译标志导出给消费者：

```python
self.cpp_info.cflags.append("-fopenmp=libomp")
self.cpp_info.cxxflags.append("-fopenmp=libomp")
```

**只需编译标志，不要再加链接库**：若 OpenMP 运行时已静态链入 `libtorch_cpu.so`
（可用 `llvm-nm -D` 确认 `omp_*` / `__kmpc_*` 是**定义**符号而非未定义），消费者的
目标文件会直接解析到该 .so 里的实现；此时若再往链接行上加第二个 libomp，反而会引入
"一个进程两个 OpenMP 运行时"（经典 `OMP: Error #15`）风险。
