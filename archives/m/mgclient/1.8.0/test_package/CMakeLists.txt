cmake_minimum_required(VERSION 3.15)
project(test_mgclient C)

# Find the package via Conan-generated CMakeDeps
find_package(mgclient REQUIRED)

add_executable(test_mgclient test.c)
target_link_libraries(test_mgclient mgclient::mgclient)

add_executable(harmonyos_specific_test harmonyos_specific_test.c)
target_link_libraries(harmonyos_specific_test mgclient::mgclient)

enable_testing()
add_test(NAME test_mgclient COMMAND test_mgclient)
add_test(NAME harmonyos_specific_test
         COMMAND harmonyos_specific_test 127.0.0.1 1)
