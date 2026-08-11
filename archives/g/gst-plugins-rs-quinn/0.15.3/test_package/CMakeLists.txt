cmake_minimum_required(VERSION 3.15)
project(test_gst-plugins-rs-quinn C)

# ELF symbol table verification test: parses the packaged .so ELF structure
# directly (Elf64 header / section headers / .dynsym / .dynstr), no
# dlopen/dlsym needed due to OHOS ldso namespace limitation (E186).
add_executable(test_gst-plugins-rs-quinn test.c)
target_link_libraries(test_gst-plugins-rs-quinn ${CMAKE_DL_LIBS})

# Plugin path is passed at runtime by test_package/conanfile.py
enable_testing()
add_test(NAME test_gst-plugins-rs-quinn
         COMMAND test_gst-plugins-rs-quinn "$<TARGET_FILE_DIR:test_gst-plugins-rs-quinn>")
