cmake_minimum_required(VERSION 3.16)
project(test_kconfig CXX)

# KF6ConfigTargets.cmake references Qt6::Core/Qt6::Xml/Qt6::Gui/Qt6::Qml
# targets, so load Qt6 first. Qt6Qml resolves through the qtdeclarative
# package root advertised via QT_ADDITIONAL_PACKAGES_PREFIX_PATH.
find_package(Qt6 REQUIRED COMPONENTS Core Xml Gui Qml)

# Brings in KF6ConfigTargets.cmake, KF6ConfigCompilerTargets.cmake (the
# KF6::kconfig_compiler imported target) and KF6ConfigMacros.cmake, exactly
# like a downstream KDE application consuming the package.
find_package(KF6Config REQUIRED)

add_executable(test_kconfig test.cpp)
target_link_libraries(test_kconfig PRIVATE KF6::ConfigCore KF6::ConfigGui Qt6::Gui Qt6::Qml)

# KConfig XT consumer case: the installed CMake machinery generates the
# sources with the packaged kconfig_compiler at build time.
add_executable(test_kconfig_xt xt_main.cpp)
target_include_directories(test_kconfig_xt PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
kconfig_add_kcfg_files(test_kconfig_xt kcfg/xttest.kcfgc GENERATE_MOC)
target_link_libraries(test_kconfig_xt PRIVATE KF6::ConfigGui KF6::ConfigCore Qt6::Core)

set_target_properties(test_kconfig test_kconfig_xt PROPERTIES AUTOMOC ON)

enable_testing()
add_test(NAME test_kconfig COMMAND test_kconfig)
add_test(NAME test_kconfig_xt COMMAND test_kconfig_xt)
