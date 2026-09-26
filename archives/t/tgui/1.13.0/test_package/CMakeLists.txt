cmake_minimum_required(VERSION 3.15)
project(TguiTest CXX)

find_package(TGUI REQUIRED CONFIG)
find_package(freetype REQUIRED CONFIG)
find_library(FREETYPE_LIBRARY NAMES freetype libfreetype.so.6
             PATHS "${freetype_PACKAGE_FOLDER_RELEASE}/lib" NO_DEFAULT_PATH REQUIRED)

add_executable(test_tgui test_package.cpp)
target_link_libraries(test_tgui PRIVATE TGUI::TGUI "${FREETYPE_LIBRARY}")
target_compile_features(test_tgui PRIVATE cxx_std_17)
