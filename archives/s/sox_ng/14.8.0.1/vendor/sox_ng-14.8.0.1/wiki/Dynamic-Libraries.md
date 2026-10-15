# Dynamic libraries

On most operating systems, software libraries can be provided as
static libraries, whereby a copy of the code in question is included
in the executable file, making it rather large and resulting in
a copy of the same library code being included in many executable files,
and/or as dynamically loaded libraries (".dll" files on Windows or ".so"
files on Unix), whereby one copy of the library code is stored on the disk
and that same copy is added to the code of executable that use it
when the executable file is loaded into memory ready to be executed,
meaning that if the library is upgraded, all programs that use it
get the new version without having to be recompiled.

SoX can be made to provide `libsox` as one kind or the other
by its configure options by default it builds both kinds. 
`--enable-static --disable-shared` only builds one kind of `libsox`
and the `sox` executable and `libsox.a` library will be enormous
will all of the format handlers built-in, currently 3MB and 6MB respectively
instead of 187K and 2.8MB,
(the system libraries they use are still loaded by the above mechanism).

SoX has a two other ways in which it can use dynamic libraries:

* Dynamically-loaded libraries, the subject of this article
* Dynamically-loaded audio file formats, the subject of a separate article:
  [Dynamic Formats](Dynamic-Formats).

## Dynamically-loaded libraries

`configure --enable-dl-{amrnw,amrwb,mad,lame,twolame,sndfile}`
does not use the operating system's usual mechanism to load these
libraries when you compile SoX, but looks for them when sox is run.

For each of the six libraries, the process starts with code in
`configure.ac` that checks for the presence of the option and the
availability of `libltdl`, the mechanism that it uses to load them,
and sets a C preprocessor `#define`, for example `DL_SNDFILE`.

In the source file, for example `src/whatever.c`, it then has:

* a list of possible names for the library file to load
* a list of the functions it calls in that library

At compile-time, the macro `LSX_DLENTRIES_TO_PTRS` creates a list
of function pointers in the format's private date structure (`priv_t`)
with the same names as the library functions it will call,
and
`LSX_DLENTRIES_TO_FUNCTIONS` creates a list of declarations for those
functions.

At run-time, the format handler's `start()` function uses `LSX_DLLIBRARY_OPEN`
to fill in the values of the function pointers, either to the static functions
if the library is being loaded in the usual way or to wherever they were
loaded into memory by `libltdl` if the dynamic option was selected.
In the code, the functions are then called as, for example, `p->sf_open()`
instead of the usual `sf_open()`.

To make a library dynamically loaded in this way, you need to:

* in `configure.ac`, modify its paragraph to include `--enable-dl-whatever`
  and the stuff that follows it - take another dynamic library as an example
* in its source file,
  * add the `DL_WHATEVER` stuff at the top, including `whatever_library_names`
  * add the `WHATEVER_FUNC_ENTRIES`, listing the library's functions that it
    calls with their return type and argument types
  * in its `priv_t` structure, add `LSX_DLENTRIES_TO_PTRS(WHATEVER_FUNC_ENTRIES, whatever_dl);`
  * in its `start()` function, add `LSX_DLLIBRARY_OPEN(...);` and the
    `library_result` lines
  * in its `kill()` function, add `LSX_DLLIBRARY_CLOSE(p, speexdsp_dl);`
  * throughout the code, for every library function that it calls, change
    `whatever_init()` to `p->whatever_init()` and so on.
