cmake_minimum_required(VERSION 3.15)
project(test_parole C)

# parole is an application — verify it provides the expected package
find_package(parole REQUIRED)

# Build a test that links against parole's libraries to verify installation
add_executable(test_parole test.c)

# Link against parole's dependencies (glib, gtk, etc. are pulled in transitively)
target_link_libraries(test_parole parole::parole)

enable_testing()
add_test(NAME test_parole COMMAND test_parole)
