cmake_minimum_required(VERSION 3.16)
project(plasma_activities_consumer_e2e CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt6 first: PlasmaActivitiesConfig.cmake calls find_dependency(Qt6Core).
find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(PlasmaActivities REQUIRED)

add_executable(consumer_e2e src/consumer_e2e.cpp)
target_link_libraries(consumer_e2e PRIVATE Plasma::Activities Qt6::Core)

enable_testing()
add_test(NAME consumer_e2e COMMAND consumer_e2e)
