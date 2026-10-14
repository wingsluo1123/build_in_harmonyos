cmake_minimum_required(VERSION 3.18)
project(test_manifold LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(manifold CONFIG REQUIRED)

# C 绑定测试仅在库以 cross_section+cbind 构建时可用
if(TARGET manifold::manifoldc)
  set(MANIFOLD_TEST_CBIND 1)
endif()

add_executable(test_manifold test_manifold.cpp)
target_link_libraries(test_manifold PRIVATE manifold::manifold)
if(MANIFOLD_TEST_CBIND)
  target_compile_definitions(test_manifold PRIVATE MANIFOLD_TEST_CBIND=1)
  target_link_libraries(test_manifold PRIVATE manifold::manifoldc)
endif()

set_target_properties(test_manifold PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
