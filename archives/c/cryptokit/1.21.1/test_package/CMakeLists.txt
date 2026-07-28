cmake_minimum_required(VERSION 3.15)
project(test_cryptokit C)

find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(CRYPTOKIT cryptokit)
endif()

if(CRYPTOKIT_FOUND)
    add_executable(test_cryptokit test.c)
    target_include_directories(test_cryptokit PRIVATE ${CRYPTOKIT_INCLUDE_DIRS})
    target_link_libraries(test_cryptokit PRIVATE ${CRYPTOKIT_LIBRARIES})
else()
    add_executable(test_cryptokit test.c)
    target_include_directories(test_cryptokit PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../../src)
    target_link_libraries(test_cryptokit PRIVATE cryptokit)
endif()

# R34: Verify the test actually links and calls the library
target_link_options(test_cryptokit PRIVATE -Wl,--no-undefined)
