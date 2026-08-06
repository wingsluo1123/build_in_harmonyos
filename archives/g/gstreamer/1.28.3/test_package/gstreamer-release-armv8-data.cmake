########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

list(APPEND gstreamer_COMPONENT_NAMES gstreamer::gstreamer gstreamer::base gstreamer::controller gstreamer::net)
list(REMOVE_DUPLICATES gstreamer_COMPONENT_NAMES)
if(DEFINED gstreamer_FIND_DEPENDENCY_NAMES)
  list(APPEND gstreamer_FIND_DEPENDENCY_NAMES orc glib2)
  list(REMOVE_DUPLICATES gstreamer_FIND_DEPENDENCY_NAMES)
else()
  set(gstreamer_FIND_DEPENDENCY_NAMES orc glib2)
endif()
set(orc_FIND_MODE "NO_MODULE")
set(glib2_FIND_MODE "NO_MODULE")

########### VARIABLES #######################################################################
#############################################################################################
set(gstreamer_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/gstrea0a182c512219/p")
set(gstreamer_BUILD_MODULES_PATHS_RELEASE )


set(gstreamer_INCLUDE_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gstreamer_RES_DIRS_RELEASE )
set(gstreamer_DEFINITIONS_RELEASE )
set(gstreamer_SHARED_LINK_FLAGS_RELEASE )
set(gstreamer_EXE_LINK_FLAGS_RELEASE )
set(gstreamer_OBJECTS_RELEASE )
set(gstreamer_COMPILE_DEFINITIONS_RELEASE )
set(gstreamer_COMPILE_OPTIONS_C_RELEASE )
set(gstreamer_COMPILE_OPTIONS_CXX_RELEASE )
set(gstreamer_LIB_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/lib")
set(gstreamer_BIN_DIRS_RELEASE )
set(gstreamer_LIBRARY_TYPE_RELEASE STATIC)
set(gstreamer_IS_HOST_WINDOWS_RELEASE 0)
set(gstreamer_LIBS_RELEASE gstnet-1.0 gstcontroller-1.0 gstbase-1.0 gstreamer-1.0)
set(gstreamer_SYSTEM_LIBS_RELEASE )
set(gstreamer_FRAMEWORK_DIRS_RELEASE )
set(gstreamer_FRAMEWORKS_RELEASE )
set(gstreamer_BUILD_DIRS_RELEASE )
set(gstreamer_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(gstreamer_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gstreamer_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gstreamer_COMPILE_OPTIONS_C_RELEASE}>")
set(gstreamer_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gstreamer_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gstreamer_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gstreamer_EXE_LINK_FLAGS_RELEASE}>")


set(gstreamer_COMPONENTS_RELEASE gstreamer::gstreamer gstreamer::base gstreamer::controller gstreamer::net)
########### COMPONENT gstreamer::net VARIABLES ############################################

set(gstreamer_gstreamer_net_INCLUDE_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gstreamer_gstreamer_net_LIB_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/lib")
set(gstreamer_gstreamer_net_BIN_DIRS_RELEASE )
set(gstreamer_gstreamer_net_LIBRARY_TYPE_RELEASE STATIC)
set(gstreamer_gstreamer_net_IS_HOST_WINDOWS_RELEASE 0)
set(gstreamer_gstreamer_net_RES_DIRS_RELEASE )
set(gstreamer_gstreamer_net_DEFINITIONS_RELEASE )
set(gstreamer_gstreamer_net_OBJECTS_RELEASE )
set(gstreamer_gstreamer_net_COMPILE_DEFINITIONS_RELEASE )
set(gstreamer_gstreamer_net_COMPILE_OPTIONS_C_RELEASE "")
set(gstreamer_gstreamer_net_COMPILE_OPTIONS_CXX_RELEASE "")
set(gstreamer_gstreamer_net_LIBS_RELEASE gstnet-1.0)
set(gstreamer_gstreamer_net_SYSTEM_LIBS_RELEASE )
set(gstreamer_gstreamer_net_FRAMEWORK_DIRS_RELEASE )
set(gstreamer_gstreamer_net_FRAMEWORKS_RELEASE )
set(gstreamer_gstreamer_net_DEPENDENCIES_RELEASE gstreamer::gstreamer)
set(gstreamer_gstreamer_net_SHARED_LINK_FLAGS_RELEASE )
set(gstreamer_gstreamer_net_EXE_LINK_FLAGS_RELEASE )
set(gstreamer_gstreamer_net_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gstreamer_gstreamer_net_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gstreamer_gstreamer_net_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gstreamer_gstreamer_net_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gstreamer_gstreamer_net_EXE_LINK_FLAGS_RELEASE}>
)
set(gstreamer_gstreamer_net_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gstreamer_gstreamer_net_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gstreamer_gstreamer_net_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gstreamer::controller VARIABLES ############################################

set(gstreamer_gstreamer_controller_INCLUDE_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gstreamer_gstreamer_controller_LIB_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/lib")
set(gstreamer_gstreamer_controller_BIN_DIRS_RELEASE )
set(gstreamer_gstreamer_controller_LIBRARY_TYPE_RELEASE STATIC)
set(gstreamer_gstreamer_controller_IS_HOST_WINDOWS_RELEASE 0)
set(gstreamer_gstreamer_controller_RES_DIRS_RELEASE )
set(gstreamer_gstreamer_controller_DEFINITIONS_RELEASE )
set(gstreamer_gstreamer_controller_OBJECTS_RELEASE )
set(gstreamer_gstreamer_controller_COMPILE_DEFINITIONS_RELEASE )
set(gstreamer_gstreamer_controller_COMPILE_OPTIONS_C_RELEASE "")
set(gstreamer_gstreamer_controller_COMPILE_OPTIONS_CXX_RELEASE "")
set(gstreamer_gstreamer_controller_LIBS_RELEASE gstcontroller-1.0)
set(gstreamer_gstreamer_controller_SYSTEM_LIBS_RELEASE )
set(gstreamer_gstreamer_controller_FRAMEWORK_DIRS_RELEASE )
set(gstreamer_gstreamer_controller_FRAMEWORKS_RELEASE )
set(gstreamer_gstreamer_controller_DEPENDENCIES_RELEASE gstreamer::gstreamer)
set(gstreamer_gstreamer_controller_SHARED_LINK_FLAGS_RELEASE )
set(gstreamer_gstreamer_controller_EXE_LINK_FLAGS_RELEASE )
set(gstreamer_gstreamer_controller_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gstreamer_gstreamer_controller_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gstreamer_gstreamer_controller_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gstreamer_gstreamer_controller_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gstreamer_gstreamer_controller_EXE_LINK_FLAGS_RELEASE}>
)
set(gstreamer_gstreamer_controller_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gstreamer_gstreamer_controller_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gstreamer_gstreamer_controller_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gstreamer::base VARIABLES ############################################

set(gstreamer_gstreamer_base_INCLUDE_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gstreamer_gstreamer_base_LIB_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/lib")
set(gstreamer_gstreamer_base_BIN_DIRS_RELEASE )
set(gstreamer_gstreamer_base_LIBRARY_TYPE_RELEASE STATIC)
set(gstreamer_gstreamer_base_IS_HOST_WINDOWS_RELEASE 0)
set(gstreamer_gstreamer_base_RES_DIRS_RELEASE )
set(gstreamer_gstreamer_base_DEFINITIONS_RELEASE )
set(gstreamer_gstreamer_base_OBJECTS_RELEASE )
set(gstreamer_gstreamer_base_COMPILE_DEFINITIONS_RELEASE )
set(gstreamer_gstreamer_base_COMPILE_OPTIONS_C_RELEASE "")
set(gstreamer_gstreamer_base_COMPILE_OPTIONS_CXX_RELEASE "")
set(gstreamer_gstreamer_base_LIBS_RELEASE gstbase-1.0)
set(gstreamer_gstreamer_base_SYSTEM_LIBS_RELEASE )
set(gstreamer_gstreamer_base_FRAMEWORK_DIRS_RELEASE )
set(gstreamer_gstreamer_base_FRAMEWORKS_RELEASE )
set(gstreamer_gstreamer_base_DEPENDENCIES_RELEASE gstreamer::gstreamer)
set(gstreamer_gstreamer_base_SHARED_LINK_FLAGS_RELEASE )
set(gstreamer_gstreamer_base_EXE_LINK_FLAGS_RELEASE )
set(gstreamer_gstreamer_base_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gstreamer_gstreamer_base_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gstreamer_gstreamer_base_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gstreamer_gstreamer_base_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gstreamer_gstreamer_base_EXE_LINK_FLAGS_RELEASE}>
)
set(gstreamer_gstreamer_base_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gstreamer_gstreamer_base_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gstreamer_gstreamer_base_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT gstreamer::gstreamer VARIABLES ############################################

set(gstreamer_gstreamer_gstreamer_INCLUDE_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/include/gstreamer-1.0")
set(gstreamer_gstreamer_gstreamer_LIB_DIRS_RELEASE "${gstreamer_PACKAGE_FOLDER_RELEASE}/lib")
set(gstreamer_gstreamer_gstreamer_BIN_DIRS_RELEASE )
set(gstreamer_gstreamer_gstreamer_LIBRARY_TYPE_RELEASE STATIC)
set(gstreamer_gstreamer_gstreamer_IS_HOST_WINDOWS_RELEASE 0)
set(gstreamer_gstreamer_gstreamer_RES_DIRS_RELEASE )
set(gstreamer_gstreamer_gstreamer_DEFINITIONS_RELEASE )
set(gstreamer_gstreamer_gstreamer_OBJECTS_RELEASE )
set(gstreamer_gstreamer_gstreamer_COMPILE_DEFINITIONS_RELEASE )
set(gstreamer_gstreamer_gstreamer_COMPILE_OPTIONS_C_RELEASE "")
set(gstreamer_gstreamer_gstreamer_COMPILE_OPTIONS_CXX_RELEASE "")
set(gstreamer_gstreamer_gstreamer_LIBS_RELEASE gstreamer-1.0)
set(gstreamer_gstreamer_gstreamer_SYSTEM_LIBS_RELEASE )
set(gstreamer_gstreamer_gstreamer_FRAMEWORK_DIRS_RELEASE )
set(gstreamer_gstreamer_gstreamer_FRAMEWORKS_RELEASE )
set(gstreamer_gstreamer_gstreamer_DEPENDENCIES_RELEASE glib2::glib2 orc::orc)
set(gstreamer_gstreamer_gstreamer_SHARED_LINK_FLAGS_RELEASE )
set(gstreamer_gstreamer_gstreamer_EXE_LINK_FLAGS_RELEASE )
set(gstreamer_gstreamer_gstreamer_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(gstreamer_gstreamer_gstreamer_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${gstreamer_gstreamer_gstreamer_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${gstreamer_gstreamer_gstreamer_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${gstreamer_gstreamer_gstreamer_EXE_LINK_FLAGS_RELEASE}>
)
set(gstreamer_gstreamer_gstreamer_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${gstreamer_gstreamer_gstreamer_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${gstreamer_gstreamer_gstreamer_COMPILE_OPTIONS_C_RELEASE}>")