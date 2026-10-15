/*
 * HarmonyOS-specific runtime test #2 for kea 3.2.0.
 *
 * The package ships the whole Kea runtime: the libkea-* libraries and the
 * hook plug-ins (lib/kea/hooks/libdhcp_*.so) that the servers dlopen() at
 * run time.  What must work on HarmonyOS is not only their individual load
 * but the whole NEEDED closure they drag in.  glibc and bionic differ from
 * musl here (rpath handling, soname symlinks, libc++ runtime), so this
 * behaviour is platform specific.
 *
 * Checks
 *   1. every real libkea-*.so* file in <package>/lib loads with RTLD_NOW
 *   2. the count of distinct libkea-* base names is >= 20 (the packaged
 *      closure; soname copies would otherwise over-count plain files)
 *   3. every real hook plug-in in <package>/lib/kea/hooks loads with RTLD_NOW
 *   4. the count of hook plug-ins is >= 15 (dhcp hooks; the mysql/pgsql/krb5
 *      back-ends are disabled in the build configuration, see notes.md)
 *   5. the hook contract is importable: version()/load()/unload() symbols of
 *      libdhcp_ha.so resolve, and version() reports the Kea 3.2.0 hook ABI
 *      version 30200 (src/lib/hooks/hooks.h KEA_HOOKS_VERSION)
 *
 * Usage: test_ohos_runtime <package-lib-dir>
 * Exits non-zero on any failed check.
 */
#include <dirent.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define EXPECTED_MIN_KEA_LIBS 20
#define EXPECTED_MIN_HOOKS 15
#define EXPECTED_HOOKS_VERSION 30200
#define MAX_FILES 512
#define MAX_LIBS 128
#define LIBNAME_MAX 128

static int failures = 0;

static void check(int cond, const char *what) {
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        printf("FAIL - %s\n", what);
        failures++;
    }
    fflush(stdout);
}

static int is_kea_lib(const char *name) {
    return strncmp(name, "libkea-", 7) == 0 && strstr(name, ".so") != NULL;
}

static int is_hook_lib(const char *name) {
    return (strncmp(name, "libdhcp_", 8) == 0 ||
            strncmp(name, "libddns_", 8) == 0) &&
           strstr(name, ".so") != NULL;
}

/* Load every real (non-symlink) library matching the predicate in dirpath.
 * Returns the number of real files seen; *loaded_out receives the number of
 * successful dlopen()s and handles are appended to the caller's array. */
static int load_dir(const char *dirpath, int (*predicate)(const char *),
                    void *handles[], int *loaded_out, int max_handles,
                    char bases[][LIBNAME_MAX], int *nbases_out, int max_bases) {
    DIR *dir;
    struct dirent *entry;
    int nreal = 0;

    dir = opendir(dirpath);
    if (dir == NULL) {
        return -1;
    }

    while ((entry = readdir(dir)) != NULL) {
        char full[4096];
        struct stat st;
        void *handle;

        if (!predicate(entry->d_name)) {
            continue;
        }
        snprintf(full, sizeof(full), "%s/%s", dirpath, entry->d_name);
        if (lstat(full, &st) != 0) {
            continue;
        }
        if (S_ISLNK(st.st_mode)) {
            /* the soname symlinks are covered by loading the real file */
            continue;
        }
        /* check the cap before counting so nreal always matches nloaded */
        if (nreal >= max_handles) {
            break;
        }
        nreal++;
        /* Count the library base name once ("libkea-X.so.3" and
         * "libkea-X.so.3.0.3" are the same library).  OHOS denies symlinks,
         * so the package ships each soname as a real copy and the plain file
         * count alone could over-state the distinct closure. */
        {
            const char *socut = strstr(entry->d_name, ".so");
            if (socut != NULL && (socut - entry->d_name) < LIBNAME_MAX) {
                size_t blen = (size_t)(socut - entry->d_name);
                int seen = 0;
                int b;
                for (b = 0; b < *nbases_out; ++b) {
                    if (strlen(bases[b]) == blen &&
                        strncmp(bases[b], entry->d_name, blen) == 0) {
                        seen = 1;
                        break;
                    }
                }
                if (!seen && *nbases_out < max_bases) {
                    memcpy(bases[*nbases_out], entry->d_name, blen);
                    bases[*nbases_out][blen] = '\0';
                    (*nbases_out)++;
                }
            }
        }
        handle = dlopen(full, RTLD_NOW | RTLD_LOCAL);
        if (handle != NULL) {
            printf("ok   - OHOS loader dlopen(RTLD_NOW): %s\n", entry->d_name);
            handles[(*loaded_out)++] = handle;
        } else {
            printf("FAIL - OHOS loader dlopen(RTLD_NOW): %s -> %s\n",
                   entry->d_name, dlerror());
            failures++;
        }
    }
    closedir(dir);
    return nreal;
}

int main(int argc, char **argv) {
    char hooksdir[4096], hookpath[4096], hooksdir_buf[4096];
    const char *libdir;
    int nreal, nloaded = 0, i;
    int hreal, hloaded = 0;
    void *handles[MAX_FILES];
    void *hook;
    /* distinct "libkea-X" / hook base names seen (the ".so*" suffix dropped) */
    static char bases[MAX_LIBS][LIBNAME_MAX];
    static char hook_bases[MAX_LIBS][LIBNAME_MAX];
    int nbases = 0, nhook_bases = 0;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <package-lib-dir>\n", argv[0]);
        return 2;
    }
    libdir = argv[1];
    printf("info - packaged Kea runtime lib dir: %s\n", libdir);

    /* Kea runtime libraries in <pkg>/lib. */
    nreal = load_dir(libdir, is_kea_lib, handles, &nloaded, MAX_FILES,
                     bases, &nbases, MAX_LIBS);
    if (nreal < 0) {
        perror("opendir lib");
        return 2;
    }
    check(nbases >= EXPECTED_MIN_KEA_LIBS,
          "packaged Kea runtime closure present (>= 20 distinct libraries)");
    check(nloaded == nreal,
          "every packaged Kea runtime library loads under the OHOS loader");
    printf("info - Kea runtime libraries: %d distinct, %d files, %d loaded\n",
           nbases, nreal, nloaded);

    /* Hook plug-ins in <pkg>/lib/kea/hooks.  The handles are appended after
     * the library handles (base + nloaded) so the dlclose() loop below
     * covers exactly the slots that were initialized. */
    snprintf(hooksdir_buf, sizeof(hooksdir_buf), "%s/kea/hooks", libdir);
    snprintf(hooksdir, sizeof(hooksdir), "%s", hooksdir_buf);
    hreal = load_dir(hooksdir, is_hook_lib, handles + nloaded, &hloaded, MAX_FILES - nloaded,
                     hook_bases, &nhook_bases, MAX_LIBS);
    if (hreal < 0) {
        printf("FAIL - cannot open packaged hooks dir %s\n", hooksdir);
        failures++;
    } else {
        check(nhook_bases >= EXPECTED_MIN_HOOKS,
              "packaged hook plug-ins present (>= 15 distinct hooks)");
        check(hloaded == hreal,
              "every packaged hook plug-in loads under the OHOS loader");
        printf("info - hook plug-ins: %d distinct, %d files, %d loaded\n",
               nhook_bases, hreal, hloaded);
    }

    /* Hook contract: the HA hook is the family flagship and must always be
     * present; version() reports the KEA_HOOKS_VERSION the libs were built
     * with (30200 for Kea 3.2.0). */
    snprintf(hookpath, sizeof(hookpath), "%s/libdhcp_ha.so", hooksdir);
    hook = dlopen(hookpath, RTLD_NOW | RTLD_LOCAL);
    check(hook != NULL, "libdhcp_ha.so loads for the hook contract check");
    if (hook != NULL) {
        int (*hook_version)(void) = NULL;
        *(void **)(&hook_version) = dlsym(hook, "version");
        check(hook_version != NULL, "hook contract symbol version() resolvable");
        if (hook_version != NULL) {
            int version = hook_version();
            printf("info - libdhcp_ha.so reports KEA_HOOKS_VERSION %d\n", version);
            check(version == EXPECTED_HOOKS_VERSION,
                  "hook ABI version is 30200 (Kea 3.2.0)");
        }
        check(dlsym(hook, "load") != NULL && dlsym(hook, "unload") != NULL,
              "hook contract symbols load/unload resolvable at runtime");
        dlclose(hook);
    } else {
        fprintf(stderr, "dlopen(%s) failed: %s\n", hookpath, dlerror());
    }

    /* Release the closure handles so every dlopen() is paired with a
     * dlclose() (the process is short-lived, but keep the pairing complete). */
    for (i = 0; i < nloaded + hloaded; ++i) {
        dlclose(handles[i]);
    }

    if (failures == 0) {
        printf("kea/3.2.0 OHOS runtime closure check OK\n");
        return 0;
    }
    printf("kea/3.2.0 OHOS runtime closure check FAILED (%d check(s))\n",
           failures);
    return 1;
}
