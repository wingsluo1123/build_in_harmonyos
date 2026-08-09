cmake_minimum_required(VERSION 3.15)
project(test_zathura_pdf_mupdf C)

# This test verifies the plugin .so can be loaded via dlopen and
# the zathura_plugin_67 definition symbol exists (API=6, ABI=7).
enable_testing()
add_executable(test_zathura_pdf_mupdf test.c)
target_link_libraries(test_zathura_pdf_mupdf ${CMAKE_DL_LIBS})

add_test(NAME test_zathura_pdf_mupdf
         COMMAND test_zathura_pdf_mupdf
         WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
