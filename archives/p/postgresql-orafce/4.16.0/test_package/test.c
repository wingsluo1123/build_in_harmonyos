#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <elf.h>
#include <sys/mman.h>
#include <sys/stat.h>

/* Verify orafce.so is a valid AArch64 ELF shared library AND contains
 * the required PostgreSQL extension entry-point symbols (_PG_init,
 * Pg_magic_func) by parsing the ELF dynamic symbol table.
 *
 * We cannot use dlopen because orafce.so has undefined symbols (PostgreSQL
 * server functions like pg_detoast_datum_packed) that are only resolved
 * when loaded by a running PostgreSQL server. Instead, we parse the
 * ELF .dynsym section to verify the expected symbols are exported. */
static int find_symbol(Elf64_Sym *syms, int count, const char *strtab, const char *name) {
    for (int i = 0; i < count; i++) {
        if (syms[i].st_name == 0) continue;
        const char *sym_name = strtab + syms[i].st_name;
        if (strcmp(sym_name, name) == 0)
            return 1;
    }
    return 0;
}

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

    struct stat st;
    if (fstat(fd, &st) < 0) {
        fprintf(stderr, "fstat failed\n");
        close(fd);
        return 1;
    }

    void *map = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (map == MAP_FAILED) {
        fprintf(stderr, "mmap failed\n");
        close(fd);
        return 1;
    }

    Elf64_Ehdr *ehdr = (Elf64_Ehdr *)map;
    int failures = 0;

    /* Check ELF magic */
    if (memcmp(ehdr->e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "FAIL: Not an ELF file\n");
        failures++;
        goto done;
    }

    /* Check 64-bit */
    if (ehdr->e_ident[EI_CLASS] != ELFCLASS64) {
        fprintf(stderr, "FAIL: Not 64-bit ELF\n");
        failures++;
        goto done;
    }

    /* Check shared library */
    if (ehdr->e_type != ET_DYN) {
        fprintf(stderr, "FAIL: Not a shared library (e_type=%d)\n", ehdr->e_type);
        failures++;
        goto done;
    }

    /* Check AArch64 */
    if (ehdr->e_machine != EM_AARCH64) {
        fprintf(stderr, "FAIL: Not AArch64 (e_machine=%d)\n", ehdr->e_machine);
        failures++;
        goto done;
    }

    printf("ELF header: valid 64-bit AArch64 shared library\n");

    /* Parse section headers to find .dynsym and .dynstr */
    Elf64_Shdr *shdrs = (Elf64_Shdr *)((char *)map + ehdr->e_shoff);
    Elf64_Shdr *dynsym = NULL, *dynstr = NULL;

    for (int i = 0; i < ehdr->e_shnum; i++) {
        if (shdrs[i].sh_type == SHT_DYNSYM)
            dynsym = &shdrs[i];
    }

    if (!dynsym) {
        fprintf(stderr, "FAIL: No .dynsym section found\n");
        failures++;
        goto done;
    }

    /* dynstr is linked from dynsym->sh_link */
    dynstr = &shdrs[dynsym->sh_link];
    if (dynstr->sh_type != SHT_STRTAB) {
        fprintf(stderr, "FAIL: .dynstr section not found\n");
        failures++;
        goto done;
    }

    Elf64_Sym *syms = (Elf64_Sym *)((char *)map + dynsym->sh_offset);
    int sym_count = dynsym->sh_size / sizeof(Elf64_Sym);
    const char *strtab = (const char *)map + dynstr->sh_offset;

    /* Check for required PostgreSQL extension symbols */
    if (find_symbol(syms, sym_count, strtab, "_PG_init")) {
        printf("Symbol check: _PG_init found\n");
    } else {
        fprintf(stderr, "FAIL: _PG_init symbol not found\n");
        failures++;
    }

    if (find_symbol(syms, sym_count, strtab, "Pg_magic_func")) {
        printf("Symbol check: Pg_magic_func found\n");
    } else {
        fprintf(stderr, "FAIL: Pg_magic_func symbol not found\n");
        failures++;
    }

done:
    munmap(map, st.st_size);
    close(fd);

    if (failures > 0) {
        fprintf(stderr, "FAIL: %d check(s) failed\n", failures);
        return 1;
    }
    printf("All orafce.so checks passed\n");
    return 0;
}
