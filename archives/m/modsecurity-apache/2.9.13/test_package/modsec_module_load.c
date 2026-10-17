/* Consumer case 1: the packaged Apache module must be a genuine,
 * loadable Apache DSO exposing the security2_module entry.
 *
 * Why no dlopen() here: mod_security2.so is an Apache loadable module
 * whose ap_* symbols (e.g. ap_log_perror_) are provided by the httpd
 * host process at server runtime (upstream links it with
 * -no-undefined -module on Linux, leaving httpd symbols undefined).
 * HarmonyOS uses musl libc, which resolves ALL relocations eagerly at
 * dlopen time (BIND_NOW semantics; RTLD_LAZY is effectively ignored),
 * so a standalone dlopen() without a running httpd host always fails
 * with "ap_log_perror_: symbol not found" -- even for a perfectly good
 * module (preflight 2026-10-16 evidence). That failure proves nothing
 * about packaging quality. Instead this case statically verifies the
 * packaged artifact (dragonfly-reverb LV2 precedent: nm -D symbol check
 * for host-loaded plugins):
 *   1. file exists, is a 32/64-bit ELF shared object (ET_DYN), non-empty
 *      (toybox-tar lesson: refuse empty fixtures);
 *   2. dynamic symbol table exports the "security2_module" entry
 *      (via llvm-nm/nm -D when available, else dynstr substring proof);
 *   3. the image references the httpd host import "ap_log_perror"
 *      (proves it is the genuine httpd-bound module, not a stub .so).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef MODSEC_MODULE_PATH
#error "MODSEC_MODULE_PATH is not defined"
#endif

#define MIN_MODULE_BYTES 32768

static int has_substring(const unsigned char *hay, size_t hay_len,
                         const char *needle) {
    size_t nlen = strlen(needle);
    if (nlen == 0 || hay_len < nlen) {
        return 0;
    }
    for (size_t i = 0; i + nlen <= hay_len; i++) {
        if (memcmp(hay + i, needle, nlen) == 0) {
            return 1;
        }
    }
    return 0;
}

/* Try "nm -D <path>" with the first available nm binary. Returns:
 *  1 = nm ran and "security2_module" is listed as a DEFINED symbol,
 *  0 = nm ran but no defined entry found,
 * -1 = no nm binary available (caller falls back to dynstr proof). */
static int nm_defines_entry(const char *path, char *used_nm, size_t used_len) {
    static const char *candidates[] = {
        "/data/service/hnp/bin/llvm-nm",
        "llvm-nm",
        "nm",
        NULL
    };
    for (int c = 0; candidates[c] != NULL; c++) {
        char cmd[4096];
        /* "command -v" probe avoids noisy stderr when the name is absent. */
        if (candidates[c][0] != '/') {
            char probe[256];
            snprintf(probe, sizeof(probe), "command -v %s >/dev/null 2>&1",
                     candidates[c]);
            if (system(probe) != 0) {
                continue;
            }
        } else {
            FILE *ex = fopen(candidates[c], "rb");
            if (ex == NULL) {
                continue;
            }
            fclose(ex);
        }
        snprintf(cmd, sizeof(cmd), "\"%s\" -D \"%s\" 2>/dev/null",
                 candidates[c], path);
        FILE *pipe = popen(cmd, "r");
        if (pipe == NULL) {
            continue;
        }
        snprintf(used_nm, used_len, "%s", candidates[c]);
        char line[1024];
        int found_defined = 0;
        int ran = 0;
        while (fgets(line, sizeof(line), pipe) != NULL) {
            ran = 1;
            if (strstr(line, "security2_module") != NULL) {
                /* nm -D rows look like "00000000 D security2_module".
                 * Undefined rows show " U <name>"; only a non-U row
                 * counts as a defined export. */
                char *u = strstr(line, " U ");
                char *w = strstr(line, " w ");
                if (u == NULL && w == NULL) {
                    found_defined = 1;
                }
            }
        }
        int rc = pclose(pipe);
        (void)rc;
        if (!ran) {
            continue;
        }
        return found_defined ? 1 : 0;
    }
    return -1;
}

int main(void) {
    const char *path = MODSEC_MODULE_PATH;
    FILE *file = fopen(path, "rb");
    if (file == NULL) {
        fprintf(stderr, "FATAL: cannot open %s\n", path);
        return 1;
    }
    if (fseek(file, 0, SEEK_END) != 0) {
        fprintf(stderr, "FATAL: cannot seek %s\n", path);
        fclose(file);
        return 1;
    }
    long size = ftell(file);
    if (size < MIN_MODULE_BYTES) {
        fprintf(stderr,
                "FATAL: %s is only %ld bytes (<%d); refusing empty fixture\n",
                path, size, MIN_MODULE_BYTES);
        fclose(file);
        return 1;
    }
    rewind(file);
    unsigned char *body = (unsigned char *)malloc((size_t)size);
    if (body == NULL) {
        fprintf(stderr, "FATAL: out of memory\n");
        fclose(file);
        return 1;
    }
    size_t got = fread(body, 1, (size_t)size, file);
    fclose(file);
    if ((long)got != size) {
        fprintf(stderr, "FATAL: short read on %s\n", path);
        free(body);
        return 1;
    }

    /* ELF header: magic + class + ET_DYN. */
    if (size < 18 || body[0] != 0x7f || body[1] != 'E' ||
        body[2] != 'L' || body[3] != 'F') {
        fprintf(stderr, "FATAL: %s has no ELF magic\n", path);
        free(body);
        return 1;
    }
    if (body[4] != 1 && body[4] != 2) {
        fprintf(stderr, "FATAL: %s has unknown ELF class %d\n", path, body[4]);
        free(body);
        return 1;
    }
    /* e_type is u16le at offset 16; ET_DYN == 3. */
    unsigned etype = (unsigned)body[16] | ((unsigned)body[17] << 8);
    if (etype != 3) {
        fprintf(stderr, "FATAL: %s is not a shared object (e_type=%u)\n",
                path, etype);
        free(body);
        return 1;
    }

    if (!has_substring(body, (size_t)size, "security2_module")) {
        fprintf(stderr,
                "FATAL: security2_module entry string missing in %s\n", path);
        free(body);
        return 1;
    }
    if (!has_substring(body, (size_t)size, "ap_log_perror")) {
        fprintf(stderr,
                "FATAL: httpd host import ap_log_perror missing in %s "
                "(not the genuine httpd-bound module?)\n", path);
        free(body);
        return 1;
    }

    char used_nm[256] = {0};
    int nm = nm_defines_entry(path, used_nm, sizeof(used_nm));
    if (nm == 0) {
        fprintf(stderr,
                "FATAL: %s lists no DEFINED security2_module in nm -D (%s)\n",
                path, used_nm);
        free(body);
        return 1;
    }

    printf("module_load: %s is %ld bytes, ELF ET_DYN class %d\n",
           path, size, body[4]);
    printf("module_load: security2_module entry present, "
           "httpd import ap_log_perror present\n");
    if (nm == 1) {
        printf("module_load: nm -D (%s) confirms DEFINED security2_module\n",
               used_nm);
    } else {
        printf("module_load: nm unavailable, dynstr substring proof used\n");
    }
    printf("module_load: PASS (musl BIND_NOW: no standalone dlopen; "
           "httpd symbols resolve at server runtime)\n");
    free(body);
    return 0;
}
