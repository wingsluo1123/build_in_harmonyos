/* Consumer case 2: the packaged modsecurity.conf-recommended must be a
 * real, non-empty engine configuration — not an empty fixture that a
 * harness would happily "pass" over. Asserts the presence of core
 * directives and a minimum body size.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef MODSEC_CONF_PATH
#error "MODSEC_CONF_PATH is not defined"
#endif

#define MIN_CONF_BYTES 1024

static int contains(const char *haystack, const char *needle) {
    return strstr(haystack, needle) != NULL;
}

int main(void) {
    const char *path = MODSEC_CONF_PATH;
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
    if (size < MIN_CONF_BYTES) {
        fprintf(stderr, "FATAL: %s is only %ld bytes (<%d); refusing empty fixture\n",
                path, size, MIN_CONF_BYTES);
        fclose(file);
        return 1;
    }
    rewind(file);
    char *body = (char *)malloc((size_t)size + 1);
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
    body[size] = '\0';

    int ok = 1;
    if (!contains(body, "SecRuleEngine")) {
        fprintf(stderr, "FATAL: SecRuleEngine directive missing\n");
        ok = 0;
    }
    if (!contains(body, "SecRequestBodyAccess")) {
        fprintf(stderr, "FATAL: SecRequestBodyAccess directive missing\n");
        ok = 0;
    }
    if (!contains(body, "SecAuditEngine")
        && !contains(body, "SecAuditLog")) {
        fprintf(stderr, "FATAL: no audit directives found\n");
        ok = 0;
    }
    if (ok) {
        printf("conf_check: %s is %ld bytes with engine directives\n", path, size);
        printf("conf_check: PASS\n");
    }
    free(body);
    return ok ? 0 : 1;
}
