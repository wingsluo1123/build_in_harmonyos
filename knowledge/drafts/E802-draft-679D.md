# E802 — 公共头 include 传递依赖的头文件时，requires() 必须声明 transitive_headers/transitive_libs

## 错误特征

消费者编译期：
```
fatal error: 'xcb/xcb.h' file not found
#include <xcb/xcb.h>
```
或链接期缺库。注意本包自身编译是通过的——只有**消费方**才暴露。

## 触发条件

- 构建系统: cmake + Conan CMakeDeps（消费方 `conan create` 的 test_package）
- 阶段: compilation / linking（消费者侧）
- 上游特征: 本库的 **PUBLIC 头文件** include 了某个（直接或间接）依赖的头文件；
  该依赖在 Conan 里默认不向下游传播头文件

## 根因分析

Conan 2 默认 `transitive_headers=False` / `transitive_libs=False`：传递依赖的头文件
与库**不向消费者传播**，CMakeDeps 生成的消费配置里该依赖的 include 目录为空
（`set(<dep>_<comp>_INCLUDE_DIRS_RELEASE )`）。若本库的 PUBLIC 头引用了该依赖的头，
消费者编译即 `file not found`；若对应符号由该依赖提供，链接期还会缺库。

QtADS 4.5.0 实证：`ads_globals.h`（安装到 `include/qtadvanceddocking-qt6/` 的公共头）
在 `Q_OS_UNIX && !Q_OS_MACOS` 下无条件 `#include <xcb/xcb.h>`。OHOS 的 Qt 移植
**定义了 `Q_OS_UNIX`**，因此"OHOS 无 X11"并不免除该编译期依赖。

## 解决方案

### 推荐方案

对照本库 PUBLIC 头文件的 include 清单，把其中出现的依赖在 `requirements()` 里声明
为传递可见：

```python
self.requires("libxcb/1.17.0.1", transitive_headers=True, transitive_libs=True)
```

判据：该头文件是否安装在 `include/<本包>/` 且被下游 include —— 是则其 include 的
第三方头必须可传播。

### 禁止做法

- ❌ 在 test_package 里手工 `-I <依赖 include 目录>` 绕过——只让自测通过，真实下游
  仍失败，属伪造验证。

## 验证

```bash
conan create <pkg> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 2>&1 \
  | grep -E "file not found|undefined reference"
# 无输出即修复
```

## 关联条目

- 相关: E801（同为 CMakeDeps 消费侧传播问题，但那条是 find_mode=none 的目标悬空）
- 实证: qt-advanced-docking-system 4.5.0（test_package 编译缺 `xcb/xcb.h`）
