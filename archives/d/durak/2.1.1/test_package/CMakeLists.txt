cmake_minimum_required(VERSION 3.15)
project(test_durak LANGUAGES CXX)

find_package(durak REQUIRED)

add_executable(test_durak test_durak_consumer.cpp)
target_compile_features(test_durak PRIVATE cxx_std_20)
target_link_libraries(test_durak PRIVATE durak::durak)

enable_testing()
add_test(NAME test_durak COMMAND test_durak)