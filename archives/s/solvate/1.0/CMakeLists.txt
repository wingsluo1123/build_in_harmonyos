cmake_minimum_required(VERSION 3.15)
project(solvate VERSION 1.0 LANGUAGES C)

if(NOT DEFINED SOLVATE_SOURCE_DIR)
    message(FATAL_ERROR "SOLVATE_SOURCE_DIR must name the fixed upstream source")
endif()
add_executable(solvate "${SOLVATE_SOURCE_DIR}/solvate.c")
target_compile_options(solvate PRIVATE -O2)
target_link_libraries(solvate PRIVATE m)
install(TARGETS solvate RUNTIME DESTINATION bin)
install(FILES
    "${SOLVATE_SOURCE_DIR}/bpti.pdb" "${SOLVATE_SOURCE_DIR}/bpti.psf"
    "${SOLVATE_SOURCE_DIR}/globh.pdb" "${SOLVATE_SOURCE_DIR}/globh.psf"
    DESTINATION share/solvate)
install(FILES "${SOLVATE_SOURCE_DIR}/docu_html/node8.html"
    DESTINATION licenses RENAME solvate-license.html)
