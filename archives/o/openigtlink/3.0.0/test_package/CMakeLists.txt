cmake_minimum_required(VERSION 3.15)
project(test_openigtlink CXX)

# Find the package via the Conan-generated CMakeDeps files. The recipe exports
# the package name OpenIGTLink and the target OpenIGTLink::OpenIGTLink, which
# is the same spelling the upstream OpenIGTLinkConfig.cmake uses.
find_package(OpenIGTLink REQUIRED)

add_executable(test_openigtlink test_openigtlink.cpp)
target_link_libraries(test_openigtlink PRIVATE OpenIGTLink::OpenIGTLink)

enable_testing()
add_test(NAME test_openigtlink COMMAND test_openigtlink)
