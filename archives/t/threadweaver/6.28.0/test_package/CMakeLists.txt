cmake_minimum_required(VERSION 3.15)
project(test_threadweaver CXX)

# KF6ThreadWeaverTargets.cmake references Qt6::Core targets, so load Qt6
# first.
find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6ThreadWeaver REQUIRED)

add_executable(test_threadweaver test.cpp)
target_link_libraries(test_threadweaver KF6::ThreadWeaver)
