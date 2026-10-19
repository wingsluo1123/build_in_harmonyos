cmake_minimum_required(VERSION 3.16)
project(test_live LANGUAGES CXX)

find_package(live REQUIRED CONFIG)
find_package(Threads REQUIRED)

add_executable(test_live test_live.cpp)
target_compile_features(test_live PRIVATE cxx_std_20)
target_link_libraries(test_live PRIVATE live::live Threads::Threads)

# Reproducibility probe for the documented original/wrong/correct three-arm
# experiment. It is built from the same installed package but is not counted as
# an additional upstream or consumer test.
add_executable(three_arm_probe three_arm_probe.cpp)
target_compile_features(three_arm_probe PRIVATE cxx_std_20)
target_link_libraries(three_arm_probe PRIVATE live::live Threads::Threads)
