# E731: HNP cmake 二进制依赖 SDK aarch64-linux-ohos/libc++_shared.so

> Status: **Draft** | severity: `2` | category: `ohos|toolchain|conan|cmake|environment`
> 来源: ecm 6.28.0 依赖项适配（prison 6.28.0 前置依赖）2026-10-03

## 错误特征

```
Error loading shared library libc++_shared.so: (needed by /data/service/hnp/bin/cmake)
Error relocating /data/service/hnp/bin/cmake: _ZdlPv: symbol not found
```

触发时机：`conan create` 在 `CMake.configure()`、`cmake --build`、`cmake --install`
以及 test_package 的 `cmake.configure()` / `test()` 各阶段拉起
`/data/service/hnp/bin/cmake` 时均可能复现。

## 触发条件

1. 目标平台 OHOS（`ci/conan/profiles/ohos-aarch64`），conan create 全流程；
2. 工具链使用 HNP 打包的 CMake（`/data/service/hnp/bin/cmake`，版本 4.1.2）；
3. profile buildenv 的 `LD_LIBRARY_PATH` 只含 `llvm/lib` 顶层，不含
   `llvm/lib/aarch64-linux-ohos`（libc++_shared.so 实际所在子目录）。

## 根因

- HNP 的 cmake 二进制动态链接 `libc++_shared.so`（`readelf -d` 可见 NEEDED）；
- SDK 的 `libc++_shared.so` 位于 `llvm/lib/aarch64-linux-ohos/` 子目录，
  `llvm/lib` 顶层没有该库；
- conan profile `[buildenv]` 只加了顶层 `llvm/lib`，加载器按 soname 找不到
  libc++_shared.so → 进程启动失败 → 所有后续阶段全部中断。

与 E540 的差异：E540 是 shadow CI runner 的 **PATH** 缺 `/data/service/hnp/bin`
（make not found）；本条目是 conan create **内部** LD_LIBRARY_PATH 缺 SDK
子目录（cmake 二进制加载 libc++_shared.so 失败）。两者同为 HNP 工具链路径
类问题，但缺失变量、缺失目录、触发场景均不同。

与 DRAFT-8960（libei）的差异：DRAFT-8960 是 meson/ninja 场景，ninja 依赖
`/system/lib64/libc++_shared.so`，解决方式是前置干净的 `/system/lib64`；
本条目是 CMake/cmake 场景，cmake 依赖 **SDK** 的 `aarch64-linux-ohos`
子目录，解决方式前置 SDK lib 目录（顶层 + 子目录），且需覆盖
build/package/test 全阶段（test_package 的 configure/build/test() 都要）。

## 解决方案

conanfile.py 的 `generate()` 中用 `Environment` 将 SDK lib 目录前置到
`LD_LIBRARY_PATH`，并 `save_script` 持久化（覆盖 build/package/test 全阶段）：

```python
import glob, os
from conan.tools.env import Environment

def generate(self):
    tc = CMakeToolchain(self)
    # ... 其他变量 ...
    tc.generate()
    self._sdk_runtime_env().vars(self).save_script("sdk_runtime_env")

def _sdk_runtime_env(self):
    env = Environment()
    sdk_base = os.environ.get("OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
    sdk_libs = sorted(glob.glob(os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib")))
    for lib_dir in sdk_libs:
        env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        sub = os.path.join(lib_dir, "aarch64-linux-ohos")
        if os.path.isdir(sub):
            env.prepend_path("LD_LIBRARY_PATH", sub)
    return env
```

test_package/conanfile.py 同样需要注入（其 configure/build/test() 也拉起
cmake 并运行被测二进制）。

## 适用边界

- 适用：OHOS 上所有使用 HNP cmake 工具链的 CMake 系 conan 配方
  （KDE Frameworks 组件、依赖 HNP cmake 的第三方库）。
- 不适用：不使用 HNP cmake（如自带工具链、纯脚本构建）的配方；
  Linux 原生环境无此问题（cmake 不依赖 SDK libc++_shared.so）。

## 验证证据

- 修复前：`conan-verify ecm 6.28.0` G2 必现 `Error loading shared library
  libc++_shared.so`（conan-create.log 第 81-82 行）。
- 修复后：`conan-verify ecm 6.28.0` G0-G4 全部通过；
  `conan create` 主包 configure/build/install + test_package
  configure/build/test() 全绿。
- 手工验证：`LD_LIBRARY_PATH="$SDK/aarch64-linux-ohos:$SDK" \
  /data/service/hnp/bin/cmake --version` 输出 `cmake version 4.1.2`。

## 关联条目

- `similar_to`: E540（HNP 工具链路径类，但 PATH vs LD_LIBRARY_PATH、
  runner vs conan create 内部、make vs cmake）
- `similar_to`: E520（同为 Error relocating symbol not found / LD_LIBRARY_PATH
  缺失类，但 E520 是 Qt 宿主工具 qsb 缺 Qt 依赖包 lib 路径，方案为
  cmake -E env 注入；本条目是 HNP cmake 二进制缺 SDK libc++_shared.so，
  方案为 generate() Environment 注入 + save_script 全阶段覆盖）
- `similar_to`: DRAFT-8960（libei：ninja 依赖 /system/lib64/libc++_shared.so，
  同为工具链二进制动态依赖 libc++_shared.so，但工具、缺失目录、覆盖阶段不同）
