# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(gstreamer_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(gstreamer_FRAMEWORKS_FOUND_RELEASE "${gstreamer_FRAMEWORKS_RELEASE}" "${gstreamer_FRAMEWORK_DIRS_RELEASE}")

set(gstreamer_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET gstreamer_DEPS_TARGET)
    add_library(gstreamer_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET gstreamer_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${gstreamer_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${gstreamer_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:glib2::glib2;orc::orc;gstreamer::gstreamer>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### gstreamer_DEPS_TARGET to all of them
conan_package_library_targets("${gstreamer_LIBS_RELEASE}"    # libraries
                              "${gstreamer_LIB_DIRS_RELEASE}" # package_libdir
                              "${gstreamer_BIN_DIRS_RELEASE}" # package_bindir
                              "${gstreamer_LIBRARY_TYPE_RELEASE}"
                              "${gstreamer_IS_HOST_WINDOWS_RELEASE}"
                              gstreamer_DEPS_TARGET
                              gstreamer_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "gstreamer"    # package_name
                              "${gstreamer_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${gstreamer_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## COMPONENTS TARGET PROPERTIES Release ########################################

    ########## COMPONENT gstreamer::net #############

        set(gstreamer_gstreamer_net_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gstreamer_gstreamer_net_FRAMEWORKS_FOUND_RELEASE "${gstreamer_gstreamer_net_FRAMEWORKS_RELEASE}" "${gstreamer_gstreamer_net_FRAMEWORK_DIRS_RELEASE}")

        set(gstreamer_gstreamer_net_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gstreamer_gstreamer_net_DEPS_TARGET)
            add_library(gstreamer_gstreamer_net_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gstreamer_gstreamer_net_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gstreamer_gstreamer_net_DEPS_TARGET' to all of them
        conan_package_library_targets("${gstreamer_gstreamer_net_LIBS_RELEASE}"
                              "${gstreamer_gstreamer_net_LIB_DIRS_RELEASE}"
                              "${gstreamer_gstreamer_net_BIN_DIRS_RELEASE}" # package_bindir
                              "${gstreamer_gstreamer_net_LIBRARY_TYPE_RELEASE}"
                              "${gstreamer_gstreamer_net_IS_HOST_WINDOWS_RELEASE}"
                              gstreamer_gstreamer_net_DEPS_TARGET
                              gstreamer_gstreamer_net_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gstreamer_gstreamer_net"
                              "${gstreamer_gstreamer_net_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gstreamer::net
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_LIBRARIES_TARGETS}>
                     )

        if("${gstreamer_gstreamer_net_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gstreamer::net
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gstreamer_gstreamer_net_DEPS_TARGET)
        endif()

        set_property(TARGET gstreamer::net APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gstreamer::net APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gstreamer::net APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_LIB_DIRS_RELEASE}>)
        set_property(TARGET gstreamer::net APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gstreamer::net APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_net_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gstreamer::controller #############

        set(gstreamer_gstreamer_controller_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gstreamer_gstreamer_controller_FRAMEWORKS_FOUND_RELEASE "${gstreamer_gstreamer_controller_FRAMEWORKS_RELEASE}" "${gstreamer_gstreamer_controller_FRAMEWORK_DIRS_RELEASE}")

        set(gstreamer_gstreamer_controller_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gstreamer_gstreamer_controller_DEPS_TARGET)
            add_library(gstreamer_gstreamer_controller_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gstreamer_gstreamer_controller_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gstreamer_gstreamer_controller_DEPS_TARGET' to all of them
        conan_package_library_targets("${gstreamer_gstreamer_controller_LIBS_RELEASE}"
                              "${gstreamer_gstreamer_controller_LIB_DIRS_RELEASE}"
                              "${gstreamer_gstreamer_controller_BIN_DIRS_RELEASE}" # package_bindir
                              "${gstreamer_gstreamer_controller_LIBRARY_TYPE_RELEASE}"
                              "${gstreamer_gstreamer_controller_IS_HOST_WINDOWS_RELEASE}"
                              gstreamer_gstreamer_controller_DEPS_TARGET
                              gstreamer_gstreamer_controller_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gstreamer_gstreamer_controller"
                              "${gstreamer_gstreamer_controller_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gstreamer::controller
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_LIBRARIES_TARGETS}>
                     )

        if("${gstreamer_gstreamer_controller_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gstreamer::controller
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gstreamer_gstreamer_controller_DEPS_TARGET)
        endif()

        set_property(TARGET gstreamer::controller APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gstreamer::controller APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gstreamer::controller APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_LIB_DIRS_RELEASE}>)
        set_property(TARGET gstreamer::controller APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gstreamer::controller APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_controller_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gstreamer::base #############

        set(gstreamer_gstreamer_base_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gstreamer_gstreamer_base_FRAMEWORKS_FOUND_RELEASE "${gstreamer_gstreamer_base_FRAMEWORKS_RELEASE}" "${gstreamer_gstreamer_base_FRAMEWORK_DIRS_RELEASE}")

        set(gstreamer_gstreamer_base_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gstreamer_gstreamer_base_DEPS_TARGET)
            add_library(gstreamer_gstreamer_base_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gstreamer_gstreamer_base_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gstreamer_gstreamer_base_DEPS_TARGET' to all of them
        conan_package_library_targets("${gstreamer_gstreamer_base_LIBS_RELEASE}"
                              "${gstreamer_gstreamer_base_LIB_DIRS_RELEASE}"
                              "${gstreamer_gstreamer_base_BIN_DIRS_RELEASE}" # package_bindir
                              "${gstreamer_gstreamer_base_LIBRARY_TYPE_RELEASE}"
                              "${gstreamer_gstreamer_base_IS_HOST_WINDOWS_RELEASE}"
                              gstreamer_gstreamer_base_DEPS_TARGET
                              gstreamer_gstreamer_base_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gstreamer_gstreamer_base"
                              "${gstreamer_gstreamer_base_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gstreamer::base
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_LIBRARIES_TARGETS}>
                     )

        if("${gstreamer_gstreamer_base_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gstreamer::base
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gstreamer_gstreamer_base_DEPS_TARGET)
        endif()

        set_property(TARGET gstreamer::base APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gstreamer::base APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gstreamer::base APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_LIB_DIRS_RELEASE}>)
        set_property(TARGET gstreamer::base APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gstreamer::base APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_base_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gstreamer::gstreamer #############

        set(gstreamer_gstreamer_gstreamer_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gstreamer_gstreamer_gstreamer_FRAMEWORKS_FOUND_RELEASE "${gstreamer_gstreamer_gstreamer_FRAMEWORKS_RELEASE}" "${gstreamer_gstreamer_gstreamer_FRAMEWORK_DIRS_RELEASE}")

        set(gstreamer_gstreamer_gstreamer_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gstreamer_gstreamer_gstreamer_DEPS_TARGET)
            add_library(gstreamer_gstreamer_gstreamer_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gstreamer_gstreamer_gstreamer_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gstreamer_gstreamer_gstreamer_DEPS_TARGET' to all of them
        conan_package_library_targets("${gstreamer_gstreamer_gstreamer_LIBS_RELEASE}"
                              "${gstreamer_gstreamer_gstreamer_LIB_DIRS_RELEASE}"
                              "${gstreamer_gstreamer_gstreamer_BIN_DIRS_RELEASE}" # package_bindir
                              "${gstreamer_gstreamer_gstreamer_LIBRARY_TYPE_RELEASE}"
                              "${gstreamer_gstreamer_gstreamer_IS_HOST_WINDOWS_RELEASE}"
                              gstreamer_gstreamer_gstreamer_DEPS_TARGET
                              gstreamer_gstreamer_gstreamer_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gstreamer_gstreamer_gstreamer"
                              "${gstreamer_gstreamer_gstreamer_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gstreamer::gstreamer
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_LIBRARIES_TARGETS}>
                     )

        if("${gstreamer_gstreamer_gstreamer_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gstreamer::gstreamer
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gstreamer_gstreamer_gstreamer_DEPS_TARGET)
        endif()

        set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_LIB_DIRS_RELEASE}>)
        set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gstreamer_gstreamer_gstreamer_COMPILE_OPTIONS_RELEASE}>)


    ########## AGGREGATED GLOBAL TARGET WITH THE COMPONENTS #####################
    set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_LINK_LIBRARIES gstreamer::net)
    set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_LINK_LIBRARIES gstreamer::controller)
    set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_LINK_LIBRARIES gstreamer::base)
    set_property(TARGET gstreamer::gstreamer APPEND PROPERTY INTERFACE_LINK_LIBRARIES gstreamer::gstreamer)

########## For the modules (FindXXX)
set(gstreamer_LIBRARIES_RELEASE gstreamer::gstreamer)
