cmake_minimum_required(VERSION 3.15)
project(nfdump_consumer_test C)

set(CMAKE_C_STANDARD 11)

find_package(nfdump REQUIRED)

# The recipe exports one CMake target carrying both installed archives
# (libnfdump.a and libnffile.a); linking it is what proves they are consumable.
#
# Consumer test of the packaged command line tools and artefacts.
add_executable(test_nfdump test_nfdump.c)
target_link_libraries(test_nfdump PRIVATE nfdump::nfdump)

# HarmonyOS specific consumer test: drives the real collection pipeline.
add_executable(test_nfdump_ohos test_nfdump_ohos.c)
target_link_libraries(test_nfdump_ohos PRIVATE nfdump::nfdump)

# Both programs take the package folder as argv[1] (the HarmonyOS one a scratch
# folder as argv[2] as well), so they are launched from test_package/conanfile.py
# test() instead of being registered with ctest, which would run them bare.
