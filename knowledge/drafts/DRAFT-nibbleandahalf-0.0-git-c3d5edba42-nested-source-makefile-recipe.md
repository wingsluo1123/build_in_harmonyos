# DRAFT-nibbleandahalf-0.0-git-c3d5edba42-nested-source-makefile-recipe

GitHub commit tarball 仓库根含 IDE 文件、源码在子目录 + 纯 Makefile 项目被 conan-init
误判 autotools 模板 → source() 展平 + make 驱动配方。

## 基本信息

- **严重度**: 2
- **类别**: build-system, make, conan-recipe, source-layout, git-tarball
- **来源**: nibbleandahalf 0.0-git-c3d5edba42 适配（HarmonyOS PC aarch64）
- **状态**: 草稿（待审核 promote）
- **来源 PR**: （随 nibbleandahalf 归档 PR 一并交付）

## 错误特征

```
make: *** No rule to make target 'libnaah64.a'
下载内容是 HTML
make: *** No rule to make target '<目标>.a/.so'
```

## 根因分析

1. GitHub commit tarball（`NibbleAndAHalf-c3d5edba42.../`）仓库根混放 IDE 工程文件
   （.sln / .xcodeproj / .vcxproj）与源码子目录（`NibbleAndAHalf/`）；conan
   `get(strip_root=True)` 只剥离一层 commit 前缀目录，Makefile 落在
   `source_folder/NibbleAndAHalf/` 下，`build()` 里 make 找不到目标 →
   `No rule to make target`。
2. conan-init 依据 init-build 对 URL 的 build_system 猜测（autotools）生成
   `AutotoolsToolchain` 模板，但上游是纯 Makefile（无 configure 脚本），模板不适用。
3. git 版本（`0.0-git-<sha>`）无 release tag；若 init-build 拿到仓库页 URL 会下载到
   HTML → `下载内容是 HTML`。必须用官方 commit tarball URL。

## 推荐方案

**方法**: flatten-nested-source-plus-make-recipe

1. `source()`：`get(strip_root=True)` 后检测嵌套源码子目录（如 `NibbleAndAHalf/`），
   把子目录内容 `shutil.move` 到 `source_folder` 根（若根尚无 Makefile）。
2. `conanfile.py` 改写为 make 驱动：`generate()` 用 `AutotoolsToolchain`（提供
   conanbuild env，满足 R33）；`build()` 用 `self.run("make -j1 <目标>",
   cwd=self.source_folder, env="conanbuild")`；`package()` 用 `copy()` 收集
   include/lib；`package_info()` 设 `cpp_info.libs`。
3. 下载 URL 用 `/archive/<sha>.tar.gz` 官方 commit tarball（R39），SHA-256 如实填写。

**验证/命令**:

```bash
python3 scripts/ohc-run.py conan-verify nibbleandahalf 0.0-git-c3d5edba42
# G0-G4 全 PASS；test_package 1/1 通过
```

## 回退方案

不展平源码树时，`build()` 把 cwd 指向嵌套子目录
（`os.path.join(self.source_folder, "NibbleAndAHalf")`），`package()` 从该子目录 copy()。

## 关系

- similar_to: E392（raw makefile Conan 配方三陷阱，cwd=source_folder）、
  E195（init-build 嵌套源码 promote 删除同级目录，CMake 场景）、
  E276（codeload 末段无扩展名 BadZipFile，filename= 修复）
- caused_by: 无 | prerequisite_of: 无 | conflicts_with: 无

## 适用边界 / 反例

- 适用：仓库根含 .sln/.xcodeproj 等 IDE 文件、实际源码在子目录的 GitHub 仓库；
  `0.0-git-<sha>` 版本；纯 Makefile（无 configure）C/C++ 库。
- 反例：单层 tarball（源码直接在根）无需展平；autotools/cmake/meson 项目不适用；
  E195 的 init-build promote 删除同级目录问题机制不同（本候选不动 init-build）。

## 真实证据

- conan create（ohos-aarch64 profile）G2 通过；`reports/conan-verify-report.md`
- `reports/upstream-test-ledger.md`：上游 5/5 用例全通过
- `reports/ohos-test-full.log`：鸿蒙专项 ALL PASS
- 源码：`archives/n/nibbleandahalf/0.0-git-c3d5edba42/conanfile.py`
