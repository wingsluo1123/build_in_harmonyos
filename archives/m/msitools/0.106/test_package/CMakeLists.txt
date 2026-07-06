cmake_minimum_required(VERSION 3.15)
project(test_msitools C)

# Find the package via Conan-generated CMakeDeps
find_package(msitools REQUIRED)

add_executable(test_msitools test.c)
target_link_libraries(test_msitools msitools::msitools)

# Set RPATH so the test binary can find libmsi-1.0.so at runtime
set_target_properties(test_msitools PROPERTIES
  BUILD_RPATH_USE_ORIGIN ON
  INSTALL_RPATH_USE_ORIGIN ON
)

enable_testing()
add_test(NAME test_msitools COMMAND test_msitools)
