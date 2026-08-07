# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(qt-libiodbc_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(qt-libiodbc_FRAMEWORKS_FOUND_RELEASE "${qt-libiodbc_FRAMEWORKS_RELEASE}" "${qt-libiodbc_FRAMEWORK_DIRS_RELEASE}")

set(qt-libiodbc_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET qt-libiodbc_DEPS_TARGET)
    add_library(qt-libiodbc_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET qt-libiodbc_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${qt-libiodbc_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${qt-libiodbc_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:qt5-qtbase::qt5-qtbase;libiodbc::libiodbc>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### qt-libiodbc_DEPS_TARGET to all of them
conan_package_library_targets("${qt-libiodbc_LIBS_RELEASE}"    # libraries
                              "${qt-libiodbc_LIB_DIRS_RELEASE}" # package_libdir
                              "${qt-libiodbc_BIN_DIRS_RELEASE}" # package_bindir
                              "${qt-libiodbc_LIBRARY_TYPE_RELEASE}"
                              "${qt-libiodbc_IS_HOST_WINDOWS_RELEASE}"
                              qt-libiodbc_DEPS_TARGET
                              qt-libiodbc_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "qt-libiodbc"    # package_name
                              "${qt-libiodbc_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${qt-libiodbc_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## GLOBAL TARGET PROPERTIES Release ########################################
    set_property(TARGET qt-libiodbc::qt-libiodbc
                 APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                 $<$<CONFIG:Release>:${qt-libiodbc_OBJECTS_RELEASE}>
                 $<$<CONFIG:Release>:${qt-libiodbc_LIBRARIES_TARGETS}>
                 )

    if("${qt-libiodbc_LIBS_RELEASE}" STREQUAL "")
        # If the package is not declaring any "cpp_info.libs" the package deps, system libs,
        # frameworks etc are not linked to the imported targets and we need to do it to the
        # global target
        set_property(TARGET qt-libiodbc::qt-libiodbc
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     qt-libiodbc_DEPS_TARGET)
    endif()

    set_property(TARGET qt-libiodbc::qt-libiodbc
                 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                 $<$<CONFIG:Release>:${qt-libiodbc_LINKER_FLAGS_RELEASE}>)
    set_property(TARGET qt-libiodbc::qt-libiodbc
                 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                 $<$<CONFIG:Release>:${qt-libiodbc_INCLUDE_DIRS_RELEASE}>)
    # Necessary to find LINK shared libraries in Linux
    set_property(TARGET qt-libiodbc::qt-libiodbc
                 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                 $<$<CONFIG:Release>:${qt-libiodbc_LIB_DIRS_RELEASE}>)
    set_property(TARGET qt-libiodbc::qt-libiodbc
                 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                 $<$<CONFIG:Release>:${qt-libiodbc_COMPILE_DEFINITIONS_RELEASE}>)
    set_property(TARGET qt-libiodbc::qt-libiodbc
                 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                 $<$<CONFIG:Release>:${qt-libiodbc_COMPILE_OPTIONS_RELEASE}>)

########## For the modules (FindXXX)
set(qt-libiodbc_LIBRARIES_RELEASE qt-libiodbc::qt-libiodbc)
