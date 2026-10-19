# E543-draft — test_package generate() 裸调 llvm-ar 依赖进程 PATH

## 现象

PR #13558（or-tools 9.15 适配）构建 #66056 在 **conan-build-test** 步骤失败，
主包编译与安装均成功（日志出现 `-- Installing: .../include/ortools/...`），
失败点仅在 test_package 阶段：

```
subprocess.run(
FileNotFoundError: [Errno 2] No such file or directory: 'llvm-ar'
[fail] or-tools/9.15 — conan create failed
```

失败代码在 `test_package/conanfile.py` 的 `generate()`：

```python
subprocess.run(
    ["llvm-ar", "d", pruned_lib, "model_builder_helper.cc.obj"],
    check=False,
)
```

## 为什么本地通过、CI 失败

- 本机 shell PATH 含 `/data/service/hnp/bin`（`which llvm-ar` → 命中该目录），
  本地 conan create 时 `generate()` 内 subprocess 能找到 `llvm-ar`；
- CI worker 由 buildbot 启动，环境 PATH 为
  `/data/app/bin:/system/bin:/system/sbin:/vendor/bin:/storage/Users/currentUser/.local/bin`
  —— **不含** `/data/service/hnp/bin`；
- profile `[buildenv]` 的 `PATH=+(path)/data/service/hnp/bin` 只在 conan
  脚本执行阶段（build()/test()）生效，**不会注入 generate() 内 Python
  子进程**，于是裸调工具名报 FileNotFoundError。

结论：**本地通过不能作为 CI 依据**，必须模拟 CI worker 无工具链目录的 PATH。

## 修复

不要裸调 llvm-ar。在 `generate()` 中从
`tools.build:compiler_executables` 读取 c/cpp 编译器路径，取其目录拼接
llvm-ar 绝对路径（E012/E528 与 glib-networking、gtk4、gnome-autoar 的
test_package 同款模式）：

```python
executables = self.conf.get(
    "tools.build:compiler_executables", default={}, check_type=dict
) or {}
compiler = executables.get("c") or executables.get("cpp") or ""
bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
ar_tool = os.path.join(bindir, "llvm-ar")
if not bindir or not os.path.isfile(ar_tool):
    ar_tool = shutil.which("llvm-ar") or "llvm-ar"
subprocess.run([ar_tool, "d", pruned_lib, "model_builder_helper.cc.obj"],
               check=False)
```

验证：用与 CI 相同 profile 跑 `conan test <test_package> or-tools/9.15`，
可精确复现 generate() 阶段；修复后 ctest 用例通过。

## 关联

- E012：configure/make 阶段 `ar not found`，设置 `AR=llvm-ar` 环境变量
  （autotools 场景）；本条目是其 test_package 子进程场景的补充。
- E528：从 `tools.build:compiler_executables` 推导工具目录（同源思路）。
