# Avoid multiple calls to find_package to append duplicated properties to the targets
include_guard()########### VARIABLES #######################################################################
#############################################################################################
set(gst-plugins-base_FRAMEWORKS_FOUND_RELEASE "") # Will be filled later
conan_find_apple_frameworks(gst-plugins-base_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_FRAMEWORKS_RELEASE}" "${gst-plugins-base_FRAMEWORK_DIRS_RELEASE}")

set(gst-plugins-base_LIBRARIES_TARGETS "") # Will be filled later


######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
if(NOT TARGET gst-plugins-base_DEPS_TARGET)
    add_library(gst-plugins-base_DEPS_TARGET INTERFACE IMPORTED)
endif()

set_property(TARGET gst-plugins-base_DEPS_TARGET
             APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             $<$<CONFIG:Release>:${gst-plugins-base_FRAMEWORKS_FOUND_RELEASE}>
             $<$<CONFIG:Release>:${gst-plugins-base_SYSTEM_LIBS_RELEASE}>
             $<$<CONFIG:Release>:gstreamer::gstreamer;glib2::glib2;orc::orc>)

####### Find the libraries declared in cpp_info.libs, create an IMPORTED target for each one and link the
####### gst-plugins-base_DEPS_TARGET to all of them
conan_package_library_targets("${gst-plugins-base_LIBS_RELEASE}"    # libraries
                              "${gst-plugins-base_LIB_DIRS_RELEASE}" # package_libdir
                              "${gst-plugins-base_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_DEPS_TARGET
                              gst-plugins-base_LIBRARIES_TARGETS  # out_libraries_targets
                              "_RELEASE"
                              "gst-plugins-base"    # package_name
                              "${gst-plugins-base_NO_SONAME_MODE_RELEASE}")  # soname

# FIXME: What is the result of this for multi-config? All configs adding themselves to path?
set(CMAKE_MODULE_PATH ${gst-plugins-base_BUILD_DIRS_RELEASE} ${CMAKE_MODULE_PATH})

########## COMPONENTS TARGET PROPERTIES Release ########################################

    ########## COMPONENT gst-plugins-base::gstreamer-allocators-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-allocators-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-allocators-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-allocators-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-allocators-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-allocators-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-allocators-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-allocators-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-video-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-video-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-video-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-video-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-video-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-video-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-video-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-video-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-video-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-tag-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-tag-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-tag-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-tag-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-tag-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-tag-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-tag-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-tag-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-sdp-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-sdp-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-sdp-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-sdp-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-sdp-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-sdp-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-sdp-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-sdp-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-rtsp-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-rtsp-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-rtsp-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-rtsp-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-rtsp-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-rtsp-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-rtsp-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-rtsp-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-rtp-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-rtp-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-rtp-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-rtp-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-rtp-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-rtp-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-rtp-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-rtp-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-riff-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-riff-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-riff-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-riff-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-riff-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-riff-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-riff-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-riff-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-pbutils-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-pbutils-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-pbutils-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-pbutils-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-pbutils-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-pbutils-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-pbutils-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-pbutils-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-fft-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-fft-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-fft-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-fft-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-fft-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-fft-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-fft-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-fft-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-audio-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-audio-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-audio-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-audio-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-audio-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-audio-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-audio-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-audio-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## COMPONENT gst-plugins-base::gstreamer-app-1.0 #############

        set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_FRAMEWORKS_FOUND_RELEASE "")
        conan_find_apple_frameworks(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_FRAMEWORKS_FOUND_RELEASE "${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_FRAMEWORKS_RELEASE}" "${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_FRAMEWORK_DIRS_RELEASE}")

        set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIBRARIES_TARGETS "")

        ######## Create an interface target to contain all the dependencies (frameworks, system and conan deps)
        if(NOT TARGET gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEPS_TARGET)
            add_library(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEPS_TARGET INTERFACE IMPORTED)
        endif()

        set_property(TARGET gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEPS_TARGET
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_FRAMEWORKS_FOUND_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_SYSTEM_LIBS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEPENDENCIES_RELEASE}>
                     )

        ####### Find the libraries declared in cpp_info.component["xxx"].libs,
        ####### create an IMPORTED target for each one and link the 'gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEPS_TARGET' to all of them
        conan_package_library_targets("${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIBS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIB_DIRS_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_BIN_DIRS_RELEASE}" # package_bindir
                              "${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIBRARY_TYPE_RELEASE}"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_IS_HOST_WINDOWS_RELEASE}"
                              gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEPS_TARGET
                              gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIBRARIES_TARGETS
                              "_RELEASE"
                              "gst-plugins-base_gst-plugins-base_gstreamer-app-1.0"
                              "${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_NO_SONAME_MODE_RELEASE}")


        ########## TARGET PROPERTIES #####################################
        set_property(TARGET gst-plugins-base::gstreamer-app-1.0
                     APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_OBJECTS_RELEASE}>
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIBRARIES_TARGETS}>
                     )

        if("${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIBS_RELEASE}" STREQUAL "")
            # If the component is not declaring any "cpp_info.components['foo'].libs" the system, frameworks etc are not
            # linked to the imported targets and we need to do it to the global target
            set_property(TARGET gst-plugins-base::gstreamer-app-1.0
                         APPEND PROPERTY INTERFACE_LINK_LIBRARIES
                         gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEPS_TARGET)
        endif()

        set_property(TARGET gst-plugins-base::gstreamer-app-1.0 APPEND PROPERTY INTERFACE_LINK_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LINKER_FLAGS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-app-1.0 APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_INCLUDE_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-app-1.0 APPEND PROPERTY INTERFACE_LINK_DIRECTORIES
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIB_DIRS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-app-1.0 APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_COMPILE_DEFINITIONS_RELEASE}>)
        set_property(TARGET gst-plugins-base::gstreamer-app-1.0 APPEND PROPERTY INTERFACE_COMPILE_OPTIONS
                     $<$<CONFIG:Release>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_COMPILE_OPTIONS_RELEASE}>)


    ########## AGGREGATED GLOBAL TARGET WITH THE COMPONENTS #####################
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-allocators-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-video-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-tag-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-sdp-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-rtsp-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-rtp-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-riff-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-pbutils-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-fft-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-audio-1.0)
    set_property(TARGET gst-plugins-base::gst-plugins-base APPEND PROPERTY INTERFACE_LINK_LIBRARIES gst-plugins-base::gstreamer-app-1.0)

########## For the modules (FindXXX)
set(gst-plugins-base_LIBRARIES_RELEASE gst-plugins-base::gst-plugins-base)
