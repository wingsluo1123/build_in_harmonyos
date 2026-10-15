# qt-advanced-docking-system 4.5.0 验证报告

## 1. W3 本地构建验证（conan create，与 CI 同源命令）

```
conan create archives/q/qt-advanced-docking-system/4.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="qt-advanced-docking-system/*"
→ EXIT=0
```

## 2. test_package 消费者测试输出（offscreen QPA，30 断言）

```
qt-advanced-docking-system/4.5.0 (test package): Running CMake.build()
ok   ads::CDockManager::testConfigFlag(ads::CDockManager::OpaqueSplitterResize)
ok   ads::CDockManager::testConfigFlag(ads::CDockManager::FocusHighlighting)
ok   manager != nullptr
ok   manager->dockWidgetsMap().isEmpty()
ok   manager->addDockWidget(ads::LeftDockWidgetArea, left) != nullptr
ok   manager->addDockWidget(ads::RightDockWidgetArea, right) != nullptr
ok   manager->addDockWidget(ads::TopDockWidgetArea, top) != nullptr
ok   manager->addDockWidget(ads::BottomDockWidgetArea, bottom) != nullptr
ok   manager->dockWidgetsMap().size() == 4
ok   manager->dockWidgetsMap().contains("LeftDock")
ok   manager->dockWidgetsMap().value("LeftDock") == left
ok   left->dockAreaWidget() != nullptr
ok   right->dockAreaWidget() != nullptr
ok   !left->isClosed()
ok   !right->isClosed()
ok   !left->isFloating()
ok   manager->addDockWidgetTab(ads::CenterDockWidgetArea, tabbed) != nullptr
ok   tabbed->dockAreaWidget() != nullptr
ok   tabbed->dockAreaWidget() != left->dockAreaWidget()
ok   left->isClosed()
ok   !left->isClosed()
ok   manager->perspectiveNames().contains("LayoutOne")
ok   This plugin does not support propagateSizeHints()
ok   !state.isEmpty()
ok   manager->restoreState(state)
ok   floatingContainer != nullptr
ok   floating->isFloating()
ok   !manager->floatingWidgets().isEmpty()
ok   manager->addDockWidget(ads::CenterDockWidgetArea, floating) != nullptr
ok   !floating->isFloating()
30 checks, 0 failures
RESULT: PASSED
```

## 3. 产物与 SONAME（CI L5 门禁自查）

```
total 1015808
  3440 2026-10-15 01:49 .
  3440 2026-10-15 01:49 ..
  3440 2026-10-15 01:49 cmake
    29 2026-10-15 01:49 libqtadvanceddocking-qt6.so -> libqtadvanceddocking-qt6.so.4
    33 2026-10-15 01:49 libqtadvanceddocking-qt6.so.4 -> libqtadvanceddocking-qt6.so.4.5.0
969344 2026-10-15 01:49 libqtadvanceddocking-qt6.so.4.5.0

 0x0000000000000001 (NEEDED)             Shared library: [libQt6Widgets.so.6]
 0x0000000000000001 (NEEDED)             Shared library: [libQt6Gui.so.6]
 0x0000000000000001 (NEEDED)             Shared library: [libQt6Core.so.6]
 0x0000000000000001 (NEEDED)             Shared library: [libxcb.so.1]
 0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]
 0x000000000000000e (SONAME)             Library soname: [libqtadvanceddocking-qt6.so.4]
```

- L5a DT_SONAME：通过（libqtadvanceddocking-qt6.so.4，相对路径）
- L5b DT_NEEDED：通过（全部裸名，无绝对/相对路径）
- L5c 包内 .cmake 无 IMPORTED_NO_SONAME TRUE：通过

## 4. 产物清单

```
./lib/libqtadvanceddocking-qt6.so
./lib/libqtadvanceddocking-qt6.so.4
./lib/libqtadvanceddocking-qt6.so.4.5.0
```
