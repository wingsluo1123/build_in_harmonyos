/*
 * test.c — bison test_package smoke test.
 *
 * bison is a command-line tool (not a library), so this test verifies the
 * bison binary is callable and can parse a minimal grammar. We invoke it
 * via system() with the grammar on stdin and check the generated parser
 * source is non-empty.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>

static int run_cmd(const char *cmd) {
    int ret = system(cmd);
    if (ret == -1) return -1;
    return WIFEXITED(ret) && WEXITSTATUS(ret) == 0 ? 0 : -1;
}

static int file_exists(const char *path) {
    struct stat st;
    return stat(path, &st) == 0 && st.st_size > 0 ? 0 : -1;
}

int main(void) {
    /* Path to the generated parser output (in TMPDIR or cwd). */
    const char *out_path = "test_y.tab.c";
    char cmd[1024];

    /* Run bison on a minimal grammar, writing parser to out_path. */
    snprintf(cmd, sizeof(cmd),
             "bison -o %s <<'EOF'\n"
             "%%\n"
             "start: ;\n"
             "%%%%\n"
             "EOF",
             out_path);

    if (run_cmd(cmd) != 0) {
        fprintf(stderr, "FAIL: bison invocation returned non-zero exit\n");
        return 1;
    }

    if (file_exists(out_path) != 0) {
        fprintf(stderr, "FAIL: bison did not generate %s\n", out_path);
        return 1;
    }

    printf("PASS: bison generated parser source %s\n", out_path);
    return 0;
}
