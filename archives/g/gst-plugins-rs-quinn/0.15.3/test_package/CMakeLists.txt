cmake_minimum_required(VERSION 3.15)
project(test_gst-plugins-rs-quinn C)

# ELF symbol table verification test: parses the packaged .so ELF structure
# directly (Elf64 header / section headers / .dynsym / .dynstr), no
# dlopen/dlsym needed due to OHOS ldso namespace limitation (E186).
add_executable(test_gst-plugins-rs-quinn test.c)
target_link_libraries(test_gst-plugins-rs-quinn ${CMAKE_DL_LIBS})

# 插件 .so 路径由 test_package/conanfile.py 在 test() 阶段传入并直接运行，
# 这里不注册 ctest（避免 add_test 参数与运行方式不一致）。
