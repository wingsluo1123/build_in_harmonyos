/*
 * Consumer test for sokol 0.0-git.2e75443 (C++11 TU).
 *
 * Exercises the sokol_gfx.h AND sokol_cmdbuf.h implementation sections
 * compiled as C++ in one TU — mirroring the upstream compile-suite
 * contract (tests/compile/sokol_gfx.cc + sokol_cmdbuf.cc): SOKOL_IMPL
 * activates both impl sections in this binary, so all sg_ and scb_
 * symbols resolve at link time. This is the exact code path fixed by
 * patch s0001 (void* to uint8_t* cast in _scb_init_cmdbuf).
 */
#ifndef SOKOL_DUMMY_BACKEND
#define SOKOL_DUMMY_BACKEND
#endif
#define SOKOL_IMPL
#include "sokol_gfx.h"
#include "sokol_cmdbuf.h"

#include <cstdio>

static int failures = 0;
#define CHECK(cond) do { \
    if (!(cond)) { failures++; std::printf("FAIL: %s (line %d)\n", #cond, __LINE__); } \
} while (0)

int main(void) {
    /* sokol_gfx lifecycle in C++ (dummy backend). sg_setup takes a
     * pointer and sokol_gfx.h ships no C++ reference overload — pass a
     * stack desc (upstream C++ consumers do the same). */
    sg_desc gfx_desc = {};
    sg_setup(&gfx_desc);
    CHECK(sg_isvalid());
    sg_shutdown();
    CHECK(!sg_isvalid());

    /* cmdbuf pool lifecycle in C++ — scb_setup HAS an inline C++
     * reference overload (sokol_cmdbuf.h line 444), and the impl
     * section runs the patch s0001 code path */
    scb_setup(scb_desc{});
    scb_shutdown();

    std::printf("sokol consumer test (C++): gfx+cmdbuf C++ impl OK, %d failures\n",
                failures);
    return failures ? 1 : 0;
}
