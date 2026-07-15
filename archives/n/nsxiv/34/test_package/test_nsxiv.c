/*
 * test_package/test_nsxiv.c — nsxiv test source
 *
 * This test verifies that the nsxiv binary is installed and is a valid
 * ELF executable. Since nsxiv is a GUI image viewer requiring X11 display,
 * we verify the binary exists rather than launching it (which needs a display).
 *
 * The actual runtime test (nsxiv -v) is performed in conanfile.py test().
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <elf.h>
#include <fcntl.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <nsxiv_binary_path>\n", argv[0]);
        return 1;
    }

    const char *bin_path = argv[1];
    struct stat st;

    /* Check binary exists */
    if (stat(bin_path, &st) != 0) {
        fprintf(stderr, "FAIL: nsxiv binary not found at %s\n", bin_path);
        return 1;
    }

    /* Check it's a regular file */
    if (!S_ISREG(st.st_mode)) {
        fprintf(stderr, "FAIL: %s is not a regular file\n", bin_path);
        return 1;
    }

    /* Check it's executable */
    if (!(st.st_mode & S_IXUSR)) {
        fprintf(stderr, "FAIL: %s is not executable\n", bin_path);
        return 1;
    }

    /* Verify ELF header */
    int fd = open(bin_path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "FAIL: cannot open %s\n", bin_path);
        return 1;
    }

    unsigned char eident[EI_NIDENT];
    if (read(fd, eident, EI_NIDENT) != EI_NIDENT) {
        fprintf(stderr, "FAIL: cannot read ELF header\n");
        close(fd);
        return 1;
    }
    close(fd);

    /* Check ELF magic */
    if (eident[EI_MAG0] != ELFMAG0 ||
        eident[EI_MAG1] != ELFMAG1 ||
        eident[EI_MAG2] != ELFMAG2 ||
        eident[EI_MAG3] != ELFMAG3) {
        fprintf(stderr, "FAIL: not an ELF file\n");
        return 1;
    }

    /* Check it's 64-bit */
    if (eident[EI_CLASS] != ELFCLASS64) {
        fprintf(stderr, "FAIL: not 64-bit ELF\n");
        return 1;
    }

    printf("PASS: nsxiv binary verified (ELF64, executable)\n");
    return 0;
}
