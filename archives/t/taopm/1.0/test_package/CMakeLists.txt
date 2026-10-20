cmake_minimum_required(VERSION 3.15)
project(test_taopm CXX)

# Pull in taopm through Conan's CMakeDeps generator.  The package also exports
# TAO_NO_GRAPHICS as an INTERFACE compile definition, so taodefs.h resolves
# without any GL/GLUT headers here.
find_package(taopm REQUIRED)

# CMakeDeps publishes the package folder as <name>_PACKAGE_FOLDER_<CONFIG>;
# the packaged CLI tools live next to it and are used below.
string(TOUPPER "${CMAKE_BUILD_TYPE}" _TAOPM_BUILD_TYPE)
if(NOT _TAOPM_BUILD_TYPE)
    set(_TAOPM_BUILD_TYPE RELEASE)
endif()
set(TAOPM_PACKAGE_DIR "${taopm_PACKAGE_FOLDER_${_TAOPM_BUILD_TYPE}}")
if(NOT TAOPM_PACKAGE_DIR)
    message(FATAL_ERROR "cannot locate the taopm package folder "
                        "(expected taopm_PACKAGE_FOLDER_${_TAOPM_BUILD_TYPE})")
endif()
set(TAOPARSE "${TAOPM_PACKAGE_DIR}/bin/taoparse")
if(NOT EXISTS "${TAOPARSE}")
    message(FATAL_ERROR "the packaged taoparse tool is missing: ${TAOPARSE}")
endif()

# 1) The library API: a real Tao program that synthesises and self-validates.
add_executable(test_tao_api test_tao.cpp)
target_link_libraries(test_tao_api PRIVATE taopm::taopm)

# 2) The WAVE validator for the tao2wav output.
add_executable(check_wav check_wav.cpp)

# 3) The documented script workflow: taoparse translates a .tao score into a
#    C++ program, which is then compiled against libtao and run.
#
#    taoparse names the score's output streams after the script file it was
#    given (strtok of the argument at the first '.'), so it has to be invoked
#    with a bare relative name from the directory holding the script — an
#    absolute path would put the '.' of a directory component into the stream
#    name.  This also mirrors what `taoparse circle.tao' does for a user.
set(TAO_GENERATED_CC "${CMAKE_CURRENT_BINARY_DIR}/tao_script_generated.cc")
add_custom_command(
    OUTPUT "${TAO_GENERATED_CC}"
    COMMAND sh -c "\"${TAOPARSE}\" test_script.tao > \"${TAO_GENERATED_CC}\""
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/test_script.tao" "${TAOPARSE}"
    COMMENT "taoparse: test_script.tao -> tao_script_generated.cc"
    VERBATIM)
add_executable(test_tao_script "${TAO_GENERATED_CC}")
target_link_libraries(test_tao_script PRIVATE taopm::taopm)
