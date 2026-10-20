# taopm 1.0：OHOS 的 bison/flex 运行期找不到数据目录与 m4

> 草稿（DRAFT）— 来自 taopm 1.0（`taoparse` 的 bison/flex 生成步骤）真机 `conan create` 实测。
> 与 `.kv` 同 stem 配对：`knowledge/DRAFT-taopm-1.0-ohos-bison-flex-runtime-datadir.kv`

## 问题

`conan create archives/t/taopm/1.0` 在真机上第一次失败在 bison：

```text
taopm/1.0@ohpcd/stable: bison -d -o taoparser.cc --defines=taoparser.h taoparser.yy
bison: /share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory
ERROR: taopm/1.0@ohpcd/stable: Error in build() method, line 264
```

补上 `BISON_PKGDATADIR` 后前进到 flex，又在 m4 处失败：

```text
flex -o taoscanner.cc taoscanner.ll
flex: fatal internal error, exec of /storage/Users/currentUser/.cache/conan2/p/m42d92622f4ed01/p/bin/m4 failed
```

手动验证时（PATH 上没有 m4）bison 还会报：

```text
bison: m4 subprocess failed
```

## 根因

- OHOS 适配的 `bison`/`flex` 包按 `--prefix=/` 打包，`pkgdatadir` 编译进二进制即
  `/share/bison`（`m4sugar/`、`skeletons/` 都在这个目录下）。包被解到 Conan 缓存后，
  这个绝对路径不存在。
- `flex` 还会 **exec m4**：`m4` 的路径是 flex 构建时 configure 得到的绝对路径
  （指向当时的缓存目录），消费端同样不存在。flex 会优先使用 `M4` 环境变量，
  未设置时才回退到编译进去的路径。
- `bison` 也依赖 m4 子进程，m4 不在 PATH 上时表现为 `m4 subprocess failed`。

## 修复（taopm 1.0 配方实际采用，最终版）

```python
def build_requirements(self):
    self.tool_requires("bison/3.8.2")
    self.tool_requires("flex/2.6.4.2")
    # flex shells out to m4; keep it in this build environment
    self.tool_requires("m4/1.4.19")

def _build_tool_folder(self, name):
    """tool_requires 的包目录（build context）。"""
    for collection in ("build", None):
        deps = self.dependencies.build if collection else self.dependencies
        for dep in deps.values():
            if dep.ref.name == name and dep.package_folder:
                return dep.package_folder
    return None

def _build_tool(self, package, binary):
    """<pkg>/bin/<binary>，找不到才回退到裸名字。"""
    folder = self._build_tool_folder(package)
    if folder:
        candidate = os.path.join(folder, "bin", binary)
        if os.path.isfile(candidate):
            return candidate
    return binary

def build(self):
    bison = self._build_tool("bison", "bison")
    flex = self._build_tool("flex", "flex")
    m4 = self._build_tool("m4", "m4")
    bison_data = os.path.join(self._build_tool_folder("bison"), "share", "bison")
    if not os.path.isdir(bison_data):
        raise ConanException(f"bison pkgdatadir missing: {bison_data!r}")
    tool_env = (f'BISON_PKGDATADIR="{bison_data}"; export BISON_PKGDATADIR; '
                f'M4="{m4}"; export M4; ')
    self._run(f'{tool_env}"{bison}" -d -o taoparser.cc --defines=taoparser.h taoparser.yy',
              cwd=parse_src)
    self._run(f'{tool_env}"{flex}" -o taoscanner.cc taoscanner.ll', cwd=parse_src)
```

要点：

1. **工具和数据目录都从 Conan 包目录取**，不用 `command -v` 反推、也不用裸名字调用。
2. `m4` 必须显式进 build env（`tool_requires("m4/1.4.19")`）。
3. 数据目录缺失时**直接报错**，不要静默回退 PATH。
4. flex 不需要 `FLEX_PKGDATADIR`（skeleton 内嵌）；只要 `M4` 可达即可。

## 为什么不能用 `command -v` 反推（CI 实测）

第一版用的是：

```sh
BISON_PKGDATADIR=$(dirname "$(dirname "$(command -v bison)")")/share/bison
```

本机隔离 job 通过，但平台 CI（PR #16744 / 构建 #98634）失败：

```text
taopm/1.0: BISON_PKGDATADIR="$(dirname "$(dirname "$(command -v bison)")")/share/bison"; ... bison ...
bison: /data/service/hnp/share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory
```

CI worker 预装了 `/data/service/hnp/bin/bison`（prefix=`/data/service/hnp`，没有
`share/bison`），它在 PATH 上排在 Conan `tool_requires` 的 `bin` 之前，于是
`command -v bison` / `dirname` 反推出来的数据目录指向一个不存在的位置。
**这类"路径依赖环境"的写法在本机永远测不出来，只能在 CI 暴露。**

## 验证

- 修复前：`taopm-taopm-conan-create-r1` 失败（bison m4sugar）、`r2`–`r6` 逐步推进，
  `r6` 时 taoparse 已能生成但 `taosf` PATH 未处理；
- 最终版（包目录解析）：`taopm-taopm-conan-create-r7`（以及加了 Label guard 后的
  `r8`）`exit-code.txt = 0`，`conan create` + `test_package` 全绿；
- **CI 失败模式回归**：在隔离 job 里把三个假的 `bison/flex/m4` 放到 PATH 最前面
  （内容就是 CI 的那条 `cannot open` 报错），再跑 `conan create` →
  `taopm-taopm-cipath-test-r1` `exit 0`；日志显示实际调用的是
  `<cache>/p/bison.../p/bin/bison`，`BISON_PKGDATADIR=<cache>/p/bison.../p/share/bison`，
  假工具完全没被使用；
- 该修复对任何使用 bison/flex 的 OHOS 配方通用（taopm 只是首个命中者）。
