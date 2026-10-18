cmake_minimum_required(VERSION 3.15)
project(ktx_module_test C)

# Consumer-side test for ktx/1.45 (see ktx_module_test.c for what it checks).
# Upstream ships no automated tests, so this is OHOS-adaptation self-authored.
#
# find_package() is deliberately kept even though nothing is linked: it proves
# the CMake config generated from the recipe is consumable by a downstream
# CMake project. ktx is a dlopen-only plugin whose DT_SONAME (qwprogs.so) has no
# `lib` prefix, so cpp_info.libs is intentionally empty -- see the recipe's
# package_info() and notes.md section 5.1. Adding a bogus libs entry here would
# reproduce the very defect that section documents.

find_package(ktx REQUIRED)

add_executable(ktx_module_test ktx_module_test.c)
target_link_libraries(ktx_module_test PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME ktx_module_test COMMAND ktx_module_test)