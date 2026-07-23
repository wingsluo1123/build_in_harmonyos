cmake_minimum_required(VERSION 3.15)
project(test_ElaWidgetTools CXX)

# Qt5 is a system-installed dependency (append, don't override Conan's CMAKE_PREFIX_PATH)
list(APPEND CMAKE_PREFIX_PATH "$ENV{HOME}/usr/local/Qt5")
set(CMAKE_CXX_FLAGS "-stdlib=libc++")
set(CMAKE_EXE_LINKER_FLAGS "-stdlib=libc++")

# Find the package via Conan-generated CMakeDeps (lowercase name)
find_package(elawidgettools REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_executable(test_ElaWidgetTools test.cpp)
target_link_libraries(test_ElaWidgetTools elawidgettools::elawidgettools Qt5::Widgets)

enable_testing()
add_test(NAME test_ElaWidgetTools COMMAND test_ElaWidgetTools)
