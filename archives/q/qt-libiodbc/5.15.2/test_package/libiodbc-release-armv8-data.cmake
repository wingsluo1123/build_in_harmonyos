########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(libiodbc_COMPONENT_NAMES "")
if(DEFINED libiodbc_FIND_DEPENDENCY_NAMES)
  list(APPEND libiodbc_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES libiodbc_FIND_DEPENDENCY_NAMES)
else()
  set(libiodbc_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(libiodbc_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/libiof05d4868d6380/p")
set(libiodbc_BUILD_MODULES_PATHS_RELEASE )


set(libiodbc_INCLUDE_DIRS_RELEASE )
set(libiodbc_RES_DIRS_RELEASE )
set(libiodbc_DEFINITIONS_RELEASE )
set(libiodbc_SHARED_LINK_FLAGS_RELEASE )
set(libiodbc_EXE_LINK_FLAGS_RELEASE )
set(libiodbc_OBJECTS_RELEASE )
set(libiodbc_COMPILE_DEFINITIONS_RELEASE )
set(libiodbc_COMPILE_OPTIONS_C_RELEASE )
set(libiodbc_COMPILE_OPTIONS_CXX_RELEASE )
set(libiodbc_LIB_DIRS_RELEASE "${libiodbc_PACKAGE_FOLDER_RELEASE}/lib")
set(libiodbc_BIN_DIRS_RELEASE "${libiodbc_PACKAGE_FOLDER_RELEASE}/bin")
set(libiodbc_LIBRARY_TYPE_RELEASE SHARED)
set(libiodbc_IS_HOST_WINDOWS_RELEASE 0)
set(libiodbc_LIBS_RELEASE )
set(libiodbc_SYSTEM_LIBS_RELEASE )
set(libiodbc_FRAMEWORK_DIRS_RELEASE )
set(libiodbc_FRAMEWORKS_RELEASE )
set(libiodbc_BUILD_DIRS_RELEASE )
set(libiodbc_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(libiodbc_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${libiodbc_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${libiodbc_COMPILE_OPTIONS_C_RELEASE}>")
set(libiodbc_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${libiodbc_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${libiodbc_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${libiodbc_EXE_LINK_FLAGS_RELEASE}>")


set(libiodbc_COMPONENTS_RELEASE )