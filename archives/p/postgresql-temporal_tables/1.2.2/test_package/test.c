#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <elf.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>

/* Path to the shared library, set via -D at compile time */
#ifndef TEMPORAL_TABLES_LIB_PATH
#error "TEMPORAL_TABLES_LIB_PATH must be defined"
#endif

static int check_elf_shared(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return 0;

    struct stat st;
    if (fstat(fd, &st) < 0) { close(fd); return 0; }

    void *map = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);
    if (map == MAP_FAILED) return 0;

    Elf64_Ehdr *ehdr = (Elf64_Ehdr *)map;
    /* Check ELF magic and shared object type */
    int ok = (ehdr->e_ident[EI_MAG0] == ELFMAG0 &&
              ehdr->e_ident[EI_MAG1] == ELFMAG1 &&
              ehdr->e_ident[EI_MAG2] == ELFMAG2 &&
              ehdr->e_ident[EI_MAG3] == ELFMAG3 &&
              ehdr->e_type == ET_DYN);

    munmap(map, st.st_size);
    return ok;
}

static int check_symbol_via_nm(const char *path, const char *sym_name) {
    char cmd[512];
    /* nm -D lists dynamic symbols; T = text (code) section */
    snprintf(cmd, sizeof(cmd), "nm -D '%s' 2>/dev/null | grep -w '%s' | grep -E '^[0-9a-f]+ T'", path, sym_name);
    FILE *fp = popen(cmd, "r");
    if (!fp) return 0;
    char buf[256];
    int found = (fgets(buf, sizeof(buf), fp) != NULL);
    pclose(fp);
    return found;
}

int main(void) {
    const char *lib_path = TEMPORAL_TABLES_LIB_PATH;
    int failures = 0;

    printf("Checking temporal_tables at: %s\n", lib_path);

    /* 1. Check the file exists and is readable */
    FILE *f = fopen(lib_path, "r");
    if (!f) {
        fprintf(stderr, "FAIL: Cannot open %s\n", lib_path);
        return 1;
    }
    fclose(f);
    printf("File exists: OK\n");

    /* 2. Check it's a valid ELF shared object */
    if (!check_elf_shared(lib_path)) {
        fprintf(stderr, "FAIL: Not a valid ELF shared object\n");
        return 1;
    }
    printf("ELF shared object: OK\n");

    /* 3. Check for Pg_magic_func — required by PostgreSQL for all extensions */
    if (!check_symbol_via_nm(lib_path, "Pg_magic_func")) {
        fprintf(stderr, "FAIL: Pg_magic_func symbol not found\n");
        failures++;
    } else {
        printf("Pg_magic_func: found\n");
    }

    /* 4. Check for versioning — the main trigger function */
    if (!check_symbol_via_nm(lib_path, "versioning")) {
        fprintf(stderr, "FAIL: versioning symbol not found\n");
        failures++;
    } else {
        printf("versioning: found\n");
    }

    /* 5. Check for _PG_init — extension initialization function */
    if (!check_symbol_via_nm(lib_path, "_PG_init")) {
        fprintf(stderr, "FAIL: _PG_init symbol not found\n");
        failures++;
    } else {
        printf("_PG_init: found\n");
    }

    /* 6. Check for pg_finfo_versioning — function info marker */
    if (!check_symbol_via_nm(lib_path, "pg_finfo_versioning")) {
        fprintf(stderr, "FAIL: pg_finfo_versioning symbol not found\n");
        failures++;
    } else {
        printf("pg_finfo_versioning: found\n");
    }

    if (failures > 0) {
        fprintf(stderr, "FAIL: %d symbol check(s) failed\n", failures);
        return 1;
    }

    printf("test temporal_tables 1.2.2: ALL CHECKS PASSED\n");
    return 0;
}
