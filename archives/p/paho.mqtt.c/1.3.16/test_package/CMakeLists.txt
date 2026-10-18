cmake_minimum_required(VERSION 3.12)
project(test_paho_mqtt_c C)

option(PAHO_TEST_WITH_SSL "Exercise Paho SSL/TLS transport" OFF)

find_package(paho.mqtt.c REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_paho_mqtt_c test_harmonyos_mqtt.c)
add_library(paho_shared_link_probe SHARED test_harmonyos_mqtt.c)

foreach(target test_paho_mqtt_c paho_shared_link_probe)
    target_link_libraries(${target} PRIVATE
        paho.mqtt.c::paho.mqtt.c
        Threads::Threads
    )

    if(PAHO_TEST_WITH_SSL)
        target_compile_definitions(${target} PRIVATE PAHO_TEST_WITH_SSL=1)
        target_include_directories(${target} PRIVATE "${PAHO_OPENSSL_INCLUDE_DIR}")
        target_link_libraries(${target} PRIVATE openssl::openssl)
    endif()
endforeach()
