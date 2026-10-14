# Forward upstream-owned subproject targets to published Conan GTest.
# Real INTERFACE targets, rather than aliases, accept upstream set_property
# calls without mutating the imported dependency or compiling vendored code.
find_package(GTest CONFIG REQUIRED)
foreach(component gtest gmock gmock_main)
  add_library(${component} INTERFACE)
  target_link_libraries(${component} INTERFACE GTest::${component})
endforeach()
