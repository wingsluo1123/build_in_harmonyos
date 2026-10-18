# DRAFT-conan-test-package-artifacts-pollute-workspace

## `conan create` 的 test_package 会把产物写进你的工作区

### 现象

`conan create archives/…/kdevelop-pg-qt/1.90.92` 之后，`git status` 里突然多出一串
未跟踪文件：

```
?? archives/k/kdevelop-pg-qt/1.90.92/test_package/generated/factparser.cpp
?? archives/k/kdevelop-pg-qt/1.90.92/test_package/generated/factast.h
?? …（共 9 个）
```

日志里其实写了原因，但很容易被忽略：

```
kdevelop-pg-qt/1.90.92 (test package): Test package build folder:
    /storage/…/archives/k/kdevelop-pg-qt/1.90.92/test_package
```

**`conan create <recipe>` 时，test_package 的 build_folder 就是 test_package 目录本身**，
不是缓存里的临时目录 —— 于是测试里任何写文件行为（生成器输出、`.qm`、中间 `.cc/.h`）
都直接落在你的工作区里。

### 为什么会变成事故

提交时顺手写的 `git add archives/k/kdevelop-pg-qt`（整目录）会把这些**一起入库** ——
而它们正是 CI 的 **JC（杂项文件拦截）** 要拦的对象：二进制产物 / 源码 tarball /
临时构建产物。JC 的判据是 **PR diff**，所以合并前必须把历史里的产物清掉。

本仓实测两例：

| 包 | 产物 | 处置 |
|---|---|---|
| kdevelop-pg-qt/1.90.92 | 生成器输出 9 个文件 | `git rm -r --cached` + `--amend` + 对自己的 fork 分支 `--force-with-lease` 订正 |
| qt5-qttools/5.15.2 | 消费测试的 `hello_zh_CN.ts/.qm` | 同法清理 |

### 正解：测试产物写到系统临时目录

```python
import tempfile

# ✗ 不要写 self.build_folder —— conan create 时它就是 test_package 目录
out_dir = os.path.join(self.build_folder, "generated")

# ✓ 用标准库临时目录，并打日志便于排查
out_dir = tempfile.mkdtemp(prefix="kdevpg-qt-test-")
self.output.info("generator output dir: %s" % out_dir)
```

配套习惯：

- 提交前自查 `git status --porcelain | grep test_package`；
- 尽量**逐文件** `git add`，避免整目录 `git add <dir>`；
- 误提交后：`git rm -r --cached <产物>` → `git commit --amend`（自己的 fork 分支可
  `--force-with-lease` 推送；**他人分支严禁强推**）。

### 教训

"build_folder" 这个名字会让人直觉认为它是缓存里的临时目录 —— **不要按直觉假设，
按日志核实**。这类"产物落进源码树"的坑在本地看不出来（构建照样成功），只在提交/
CI 的 JC 阶段炸，属于典型的"当时没感觉、事后很贵"。
