cmake_minimum_required(VERSION 3.15)
project(ViskoresConsumer LANGUAGES CXX)
find_package(Viskores 1.1 CONFIG REQUIRED)
add_executable(test_viskores test_viskores.cpp)
target_compile_features(test_viskores PRIVATE cxx_std_17)
target_link_libraries(test_viskores PRIVATE viskores::cont viskores::worklet
  viskores::filter viskores::source viskores::io viskores::rendering)
enable_testing()
add_test(NAME HarmonyViskoresConsumer COMMAND test_viskores)
