cmake_minimum_required(VERSION 3.15)
project(mar_consumers LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Headers, libmar.a and the MAR_STATIC definition all come from the packaged mar.
find_package(mar CONFIG REQUIRED)

add_executable(mar_consumer_c consumer.c)
target_link_libraries(mar_consumer_c PRIVATE mar::mar)

add_executable(mar_consumer_cpp consumer_cpp.cpp)
target_link_libraries(mar_consumer_cpp PRIVATE mar::mar)

# Self-contained static-pie executables, like the packaged bin/mar: they run natively on AArch64
# and through qemu-aarch64 on x86 runners (there is no /lib/ld-musl-aarch64.so.1 there).
set_target_properties(mar_consumer_c mar_consumer_cpp PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_link_options(mar_consumer_c PRIVATE -static-pie)
target_link_options(mar_consumer_cpp PRIVATE -static-pie)
