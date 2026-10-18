/* OHOS-specific port test for xcb-util 0.4.1 (runs without an X server).
 *
 * Asserts the platform differences this adaptation introduces/configures on
 * OHOS, beyond what the generic consumer test covers:
 *
 *   1. The OHOS toolchain guard __OHOS__ is actually active for this build,
 *      so any OHOS-conditional code path in the chain is the one compiled.
 *   2. The loaded library is the libtool versioned soname libxcb-util.so.1
 *      (version-info 1:0:0), located through the loader's own bookkeeping
 *      (dl_iterate_phdr). The OHOS loader ignores DT_RUNPATH, so consumers
 *      resolve the library only through LD_LIBRARY_PATH + DT_NEEDED, making
 *      the soname spelling load-bearing.
 *   3. Link closure sanity of the shipped library: its ELF DT_NEEDED entries
 *      are parsed from the file on disk and must (a) name the direct
 *      dependency libxcb.so.1 — the dependency wired through the recipe's
 *      explicit -L/-Wl,-rpath-link closure (implement-policy item 5) — and
 *      (b) be bare sonames only, never absolute or ../ paths (the L5b rule;
 *      on OHOS a path-shaped NEEDED cannot be resolved via LD_LIBRARY_PATH).
 *      The full transitive set is toolchain-owned (lld records the transitive
 *      DT_NEEDED of libxcb itself: libXau/libXdmcp/libc — same as the
 *      xcb-util-wm/0.4.2 precedent), so it is deliberately not over-pinned.
 *   4. The dependency closes at runtime: libxcb.so.1 with xcb_connect is
 *      loadable through the same environment.
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif

#include <dlfcn.h>
#include <elf.h>
#include <link.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <xcb/xcb_util.h>

static int failures = 0;
static int assertions = 0;

static void expect(const char *what, int condition) {
    assertions++;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

static const char *path_basename(const char *path) {
    const char *slash = strrchr(path, '/');
    return slash ? slash + 1 : path;
}

/* dl_iterate_phdr callback: capture the load path of libxcb-util.so.1. */
static char lib_path[4096];

static int phdr_callback(struct dl_phdr_info *info, size_t size, void *data) {
    (void)size;
    (void)data;
    const char *name = info->dlpi_name ? info->dlpi_name : "";
    if (strcmp(path_basename(name), "libxcb-util.so.1") == 0 && name[0] != '\0') {
        snprintf(lib_path, sizeof(lib_path), "%s", name);
        return 1; /* stop iteration */
    }
    return 0;
}

/* Parse an ELF64 shared object and return the list of DT_NEEDED strings.
 * Returns a malloc'd array of malloc'd strings; *count receives the number
 * of entries. Returns NULL when the file cannot be parsed. */
static char **read_dt_needed(const char *path, int *count) {
    FILE *f = fopen(path, "rb");
    unsigned char *buf = NULL;
    long len;
    char **needed = NULL;
    int n = 0;
    *count = 0;
    if (!f) {
        return NULL;
    }
    if (fseek(f, 0, SEEK_END) != 0 || (len = ftell(f)) < 0 ||
        fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        return NULL;
    }
    buf = malloc((size_t)len);
    if (!buf || fread(buf, 1, (size_t)len, f) != (size_t)len) {
        free(buf);
        fclose(f);
        return NULL;
    }
    fclose(f);

    do {
        const Elf64_Ehdr *eh = (const Elf64_Ehdr *)buf;
        const Elf64_Phdr *ph;
        const Elf64_Dyn *dyn = NULL;
        size_t dyn_count = 0;
        Elf64_Addr strtab_vaddr = 0;
        int i, j;
        int n_phdr;

        if (len < (long)sizeof(Elf64_Ehdr) ||
            memcmp(eh->e_ident, ELFMAG, SELFMAG) != 0 ||
            eh->e_ident[EI_CLASS] != ELFCLASS64 ||
            eh->e_ident[EI_DATA] != ELFDATA2LSB) {
            break;
        }

        n_phdr = eh->e_phnum;
        if (len < (long)(eh->e_phoff + (size_t)n_phdr * sizeof(Elf64_Phdr))) {
            break;
        }
        ph = (const Elf64_Phdr *)(buf + eh->e_phoff);
        for (i = 0; i < n_phdr; i++) {
            if (ph[i].p_type == PT_DYNAMIC) {
                if (len < (long)(ph[i].p_offset + ph[i].p_filesz)) {
                    break;
                }
                dyn = (const Elf64_Dyn *)(buf + ph[i].p_offset);
                dyn_count = ph[i].p_filesz / sizeof(Elf64_Dyn);
            }
        }
        if (!dyn) {
            break;
        }
        for (j = 0; (size_t)j < dyn_count && dyn[j].d_tag != DT_NULL; j++) {
            if (dyn[j].d_tag == DT_STRTAB) {
                strtab_vaddr = (Elf64_Addr)dyn[j].d_un.d_ptr;
            } else if (dyn[j].d_tag == DT_NEEDED) {
                n++;
            }
        }

        /* Translate the dynstr virtual address through PT_LOAD segments. */
        if (strtab_vaddr != 0) {
            const unsigned char *strtab_file = NULL;
            for (i = 0; i < n_phdr; i++) {
                if (ph[i].p_type == PT_LOAD &&
                    strtab_vaddr >= ph[i].p_vaddr &&
                    strtab_vaddr < ph[i].p_vaddr + ph[i].p_filesz) {
                    strtab_file = buf + (strtab_vaddr - ph[i].p_vaddr) + ph[i].p_offset;
                    break;
                }
            }
            if (strtab_file && n > 0) {
                needed = malloc((size_t)n * sizeof(char *));
                if (needed) {
                    int k = 0;
                    for (j = 0; (size_t)j < dyn_count && dyn[j].d_tag != DT_NULL; j++) {
                        if (dyn[j].d_tag == DT_NEEDED) {
                            const char *s =
                                (const char *)(strtab_file + dyn[j].d_un.d_val);
                            needed[k] = strdup(s);
                            if (!needed[k]) {
                                break;
                            }
                            k++;
                        }
                    }
                    *count = k;
                }
            }
        }
    } while (0);

    free(buf);
    return needed;
}

int main(void) {
    /* 1. The OHOS guard must be active on this toolchain. */
#if defined(__OHOS__)
    expect("__OHOS__ macro is defined on the OHOS toolchain", 1);
#else
    expect("__OHOS__ macro is defined on the OHOS toolchain", 0);
#endif

    /* 2. The library providing xcb_aux_* is loaded under the versioned
     *    soname libxcb-util.so.1, per the loader's own bookkeeping. */
    expect("libxcb-util.so.1 present in loaded modules (dl_iterate_phdr)",
           dl_iterate_phdr(phdr_callback, NULL) == 1 && lib_path[0] != '\0');
    if (lib_path[0] != '\0') {
        expect("loaded library path is a readable file",
               access(lib_path, R_OK) == 0);
    } else {
        expect("loaded library path is a readable file", 0);
    }

    /* 3. Link closure: direct dependency present, entries all bare sonames. */
    {
        int count = 0;
        int has_xcb = 0;
        int bad_paths = 0;
        char **needed = read_dt_needed(lib_path, &count);
        expect("DT_NEEDED list readable from loaded library", needed != NULL);
        if (needed) {
            int i;
            for (i = 0; i < count; i++) {
                if (strcmp(needed[i], "libxcb.so.1") == 0) {
                    has_xcb = 1;
                }
                if (needed[i][0] == '/' || strncmp(needed[i], "../", 3) == 0 ||
                    strchr(needed[i], '/') != NULL) {
                    bad_paths++;
                }
            }
            expect("DT_NEEDED contains direct dependency libxcb.so.1", has_xcb);
            expect("DT_NEEDED entries are all bare sonames (no absolute/.. paths)",
                   count > 0 && bad_paths == 0);
            for (i = 0; i < count; i++) {
                free(needed[i]);
            }
            free(needed);
        } else {
            expect("DT_NEEDED contains direct dependency libxcb.so.1", 0);
            expect("DT_NEEDED entries are all bare sonames (no absolute/.. paths)", 0);
        }
    }

    /* 4. The dependency closes at runtime through the same environment. */
    {
        void *xcb = dlopen("libxcb.so.1", RTLD_NOW);
        expect("libxcb.so.1 loadable at runtime (closure resolves)", xcb != NULL);
        if (xcb) {
            void *sym = dlsym(xcb, "xcb_connect");
            expect("xcb_connect reachable from libxcb.so.1", sym != NULL);
            dlclose(xcb);
        } else {
            expect("xcb_connect reachable from libxcb.so.1", 0);
        }
    }

    printf("xcb-util OHOS port test: assertions=%d failures=%d (lib=%s)\n",
           assertions, failures, lib_path[0] ? lib_path : "(not found)");
    return failures == 0 ? 0 : 1;
}
