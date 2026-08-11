cmake_minimum_required(VERSION 3.15)
project(test_svgpart CXX)

# svgpart depends on Qt6/KF6 targets; load Qt6 first, then qtsvg package.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(Qt6Svg REQUIRED CONFIG)
find_package(Qt6SvgWidgets REQUIRED CONFIG)
find_package(KF6Parts REQUIRED)
find_package(KF6XmlGui REQUIRED)

add_executable(test_svgpart test.cpp)
target_link_libraries(test_svgpart KF6::Parts KF6::XmlGui)

enable_testing()
add_test(NAME test_svgpart COMMAND test_svgpart)
