# Original x86 port-I/O header under the OHOS aarch64 target

Probe input `port_asm.c` contains `#include "io_cpu.h"` from the unchanged
xmbmon 2.05 source tarball (SHA-256
`65b10ebfe53585ac22d6a31d8ef3fea552cb266cf2c124c00421dec1df5a4a4f`).
The probe checks compilation of the original inline port-I/O implementation,
not execution of a diagnostic on OHOS. Source path is abbreviated below.

```text
$ clang --target=aarch64-linux-ohos -I<upstream> -c port_asm.c -o port_asm.o
exit=1
In file included from port_asm.c:1:
<upstream>/io_cpu.h:41:37: error: invalid output constraint '=a' in asm
   41 |         __asm__ __volatile__("inb %1,%0" : "=a" (ret) : "d" (port));
      |                                            ^
<upstream>/io_cpu.h:49:37: error: invalid output constraint '=a' in asm
   49 |         __asm__ __volatile__("inw %1,%0" : "=a" (ret) : "d" (port));
      |                                            ^
<upstream>/io_cpu.h:57:37: error: invalid output constraint '=a' in asm
   57 |         __asm__ __volatile__("inl %1,%0" : "=a" (ret) : "d" (port));
      |                                            ^
<upstream>/io_cpu.h:64:40: error: invalid input constraint 'a' in asm
   64 |         __asm__ __volatile__("outb %0,%1" : : "a" (val), "d" (port));
      |                                               ^
<upstream>/io_cpu.h:70:40: error: invalid input constraint 'a' in asm
   70 |         __asm__ __volatile__("outw %0,%1" : : "a" (val), "d" (port));
      |                                               ^
<upstream>/io_cpu.h:76:40: error: invalid input constraint 'a' in asm
   76 |         __asm__ __volatile__("outl %0,%1" : : "a" (val), "d" (port));
      |                                               ^
6 errors generated.
```
