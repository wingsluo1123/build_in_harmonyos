cmake_minimum_required(VERSION 3.15)
project(test_decker C)

# decker is an application package (cpp_info.libdirs = []), so
# find_package + target_link_libraries(decker::decker) is a no-op.
# We instead resolve the installed lilt binary path from the Conan
# bindir exposed via the imported target's INTERFACE_INCLUDE_DIRECTORIES
# is NOT set; use the standard DECKER_BIN env passed by the test runner,
# falling back to the CMake-provided package location.

find_package(decker REQUIRED)

# decker package sets cpp_info.bindirs = ["bin"]; Conan's CMakeDeps
# generator exposes it via the imported target's LOCATION property.
get_target_property(_decker_bin_dir decker::decker INTERFACE_LINK_DIRECTORIES)
if(NOT _decker_bin_dir)
    # Fall back to the CMAKE_INSTALL_PREFIX-relative bin/ layout.
    set(_decker_bin_dir "${CMAKE_INSTALL_PREFIX}/bin")
endif()

add_executable(test_decker test.c)
target_compile_definitions(test_decker PRIVATE
    LILT_DEFAULT_BIN="${_decker_bin_dir}/lilt")

enable_testing()
add_test(NAME test_decker COMMAND test_decker)
