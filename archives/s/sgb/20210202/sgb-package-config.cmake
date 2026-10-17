# Independent installed-package config; not part of Stanford GraphBase.
get_filename_component(_sgb_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
if(NOT EXISTS "${_sgb_prefix}/lib/libgb.a" OR
   NOT EXISTS "${_sgb_prefix}/include/gb_graph.h")
    message(FATAL_ERROR "The installed SGB library or public headers are missing")
endif()
if(NOT TARGET sgb::sgb)
    add_library(sgb::sgb STATIC IMPORTED)
    set_target_properties(sgb::sgb PROPERTIES
        IMPORTED_LOCATION "${_sgb_prefix}/lib/libgb.a"
        INTERFACE_INCLUDE_DIRECTORIES "${_sgb_prefix}/include"
        INTERFACE_COMPILE_DEFINITIONS SYSV
        INTERFACE_LINK_LIBRARIES m)
endif()
unset(_sgb_prefix)
