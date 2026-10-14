# kservice5

KDE Frameworks 5 `kservice`（Qt5），为 OpenHarmony PC 打包。

| 项目 | 值 |
|---|---|
| 上游 | https://invent.kde.org/frameworks/kservice |
| 版本 | 5.116.0（KF5 最后一个发布版） |
| 源码 | https://download.kde.org/stable/frameworks/5.116/kservice-5.116.0.tar.xz |
| SHA-256 | `52b7c2c317d0a662ca33200f9b4f93e0b7efb1843abd120a3b49c9a092f4a869` |
| 构建系统 | CMake + extra-cmake-modules，测试走 CTest |
| 语言 | C++（Qt5），Trader 解析器由 flex/bison 生成 |
| 许可证 | LGPL-2.0-or-later |
| 交付物 | `libKF5Service.so`、`bin/kbuildsycoca5` |

这是 KF5/Qt5 模块，与 Qt6 基础的同名 6.x 配方不是同一个包。

## 依赖

- `qt5-qtbase/5.15.2.2`（Xml、DBus REQUIRED；测试另需 Concurrent/Test）
- `kconfig5/5.116.0`（`CMakeLists.txt:52` REQUIRED）
- `kcoreaddons5/5.116.0.1`（`CMakeLists.txt:53` REQUIRED）
- `kdbusaddons5/5.116.0`（`CMakeLists.txt:55` REQUIRED）
- `ki18n5/5.116.0`（`CMakeLists.txt:57` REQUIRED）
- `ecm/6.26.0`（构建工具）
- `flex/2.6.4.2`、`bison/3.8.2`、`m4/1.4.19` —— Trader 解析器是构建期生成的，二者
  均为上游 REQUIRED，不可省略

`KF5DocTools` 是**可选**依赖（`CMakeLists.txt:58` 无 REQUIRED，项目用
`KF5DocTools_FOUND` 保护 docs/ 与 `kdoctools_install`），仓库内也没有
`kdoctools5` 配方，因此显式关闭该可选路径。

## Qt5 基线冲突与处理

已发布的 KF5 5.116.0 包分布在**两条 Qt5 基线**上：`kcoreaddons5` 等 21 个配方钉
`qt5-qtbase/5.15.2`，而 `kconfig5`/`kdbusaddons5`/`ki18n5` 等 73 个用
`qt5-qtbase/5.15.2.2`。kservice 同时需要两侧，直接解析会得到：

    ERROR: Version conflict: Conflict between qt5-qtbase/5.15.2 and
    qt5-qtbase/5.15.2.2 in the graph

处理方式沿用仓库既有先例（`kjobwidgets5/5.116.0` 已就此写明）：

```python
self.requires("qt5-qtbase/5.15.2.2", force=True)
```

`force=True`（而非 `override=True`）在统一版本的同时保留 `qt5-qtbase` 作为消费型
依赖，使 `generate()` 仍能拿到 `package_folder`。没有选择“重新发布
`kcoreaddons5`”的路线，因为那会级联影响钉住它的全部 21 个配方。

## flex / bison / m4 用宿主依赖而非 tool_requires

本农场的 Harmony PC 是**本机构建**（host 与 build profile 同为
`ohos-aarch64`），宿主上下文的 armv8 二进制在构建期可直接执行；而 build 上下文会
算出另一个 package id（`a6727273...`），ohpcd 上并无该制品，且农场 verify 执行
`conan create` 时**不带 `--build=missing`**，会直接硬失败。因此三者声明为宿主
`requires`，仅通过 `CMAKE_PROGRAM_PATH` 供 `find_program` 定位，不参与链接。

## 上游测试

`autotests/` 下 11 个 `ecm_add_test` 注册的 QTest 类，合计 **78** 个用例（已排除
`initTestCase`/`cleanupTestCase`/`init`/`cleanup` 与 `*_data`），全部并入
`build()` 的 `ctest`。逐类计数与推导见 `5.116.0/notes.md` 与
`5.116.0/test_package/MANIFEST.yml`。
