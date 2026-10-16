# DRAFT: KDE Frameworks 依赖图版本冲突——已发布配方不直接改，升版本重新发布

> 状态: 本地知识草稿，未提交、未发布、未关联任何远端。
> 本文档对应同一 stem 的 `.kv` 结构化版本，字段与 KV 逐字节语义配对。
> 范围声明：本文档是可复用的诊断证据与规则草稿；不声称创建了任何源码补丁、框架改动、远端 PR、Issue 或正式知识条目。
> 不含凭据、令牌、主机私有值、远端成功声明或不可验证证据链接。

## topic

KF5/KF6 适配里，多个框架配方各自声明不同版本的基础库（如 `qt5-qtbase`），Conan 图只允许每个包名一个版本，于是 configure 阶段直接失败；正确处理是**不修改已发布配方**，按 R37 升版本重新发布，或在该配方上用 `force=True` 显式钉住一个版本。

## error_signature

```
ERROR: Version conflict: Conflict between qt5-qtbase/5.15.2 and qt5-qtbase/5.15.2.2
       in the graph. ... Version ranges and conflicts must be resolved.
```

或在下游表现为 configure 找不到某个基础库的头文件/CMake 配置（因为解析到了另一个版本）。

## wrong_turns

1. **直接改已发布配方的版本要求**。已发布版本对外可见，改动会让同一 version 在不同时间产生不同制品，账目与复现都失效。
2. **在下游配方里临时引入/内联一个基础库**（例如把 qtbase 的改动塞进 kservice5）。依赖问题被藏在叶子配方里，其它消费者仍会命中。
3. **只看单个库的 `conan install` 成功**就判定无冲突。冲突只在**整图**里出现，单库安装可能恰好只解析到自己那一支。

## root_cause

Conan 2 的图中每个包名只允许一个版本。KF5 这一族配方的依赖是逐层叠加的：

```
qt5-qtbase/5.15.2.2
  ├── kcoreaddons5/5.116.0.1
  │     ├── kpty5/5.116.0        （+ ki18n5/5.116.0）
  │     └── kservice5/5.116.0    （+ kconfig5/5.116.0, kdbusaddons5/5.116.0, ki18n5/5.116.0）
  └── kconfig5/5.116.0
        └── kactivities5/5.116.0 （+ kwindowsystem5/5.116.0, qt5-qtdeclarative/5.15.2.1, qt5-qtsql/5.15.19）
```

只要其中任一配方声明了不同版本的 `qt5-qtbase`（例如 kcoreaddons5 写 `5.15.2`、ki18n5 写 `5.15.2.2`），整图解析即失败。上层到底层是共享的：任何一个叶子改版本，都会波及所有同图消费者。

## detection

```
conan graph info --requires=kservice5/5.116.0 --format=html > graph.html
# 或直接看冲突包：
conan graph info --requires=kservice5/5.116.0 2>&1 | grep -i conflict
```

`conan list "<pkg>/*" -r ohpcd` 用来确认**已发布**了哪些版本——决定是"能用现成版本解决"还是"必须升版本重新发布"。

## affected_scope

所有 KF5/KF6 叠加适配（kcoreaddons5 → kpty5/kservice5 → kactivities5 这一族），以及任何共享基础库（qtbase、ecm、ki18n5）的框架栈。当前仓库里 `kcoreaddons5` 同时存在 `5.116.0` 与 `5.116.0.1` 两个版本，正是这条规则作用的结果。

## durable_solution

1. **先查已发布版本**：`conan list "<pkg>/*" -r <remote>`，以现有版本尝试解决。
2. **同一图内显式钉住一个版本**：在各兄弟配方上对该依赖写

   ```python
   self.requires("qt5-qtbase/5.15.2.2", force=True)
   ```

   `force=True` 让该声明覆盖其它分支的版本要求，图因此收敛到唯一版本。本仓库的 KF5 配方已统一采用该写法。
3. **必须改配方内容时，按 R37 升版本重新发布**，不在已发布版本上原地修改。版本号递增（`5.116.0` → `5.116.0.1`）并走独立分支与独立验证。
4. **不把基础库改动混入叶子配方**。若冲突的根因确实是基础库本身缺东西（如需要 `-make tests -feature-private-tests` 的 qtbase），那是**独立任务**：独立分支、独立 PR、独立验证。

## verification

- `conan graph info` 输出中不再出现 `Version conflict`。
- 冲突包在全图只剩一个版本：`conan graph info ... | grep qt5-qtbase` 应只出现一行版本。
- 升版本后必须对该版本**重新跑完整真机验证**，不能沿用旧版本的结果。

## recovery_condition

出现以下任一情况即应重新调查：上游发布了新的基础库版本使现有钉法失效；新增的兄弟配方未使用同一钉法从而重新引入冲突；有人直接在已发布版本上修改了 conanfile；图中出现同一包名的两个版本。
