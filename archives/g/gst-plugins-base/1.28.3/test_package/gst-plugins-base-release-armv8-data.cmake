########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

list(APPEND gst-plugins-base_COMPONENT_NAMES gst-plugins-base::gstreamer-app-1.0 gst-plugins-base::gstreamer-audio-1.0 gst-plugins-base::gstreamer-fft-1.0 gst-plugins-base::gstreamer-pbutils-1.0 gst-plugins-base::gstreamer-riff-1.0 gst-plugins-base::gstreamer-rtp-1.0 gst-plugins-base::gstreamer-rtsp-1.0 gst-plugins-base::gstreamer-sdp-1.0 gst-plugins-base::gstreamer-tag-1.0 gst-plugins-base::gstreamer-video-1.0 gst-plugins-base::gstreamer-allocators-1.0)
list(REMOVE_DUPLICATES gst-plugins-base_COMPONENT_NAMES)
if(DEFINED gst-plugins-base_FIND_DEPENDENCY_NAMES)
  list(APPEND gst-plugins-base_FIND_DEPENDENCY_NAMES gstreamer orc glib2)
  list(REMOVE_DUPLICATES gst-plugins-base_FIND_DEPENDENCY_NAMES)
else()
  set(gst-plugins-base_FIND_DEPENDENCY_NAMES gstreamer orc glib2)
endif()
set(gstreamer_FIND_MODE "NO_MODULE")
set(orc_FIND_MODE "NO_MODULE")
set(glib2_FIND_MODE "NO_MODULE")

########### VARIABLES #######################################################################
#############################################################################################
set(gst-plugins-base_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/gst-p5e47a892e90ee/p")
set(gst-plugins-base_BUILD_MODULES_PATHS_RELEASE )


set(gst-plugins-base_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_RES_DIRS_RELEASE )
set(gst-plugins-base_DEFINITIONS_RELEASE )
set(gst-plugins-base_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_OBJECTS_RELEASE )
set(gst-plugins-base_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_COMPILE_OPTIONS_C_RELEASE )
set(gst-plugins-base_COMPILE_OPTIONS_CXX_RELEASE )
set(gst-plugins-base_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_BIN_DIRS_RELEASE )
set(gst-plugins-base_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_LIBS_RELEASE gstallocators-1.0 gstvideo-1.0 gsttag-1.0 gstsdp-1.0 gstrtsp-1.0 gstrtp-1.0 gstriff-1.0 gstpbutils-1.0 gstfft-1.0 gstaudio-1.0 gstapp-1.0)
set(gst-plugins-base_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_FRAMEWORKS_RELEASE )
set(gst-plugins-base_BUILD_DIRS_RELEASE )
set(gst-plugins-base_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(gst-plugins-base_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_COMPILE_OPTIONS_C_RELEASE}>")
set(gst-plugins-base_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_EXE_LINK_FLAGS_RELEASE}>")


set(gst-plugins-base_COMPONENTS_RELEASE gst-plugins-base::gstreamer-app-1.0 gst-plugins-base::gstreamer-audio-1.0 gst-plugins-base::gstreamer-fft-1.0 gst-plugins-base::gstreamer-pbutils-1.0 gst-plugins-base::gstreamer-riff-1.0 gst-plugins-base::gstreamer-rtp-1.0 gst-plugins-base::gstreamer-rtsp-1.0 gst-plugins-base::gstreamer-sdp-1.0 gst-plugins-base::gstreamer-tag-1.0 gst-plugins-base::gstreamer-video-1.0 gst-plugins-base::gstreamer-allocators-1.0)
########### COMPONENT gst-plugins-base::gstreamer-allocators-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LIBS_RELEASE gstallocators-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-allocators-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-video-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LIBS_RELEASE gstvideo-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-video-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-tag-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LIBS_RELEASE gsttag-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-tag-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-sdp-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LIBS_RELEASE gstsdp-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-sdp-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-rtsp-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LIBS_RELEASE gstrtsp-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-rtsp-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-rtp-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LIBS_RELEASE gstrtp-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-rtp-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-riff-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LIBS_RELEASE gstriff-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-riff-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-pbutils-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LIBS_RELEASE gstpbutils-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-pbutils-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-fft-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LIBS_RELEASE gstfft-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-fft-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-audio-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LIBS_RELEASE gstaudio-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-audio-1.0_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gst-plugins-base::gstreamer-app-1.0 VARIABLES ############################################

set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_INCLUDE_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIB_DIRS_RELEASE "${gst-plugins-base_PACKAGE_FOLDER_RELEASE}/lib")
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_BIN_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIBRARY_TYPE_RELEASE STATIC)
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_IS_HOST_WINDOWS_RELEASE 0)
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_RES_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_OBJECTS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_COMPILE_DEFINITIONS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_COMPILE_OPTIONS_C_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_COMPILE_OPTIONS_CXX_RELEASE "")
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LIBS_RELEASE gstapp-1.0)
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_SYSTEM_LIBS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_FRAMEWORK_DIRS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_FRAMEWORKS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_DEPENDENCIES_RELEASE gstreamer::gstreamer glib2::glib2 orc::orc)
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_SHARED_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_EXE_LINK_FLAGS_RELEASE )
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_EXE_LINK_FLAGS_RELEASE}>
)
set(gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gst-plugins-base_gst-plugins-base_gstreamer-app-1.0_COMPILE_OPTIONS_C_RELEASE}>")