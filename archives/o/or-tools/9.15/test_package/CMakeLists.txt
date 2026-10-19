cmake_minimum_required(VERSION 3.16)
project(test_ortools LANGUAGES CXX)

find_package(ortools CONFIG REQUIRED)

add_executable(test_ortools test.cpp)
target_compile_features(test_ortools PRIVATE cxx_std_17)
# OR-Tools registers its solvers (GLOP/CBC/...) through static initializers
# (e.g. kRegisterGlop in glop_interface.cc).  When linking the merged static
# archive normally, the linker drops those unreferenced objects and MPSolver
# aborts at runtime with "No factory registered".  Wrap exactly the ortools
# archive with --whole-archive so the registration objects are kept.
# ortools::ortools is an INTERFACE target, so the archive path is injected
# by test_package/conanfile.py (OR_TOOLS_LIB).
if(OR_TOOLS_LIB AND EXISTS "${OR_TOOLS_LIB}")
  target_link_libraries(test_ortools PRIVATE
    ortools::ortools
    "-Wl,--whole-archive"
    "${OR_TOOLS_LIB}"
    "-Wl,--no-whole-archive")
else()
  target_link_libraries(test_ortools PRIVATE ortools::ortools)
endif()
# or-tools generated pb headers declare members as `OR_PROTO_DLL ...`; the
# upstream build defines OR_PROTO_DLL= empty on every target but the value is
# not exported through the installed config, so define it here for consumers.
target_compile_definitions(test_ortools PRIVATE OR_PROTO_DLL=)

enable_testing()
add_test(NAME or_tools_lp_cp_ohos COMMAND test_ortools)
