# 知识库拓展：OHOS 构建环境 itstool 不可用 → `gnome.yelp()` 帮助页构建失败

> 本目录是随 `parlatype/4.3` 适配一起提交的**共性阻塞问题**知识拓展。
> 样例演示库 = `parlatype/4.3` 本体（配方 `../../`）：关掉本策略能复现原始报错，
> 打开即通过（见 §6 实测记录）。

## 1. 触发现象（trigger scenario）

任何使用 `gnome.yelp()` 的 **meson** 项目，在本仓 OHOS 构建环境里编译时会失败，
且失败点固定在帮助页目标，与库本身无关：

实测原文（`parlatype/4.3`，日志见 §6）：

```
FAILED: [code=126] help/cs/index.page help/cs/drag-and-drop.page ... 
<...>/bin/itstool -m help/cs/xyz.parlatype.Parlatype-cs.gmo --lang cs -o help/cs ../help/C/index.page ...
/bin/sh: <...>/bin/itstool: No such file or directory
ninja: build stopped: subcommand failed.
```

注意报错措辞是 `/bin/sh: ...: No such file or directory` —— **文件明明存在**，
是内核执行脚本时**找不到 shebang 指定的解释器**，`/bin/sh` 把这一情形回报成
ENOENT，因此极易被误读成「itstool 没装」。`code=126` 即 command found but
not executable。

或（未引入 itstool 依赖时更早失败）：

```
Program 'itstool' not found or not executable
```

**根因**：itstool 是 python 脚本，本仓（及 OHOS 镜像）提供的 itstool

1. shebang 指向构建机上不存在的解释器 —— `#!/data/service/hnp/bin/python3 -s`；
2. 即便绕过 shebang，python 侧也缺 `libxml2` 绑定
   （`ModuleNotFoundError: No module named 'libxml2'`）。

两种缺失叠加的结果：**命令存在但不可执行** → `code=126`。这不是「没装」，
所以「把 itstool 加进 `tool_requires`」并不能解决（反而把失败点前移到 configure）。

## 2. 适用库范围（applicable libraries）

| 维度 | 范围 |
|---|---|
| 构建系统 | **meson**（`gnome.yelp()` 是 meson 的 gnome 模块函数） |
| 项目族 | GNOME / GTK 栈：`parlatype`、`ghex`、`libgdm`、`libmalcontent`、`kylin-burner` 等 |
| 判定条件 | 源码 `meson.build` 含 `gnome.yelp(` 或 `subdir('help')`，且环境 itstool 不可用 |
| 不适用 | autotools 项目（自带 `--disable-*help*` 开关）；itstool 可用的宿主 |

本仓实测同类实践（同问题、同类处方）共 **32 个配方的 conanfile/patches 触及
itstool/yelp**、13 份 notes 记录 —— 符合「共性问题才入库」口径。

## 3. 限制（limits）

- **只禁用帮助页，不动翻译产物**。LC_MESSAGES 下的 `.mo`（msgfmt/ITS 路径）照常
  构建并随包发布；本包 `share/locale/*/LC_MESSAGES/parlatype.mo` 实测存在。
  因此这**不属于 R40「深度适配不完整」**：被禁的是 yelp 帮助页文档目标。
- 需要帮助页的宿主必须显式 `-Dhelp=true`，且该宿主必须有可用的 itstool。
- 补丁锚点是 `subdir('help')` 与 `meson_options.txt` 尾部；上游大改这两个位置时
  补丁需重新生成（`refresh-patch --auto`）。
- itstool 若哪天在 OHOS 上可用（解释器 + libxml2 绑定齐备），本策略可以整体撤下，
  不影响其他改动。

## 4. 处理策略摘要

补丁在 `meson_options.txt` 增加布尔选项 `help`（**默认 false**），并在 `meson.build`
用 `if get_option('help')` 守卫 `subdir('help')`。完整模板、备选方案取舍与
「为什么不用平台宏/桩」见 **[strategy.md](strategy.md)**。

## 5. 复现方法（reproduce）

```sh
# 前置：本机 patch 必须是可用实现。部分 OHOS 镜像自带 toybox 的 patch 是空实现
#（静默 no-op，退出码 0 却不改文件）——脚本第 3 步会自检并在不可用时 exit 3。
sh detect-gnome-yelp-itstool.sh <源码目录> [构建日志]   # 识别：命中则 exit 1
sh reproduce.sh                                        # 关策略应失败 / 开策略应通过
```

`reproduce.sh` 做两件事（默认每步先 `conan remove` 本包，保证**干净无缓存**环境）：

- **A 关策略**：把本配方复制到临时目录并剥除 yelp 禁用补丁声明，使 `help/` 回到
  上游行为 → 预期 `conan create` **非 0**，日志含 itstool 报错特征；
- **B 开策略**：配方原样 `conan create` → 预期 **0**。

脚本不含任何写死的本地绝对路径：仓库根由脚本自身位置向上推导，也可用
`--skill-root` 显式指定。

## 6. 实测记录（干净无缓存环境）

命令：

```sh
conan remove --confirm parlatype/4.3
conan create <配方目录> -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

| 步骤 | 实测结果 |
|---|---|
| A 关策略（剥除 yelp 禁用补丁） | `exit code = 1`。日志第 1047 行 `FAILED: [code=126] help/cs/index.page ...`，紧随 `bin/itstool -m help/cs/xyz.parlatype.Parlatype-cs.gmo ...` 与 `/bin/sh: <...>/bin/itstool: No such file or directory`，`ninja: build stopped: subcommand failed.` |
| B 开策略（配方原样） | `exit code = 0`。`parlatype/4.3 (test package): [test] test_parlatype.sh PASSED`，`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_parlatype.sh","discovered":10,"passedCount":10}` |

见 `reproduce.sh` 运行输出；完整日志留在工作目录（默认
`$HOME/tmp/parlatype-kb-repro/{skill-off,skill-on}.log`）。

## 7. 文件清单

| 文件 | 作用 |
|---|---|
| `detect-gnome-yelp-itstool.sh` | 问题识别：源码特征 + 环境探测 + 构建日志特征，命中 exit 1 |
| `strategy.md` | 处理策略：补丁模板、备选方案取舍、适用口径、与相邻知识的区别 |
| `reproduce.sh` | 关/开策略双跑复现（含 patch 可用性自检、干净缓存） |
| `README.md` | 本文件：触发场景 / 适用范围 / 限制 / 复现方法 / 实测记录 |
