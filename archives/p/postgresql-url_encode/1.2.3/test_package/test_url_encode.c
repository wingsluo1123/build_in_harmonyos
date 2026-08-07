/*
 * Test program for postgresql-url_encode extension.
 * Reads the .so ELF file directly (without dlopen, since PostgreSQL
 * extensions require server-provided symbols) and verifies:
 * 1. Valid ELF header
 * 2. Shared object type (ET_DYN)
 * 3. Contains Pg_magic_func symbol (PG_MODULE_MAGIC)
 * 4. Contains url_encode and url_decode exported function symbols
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <elf.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path_to_url_encode.so>\n", argv[0]);
        return 1;
    }

    const char *so_path = argv[1];
    FILE *f = fopen(so_path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: Cannot open %s\n", so_path);
        return 1;
    }

    /* Read ELF header */
    Elf64_Ehdr ehdr;
    if (fread(&ehdr, sizeof(ehdr), 1, f) != 1) {
        fprintf(stderr, "FAIL: Cannot read ELF header\n");
        fclose(f);
        return 1;
    }

    /* Check ELF magic */
    if (memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "FAIL: Not an ELF file\n");
        fclose(f);
        return 1;
    }
    printf("OK: Valid ELF header\n");

    /* Check ELF type is shared object (ET_DYN) */
    if (ehdr.e_type != ET_DYN) {
        fprintf(stderr, "FAIL: Not a shared object (e_type=%d)\n", ehdr.e_type);
        fclose(f);
        return 1;
    }
    printf("OK: Shared object type\n");

    /* Read section header string table */
    Elf64_Shdr shstrtab_shdr;
    fseek(f, ehdr.e_shoff + ehdr.e_shstrndx * sizeof(Elf64_Shdr), SEEK_SET);
    fread(&shstrtab_shdr, sizeof(shstrtab_shdr), 1, f);

    char *shstrtab = malloc(shstrtab_shdr.sh_size);
    fseek(f, shstrtab_shdr.sh_offset, SEEK_SET);
    fread(shstrtab, shstrtab_shdr.sh_size, 1, f);

    /* Find .dynsym and .dynstr sections */
    Elf64_Shdr dynsym_shdr, dynstr_shdr;
    int found_dynsym = 0, found_dynstr = 0;

    Elf64_Shdr shdr;
    for (int i = 0; i < ehdr.e_shnum; i++) {
        fseek(f, ehdr.e_shoff + i * sizeof(Elf64_Shdr), SEEK_SET);
        fread(&shdr, sizeof(shdr), 1, f);
        char *secname = shstrtab + shdr.sh_name;
        if (strcmp(secname, ".dynsym") == 0) {
            dynsym_shdr = shdr;
            found_dynsym = 1;
        }
        if (strcmp(secname, ".dynstr") == 0) {
            dynstr_shdr = shdr;
            found_dynstr = 1;
        }
    }

    if (!found_dynsym || !found_dynstr) {
        fprintf(stderr, "FAIL: .dynsym or .dynstr section not found\n");
        free(shstrtab);
        fclose(f);
        return 1;
    }

    /* Read dynamic string table */
    char *dynstr = malloc(dynstr_shdr.sh_size);
    fseek(f, dynstr_shdr.sh_offset, SEEK_SET);
    fread(dynstr, dynstr_shdr.sh_size, 1, f);

    /* Read dynamic symbol table and search for expected symbols */
    Elf64_Sym *dynsym = malloc(dynsym_shdr.sh_size);
    fseek(f, dynsym_shdr.sh_offset, SEEK_SET);
    fread(dynsym, dynsym_shdr.sh_size, 1, f);
    int nsyms = dynsym_shdr.sh_size / sizeof(Elf64_Sym);

    int found_magic = 0, found_encode = 0, found_decode = 0;
    int found_uri_encode = 0, found_uri_decode = 0;
    for (int i = 0; i < nsyms; i++) {
        char *name = dynstr + dynsym[i].st_name;
        if (strcmp(name, "Pg_magic_func") == 0) found_magic = 1;
        if (strcmp(name, "url_encode") == 0) found_encode = 1;
        if (strcmp(name, "url_decode") == 0) found_decode = 1;
        if (strcmp(name, "uri_encode") == 0) found_uri_encode = 1;
        if (strcmp(name, "uri_decode") == 0) found_uri_decode = 1;
    }

    free(shstrtab); free(dynstr); free(dynsym);
    fclose(f);

    if (!found_magic) {
        fprintf(stderr, "FAIL: Pg_magic_func symbol not found\n");
        return 1;
    }
    printf("OK: Pg_magic_func (PG_MODULE_MAGIC) found\n");

    if (!found_encode || !found_decode) {
        fprintf(stderr, "FAIL: url_encode or url_decode symbol not found\n");
        return 1;
    }
    printf("OK: url_encode and url_decode symbols found\n");

    if (!found_uri_encode || !found_uri_decode) {
        fprintf(stderr, "FAIL: uri_encode or uri_decode symbol not found\n");
        return 1;
    }
    printf("OK: uri_encode and uri_decode symbols found\n");

    printf("ALL TESTS PASSED\n");
    return 0;
}
