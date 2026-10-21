cmake_minimum_required(VERSION 3.16)
project(test_krunner5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# The aggregate Qt5Config comes from the CMakeDeps-generated config (the
# consumer-side mirror of the main recipe's supply).
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core)

# KF5RunnerConfig find_dependency's KF5CoreAddons + KF5Config itself; KF5I18n
# is referenced by KF5::Runner's exported interface but NOT pulled by
# upstream's KF5RunnerConfig, so the consumer must find it for the link
# interface to resolve.
find_package(KF5I18n 5.116.0 REQUIRED)
find_package(KF5Runner 5.116.0 REQUIRED)

add_executable(test_krunner5 test.cpp)
target_link_libraries(test_krunner5 PRIVATE Qt5::Core KF5::Runner)

# /proc/self/maps reports the bare soname on OHOS, so give the test the real
# packaged library path to assert its ELF adaptation properties (R53).
target_compile_definitions(test_krunner5 PRIVATE
    KRUNNER_SO_PATH="$<TARGET_FILE:KF5::Runner>")

enable_testing()
add_test(NAME test_krunner5 COMMAND test_krunner5)
