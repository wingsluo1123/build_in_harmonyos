# DRAFT-libzc-0.4.3-r8-platform-macro-posix — R8 平台条件编译宏违规识别与 POSIX 无条件化改法

## 问题

第三方库补丁用平台条件编译宏（如 `#if defined(__OHOS__)`）包裹功能替代实现，被远端
AI Review 判定违反项目规则《欺骗性行为检测》R8「源码和 patches/ 补丁不得引入平台条件
编译宏」（`#if defined(__OHOS__)` 与 `#ifdef __OHOS__` 语义等价，`__MUSL__`/`__linux__`
等其他平台/环境宏同样违规）。本库实例：`patches/0001-lib-zc_crk_bforce.c.patch` 第 15 行
`+#if defined(__OHOS__)` 至第 76 行 `+#endif` 整段包裹 pthread 取消信号回退垫片。

## 根因

平台条件编译宏使同一份交付源码在不同平台编译出不同行为，破坏可复现性与跨平台语义一致
性：设备本机（OHOS）构建走垫片分支，其他平台走标准接口分支，补丁的真实验证面不可跨
平台迁移；且 `#ifdef __OHOS__` 类写法属于按平台分叉（platform forking），与「POSIX 适配
（用标准接口在一切平台给出等价语义）」的原则相悖。R8 要求改为不依赖平台宏的适配方式。

## 方案

1. **删除平台宏包装**：移除 `#if defined(__OHOS__)` 与配对 `#endif`（及其变体），替代实现
   无条件编译生效；禁止改用 `__MUSL__`、`__linux__`、`#ifdef OHOS` 等任何等价宏。
2. **替代实现全部使用 POSIX 标准接口**：本实例垫片用
   `sigaction`/`sigemptyset`/`pthread_kill`/`SIGUSR1`/`pthread_exit`/`__thread`/
   `sig_atomic_t`——均为 POSIX 标准，不依赖任何平台宏，所有平台行为一致。
3. **语义保持论证**：无条件生效不等于改变语义——垫片实现的是延迟取消（deferred
   cancellation）语义：`zc_pthread_cancel`=信号投递、`zc_pthread_testcancel` 在既有取消点
   轮询标志并 `pthread_exit()`（执行 `pthread_cleanup_push` 清理器）、`wait_workers()`
   `pthread_join()` 回收语义不变；`setcanceltype/setcancelstate` 返回 0 保持默认 deferred
   语义，不吞失败。
4. **规则对照**：新写法无 `#if/#ifdef/#ifndef` + 平台/环境宏，垫片在所有平台无条件编译、
   行为一致，非按平台分叉，故不构成 R8 违规。
5. **全量扫描**：对交付范围全部文件（conanfile.py/patches/**/test_package/**）检索
   `__OHOS__|OHOS|__MUSL__|__linux__|#ifdef|#ifndef` 类模式，给出计数与零命中（或逐项
   对照说明）证据，不只检查单个补丁。

## 验证

- 新补丁对干净上游源码 dry-run/实际应用成功（hunk 行数须与增删行一致，否则 conan
  create 报 `Failed to parse patch`）。
- 应用后源码零平台宏命中；交付态干净 `conan create` exit 0；上游测试 8/8（TEMP 机制）
  真实通过；鸿蒙特有测试 exit 0（验证垫片在新写法下仍保持 join 语义）。

## 适用边界

- 适用于所有被 AI Review R8 门禁拦截的含平台条件编译宏补丁，且替代实现可用 POSIX
  标准接口无条件表达的场景（线程取消、信号、mutex 等）。
- 若功能确实只能在特定平台提供（如内核能力），需先评估能否用无条件等价 POSIX 语义
  或构建系统级能力探测表达；无法表达时须在报告/PR 中如实说明并给出 R8 例外依据。

## 反例与限制

- 禁止：`#ifdef __OHOS__`、`#if defined(__OHOS__)`、`__MUSL__`、`__linux__`、`#ifdef OHOS`
  等一切平台/环境宏变体；禁止用「仅改注释/宏名」假装移除；禁止删除功能后吞掉失败或
  退化取消/join/cleanup 语义；禁止空壳 stub 或伪造 exit 0。
- 删除宏后必须完整复验（干净 conan create、上游测试、鸿蒙特有测试），不得因「只是去
  宏」跳过重跑。
- 补丁 hunk 头行数（`@@ -a,b +c,d @@`）必须与增删行数精确一致，删除宏包装时新增行数
  变化须同步更新，否则补丁解析失败。