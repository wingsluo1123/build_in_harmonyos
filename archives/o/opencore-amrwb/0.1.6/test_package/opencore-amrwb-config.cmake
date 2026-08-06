########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(opencore-amrwb_FIND_QUIETLY)
    set(opencore-amrwb_MESSAGE_MODE VERBOSE)
else()
    set(opencore-amrwb_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/opencore-amrwbTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${opencore-amrwb_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(opencore-amrwb_VERSION_STRING "0.1.6")
set(opencore-amrwb_INCLUDE_DIRS ${opencore-amrwb_INCLUDE_DIRS_RELEASE} )
set(opencore-amrwb_INCLUDE_DIR ${opencore-amrwb_INCLUDE_DIRS_RELEASE} )
set(opencore-amrwb_LIBRARIES ${opencore-amrwb_LIBRARIES_RELEASE} )
set(opencore-amrwb_DEFINITIONS ${opencore-amrwb_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${opencore-amrwb_BUILD_MODULES_PATHS_RELEASE} )
    message(${opencore-amrwb_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


