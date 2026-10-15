cmake_minimum_required(VERSION 3.15)
project(test_kaccounts_integration CXX)

# KAccounts6 = kaccounts-integration (cmake_file_name mapped in the test
# conanfile). The exported KAccounts6 target links Qt6 + KF6::I18n
# transitively, so those must be found first.
find_package(Qt6 CONFIG REQUIRED Core Gui Xml DBus)
find_package(KF6I18n REQUIRED)
find_package(KF6CoreAddons REQUIRED)
find_package(KAccounts6 REQUIRED)

add_executable(test_kaccounts_integration test_kaccounts_integration.cpp)

target_link_libraries(test_kaccounts_integration KAccounts6)

# The ohpcd-published libaccounts-qt binary ships no cpp_info metadata, so
# CMakeDeps leaves its include dirs empty; point at the packaged header dir
# explicitly (the PACKAGE_FOLDER var comes from the CMakeDeps data file).
target_include_directories(test_kaccounts_integration PRIVATE
    "${libaccounts-qt_PACKAGE_FOLDER_RELEASE}/include/accounts-qt"
    "${libaccounts-glib_PACKAGE_FOLDER_RELEASE}/include/libaccounts-glib"
)

# Exercise the exported KAccountsMacros.cmake as a real consumer would
# (kaccounts-providers drives this macro for every provider file).
kaccounts_add_provider(${CMAKE_CURRENT_SOURCE_DIR}/test.provider NO_INTLTOOL)

enable_testing()
add_test(NAME test_kaccounts_integration COMMAND test_kaccounts_integration)
