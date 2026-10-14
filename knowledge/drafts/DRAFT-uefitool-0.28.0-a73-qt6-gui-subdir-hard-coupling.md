# 上游 CMakeLists 用无条件 ADD_SUBDIRECTORY 把 Qt6 GUI 目标耦合进整棵构建树

- **草稿 ID**: DRAFT-uefitool-0.28.0-a73-qt6-gui-subdir-hard-coupling
- **来源**: UEFITool 0.28.0-a73（上游 tag `A73`，new_engine 分支）适配
- **分类**: build-system / cmake / qt6 / dependency / limitation
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无审核结论）

## 问题 / 错误签名

在只有 Qt5 的平台上对上游根工程跑 CMake configure，直接中止：

```
CMake Error at UEFITool/CMakeLists.txt:9 (FIND_PACKAGE):
  By not providing "FindQt6.cmake" in CMAKE_MODULE_PATH this project has
  asked CMake to find a package configuration file provided by "Qt6", but
  CMake did not find one.
```

被阻断的不只是 GUI。上游根文件总共只有五行：

```cmake
CMAKE_MINIMUM_REQUIRED(VERSION 3.22)
PROJECT(UEFITool_everything)
ADD_SUBDIRECTORY(UEFIExtract)     # 纯 C++，零 Qt 依赖
ADD_SUBDIRECTORY(UEFIFind)        # 纯 C++，零 Qt 依赖
ADD_SUBDIRECTORY(UEFITool)        # Qt6 Widgets GUI，第 9 行 REQUIRED
```

`UEFIExtract` / `UEFIFind` 与 GUI 是**平级且都没有条件保护**的。CMake 处理
`ADD_SUBDIRECTORY` 时立即展开子目录 ⇒ GUI 的 `FIND_PACKAGE(Qt6 REQUIRED …)` 一失败，
整个 configure 流程中止，此时还没进入任何语言编译阶段 ——
「本次不需要 GUI」这个事实救不了同级的两个 CLI。

## 根因

**可选目标被硬编码进了必需路径。**

上游的意图可以理解：项目就是从 GUI 长出来的，CLI 是后来加的，`ADD_SUBDIRECTORY`
无条件写是 CMake 里最常见的写法。问题不在"用了 REQUIRED"（GUI 确实需要 Qt6，
用 REQUIRED 是对的），而在于**根工程把所有子目录都当作必需**。
当交付平台只提供 Qt5 时，这个假设就破了。

判别这类问题只需两个问题：

1. 报错的子目录，是**产物本身**还是**可选目标**？
2. 被连带阻断的目标，其子目录 CMakeLists 里有没有 `FIND_PACKAGE`？
   其源码有没有 `#include <Q...>`？

本例：报错目录是可选目标（GUI 不参与本次交付），被阻断的两个 CLI
`grep FIND_PACKAGE` 与 `grep "#include <Q"` **均为空** ⇒ 它们本可以独立构建。

## 最小修复方案

**不动上游一个字节**，新增一个适配侧薄 `cmake/CMakeLists.txt`：

```cmake
cmake_minimum_required(VERSION 3.22)
project(uefitool CLI CXX C)

# 第二个参数显式给独立 binary dir，避免与上游子目录的同名目标/产物冲突
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../UEFIExtract"
                 "${CMAKE_CURRENT_BINARY_DIR}/UEFIExtract")
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../UEFIFind"
                 "${CMAKE_CURRENT_BINARY_DIR}/UEFIFind")

# 上游只在 IF(UNIX) 分支里改名；不要依赖"本平台会被判成 UNIX"这一间接假设
set_target_properties(UEFIExtract PROPERTIES OUTPUT_NAME "uefiextract")
set_target_properties(UEFIFind    PROPERTIES OUTPUT_NAME "uefifind")
```

配方侧（conan）：

```python
def export_sources(self):
    copy(self, "cmake/CMakeLists.txt",
         src=self.recipe_folder, dst=self.export_sources_folder)

def build(self):
    cmake = CMake(self)
    cmake.configure(build_script_folder="cmake")   # ← 指向适配侧入口
```

因为该文件**不在上游源码树里**，它不构成 patch ⇒ `patches_applied` 为空，
也就没有"补丁计数同步"这一类问题。

**适用边界**：只有当被丢弃的目标是**真正可选**的（本例 GUI 不参与交付）时才适用。
若被丢弃的目标就是产物本身，那是功能裁剪，需要另走评估，不能套用本条目。

## 为什么不是「绕过平台限制」

- 剥离 GUI **不损失任何被交付能力**：全部解析逻辑在 `common/` 下
  （FV/FFS/段/NVRAM/PE 镜像/各家 OEM 专用格式），GUI 只是这套解析器的一个消费者；
  两个 CLI 复用完全相同的解析代码路径。
- 这是**按平台能力裁剪交付面**，而不是"让平台限制变得不生效"（P013 的反面）。
- 若后续平台补齐了 Qt6，只需在适配侧入口加回一行 `add_subdirectory(... UEFITool)`，
  上游依然零改动 ⇒ 该决策**可逆**。

## 验证证据

- 上游 `UEFITool A73`：适配侧入口装载 `UEFIExtract` + `UEFIFind` 后 configure 成功，
  产出两个可执行文件；`patches_applied` 为空，上游源码零改动。
- 被丢弃目标的独立性核对（均为空即证明零 Qt 依赖）：
  `grep -n "FIND_PACKAGE" UEFIExtract/CMakeLists.txt UEFIFind/CMakeLists.txt`；
  `grep -rn "#include <Q" UEFIExtract/ UEFIFind/`。

## 查重结论（全量池硬查重）

扫 `knowledge/doc/` 541 条 + `knowledge/drafts/` 3853 个文件（共 4394 文件）：

| 锚点 | 命中 | 说明 |
|---|---|---|
| `ADD_SUBDIRECTORY+Qt6` | 3 | `DRAFT-kangaru-…-catch2-submodule-test-requires`（子模块空目录）、`DRAFT-kf6-top-level-component-negotiation`（顶层组件可选化协商）—— 均非本形态 |
| `FIND_PACKAGE+Qt6` | 38 | 全是 find_package 的组件/依赖问题，无一条讲"同级兄弟目录把 CLI 连带阻断" |

**与最近条目的判别点**：

- `DRAFT-kf6-top-level-component-negotiation`：讲的是 **`find_package` 的
  optional components 协商**（把非必需组件移入 `optional_components`、
  在平台适配补丁里放宽版本要求）。层面在"依赖声明"，本条目在"**子目录装载**"。
  已登记为 `similar_to`。
- `E439`（子模块可选组件误设为 `REQUIRED`、依赖膨胀）：层面在 **conan 配方的
  `requirements()`**（不要把非必需模块写进依赖）。本条目在**上游 CMake 树的装载
  结构**，处置方式也不同（E439 改配方，本条目新增构建入口）。已登记为 `similar_to`。

## 可复用判据（速查）

1. 症状是 configure 期 `By not providing "FindXxx.cmake"` / `Could not find a package
   configuration file provided by "Xxx"`，而**你并不需要那个 Xxx 目标**；
2. `grep -n "ADD_SUBDIRECTORY" <root>/CMakeLists.txt` 确认所有子目录都无条件装载；
3. 对被阻断的目标做依赖体检（`FIND_PACKAGE` 与 `#include <Q` 双空）；
4. 处置一律是**新增适配侧构建入口**，不改上游 —— 这样上游零改动且决策可逆。
