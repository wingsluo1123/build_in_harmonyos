cmake_minimum_required(VERSION 3.15)
project(test_libvorbis C)

# Find both libvorbis and its dependency libogg via Conan-generated CMakeDeps
find_package(libvorbis REQUIRED)
find_package(libogg REQUIRED)

add_executable(test_libvorbis test.c)
target_link_libraries(test_libvorbis libvorbis::libvorbis libogg::libogg)

# Workaround: libogg 1.3.6 cached binary has empty cpp_info.includedirs,
# so INTERFACE_INCLUDE_DIRECTORIES on libogg::libogg is not set.
# Manually add the ogg include directory from the CMakeDeps package folder variable.
if(DEFINED libogg_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_libvorbis PRIVATE ${libogg_PACKAGE_FOLDER_RELEASE}/include)
endif()

enable_testing()
add_test(NAME test_libvorbis COMMAND test_libvorbis)
