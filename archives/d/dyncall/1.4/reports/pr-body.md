## PR 信息

- **三方库名称**：dyncall
- **上游版本**：1.4
- **上游仓库地址**：https://dyncall.org/
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（高难度挑战候选）
- **使用知识库**：E15168-draft-D014；复用 E374 的真实签名运行边界，并相对 DRAFT-lfortran-complex32-c99-hfa-abi 新增通用 FFI 对称 PCS、整组溢出与 x8 结果知识。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 5000 | 九个上游参数化/生成套件的连续 case ID；包括两个各 400 用例的聚合调用与回调套件 |
| 集成测试 | 10 | 原生调用、C++、加载符号、进程符号、thunk、执行内存和回调等十个程序各计一个复合用例 |
| 其他测试 | 0 | 当前 ARM64/HarmonyOS CMake 配置没有其他注册入口；未注册的 x86/Windows 与原本缺失的 ARM64 syscall 不并入分母 |
| **合计** | **5010** | 19 个程序，case ID 完整盘点，来源 test/CMakeLists.txt 与各套件配置/生成源码，见 MANIFEST.yml 和 reports/test-report.md |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 5000 | 不变 | 完整执行，没有删除聚合套件、跳过或降低分母 |
| 集成测试 | 10 | 不变 | 保留原生保护测试，修正 libc provider、export 和 POSIX 信号掩码行为 |
| 鸿蒙特有测试 | 1 | 新增 | Conan 安装后包外消费者，15 项断言，真实 OHOS ELF 签名、三个组件加载、ARM64 聚合调用/回调、FP/GPR 整组溢出与 x8 间接返回 |
| **合计** | **5011** | **+1** | 新增消费者按一个复合用例计，15 项断言不混入上游分母 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. `test/dynload_plain/dynload_plain.c`：HarmonyOS musl 的猜测 libc 别名不能作为已加载 provider；通过 dladdr(printf) 获取实际 provider，保留原有加载/卸载/符号断言。
2. `test/resolve_self/CMakeLists.txt`：未知 HarmonyOS CMake platform 不提供足够的 ENABLE_EXPORTS 支持；探测 ELF export-dynamic 参数后显式启用，保留符号查询断言。
3. `test/thunk/test_thunk.c`：连续两次故意触发 NX fault 时普通 longjmp 不恢复 POSIX 信号掩码；用 sigsetjmp/siglongjmp 并正确初始化 sigaction，仍要求 heap/stack 的 SIGSEGV，不放宽 NX。
4. `test/callf/main.c`：ARM64 plain char 默认无符号；按 `(char)-89` 比较同一字节值，不修改平台默认 char ABI。
5. 根 `CMakeLists.txt` 显式测试开关令 Conan 构建全部 19 个已注册程序；未修改或重生成两个各 400 用例的聚合测试网格。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增消费者是平台/包装边界强化，不把“上游无测试”作为理由。`test_package/consumer.c` 实际链接 dyncall、dyncallback、dynload，执行小聚合体、大副本、四寄存器 HFA 返回、显式 GPR/FP 溢出、callback x8 返回、VM 错误状态及进程符号查询。`dyncall_sign.py` 在 OHOS 执行前验证签名结果，签名或执行失败均阻塞；`run_consumer.py` 只接受真实消费者成功。CI L1e 移走库与头文件后确认失败。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：5010/5010（100%）
- 新增测试用例通过率：1/1（100%）

正式 Conan 共享验证 `dyncall-official-w3-20261013-r4`，唯一 launch，12 项回执和 release/postrelease 通过。原始日志 SHA-256：`5e5c6b6ceb50105ab40a30155400d1db7e71f336600f8a439225ca1954ec1272`。原工具 FinishPipeline.step35_local_ci 生成真实结果，不手工伪造 `.ci-result.json`。

静态正式 Conan 验证 `dyncall-official-w3-20261013-r3` 同样 5010/5010、消费者 1/1，日志 SHA-256：`a3c4be42e1fe882f8b3b72ffd7baa6243f9e1cba137093cc2cadcd5116f88786`。r4 相对 r3 的测试驱动仅增加完整 N/N 输出行，ABI 源码/20 个补丁不变；各事务、输入绑定和证据独立保存，不拼接 PASS。

共享包：`dyncall/1.4#852bc5e34a41690985ea1aab44733906:0726937e17000c634ad5fc029642008575bda6b0#dca1e4b3de03d1c707bb8e3a0622bc7a`。平台 worker CI 和发布是后续阶段，不能由真机结果代替。

---

## 补充说明

- 关联 Issue：#3988，https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3988
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/dyncall-1.4
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 任务：贡献者依赖任务 #15168，已领取；上游三核心库无外部包要求。
- 高难依据：HD3_COMPLEX_ARCHITECTURE，补齐缺失的 ARM64 聚合类型分类、调用 VM、汇编返回通道、callback 元数据及对称返回帧；普通配方或平台宏无法实现该功能。只申请 C 类候选确认，分值由评审决定。
- 知识查重：四个知识目录已检索。现有 complex32 HFA 条目不覆盖通用 FFI 的递归 union/数组分类、整组参数溢出、大副本、独立 x8 和双向 callback closure；新增配对草稿而非同义复述。
- 边界：仅小端 ELF AArch64、普通 C 标量字段聚合体与 float/double HFA；不声称 Darwin/Windows、大端、SIMD/HVA、half 或显式过对齐支持；不新增上游 ARM64 raw syscall 功能。
- 默认共享库保留 `_s` 命名契约，提供三个 CMake 组件和 ARM64 thunk 公共头文件。补丁由官方 POSIX refresh-patch 自动生成，Windows GNU patch 零 fuzz 重放完全匹配实测源码 SHA-256。
- 合并后才进入 `/release` 发布；PR 校验不 upload。
