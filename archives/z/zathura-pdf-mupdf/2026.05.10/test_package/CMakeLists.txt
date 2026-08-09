cmake_minimum_required(VERSION 3.15)
project(test_zathura_pdf_mupdf C)

# This test verifies the plugin .so can be loaded and the plugin symbol exists.
# The plugin is a shared module loaded at runtime by zathura — we use dlopen
# to verify the ELF is valid and contains the expected plugin definition symbol.

enable_testing()
add_executable(test_zathura_pdf_mupdf test.c)
target_link_libraries(test_zathura_pdf_mupdf ${CMAKE_DL_LIBS})

# Find the plugin .so path from the conan package
add_test(NAME test_zathura_pdf_mupdf
         COMMAND test_zathura_pdf_mupdf
         WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
