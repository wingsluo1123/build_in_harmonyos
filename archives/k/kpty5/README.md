# kpty5

KDE Frameworks 5 `kpty`（Qt5），为 OpenHarmony PC 打包。

| 项目 | 值 |
|---|---|
| 上游 | https://invent.kde.org/frameworks/kpty |
| 版本 | 5.116.0（KF5 最后一个发布版） |
| 源码 | https://download.kde.org/stable/frameworks/5.116/kpty-5.116.0.tar.xz |
| SHA-256 | `ad4f6322544f65c7c900003d86ffeaac350fd2e2739b4777997ece49d8f04630` |
| 构建系统 | CMake + extra-cmake-modules，测试走 CTest |
| 语言 | C++（Qt5） |
| 许可证 | LGPL-2.0-or-later |

这是 KF5/Qt5 模块，与 Qt6 基础的同名 6.x 模块不是同一个包。

## 依赖

- `qt5-qtbase/5.15.2.2`（Qt5 Core，上游 `CMakeLists.txt` REQUIRED）
- `kcoreaddons5/5.116.0.1`（`CMakeLists.txt:31` REQUIRED，用于 KProcess）
- `ki18n5/5.116.0`（`CMakeLists.txt:32` REQUIRED，用于 KPTY_LOG 分类）
- `ecm/6.26.0`（构建工具）

`UTEMPTER` 是可选依赖（`CMakeLists.txt:38-44`），OHOS sysroot 不提供
libutempter，因此 `HAVE_UTEMPTER` 关闭，KPty 不管理 utmp 条目。

## ⚠️ 当前阻塞

**本配方已编写并通过 `conan export`，但由于依赖图无法解析，尚不能构建或上机验证。**

`kpty 5.116.0` 同时硬依赖 `KF5CoreAddons` 与 `KF5I18n`，而这两个已发布配方
要求的 `qt5-qtbase` 版本互不兼容：

    kcoreaddons5/5.116.0  ->  qt5-qtbase/5.15.2
    ki18n5/5.116.0        ->  qt5-qtbase/5.15.2.2

两者在 `ohpcd` 上都有 `armv8` 二进制，且 `kcoreaddons5/5.116.0` 只有一个
revision（`e10997493b9b`，本地与远端一致），没有更新的 revision 可选。该冲突
不依赖本配方即可复现：

    $ conan graph info --requires=kcoreaddons5/5.116.0 --requires=ki18n5/5.116.0 \
        -pr ohos-aarch64-wsl
    ERROR: Version conflict: Conflict between qt5-qtbase/5.15.2.2 and
    qt5-qtbase/5.15.2 in the graph.
    Conflict originates from ki18n5/5.116.0

同一对冲突也是 `kpackage5/5.116.0` 的硬依赖，因此这同样解释了该任务为何无法
configure。详尽的推导与修复方向见 `5.116.0/notes.md`。
