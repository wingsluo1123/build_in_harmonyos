cmake_minimum_required(VERSION 3.16)
project(test_karchive CXX)

# R34: 实质调用 KF6::Archive API
find_package(KF6Archive REQUIRED CONFIG)

add_executable(test_karchive src/test_karchive.cpp)
target_link_libraries(test_karchive PRIVATE KF6::Archive)

enable_testing()
add_test(NAME karchive_link COMMAND test_karchive)
