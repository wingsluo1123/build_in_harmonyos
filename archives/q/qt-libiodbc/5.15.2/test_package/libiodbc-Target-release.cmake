# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(libiodbc_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(libiodbc_FRAMEWORKS_FOUND_RELEASE "${libiodbc_FRAMEWORKS_RELEASE}" "${libiodbc_FRAMEWORK_DIRS_RELEASE}")

set(libiodbc_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET libiodbc_DEPS_TARGET)
    add_library(libiodbc_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET libiodbc_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${libiodbc_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${libiodbc_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### libiodbc_DEPS_TARGET to all of them
conan_package_library_targets("${libiodbc_LIBS_RELEASE}"    # libraries
                              "${libiodbc_LIB_DIRS_RELEASE}" # package_libdir
                              "${libiodbc_BIN_DIRS_RELEASE}" # package_bindir
                              "${libiodbc_LIBRARY_TYPE_RELEASE}"
                              "${libiodbc_IS_HOST_WINDOWS_RELEASE}"
                              libiodbc_DEPS_TARGET
                              libiodbc_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "libiodbc"    # package_name
                              "${libiodbc_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${libiodbc_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## GLOBAL TARGET PROPERTIES Release ########################################
    set_property(TARGET libiodbc::libiodbc
                 APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                 $<$<CONFIG:Release>:${libiodbc_OBJECTS_RELEASE}>
                 $<$<CONFIG:Release>:${libiodbc_LIBRARIES_TARGETS}>
                 )

    if("${libiodbc_LIBS_RELEASE}" STREQUAL "")
        # If the package is not declaring any "cpp_info.libs" the package deps, system libs,
        # frameworks etc are not linked to the imported targets and we need to do it to the
        # global target
        set_property(TARGET libiodbc::libiodbc
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     libiodbc_DEPS_TARGET)
    endif()

    set_property(TARGET libiodbc::libiodbc
                 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                 $<$<CONFIG:Release>:${libiodbc_LINKER_FLAGS_RELEASE}>)
    set_property(TARGET libiodbc::libiodbc
                 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                 $<$<CONFIG:Release>:${libiodbc_INCLUDE_DIRS_RELEASE}>)
    # Necessary to find LINK shared libraries in Linux
    set_property(TARGET libiodbc::libiodbc
                 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                 $<$<CONFIG:Release>:${libiodbc_LIB_DIRS_RELEASE}>)
    set_property(TARGET libiodbc::libiodbc
                 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                 $<$<CONFIG:Release>:${libiodbc_COMPILE_DEFINITIONS_RELEASE}>)
    set_property(TARGET libiodbc::libiodbc
                 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                 $<$<CONFIG:Release>:${libiodbc_COMPILE_OPTIONS_RELEASE}>)

########## For the modules (FindXXX)
set(libiodbc_LIBRARIES_RELEASE libiodbc::libiodbc)
