cmake_minimum_required(VERSION 3.15)
project(consumer_test C)

# Standalone consumer: it drives the wavplay / wavrec CLI (the package's public
# interface) at runtime via PATH, so it does not link against a wavplay library.
# It only needs libc (stdio/stdlib) and libm (sin for the generated test WAV).
add_executable(consumer_test consumer_test.c)
target_link_libraries(consumer_test PRIVATE m)
