# DRAFT: 单体仓（monorepo）里「无独立 tag」的子组件如何取源与建树

> 草稿（DRAFT）。与同目录
> `libusbauth-configparser-1.0.5-monorepo-subdir-pinned-commit-flatten.kv` 成对。
> 实证来源：libusbauth-configparser 1.0.5 适配 HarmonyOS PC，2026-10-08。
> 上游 monorepo = `kochstefan/usbauth-all`，组件子目录 = `libusbauth-configparser/`。

## 现象 / 问题

上游是**一个 git 仓库、多个组件各占一个子目录**，每个子目录自带
`configure.ac` / `Makefile.am`（或 `CMakeLists.txt`）。本仓要交付的
`libusbauth-configparser` 只是其中一个子目录，且**它没有独立 tag**：

```console
$ git ls-remote --tags https://github.com/kochstefan/usbauth-all | tail
# （空：仓库没有 tag）

$ curl -sI https://github.com/kochstefan/usbauth-all/archive/refs/tags/1.0.5.tar.gz | head -1
HTTP/2 404                       # 没有 tags/1.0.5 这样的组件级 tag
```

于是两个直觉性做法都不成立：

1. **按 `archive/refs/tags/<ver>.tar.gz` 取源** → 组件没有 tag，404（或
   取到整仓某个代次，与你要的组件版本不对应）。
2. **把整仓当包子树跑构建** → `get()` 拿到的是 `usbauth-all-<sha>/`，组件
   树在其下的 `libusbauth-configparser/` 子目录里；在源根跑
   `autoreconf`/`configure` 会直接报：

   ```
   autoreconf: 'configure.ac' or 'configure.in' is required
   ```

   或 `configure: No such file or directory`。

叠加一点：该快照是**纯 git 归档**，不含生成物，`libusbauth-configparser/`
里根本没有 `configure`（只有 `configure.ac` + `Makefile.am`），必须自举。

## 根因

「组件粒度成包」与「上游仓库的组织方式」不一致：

- 制品仓/发行版按**组件**建包（`libusbauth-configparser` 是一个独立包）；
- 上游按**仓库**组织，tag 是整仓的（或没有），组件版本只写在**子目录的构建
  脚本**里（autotools 的 `AC_INIT` 第二参、CMake 的 `project(... VERSION)`）。

**组件版本的唯一权威来源不在 URL 里，而在子目录的构建脚本里。** 所以取源
必须「钉定 commit」，建树必须「把子目录提升为源根」，二者缺一不可。

## 解决方案（HOW-TO）

### 1. 版本号：从子目录构建脚本读

```console
$ grep -n AC_INIT libusbauth-configparser/configure.ac
16:AC_INIT([libusbauth-configparser], [1.0.5], [stefan.koch10@gmail.com])
```

`1.0.5` 即组件版本。**核验**这个代次确实是你想交付的那一代（对比
CHANGELOG / 发布说明），再据此选 commit。

### 2. 取源：官方 codeload 的 commit 端点

```yaml
# conandata.yml
sources:
  url: "https://codeload.github.com/kochstefan/usbauth-all/tar.gz/d40b9790f776e698bd84b42ea5555c29ed3fbfee"
  sha256: "7dc6aa9323ea6de56f0add4c06a72b1efebdc4d49461604c2d6f17e79ddc2ce8"
```

- 用 **40 位完整 commit sha**（截断会解析到浮动分支或非预期树）；
- `sha256` 本地下载后算，写全 64 位十六进制；
- **不要**用 `refs/tags/…`（组件可能没 tag）。

### 3. 建树：source() 里把子目录上提为源根

```python
def source(self):
    get(self, **self.conan_data["sources"]["1.0.5"], strip_root=True)
    # strip_root 去掉 <repo>-<sha>/ 这一层，剩下的根下是各组件子目录
    sub = os.path.join(self.source_folder, "libusbauth-configparser")
    for name in os.listdir(sub):
        shutil.move(os.path.join(sub, name), os.path.join(self.source_folder, name))
    os.rmdir(sub)
    apply_conandata_patches(self)   # 注意：上提之后再打补丁
```

上提之后，`source_folder` 根下直接有 `configure.ac` / `Makefile.am` / `src/`
/ `data/`——autotools 这才是一棵自洽的树。

### 4. 补丁路径：相对**上提后的源根**

`apply_conandata_patches()` 以 `source_folder` 为 base。既然文件已上提到
`src/usbauth-configparser.c`，补丁里就要写：

```diff
--- a/src/usbauth-configparser.c
+++ b/src/usbauth-configparser.c
```

而**不是** `libusbauth-configparser/src/usbauth-configparser.c`。搞错这一步，
`patch -p1` 会找不到文件（`can't find file to patch`），配方却继续用未打补丁
的源码——OHOS 差异（本例：只读 `/etc` 的路径覆盖）会静默丢失。

### 5. 快照无 configure：autoreconf -fi 自举

```python
def build_requirements(self):
    self.tool_requires("automake/1.18")
    self.tool_requires("libtool/2.5.4")

def generate(self):
    VirtualBuildEnv(self).generate()     # 把上面 tool_requires 的 bin 注入 conanbuild PATH
    AutotoolsToolchain(self).generate()

def build(self):
    self.run("env -u CONFIG_SHELL SHELL=/bin/sh autoreconf -fi",
             cwd=self.source_folder, env="conanbuild")
    ...
```

`autoconf` 家族与 `flex`/`bison` 通常已在设备 toolchain
（`/data/service/hnp/bin`，见 libpll）；`automake`/`libtool` 往往没有，须经
`tool_requires` 拉入，并用 `VirtualBuildEnv` 注入 PATH。

## 判据 / 何时命中本型

- 上游仓库里候选组件子目录**各自**有 `configure.ac`/`CMakeLists.txt`，而
  `git ls-remote --tags` 里**没有**对应的组件级 tag；
- `tar tzf <tarball>` 顶层是 `<repo>-<sha>/`，组件是它的下一层子目录；
- 组件版本只出现在子目录的构建脚本里（`AC_INIT` / `project(VERSION)`）。

同型征候还包括：发行版按组件拆包的「*-all / *-tools」聚合仓、GNOME/KDE 当
只有整仓 tag 时的 individual-component 子项目。

## 与相邻草稿的关系

- **`component-split-from-umbrella-tarball`（同族，但不同型）**：那型是
  「一份 tarball 用**目录级**构建入口（Kbuild 的 `all:`）拆组件」，版本沿父
  发行版；本型是「一个 git 仓库里**每个组件都是自洽子项目**，各带自己的构建
  脚本」，版本从子目录读、源用 commit 钉定、子目录上提为源根。
- **`DRAFT-indi-aok-plugin-subproject-monorepo-cmake`**：monorepo 里的插件式
  **CMake** 子项目，难点在靠仓库级 `Find*.cmake` 定位依赖；本型难点在**取源
  + 建树**，与依赖查找无关。

## 参考

- `archives/l/libusbauth-configparser/1.0.5/conanfile.py` —— `source()` 上提子目录 + `autoreconf -fi`
- `archives/l/libusbauth-configparser/1.0.5/conandata.yml` —— commit 钉定的 codeload 源
- `archives/l/libusbauth-configparser/1.0.5/manifest.yaml` —— `version_mapping` 记录 monorepo commit ↔ 组件版本
- `archives/l/libpll/0.3.2/conanfile.py` —— 无 configure 的 git 快照 + autoreconf 自举（同为 flex/bison 项目）
