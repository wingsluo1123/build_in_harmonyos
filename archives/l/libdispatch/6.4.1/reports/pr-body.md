## PR 信息

- **三方库名称**：libdispatch
- **上游版本**：6.4.1（swift-6.4.1-RELEASE）
- **上游仓库地址**：https://github.com/swiftlang/swift-corelibs-libdispatch
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；现有 SONAME、Conan VirtualRunEnv 与测试断言知识；E549-draft-LD64 配对草稿、E550-draft-LD65 对已知 PATCHES 碰撞的完整源码保留布局，以及 E551-draft-LD66 对 E046/E223 的完整执行权限夹具及 TMPDIR 覆盖边界验证增量。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 不把单个断言或源文件数量另算用例。 |
| 集成测试 | 37 | tests/CMakeLists.txt 注册的原生 C/C++ extended CTest 运行时测试，涵盖队列、线程、定时器、IO、读写互斥和压力场景；以真实 CTest ID 清单为分母。 |
| 其他测试 | 0 | Swift overlay 未启用；Apple 专属条件未在该原生平台注册，不作为被排除的已注册测试。 |
| **合计** | **37** | shared/static 两种模式分别完整执行相同 37 项，不合并成 74 项。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 未通过拆分断言增加分母。 |
| 集成测试 | 37 | 不变 | 无测试 ID 删除、失败改 PASS 或 skipped；完整清单与 JUnit ID 相等。 |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test.c：签名后的 ARM64 安装包消费者，验证 BlocksRuntime/dispatch 的实际链接与加载、64 位回调上下文、原子完成、queue/group/once、单调定时器与数据映射。多处断言属于同一消费者用例。 |
| **合计** | **38** | **+1** | 两种链接模式分别执行 37 项上游测试和 1 项安装包消费者。 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

| 修改的测试文件 | 修改原因与内容 |
| --- | --- |
| tests/CMakeLists.txt | 保留 Release 测试断言；按真实接口能力注册线程命名测试；使用声明的 FTS 测试依赖；明确启用上游 LENIENT_DEADLINES CI 模式，并从实际后端源码容量生成测试常量。 |
| tests/dispatch_cascade.c | 受界索引显式转 double，修正 Clang 警告，保留原比较。 |
| tests/dispatch_drift.c | 同上，保留定时器校验。 |
| tests/dispatch_priority.c | 同上，保留调度优先级比较。 |
| tests/dispatch_read.c | 同上，保留读操作和性能比较。 |
| tests/dispatch_group.c | 把无人读取的共享写入改为回调内 volatile 运算；保留工作量和组完成断言。 |
| tests/dispatch_concur.c | 有限宽度队列先按 concurrent 属性创建再设置宽度，宽度一仍为 serial；用有界就绪屏障保证实际到达原期望宽度后才允许提交回调结束，保留所有队列层级、工作量和峰值断言，超时失败。 |
| tests/dispatch_read2.c | 移除未使用的 fts include，使用经检查的任务私有临时路径。以有界逐块交付确认替代10ms睡眠假设，防止管道合并相邻写入；保留320次交付及10240字节断言，超时失败。 |
| tests/dispatch_io.c | 使用声明的 FTS 包和经检查的 TMPDIR。OHOS 权限夹具使用经配方双向能力验证的临时根；原始worker TMPDIR也可能不执行DAC，不能仅保留环境变量。chmod(0) 后原C用例再次同步验证独占 open 精确返回 EACCES，再保留原异步 EACCES、256字节未写入数据及后续成功读回断言。不能执行 DAC 时明确失败，不接受成功或跳过。 |
| tests/dispatch_readsync.c | 将全员集合任务数绑定内部池容量 255，扣除原先预留的两个线程；保留 LAPS=10000、两种队列布局、全部读写互斥及并发断言。容量内验证不宣称 1280 线程同时运行。 |
| tests/dispatch_test.c | 共用测试辅助路径使用可写且私有的 TMPDIR。 |
| tests/dispatch_test.h | 测试断言在 Release 中保持启用，能力宏不伪造探测成功。 |

严格延迟模式的真实历史失败单独保留；当前通过的是上游已有的 CI 宽容延迟模式，不宣称严格性能达标。新增消费者不替代任何上游测试。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

额外的 test_package 是安装包在 HarmonyOS PC ARM64 上的公开 API 消费者验证，不属于替代上游测试或宣称上游无测试的补全情形。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：37/37（100%）
- 新增测试用例通过率：1/1（100%）

本轮当前运行输入的完整证据及日志哈希见 reports/worker-dac-ci-repair.md。正式原生Conan r12在210132上按shared/static分别执行，独立finish r9在20139上执行标准ConanVerifier及本地CI；每轮单独绑定端点、boot、输入哈希和12阶段回执，不跨失败事务拼接分母。旧r8/r7及permission-fixture-ci-repair.md保留为历史，不证明本轮输入。

源归档 SHA-256 为 `68ac837bc127ab2ca96c24bbf2fd58ebc737a8ef43656c211667540fcda62ce6`。比赛worker CI与真机、本地CI分别记录，不互相替代。没有关闭-Werror、修改系统编译器、降低期望值或跳过测试；保留上游PATCHES与15个同名补丁，仅0005/0011新增显式时序同步，其余补丁保持原字节。

## 补充说明

- 关联 Issue：#4015（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/4015）。
- 队伍名称：诶，云朵
- 申请人显示标识：@2501_91199785
- 源分支：upgrade/libdispatch-6.4.1
- 目标分支：main
- 平台任务：15204，升级任务；不重复导入或领取。
- 仅提交本库配方、15个同名自动源码补丁、测试/报告及 E549/E550/E551 配对草稿；保留源码子目录隔离，增量修复权限根选择及实测的两处时序夹具，不删除上游文件、不重组补丁或混入框架改动。
- 依赖：musl-fts/1.2.7 仅用于上游 dispatch_io 测试，已发布；核心带 bundled BlocksRuntime，未开启 Swift/DTrace。只复制、签名任务自己的测试运行时文件，不改发布依赖或系统库。
- 默认 shared，也验证 static；安装后的共享库有 basename SONAME 和有效签名，NEEDED 无任务绝对路径；没有上传制品。
- 路径 B 为候选申请，最终分类与分值以官方审核为准，不申报路径 C。测试数量、补丁数量与修复轮数不作为 C 类依据。
- 原 HEAD 的 CI91435 在 source() 因 PATCHES 文件与导出 patches/ 目录大小写碰撞失败；详见 reports/source-layout-ci-repair.md。当前修复的真机与本地 CI 已通过，但不宣称更新后平台 AI Review/worker CI 已通过；新 HEAD 双向回读与 POST_CREATE 通过后再检视/rebuild，合并后发布。
- 同一旧 HEAD 的 CI92608 已完成编译，因 HMDFS 权限夹具前提不成立而36/37；本轮修复保留原错误断言并在新机完整复验。此前210132机器的 shared-only PASS/static fork FAIL 以及201机器默认clang包装器的失败均保留，不冒充完整通过或计入本轮分母。
