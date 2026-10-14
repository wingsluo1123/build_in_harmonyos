cmake_minimum_required(VERSION 3.18)
project(TguiTest CXX)

find_package(TGUI REQUIRED CONFIG)

# freetype/2.14.3.1 的包元数据不完整（cpp_info.libs 为空），它生成的
# freetype::freetype 目标只带 -L 不带 -lfreetype，消费者链接 libtgui.so 时会报
# FT_* 未定义符号（OHOS 链接器默认 --no-allow-shlib-undefined）。
# 这里改用 CMake 内置的 FindFreetype（MODULE 模式）拿到标准 Freetype::Freetype
# 目标：Conan 已把依赖包 lib 目录放入 CMAKE_LIBRARY_PATH，因此解析到的正是制品
# 仓中的 freetype，无需硬编码 soname，也不用 NO_DEFAULT_PATH。
find_package(Freetype MODULE REQUIRED)

add_executable(test_tgui test_package.cpp)
target_link_libraries(test_tgui PRIVATE TGUI::TGUI Freetype::Freetype)
target_compile_features(test_tgui PRIVATE cxx_std_17)
