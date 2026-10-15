cmake_minimum_required(VERSION 3.15)
project(test_wxgtk3 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(wxwidgets-gtk3 CONFIG REQUIRED)
find_package(glib CONFIG REQUIRED)

add_executable(test_wxgtk3 test_wxgtk3.cpp)
target_link_libraries(test_wxgtk3 PRIVATE wxwidgets-gtk3::wxwidgets-gtk3)

add_executable(test_wxgtk3_gui test_wxgtk3_gui.cpp)
target_link_libraries(test_wxgtk3_gui PRIVATE wxwidgets-gtk3::wxwidgets-gtk3 GLib::GLib)

if(WX_TEST_SHARED)
    add_library(wx_state_bridge SHARED wx_state_bridge.cpp)
    target_link_libraries(wx_state_bridge PRIVATE wxwidgets-gtk3::wxwidgets-gtk3)
    add_executable(test_wx_app_state test_wx_app_state.cpp)
    target_link_libraries(test_wx_app_state PRIVATE wx_state_bridge wxwidgets-gtk3::wxwidgets-gtk3)
    if(UNIX OR CMAKE_SYSTEM_NAME MATCHES "^(OHOS|HarmonyOS)$")
        # OHOS toolchains do not supply an automatic build-tree RUNPATH.
        target_link_options(test_wx_app_state PRIVATE
            "LINKER:-rpath,$<TARGET_FILE_DIR:wx_state_bridge>")
    endif()
endif()
