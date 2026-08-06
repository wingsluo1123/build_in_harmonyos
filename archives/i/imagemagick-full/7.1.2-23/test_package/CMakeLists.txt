cmake_minimum_required(VERSION 3.15)
project(test_imagemagick_full C)

# Find ImageMagick via pkg-config (conan generates .pc files)
find_package(PkgConfig REQUIRED)
pkg_check_modules(MAGICKWAND REQUIRED IMPORTED_TARGET MagickWand-7.Q16HDRI)

add_executable(test_imagemagick_full test.c)
target_link_libraries(test_imagemagick_full PkgConfig::MAGICKWAND)

enable_testing()
add_test(NAME test_imagemagick_full COMMAND test_imagemagick_full)
