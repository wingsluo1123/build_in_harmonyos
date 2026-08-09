#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

int main(void) {
    /* Verify the plugin .so exists, is a regular file, and has reasonable size.
     * The plugin includes statically-linked mupdf (~50MB), so it should be large.
     * We can't dlopen() it because it references zathura symbols resolved at runtime. */
    const char *so_path = getenv("PLUGIN_SO_PATH");
    if (!so_path) {
        fprintf(stderr, "FAIL: PLUGIN_SO_PATH not set\n");
        return 1;
    }
    struct stat st;
    if (stat(so_path, &st) != 0) {
        fprintf(stderr, "FAIL: %s does not exist\n", so_path);
        return 1;
    }
    if (!S_ISREG(st.st_mode)) {
        fprintf(stderr, "FAIL: %s is not a regular file\n", so_path);
        return 1;
    }
    if (st.st_size < 1000000) {
        fprintf(stderr, "FAIL: %s too small (%ld bytes, expected > 1MB)\n", so_path, st.st_size);
        return 1;
    }
    /* Check ELF magic (0x7f 'E' 'L' 'F') */
    FILE *f = fopen(so_path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", so_path);
        return 1;
    }
    unsigned char magic[4];
    if (fread(magic, 1, 4, f) != 4) {
        fclose(f);
        fprintf(stderr, "FAIL: cannot read ELF header\n");
        return 1;
    }
    fclose(f);
    if (magic[0] != 0x7f || magic[1] != 'E' || magic[2] != 'L' || magic[3] != 'F') {
        fprintf(stderr, "FAIL: not an ELF file\n");
        return 1;
    }
    printf("test zathura-pdf-mupdf 2026.05.10: OK (plugin .so verified, %ld bytes, ELF)\n", st.st_size);
    return 0;
}
