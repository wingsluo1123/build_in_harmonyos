cmake_minimum_required(VERSION 3.15)
project(test_bib-tool C)

# Find the package via Conan-generated CMakeDeps
find_package(bib-tool REQUIRED)

add_executable(test_bib-tool test.c)
target_link_libraries(test_bib-tool bib-tool::bib-tool)

enable_testing()
add_test(NAME test_bib-tool COMMAND test_bib-tool)
