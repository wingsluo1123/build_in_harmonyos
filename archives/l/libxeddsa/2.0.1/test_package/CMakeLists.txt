cmake_minimum_required(VERSION 3.15)
project(test_libxeddsa C)

# Find the package via Conan-generated CMakeDeps
find_package(libxeddsa REQUIRED)

add_executable(test_libxeddsa test.c)
target_link_libraries(test_libxeddsa libxeddsa::libxeddsa)

# HarmonyOS-specific test: verifies OHOS random-source probing, public-key
# conversion roundtrips, X25519 key agreement and Ed25519 sign/verify on the
# packaged library (public headers/API only).
add_executable(ohos_specific_test ohos_specific_test.c)
target_link_libraries(ohos_specific_test libxeddsa::libxeddsa)

enable_testing()
add_test(NAME test_libxeddsa COMMAND test_libxeddsa)
add_test(NAME ohos_specific_test COMMAND ohos_specific_test)
