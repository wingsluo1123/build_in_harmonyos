cmake_minimum_required(VERSION 3.16)
project(test_kunitconversion LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC OFF)

# KF6UnitConversionConfig.cmake does find_dependency(Qt6Core) and the
# exported KF6::UnitConversion target carries Qt6::Core in its interface
# (Qt6::Network and the bare-name KF6I18n linkage stay PRIVATE to the
# library).
find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6UnitConversion REQUIRED)

add_executable(test_kunitconversion test.cpp)
target_link_libraries(
    test_kunitconversion
    PRIVATE
        Qt6::Core
        KF6::UnitConversion
)

# OHOS-specific consumer check: parses its own ELF dynamic section plus
# the loaded libKF6UnitConversion.so (located through /proc/self/maps /
# LD_LIBRARY_PATH candidates) and asserts the SONAME-based linkage the
# recipe guarantees: a bare DT_SONAME and no slash-qualified DT_NEEDED
# entries (platform E537).
add_executable(test_kunitconversion_ohos test_ohos_soname.cpp)
target_link_libraries(
    test_kunitconversion_ohos
    PRIVATE
        Qt6::Core
        KF6::UnitConversion
)

enable_testing()
add_test(NAME test_kunitconversion COMMAND test_kunitconversion)
add_test(NAME test_kunitconversion_ohos COMMAND test_kunitconversion_ohos)
