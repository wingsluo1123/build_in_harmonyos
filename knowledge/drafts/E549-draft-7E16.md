# E549（草稿）: raw makefile 多目录仓库适配 —— Makefile git 探针固定 + init-build F068 嵌套提升边界

- **来源**：infnoise 0.3.3 适配（2026-10-14，pc1-28）
- **领域**：构建系统 / 打包 / 提取
- **邻近但不同**：
  - E392（raw makefile 三陷阱：BadZipFile / compiler_executables / make cwd）——同族但未覆盖 git 探针与多目录 F068
  - E466（init_build._promote_nested_source 提升 Python sdist docs/）——同机制但为 Python 单场景，未覆盖 C 多目录仓库
  - E150（release tarball 缺 submodule）——触发面相似（tarball 无 git 元数据）但对象是 submodule 而非 Makefile 探针
  - E276（codeload URL basename 误判 zip 报 BadZipFile）——独立问题，仅同库出现

## 现象 1：Makefile 内嵌 git 探针在 release tarball 中报错

多目录 raw makefile 仓库（如 infnoise 的 `software/Makefile.linux`）用探针生成版本宏：

```make
GIT_VERSION := $(shell git --no-pager describe --tags --always)
GIT_COMMIT  := $(shell git rev-parse --verify HEAD)
GIT_DATE    := $(firstword $(shell git --no-pager show --date=iso-strict --format="%ad" --name-only))
```

官方 release tarball（codeload tar.gz）**不包含 .git**，make 解析期每行探针都输出：

```
fatal: not a git repository (or any parent up to mount point /storage/Users)
```

且 `GIT_VERSION` 宏为空字符串（`-DGIT_VERSION=\"\"`），`--version` 输出空版本。

## 现象 2：init-build F068 把多目录仓库截断

infnoise tarball 顶层含 `software/`（主代码+88 文件）、`tests/`（198 文件）、`kicad/eagle/images`（硬件设计）等。init-build 的嵌套源码检测把含 Makefile 的 `software/examples/libinfnoise` 提升为源码根：

```
✅ 嵌套源码提升完成: software/examples/libinfnoise → infnoise-0.3.3.orig
```

`.work` 只剩 7 个文件（Makefile + 2 个 example .c + .gitignore），`software/` 主体全部丢失。

## 根因

1. Makefile 内嵌 git 探针假设构建目录在 git 仓库内；release tarball 适配必然无 .git。
2. `_promote_nested_source` 只按构建标记递归找"源码子目录"，多目录仓库中主代码子目录与示例子目录都可能含 Makefile，无法区分；顶层无 configure/CMakeLists 时把第一个含构建标记的子目录提升为根。

## 方案

### 修复 1：补丁固定版本字符串（零平台宏）

```make
GIT_VERSION ?= 0.3.3
GIT_COMMIT  ?= 0.3.3
GIT_DATE    ?= 2026-10-14
```

`?=` 保留环境覆盖能力；补丁不含 `__OHOS__`（R8 合规）。

### 修复 2：从官方 tarball 全量重建 .orig/.work

```bash
FULL="$HOME/infnoise-0.3.3-full/infnoise-0.3.3"   # tar -xzf 官方 tarball
rm -rf infnoise-0.3.3.orig infnoise-0.3.3.work
cp -a "$FULL" infnoise-0.3.3.orig
cp -a "$FULL" infnoise-0.3.3.work
cd infnoise-0.3.3.work && patch -p1 -s < patches/0001-software-Makefile.linux.patch
diff -rq .orig .work   # 应仅剩 Makefile.linux 一处差异
```

### 重要纪律（后续步骤的错误源）

- **不要在截断的 work 上直接 refresh-patch --auto**：会把后来手工拉取的 submodule（bats-assert/bats-support）内容也生成补丁（本库 13 个误补丁），且 conandata 声明的 `0001-software-Makefile.linux.patch` 与 refresh-patch 重命名后的实际文件名失配 → conan create 报 `Patch file does not exist`（E515 同类）。必须先清理误补丁、把 Makefile.linux 补丁恢复到 conandata 声明的 0001 名称。
- 重建 work 后**重新应用补丁**再验证，diff 只应剩补丁文件差异。
- 清理命令通配符别误删源文件（`libinfnoise.*` 会匹配 .c/.h/.version）。

## 验证

```bash
make -f Makefile.linux          # 无 "fatal: not a git repository" 输出
./infnoise --version            # GIT VERSION - 0.3.3
python3 scripts/ohc-run.py conan-verify infnoise 0.3.3   # G2 PASS
```

## 适用边界 / 反例

- 适用：raw POSIX Makefile 构建、多目录源码树（主代码在子目录）、release tarball 无 .git。
- 不适用：autotools/cmake/meson（有自己版本机制）、单目录仓库（F068 不触发）。
- 反例：若 Makefile 探针有 `|| true` 兜底且版本宏非关键，可不打补丁；但 CI 的 `--version` 验证（L2）会暴露空版本。

## 查重差异（七轴结论摘要）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否（E392/E150/E466 均未覆盖本组合） |
| causal_duplicate | 部分（E466 同机制，但 Python sdist 场景） |
| trigger_overlap | 是（E150 tarball 无 git；E466 嵌套提升） |
| solution_overlap | 部分（tarball 全量重建与 E466 重建思路一致） |
| combination_novelty | 是（多目录 C 仓库 + git 探针 + F068 的组合未见于既有条目） |
| boundary_novelty | 是（E466 仅覆盖 Python sdist，本条目扩展到 C 多目录仓库） |
| test_migration_novelty | 否 |