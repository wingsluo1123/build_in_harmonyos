cmake_minimum_required(VERSION 3.15)
project(modsecurity_apache_test C)

if(NOT DEFINED MODSEC_LIBDIR)
  message(FATAL_ERROR "MODSEC_LIBDIR is not set")
endif()
if(NOT DEFINED MODSEC_RESDIR)
  message(FATAL_ERROR "MODSEC_RESDIR is not set")
endif()

file(TO_CMAKE_PATH "${MODSEC_LIBDIR}" MODSEC_LIBDIR)
file(TO_CMAKE_PATH "${MODSEC_RESDIR}" MODSEC_RESDIR)

add_executable(modsec_module_load modsec_module_load.c)
target_compile_definitions(modsec_module_load PRIVATE
  MODSEC_MODULE_PATH="${MODSEC_LIBDIR}/mod_security2.so")

add_executable(modsec_conf_check modsec_conf_check.c)
target_compile_definitions(modsec_conf_check PRIVATE
  MODSEC_CONF_PATH="${MODSEC_RESDIR}/modsecurity.conf-recommended")
