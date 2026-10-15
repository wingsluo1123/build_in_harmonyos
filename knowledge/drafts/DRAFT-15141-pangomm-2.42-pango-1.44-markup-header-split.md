# DRAFT-15141-pangomm-2.42-pango-1.44-markup-header-split：mm 绑定老线 × pango 1.44+ 头拆分的编译失败与最小补丁

> Contributor: j669539 | Status: Draft | 2026-10-13
> Source: pangomm 2.42.2 适配 HarmonyOS PC（任务卡 #15141，PR #15574）
> 对应：`knowledge/drafts/DRAFT-15141-pangomm-2.42-pango-1.44-markup-header-split.kv`

## 错误特征

pangomm 2.42.2（pangomm-1.4 旧 ABI 线）对 pango 1.50.14 编译：

```
untracked/pango/pangomm/attrlist.cc:38:20: error: use of undeclared identifier 'pango_parse_markup'
untracked/pango/pangomm/attrlist.cc:65:20: error: use of undeclared identifier 'pango_parse_markup'
```

`ninja -k 0` 收敛后全库仅此一处缺口（两行同一符号）。

## 根因

- pango 1.44（2019-09）把 markup API 从 `pango-attributes.h` 拆进独立的
  `pango-markup.h`；伞形 `pango/pango.h` 仍传递包含它。
- mm 绑定老线的生成头用**细粒度**头：`attrlist.h` 只 include
  `<pango/pango-attributes.h>`（2.42 线由 gmmproc 2.64.3 生成），
  `pango_parse_markup` 声明不可达。
- 近线（2.46+，gmmproc 2.66+）生成头统一改伞形 `<pango/pango.h>`，
  天然免疫——对照 `archives/p/pangomm/2.46.5` 无此补丁。
- 本质是「上游老版本绑定 × 新版本依赖头重组」的兼容窗口问题，
  不是 HarmonyOS 平台差异，Linux 新发行版配 pango>=1.44 同样会踩。

## 解法（最小补丁）

`untracked/pango/pangomm/attrlist.cc` 的既有 include 块后显式补：

```cpp
// pango >= 1.44 moved pango_parse_markup() into <pango/pango-markup.h>;
// the gmmproc-2.64-generated headers only include the fine-grained
// <pango/pango-attributes.h>. Include the split header explicitly so the
// markup ctors compile against pango 1.44+ (e.g. 1.50.x used here).
#include <pango/pango-markup.h>
```

conandata.yml：

```yaml
patches:
  - patch_file: "patches/0001-pango-1.44-markup-header-split.patch"
```

### 同类问题排查法（全量收敛，避免逐轮试错）

1. `ninja -k 0`（continue-on-error）一次性收集全部编译错误；
2. 提取全部 `pango_*` 调用符号，逐个 `grep -rl` pango 头目录定位声明文件；
3. 对照生成头的 include 链找缺口，一处补丁收敛全部错误。

## 降级方案

- meson 注入强制包含 `add_project_arguments('-include','pango/pango-markup.h')`；
- 或降依赖 pango < 1.44（不推荐：制品仓 pango 线已 1.50/1.56）。
- 不可 sed 改 meson.build 换头：生成代码预置于 untracked/，不受
  meson.build 控制。

## 验证

- 本机：`conan create archives/p/pangomm/2.42.2 -pr:h=<ohos-aarch64> --build=missing`
  RC=0，L1 4/4 + 鸿蒙特有 14/14 全绿。
- CI：PR #15574 构建 #89253 passed。

## 查重与增量

- `DRAFT-13572-pangomm-2.46-legacy-mm-abi-line-matching`：覆盖 **ABI 线选型/
  依赖版本匹配**（按 pc 名反查），未覆盖**选线正确后老线生成代码对新 pango
  的头拆分兼容**——本条覆盖其下游相邻环节。
- `DRAFT-13572-pangomm-2.46-meson-pkgconfigdeps-gap-trio`：覆盖 PkgConfigDeps
  三缺口（gmmprocdir/转发 pc/-L 注入），与编译期头缺口无关。
- `DRAFT-24650-conan2-override-dep-rebuild-source-cache-fallback`：覆盖 override
  重建的源码缓存兜底，无关。
- 增量：mm 家族「老线绑定配新依赖」的头重组兼容窗口 + 全量错误收敛排查法。

## 推广价值

任何 gmmproc 2.6x 时代生成、细粒度 pango 头链的 mm 绑定老线
（pangomm 2.42 线、gtkmm 2.4/3.0 老线消费 pango 的面）配 pango>=1.44
的场景；方法论（ninja -k 0 + 符号级声明定位 + 伞形/细粒度头对照）
适用于一切「上游版本窗口错配」类编译失败。
