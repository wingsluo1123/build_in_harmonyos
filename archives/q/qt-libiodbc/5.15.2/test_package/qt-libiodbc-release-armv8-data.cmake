########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

set(qt-libiodbc_COMPONENT_NAMES "")
if(DEFINED qt-libiodbc_FIND_DEPENDENCY_NAMES)
  list(APPEND qt-libiodbc_FIND_DEPENDENCY_NAMES qt5-qtbase libiodbc)
  list(REMOVE_DUPLICATES qt-libiodbc_FIND_DEPENDENCY_NAMES)
else()
  set(qt-libiodbc_FIND_DEPENDENCY_NAMES qt5-qtbase libiodbc)
endif()
set(qt5-qtbase_FIND_MODE "NO_MODULE")
set(libiodbc_FIND_MODE "NO_MODULE")

########### VARIABLES #######################################################################
#############################################################################################
set(qt-libiodbc_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/b/qt-li35d3f2ec06787/p")
set(qt-libiodbc_BUILD_MODULES_PATHS_RELEASE )


set(qt-libiodbc_INCLUDE_DIRS_RELEASE "${qt-libiodbc_PACKAGE_FOLDER_RELEASE}/include")
set(qt-libiodbc_RES_DIRS_RELEASE )
set(qt-libiodbc_DEFINITIONS_RELEASE )
set(qt-libiodbc_SHARED_LINK_FLAGS_RELEASE )
set(qt-libiodbc_EXE_LINK_FLAGS_RELEASE )
set(qt-libiodbc_OBJECTS_RELEASE )
set(qt-libiodbc_COMPILE_DEFINITIONS_RELEASE )
set(qt-libiodbc_COMPILE_OPTIONS_C_RELEASE )
set(qt-libiodbc_COMPILE_OPTIONS_CXX_RELEASE )
set(qt-libiodbc_LIB_DIRS_RELEASE "${qt-libiodbc_PACKAGE_FOLDER_RELEASE}/lib")
set(qt-libiodbc_BIN_DIRS_RELEASE "${qt-libiodbc_PACKAGE_FOLDER_RELEASE}/bin")
set(qt-libiodbc_LIBRARY_TYPE_RELEASE SHARED)
set(qt-libiodbc_IS_HOST_WINDOWS_RELEASE 0)
set(qt-libiodbc_LIBS_RELEASE qsqliodbc)
set(qt-libiodbc_SYSTEM_LIBS_RELEASE )
set(qt-libiodbc_FRAMEWORK_DIRS_RELEASE )
set(qt-libiodbc_FRAMEWORKS_RELEASE )
set(qt-libiodbc_BUILD_DIRS_RELEASE )
set(qt-libiodbc_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(qt-libiodbc_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${qt-libiodbc_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${qt-libiodbc_COMPILE_OPTIONS_C_RELEASE}>")
set(qt-libiodbc_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${qt-libiodbc_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${qt-libiodbc_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${qt-libiodbc_EXE_LINK_FLAGS_RELEASE}>")


set(qt-libiodbc_COMPONENTS_RELEASE )