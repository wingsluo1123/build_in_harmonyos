# DRAFT-14435-libhinoko-1.0.3-libhinawa-glib2-zlib-conflict

## 摘要

libhinoko/1.0.3（PR #14435）构建 #90910（worker CI-016，buildid 104466）在
`conan-build-test` 步骤的 **conan create 依赖图解析期**失败，错误为：

```
ERROR: Version conflict: Conflict between zlib/1.3.1 and zlib/1.3.1.1 in the graph.
Conflict originates from glib2/2.88.0
```

与同 PR 前一失败轮次（#85600，L0i 依赖未发布，见
DRAFT-14435-libhinoko-1.0.3-l0i-unpublished-dep-hinawa）不同：本轮 L0i 已通过
（`[ok] dependency in registry: libhinawa/4.0.2`），依赖包 libhinawa/4.0.2 已发布，
失败点后移到 conan create 的依赖图解析。

## 现象（CI 日志 #90910）

```
oL0i: Checking dependency availability in registry (R36)...
o        [ok] dependency in registry: libhinawa/4.0.2      ← 依赖已发布，L0i 通过
...
o======== Computing dependency graph ========
olibhinawa/4.0.2#1231852695264209158e5d43444262ee - Cache
oglib2/2.88.0#aa5b8908c41279c288b09b5e22282c0e - Downloaded (ohpcd)
oERROR: Version conflict: Conflict between zlib/1.3.1 and zlib/1.3.1.1 in the graph.
oConflict originates from glib2/2.88.0
o[fail] libhinoko/1.0.3 — conan create failed
```

CI worker 的依赖图里同时出现两个 glib 系包：

| 包 | 来源 | zlib 依赖 |
|----|------|-----------|
| `glib/2.84.0.2` | libhinoko 配方直接 require | `zlib/1.3.1.1` |
| `glib2/2.88.0` | **制品仓 libhinawa/4.0.2 新 recipe 引入** | `zlib/1.3.1` |

两个不同 glib 系包对 zlib pin 了不同精确版本 → conan 2 图解析硬冲突（不自动择优）。

## 关键判定：制品仓依赖 recipe revision 漂移（本地过、PR 挂）

本地同配方 `conan graph info` / `conan create` 均通过，图里只有 `glib/2.84.0.2` →
`zlib/1.3.1.1`，**无 glib2**。原因是本地缓存里的 `libhinawa/4.0.2` 是旧 recipe
revision：

| 环境 | libhinawa/4.0.2 recipe revision | 依赖 |
|------|----------------------------------|------|
| 本地缓存 | `d00a6765ba368e28ae83339d4f5c0f57` | `glib/2.84.0.2` |
| ohpcd 制品仓（2026-10-14 发布） | `1231852695264209158e5d43444262ee` | `glib2/2.88.0` |

制品仓的 libhinawa/4.0.2 已完成 **glib → glib2 迁移**（requirements 改为
`self.requires("glib2/2.88.0", transitive_headers=True)`），而 libhinoko 配方仍直接
require `glib/2.84.0.2`，两个 glib 系包同图 → zlib 冲突。

## 实证（本地复现）

1. **复现 CI 冲突**：用干净临时 CONAN_HOME 拉取制品仓 libhinawa/4.0.2
   （rev 1231852695）+ glib2/2.88.0 后跑 `conan graph info`，得到与 CI 逐字一致的：
   ```
   ERROR: Version conflict: Conflict between zlib/1.3.1 and zlib/1.3.1.1 in the graph.
   Conflict originates from glib2/2.88.0
   ```
2. **验证修复方向**：把 libhinoko 配方的 `glib/2.84.0.2` 切换为 `glib2/2.88.0`
   （并同步 `self.dependencies["glib"]` → `["glib2"]`），同一临时 home 跑
   `conan graph info` → 无 Conflict，图收敛为单 glib2 系。

## 根因

- libhinoko/1.0.3 配方 `requirements()`：
  ```python
  self.requires("glib/2.84.0.2", transitive_headers=True, transitive_libs=True)
  self.requires("libhinawa/4.0.2", transitive_headers=True, transitive_libs=True)
  ```
- 制品仓 `libhinawa/4.0.2` recipe（rev 1231852695，2026-10-14 01:19:54 UTC 发布）
  已完成 glib→glib2 迁移，require `glib2/2.88.0`；
- `glib2/2.88.0` 配方 requires `zlib/1.3.1`；`glib/2.84.0.2` 配方 requires
  `zlib/1.3.1.1` → 双 glib 系包对 zlib 精确版本 pin 冲突；
- 本地缓存 libhinawa 为旧 revision（依赖 glib/2.84.0.2）→ 本地图无 glib2 → 本地过。

这是「制品仓已发布依赖 recipe revision 与本地缓存漂移」型问题，根因在上游依赖包
（libhinawa）的 glib→glib2 迁移，而非 libhinoko 配方自身缺陷。

## 推荐解法（rec_approach: align-direct-glib-dep-with-published-dependency）

1. **核对漂移**：
   ```bash
   conan download "libhinawa/4.0.2" -r=ohpcd --only-recipe   # 看最新 revision
   conan cache path libhinawa/4.0.2                          # 对比本地缓存 revision
   ```
2. **配方对齐 glib2**：libhinoko 把直接依赖从 `glib/2.84.0.2` 切换为 `glib2/2.88.0`
   （与制品仓 libhinawa 新 recipe 一致；main 生态 74 个配方已用 glib2/2.88.0 vs
   8 个用 glib/2.84.0.2，glib2 是主流）：
   ```python
   self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
   ```
3. **同步 dependencies 引用**：配方内所有 `self.dependencies["glib"]` 改为
   `["glib2"]`（generate() 里的 gobject-2.0.pc wrapper、glib-2.0.pc 追加
   `glib_genmarshal`/`glib_mkenums` 变量、PATH/LIBRARY_PATH 注入等）。glib2/2.88.0
   的 bin/ 同样含 glib-genmarshal/glib-mkenums（E348、gssdp 先例），工具可用性不降级。
4. **验证**：干净 CONAN_HOME 复现 CI 图确认无 Conflict → 本地 build_and_test.sh 通过
   → 推送 + `/rebuild`。

## 兜底解法（fallback: zlib-override-force）

若上游依赖包的 glib2 迁移尚未在 main 铺开或 glib2 组件无法满足 meson 需求，可对
zlib 版本做 force 钉扎统一消解冲突（`self.requires("zlib/1.3.1", force=True)` 或
`1.3.1.1`，需与全图一致）。注意：**不要用 override=True**——conan 2 会把
override=True 的 require 排除出 direct dependencies，导致 package_info 组件
requires 引用 `glib::` 时报 "not a direct requirement"（见
DRAFT-appstream-1.2.0-r04-conan-override-force-direct）。双 glib 系包并存本身有
符号/组件重复风险，优先推荐对齐 glib2 而非 force。

## 禁止策略

- **不要**不核对制品仓 recipe revision 就盲目 `/rebuild`：冲突源是制品仓已发布
  依赖 recipe 漂移，换 worker 不改变制品仓已发布内容，每次同点失败（与
  DRAFT-14435-l0i 的 8 次 rebuild 同型浪费）。
- **不要**对 zlib 用 override=True 掩盖：会把问题从图解析转移到 package_info
  组件校验失败。

## 同类先例

- **DRAFT-14435-libhinoko-1.0.3-l0i-unpublished-dep-hinawa**：同 PR 前一失败轮次
  （依赖未发布 → L0i），本轮是依赖已发布但 recipe 漂移 → 图解析冲突，两轮根因不同，
  需分别处置。
- **DRAFT-conan-version-family-override-uppin**：同族「版本对撞不择优」，但那是
  "同包多版本"；本实例是"不同 glib 系包各带不同 zlib pin"。
- **DRAFT-zlib-pin-conflict-pruning**：zlib 精确版本 pin 冲突的选项裁剪/对齐思路。
- **E348**：glib2 配方只声明 glib-2.0 一个 pkg_config_name，消费方需在 generate()
  写 gobject-2.0.pc 等 wrapper——libhinoko 切换 glib2 后该 wrapper 逻辑保留。

---
*草稿：AtomCode；来源 PR #14435（构建 #90910）；对应知识条目待 promote（当前 DRAFT）。*
