cmake_minimum_required(VERSION 3.15)
project(test_knewstuff5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui Xml)

# knewstuff5 installs its own KF5NewStuffCoreConfig.cmake (recipe uses
# cmake_find_mode=none); the canonical target is KF5::NewStuffCore.
find_package(KF5NewStuffCore 5.116.0 REQUIRED CONFIG)

if(NOT TARGET KF5::NewStuffCore)
    message(FATAL_ERROR "KF5::NewStuffCore target not provided by KF5NewStuffCoreConfig.cmake")
endif()

add_executable(test_knewstuff5 test.cpp)
target_link_libraries(test_knewstuff5 PRIVATE KF5::NewStuffCore Qt5::Core Qt5::Gui)

enable_testing()
add_test(NAME test_knewstuff5 COMMAND test_knewstuff5)
