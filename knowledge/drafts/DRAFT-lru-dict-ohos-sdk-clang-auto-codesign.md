# DRAFT — OHOS SDK clang 链接期自动生成 `.codesign` 段：C 扩展无需手工重签

> Status: DRAFT | Source: lru-dict/1.5.0 adaptation（CPython C 扩展）
> Environment: HarmonyOS PC aarch64，OHOS SDK clang 15.0.4（Target: aarch64-unknown-linux-ohos），Conan 2.29.1

## 1. 背景与先例的分歧

仓内既有先例把「OHOS 要求被 dlopen 的 `.so` 带 `.codesign` 段」表述为**无条件
必需的手工步骤**：

- `archives/c/cffi/2.1.1`、`archives/l/lazy-object-proxy/1.12.0`：在 `build()`
  与 `package()` 各调一次 `binary-sign-tool ... -selfSign 1`，理由是「conan 的
  `copy()` 会使既有签名失效」。
- 知识库 **E077**：鸿蒙 ELF 必须含有效 `.codesign` 才能被内核加载执行；
  `patchelf` / `llvm-strip` / `llvm-objcopy` 修改 ELF 后签名失效；
  `binary-sign-tool` 无法覆盖已有签名段（报 `section already exists`），
  必须先移除旧签名再重签。
- 知识库 **E452**：task-private 共享库副本上的旧签名需要强制重签。

lru-dict 1.5.0 适配时实测发现：**在本平台，链接期工具链已经签好了**，手工重签
既非必需，且会用 `selfSign` 覆盖工具链的可信签名。

## 2. 实测证据（三步）

| 步骤 | 命令 | 结果 |
|---|---|---|
| ① 链接产物是否自带段 | `readelf -S _lru.cpython-312-aarch64-linux-ohos.so \| grep codesign` | `[36] .codesign PROGBITS` —— **存在** |
| ② 直接 import | 宿主 OHOS `python3 -c "import lru"`（`sys.platform=ohos`）与 conan python 解释器 | **均成功**，无任何手工签名 |
| ③ 负向对照（证明该段是必要条件） | `llvm-objcopy --remove-section .codesign <so>` 后再 import | **立即失败**：`ImportError: Error loading shared library ...: Permission denied` |

步骤 ③ 是关键：它把「段存在」与「段是加载必要条件」两件事分开验证了。
若无 ③，无法排除「段是无关产物、import 成功另有原因」。

工具链信息：`/data/service/hnp/bin/clang` → `clang version 15.0.4`，
`Target: aarch64-unknown-linux-ohos`（本机 `CC` 默认值）。

## 3. 结论与处置

**结论**：`.codesign` 段确实是 OHOS `dlopen` 的必要条件（E077 成立），
但「必须手工重签」不是本平台事实——**链接期已自动生成**。

**处置**（lru-dict 配方采用的形态）：签名逻辑改为**校验兜底**而非无条件自签：

1. 构建/打包后，用**纯 Python 解析 ELF 段名表**实测 `.codesign` 是否存在；
2. 存在 → **不改动**（保留工具链可信签名）；
3. 缺失（被 `copy()` / `llvm-objcopy` 等破坏）→ 才调 `binary-sign-tool`
   重签并**复验**；
4. 仍缺失 → 显式抛错，绝不静默交付装不上的模块。

第 1 步不能依赖签名工具的输出判定：`binary-sign-tool` 会打印
`add codesign section success` 并返回 0，但产物可能不含该段（cffi 先例实测）。
只有读 ELF 段名表是硬证据。

## 4. 适用边界与反例

- **适用**：用本平台 OHOS SDK clang（15.0.4，`aarch64-unknown-linux-ohos`）
  链接的 `.so`，包括 CPython C 扩展与共享库插件。
- **反例 / 需回退**：其它工具链或旧 SDK 若实测 `readelf -S` 无该段且 import
  失败，应按先例每步重签（`fallback_*` 字段）。
- **不得**仅凭 `binary-sign-tool` 的 rc/输出断言语义已签名。
- **不得**因为「本平台自动签」就删掉打包后的复验——`copy()` 仍可能破坏段。

## 5. 与既有知识的差异

- 与 **E077** 不冲突：E077 说「ELF 必须有有效 `.codesign` 才能加载」，
  本条目补充「本平台该段由链接期自动生成，故不必无条件手工重签」，
  以及「判定必须实测段名表而非信任工具输出」。
- 与 **E452**（task-private 副本强制重签）互补：E452 处理的是**副本**场景，
  本条目处理的是**首次产出**场景。
- 差异点：既有语料未记录「OHOS SDK clang 自动签名」这一事实，故本条目不是重复。
