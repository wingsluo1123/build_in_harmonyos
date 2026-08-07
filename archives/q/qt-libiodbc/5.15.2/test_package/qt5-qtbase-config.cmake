########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(qt5-qtbase_FIND_QUIETLY)
    set(qt5-qtbase_MESSAGE_MODE VERBOSE)
else()
    set(qt5-qtbase_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/qt5-qtbaseTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${qt5-qtbase_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(qt5-qtbase_VERSION_STRING "5.15.2")
set(qt5-qtbase_INCLUDE_DIRS ${qt5-qtbase_INCLUDE_DIRS_RELEASE} )
set(qt5-qtbase_INCLUDE_DIR ${qt5-qtbase_INCLUDE_DIRS_RELEASE} )
set(qt5-qtbase_LIBRARIES ${qt5-qtbase_LIBRARIES_RELEASE} )
set(qt5-qtbase_DEFINITIONS ${qt5-qtbase_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${qt5-qtbase_BUILD_MODULES_PATHS_RELEASE} )
    message(${qt5-qtbase_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


