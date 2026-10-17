/*
 * imagination_consumer_test.c — installed-package consumer test.
 *
 * Usage: imagination_consumer_test <plugin-dir> <imagination-binary>
 *
 * 4 test cases:
 *   1. packaged-binary contract (genuine aarch64 ELF, executable)
 *   2. transition-plugin inventory: all 15 packaged GModule plugins
 *      dlopen cleanly on the OHOS loader
 *   3. plugin API contract: img_get_plugin_info() resolves per plugin,
 *      returns a non-empty group and a NULL-terminated name/symbol/id
 *      triplet array whose advertised render symbols all resolve
 *   4. headless entrypoint smoke: the binary resolves its whole GTK+3
 *      shared-library closure and stops exactly at GTK display
 *      initialisation (no dynamic-link failure), the furthest a GUI
 *      binary can be asserted on a headless device (l3afpad precedent)
 */
#include <ctype.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; return 1; } \
    printf("PASS: %s\n", msg); \
} while (0)

static void lowercase(char *s)
{
    for (; *s; s++)
        *s = (char)tolower((unsigned char)*s);
}

/* ---- 1. packaged binary contract ---- */
static int check_binary(const char *binary)
{
    FILE *f;
    unsigned char head[20];
    unsigned short machine;

    f = fopen(binary, "rb");
    CHECK(f != NULL, "case1: bin/imagination exists and is readable");
    CHECK(fread(head, 1, 20, f) == 20, "case1: binary header is at least 20 bytes");
    fclose(f);

    CHECK(head[0] == 0x7f && head[1] == 'E' && head[2] == 'L' && head[3] == 'F',
          "case1: packaged binary is an ELF file");
    CHECK(head[4] == 2, "case1: ELF class is 64-bit");
    machine = (unsigned short)head[18] | ((unsigned short)head[19] << 8);
    CHECK(machine == 0xB7, "case1: ELF e_machine is aarch64 (EM_AARCH64)");
    CHECK(access(binary, X_OK) == 0, "case1: binary is executable");
    return 0;
}

/* ---- 2 + 3. plugin inventory & API contract ---- */
typedef void (*plugin_info_fn)(char **group, char ***trans);

static int check_plugins(const char *plugin_dir)
{
    static const char *expected[] = {
        "bar_wipe", "barn_door_wipe", "bow_tie_wipe", "box_wipe",
        "clock_wipe", "diagonal_wipe", "ellipse_wipe", "four_box_wipe",
        "insert", "misc", "misc_diagonal_wipe", "misc_shape_wipe",
        "push_wipe", "rochade", "wave",
    };
    const size_t expected_count = sizeof(expected) / sizeof(expected[0]);
    size_t found = 0, i;

    for (i = 0; i < expected_count; i++) {
        char path[4096];
        void *handle;
        plugin_info_fn info;
        char *group = NULL;
        char **trans = NULL;
        size_t triplets = 0, t;

        snprintf(path, sizeof(path), "%s/%s.so", plugin_dir, expected[i]);
        CHECK(access(path, R_OK) == 0, "case2: packaged plugin file present");

        handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
        if (handle == NULL) {
            fprintf(stderr, "FAIL: case2: dlopen(%s): %s\n", path, dlerror());
            failures++;
            return 1;
        }
        printf("PASS: case2: dlopen %s\n", expected[i]);

        info = (plugin_info_fn)dlsym(handle, "img_get_plugin_info");
        if (info == NULL) {
            fprintf(stderr, "FAIL: case3: dlsym(img_get_plugin_info) in %s: %s\n",
                    expected[i], dlerror());
            failures++;
            dlclose(handle);
            return 1;
        }
        printf("PASS: case3: img_get_plugin_info resolves in %s\n", expected[i]);

        info(&group, &trans);
        if (trans == NULL || group == NULL || group[0] == '\0') {
            fprintf(stderr, "FAIL: case3: %s returned empty group/array\n",
                    expected[i]);
            failures++;
            dlclose(handle);
            return 1;
        }
        printf("PASS: case3: %s advertises group \"%s\"\n", expected[i], group);

        /* Termination semantics mirror the app's own loader (support.c:
         * "for (bak = trans; *trans; trans += 3)") - the name slot is the
         * terminator; ids may legitimately be GINT_TO_POINTER(0) == NULL. */
        for (t = 0; trans[t] != NULL; t += 3) {
            if (trans[t + 1] == NULL) {
                fprintf(stderr, "FAIL: case3: %s: symbol slot NULL at %zu\n",
                        expected[i], t + 1);
                failures++;
                dlclose(handle);
                return 1;
            }
            if (dlsym(handle, trans[t + 1]) == NULL) {
                fprintf(stderr, "FAIL: case3: %s advertises unresolved symbol %s\n",
                        expected[i], trans[t + 1]);
                failures++;
                dlclose(handle);
                return 1;
            }
            triplets++;
        }
        CHECK(triplets > 0, "case3: plugin triplet array is non-empty");
        printf("INFO: case3: %s exports %zu transition(s)\n",
               expected[i], triplets);

        dlclose(handle);
        found++;
    }
    CHECK(found == expected_count,
          "case2: all 15 upstream transition plugins are packaged");
    return 0;
}

/* ---- 4. headless entrypoint smoke ---- */
static int check_headless_run(const char *binary)
{
    int out_fd[2];
    pid_t pid;
    char buf[8192];
    size_t total = 0;
    ssize_t n;
    int status, wret;
    char *low;

    CHECK(pipe(out_fd) == 0, "case4: output pipe created");

    /* Deterministic headless behaviour regardless of the ambient session. */
    unsetenv("DISPLAY");
    unsetenv("WAYLAND_DISPLAY");

    pid = fork();
    CHECK(pid >= 0, "case4: fork succeeded");
    if (pid == 0) {
        char *argv[2];
        dup2(out_fd[1], STDOUT_FILENO);
        dup2(out_fd[1], STDERR_FILENO);
        close(out_fd[0]);
        close(out_fd[1]);
        argv[0] = (char *)binary;
        argv[1] = NULL;
        execv(binary, argv);
        _exit(127);
    }
    close(out_fd[1]);
    while (total < sizeof(buf) - 1 &&
           (n = read(out_fd[0], buf + total, sizeof(buf) - 1 - total)) > 0)
        total += (size_t)n;
    close(out_fd[0]);
    buf[total] = '\0';

    wret = waitpid(pid, &status, 0);
    CHECK(wret == pid, "case4: child was reaped");
    CHECK(WIFEXITED(status), "case4: child exited normally (no signal)");
    CHECK(WEXITSTATUS(status) != 0, "case4: child exited non-zero as expected");

    low = strdup(buf);
    CHECK(low != NULL, "case4: output captured");
    lowercase(low);

    CHECK(strstr(low, "error loading shared library") == NULL,
          "case4: no dynamic-link failure in GTK closure");
    CHECK(strstr(low, "symbol not found") == NULL,
          "case4: no unresolved symbol in GTK closure");
    CHECK(strstr(low, "error while loading shared libraries") == NULL,
          "case4: no loader error in GTK closure");
    CHECK(strstr(low, "undefined symbol") == NULL,
          "case4: no undefined symbol in GTK closure");
    CHECK(strstr(low, "open display") != NULL,
          "case4: execution reached GTK display init (expected headless stop)");
    free(low);
    return 0;
}

int main(int argc, char **argv)
{
    const char *plugin_dir, *binary;

    if (argc != 3) {
        fprintf(stderr, "usage: %s <plugin-dir> <imagination-binary>\n", argv[0]);
        return 2;
    }
    plugin_dir = argv[1];
    binary = argv[2];

    if (check_binary(binary) != 0)
        return 1;
    if (check_plugins(plugin_dir) != 0)
        return 1;
    if (check_headless_run(binary) != 0)
        return 1;

    if (failures > 0) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("IMAGINATION-CONSUMER-OK\n");
    return 0;
}
