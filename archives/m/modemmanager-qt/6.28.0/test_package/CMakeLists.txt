cmake_minimum_required(VERSION 3.15)
project(test_modemmanagerqt CXX)

# Match the C++ standard the library itself is built with.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt6 targets are linked directly below, so resolve them explicitly instead of
# relying on the find_dependency() inside KF6ModemManagerQtConfig.cmake.
find_package(Qt6 REQUIRED COMPONENTS Core DBus)

# Find the package through the upstream-installed KF6ModemManagerQtConfig.cmake
# (package_info sets cmake_find_mode=none, so CMakeDeps does not shadow it).
find_package(KF6ModemManagerQt REQUIRED)

# Consumer test: links the installed shared library and exercises the public
# ModemManagerQt API surface against a private D-Bus daemon.
add_executable(test_modemmanagerqt test_modemmanagerqt.cpp)
target_link_libraries(test_modemmanagerqt KF6::ModemManagerQt Qt6::Core Qt6::DBus)

enable_testing()
add_test(NAME test_modemmanagerqt COMMAND test_modemmanagerqt)
