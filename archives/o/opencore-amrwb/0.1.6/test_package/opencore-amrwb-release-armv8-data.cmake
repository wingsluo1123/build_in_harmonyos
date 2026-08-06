########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(opencore-amrwb_COMPONENT_NAMES "")
if(DEFINED opencore-amrwb_FIND_DEPENDENCY_NAMES)
  list(APPEND opencore-amrwb_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES opencore-amrwb_FIND_DEPENDENCY_NAMES)
else()
  set(opencore-amrwb_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(opencore-amrwb_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/openc3bc4914132166/p")
set(opencore-amrwb_BUILD_MODULES_PATHS_RELEASE )


set(opencore-amrwb_INCLUDE_DIRS_RELEASE "${opencore-amrwb_PACKAGE_FOLDER_RELEASE}/include")
set(opencore-amrwb_RES_DIRS_RELEASE )
set(opencore-amrwb_DEFINITIONS_RELEASE )
set(opencore-amrwb_SHARED_LINK_FLAGS_RELEASE )
set(opencore-amrwb_EXE_LINK_FLAGS_RELEASE )
set(opencore-amrwb_OBJECTS_RELEASE )
set(opencore-amrwb_COMPILE_DEFINITIONS_RELEASE )
set(opencore-amrwb_COMPILE_OPTIONS_C_RELEASE )
set(opencore-amrwb_COMPILE_OPTIONS_CXX_RELEASE )
set(opencore-amrwb_LIB_DIRS_RELEASE "${opencore-amrwb_PACKAGE_FOLDER_RELEASE}/lib")
set(opencore-amrwb_BIN_DIRS_RELEASE )
set(opencore-amrwb_LIBRARY_TYPE_RELEASE UNKNOWN)
set(opencore-amrwb_IS_HOST_WINDOWS_RELEASE 0)
set(opencore-amrwb_LIBS_RELEASE opencore-amrwb)
set(opencore-amrwb_SYSTEM_LIBS_RELEASE )
set(opencore-amrwb_FRAMEWORK_DIRS_RELEASE )
set(opencore-amrwb_FRAMEWORKS_RELEASE )
set(opencore-amrwb_BUILD_DIRS_RELEASE )
set(opencore-amrwb_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(opencore-amrwb_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${opencore-amrwb_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${opencore-amrwb_COMPILE_OPTIONS_C_RELEASE}>")
set(opencore-amrwb_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${opencore-amrwb_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${opencore-amrwb_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${opencore-amrwb_EXE_LINK_FLAGS_RELEASE}>")


set(opencore-amrwb_COMPONENTS_RELEASE )