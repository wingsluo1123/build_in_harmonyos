cmake_minimum_required(VERSION 3.15)
project(test_wavetral CXX)

if(NOT WAVETRAL_BIN)
    message(FATAL_ERROR "WAVETRAL_BIN must point at the packaged wavetral executable")
endif()
if(NOT EXISTS ${WAVETRAL_BIN})
    message(FATAL_ERROR "packaged wavetral is missing: ${WAVETRAL_BIN}")
endif()
if(NOT EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/fixtures/sine8.txt)
    message(FATAL_ERROR "sine8.txt fixture is missing")
endif()

add_executable(test_wavetral test_wavetral.cpp)
target_compile_features(test_wavetral PRIVATE cxx_std_11)
target_compile_definitions(test_wavetral PRIVATE
    WAVETRAL_BIN="${WAVETRAL_BIN}"
    SINE8_TXT="${CMAKE_CURRENT_SOURCE_DIR}/fixtures/sine8.txt")
