/*
 * Consumer test for the nfdump package.
 *
 * It exercises what the package installs: the five command line tools are
 * executed and their output is checked, and the shipped libraries, the
 * default configuration file and the man pages are verified to be in place.
 *
 * Every step prints its own PASS/FAIL line and the process exits non zero as
 * soon as one step failed; no assertion is used.
 */
#define _GNU_SOURCE

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>

#define VERSION_STRING "1.7.6"

static int g_failures = 0;

static int check(int ok, const char *description) {
    printf("  %-4s %s\n", ok ? "PASS" : "FAIL", description);
    if (!ok) g_failures++;

    return ok;

}  // End of check

static void note(const char *format, ...) {
    va_list args;

    va_start(args, format);
    printf("  info ");
    vprintf(format, args);
    printf("\n");
    va_end(args);

}  // End of note

static long file_size(const char *path) {
    struct stat st;

    if (stat(path, &st) != 0) return -1;

    return (long)st.st_size;

}  // End of file_size

// Run a command and collect its combined output. Returns the exit status of
// the command, or -1 when it could not be started.
static int run_command(const char *command, char *buffer, size_t buffer_size) {
    FILE *pipe;
    int status;
    size_t used = 0;

    buffer[0] = '\0';

    pipe = popen(command, "r");
    if (pipe == NULL) return -1;

    while (used + 1 < buffer_size) {
        size_t got = fread(buffer + used, 1, buffer_size - 1 - used, pipe);
        used += got;
        if (got == 0) break;
    }
    buffer[used] = '\0';

    status = pclose(pipe);
    if (status == -1) return -1;
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);

    return -1;

}  // End of run_command

// Execute one of the packaged tools and check that the output mentions what
// the caller expects.
static void check_tool(const char *bindir, const char *tool, const char *option, const char *expected) {
    char command[2048];
    char output[16384];
    int status;

    snprintf(command, sizeof(command), "\"%s/%s\" %s 2>&1", bindir, tool, option);
    status = run_command(command, output, sizeof(output));

    char description[256];
    snprintf(description, sizeof(description), "%s %s runs and reports '%s'", tool, option, expected);

    if (status != 0) {
        check(0, description);
        note("%s %s exited with %d", tool, option, status);
        return;
    }

    if (strstr(output, expected) == NULL) {
        check(0, description);
        note("%s %s printed: %s", tool, option, output);
        return;
    }

    check(1, description);

}  // End of check_tool

int main(int argc, char **argv) {
    const char *package_folder;
    char bindir[1024];
    char path[1200];

    printf("=== nfdump consumer test ===\n");

    if (argc < 2) {
        printf("usage: %s <package folder>\n", argv[0]);
        return 2;
    }
    package_folder = argv[1];
    snprintf(bindir, sizeof(bindir), "%s/bin", package_folder);

    printf("[1] command line tools\n");
    // nfdump, nfcapd and nfreplay all answer -V; nfanon and nfexpire only
    // document their options, so -h is used for those two.
    check_tool(bindir, "nfdump", "-V", VERSION_STRING);
    check_tool(bindir, "nfcapd", "-V", VERSION_STRING);
    check_tool(bindir, "nfreplay", "-V", VERSION_STRING);
    check_tool(bindir, "nfanon", "-h", "usage");
    check_tool(bindir, "nfexpire", "-h", "usage");

    printf("[2] installed libraries, configuration and manual pages\n");
    const char *libraries[] = {"libnfdump.a", "libnffile.a"};
    for (unsigned int i = 0; i < sizeof(libraries) / sizeof(libraries[0]); i++) {
        snprintf(path, sizeof(path), "%s/lib/%s", package_folder, libraries[i]);
        char description[256];
        snprintf(description, sizeof(description), "lib/%s is installed and not empty (%ld bytes)", libraries[i], file_size(path));
        check(file_size(path) > 0, description);
    }

    snprintf(path, sizeof(path), "%s/etc/nfdump.conf.dist", package_folder);
    check(file_size(path) > 0, "etc/nfdump.conf.dist is installed");

    const char *pages[] = {"nfanon.1", "nfcapd.1", "nfdump.1", "nfexpire.1", "nfreplay.1"};
    for (unsigned int i = 0; i < sizeof(pages) / sizeof(pages[0]); i++) {
        snprintf(path, sizeof(path), "%s/share/man/man1/%s", package_folder, pages[i]);
        char description[256];
        snprintf(description, sizeof(description), "share/man/man1/%s is installed", pages[i]);
        check(file_size(path) > 0, description);
    }

    printf("\n");
    if (g_failures > 0) {
        printf("=== %d check(s) failed ===\n", g_failures);
        return 1;
    }
    printf("=== nfdump consumer test PASSED ===\n");

    return 0;

}  // End of main
