# dyncall 1.4 HarmonyOS PC 适配

用户明确授权补齐 ARM64 结构体按值调用和回调，争取 C 类。不是仅调整配方：上游 ARM64 标量调用已可运行，但缺少聚合 PCS。实现限定为小端 ELF AArch64 的普通 C 聚合及 float/double HFA；不伪称其他 PCS 或 SIMD/HVA 已支持。

## 实质修复

- 递归分类实际字段、嵌套数组和 union 重叠；HFA 最多四个同类型成员。
- 实现 HFA FP 参数/返回、普通聚合体 GPR 参数/返回、整个聚合体栈溢出、大聚合体调用者副本及独立 x8 结果指针。
- 汇编调用入口保存 x0/x1、d0–d3；回调保存相同分类所需的寄存器、x8、类型描述，C/汇编布局有编译期偏移断言。
- VM reset/free 释放大聚合体副本，聚合栈写入带容量检查。
- 默认构建共享库，保留上游 `_s` 库名契约；Conan 提供 dyncall、dyncallback、dynload 三个组件；安装 ARM64 callback thunk 头文件。

## 上游测试修正

没有删除上游用例，尤其保留原本暴露缺失功能的两个各 400 用例聚合套件。

1. `test/dynload_plain/dynload_plain.c`：使用 `dladdr(printf)` 的实际已加载 C provider，避免错误猜测 libc 别名引起崩溃。
2. `test/resolve_self/CMakeLists.txt`：未知 HarmonyOS CMake platform 上探测并显式启用 ELF executable symbol export。
3. `test/thunk/test_thunk.c`：POSIX `sigsetjmp/siglongjmp` 保存/恢复信号掩码，使连续两次故意触发的 heap/stack NX fault 都能观察，未放宽 NX。
4. `test/callf/main.c`：按 `(char)-89` 比较 plain char，保留 ARM64 默认无符号 char，不用全局 `-fsigned-char` 改 ABI。
5. 根 CMake 增加显式测试开关，使 Conan build 构建全部已注册程序；默认仍保持上游不开启测试。

## 失败与恢复

- 首个工具準备失败是 Python API `conan.cli.cli.main` 缺少 args，不是缺包；新事务改为传 `sys.argv[1:]`。gpatch/2.8 已通过 `--build=never` 从制品仓下载，只用于任务私有补丁生成，不作为本库依赖。
- 正式 W3 r1 在 CMake 根最小版本检查失败。toolchain 中设置 policy minimum 会加载太晚；改为 `cmake.configure(variables=...)` 的命令行输入，r2 成功。
- 原始失败回执均保留，不覆盖、不二次 launch 或拼接为成功。

## 补丁与正式验证

所有 20 个补丁由不改动的官方 `refresh-patch --auto` 在 POSIX 目标生成。Windows 独立 GNU patch `--fuzz=0` 干净重放，20 个修改后文件 SHA-256 与实测源码完全相同；无手写 diff。

正式 `FinishPipeline.step35_local_ci()` 在 `dyncall-official-w3-20261013-r2` 生成原始 `.ci-result.json`，完成共享包构建、5,010/5,010 上游用例、包外消费者 15 项断言及 CI L1e 破坏性反向验证。12 项事务回执与释放后进程不存在检查通过。详见 `reports/test-report.md`；平台 worker CI 与发布未执行，不能写成已发布。
