# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(opencore-amrwb_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(opencore-amrwb_FRAMEWORKS_FOUND_RELEASE "${opencore-amrwb_FRAMEWORKS_RELEASE}" "${opencore-amrwb_FRAMEWORK_DIRS_RELEASE}")

set(opencore-amrwb_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET opencore-amrwb_DEPS_TARGET)
    add_library(opencore-amrwb_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET opencore-amrwb_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${opencore-amrwb_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${opencore-amrwb_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### opencore-amrwb_DEPS_TARGET to all of them
conan_package_library_targets("${opencore-amrwb_LIBS_RELEASE}"    # libraries
                              "${opencore-amrwb_LIB_DIRS_RELEASE}" # package_libdir
                              "${opencore-amrwb_BIN_DIRS_RELEASE}" # package_bindir
                              "${opencore-amrwb_LIBRARY_TYPE_RELEASE}"
                              "${opencore-amrwb_IS_HOST_WINDOWS_RELEASE}"
                              opencore-amrwb_DEPS_TARGET
                              opencore-amrwb_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "opencore-amrwb"    # package_name
                              "${opencore-amrwb_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${opencore-amrwb_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## GLOBAL TARGET PROPERTIES Release ########################################
    set_property(TARGET opencore_amrwb::opencore_amrwb
                 APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                 $<$<CONFIG:Release>:${opencore-amrwb_OBJECTS_RELEASE}>
                 $<$<CONFIG:Release>:${opencore-amrwb_LIBRARIES_TARGETS}>
                 )

    if("${opencore-amrwb_LIBS_RELEASE}" STREQUAL "")
        # If the package is not declaring any "cpp_info.libs" the package deps, system libs,
        # frameworks etc are not linked to the imported targets and we need to do it to the
        # global target
        set_property(TARGET opencore_amrwb::opencore_amrwb
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     opencore-amrwb_DEPS_TARGET)
    endif()

    set_property(TARGET opencore_amrwb::opencore_amrwb
                 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                 $<$<CONFIG:Release>:${opencore-amrwb_LINKER_FLAGS_RELEASE}>)
    set_property(TARGET opencore_amrwb::opencore_amrwb
                 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                 $<$<CONFIG:Release>:${opencore-amrwb_INCLUDE_DIRS_RELEASE}>)
    # Necessary to find LINK shared libraries in Linux
    set_property(TARGET opencore_amrwb::opencore_amrwb
                 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                 $<$<CONFIG:Release>:${opencore-amrwb_LIB_DIRS_RELEASE}>)
    set_property(TARGET opencore_amrwb::opencore_amrwb
                 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                 $<$<CONFIG:Release>:${opencore-amrwb_COMPILE_DEFINITIONS_RELEASE}>)
    set_property(TARGET opencore_amrwb::opencore_amrwb
                 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                 $<$<CONFIG:Release>:${opencore-amrwb_COMPILE_OPTIONS_RELEASE}>)

########## For the modules (FindXXX)
set(opencore-amrwb_LIBRARIES_RELEASE opencore_amrwb::opencore_amrwb)
