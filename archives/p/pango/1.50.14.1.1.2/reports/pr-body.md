## 三方库信息

- **三方库名称**：pango
- **上游版本**：1.50.14（本提交发布 **pango/1.50.14.1.1.2**）
- **上游仓库地址**：https://download.gnome.org/sources/pango/1.50/（与既有 1.50.14.1.1 同源、同 sha256）
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展，候选）
- **使用知识库**：openharmony-compile-agent

## 为什么需要递增（依赖侧钉版对齐，非功能改动）

消费者（mplayer 1.5-svn38681，PR #15441）要启用 **gmplayer GUI**（`--enable-gui`，依赖 `gtk+-2.0` → gtk2 → pango），
而同一个依赖图里已有字幕栈 `libass/0.17.5`。两者对 **harfbuzz** 的精确钉版不同：

```
libass/0.17.5        → harfbuzz/14.2.0
pango/1.50.14.1.1    → harfbuzz/14.2.0.1.1.1        # 原版本
```

同图时实测：

```
ERROR: Version conflict: Conflict between harfbuzz/14.2.0 and harfbuzz/14.2.0.1.1.1 in the graph.
```

消费者的替代做法是 `override=True` 强行统一，但那会迫使 **libass 等已发布依赖在 CI 里从源码重建**（违反仓内 R36）。
因此改在**依赖侧**递增一个只改钉版的版本：`pango/1.50.14.1.1.2` → `harfbuzz/14.2.0`，与 libass 对齐，同图自然共存。

## 变更范围（最小化）

| 项 | 1.50.14.1.1 | 1.50.14.1.1.2 |
|---|---|---|
| `version` | 1.50.14.1.1 | **1.50.14.1.1.2** |
| `harfbuzz` requires | 14.2.0.1.1.1 | **14.2.0** |
| 源/补丁/configure 选项/产物布局 | 不变（同 URL、同 sha256、同 patch 集） | 不变 |
| `test_package` 内 harfbuzz 钉版 | 14.2.0.1.1.1 | **14.2.0**（同步，否则测试包自身图冲突——本次实测踩到） |

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 27 | 来源：上游 meson `tests/`（`tests/meson.build` 声明；评审实测口径 **27**，本构型 `meson test --list` 注册 **26** 个可执行目标 = 18 常规 + 8 标入 `failing` suite） |
| 集成测试 | 0 | 上游无独立集成套件 |
| 其他测试 | 0 | — |
| **合计** | **27** | 声明值取评审实测口径，避免少报 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 15 | -12 | **真实执行**上游 meson 套件（本机 OHOS 原生运行）：18 例执行 → **15 通过 / 0 失败 / 3 跳过**（跳过：`test-shape`、`cxx-test`、`test-itemize`，原因均为本机无 `fonts.conf`）；另有 8 例同因标入 `failing` suite 并由 `--no-suite=failing` 排除：`test-font`/`test-fonts`/`test-layout`/`test-bidi`/`testiter`/`test-ellipsize`/`test-harfbuzz`/`testmisc` |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 1 | 新增 | 消费者用例（`test_package`）：链接并运行 `test_probe`，断言 `pango_version_string`、`pango_cairo_font_map_get_default` 与 `libpangocairo-1.0.so` 动态加载 |
| **合计** | **16** | **-11** | 减少的 11 例**全部**为具体环境原因（OHOS 上无 fontconfig 配置文件 `fonts.conf`，fontconfig 报 `Cannot load default config file: File not found`），非能力删减 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

说明（补充上下文，供人工确认）：补丁 `patches/0001-ohos-failing-suite-font-tests.patch` **只改测试的构建定义**
（`tests/meson.build` 中把 8 个依赖 `fonts.conf` 的用例加进 meson 的 `failing` suite），**未删除、未修改任何用例源码**；
配方以 `--no-suite=failing` 排除它们，其它失败仍会中断构建。8 个用例：`test-font`/`test-fonts`/`test-layout`/`test-bidi`/
`testiter`/`test-ellipsize`/`test-harfbuzz`/`testmisc`；另有 3 例（`test-shape`/`cxx-test`/`test-itemize`）因同样缺 `fonts.conf` 被跳过。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

说明（补充上下文，供人工确认）：上游 meson 已自带 27 例测试；本包另外补充了 1 个**消费者用例**
（`test_package`：链接并运行 `test_probe`，断言 `pango_version_string`、`pango_cairo_font_map_get_default` 与
`libpangocairo-1.0.so` 动态加载），属于消费者验证而非"上游无测试的补全"。

## 验证结果

- 编译状态：**通过** —— `conan create archives/p/pango/1.50.14.1.1.2 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` → rc=0
- 上游测试用例通过率：**15/18（83.3%）** —— 上游 meson 套件**真实执行**，`Ok: 15 / Fail: 0 / Skipped: 3`（失败 0 例；3 例跳过与 8 例排除均为具体的环境原因：本机无 `fonts.conf`）
- 新增测试用例通过率：**1/1（100%）** —— `test_package` 消费者用例
- 上游套件执行输出（本机 OHOS 原生运行，非交叉跳过）：
```
Ok:                15
Fail:              0
Skipped:           3
```
- test_package 实测输出：
```
pango/1.50.14.1.1.2 (test package): RUN: ./test_probe
pango ok version=1.50.14 (pangocairo)
```
- 图验证：与 `libass/0.17.5` 同图不再报 harfbuzz 版本冲突（消费者侧无需 override）

## 路径评估（按仓内口径）

- **路径 A（基础适配）**：已完成 —— 构建与消费者探针通过。
- **路径 B（知识库扩展）**：**可申报（候选）** —— 可迁移经验：*跨包传递依赖钉版冲突的依赖侧解法*——
  不 override、不重建已发布依赖，而是为冲突方递增一个**只改钉版**的版本；且 `test_package` 内的钉版必须同步，
  否则测试包自身会在图解析阶段失败（本次实测踩到并在本提交修正）。
- **路径 C（高难度挑战）**：**不主张** —— 一处钉版对齐 + 版本递增，无 bundled 依赖与高成本验证矩阵。
