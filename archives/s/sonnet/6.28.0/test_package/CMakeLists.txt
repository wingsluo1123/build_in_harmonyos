cmake_minimum_required(VERSION 3.16)
project(test_sonnet CXX)

# KF6SonnetConfig.cmake (installed by the sonnet package) forwards to
# find_dependency(Qt6Core/Qt6Widgets); Qt6Qml/Qt6Quick resolve through the
# qtdeclarative package root advertised via QT_ADDITIONAL_PACKAGES_PREFIX_PATH.
find_package(Qt6 REQUIRED COMPONENTS Core Widgets Qml Quick)

# Brings in KF6SonnetTargets.cmake, exactly like a downstream KDE
# application (ktextwidgets/ktextaddons) consuming the package.
find_package(KF6Sonnet REQUIRED)

add_executable(test_sonnet test_sonnet.cpp)
target_link_libraries(test_sonnet PRIVATE
    KF6::SonnetCore
    KF6::SonnetUi
    Qt6::Widgets
    Qt6::Qml
    Qt6::Quick
)

enable_testing()
add_test(NAME test_sonnet COMMAND test_sonnet)
