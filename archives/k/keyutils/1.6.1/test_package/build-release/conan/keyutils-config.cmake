########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(keyutils_FIND_QUIETLY)
    set(keyutils_MESSAGE_MODE VERBOSE)
else()
    set(keyutils_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/keyutilsTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${keyutils_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(keyutils_VERSION_STRING "1.6.1")
set(keyutils_INCLUDE_DIRS ${keyutils_INCLUDE_DIRS_RELEASE} )
set(keyutils_INCLUDE_DIR ${keyutils_INCLUDE_DIRS_RELEASE} )
set(keyutils_LIBRARIES ${keyutils_LIBRARIES_RELEASE} )
set(keyutils_DEFINITIONS ${keyutils_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${keyutils_BUILD_MODULES_PATHS_RELEASE} )
    message(${keyutils_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


