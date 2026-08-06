########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(orc_COMPONENT_NAMES "")
if(DEFINED orc_FIND_DEPENDENCY_NAMES)
  list(APPEND orc_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES orc_FIND_DEPENDENCY_NAMES)
else()
  set(orc_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(orc_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/orcd61cf337cf9a8/p")
set(orc_BUILD_MODULES_PATHS_RELEASE )


set(orc_INCLUDE_DIRS_RELEASE "${orc_PACKAGE_FOLDER_RELEASE}/include/orc-0.4")
set(orc_RES_DIRS_RELEASE )
set(orc_DEFINITIONS_RELEASE )
set(orc_SHARED_LINK_FLAGS_RELEASE )
set(orc_EXE_LINK_FLAGS_RELEASE )
set(orc_OBJECTS_RELEASE )
set(orc_COMPILE_DEFINITIONS_RELEASE )
set(orc_COMPILE_OPTIONS_C_RELEASE )
set(orc_COMPILE_OPTIONS_CXX_RELEASE )
set(orc_LIB_DIRS_RELEASE "${orc_PACKAGE_FOLDER_RELEASE}/lib")
set(orc_BIN_DIRS_RELEASE )
set(orc_LIBRARY_TYPE_RELEASE STATIC)
set(orc_IS_HOST_WINDOWS_RELEASE 0)
set(orc_LIBS_RELEASE orc-0.4 orc-test-0.4)
set(orc_SYSTEM_LIBS_RELEASE )
set(orc_FRAMEWORK_DIRS_RELEASE )
set(orc_FRAMEWORKS_RELEASE )
set(orc_BUILD_DIRS_RELEASE )
set(orc_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(orc_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${orc_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${orc_COMPILE_OPTIONS_C_RELEASE}>")
set(orc_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${orc_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${orc_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${orc_EXE_LINK_FLAGS_RELEASE}>")


set(orc_COMPONENTS_RELEASE )