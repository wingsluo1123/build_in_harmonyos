# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(qt5-qtbase_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(qt5-qtbase_FRAMEWORKS_FOUND_RELEASE "${qt5-qtbase_FRAMEWORKS_RELEASE}" "${qt5-qtbase_FRAMEWORK_DIRS_RELEASE}")

set(qt5-qtbase_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET qt5-qtbase_DEPS_TARGET)
    add_library(qt5-qtbase_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET qt5-qtbase_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${qt5-qtbase_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${qt5-qtbase_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:Qt5::Core>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### qt5-qtbase_DEPS_TARGET to all of them
conan_package_library_targets("${qt5-qtbase_LIBS_RELEASE}"    # libraries
                              "${qt5-qtbase_LIB_DIRS_RELEASE}" # package_libdir
                              "${qt5-qtbase_BIN_DIRS_RELEASE}" # package_bindir
                              "${qt5-qtbase_LIBRARY_TYPE_RELEASE}"
                              "${qt5-qtbase_IS_HOST_WINDOWS_RELEASE}"
                              qt5-qtbase_DEPS_TARGET
                              qt5-qtbase_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "qt5-qtbase"    # package_name
                              "${qt5-qtbase_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${qt5-qtbase_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## COMPONENTS TARGET PROPERTIES Release ########################################

    ########## COMPONENT Qt5::Concurrent #############

        set(qt5-qtbase_Qt5_Concurrent_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(qt5-qtbase_Qt5_Concurrent_FRAMEWORKS_FOUND_RELEASE "${qt5-qtbase_Qt5_Concurrent_FRAMEWORKS_RELEASE}" "${qt5-qtbase_Qt5_Concurrent_FRAMEWORK_DIRS_RELEASE}")

        set(qt5-qtbase_Qt5_Concurrent_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET qt5-qtbase_Qt5_Concurrent_DEPS_TARGET)
            add_library(qt5-qtbase_Qt5_Concurrent_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET qt5-qtbase_Qt5_Concurrent_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'qt5-qtbase_Qt5_Concurrent_DEPS_TARGET' to all of them
        conan_package_library_targets("${qt5-qtbase_Qt5_Concurrent_LIBS_RELEASE}"
                              "${qt5-qtbase_Qt5_Concurrent_LIB_DIRS_RELEASE}"
                              "${qt5-qtbase_Qt5_Concurrent_BIN_DIRS_RELEASE}" # package_bindir
                              "${qt5-qtbase_Qt5_Concurrent_LIBRARY_TYPE_RELEASE}"
                              "${qt5-qtbase_Qt5_Concurrent_IS_HOST_WINDOWS_RELEASE}"
                              qt5-qtbase_Qt5_Concurrent_DEPS_TARGET
                              qt5-qtbase_Qt5_Concurrent_LIBRARIES_TARGETS
                              "_RELEASE"
                              "qt5-qtbase_Qt5_Concurrent"
                              "${qt5-qtbase_Qt5_Concurrent_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET Qt5::Concurrent
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_LIBRARIES_TARGETS}>
                     )

        if("${qt5-qtbase_Qt5_Concurrent_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET Qt5::Concurrent
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         qt5-qtbase_Qt5_Concurrent_DEPS_TARGET)
        endif()

        set_property(TARGET Qt5::Concurrent APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET Qt5::Concurrent APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Concurrent APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_LIB_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Concurrent APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET Qt5::Concurrent APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Concurrent_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT Qt5::Test #############

        set(qt5-qtbase_Qt5_Test_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(qt5-qtbase_Qt5_Test_FRAMEWORKS_FOUND_RELEASE "${qt5-qtbase_Qt5_Test_FRAMEWORKS_RELEASE}" "${qt5-qtbase_Qt5_Test_FRAMEWORK_DIRS_RELEASE}")

        set(qt5-qtbase_Qt5_Test_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET qt5-qtbase_Qt5_Test_DEPS_TARGET)
            add_library(qt5-qtbase_Qt5_Test_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET qt5-qtbase_Qt5_Test_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'qt5-qtbase_Qt5_Test_DEPS_TARGET' to all of them
        conan_package_library_targets("${qt5-qtbase_Qt5_Test_LIBS_RELEASE}"
                              "${qt5-qtbase_Qt5_Test_LIB_DIRS_RELEASE}"
                              "${qt5-qtbase_Qt5_Test_BIN_DIRS_RELEASE}" # package_bindir
                              "${qt5-qtbase_Qt5_Test_LIBRARY_TYPE_RELEASE}"
                              "${qt5-qtbase_Qt5_Test_IS_HOST_WINDOWS_RELEASE}"
                              qt5-qtbase_Qt5_Test_DEPS_TARGET
                              qt5-qtbase_Qt5_Test_LIBRARIES_TARGETS
                              "_RELEASE"
                              "qt5-qtbase_Qt5_Test"
                              "${qt5-qtbase_Qt5_Test_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET Qt5::Test
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_LIBRARIES_TARGETS}>
                     )

        if("${qt5-qtbase_Qt5_Test_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET Qt5::Test
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         qt5-qtbase_Qt5_Test_DEPS_TARGET)
        endif()

        set_property(TARGET Qt5::Test APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET Qt5::Test APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Test APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_LIB_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Test APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET Qt5::Test APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Test_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT Qt5::Gui #############

        set(qt5-qtbase_Qt5_Gui_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(qt5-qtbase_Qt5_Gui_FRAMEWORKS_FOUND_RELEASE "${qt5-qtbase_Qt5_Gui_FRAMEWORKS_RELEASE}" "${qt5-qtbase_Qt5_Gui_FRAMEWORK_DIRS_RELEASE}")

        set(qt5-qtbase_Qt5_Gui_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET qt5-qtbase_Qt5_Gui_DEPS_TARGET)
            add_library(qt5-qtbase_Qt5_Gui_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET qt5-qtbase_Qt5_Gui_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'qt5-qtbase_Qt5_Gui_DEPS_TARGET' to all of them
        conan_package_library_targets("${qt5-qtbase_Qt5_Gui_LIBS_RELEASE}"
                              "${qt5-qtbase_Qt5_Gui_LIB_DIRS_RELEASE}"
                              "${qt5-qtbase_Qt5_Gui_BIN_DIRS_RELEASE}" # package_bindir
                              "${qt5-qtbase_Qt5_Gui_LIBRARY_TYPE_RELEASE}"
                              "${qt5-qtbase_Qt5_Gui_IS_HOST_WINDOWS_RELEASE}"
                              qt5-qtbase_Qt5_Gui_DEPS_TARGET
                              qt5-qtbase_Qt5_Gui_LIBRARIES_TARGETS
                              "_RELEASE"
                              "qt5-qtbase_Qt5_Gui"
                              "${qt5-qtbase_Qt5_Gui_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET Qt5::Gui
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_LIBRARIES_TARGETS}>
                     )

        if("${qt5-qtbase_Qt5_Gui_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET Qt5::Gui
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         qt5-qtbase_Qt5_Gui_DEPS_TARGET)
        endif()

        set_property(TARGET Qt5::Gui APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET Qt5::Gui APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Gui APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_LIB_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Gui APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET Qt5::Gui APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Gui_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT Qt5::Network #############

        set(qt5-qtbase_Qt5_Network_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(qt5-qtbase_Qt5_Network_FRAMEWORKS_FOUND_RELEASE "${qt5-qtbase_Qt5_Network_FRAMEWORKS_RELEASE}" "${qt5-qtbase_Qt5_Network_FRAMEWORK_DIRS_RELEASE}")

        set(qt5-qtbase_Qt5_Network_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET qt5-qtbase_Qt5_Network_DEPS_TARGET)
            add_library(qt5-qtbase_Qt5_Network_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET qt5-qtbase_Qt5_Network_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'qt5-qtbase_Qt5_Network_DEPS_TARGET' to all of them
        conan_package_library_targets("${qt5-qtbase_Qt5_Network_LIBS_RELEASE}"
                              "${qt5-qtbase_Qt5_Network_LIB_DIRS_RELEASE}"
                              "${qt5-qtbase_Qt5_Network_BIN_DIRS_RELEASE}" # package_bindir
                              "${qt5-qtbase_Qt5_Network_LIBRARY_TYPE_RELEASE}"
                              "${qt5-qtbase_Qt5_Network_IS_HOST_WINDOWS_RELEASE}"
                              qt5-qtbase_Qt5_Network_DEPS_TARGET
                              qt5-qtbase_Qt5_Network_LIBRARIES_TARGETS
                              "_RELEASE"
                              "qt5-qtbase_Qt5_Network"
                              "${qt5-qtbase_Qt5_Network_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET Qt5::Network
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_LIBRARIES_TARGETS}>
                     )

        if("${qt5-qtbase_Qt5_Network_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET Qt5::Network
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         qt5-qtbase_Qt5_Network_DEPS_TARGET)
        endif()

        set_property(TARGET Qt5::Network APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET Qt5::Network APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Network APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_LIB_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Network APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET Qt5::Network APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Network_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT Qt5::Core #############

        set(qt5-qtbase_Qt5_Core_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(qt5-qtbase_Qt5_Core_FRAMEWORKS_FOUND_RELEASE "${qt5-qtbase_Qt5_Core_FRAMEWORKS_RELEASE}" "${qt5-qtbase_Qt5_Core_FRAMEWORK_DIRS_RELEASE}")

        set(qt5-qtbase_Qt5_Core_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET qt5-qtbase_Qt5_Core_DEPS_TARGET)
            add_library(qt5-qtbase_Qt5_Core_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET qt5-qtbase_Qt5_Core_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'qt5-qtbase_Qt5_Core_DEPS_TARGET' to all of them
        conan_package_library_targets("${qt5-qtbase_Qt5_Core_LIBS_RELEASE}"
                              "${qt5-qtbase_Qt5_Core_LIB_DIRS_RELEASE}"
                              "${qt5-qtbase_Qt5_Core_BIN_DIRS_RELEASE}" # package_bindir
                              "${qt5-qtbase_Qt5_Core_LIBRARY_TYPE_RELEASE}"
                              "${qt5-qtbase_Qt5_Core_IS_HOST_WINDOWS_RELEASE}"
                              qt5-qtbase_Qt5_Core_DEPS_TARGET
                              qt5-qtbase_Qt5_Core_LIBRARIES_TARGETS
                              "_RELEASE"
                              "qt5-qtbase_Qt5_Core"
                              "${qt5-qtbase_Qt5_Core_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET Qt5::Core
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_LIBRARIES_TARGETS}>
                     )

        if("${qt5-qtbase_Qt5_Core_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET Qt5::Core
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         qt5-qtbase_Qt5_Core_DEPS_TARGET)
        endif()

        set_property(TARGET Qt5::Core APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET Qt5::Core APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Core APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_LIB_DIRS_RELEASE}>)
        set_property(TARGET Qt5::Core APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET Qt5::Core APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Core_COMPILE_OPTIONS_RELEASE}>)


    ########## AGGREGATED GLOBAL TARGET WITH THE COMPONENTS #####################
    set_property(TARGET qt5-qtbase::qt5-qtbase APPEND PROPERTY INTERFACE_LINK_LIBRARIES Qt5::Concurrent)
    set_property(TARGET qt5-qtbase::qt5-qtbase APPEND PROPERTY INTERFACE_LINK_LIBRARIES Qt5::Test)
    set_property(TARGET qt5-qtbase::qt5-qtbase APPEND PROPERTY INTERFACE_LINK_LIBRARIES Qt5::Gui)
    set_property(TARGET qt5-qtbase::qt5-qtbase APPEND PROPERTY INTERFACE_LINK_LIBRARIES Qt5::Network)
    set_property(TARGET qt5-qtbase::qt5-qtbase APPEND PROPERTY INTERFACE_LINK_LIBRARIES Qt5::Core)

########## For the modules (FindXXX)
set(qt5-qtbase_LIBRARIES_RELEASE qt5-qtbase::qt5-qtbase)
