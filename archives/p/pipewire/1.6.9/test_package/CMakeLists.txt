cmake_minimum_required(VERSION 3.15)
project(test_pipewire C)

# Find the package via Conan-generated CMakeDeps
find_package(pipewire REQUIRED)

add_executable(test_pipewire test.c)
target_link_libraries(test_pipewire pipewire::pipewire)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos pipewire::pipewire)

# The tests are executed by test_package/conanfile.py, which exports the
# PIPEWIRE_* / LD_LIBRARY_PATH environment they need. Registering them with
# add_test() would make a plain `ctest` run fail on the missing environment
# without adding any coverage, so no CTest entries are declared here.
