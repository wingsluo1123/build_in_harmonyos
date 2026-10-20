cmake_minimum_required(VERSION 3.20)
project(test_pam_script C)

# linux-pam provides <security/pam_appl.h> and libpam; pam_script itself is a
# dlopen()ed module, so it is only located, never linked.
find_package(linux-pam REQUIRED)
find_package(pam_script REQUIRED)

add_executable(test_pam_script test_pam_script.c)
target_link_libraries(test_pam_script PRIVATE linux-pam::pam ${CMAKE_DL_LIBS})
target_compile_options(test_pam_script PRIVATE -Wall)
