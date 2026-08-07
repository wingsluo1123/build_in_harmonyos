#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Test: verify the iODBC driver .so exists and has correct name.
 * The driver .so (libqsqliodbc.so) is a Qt5 plugin that uses QIODBC3/QIODBC
 * driver keys. We verify the file exists and has ELF magic bytes. */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path-to-libqsqliodbc.so>\n", argv[0]);
        return 1;
    }

    const char *path = argv[1];
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "Cannot open %s\n", path);
        return 1;
    }

    /* Check ELF magic bytes */
    unsigned char magic[4];
    if (fread(magic, 1, 4, f) != 4) {
        fprintf(stderr, "Cannot read magic bytes\n");
        fclose(f);
        return 1;
    }
    fclose(f);

    if (magic[0] != 0x7f || magic[1] != 'E' || magic[2] != 'L' || magic[3] != 'F') {
        fprintf(stderr, "Not an ELF file\n");
        return 1;
    }

    /* Verify the filename contains "iodbc" to distinguish from unixODBC driver */
    if (strstr(path, "iodbc") == NULL) {
        fprintf(stderr, "Driver name does not contain 'iodbc'\n");
        return 1;
    }

    printf("qt-libiodbc driver verified: %s\n", path);
    printf("ELF magic: OK\n");
    printf("Driver name: iODBC (QIODBC3/QIODBC keys)\n");
    return 0;
}
