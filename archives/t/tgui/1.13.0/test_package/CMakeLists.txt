cmake_minimum_required(VERSION 3.15)
project(TguiTest CXX)

find_package(TGUI REQUIRED CONFIG)

add_executable(test_tgui test_package.cpp)
target_link_libraries(test_tgui PRIVATE TGUI::TGUI freetype)
target_compile_features(test_tgui PRIVATE cxx_std_17)
