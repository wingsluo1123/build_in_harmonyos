# ecdsautils test_package — the executable built here is what the consumer test
# exercises. It is EXECUTED by conanfile.py test() via self.run(exe, ...), i.e.
# directly (not driven by ctest): the local CI gate requires an explicit
# self.run() in test(). enable_testing()/add_test() below keep the executable
# registered so ctest can still be invoked manually from this build folder.
#
# Upstream declares cmake_minimum_required(VERSION 2.8.3); CMake >= 4.0 refuses
# policy versions older than 3.5, so cap the policy before project().
cmake_minimum_required(VERSION 3.15)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5 CACHE STRING "" FORCE)

project(test_ecdsautils C)

find_package(ecdsautils REQUIRED)

add_executable(test_ecdsautils test_ecdsautils.c)
# Conan 2 CMakeDeps generates <pkg>::<pkg>; transitive usage requirements pull
# in libuecc (public header ecdsautil/ecdsa.h includes <libuecc/ecc.h>).
target_link_libraries(test_ecdsautils ecdsautils::ecdsautils)

enable_testing()
add_test(NAME test_ecdsautils COMMAND test_ecdsautils)
