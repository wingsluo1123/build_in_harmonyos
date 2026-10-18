cmake_minimum_required(VERSION 3.16)
project(test_ktextaddons LANGUAGES CXX)

include(${CMAKE_BINARY_DIR}/conan_toolchain.cmake OPTIONAL)
include(${CMAKE_BINARY_DIR}/conan_cmakedeps_paths.cmake OPTIONAL)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6Config CONFIG REQUIRED)
find_package(KF6ColorScheme CONFIG REQUIRED)
find_package(KF6CoreAddons CONFIG REQUIRED)
find_package(KF6I18n CONFIG REQUIRED)
find_package(KF6Sonnet CONFIG REQUIRED)
find_package(KF6SyntaxHighlighting CONFIG REQUIRED)
find_package(KF6WidgetsAddons CONFIG REQUIRED)
find_package(KF6Archive CONFIG REQUIRED)
find_package(KF6ItemViews CONFIG REQUIRED)
find_package(KF6TextWidgets CONFIG REQUIRED)
find_package(KF6TextAutoCorrectionWidgets CONFIG REQUIRED)
find_package(KF6TextAddonsWidgets CONFIG REQUIRED)
find_package(KF6TextEmoticonsCore CONFIG REQUIRED)
find_package(KF6TextEmoticonsWidgets CONFIG REQUIRED)
find_package(KF6TextCustomEditor CONFIG REQUIRED)
find_package(KF6TextUtils CONFIG REQUIRED)

add_executable(test_ktextaddons test_package.cpp)
target_link_libraries(test_ktextaddons PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    KF6::TextAddonsWidgets
    KF6::TextCustomEditor
    KF6::TextEmoticonsCore
    KF6::TextEmoticonsWidgets
    KF6::TextUtils
    KF6::TextAutoCorrectionWidgets
)

enable_testing()
add_test(NAME test_ktextaddons COMMAND test_ktextaddons)
