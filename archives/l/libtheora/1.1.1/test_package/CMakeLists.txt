cmake_minimum_required(VERSION 3.10)
project(test_theora C)

find_package(libtheora REQUIRED)
find_package(Ogg REQUIRED)

add_executable(test_theora src/test_theora.c)
target_link_libraries(test_theora libtheora::libtheora Ogg::ogg)
# Workaround: libogg's CMakeDeps data has empty INCLUDE_DIRS, so add the
# include directory manually from the package folder variable.
target_include_directories(test_theora PRIVATE $<TARGET_PROPERTY:Ogg::ogg,INTERFACE_INCLUDE_DIRECTORIES>)
