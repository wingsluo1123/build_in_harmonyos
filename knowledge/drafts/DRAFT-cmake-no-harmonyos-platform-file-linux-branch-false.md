# CMake 没有 HarmonyOS 平台文件 ⇒ `if(LINUX)` 分支被静默跳过

## 症状：库自己编得过，消费方链接才炸

opennurbs 8.35 的构建全程顺利（编译 100% ✓），但**消费测试**在链接阶段报：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: z_deflateInit_
>>> referenced by /…/p/lib/libOpenNURBS.so
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: uuid_generate
>>> referenced by /…/p/lib/libOpenNURBS.so
```

## 根因链

configure 日志里其实一直有提示（但很容易被当成噪声）：

```
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org
```

CMake 没有 `Platform/HarmonyOS.cmake` ⇒ 平台布尔变量 **`LINUX` 为假**，而上游用它做
平台相关的库链接：

```cmake
if (LINUX AND NOT ANDROID)
  target_link_libraries( OpenNURBS zlib opennurbs_public_freetype android_uuid)
endif()
```

⇒ 该分支被跳过 ⇒ 共享库**漏链了仓内 vendored 的 zlib / freetype / android_uuid**。
证据（决定性的一步诊断）：

```bash
llvm-readelf -d <pkg>/lib/libOpenNURBS.so | grep NEEDED
#   NEEDED  libc++_shared.so
#   NEEDED  libc.so            ← 只有这两条；本该有 zlib/uuid 却一条都没有
```

因为符号在 `.so` 里是 UND 且没有 DT_NEEDED，**只有消费方链接时才会失败** ——
包自己的 `cmake.build()` 完全看不出来 ✗。

## 修法（一行 cache var）

```python
tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
```

- 本机编译器 target 本就是 `aarch64-unknown-linux-ohos`，把系统名呈现为 Linux 是
  既有做法（仓内 bliss/trilinos 注入 user_toolchain 的同源手段）。
- 用 **cache var**（`-DCMAKE_SYSTEM_NAME=Linux`）以确保覆盖 conan toolchain 里的
  `set(CMAKE_SYSTEM_NAME OHOS)`。
- 修完后 `LINUX` 为真 → 上游那条 `target_link_libraries` 生效 → 消费测试通过 ✓。

## 教训（可迁移）

| 教训 | 说明 |
|---|---|
| **消费测试是必需品，不是装饰** | 这类"库内漏链"缺陷在包自身构建时 100% 不可见；只有以消费方身份链接共享库才能暴露 |
| **`System is unknown to cmake` 不是噪声** | 它是"平台变量分支可能全为假"的先兆；本包正好被它骗过一次 |
| **诊断看 `DT_NEEDED`** | 产物该有哪些动态依赖，一条 `readelf -d \| grep NEEDED` 就能证伪 |

## 次生坑（同一原因的另一面）

把平台呈现为 Linux 后，上游 `if (ANDROID OR LINUX)` 才会把仓内 vendored 子目录
（`freetype263`、`android_uuid`）**纳入配置**；而这类老 vendored 子目录的
`cmake_minimum_required` 常低于 3.5，CMake 4 直接拒绝：

```
CMake Error at android_uuid/CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
  ...
  Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.
```

照报错给的官方开关即可：`CMAKE_POLICY_VERSION_MINIMUM=3.5`（与 kdevelop-pg-qt
踩到的同一个 CMake 4 时代坑）。

## 同一包上的另外三个上游缺口（同类"上游清单/规则不完整"）

1. `fcloseall()` 是 glibc 扩展、musl 没有 ⇒ 把上游**自带的** EOF 回退分支扩到
   `__OHOS__`（单行替换即可；该文件 2881 行源自 Windows，`.patch` 的逐行上下文
   实测无法命中，用 `replace_in_file` 更稳）。
2. `opennurbs_system.h` 引用的 `android_uuid/uuid.h` **不在 install 规则里**
   ⇒ `package()` 补齐安装。
3. 上游 `OPENNURBS_PUBLIC_HEADERS` 清单不完整（源码 179 个 `.h` 只装 169 个，
   被 `opennurbs.h` 第 43 行包含的 `opennurbs_cpp_base.h` 恰在漏装之列）
   ⇒ `package()` 把源码根目录头整套补齐。

共同点：**上游的 install/清单类规则是"作者本机够用"写出来的**，跨平台消费时要按
"消费方需要什么"重新核对一遍，别默认它完整。
