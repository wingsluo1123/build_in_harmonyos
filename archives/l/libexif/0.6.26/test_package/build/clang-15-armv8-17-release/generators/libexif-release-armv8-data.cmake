########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(libexif_COMPONENT_NAMES "")
if(DEFINED libexif_FIND_DEPENDENCY_NAMES)
  list(APPEND libexif_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES libexif_FIND_DEPENDENCY_NAMES)
else()
  set(libexif_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(libexif_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/libex28758d2420962/p")
set(libexif_BUILD_MODULES_PATHS_RELEASE )


set(libexif_INCLUDE_DIRS_RELEASE "${libexif_PACKAGE_FOLDER_RELEASE}/include")
set(libexif_RES_DIRS_RELEASE )
set(libexif_DEFINITIONS_RELEASE )
set(libexif_SHARED_LINK_FLAGS_RELEASE )
set(libexif_EXE_LINK_FLAGS_RELEASE )
set(libexif_OBJECTS_RELEASE )
set(libexif_COMPILE_DEFINITIONS_RELEASE )
set(libexif_COMPILE_OPTIONS_C_RELEASE )
set(libexif_COMPILE_OPTIONS_CXX_RELEASE )
set(libexif_LIB_DIRS_RELEASE "${libexif_PACKAGE_FOLDER_RELEASE}/lib")
set(libexif_BIN_DIRS_RELEASE )
set(libexif_LIBRARY_TYPE_RELEASE STATIC)
set(libexif_IS_HOST_WINDOWS_RELEASE 0)
set(libexif_LIBS_RELEASE exif)
set(libexif_SYSTEM_LIBS_RELEASE )
set(libexif_FRAMEWORK_DIRS_RELEASE )
set(libexif_FRAMEWORKS_RELEASE )
set(libexif_BUILD_DIRS_RELEASE )
set(libexif_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(libexif_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${libexif_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${libexif_COMPILE_OPTIONS_C_RELEASE}>")
set(libexif_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${libexif_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${libexif_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${libexif_EXE_LINK_FLAGS_RELEASE}>")


set(libexif_COMPONENTS_RELEASE )