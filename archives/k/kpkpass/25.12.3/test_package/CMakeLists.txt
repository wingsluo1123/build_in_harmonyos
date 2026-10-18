cmake_minimum_required(VERSION 3.16)
project(kpkpass_consumer LANGUAGES CXX)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 6.8 CONFIG REQUIRED COMPONENTS Core Gui Qml)
find_package(KPim6PkPass 6.6.3 CONFIG REQUIRED)

add_executable(consumer consumer.cpp)
target_link_libraries(consumer PRIVATE KPim6::PkPass Qt6::Core Qt6::Gui Qt6::Qml)
