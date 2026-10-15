cmake_minimum_required(VERSION 3.29)
project(kitemmodels_consumer LANGUAGES CXX)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

find_package(Qt6 6.9 CONFIG REQUIRED COMPONENTS Core Qml)
find_package(KF6ItemModels 6.26.0 CONFIG REQUIRED)

add_executable(consumer consumer.cpp)
target_compile_features(consumer PRIVATE cxx_std_17)
target_link_libraries(consumer PRIVATE KF6::ItemModels Qt6::Core Qt6::Qml)
