########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(opencore-amrnb_COMPONENT_NAMES "")
if(DEFINED opencore-amrnb_FIND_DEPENDENCY_NAMES)
  list(APPEND opencore-amrnb_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES opencore-amrnb_FIND_DEPENDENCY_NAMES)
else()
  set(opencore-amrnb_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(opencore-amrnb_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/openc6c611d0ca26df/p")
set(opencore-amrnb_BUILD_MODULES_PATHS_RELEASE )


set(opencore-amrnb_INCLUDE_DIRS_RELEASE "${opencore-amrnb_PACKAGE_FOLDER_RELEASE}/include")
set(opencore-amrnb_RES_DIRS_RELEASE )
set(opencore-amrnb_DEFINITIONS_RELEASE )
set(opencore-amrnb_SHARED_LINK_FLAGS_RELEASE )
set(opencore-amrnb_EXE_LINK_FLAGS_RELEASE )
set(opencore-amrnb_OBJECTS_RELEASE )
set(opencore-amrnb_COMPILE_DEFINITIONS_RELEASE )
set(opencore-amrnb_COMPILE_OPTIONS_C_RELEASE )
set(opencore-amrnb_COMPILE_OPTIONS_CXX_RELEASE )
set(opencore-amrnb_LIB_DIRS_RELEASE "${opencore-amrnb_PACKAGE_FOLDER_RELEASE}/lib")
set(opencore-amrnb_BIN_DIRS_RELEASE )
set(opencore-amrnb_LIBRARY_TYPE_RELEASE STATIC)
set(opencore-amrnb_IS_HOST_WINDOWS_RELEASE 0)
set(opencore-amrnb_LIBS_RELEASE opencore-amrnb)
set(opencore-amrnb_SYSTEM_LIBS_RELEASE m)
set(opencore-amrnb_FRAMEWORK_DIRS_RELEASE )
set(opencore-amrnb_FRAMEWORKS_RELEASE )
set(opencore-amrnb_BUILD_DIRS_RELEASE )
set(opencore-amrnb_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(opencore-amrnb_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${opencore-amrnb_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${opencore-amrnb_COMPILE_OPTIONS_C_RELEASE}>")
set(opencore-amrnb_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${opencore-amrnb_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${opencore-amrnb_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${opencore-amrnb_EXE_LINK_FLAGS_RELEASE}>")


set(opencore-amrnb_COMPONENTS_RELEASE )