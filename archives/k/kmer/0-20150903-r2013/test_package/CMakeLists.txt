cmake_minimum_required(VERSION 3.15)
project(kmer_consumer CXX)

find_package(kmer REQUIRED)

add_executable(test_kmer test_kmer.cc)
target_link_libraries(test_kmer PRIVATE kmer::kmer)
