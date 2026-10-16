# KProperty

Qt5/KF5 property editing library, version 3.2.0, with shared Core and Widgets
libraries. Native upstream tests and installed API/QM consumers passed on
OHOS arm64; formal submission is still pending.

## Runtime data

Activate Conan's VirtualRunEnv. The recipe exports its share directory via
XDG_DATA_DIRS so the installed icon RCC is discoverable. Missing resources
can open a modal error dialog even from a non-GUI API; do not hide this by
skipping tests or changing the original GUILESS harness.

## Conan CMake consumer

See 3.2.0/test_package for the tested aggregate target integration. Released
KF5 dependencies opt out of CMakeDeps; when using the aggregate Conan target,
explicitly enable cmake_find_mode=config in CMakeDeps for kconfig5,
kcoreaddons5, kguiaddons5 and kwidgetsaddons5. This consumes their released
cpp_info library interfaces without modifying any dependency package.
Native upstream KPropertyCore/KPropertyWidgets configs are also installed.

## Scope

Qt6 translation programs are build tools only; host libraries remain Qt5.
The consumer actually loads the generated French QM with Qt5 QTranslator.
This is not a claim of native desktop window/input integration.
