cmake_minimum_required(VERSION 3.16)
project(test_krunner CXX)

# The KF6Runner public headers are KF6 C++20 headers. AUTOMOC generates
# the meta-object code for the AbstractRunner subclass declared inside
# test_krunner.cpp (the file includes its own "test_krunner.moc").
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

# Qt6::Core/Qt6::Gui come from qtbase (the QGuiApplication runs on the
# offscreen platform plugin); KF6Runner resolves through the
# project-installed KF6RunnerConfig.cmake (the recipe sets
# cmake_find_mode=none so CMakeDeps does not shadow it).
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Runner REQUIRED)

add_executable(test_krunner test_krunner.cpp)
target_link_libraries(test_krunner PRIVATE KF6::Runner Qt6::Core Qt6::Gui)

enable_testing()
add_test(NAME test_krunner COMMAND test_krunner)
