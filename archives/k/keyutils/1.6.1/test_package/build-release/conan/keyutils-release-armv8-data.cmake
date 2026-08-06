########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(keyutils_COMPONENT_NAMES "")
if(DEFINED keyutils_FIND_DEPENDENCY_NAMES)
  list(APPEND keyutils_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES keyutils_FIND_DEPENDENCY_NAMES)
else()
  set(keyutils_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(keyutils_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/keyut28d300bf743fc/p")
set(keyutils_BUILD_MODULES_PATHS_RELEASE )


set(keyutils_INCLUDE_DIRS_RELEASE "${keyutils_PACKAGE_FOLDER_RELEASE}/include")
set(keyutils_RES_DIRS_RELEASE )
set(keyutils_DEFINITIONS_RELEASE )
set(keyutils_SHARED_LINK_FLAGS_RELEASE )
set(keyutils_EXE_LINK_FLAGS_RELEASE )
set(keyutils_OBJECTS_RELEASE )
set(keyutils_COMPILE_DEFINITIONS_RELEASE )
set(keyutils_COMPILE_OPTIONS_C_RELEASE )
set(keyutils_COMPILE_OPTIONS_CXX_RELEASE )
set(keyutils_LIB_DIRS_RELEASE "${keyutils_PACKAGE_FOLDER_RELEASE}/lib")
set(keyutils_BIN_DIRS_RELEASE "${keyutils_PACKAGE_FOLDER_RELEASE}/bin")
set(keyutils_LIBRARY_TYPE_RELEASE SHARED)
set(keyutils_IS_HOST_WINDOWS_RELEASE 0)
set(keyutils_LIBS_RELEASE keyutils)
set(keyutils_SYSTEM_LIBS_RELEASE )
set(keyutils_FRAMEWORK_DIRS_RELEASE )
set(keyutils_FRAMEWORKS_RELEASE )
set(keyutils_BUILD_DIRS_RELEASE )
set(keyutils_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(keyutils_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${keyutils_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${keyutils_COMPILE_OPTIONS_C_RELEASE}>")
set(keyutils_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${keyutils_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${keyutils_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${keyutils_EXE_LINK_FLAGS_RELEASE}>")


set(keyutils_COMPONENTS_RELEASE )