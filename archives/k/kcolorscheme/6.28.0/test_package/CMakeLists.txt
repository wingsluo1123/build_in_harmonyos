cmake_minimum_required(VERSION 3.16)
project(test_kcolorscheme CXX)

# The KF6ColorScheme public headers are KF6 6.28 C++20 headers.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt6::Core/Qt6::Gui come from qtbase (the QGuiApplication runs on the
# offscreen platform plugin); KF6ColorScheme resolves through the
# project-installed KF6ColorSchemeConfig.cmake (the recipe sets
# cmake_find_mode=none so CMakeDeps does not shadow it).
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6ColorScheme REQUIRED)

add_executable(test_kcolorscheme test_kcolorscheme.cpp)
target_link_libraries(test_kcolorscheme PRIVATE KF6::ColorScheme Qt6::Core Qt6::Gui)

enable_testing()
add_test(NAME test_kcolorscheme COMMAND test_kcolorscheme)
