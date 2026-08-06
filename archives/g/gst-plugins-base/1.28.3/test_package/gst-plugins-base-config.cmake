########## MACROS ###########################################################################
#############################################################################################

# Requires CMake > 3.15
if(${CMAKE_VERSION} VERSION_LESS "3.15")
    message(FATAL_ERROR "The 'CMakeDeps' generator only works with CMake >= 3.15")
endif()

if(gst-plugins-base_FIND_QUIETLY)
    set(gst-plugins-base_MESSAGE_MODE VERBOSE)
else()
    set(gst-plugins-base_MESSAGE_MODE STATUS)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/cmakedeps_macros.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/gst-plugins-baseTargets.cmake)
include(CMakeFindDependencyMacro)

check_build_type_defined()

foreach(_DEPENDENCY ${gst-plugins-base_FIND_DEPENDENCY_NAMES} )
    # Check that we have not already called a find_package with the transitive dependency
    if(NOT ${_DEPENDENCY}_FOUND)
        find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
    endif()
endforeach()

set(gst-plugins-base_VERSION_STRING "1.28.3")
set(gst-plugins-base_INCLUDE_DIRS ${gst-plugins-base_INCLUDE_DIRS_RELEASE} )
set(gst-plugins-base_INCLUDE_DIR ${gst-plugins-base_INCLUDE_DIRS_RELEASE} )
set(gst-plugins-base_LIBRARIES ${gst-plugins-base_LIBRARIES_RELEASE} )
set(gst-plugins-base_DEFINITIONS ${gst-plugins-base_DEFINITIONS_RELEASE} )


# Definition of extra CMake variables from cmake_extra_variables


# Only the last installed configuration BUILD_MODULES are included to avoid the collision
foreach(_BUILD_MODULE ${gst-plugins-base_BUILD_MODULES_PATHS_RELEASE} )
    message(${gst-plugins-base_MESSAGE_MODE} "Conan: Including build module from '${_BUILD_MODULE}'")
    include(${_BUILD_MODULE})
endforeach()


