/*
 * Minimal freestanding AArch64 guest for the gem5 SE smoke test.
 *
 * Uses only write(2) and exit(2) via direct syscalls, so it is a
 * self-contained static ELF with no libc / libc-startup dependencies.
 * (The OHOS musl libc startup issues prctl(167), which gem5 SE does not
 * emulate; the freestanding program keeps the test hermetic.)
 *
 * Compiled at test time with the platform clang:
 *   clang -static -nostdlib -fno-stack-protector \
 *         -Wl,--build-id=none -O1 -o hello hello.c
 */
typedef unsigned long ulong;

static long
write_syscall(long fd, const void *buf, ulong count)
{
    register long x0 __asm__("x0") = fd;
    register const void *x1 __asm__("x1") = buf;
    register ulong x2 __asm__("x2") = count;
    register long x8 __asm__("x8") = 64; /* __NR_write */
    __asm__ volatile("svc #0"
                     : "+r"(x0)
                     : "r"(x1), "r"(x2), "r"(x8)
                     : "memory");
    return x0;
}

static void
exit_syscall(long code)
{
    register long x0 __asm__("x0") = code;
    register long x8 __asm__("x8") = 93; /* __NR_exit */
    __asm__ volatile("svc #0" : : "r"(x0), "r"(x8) : "memory");
    __builtin_unreachable();
}

void
_start(void)
{
    static const char msg[] = "Hello world!\n";
    write_syscall(1, msg, sizeof(msg) - 1);
    exit_syscall(0);
}
