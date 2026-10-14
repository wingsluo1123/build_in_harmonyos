cmake_minimum_required(VERSION 3.15)
project(test_juce CXX)

set(CMAKE_CXX_STANDARD 17)

# Find the package via Conan-generated CMakeDeps.  Transitive deps of the
# juce dependency chain must be found explicitly (CMakeDeps only emits
# config files for find_package'd packages); names follow each recipe's
# cmake_file_name (ALSA, mesa, fontconfig, freetype, expat).
find_package(ALSA REQUIRED)
find_package(expat REQUIRED)
find_package(freetype REQUIRED)
find_package(fontconfig REQUIRED)
# mesa-Target-release.cmake references llvm::llvm (mesa recipe emits its
# tool_requires into the link interface), but llvm is a build-time tool
# and CMakeDeps generates no config for it — stub the imported target.
if(NOT TARGET llvm::llvm)
    add_library(llvm::llvm INTERFACE IMPORTED)
endif()
find_package(mesa REQUIRED)
find_package(juce REQUIRED)

# juce_add_... helpers live in the JUCE CMake config; add the modules the
# consumer test exercises so the test compiles real JUCE module sources.
include_directories(${juce_INCLUDE_DIRS})

add_executable(test_juce test_juce_consumer.cpp)
# Compile the consumed JUCE modules into the test binary (module sources
# ship with the package).  Resolve the modules dir from the imported
# target's INTERFACE_INCLUDE_DIRECTORIES — entries may be wrapped in a
# generator expression; unwrap and pick the one holding modules/.
get_target_property(_juce_inc juce::juce INTERFACE_INCLUDE_DIRECTORIES)
set(_juce_modules "")
foreach(_entry ${_juce_inc})
    # strip $<$<CONFIG:Release>:...> wrapper by evaluating in Release
    string(REGEX REPLACE "^\\$<\\$<CONFIG:[^>]*>:" "" _e "${_entry}")
    string(REGEX REPLACE ">$" "" _e "${_e}")
    foreach(_d ${_e})
        if(IS_DIRECTORY "${_d}/modules")
            set(_juce_modules "${_d}/modules")
            break()
        endif()
        if(_d MATCHES "JUCE-8.0.14$" AND IS_DIRECTORY "${_d}")
            set(_juce_modules "${_d}/modules")
            break()
        endif()
    endforeach()
    if(_juce_modules)
        break()
    endif()
endforeach()
if(NOT _juce_modules)
    # Last resort: fixed install layout include/JUCE-<version>/modules.
    foreach(_d ${_juce_inc})
        if(_d MATCHES "include$")
            file(GLOB _cand "${_d}/JUCE-*/modules")
            if(_cand)
                list(GET _cand 0 _juce_modules)
                break()
            endif()
        endif()
    endforeach()
endif()
if(NOT _juce_modules)
    message(FATAL_ERROR "juce modules dir not found under ${_juce_inc}")
endif()
message(STATUS "juce modules: ${_juce_modules}")

target_compile_definitions(test_juce PRIVATE
    JUCE_MODULE_AVAILABLE_juce_core=1
    JUCE_MODULE_AVAILABLE_juce_events=1
    JUCE_MODULE_AVAILABLE_juce_data_structures=1
    JUCE_MODULE_AVAILABLE_juce_audio_basics=1
    JUCE_MODULE_AVAILABLE_juce_midi_ci=1
    JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1
    JUCE_STANDALONE_APPLICATION=1
    # 编译模块内上游单元测试类（juce_core/audio_basics/midi_ci 各 *Tests，
    # 受 #if JUCE_UNIT_TESTS 保护），供 test_juce 的 UnitTestRunner 执行。
    JUCE_UNIT_TESTS=1
    JUCE_USE_CURL=0)
target_include_directories(test_juce PRIVATE ${_juce_modules})
target_sources(test_juce PRIVATE
    ${_juce_modules}/juce_core/juce_core.cpp
    ${_juce_modules}/juce_core/juce_core_CompilationTime.cpp
    ${_juce_modules}/juce_events/juce_events.cpp
    ${_juce_modules}/juce_data_structures/juce_data_structures.cpp
    ${_juce_modules}/juce_audio_basics/juce_audio_basics.cpp
    ${_juce_modules}/juce_midi_ci/juce_midi_ci.cpp)
target_link_libraries(test_juce PRIVATE juce::juce)

enable_testing()
add_test(NAME test_juce COMMAND test_juce "${_juce_modules}")
