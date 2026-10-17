cmake_minimum_required(VERSION 3.15)
project(test_libzc C)

# Find the package via Conan-generated CMakeDeps
find_package(libzc REQUIRED)

add_executable(test_libzc test.c)
target_link_libraries(test_libzc libzc::libzc)

# HarmonyOS-specific test: drives zc_crk_bforce which exercises the OHOS
# pthread-cancellation fallback (patch 0001) — must run and pass on OHOS.
add_executable(harmonyos_ohos_test harmonyos_ohos_test.c)
target_link_libraries(harmonyos_ohos_test libzc::libzc)

enable_testing()
add_test(NAME test_libzc COMMAND test_libzc)
add_test(NAME harmonyos_ohos_test COMMAND harmonyos_ohos_test)