cmake_minimum_required(VERSION 3.15)
project(test_kdsoap_ws_discovery LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The tested package installs its own KDSoapWSDiscoveryClientConfig.cmake; it is
# on CMAKE_PREFIX_PATH via the manually written conan_cmakedeps_paths.cmake, and
# its find_dependency(Qt6Core)/find_dependency(KDSoap-qt6) resolve the same way.
find_package(KDSoapWSDiscoveryClient REQUIRED CONFIG)

add_executable(test_kdsoap_ws_discovery test_kdsoapwsdiscovery.cpp)
target_link_libraries(test_kdsoap_ws_discovery PRIVATE KDSoap::WSDiscoveryClient)

enable_testing()
add_test(NAME test_kdsoap_ws_discovery COMMAND test_kdsoap_ws_discovery)
