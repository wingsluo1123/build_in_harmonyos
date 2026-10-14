# DRAFT — conan `build()` 内跑 pytest：子进程 env 缺 `LD_LIBRARY_PATH`，CPython 扩展 `dlopen` 全数失败

> 触发事件：greenlet 3.5.6 HarmonyOS PC 适配（PR #10408）第 3 轮 CI。
> `conan create` 的上游测试步骤在收集期报 **15 errors / 0 collected，0.24s 即结束**
> （2026-10-02 CI 实测）。

## 相关既有条目（同族差异化定位）

全库查重（`knowledge/graph/index.tsv` + `knowledge/graph/E*.kv` + `knowledge/drafts/`）：

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E736`（cmake/ctest） | 正式 | `CMAKE_SYSTEM_NAME=HarmonyOS` 无平台模块 → rpath 标志缺失，构建树内 **ctest** 加载共享库失败，应在测试命令注入 `LD_LIBRARY_PATH` | E736 的注入点是 **ctest**（CMake 项目）；本条是 **pytest 子进程**加载 CPython 原生扩展，且根因是「子进程 env 取自 `dict(os.environ)`，而编译期那份路径不在 os.environ 里」 |
| `DRAFT-pyjson5-0.15.0-test-package-python-libdirs-ld-library-path` | 草稿 | `test_package` **显式调用** conan python **二进制**时须注入 `cpp_info.libdirs` | 同为「运行期补 `LD_LIBRARY_PATH`」家族，但那条是**显式执行 python**；本条是 pytest **隐式 dlopen 扩展**，且强调「buildenv 不进 os.environ」这一不对称 |
| `DRAFT-binary-sign-tool-buildenv-ldlibrarypath` | 草稿 | 反向问题：buildenv **多了** `LD_LIBRARY_PATH` 反而毒害 `binary-sign-tool`，需 `env -u` | 那条要**剔除**该变量，本条要**补充**该变量；两者共同说明「buildenv 与子进程实际环境不是一套」 |

**结论：本条为真增量**（无 E 编号条目覆盖「pytest 子进程 + CPython 扩展 + 缺 LD_LIBRARY_PATH」）。

## 错误特征

```
ERROR src/greenlet/tests/test_generator_nested.py
ERROR src/greenlet/tests/test_greenlet.py
... （15 个测试文件全数 ERROR）
!!!!!!!!!!!!!!!!!!! Interrupted: 15 errors during collection !!!!!!!!!!!!!!!!!!!
no tests collected, 15 errors in 0.24s
```

**辨识要点（最易误判处）**：症状是**所有**测试文件**同时**在收集期 ERROR，而不是
个别用例 FAILED；总耗时 0.24s，符合「导入阶段就挂」。若看到「一批文件齐刷刷 import 失败」，
应立刻怀疑**共享库解析**而非测试本身。

## 根因分析

### 要点 1：扩展 `NEEDED` libpython 且**无 RUNPATH**

配方绕开 setuptools，直接用 `-L<py_lib> -lpython3.12 -fuse-ld=bfd` 编译扩展。
产物实测：

```
NEEDED  libpython3.12.so.1.0
NEEDED  libc++_shared.so
NEEDED  libc.so
（无 RPATH / RUNPATH 条目）
```

无 RUNPATH ⇒ 加载器只能靠 `LD_LIBRARY_PATH` 或系统默认路径找到 `libpython3.12.so.1.0`。

### 要点 2：**编译期**设了 `LD_LIBRARY_PATH`，**测试期**没有

```
编译步骤： env_prefix = 'export LD_LIBRARY_PATH="<ld_path>" && ...'   ← 有
测试步骤： env = dict(os.environ)                                     ← 没有
```

而配方进程的 `os.environ` 里**本来就没有**该变量（实测 unset）：conan profile 的
`[buildenv]` 只作用于 `self.run()` 派生的子进程，**不会写回配方的 `os.environ`**。
两者叠加 ⇒ pytest 子进程加载扩展时找不到 libpython ⇒ 每个 import 扩展的测试文件都失败。

### 要点 3：设备端与 CI 的差异会掩盖它

设备端加载器的默认搜索路径可解析到该库，故**单独跑**能通过；CI worker 上才暴露。
即这条问题在本地「看起来是好的」。

## 推荐方案

`build()` 编译期算出的 lib 目录集合（python 制品 `lib` + 各依赖 `lib`）存到
`self._ld_path`，跑 pytest/ctest 前**前置拼接**进子进程 env：

```python
env["LD_LIBRARY_PATH"] = os.pathsep.join(
    [self._ld_path] + [p for p in (os.environ.get("LD_LIBRARY_PATH", ""),) if p])
```

先新后旧、不覆盖已有值。备选是编译期加 `-Wl,-rpath,<py_lib>`（让产物自带 RUNPATH），
但 musl/OHOS 下 rpath 支持需先验证（E736 记录过 `CMAKE_BUILD_RPATH` 静默无效），故列为备选。

## 禁止做法

- ❌ **不要**靠 `import <pkg>` 成功就断定扩展可加载：顶层 `__init__.py` 可能根本走不到 dlopen 那一步。
- ❌ **不要**把「收集期整片 ERROR」当成「用例失败」去改测试 —— 方向完全错。
- ❌ **不要**用 profile `[buildenv]` 的 `LD_LIBRARY_PATH` 指望它对 pytest 子进程生效：
  它只进 `self.run()` 的子进程，不进 `os.environ`。

## 验证证据

- **主证据（CI）**：greenlet 3.5.6 / PR #10408 第 3 轮，`15 errors / 0 collected / 0.24s`。
  前一轮同套件在注入 pygments 后已能启动 pytest，可见是「加载期」而非「用例期」。
- **产物实测**：`llvm-readelf -d <ext>.so` → 三条 `NEEDED`、无 `RPATH/RUNPATH`。
- **环境实测**：配方进程 `LD_LIBRARY_PATH` = unset（编译期靠 `env_prefix` 显式设置）。

### ⚠️ 证据强度声明（务必阅读）

**本条是「环境不对称」推断，本机未能复现 CI 的失败。** 本机 `LD_LIBRARY_PATH` 已 unset、
`/etc/ld.so.conf.d/` 为空，但加载器仍能经默认路径解析到 `libpython3.12.so.1.0`，
故本机清空该变量后 `import greenlet` 仍成功、本地收集亦通过（154 collected）。
因此本条的「修法」是基于 `NEEDED` 记录与编译/测试环境不对称推出的，**非实测确认**。
`metrics_confidence` 记为 0.5。若后续 CI 证明无效应及时降级或修订。

## 查重结论

- 对 `pytest` + `LD_LIBRARY_PATH` 检索：命中 E736（ctest）、pyjson5（显式 python 二进制）、
  binary-sign-tool（反向剔除）、boost/flang（静态链接）等，**机制均不同**。
- 对「子进程 env 取自 os.environ、buildenv 不生效」检索：无同机制条目，本条为真增量。
- **盲区声明**：基于本地已合并知识（本地 main + 本分支），无法排除外部有人提交过同主题草稿。
