# DRAFT-kati：Go 测试 harness 的忠实 Python 移植——同正则/同顺序/同 xfail 语义 + 逐行对照表（kati 0_git20251208）

- **触发实例**：kati 0_git20251208 适配（任务 contrib-7754，2026-10-08 Windows 移植 + 真机 4 轮收敛）
- **错误签名**：`go: command not found` / 上游 run_test.go（go test 驱动）在 OHOS 无法执行
- **类别**：ohos / testing / porting / methodology
- **严重度**：2（不崩溃，但处理不当会把移植 bug 冒充平台差异，永久污染 xfail 钉单）

## 症状

kati 上游 355 个行为回归用例由 Go 源码 `run_test.go` 驱动（`go test`）。
OHOS 无 Go 工具链 → 上游测试体系整体不可运行。harness 里藏着的不是
"怎么调命令"这么简单，而是完整测试语义：

- 被测物调用参数（`make [-s] [tc] SHELL=...`）
- stdout/stderr **归一化正则链**（含非常规控制流：`Circular … dropped.`
  行先从输出抽取、置顶、再整体比对——run_test.go:131-143）
- 沙箱布局：`out/<name>/{make,kati}` **兄弟目录**（绝对路径类用例依赖）
- 执行顺序：先跑完全部 make 侧、再全部 kati 侧；同 .mk 的 testN **顺序
  共用同一目录**（run_test.go:442-486）
- xfail/TODO 语义：TODO 钉住的用例输出相等 = **XPASS = rc1**（与 FAIL
  同级使套件失败）

## 根因

要移植的是**语义而非代码**。预验证暴露的 3 处移植偏差全部属于"隐式
语义在移植时丢失"：

| # | 移植偏差 | 后果 | 对齐后 |
|---|---|---|---|
| 1 | normalize() 漏了 circularRE **前置抽取** | circular_dep 误红 | 转绿 |
| 2 | 沙箱不是兄弟目录布局 | curdir_var/realpath 类用例走偏 | 转绿 |
| 3 | testN 各自独立目录、make/kati 交错跑 | order_only2 的 MAKE-SIDE-FAIL 误红、makefile_list touch 顺序效应失真 | 转绿/正确 xfail |

若不预验证，这 3 处会被误归因为"平台差异"钉进 xfail——**移植 bug 从此
永久伪装成平台特性**。

## 方法四步

1. **逐行对照表**：按 run_test.go 函数顺序列 Go 行号 → Python 行号 +
   语义注释，作为可审计工件随 PR 提交。normalize 链逐条抄，特殊控制流
   不得简化。
2. **隐式语义显式保真**：执行顺序、沙箱共享、xfail 双向判定三类隐式
   控制流单独核对（它们是移植偏差高发区）。
3. **容器预验证做移植偏差探测器**：musl 容器（Alpine 3.20 + python3
   3.12）跑全量 → 355 用例 316/15/24，15 例失败逐个问"移植偏差还是
   平台差"。注意：容器分布不代表真机（make 版本不同分布会变），容器
   只验语义。
4. **偏差分流**：移植偏差 → 修移植代码；平台差异 → 才进 xfail 钉单。
   平台扩展点（workdir 参数化应对设备 /tmp 只读、SHELL 经 CONFIG_SHELL
   注入、python3 发现链）独立成节、注明与上游差异原因，与忠实移植部分
   物理隔离。

## 实测结果（MateBook，OHOS aarch64）

- 真机终态：total=355 pass=249 fail=0 xfail=106 xpass=0，连跑 ×2 逐字一致
- 解钉实证：第 1 轮误钉 4 项（归一化前 diff 证据），第 2 轮 gate-PATH
  取证证明归一化后双侧 EQUAL，解钉后零 XPASS——钉单证据必须取自
  归一化后的最终输出

## 适用边界

- **适用**：上游测试驱动为脚本/编译型语言源码且该语言平台不可得（go
  test 最常见；perl/pytest 驱动同理）。Go-harness 测试套件不止 kati 一家。
- **不适用**：harness 薄封装、语义可直接从 Makefile 读出的（直接读懂
  即可）；驱动依赖 CGO/原生测试二进制的部分（如实划出未覆盖面）。

## 关联

- 姊妹条目：
  `DRAFT-kati-0-git20251208-build-tool-reference-impl-differential-regression`
  （差分回归体系整体；本条目是其 harness 移植环节的展开）
- 相邻：`DRAFT-14401`（GNU diff runner 替身）、`DRAFT-14402`
  （dbus-test-runner 运行时翻译 shim）——同属"等价替换"家族，但作用于
  运行时工具；本条目作用于**测试驱动源码**，层级不同
- 关联适配 PR：kati 0_git20251208（路径 A，MR !15243）
