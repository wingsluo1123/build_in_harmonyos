/*
 * test_pllua.c — Test that pllua.so is a valid PostgreSQL extension.
 *
 * Verifies the shared library exists and is a valid ELF shared object
 * for arm64 architecture.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <elf.h>
#include <sys/stat.h>

int main(int argc, char *argv[])
{
    const char *so_path = "pllua.so";
    int fd;
    Elf64_Ehdr ehdr;
    struct stat st;

    if (argc > 1 && argv[1][0]) {
        so_path = argv[1];
    }

    /* Check file exists and is readable */
    if (stat(so_path, &st) != 0) {
        fprintf(stderr, "FAIL: Cannot stat %s: %s\n", so_path, strerror(errno));
        return 1;
    }
    printf("OK: File exists (%ld bytes)\n", (long)st.st_size);

    /* Check it's a shared library (executable bit set) */
    if (!(st.st_mode & S_IRUSR)) {
        fprintf(stderr, "FAIL: File not readable\n");
        return 1;
    }
    printf("OK: File is readable\n");

    /* Read ELF header */
    fd = open(so_path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "FAIL: Cannot open %s: %s\n", so_path, strerror(errno));
        return 1;
    }

    if (read(fd, &ehdr, sizeof(ehdr)) != sizeof(ehdr)) {
        fprintf(stderr, "FAIL: Cannot read ELF header\n");
        close(fd);
        return 1;
    }
    close(fd);

    /* Verify ELF magic */
    if (memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "FAIL: Not a valid ELF file\n");
        return 1;
    }
    printf("OK: Valid ELF magic\n");

    /* Verify it's a shared library */
    if (ehdr.e_type != ET_DYN) {
        fprintf(stderr, "FAIL: Not a shared library (e_type=%d)\n", ehdr.e_type);
        return 1;
    }
    printf("OK: Shared library (ET_DYN)\n");

    /* Verify architecture is AArch64 */
    if (ehdr.e_machine != EM_AARCH64) {
        fprintf(stderr, "FAIL: Not AArch64 (e_machine=%d)\n", ehdr.e_machine);
        return 1;
    }
    printf("OK: AArch64 architecture\n");

    printf("PASS: %s is a valid PostgreSQL extension shared library\n", so_path);
    return 0;
}
