########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(glib2_COMPONENT_NAMES "")
if(DEFINED glib2_FIND_DEPENDENCY_NAMES)
  list(APPEND glib2_FIND_DEPENDENCY_NAMES pcre2 zlib)
  list(REMOVE_DUPLICATES glib2_FIND_DEPENDENCY_NAMES)
else()
  set(glib2_FIND_DEPENDENCY_NAMES pcre2 zlib)
endif()
set(pcre2_FIND_MODE "NO_MODULE")
set(zlib_FIND_MODE "NO_MODULE")

########### VARIABLES #######################################################################
#############################################################################################
set(glib2_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/glib22586c806033e5/p")
set(glib2_BUILD_MODULES_PATHS_RELEASE )


set(glib2_INCLUDE_DIRS_RELEASE "${glib2_PACKAGE_FOLDER_RELEASE}/include/glib-2.0"
			"${glib2_PACKAGE_FOLDER_RELEASE}/lib/glib-2.0/include")
set(glib2_RES_DIRS_RELEASE )
set(glib2_DEFINITIONS_RELEASE )
set(glib2_SHARED_LINK_FLAGS_RELEASE )
set(glib2_EXE_LINK_FLAGS_RELEASE )
set(glib2_OBJECTS_RELEASE )
set(glib2_COMPILE_DEFINITIONS_RELEASE )
set(glib2_COMPILE_OPTIONS_C_RELEASE )
set(glib2_COMPILE_OPTIONS_CXX_RELEASE )
set(glib2_LIB_DIRS_RELEASE "${glib2_PACKAGE_FOLDER_RELEASE}/lib")
set(glib2_BIN_DIRS_RELEASE )
set(glib2_LIBRARY_TYPE_RELEASE STATIC)
set(glib2_IS_HOST_WINDOWS_RELEASE 0)
set(glib2_LIBS_RELEASE glib-2.0 gobject-2.0 gio-2.0 gmodule-2.0 gthread-2.0 ffi intl)
set(glib2_SYSTEM_LIBS_RELEASE m pthread dl rt)
set(glib2_FRAMEWORK_DIRS_RELEASE )
set(glib2_FRAMEWORKS_RELEASE )
set(glib2_BUILD_DIRS_RELEASE )
set(glib2_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(glib2_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${glib2_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${glib2_COMPILE_OPTIONS_C_RELEASE}>")
set(glib2_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${glib2_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${glib2_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${glib2_EXE_LINK_FLAGS_RELEASE}>")


set(glib2_COMPONENTS_RELEASE )