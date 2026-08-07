########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(libiodbc_FIND_QUIETLY)
    set(libiodbc_MESSAGE_MODE VERBOSE)
else()
    set(libiodbc_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/libiodbcTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${libiodbc_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(libiodbc_VERSION_STRING "3.52.16")
set(libiodbc_INCLUDE_DIRS ${libiodbc_INCLUDE_DIRS_RELEASE} )
set(libiodbc_INCLUDE_DIR ${libiodbc_INCLUDE_DIRS_RELEASE} )
set(libiodbc_LIBRARIES ${libiodbc_LIBRARIES_RELEASE} )
set(libiodbc_DEFINITIONS ${libiodbc_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${libiodbc_BUILD_MODULES_PATHS_RELEASE} )
    message(${libiodbc_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


