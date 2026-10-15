# plank

Memory instrumentation library by Karsten Pedersen (osen).

Plank detects heap-related memory errors by marking freed memory as forbidden
(using `mprotect(PROT_NONE)`) rather than actually freeing it. Any subsequent
read or write attempt produces a `SIGSEGV` signal.

## Libraries

- **libplank.a** — C pool allocator (`palloc`/`pfree`), vector, sstream
- **libplankmm.a** — C++ wrapper overriding global `new`/`delete`

## Build system

CMake (`cmake_minimum_required 2.6`, policy override 3.5)

## Dependencies

None — only uses POSIX libc (`mmap`, `mprotect`, `munmap`, `atexit`).
