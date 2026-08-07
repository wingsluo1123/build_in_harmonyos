########### AGGREGATED COMPONENTS AND DEPENDENCIES FOR THE MULTI CONFIG #####################
#############################################################################################

list(APPEND qt5-qtbase_COMPONENT_NAMES Qt5::Core Qt5::Network Qt5::Gui Qt5::Test Qt5::Concurrent)
list(REMOVE_DUPLICATES qt5-qtbase_COMPONENT_NAMES)
if(DEFINED qt5-qtbase_FIND_DEPENDENCY_NAMES)
  list(APPEND qt5-qtbase_FIND_DEPENDENCY_NAMES )
  list(REMOVE_DUPLICATES qt5-qtbase_FIND_DEPENDENCY_NAMES)
else()
  set(qt5-qtbase_FIND_DEPENDENCY_NAMES )
endif()

########### VARIABLES #######################################################################
#############################################################################################
set(qt5-qtbase_PACKAGE_FOLDER_RELEASE "/storage/Users/currentUser/.conan2/p/qt5-q828d2380abd85/p")
set(qt5-qtbase_BUILD_MODULES_PATHS_RELEASE )


set(qt5-qtbase_INCLUDE_DIRS_RELEASE )
set(qt5-qtbase_RES_DIRS_RELEASE )
set(qt5-qtbase_DEFINITIONS_RELEASE )
set(qt5-qtbase_SHARED_LINK_FLAGS_RELEASE )
set(qt5-qtbase_EXE_LINK_FLAGS_RELEASE )
set(qt5-qtbase_OBJECTS_RELEASE )
set(qt5-qtbase_COMPILE_DEFINITIONS_RELEASE )
set(qt5-qtbase_COMPILE_OPTIONS_C_RELEASE )
set(qt5-qtbase_COMPILE_OPTIONS_CXX_RELEASE )
set(qt5-qtbase_LIB_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/lib")
set(qt5-qtbase_BIN_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/bin")
set(qt5-qtbase_LIBRARY_TYPE_RELEASE SHARED)
set(qt5-qtbase_IS_HOST_WINDOWS_RELEASE 0)
set(qt5-qtbase_LIBS_RELEASE )
set(qt5-qtbase_SYSTEM_LIBS_RELEASE EGL GLESv2)
set(qt5-qtbase_FRAMEWORK_DIRS_RELEASE )
set(qt5-qtbase_FRAMEWORKS_RELEASE )
set(qt5-qtbase_BUILD_DIRS_RELEASE )
set(qt5-qtbase_NO_SONAME_MODE_RELEASE FALSE)


# COMPOUND VARIABLES
set(qt5-qtbase_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${qt5-qtbase_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${qt5-qtbase_COMPILE_OPTIONS_C_RELEASE}>")
set(qt5-qtbase_LINKER_FLAGS_RELEASE
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${qt5-qtbase_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${qt5-qtbase_SHARED_LINK_FLAGS_RELEASE}>"
    "$<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${qt5-qtbase_EXE_LINK_FLAGS_RELEASE}>")


set(qt5-qtbase_COMPONENTS_RELEASE Qt5::Core Qt5::Network Qt5::Gui Qt5::Test Qt5::Concurrent)
########### COMPONENT Qt5::Concurrent VARIABLES ############################################

set(qt5-qtbase_Qt5_Concurrent_INCLUDE_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_LIB_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/lib")
set(qt5-qtbase_Qt5_Concurrent_BIN_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/bin")
set(qt5-qtbase_Qt5_Concurrent_LIBRARY_TYPE_RELEASE SHARED)
set(qt5-qtbase_Qt5_Concurrent_IS_HOST_WINDOWS_RELEASE 0)
set(qt5-qtbase_Qt5_Concurrent_RES_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_OBJECTS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_COMPILE_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_COMPILE_OPTIONS_C_RELEASE "")
set(qt5-qtbase_Qt5_Concurrent_COMPILE_OPTIONS_CXX_RELEASE "")
set(qt5-qtbase_Qt5_Concurrent_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_SYSTEM_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_FRAMEWORK_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_FRAMEWORKS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_DEPENDENCIES_RELEASE Qt5::Core)
set(qt5-qtbase_Qt5_Concurrent_SHARED_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_EXE_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Concurrent_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(qt5-qtbase_Qt5_Concurrent_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${qt5-qtbase_Qt5_Concurrent_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${qt5-qtbase_Qt5_Concurrent_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${qt5-qtbase_Qt5_Concurrent_EXE_LINK_FLAGS_RELEASE}>
)
set(qt5-qtbase_Qt5_Concurrent_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${qt5-qtbase_Qt5_Concurrent_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${qt5-qtbase_Qt5_Concurrent_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT Qt5::Test VARIABLES ############################################

set(qt5-qtbase_Qt5_Test_INCLUDE_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Test_LIB_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/lib")
set(qt5-qtbase_Qt5_Test_BIN_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/bin")
set(qt5-qtbase_Qt5_Test_LIBRARY_TYPE_RELEASE SHARED)
set(qt5-qtbase_Qt5_Test_IS_HOST_WINDOWS_RELEASE 0)
set(qt5-qtbase_Qt5_Test_RES_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Test_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Test_OBJECTS_RELEASE )
set(qt5-qtbase_Qt5_Test_COMPILE_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Test_COMPILE_OPTIONS_C_RELEASE "")
set(qt5-qtbase_Qt5_Test_COMPILE_OPTIONS_CXX_RELEASE "")
set(qt5-qtbase_Qt5_Test_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Test_SYSTEM_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Test_FRAMEWORK_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Test_FRAMEWORKS_RELEASE )
set(qt5-qtbase_Qt5_Test_DEPENDENCIES_RELEASE Qt5::Core)
set(qt5-qtbase_Qt5_Test_SHARED_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Test_EXE_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Test_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(qt5-qtbase_Qt5_Test_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${qt5-qtbase_Qt5_Test_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${qt5-qtbase_Qt5_Test_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${qt5-qtbase_Qt5_Test_EXE_LINK_FLAGS_RELEASE}>
)
set(qt5-qtbase_Qt5_Test_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${qt5-qtbase_Qt5_Test_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${qt5-qtbase_Qt5_Test_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT Qt5::Gui VARIABLES ############################################

set(qt5-qtbase_Qt5_Gui_INCLUDE_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Gui_LIB_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/lib")
set(qt5-qtbase_Qt5_Gui_BIN_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/bin")
set(qt5-qtbase_Qt5_Gui_LIBRARY_TYPE_RELEASE SHARED)
set(qt5-qtbase_Qt5_Gui_IS_HOST_WINDOWS_RELEASE 0)
set(qt5-qtbase_Qt5_Gui_RES_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Gui_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Gui_OBJECTS_RELEASE )
set(qt5-qtbase_Qt5_Gui_COMPILE_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Gui_COMPILE_OPTIONS_C_RELEASE "")
set(qt5-qtbase_Qt5_Gui_COMPILE_OPTIONS_CXX_RELEASE "")
set(qt5-qtbase_Qt5_Gui_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Gui_SYSTEM_LIBS_RELEASE EGL GLESv2)
set(qt5-qtbase_Qt5_Gui_FRAMEWORK_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Gui_FRAMEWORKS_RELEASE )
set(qt5-qtbase_Qt5_Gui_DEPENDENCIES_RELEASE Qt5::Core)
set(qt5-qtbase_Qt5_Gui_SHARED_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Gui_EXE_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Gui_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(qt5-qtbase_Qt5_Gui_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${qt5-qtbase_Qt5_Gui_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${qt5-qtbase_Qt5_Gui_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${qt5-qtbase_Qt5_Gui_EXE_LINK_FLAGS_RELEASE}>
)
set(qt5-qtbase_Qt5_Gui_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${qt5-qtbase_Qt5_Gui_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${qt5-qtbase_Qt5_Gui_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT Qt5::Network VARIABLES ############################################

set(qt5-qtbase_Qt5_Network_INCLUDE_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Network_LIB_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/lib")
set(qt5-qtbase_Qt5_Network_BIN_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/bin")
set(qt5-qtbase_Qt5_Network_LIBRARY_TYPE_RELEASE SHARED)
set(qt5-qtbase_Qt5_Network_IS_HOST_WINDOWS_RELEASE 0)
set(qt5-qtbase_Qt5_Network_RES_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Network_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Network_OBJECTS_RELEASE )
set(qt5-qtbase_Qt5_Network_COMPILE_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Network_COMPILE_OPTIONS_C_RELEASE "")
set(qt5-qtbase_Qt5_Network_COMPILE_OPTIONS_CXX_RELEASE "")
set(qt5-qtbase_Qt5_Network_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Network_SYSTEM_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Network_FRAMEWORK_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Network_FRAMEWORKS_RELEASE )
set(qt5-qtbase_Qt5_Network_DEPENDENCIES_RELEASE Qt5::Core)
set(qt5-qtbase_Qt5_Network_SHARED_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Network_EXE_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Network_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(qt5-qtbase_Qt5_Network_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${qt5-qtbase_Qt5_Network_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${qt5-qtbase_Qt5_Network_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${qt5-qtbase_Qt5_Network_EXE_LINK_FLAGS_RELEASE}>
)
set(qt5-qtbase_Qt5_Network_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${qt5-qtbase_Qt5_Network_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${qt5-qtbase_Qt5_Network_COMPILE_OPTIONS_C_RELEASE}>")
########### COMPONENT Qt5::Core VARIABLES ############################################

set(qt5-qtbase_Qt5_Core_INCLUDE_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Core_LIB_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/lib")
set(qt5-qtbase_Qt5_Core_BIN_DIRS_RELEASE "${qt5-qtbase_PACKAGE_FOLDER_RELEASE}/bin")
set(qt5-qtbase_Qt5_Core_LIBRARY_TYPE_RELEASE SHARED)
set(qt5-qtbase_Qt5_Core_IS_HOST_WINDOWS_RELEASE 0)
set(qt5-qtbase_Qt5_Core_RES_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Core_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Core_OBJECTS_RELEASE )
set(qt5-qtbase_Qt5_Core_COMPILE_DEFINITIONS_RELEASE )
set(qt5-qtbase_Qt5_Core_COMPILE_OPTIONS_C_RELEASE "")
set(qt5-qtbase_Qt5_Core_COMPILE_OPTIONS_CXX_RELEASE "")
set(qt5-qtbase_Qt5_Core_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Core_SYSTEM_LIBS_RELEASE )
set(qt5-qtbase_Qt5_Core_FRAMEWORK_DIRS_RELEASE )
set(qt5-qtbase_Qt5_Core_FRAMEWORKS_RELEASE )
set(qt5-qtbase_Qt5_Core_DEPENDENCIES_RELEASE )
set(qt5-qtbase_Qt5_Core_SHARED_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Core_EXE_LINK_FLAGS_RELEASE )
set(qt5-qtbase_Qt5_Core_NO_SONAME_MODE_RELEASE FALSE)

# COMPOUND VARIABLES
set(qt5-qtbase_Qt5_Core_LINKER_FLAGS_RELEASE
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,SHARED_LIBRARY>:${qt5-qtbase_Qt5_Core_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,MODULE_LIBRARY>:${qt5-qtbase_Qt5_Core_SHARED_LINK_FLAGS_RELEASE}>
        $<$<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>:${qt5-qtbase_Qt5_Core_EXE_LINK_FLAGS_RELEASE}>
)
set(qt5-qtbase_Qt5_Core_COMPILE_OPTIONS_RELEASE
    "$<$<COMPILE_LANGUAGE:CXX>:${qt5-qtbase_Qt5_Core_COMPILE_OPTIONS_CXX_RELEASE}>"
    "$<$<COMPILE_LANGUAGE:C>:${qt5-qtbase_Qt5_Core_COMPILE_OPTIONS_C_RELEASE}>")