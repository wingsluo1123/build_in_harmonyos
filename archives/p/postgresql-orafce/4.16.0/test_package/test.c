#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <elf.h>
#include <string.h>

/* Read ELF header and verify the file is a valid ARM64 shared library.
 * This tests the package by verifying its primary artifact (orafce.so)
 * is a correctly built ELF shared object for the target architecture.
 * A full dlopen test is not possible because PostgreSQL extensions
 * have undefined symbols resolved by the PostgreSQL server at runtime. */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path_to_orafce.so>\n", argv[0]);
        return 1;
    }

    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "Cannot open %s\n", argv[1]);
        return 1;
    }

    Elf64_Ehdr ehdr;
    if (read(fd, &ehdr, sizeof(ehdr)) != sizeof(ehdr)) {
        fprintf(stderr, "Cannot read ELF header\n");
        close(fd);
        return 1;
    }
    close(fd);

    /* Check ELF magic */
    if (memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "Not an ELF file\n");
        return 1;
    }

    /* Check it's a shared library (ET_DYN = 3) */
    if (ehdr.e_type != ET_DYN) {
        fprintf(stderr, "Not a shared library (e_type=%d)\n", ehdr.e_type);
        return 1;
    }

    /* Check architecture is AArch64 (EM_AARCH64 = 183) */
    if (ehdr.e_machine != EM_AARCH64) {
        fprintf(stderr, "Not AArch64 (e_machine=%d)\n", ehdr.e_machine);
        return 1;
    }

    printf("orafce.so verified: valid ELF shared library for AArch64\n");
    return 0;
}
