## PR 信息

- **三方库名称**：ucg
- **上游版本**：0.3.3
- **上游仓库地址**：https://github.com/gvansickle/ucg
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E010（工具能力背景）；本 PR 新增 E11425-draft-2501 KV/MD 配对草稿，最终编号由主编确认。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 2 | tests/unittests.cpp 原始 TEST_F；SomeOtherTest 是原空占位，保留但不冒称新增功能覆盖。 |
| 集成测试 | 61 | 发行包展开注册的 Autotest 组，包含性能组及原预期失败 28/30；按注册组而非单条断言计数。 |
| 其他测试 | 0 | 无其他独立注册入口；helper 与数据文件不额外计数。 |
| **合计** | **63** | 原发行包完整 testsuite 1–61 + 两项 TEST_F，inventory 和官方完整日志绑定。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 2 | 不变 | 原有两个 TEST_F 实际执行 2/2。 |
| 集成测试 | 61 | 不变 | Autotest 59 PASS + 原有 XFAIL 28/30；零 SKIP/FAIL/XPASS。 |
| 鸿蒙特有测试 | 5 | +5 | 安装后实际 ucg：version、literal、regex、case insensitive、no-match exit status。 |
| **合计** | **68** | **+5** | 原注册测试不减量，新增消费者不替代任何上游测试。 |

63/63 是原框架“预期结果检查”口径：61 项普通 PASS、2 项原有 XFAIL。
不是 63 项普通通过，也未修复上游原有 glob-precedence 缺陷。两项 XFAIL 同时
校验实际 group 日志、源行、预期/实际匹配数、空 stderr 与精确 diff；缺失命令、
崩溃和无关失败均拒绝。上游 benchmark 的 diff 是统计，不声称跨工具逐字节等价。

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. 手写 tests/arg_and_rc_handling.at 两处断言管线的 grep `--ignore-case` 改为
   等价 POSIX `-i`，正则、输出和返回码断言不变；通过原 Autom4te 从手写输入
   重新生成完整 61 组 testsuite，不直接修改生成脚本。
2. tests/atlocal.in 对可选 GNU grep 角色增加肯定版本首行检查，避免 Toybox 的
   `is not GNU grep` 被子串探测误认。保留必需系统 grep、全部组、完整原语料和十次迭代。
3. 测试执行环境通过 PROG_SCRIPT 使用实际 Python PTY，并前置 GNU coreutils
   stty，保持原 color/tty 测试的真实终端条件；helper.sh 不删断言，不伪造 script 成功输出。
4. 发行归档未携带 googletest checkout，使用已发布 gtest/1.17.0.2 编译原始
   unittests.cpp，两个 TEST_F 名称、断言与原占位均保留。

完整 Boost 1.58、Linux 4.8 源码搜索树、完整 OpenSubtitles2016 英文数据、
原 500 MB benchmark 均实测。Linux 语料并非已编译内核，不将下载 partial 或缩小
fixture 代替完整数据。两项原 XFAIL 不删除、不改成普通 PASS。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 test_package/test.py 的五项安装消费者用于验证 Conan 包，不申报上游无测试
补全分值。官方 L1e 移走 bin/ 后测试确实失败，证明消费者实质依赖 ucg。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：63/63（100%）
- 新增测试用例通过率：5/5（100%）

上游率采用上述明确披露的预期结果检查口径（61 普通 PASS + 2 原 XFAIL）。
OHOS arm64、Clang 15、Conan 原生构建，jobs=1。r14 唯一 launch，全 12 阶段
验证及释放 PASS，官方 W3_local_ci exit0。
W3 完整日志 SHA256：`97b5b8efa505489bdd0a80e3d2535809aed1a9ddebb4b8015ae955751d761e77`。
安装 CI 包二进制 SHA256：`4d6980b9e76aaeb85773078deeb4b148ea6e47d567f2f1ac77b5e4426887ac3a`。
官方 finish 原生 RC1 仅有后置 step5b/step8；不称 aggregate finish 全部通过。
旧 r13 误识别消费者输出而整体 FAIL，保留原证据，不追认旧事务。
当前不宣称比赛 worker CI、平台 AI Review 或制品发布已通过。

---

## 补充说明

- 关联 Issue：#3940
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/ucg-0.3.3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务 #11425，本 PR 仅含 ucg 与 E11425 配对知识草稿。四范围查重后新增
  否定版本 banner 误注册工具角色的可复用机制、修复与边界；肯定 banner 不代替
  工具能力实测。HD1–HD4 当前证据均不匹配，不因数据体积、耗时或修复次数申报路径 C。
  所有依赖使用已发布制品。合并后由平台 /release 发布，PR 阶段不自行上传。


### 2026-10-14 当前 CI 修复

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

当前真机事务 `ucg-ci-repair-w3-20261013-r103`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `8808e1df9896a4d70d37ba1318d946f7e9adc8f1dccdca0c1fc4503fb6923c61`。上游 63 项和消费者 5 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
