cmake_minimum_required(VERSION 3.15)
project(kaldi_vosk_consumer LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(MSVC)
    add_compile_options(/UNDEBUG)
else()
    add_compile_options(-UNDEBUG)
endif()
find_package(kaldi-vosk CONFIG REQUIRED)
add_executable(test_native_chain test_native_chain.cpp
    "${OPENFST_TEST_SOURCE}/src/extensions/ngram/bitmap-index.cc"
    "${OPENFST_TEST_SOURCE}/src/extensions/ngram/nthbit.cc")
# Only the optional ngram extension headers are copied here. All core headers
# and compiled FST symbols come from the tested package's dependency graph.
target_include_directories(test_native_chain PRIVATE "${OPENFST_TEST_HEADERS}")
target_compile_definitions(test_native_chain PRIVATE KALDI_TEST_NGRAM=1)
target_link_libraries(test_native_chain PRIVATE Kaldi::online2 Kaldi::nnet)
add_library(consumer_probe SHARED consumer_probe.cpp)
target_link_libraries(consumer_probe PRIVATE Kaldi::matrix Kaldi::fstext)
add_executable(test_dlopen test_dlopen.cpp)
target_link_libraries(test_dlopen PRIVATE ${CMAKE_DL_LIBS})
