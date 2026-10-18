# DRAFT-kati：构建工具类包的"参考实现差分"全量回归——用构建机已有的 GNU make 差分等价重实现（kati 0_git20251208）

- **触发实例**：kati 0_git20251208 适配（任务 contrib-7754，2026-10-08/09 MateBook 真机，4 轮收敛）
- **错误签名**：`go: command not found` / 上游测试驱动为 Go 源码（run_test.go）无法在 OHOS 执行
- **类别**：ohos / testing / methodology / build-tools
- **严重度**：2（不崩溃，但放弃上游测试即丢失全部行为等价性验证；有零依赖等价方案）

## 症状（真机实测）

kati（GNU make 克隆，Android 构建系统解释器）上游 355 个行为回归用例
（testcase/ 296 个 .mk 展开为 355 个 testN）经 `go test` 驱动 run_test.go
执行。OHOS 无 Go 工具链 → 上游测试体系整体不可运行。若止步于消费者
冒烟测试，"ckati 与 GNU make 行为等价"这一核心命题没有任何验证覆盖。

## 根因

构建工具类包的上游测试本质是**行为回归**：同一输入跑参考实现与被测物
各一遍，比对输出与产物。驱动这类测试不缺依赖——**参考实现（GNU make
4.4.1）本就在构建机 PATH 里**（conanbuild 注入，/data/service/hnp/bin）。
缺的只是把上游 harness 语义（调用参数、归一化正则链、执行顺序、xfail
语义）搬到本平台执行——即姊妹条目
`DRAFT-kati-0-git20251208-go-test-harness-faithful-python-port` 的移植问题。

## 方法五件套

1. **沙箱对布局**：`out/<name>/{make,kati}` 兄弟目录，workdir = 
   `<source root>/out`。相对深度（`../../../testcase/tools/...`）是
   **夹具契约**——第 2 轮曾因 workdir 挪到 build_folder 深度错位，
   find_command.mk[test1] 走偏。
2. **执行顺序保真**：先跑完全部 make 侧、再全部 kati 侧；同一 .mk 的
   testN 顺序**共用同一沙箱目录**（run_test.go:442-486）。顺序与共享
   状态本身就是测试语义——makefile_list 的 touch 顺序效应依赖它。
3. **归一化链对齐**：上游每条正则逐条移植，含非常规步骤（circular
   "Circular … dropped." 行先抽取置顶再比对，漏掉即 circular_dep 误红）。
4. **噪声剥离铁律**：只剥离零语义信息的环境噪声。OHOS bash 5.3 的
   getcwd 回退行（`shell-init:/chdir: error retrieving current
   directory: ...`）行数随子 shell 环境翻动、且零 make-vs-kati 信息，
   双侧同剥（NOISE_CWD；getcwd 正常平台为 no-op）。
   **钉单证据必须取自归一化后的最终输出**——第 1 轮用归一化前 diff
   误钉 4 项，第 2 轮 gate-PATH 取证证明归一化后双侧 EQUAL，解钉零 XPASS。
5. **xfail 显式钉单**：平台差逐条写根因入 tests/xfail.txt；**XPASS 与
   FAIL 同样使套件失败**（与上游 TODO 语义同严格）；自洽性约束 =
   任何归一化/钉住组合下 xpass 必须 = 0。

## 实测结果（MateBook，OHOS aarch64）

| 阶段 | total | pass | fail | xfail | xpass | 说明 |
|---|---|---|---|---|---|---|
| musl 容器预验证 | 355 | 316 | 15 | 24 | 0 | harness 语义验证；15 例归因 3 类 |
| 真机第 1 轮 | 355 | 241 | 90 | 24 | 0 | 全量 diff 取证，7 类归因 |
| 真机终态 | 355 | **249** | **0** | **106** | **0** | 归一化 + 79 行钉单（76 整文件 + 3 行 tc 级共 5 tc；106 = 上游 TODO 24 + 平台 82），连跑 ×2 逐字一致 |

musl 分布 ≠ 真机分布（make 版本不同，措辞类差异分布随之改变）——容器
只做 harness 语义预验证，钉单按真机实测回填。

真机 106 项 xfail 构成：FS 大小写不敏感错误前缀 ×65（kati 的
FindFirstMakefie 经 `Exists("makefile")` 命中沙箱大写 Makefile 后以小写名
报错）、`+=` 前导空格语义 ×4、`$(MAKEFILE_LIST)` 小写名 ×3、find
emulator vs 真 find ×6、make 版本措辞 ×1、getcwd 噪声残留组合 ×7、
var visibility ×2 等——全部确定性、可归因，见 xfail.txt 逐条原因。

## 适用边界

- **适用**：产物是构建机已有工具的行为等价物（make 克隆、shell/awk/sed
  重实现、busybox 类）；上游测试驱动不可移植但测试语义可提取。
- **不适用**：无参考实现的领域专有库；参考实现与被测物版本语义漂移过大
  （差分差异淹没平台差异时先评估版本对齐）。

## 关联

- 姊妹条目：`DRAFT-kati-0-git20251208-go-test-harness-faithful-python-port`
  （harness 语义如何从 Go 忠实搬到 Python）
- 相邻：`DRAFT-tool-fork-external-false-green-verification`（差分作为假绿
  抓取技法——本条目是差分作为**回归测试体系**，问题类不同）
- 关联适配 PR：kati 0_git20251208（路径 A，MR !15243）
