# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(libxslt_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(libxslt_FRAMEWORKS_FOUND_RELEASE "${libxslt_FRAMEWORKS_RELEASE}" "${libxslt_FRAMEWORK_DIRS_RELEASE}")

set(libxslt_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET libxslt_DEPS_TARGET)
    add_library(libxslt_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET libxslt_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${libxslt_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${libxslt_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:LibXml2::LibXml2>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### libxslt_DEPS_TARGET to all of them
conan_package_library_targets("${libxslt_LIBS_RELEASE}"    # libraries
                              "${libxslt_LIB_DIRS_RELEASE}" # package_libdir
                              "${libxslt_BIN_DIRS_RELEASE}" # package_bindir
                              "${libxslt_LIBRARY_TYPE_RELEASE}"
                              "${libxslt_IS_HOST_WINDOWS_RELEASE}"
                              libxslt_DEPS_TARGET
                              libxslt_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "libxslt"    # package_name
                              "${libxslt_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${libxslt_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## GLOBAL TARGET PROPERTIES Release ########################################
    set_property(TARGET LibXslt::LibXslt
                 APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                 $<$<CONFIG:Release>:${libxslt_OBJECTS_RELEASE}>
                 $<$<CONFIG:Release>:${libxslt_LIBRARIES_TARGETS}>
                 )

    if("${libxslt_LIBS_RELEASE}" STREQUAL "")
        # If the package is not declaring any "cpp_info.libs" the package deps, system libs,
        # frameworks etc are not linked to the imported targets and we need to do it to the
        # global target
        set_property(TARGET LibXslt::LibXslt
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     libxslt_DEPS_TARGET)
    endif()

    set_property(TARGET LibXslt::LibXslt
                 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                 $<$<CONFIG:Release>:${libxslt_LINKER_FLAGS_RELEASE}>)
    set_property(TARGET LibXslt::LibXslt
                 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                 $<$<CONFIG:Release>:${libxslt_INCLUDE_DIRS_RELEASE}>)
    # Necessary to find LINK shared libraries in Linux
    set_property(TARGET LibXslt::LibXslt
                 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                 $<$<CONFIG:Release>:${libxslt_LIB_DIRS_RELEASE}>)
    set_property(TARGET LibXslt::LibXslt
                 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                 $<$<CONFIG:Release>:${libxslt_COMPILE_DEFINITIONS_RELEASE}>)
    set_property(TARGET LibXslt::LibXslt
                 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                 $<$<CONFIG:Release>:${libxslt_COMPILE_OPTIONS_RELEASE}>)

########## For the modules (FindXXX)
set(libxslt_LIBRARIES_RELEASE LibXslt::LibXslt)
