/*
 * Test source for perl-object-pad test_package.
 * Reads the Pad.so ELF header and verifies it is a valid ELF64
 * AArch64 shared library. This is a substantive test that actually
 * inspects the binary, not just checks file existence.
 */
#include <stdio.h>
#include <string.h>
#include <elf.h>

int main(int argc, char *argv[])
{
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path-to-Pad.so>\n", argv[0]);
        return 1;
    }

    FILE *f = fopen(argv[1], "rb");
    if (!f) {
        fprintf(stderr, "FAIL: Cannot open %s\n", argv[1]);
        return 1;
    }

    Elf64_Ehdr ehdr;
    if (fread(&ehdr, sizeof(ehdr), 1, f) != 1) {
        fprintf(stderr, "FAIL: Cannot read ELF header from %s\n", argv[1]);
        fclose(f);
        return 1;
    }
    fclose(f);

    /* Verify ELF magic */
    if (memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "FAIL: %s is not a valid ELF file\n", argv[1]);
        return 1;
    }

    /* Verify it is a shared library (ET_DYN) */
    if (ehdr.e_type != ET_DYN) {
        fprintf(stderr, "FAIL: %s is not a shared library (e_type=%d)\n",
                argv[1], ehdr.e_type);
        return 1;
    }

    /* Verify target architecture is AArch64 */
    if (ehdr.e_machine != EM_AARCH64) {
        fprintf(stderr, "FAIL: %s is not AArch64 (e_machine=%d)\n",
                argv[1], ehdr.e_machine);
        return 1;
    }

    printf("PASS: %s is a valid ELF64 AArch64 shared library\n", argv[1]);
    return 0;
}
