/* test.c — Verify savage_drv.so X.Org driver module.
 *
 * This test verifies the savage_drv.so file by:
 * 1. Checking ELF magic bytes
 * 2. Reading the ELF header for validity
 * The driver module cannot be dlopen'd standalone (it requires
 * xorg-server symbols resolved at runtime by the X server).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <elf.h>

int main(int argc, char *argv[]) {
    const char *so_path = NULL;
    if (argc > 1) {
        so_path = argv[1];
    } else {
        so_path = getenv("SAVAGE_DRV_SO");
    }
    if (!so_path) {
        fprintf(stderr, "Usage: %s <savage_drv.so path>\n", argv[0]);
        return 1;
    }

    FILE *f = fopen(so_path, "rb");
    if (!f) {
        fprintf(stderr, "Cannot open %s\n", so_path);
        return 1;
    }

    Elf64_Ehdr ehdr;
    if (fread(&ehdr, sizeof(ehdr), 1, f) != 1) {
        fprintf(stderr, "Cannot read ELF header\n");
        fclose(f);
        return 1;
    }
    fclose(f);

    /* Check ELF magic */
    if (memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "Not an ELF file\n");
        return 1;
    }
    printf("ELF magic check: PASS\n");

    /* Check it's a shared library (ET_DYN) */
    if (ehdr.e_type != ET_DYN) {
        fprintf(stderr, "Not a shared library (e_type=%d)\n", ehdr.e_type);
        return 1;
    }
    printf("Shared library type check: PASS\n");

    /* Check ARM64 architecture */
    if (ehdr.e_machine != EM_AARCH64) {
        fprintf(stderr, "Not AArch64 (e_machine=%d)\n", ehdr.e_machine);
        return 1;
    }
    printf("AArch64 architecture check: PASS\n");

    printf("savage_drv.so verified successfully\n");
    return 0;
}
