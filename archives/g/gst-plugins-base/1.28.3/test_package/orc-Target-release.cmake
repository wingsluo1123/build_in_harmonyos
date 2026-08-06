# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(orc_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(orc_FRAMEWORKS_FOUND_RELEASE "${orc_FRAMEWORKS_RELEASE}" "${orc_FRAMEWORK_DIRS_RELEASE}")

set(orc_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET orc_DEPS_TARGET)
    add_library(orc_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET orc_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${orc_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${orc_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### orc_DEPS_TARGET to all of them
conan_package_library_targets("${orc_LIBS_RELEASE}"    # libraries
                              "${orc_LIB_DIRS_RELEASE}" # package_libdir
                              "${orc_BIN_DIRS_RELEASE}" # package_bindir
                              "${orc_LIBRARY_TYPE_RELEASE}"
                              "${orc_IS_HOST_WINDOWS_RELEASE}"
                              orc_DEPS_TARGET
                              orc_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "orc"    # package_name
                              "${orc_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${orc_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## GLOBAL TARGET PROPERTIES Release ########################################
    set_property(TARGET orc::orc
                 APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                 $<$<CONFIG:Release>:${orc_OBJECTS_RELEASE}>
                 $<$<CONFIG:Release>:${orc_LIBRARIES_TARGETS}>
                 )

    if("${orc_LIBS_RELEASE}" STREQUAL "")
        # If the package is not declaring any "cpp_info.libs" the package deps, system libs,
        # frameworks etc are not linked to the imported targets and we need to do it to the
        # global target
        set_property(TARGET orc::orc
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     orc_DEPS_TARGET)
    endif()

    set_property(TARGET orc::orc
                 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                 $<$<CONFIG:Release>:${orc_LINKER_FLAGS_RELEASE}>)
    set_property(TARGET orc::orc
                 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                 $<$<CONFIG:Release>:${orc_INCLUDE_DIRS_RELEASE}>)
    # Necessary to find LINK shared libraries in Linux
    set_property(TARGET orc::orc
                 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                 $<$<CONFIG:Release>:${orc_LIB_DIRS_RELEASE}>)
    set_property(TARGET orc::orc
                 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                 $<$<CONFIG:Release>:${orc_COMPILE_DEFINITIONS_RELEASE}>)
    set_property(TARGET orc::orc
                 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                 $<$<CONFIG:Release>:${orc_COMPILE_OPTIONS_RELEASE}>)

########## For the modules (FindXXX)
set(orc_LIBRARIES_RELEASE orc::orc)
