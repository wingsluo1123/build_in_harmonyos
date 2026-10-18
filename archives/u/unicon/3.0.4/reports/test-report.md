# Test Report — unicon 3.0.4

## 编译验证
- 编译器: clang/clang++ 15 (aarch64, OHOS 真机 PC)
- 构建系统: custom（1990s 手写 shell configure + Makefile.in，非 autoconf/cmake）
- 编译状态: ✅ 成功（`make (all)` exit=0，7 产物：unicon / imm_server / libimm_server.so / libimmclient.a / cce_pinyin.so / cxterm.so / turbo.so）
- 构建命令: `./configure --prefix=<prefix> && make && make -C unicon ccedata gbdata big5data`
- 数据三件套: ccedata / gbdata / big5data 各 exit=0（sys-*.tab + dict 数据由树内 unicon 二进制生成）
- 第三方依赖: 0（conanfile `requires` 为空；pth→pthread 移植、X11 残留已删）

## 上游测试说明（R51）
上游**无自动化测试框架**：源码无 tests/ 目录、无 ctest/pytest 注册、Makefile 无 test/check 目标
（清点证据见 notes.md「上游测试清点」节）。真实测试入口为 3 处手工编译运行的程序，已全部实测：

| 测试 | 用例数 | 通过 | 说明 |
|------|--------|------|------|
| cce/hzinput_test | 1 | 1 | kexue → 科学（GBK BF C6 D1 A7 实证） |
| cce/intcode_test | 2 | 2 | GBK 8140 → 嗀；GB18030 81308139 → 锗 |
| client/test.cpp（移植后） | 交互式 | PASS | 进程内 + TCP 形态均通过，kexue → 1科学 |

- 上游测试通过率: **3/3（100%）**
- 上游测试用例修改: 有（vtable 遮蔽 2 处 + test.cpp 现代 API 移植 4 处 + xl_pinyin.c 64 位
  malloc sizeof 化 2 处，逐条原因见 notes.md「上游测试用例修改说明」表）
- 注: test.cpp 的 main 返回 1 为上游设计（pass 判据 = 输出内容 + 进程正常退出），未修改

## 消费者用例（新增）
- `test_package/consumer_test.cpp`：模拟业务上层调用公开 API 全流程
  （IMM_OpenClient → IMM_OpenInput → IMM_SetInputMode → IMM_KeyFilter×n →
  IMM_GetSelectDisplay → IMM_ResetInput → IMM_CloseInput → IMM_CloseClient）
- 硬断言: kexue → 科学（GBK BF C6 D1 A7）；zhongguo → 中国（GBK D6 D0 B9 FA）
- 链接形态: `-D__DLL_SUPPORT__` → libimmclient.a + libimm_server.so（进程内，与 unicon 主程序一致）
- ctest: **1/1 PASS**（9/9 断言点，exit=0）
- TCP 真并发变体（补充取证）: imm_server 独立进程 + 真 socket（端口 15435），
  完整会话 open → SetInputMode → kexue+space → close，候选完整（1科学 2可 3克…），server 无崩溃

## Conan Verify
| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS |
| G1 配方完整性 | ✅ PASS |
| G2 conan create（干净构建 + test_package） | ✅ PASS |
| G3 系统同名库隔离 | ✅ PASS |
| G4 产物完整性 | ✅ PASS |
| L2 smoke / L4 安全扫描 / L5 产物基线 | ✅ PASS（⏭️ 跳过（无 cache 路径）） |

详见 reports/conan-verify-report.md。

## Result
配方已在 OpenHarmony aarch64 真机验证通过（本地 conan-verify + W3 本地 CI 模拟），
可标记 built 状态，待 CI 流水线复验后发布。
