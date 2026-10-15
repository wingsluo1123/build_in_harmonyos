cmake_minimum_required(VERSION 3.20)
project(test_xtrkcad C)

find_package(xtrkcad CONFIG REQUIRED)

add_executable(test_xtrkcad test.c)
target_link_libraries(test_xtrkcad PRIVATE xtrkcad::xtrkcad)
# A package consumed from the build folder it is still being tested in does not
# always come with include path and library in the generated files, so take both
# from the package folder conan reports when that happens.
if(NOT xtrkcad_INCLUDE_DIRS)
    if(NOT xtrkcad_PACKAGE_FOLDER_RELEASE)
        message(FATAL_ERROR "xtrkcad: no include directories were generated for the package")
    endif()
    target_include_directories(test_xtrkcad PRIVATE "${xtrkcad_PACKAGE_FOLDER_RELEASE}/include")
    if(EXISTS "${xtrkcad_PACKAGE_FOLDER_RELEASE}/lib/libdynstring.a")
        target_link_libraries(test_xtrkcad PRIVATE "${xtrkcad_PACKAGE_FOLDER_RELEASE}/lib/libdynstring.a")
    endif()
endif()
