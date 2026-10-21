cmake_minimum_required(VERSION 3.16)
project(test_drumstick CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

# The upstream drumstick-config.cmake checks the plain QT_VERSION_MAJOR
# variable (set by find_package(QT ...)), which Qt6Config.cmake only records
# as a directory property — declare it explicitly (libdrumstick precedent).
set(QT_VERSION_MAJOR 6)

# Drumstick ships its own relocatable cmake package files
# (lib/cmake/drumstick/drumstick-config.cmake); find_package dispatches to the
# per-component drumstick-{alsa,file,rt,widgets}-config.cmake files.
find_package(Drumstick REQUIRED COMPONENTS ALSA File RT Widgets)

# Qt6Core and the ALSA import (for alsa/asoundlib.h headers reached through
# <drumstick/alsaevent.h>) are needed by the test translation unit.
# (Qt6::Gui is intentionally NOT linked: the test avoids QWidget-derived
# classes so it runs with a plain QCoreApplication; widgetsTest in the
# upstream CTest suite already covers Drumstick::Widgets.)
find_package(Qt6 6.2 REQUIRED COMPONENTS Core Network)
# alsa-lib ships only a pkg-config file (its CMakeDeps config carries no
# include dirs), so resolve ALSA through pkg-config — same as the main recipe.
find_package(PkgConfig REQUIRED)
pkg_check_modules(ALSA REQUIRED IMPORTED_TARGET alsa)

add_executable(test_drumstick test_drumstick.cpp)
target_link_libraries(test_drumstick PRIVATE
    Drumstick::ALSA
    Drumstick::File
    Drumstick::RT
    PkgConfig::ALSA
    Qt6::Core
)

enable_testing()
add_test(NAME test_drumstick COMMAND test_drumstick)
set_tests_properties(test_drumstick PROPERTIES
    ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
