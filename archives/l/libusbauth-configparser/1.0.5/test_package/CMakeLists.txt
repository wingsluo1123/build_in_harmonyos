cmake_minimum_required(VERSION 3.15)
project(test_libusbauth_configparser C)

# Find the package via the Conan-generated CMakeDeps config
find_package(libusbauth-configparser REQUIRED)

# test.c exercises the exported public API (string <-> enum tables, Data
# construction, sub_length clamping, graceful failure on a missing config).
add_executable(test_libusbauth_configparser test.c)
target_link_libraries(test_libusbauth_configparser
                      libusbauth-configparser::libusbauth-configparser)

# test_ohos.c asserts the HarmonyOS runtime/load behaviour and the full
# flex/bison parse round-trip through the overridable config path (rule12).
add_executable(test_libusbauth_configparser_ohos test_ohos.c)
target_link_libraries(test_libusbauth_configparser_ohos
                      libusbauth-configparser::libusbauth-configparser
                      ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_libusbauth_configparser COMMAND test_libusbauth_configparser)
add_test(NAME test_libusbauth_configparser_ohos COMMAND test_libusbauth_configparser_ohos)
