cmake_minimum_required(VERSION 3.15)
project(test_lmdbxx CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find lmdbxx (header-only, provides include dirs + transitive lmdb dep)
find_package(lmdbxx REQUIRED)

add_executable(test_lmdbxx test_lmdbxx.cpp)
target_link_libraries(test_lmdbxx lmdbxx::lmdbxx)

enable_testing()
add_test(NAME test_lmdbxx COMMAND test_lmdbxx)
