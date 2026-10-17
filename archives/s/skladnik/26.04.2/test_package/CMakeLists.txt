cmake_minimum_required(VERSION 3.16)
project(skladnik_consumer_test CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core)

# The consumer test drives the installed skladnik binary (SKLADNIK_TEST_BIN)
# and parses the packaged theme data (SKLADNIK_TEST_DATA_DIR); it only needs
# QtCore for file, regex and process handling.
add_executable(skladnik_consumer_test main.cpp)
target_link_libraries(skladnik_consumer_test PRIVATE Qt6::Core)
