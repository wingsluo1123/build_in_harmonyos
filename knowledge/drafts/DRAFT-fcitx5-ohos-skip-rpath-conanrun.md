# DRAFT: OHOS 加载器拒绝 RUNPATH 指向 conan 缓存目录的共享库

## 现象

conan create 的 test_package 消费者运行时，库自带 `DT_RUNPATH` 指向 conan 缓存
目录（`<cache>/p/lib`）时：

```
Error loading shared library libFcitx5Core.so.7: (needed by ./test_fcitx5)
Error relocating ./test_fcitx5: _ZN5fcitx15SemanticVersion5parse...: symbol not found
```

dlopen 该库（绝对路径）同样报 `Permission denied`；把同一文件复制到任意普通
目录、chmod 777 均无效。去掉 RUNPATH（`CMAKE_SKIP_RPATH=ON` 重建）并以
`LD_LIBRARY_PATH`（conanrun 环境）提供路径后即可正常加载。

## 根因

conan 2.29 的 `CMakeToolchain` 中 `SkipRPath` block（blocks.py）默认
`skip_rpath=False`——即**不**设置 `CMAKE_SKIP_RPATH`，CMake 在 install 阶段
自动给共享库写入 `DT_RUNPATH` 指向安装前缀（即 conan 包缓存目录）。
OHOS 加载器（bionic/musl 式）实测拒绝加载 RUNPATH 指向用户可写缓存目录的库，
报 `Permission denied`。这是「SONAME 正常但 RUNPATH 污染」场景，与 DRAFT-13577
（无 SONAME → DT_NEEDED 记录绝对缓存路径）机制不同、互为补充。

## 解决方案

1. 配方 `generate()`：
   ```python
   tc.cache_variables["CMAKE_SKIP_RPATH"] = "ON"
   tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"  # 另见 SONAME 草稿
   ```
2. test_package 用 conanrun 环境运行消费者（LD_LIBRARY_PATH 自动含被测包与依赖 lib）：
   ```python
   def test(self):
       self.run(os.path.join(self.cpp.build.bindirs[0], "test_consumer"), env="conanrun")
   ```

## 验证

- `readelf -d <lib>` 无 `RUNPATH`/`RPATH`；
- 无 RUNPATH 库 + `LD_LIBRARY_PATH=<pkg>/lib:<deps>` 消费者 dlopen/运行 OK；
- 带缓存 RUNPATH 库一律 `Permission denied`（对照实验，fcitx5/5.1.14 实测）。

## 适用边界

OHOS（HarmonyOS PC, aarch64）上所有通过 conan create 安装共享库并在 OHOS 运行
消费者的配方；与 DRAFT-13577（DT_NEEDED 绝对路径）、DRAFT-cmake-harmonyos-
system-name-soname（SONAME 缺失）互补。

## 相关条目

- DRAFT-13577-ohos-stale-absolute-dt-needed-cache-path
- DRAFT-cmake-harmonyos-system-name-soname
- E073（HMDFS .so 加载）、E077（RPATH/RUNPATH permission denied）