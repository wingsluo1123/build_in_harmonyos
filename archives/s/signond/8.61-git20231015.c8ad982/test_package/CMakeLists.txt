cmake_minimum_required(VERSION 3.16)
project(signond-consumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt6 first: the signond package is consumed through CMakeDeps
# (find_package(signond) -> signond::signond) and its generated config
# find_dependency()s Qt6, which is already FOUND at that point (Qt6_DIR is
# supplied by the test_package generate()); the Qt6 package itself comes from
# qtbase-sql-dbus.
find_package(Qt6 REQUIRED COMPONENTS Core DBus)
find_package(signond CONFIG REQUIRED)

add_executable(signond_consumer consumer.cpp)
target_link_libraries(signond_consumer PRIVATE
    Qt6::Core
    Qt6::DBus
    signond::signond
)
