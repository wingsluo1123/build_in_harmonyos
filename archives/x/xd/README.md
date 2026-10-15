# xd

`xd`（eXtra smart Directory changer）是 Frank B. Brokken 开发的智能 `cd` 辅助工具：
把命令行参数按 `/`、`-` 或逐字符切分成嵌套目录名的**首字母**，展开出候选目录；
唯一候选时把目录绝对路径写到 stdout，供 shell 侧 `cd` 使用。

## 功能概述

- 首字母展开：`xd uic4ib` 相当于 `cd /usr/include/c++/4.3/i486-linux-gnu/bits`
- 起始点语法：`0` = 当前目录，`/` = 根，`1..9` = 上 N 级，`.` = 家目录（可配置）
- 多种展开模式：默认传统模式（要求目录分隔符）与 `--generalized-search`（GDS）
- 配置文件 `$HOME/.xdrc`（或 `--config-file`）：`ignore`、`start-at`、`add-root`、
  `history*`、`block-size`、`directories`、`icase`、`homedir-char` 等指令
- 历史记录：`--history <file>` 记录并优先显示此前选择
- `--input`：非选择字符结束时通过 `TIOCSTI` 把内容注入 shell 输入流

## OHOS 适配

- 上游 icmake 构建工具不在 OHOS 依赖链中（W0b：ohpcd 制品仓无 icmake），
  本仓配方（`5.00.03/conanfile.py`）以 Python 复刻 `icmbuild program` 的编译/链接语义。
- 依赖仓库内已适配的 `bobcat/6.14.00`（上游 `libbobcat-dev >= 3.11.01`）。
- **C++20 起**：bobcat 公共头使用 C++20 特性，消费者编译时也应使用 `-std=c++20`。
- 源码补丁 2 个：`patches/0002` 修上游 `Command::splitBase()` 的迭代器失效（libstdc++ 侥幸可用、libc++/OHOS 读到乱码并 SIGTRAP）；`patches/0001` 处理下述 HMDFS 大小写冲突。
- 卡在如上 HMDFS 大小写：上游 tarball 根级的 `VERSION`（文件）与 `version/`（目录）在
  **HMDFS（大小写不敏感）** 上同名冲突，`source()` 以 `excludes=["*VERSION"]` 排除该文件，
  并由 `patches/0001` 把其 `AUTHOR/VERSION/YEARS` 三个宏内联回 `version/version.h`。
- `<linux/input.h>` 仅出现在 `documentation/kbd/*` 文档演示程序里，不在构建范围。
- OHOS 对 `TIOCSTI` 有安全限制：`--input` 在受限环境下 ioctl 返回 -1 时 xd 会把
  诊断写到 `imsg`（默认 stderr）并正常结束；常规用法（stdout 输出目录路径，
  shell 侧自行 `cd`）不受影响。

## 依赖关系

- 编译依赖：`bobcat`（C++ 库），C++20 工具链
- 运行依赖：`libbobcat.so.6`、`libc++_shared.so`、`libc.so`
- 文档构建（可选）：yodl（本仓不构建 man/manual）

## 参考资料

- 上游仓库：https://gitlab.com/fbb-git/xd
- 项目主页：https://fbb-git.gitlab.io/xd/
- 配置样例：`xd/xdrc`（随包安装到 `share/xd/xdrc`）

## bin/ 交付物

| 文件 | 说明 |
| --- | --- |
| `bin/xd` | 唯一的可执行文件（aarch64-linux-ohos ELF） |
| `share/xd/xdrc` | 配置文件样例（上游 `./build install` 的文档组件） |
