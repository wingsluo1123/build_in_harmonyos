# DRAFT — 上游测试依赖外部网络导致间歇失败：门禁应按“网络输出特征 + 显式清单”分类

状态：草稿（OpenDesk 落稿，2026-10-13）；Exxx 编号由知识库主编定稿时分配。
案例库：two-ms 5.2.4（Checkmarx/2ms，Go CLI；上游 6 个子用例依赖 `api.github.com`）。

## 可复现症状与稳定错误签名

- 稳定签名 1（工具运行期告警）：
  `{"level":"warn","error":"Get \"https://api.github.com/\": dial tcp: lookup api.github.com on 8.8.8.8:53: read udp 10.69.70.158:40050->8.8.8.8:53: i/o timeout","message":"Failed to validate secret"}`
- 稳定签名 2（断言失败）：`validationStatus` 期望 `Invalid` 实得 `Unknown`；
  `severity` 期望 `Medium` 实得 `High`；`cvssScore` 期望 `5.2` 实得 `8.2`。
- 稳定签名 3：`lookup … no route to host`（网络更差时）。

## 根因（机理链）

1. 上游部分测试带 `--validate`（或直接断言 `validationStatus`/`severity`/`cvssScore`），
   运行期向 `https://api.github.com/` 发起真实请求校验植入的 GitHub PAT。
2. 有公网：GitHub 返回 401 → `validationStatus="Invalid"`、`severity=Medium`、
   `cvssScore=5.2`，与期望报告一致 → PASS。
3. 无公网/DNS 超时：请求失败 → 工具回退为 `validationStatus="Unknown"`、
   `severity=High`、`cvssScore=8.2` → 与期望不一致 → FAIL。
4. 上游 CI 跑在 `ubuntu-latest`（有公网），因此该环境依赖在 CI 侧**从不暴露**；
   在离线/受限网络的适配环境里则表现为**间歇性**失败（网络时好时坏）。

## 方案（分类而非一刀切）

在 conan 配方的 `build()` 测试门禁中：

1. 解析 `go test -json` 的 `output` 事件，凡失败用例的输出含网络特征
   （`Failed to validate secret` / `dial tcp` / `i/o timeout` / `no route to host` /
   `Temporary failure in name resolution`）→ 归入 `environment-network-limited`。
2. 对**不打印网络日志但同样断言 validation** 的用例（如 engine 包），用显式清单登记。
3. 判定粒度取「叶子失败」：父用例仅因子用例失败而失败时不重复计数。
4. 构建失败单独判定（`FailedBuild` 或 output 以 `# ` 开头）——注意**包级 `fail`
   事件不等于构建失败**，普通测试失败同样产生包级 fail 事件。
5. 分类命中的用例如实打印（WARN + 具体名 + 原因），**不计入门禁**；
   其余失败 + 构建失败 + 通过数低于下限 仍**硬阻塞**。

## 验证（two-ms 5.2.4 实测）

- 网络正常：1139 用例通过 1137 / 失败 0 / 跳过 2。
- 网络受限（`i/o timeout`）：6 个 validate 用例失败 → 全部归类
  `environment-network-limited`，门禁判 **PASS**（其余 1133 用例全绿），
  WARN 如实列出 6 个用例名与原因。

## 关联

E318（go test 临时 ELF 未签名）、E250（自举 Go 工具链）。
规范依据：R51 上游测试三步法（如实回填实测 N/N′/通过率，逐项列具体技术原因）。
