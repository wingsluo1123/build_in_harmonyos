cmake_minimum_required(VERSION 3.15)
project(test_readstat C)

# Consumer view: locate the packaged library through the Conan-generated
# CMakeDeps config (readstat::readstat) and link the packaged artifact only.
find_package(readstat REQUIRED)

# Consumer suites, one binary each so a failure is attributable to one scope.
# The HarmonyOS round-trip suite writes its .sav/.zsav fixtures into
# <build>/fixtures, which is also where test_package/conanfile.py runs the
# packaged `readstat` CLI against them.
function(readstat_consumer_test name source)
    add_executable(${name} ${source})
    target_link_libraries(${name} readstat::readstat)
    add_test(NAME ${name} COMMAND ${name} "${CMAKE_CURRENT_BINARY_DIR}/fixtures")
endfunction()

# Suite 1: parser lifecycle + error-code mapping for missing.
readstat_consumer_test(consumer_error_paths consumer_error_paths.c)

# Suite 2 (HarmonyOS): real POSIX write/read round-trip of .sav and .zsav,
# zlib-compressed path, row-limit window, and the missing-file parse guard.
readstat_consumer_test(consumer_round_trip consumer_round_trip.c)

enable_testing()
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/fixtures")
