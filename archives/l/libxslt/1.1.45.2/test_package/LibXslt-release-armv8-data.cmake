########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(libxslt_COMPONENT_NAMES "")
if(DEFINED libxslt_FIND_DEPENDENCY_NAMES)
  list(APPEND libxslt_FIND_DEPENDENCY_NAMES LibXml2)
  list(REMOVE_DUPLICATES libxslt_FIND_DEPENDENCY_NAMES)
else()
  set(libxslt_FIND_DEPENDENCY_NAMES LibXml2)
endif()
set(LibXml2_FIND_MODE "NO_MODULE")

########### VARIABLES #######################################################################
#############################################################################################
set(libxslt_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/libxsbfaa612a30abb/p")
set(libxslt_BUILD_MODULES_PATHS_RELEASE )


set(libxslt_INCLUDE_DIRS_RELEASE "${libxslt_PACKAGE_FOLDER_RELEASE}/include")
set(libxslt_RES_DIRS_RELEASE )
set(libxslt_DEFINITIONS_RELEASE )
set(libxslt_SHARED_LINK_FLAGS_RELEASE )
set(libxslt_EXE_LINK_FLAGS_RELEASE )
set(libxslt_OBJECTS_RELEASE )
set(libxslt_COMPILE_DEFINITIONS_RELEASE )
set(libxslt_COMPILE_OPTIONS_C_RELEASE )
set(libxslt_COMPILE_OPTIONS_CXX_RELEASE )
set(libxslt_LIB_DIRS_RELEASE "${libxslt_PACKAGE_FOLDER_RELEASE}/lib")
set(libxslt_BIN_DIRS_RELEASE )
set(libxslt_LIBRARY_TYPE_RELEASE STATIC)
set(libxslt_IS_HOST_WINDOWS_RELEASE 0)
set(libxslt_LIBS_RELEASE exslt xslt)
set(libxslt_SYSTEM_LIBS_RELEASE m)
set(libxslt_FRAMEWORK_DIRS_RELEASE )
set(libxslt_FRAMEWORKS_RELEASE )
set(libxslt_BUILD_DIRS_RELEASE )
set(libxslt_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(libxslt_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${libxslt_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${libxslt_COMPILE_OPTIONS_C_RELEASE}>")
set(libxslt_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${libxslt_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${libxslt_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${libxslt_EXE_LINK_FLAGS_RELEASE}>")


set(libxslt_COMPONENTS_RELEASE )