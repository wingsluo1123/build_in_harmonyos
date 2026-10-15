# conan 2 构建环境不注入 host 依赖 bin：configure 找不到构建工具（草稿）

- **软件**：yamcha 0.33（configure 期 `AC_PATH_PROGS(svm_learn)` 硬依赖）
- **构建系统**：conan 2.29.1 + `conan.tools.gnu.Autotools`，Autotools 透传 `--build/--host`
- **平台**：HarmonyOS PC / aarch64，OHOS SDK clang 15（交叉构建：build=macOS armv8 / host=OHOS armv8）
- **状态**：DRAFT（`DRAFT-yamcha-0.33-conan-buildenv-path-injection.{kv,md}` 成对）
- **路径**：路径 B（知识库扩展）

## 相关既有条目（撞车判定）

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| cdcd E688 草稿 | config-script 探测宏（`AM_PATH_LIBCDAUDIO`）找不到 `*-config` 脚本 → 解法 `--with-*-prefix` | 同根（conanbuild PATH 不含 host 依赖 bin），但解法不同：本条给通用 PATH 注入（`prepend_path`）与 `define_path` 覆盖语义陷阱，适配**纯 `AC_PATH_PROGS` 可执行文件**（无 config-script 宏）的场景 |
| E232 | `Conan Autotools.configure` 首进程启动无法被 CONFIG_SHELL 包装（原生 OHOS 直跑 configure） | 启动包装问题；本条是**环境变量注入**问题，互不覆盖，可组合出现 |
| E296 | Conan+Meson 交叉、Windows 构建机的 prefix 派生问题 | Meson 专用，机制无关 |
| E392 | raw makefile（无 configure）三陷阱（codeload 编码器、compiler_executables 取键、make cwd） | raw makefile 族；本条针对 autotools 生成式构建的 configure 期工具查找 |

结论：无条目覆盖"conan 2 VirtualBuildEnv 只注入 build context / host buildenv_info，普通 host requires 的 bindirs 不进 conanbuild PATH"这一机制及 `define_path` 覆盖语义陷阱；与 cdcd E688 部分相关，增量面写清，新建。

## Scope

- 触发面：conan 2.x Autotools 配方，configure 阶段需要 host 依赖提供的可执行文件（`AC_PATH_PROGS` / `AC_PATH_PROG` / 脚本探测宏）；
- 典型：老 autotools 项目把工具路径烘焙进 Makefile（yamcha `training/Makefile` 烘焙 `SVM_LEARN`，tinysvm 同为训练链）；
- 不受影响：纯库链接依赖（`-l` 消费，不需要依赖的 bin）。

## Symptom（真实日志）

修复前（configure 硬失败）：

```
configure:20342: checking for svm_learn
configure:20347: result: no
configure:20350: error: svm_learn required for training
```

修复后（`prepend_path` 注入后，config.log）：

```
configure:20342: checking for svm_learn
configure:20360: found /Users/metyierzhen/.conan2/p/tinyscf5087be4146e/p/bin/svm_learn
configure:20372: result: /Users/metyierzhen/.conan2/p/tinyscf5087be4146e/p/bin/svm_learn
```

## Root Cause

conan 2 的 `VirtualBuildEnv` 生成 conanbuild 环境时只遍历 build context 依赖的 `buildenv_info` 与 host 依赖的 `buildenv_info`；普通 host requires 的 `cpp_info.bindirs` / runenv **不进入 conanbuild PATH**。`requires(..., run=True)` 只把 bin 放进 conanrun（test/运行期）环境，不跨到 configure 期。`environment().define_path("PATH", ...)` 是**覆盖语义**——整条 PATH 被替换，系统 PATH 被清空，configure 随即报 `sed: command not found` / `chmod: command not found` / `cannot create .lineno`（比不注入更早更隐蔽地失败）。正确做法是 `prepend_path` 追加。

## Recommended Fix / Workaround

```python
# conanfile.py
def generate(self):
    env = VirtualBuildEnv(self)
    dep = self.dependencies["tinysvm"]
    env.environment().prepend_path(
        "PATH", os.path.join(dep.package_folder, "bin"))
    env.vars(self).save_script("conanbuild_extra.sh")
```

配合同步兜底：构建系统烘焙的工具路径提供环境变量覆盖（yamcha wrapper 支持 `${SVM_LEARN}`），避免依赖固定绝对路径。

## Fallback

对 config-script 探测宏：显式 `--with-<lib>-prefix=<package_folder>`（宏内直接置脚本变量为绝对路径，绕过 PATH 搜索，cdcd 0.6.6 同法）；无宏的纯 `AC_PATH_PROGS` 则只能 PATH 注入。

## Forbidden Approaches

- `requires("<dep>", run=True)`：runenv 只进 conanrun，configure 期无效，白耗排查时间；
- `environment().define_path("PATH", ...)`：覆盖语义清空系统 PATH，sed/chmod not found 连串报错，复算污染。

## Verification

```
grep -E "checking for svm_learn" <build>/config.log
# 修复后应出现: found <conan2 cache>/p/tinys*/p/bin/svm_learn
conan create <ver_dir> --profile:build=... --profile:host=...   # rc=0
```

## Prevention

写 Autotools 配方前确认 configure 期依赖工具时：先 `prepend_path` 注入依赖 bindirs，再考虑 config-script 宏的 `--with-*-prefix`；永远不用 `define_path` 或 `run=True` 解决构建期 PATH。

## References

- 证据现场：`~/.conan2/p/b/yamch*/b/config.log`、create 迭代日志 `/tmp/yamcha_conan_create{1..8}.log`（失败 2 轮：`svm_learn required for training` → `sed: command not found`）
- 归档：`archives/y/yamcha/0.33/conanfile.py`（generate() 内 prepend_path 实现）
- 相关条目：cdcd E688 草稿、E232、E296、E392
