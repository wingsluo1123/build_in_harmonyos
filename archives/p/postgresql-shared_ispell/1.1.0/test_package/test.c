/* Test package for postgresql-shared_ispell
 * Uses readelf to verify the shared_ispell.so contains PostgreSQL extension symbols
 * This is a non-trivial test that verifies the package's build output
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path-to-shared_ispell.so>\n", argv[0]);
        return 1;
    }

    const char *so_path = argv[1];
    printf("Verifying shared_ispell extension: %s\n", so_path);

    /* Check ELF magic bytes */
    FILE *fp = fopen(so_path, "rb");
    if (!fp) {
        fprintf(stderr, "Cannot open shared_ispell.so: %s\n", so_path);
        return 1;
    }
    unsigned char magic[4];
    if (fread(magic, 1, 4, fp) != 4 || magic[0] != 0x7f || magic[1] != 'E' || magic[2] != 'L' || magic[3] != 'F') {
        fprintf(stderr, "shared_ispell.so is not a valid ELF file\n");
        fclose(fp);
        return 1;
    }
    fclose(fp);
    printf("  [OK] Valid ELF shared library\n");

    /* Use readelf to check for PostgreSQL extension symbols */
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "readelf -s '%s' 2>/dev/null", so_path);
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "Cannot run readelf on shared_ispell.so\n");
        return 1;
    }

    /* Expected symbols in a PostgreSQL extension */
    const char *expected_symbols[] = {
        "_PG_init",
        "dispell_init",
        "dispell_lexize",
        "dispell_reset",
        "dispell_mem_used",
        "dispell_mem_available",
        NULL
    };
    int found[6] = {0, 0, 0, 0, 0, 0};

    char line[256];
    while (fgets(line, sizeof(line), fp)) {
        for (int i = 0; expected_symbols[i]; i++) {
            if (strstr(line, expected_symbols[i]) && !found[i]) {
                found[i] = 1;
                printf("  [OK] Found symbol: %s\n", expected_symbols[i]);
            }
        }
    }
    pclose(fp);

    /* Check that at least _PG_init and dispell_init are present */
    if (!found[0]) {
        fprintf(stderr, "  [FAIL] _PG_init not found - not a valid PostgreSQL extension\n");
        return 1;
    }
    if (!found[1]) {
        fprintf(stderr, "  [FAIL] dispell_init not found - extension API missing\n");
        return 1;
    }

    int total_found = 0;
    for (int i = 0; expected_symbols[i]; i++) {
        total_found += found[i];
    }
    printf("shared_ispell extension verified: %d/%d symbols found\n", total_found, 6);
    printf("All checks passed!\n");
    return 0;
}
