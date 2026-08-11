/*
 * test_package/test.c — verify the packaged gst-quinn plugin artifact.
 *
 * R34: the test must genuinely exercise the packaged artifact. dlopen()
 * cannot be used on OHOS for plugins whose transitive deps (gstreamer C
 * stack) live outside the musl ldso namespace: the loader resolves
 * dlopen'ed NEEDED entries only from namespace paths, so dlopen fails
 * with "Error loading shared library libgstbase-1.0.so.0" regardless of
 * LD_LIBRARY_PATH / RUNPATH (knowledge E186, verified 2026-08-11).
 *
 * This test instead verifies the plugin's ABI surface directly from the
 * packaged ELF: it must be a 64-bit aarch64 shared object that exports
 * the GStreamer plugin entry points (gst_plugin_quinn_get_desc /
 * gst_plugin_quinn_register) in its dynamic symbol table. That is exactly
 * the surface gstreamer needs to load and register the plugin at
 * runtime, so the check exercises the real package contract without
 * depending on the loader namespace.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EM_AARCH64 183
#define SHT_DYNSYM 11
#define SHN_UNDEF 0

typedef struct {
    unsigned char e_ident[16];
    uint16_t e_type;
    uint16_t e_machine;
    uint32_t e_version;
    uint64_t e_entry;
    uint64_t e_phoff;
    uint64_t e_shoff;
    uint32_t e_flags;
    uint16_t e_ehsize;
    uint16_t e_phentsize;
    uint16_t e_phnum;
    uint16_t e_shentsize;
    uint16_t e_shnum;
    uint16_t e_shstrndx;
} Elf64_Ehdr;

typedef struct {
    uint32_t sh_name;
    uint32_t sh_type;
    uint64_t sh_flags;
    uint64_t sh_addr;
    uint64_t sh_offset;
    uint64_t sh_size;
    uint32_t sh_link;
    uint32_t sh_info;
    uint64_t sh_addralign;
    uint64_t sh_entsize;
} Elf64_Shdr;

typedef struct {
    uint32_t st_name;
    unsigned char st_info;
    unsigned char st_other;
    uint16_t st_shndx;
    uint64_t st_value;
    uint64_t st_size;
} Elf64_Sym;

static int read_at(FILE *f, long off, void *buf, size_t len) {
    if (fseek(f, off, SEEK_SET) != 0) return -1;
    return fread(buf, 1, len, f) == len ? 0 : -1;
}

int main(int argc, char **argv) {
    const char *path = argv[1];
    if (!path) {
        fprintf(stderr, "usage: %s <path-to-libgstquinn.so>\n", argv[0]);
        return 2;
    }

    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "cannot open %s\n", path);
        return 1;
    }

    Elf64_Ehdr eh;
    if (read_at(f, 0, &eh, sizeof(eh)) != 0 || memcmp(eh.e_ident, "\x7f" "ELF", 4) != 0) {
        fprintf(stderr, "not a valid ELF file: %s\n", path);
        fclose(f);
        return 1;
    }
    if (eh.e_ident[4] != 2) {
        fprintf(stderr, "not a 64-bit ELF (EI_CLASS=%d)\n", eh.e_ident[4]);
        fclose(f);
        return 1;
    }
    if (eh.e_machine != EM_AARCH64) {
        fprintf(stderr, "not aarch64 (e_machine=%u)\n", eh.e_machine);
        fclose(f);
        return 1;
    }
    if (eh.e_type != 3 /* ET_DYN */) {
        fprintf(stderr, "not a shared object (e_type=%u)\n", eh.e_type);
        fclose(f);
        return 1;
    }

    /* Walk section headers to find .dynsym and its .dynstr */
    Elf64_Shdr *shdrs = calloc(eh.e_shnum, sizeof(Elf64_Shdr));
    if (!shdrs || read_at(f, (long)eh.e_shoff, shdrs, sizeof(Elf64_Shdr) * eh.e_shnum) != 0) {
        fprintf(stderr, "cannot read section headers\n");
        fclose(f);
        return 1;
    }

    const char *shstr = NULL;
    size_t shstr_size = 0;
    if (eh.e_shstrndx < eh.e_shnum) {
        Elf64_Shdr *s = &shdrs[eh.e_shstrndx];
        shstr = malloc(s->sh_size);
        if (shstr && read_at(f, (long)s->sh_offset, (void *)shstr, s->sh_size) == 0)
            shstr_size = s->sh_size;
    }

    const char *dynstr = NULL;
    size_t dynstr_size = 0;
    Elf64_Sym *dynsym = NULL;
    size_t dynsym_count = 0;

    for (unsigned i = 0; i < eh.e_shnum; i++) {
        Elf64_Shdr *s = &shdrs[i];
        const char *name = shstr && s->sh_name < shstr_size ? shstr + s->sh_name : "";
        if (s->sh_type == SHT_DYNSYM && strcmp(name, ".dynsym") == 0) {
            dynsym = malloc(s->sh_size);
            if (dynsym && read_at(f, (long)s->sh_offset, dynsym, s->sh_size) == 0)
                dynsym_count = s->sh_size / sizeof(Elf64_Sym);
        } else if (strcmp(name, ".dynstr") == 0) {
            dynstr = malloc(s->sh_size);
            if (dynstr && read_at(f, (long)s->sh_offset, (void *)dynstr, s->sh_size) == 0)
                dynstr_size = s->sh_size;
        }
    }
    free((void *)shstr);

    if (!dynsym || !dynstr || dynsym_count == 0) {
        fprintf(stderr, ".dynsym/.dynstr not found in %s\n", path);
        fclose(f);
        return 1;
    }

    const char *want[2] = {"gst_plugin_quinn_get_desc", "gst_plugin_quinn_register"};
    int found[2] = {0, 0};
    for (size_t i = 0; i < dynsym_count; i++) {
        Elf64_Sym *sym = &dynsym[i];
        if (sym->st_shndx == SHN_UNDEF || sym->st_name >= dynstr_size)
            continue;
        const char *nm = dynstr + sym->st_name;
        for (int k = 0; k < 2; k++) {
            if (strcmp(nm, want[k]) == 0) {
                found[k] = 1;
                printf("  exported: %s\n", nm);
            }
        }
    }
    free(dynsym);
    free((void *)dynstr);
    fclose(f);

    if (!found[0] || !found[1]) {
        fprintf(stderr,
                "FAIL: plugin entry symbols missing (get_desc=%d register=%d)\n",
                found[0], found[1]);
        return 1;
    }

    printf("OK: %s is aarch64 .so exporting gst_plugin_quinn_get_desc + gst_plugin_quinn_register\n",
           path);
    return 0;
}
