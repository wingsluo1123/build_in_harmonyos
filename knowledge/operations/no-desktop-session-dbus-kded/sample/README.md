# sample — 会话策略样例工程（非交付制品，仅知识库演示）

去业务化的最小复刻：把 kwrited 6.7.2 的「桌面会话插件 / 独立可执行」双分支结构抽出来，
用**可观察的两个状态**演示本主题的策略：

| 状态 | 触发 | 结果 |
|---|---|---|
| 关策略 | `SAMPLE_ASSUME_DESKTOP_SESSION=1`（假装本平台有桌面会话 / KDED） | 进入会话插件分支 → `find_package(KF6DBusAddons REQUIRED)` 配置期报错 |
| 开策略 | 默认配置 | KF6Pty 包导出 `KPty_HAVE_UTEMPTER=FALSE` → `cmake_dependent_option()` 强制 `BUILD_AS_EXECUTABLE=ON` → 独立可执行分支，配置 + 编译 + 运行全通 |

## 文件

| 文件 | 作用 |
|---|---|
| `CMakeLists.txt` | 双分支结构（与 kwrited 上游同构）+ 演示开关 |
| `main.cpp` | 分支自述程序：开策略下打开 pty 并打印 `branch=/pty_open=/tty=` |
| `sample-session-plugin.json` | 插件分支的元数据（关策略时被读入，演示「插件形态」） |
| `conanfile.py` | conan 配方：依赖 = qtbase/6.11.1、kcoreaddons/6.26.0.1、kpty/6.26.0、ecm/6.26.0(tool)（只声明样例真正 `find_package` 的三个库；kwrited 自身的 ki18n/knotifications 与样例无关） |
| `README.md` | 本文件 |

## 复现

```sh
# 上层目录的脚本会驱动两个变体（各用私有输出目录，不复用任何本地产物）
sh knowledge/operations/no-desktop-session-dbus-kded/reproduce.sh
```

脚本内部走 conan（与 CI/W3 同机制）：

```sh
conan install <sample> -of <work>/on  -pr:h=<ohos-aarch64> -pr:b=<同左> -r=ohpcd
conan build   <sample> -of <work>/on  -pr:h=... -pr:b=... -r=ohpcd
SAMPLE_ASSUME_DESKTOP_SESSION=1 conan build <sample> -of <work>/off ...   # 关策略
```

## 两个必须注意的实现点（都是踩过的坑）

1. **依赖前缀靠手工 `conan_cmakedeps_paths.cmake`**：本仓库 Qt6/KF6 配方用
   `cmake_find_mode=none`，CMakeDeps 不会生成该文件，`conan_toolchain.cmake` 里的
   `CMAKE_PREFIX_PATH` 只有部分依赖。配方 `generate()` 必须自己把每个依赖的
   `lib/cmake`、`lib`、`include` 写进去（kpty 6.26.0 / kwrited 6.7.2 先例），
   否则 `find_package(Qt6 6.10.0 CONFIG REQUIRED)` 直接报找不到。
2. **KF6Pty 的导出 include 目录是 `<prefix>/include/KF6/KPty`**，所以源码里写
   `#include <kpty.h>`（或 `<KPtyDevice>`），不要写 `<KPty/kpty.h>`。

另外，`cmake_dependent_option()` 未被满足时会**忽略命令行 `-D` 传入的值**强行置为
force 值（`ON`），而 `KPty_HAVE_UTEMPTER` 又是 KF6PtyConfig 里的普通变量、会遮蔽
命令行 `-D`。因此演示开关必须放在 `cmake_dependent_option()` **之后**直接
`set(BUILD_AS_EXECUTABLE OFF ... FORCE)`，这也解释了上游为什么不需要、也不提供这种开关。

> 本目录是知识库演示件，不参与制品构建，也不进制品仓。
