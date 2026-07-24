cmake_minimum_required(VERSION 3.16)
project(test_qtbase CXX)

# R34: 实质调用 Qt6 API — 覆盖 Core + Network + Xml + Concurrent
find_package(Qt6 REQUIRED COMPONENTS Core Network Xml Concurrent CONFIG)

add_executable(test_qtbase src/test_qtbase.cpp)
target_link_libraries(test_qtbase PRIVATE
    Qt6::Core
    Qt6::Network
    Qt6::Xml
    Qt6::Concurrent
)

enable_testing()
add_test(NAME qtbase_modules_test COMMAND test_qtbase)
