# Raw L5 evidence for final package revision

Package reference:

```text
sdl12-compat/1.2.68@ohpcd/stable#4e019b9fc09df67215d2d2ac33647eab:92219b911295cbf30b8c778a4da3b51506c9d757#add464ab86072d9d626c35518c8863c5
```

## Package files and licenses

```text
lib/libSDL-1.2.so
lib/libSDL-1.2.so.0 -> libSDL-1.2.so
lib/libSDL.so -> libSDL-1.2.so
lib/libSDL2-2.0.so.0
licenses/LICENSE.txt
licenses/SDL2-LICENSE.txt
```

License hashes:

```text
8bb90ab9c7b3b4aaa2f59e6e629ecdb55b7d8f4a0159e74d8f106237e094eaab  licenses/LICENSE.txt
204f777c4861e7acbe2671a399c1432f4e4f890084fd6e26f80daee29b0744db  licenses/SDL2-LICENSE.txt
```

## `libSDL-1.2.so`

Verbatim relevant `llvm-readelf -h/-d` and signing output:

```text
Class:                             ELF64
Type:                              DYN (Shared object file)
Machine:                           AArch64
0x0000000000000001 (NEEDED)       Shared library: [libc.so]
0x000000000000000e (SONAME)       Library soname: [libSDL-1.2.so.0]
37 .codesign          00001000 0000000000000000
code signature is self-sign
```

No `RPATH` or `RUNPATH` entry was emitted by `llvm-readelf -d`.

## `libSDL2-2.0.so.0`

Verbatim relevant `llvm-readelf -h/-d` and signing output:

```text
Class:                             ELF64
Type:                              DYN (Shared object file)
Machine:                           AArch64
0x0000000000000001 (NEEDED)       Shared library: [libc.so]
0x000000000000000e (SONAME)       Library soname: [libSDL2-2.0.so.0]
37 .codesign          00001000 0000000000000000
code signature is self-sign
```

No `RPATH` or `RUNPATH` entry was emitted by `llvm-readelf -d`.

The recipe performs these same architecture, SONAME, NEEDED, RPATH/RUNPATH and signature-metadata checks during packaging, so a mismatch fails `conan create` before package revision creation. The updated PR was independently rebuilt and tested successfully by repository CI [#25636](https://ohpcd.atomgit.com/ci?id=25636).
