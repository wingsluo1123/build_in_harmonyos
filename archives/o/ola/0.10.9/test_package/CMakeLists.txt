cmake_minimum_required(VERSION 3.15)
project(test_ola CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)  # match ola's gnu++11 default; we use gnu++17

# Find the package via Conan-generated CMakeDeps.
# ola::ola is the target name declared in conanfile.py via set_property(...).
find_package(ola REQUIRED CONFIG)

add_executable(test_ola test_ola.cpp)
target_link_libraries(test_ola
  ola::ola
)

enable_testing()
add_test(NAME test_ola COMMAND test_ola)