# DRAFT-libxext-6.4.0.1-dependency-variant-r37-increment — 依赖闭包变体补发不能改已发布版本 recipe：R37/R40 双门禁要求递增版本后缀 + 分支名精确匹配

> 草稿（待审核 promote）。来源：libxext/6.4.0.1（PR #16696）依赖变体补发失败诊断，CI #98287。

## 症状

- `libxext/6.4.0.1` 已于 2026-09-01 发布，但只发布过基于 `libx11/6.4.0` 的二进制变体（package id `e647863c…`）；
- `libxmu/1.3.1.1` 以 `force=True` 把全依赖图 libx11 钉在 `1.8.13`（libx11/1.8.13 的 package() 保留 `libX11.la` 供 libxt 的 `_prepare_ohos_libtool_shadow()` 使用，而 6.4.0 会 `rm("*.la")`）；
- 经 libxmu 的下游（如 zutty）解析 libxext 时要求其基于 libx11/1.8.13 的变体（package id `eab79208…`），制品仓缺失 → 被迫每轮从源码重编 libxext；
- 试图在同一版本号 `6.4.0.1` 下修改 recipe（`requirements()` 中 libx11 6.4.0 → 1.8.13 + `force=True`）补发变体 → CI L0 门禁直接失败：

```
[fail] L0j: libxext/6.4.0.1 already published with different recipe (R37)
制品仓中已存在 libxext/6.4.0.1, 且本次修改了 conanfile.py 或 conandata.yml
cnb.cool 制品仓不支持同版本多 revision 并存 (409 Conflict)
[hint] 适配修复必须递增版本号后缀: libxext/6.4.0.1 → libxext/6.4.0.1.1

[error] L0n: branch name mismatch (R40) — 分支名带额外后缀，要求精确匹配
分支 'feat/libxext-6.4.0.1-libx11-1.8.13-variant'（去前缀后 'libxext-6.4.0.1-libx11-1.8.13-variant'）≠ 'libxext-6.4.0.1'（不允许后缀）
```

## 根因

1. **package id 由 settings + options + 依赖闭包共同决定**："有制品"只是"默认依赖线的变体有"。同一 recipe 版本换 requires 版本线（libx11 6.4.0 → 1.8.13）会产出完全不同的 package id。
2. **制品仓（cnb.cool）不支持同版本多 recipe revision 并存（409）**：已发布版本一旦修改 conanfile.py / conandata.yml，R37/L0j 直接拦截，本地构建通过也不能覆盖制品仓身份冲突（E1520）。
3. **R40/L0n 分支名硬门禁**：分支名去掉最后一段 `/` 前缀后必须逐字等于 `包名-版本号`，带 `-variant`、`-fix` 等后缀一律失败；分支名与目录版本分裂还会导致平台按"分支名完全一致 + 作者"匹配任务失败。

## 方案

- **递增版本后缀**：`libxext/6.4.0.1 → libxext/6.4.0.1.1`，新建 `archives/l/libxext/6.4.0.1.1/` 目录。上游源码 tarball 与 sha256 **完全不变**（同一 `libXext-1.3.6.tar.xz`），唯一差异是 `requirements()` 中 libx11 改为 `1.8.13` 并加 `force=True`（与 libxmu/1.3.1.1 口径一致）；
- **同步更新**：`conanfile.py` 的 `version`、`conandata.yml` 的版本键、`manifest.yaml` 的 `version`/`dependencies`、`test_package` 引用、版本级 `MANIFEST.yml`；
- **恢复已发布版本原状**：6.4.0.1 目录的 conanfile.py / manifest.yaml 必须还原为与制品仓一致的内容（已发布版本不可变）；
- **更新所有下游引用**：把仓库中 `requires("libxext/6.4.0.1")` 全部更新为 `6.4.0.1.1`（CI hint 明确要求"更新 archives/ 目录和所有下游引用"）；
- **分支名精确匹配**：`feat/libxext-6.4.0.1.1`（前缀 `feat/` 允许，后缀禁止）。

## 验证

```bash
conan list "libxext/6.4.0.1:*" -r=ohpcd                 # package_id 级核对：应看到 e647…（6.4.0 线）
conan graph info --requires=libxext/6.4.0.1 --build=never \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64  # force 钉版后解析出 eab792…
CI_PACKAGES="archives/l/libxext/6.4.0.1.1" CI_BRANCH="feat/libxext-6.4.0.1.1" \
  zsh ci/conan/build_and_test.sh                        # 本地 CI 同款脚本，L0 全绿
```

## 禁止做法

- ❌ 在同一版本号下修改已发布版本的 conanfile.py 补发变体——必然 R37 409，本地通过也救不回（E1520）；
- ❌ 分支名带任何后缀（`-variant` / `-fix` / `_2`）——R40 硬拦截；
- ❌ 版本级 `conan list "libxext/*"` 判"有没有制品"（R35）——必须按 package_id 级 `"<ref>:*"` 核对；
- ❌ 在消费方 PR 里顺手改依赖包配方（JC6 单软件原子性）；依赖变体补发应作为独立 PR（本包新版本）发布。

## 关联

- **E1509**（Exact dependency override requires a new package identity）：替换传递依赖提供者改变下游闭包，须用下一适配版本；
- **E1520**（Published Conan versions require a new recipe and branch identity）：递增后缀版本 + 新分支精确身份；
- **DRAFT-conan2-option-variant-no-fallback-publish-new-version**：options 变体（shared=True）缺制品同族问题，同样只能新版本号发布（R37）；
- **E719**（R40/L0n 分支名门禁归一化）：分支名必须逐字匹配 包名-版本号。
