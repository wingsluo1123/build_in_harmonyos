# Includes

The include files cascade in this order:

- `"sox_i.h"`
  - `"soxomp.h"`
    - `"soxconfig.h"`
    - `<omp.h>`
  - `"sox_ng.h"`
    - `<limits.h>`
    - `<stdarg.h>`
    - `<stddef.h>`
  - `"util.h"`
    - `<stdio.h>`
    - `<stdlib.h>`
    - `"soxconfig.h"`
    - `<sys/types.h>`
    - `<sys/stat.h>`
    - `"xmalloc.h"`
      - `<stddef.h>`
      - `<string.h>`
      - `<strings.h>`
    - `<inttypes.h>` or `<stdint.h>`
    - `<math.h>`
  - `<assert.h>`
  - `<errno.h>`
  - `<byteswap.h>`
  - `"effects.h"`
  - `<ltdl.h>`

`sox_ng.h` is included by users of `libsox_ng`.

`sox_i.h` is included by sox-internal source files.

`sox_ng.c` is the only source file not to include `sox_i.h`
because it is a user of `libsox_ng`, but it does include `util.h`
for the `sox_*` type definitions and portability hacks.

That leaves individual source files to include, if needed:
- `<ctype.h>`
- `<fcntl.h>`
- `<io.h>`
- `<stropts.h>`
- `<unistd.h>`
