# E750：package() 阶段 cmake.install() 裸跑 hnp cmake 触发 libc++ relocation 失败（Error 127）

## 错误特征

```
Error relocating /data/service/hnp/bin/cmake: _ZTINSt4__n119__shared_weak_countE: symbol not found
Error relocating /data/service/hnp/bin/cmake: _ZTINSt4__n18ios_base7failureE: symbol not found
...（海量 std::__1 符号族）
ERROR: kunitconversion5/5.116.0: Error in package() method, line 379
	cmake.install()
	ConanException: Error 127 while executing
```

## 根因

OHOS PC CI 的宿主工具链 cmake 与签名工具（binary-sign-tool）位于 `/data/service/hnp`，其 ELF 依赖 LD_LIBRARY_PATH 中的**兼容 libc++** 才能完成动态链接。

- conan 的 build()/test() 阶段默认经 `_runtime_env` 包装（注入 hnp 兼容库路径）→ 正常；
- package() 阶段直接裸调 `cmake.install()` → 无包装环境 → musl 加载器解析 hnp cmake 的 libc++ 符号全部落空 → 海量 `Error relocating /data/service/hnp/bin/cmake: ... symbol not found`，退出码 **127**。

**判定要点**：日志出现 "Error relocating /data/service/hnp/bin/..." 符号族 + 退出码 127 = 加载器层 libc++ 符号缺失，**不是 cmake 脚本错误**——换环境包装而非改 CMake 逻辑。同一构建中 build 阶段已跑通、package 死掉，反差即定位线索：凡是"裸跑 hnp 宿主工具"的步骤都会踩同一边界（CI Worker 环境边界）。

## 解法

package()（及一切裸跑 hnp 宿主工具的步骤）必须与 build() 同样包在 `_runtime_env` 包装下：

```python
def package(self):
    cmake = CMake(self)
    # The host cmake (and the OHOS signing tools below) live under
    # /data/service/hnp and need the compatible libc++ on
    # LD_LIBRARY_PATH; without the wrapper the loader fails with
    # "Error relocating cmake: symbol not found" (same env as build()).
    with self._runtime_env().vars(self).apply():
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()
```

## 降级方案

不重构 `_runtime_env` 时，可在 package() 显式 `os.environ` 注入 hnp 兼容 libc++ 的 `LD_LIBRARY_PATH` 再 `cmake.install()`（等效但重复代码）。均不如统一包装——build/test/package 三阶段同一环境语义，避免阶段间环境漂移。

## 实证

kunitconversion5 5.116.0（PR !14840，j669539）：build1 修复前 package() 死于 `Error 127 while executing cmake.install()`（build1.log 3960-4013 行海量 Error relocating 符号族）；加包装后 build2 干净重跑（conan remove 后 conan create）rc=0 全绿，构建/打包/签名全链通过。
