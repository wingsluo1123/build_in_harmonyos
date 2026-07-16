#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <regex.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef PROCTOOLS_NAME
#define PROCTOOLS_NAME "pgrep"
#endif

#define VERSION "0.4pre1"

static int numeric_name(const char *name) {
    if (!name || !*name) return 0;
    for (; *name; ++name) if (!isdigit((unsigned char)*name)) return 0;
    return 1;
}

static int read_text(const char *path, char *buffer, size_t size) {
    FILE *file = fopen(path, "r");
    size_t used;
    if (!file) return -1;
    used = fread(buffer, 1, size - 1, file);
    fclose(file);
    buffer[used] = '\0';
    while (used && (buffer[used - 1] == '\n' || buffer[used - 1] == '\r'))
        buffer[--used] = '\0';
    return 0;
}

static int process_text(pid_t pid, int full, char *buffer, size_t size) {
    char path[64];
    if (full) {
        FILE *file;
        size_t used;
        snprintf(path, sizeof(path), "/proc/%d/cmdline", (int)pid);
        file = fopen(path, "r");
        if (!file) return -1;
        used = fread(buffer, 1, size - 1, file);
        fclose(file);
        buffer[used] = '\0';
        for (size_t i = 0; i < used; ++i) if (buffer[i] == '\0') buffer[i] = ' ';
        while (used && buffer[used - 1] == ' ') buffer[--used] = '\0';
        return used ? 0 : -1;
    }
    snprintf(path, sizeof(path), "/proc/%d/comm", (int)pid);
    return read_text(path, buffer, size);
}

static void usage(void) {
    fprintf(stderr, "Usage: %s [-flnvxV] [-d delimiter] [-s signal] pattern\n", PROCTOOLS_NAME);
    exit(64);
}

int main(int argc, char **argv) {
    int full = 0, long_output = 0, newest = 0, invert = 0, exact = 0;
    int signal_number = SIGTERM, option, found = 0;
    char *delimiter = "\n";
    const char *pattern;
    DIR *proc;
    struct dirent *entry;
    regex_t regex;
    pid_t newest_pid = -1;
    char newest_text[4096] = {0};

    while ((option = getopt(argc, argv, "d:flnvs:xV")) != -1) {
        switch (option) {
        case 'd': delimiter = optarg; break;
        case 'f': full = 1; break;
        case 'l': long_output = 1; break;
        case 'n': newest = 1; break;
        case 'v': invert = 1; break;
        case 's': signal_number = atoi(optarg); break;
        case 'x': exact = 1; break;
        case 'V':
            printf("%s (proctools %s) %s\n", PROCTOOLS_NAME, VERSION,
                   "https://proctools.sourceforge.net");
            return 0;
        default: usage();
        }
    }
    if (optind >= argc) usage();
    pattern = argv[optind];
    if (!exact && regcomp(&regex, pattern, REG_EXTENDED | REG_NOSUB) != 0) return 2;
    proc = opendir("/proc");
    if (!proc) return 2;

    while ((entry = readdir(proc)) != NULL) {
        pid_t pid;
        char text[4096];
        int matched;
        if (!numeric_name(entry->d_name)) continue;
        pid = (pid_t)strtol(entry->d_name, NULL, 10);
        if (pid == getpid() || process_text(pid, full, text, sizeof(text)) != 0) continue;
        matched = exact ? strcmp(text, pattern) == 0 : regexec(&regex, text, 0, NULL, 0) == 0;
        if (invert) matched = !matched;
        if (!matched) continue;
        if (newest) {
            if (pid > newest_pid) {
                newest_pid = pid;
                snprintf(newest_text, sizeof(newest_text), "%s", text);
            }
            continue;
        }
        if (strcmp(PROCTOOLS_NAME, "pkill") == 0) {
            if (kill(pid, signal_number) == 0) found = 1;
        } else {
            if (found) fputs(delimiter, stdout);
            printf("%d", (int)pid);
            if (long_output || strcmp(PROCTOOLS_NAME, "pfind") == 0) printf(" %s", text);
            found = 1;
        }
    }
    closedir(proc);
    if (!exact) regfree(&regex);

    if (newest && newest_pid > 0) {
        if (strcmp(PROCTOOLS_NAME, "pkill") == 0)
            found = kill(newest_pid, signal_number) == 0;
        else {
            printf("%d", (int)newest_pid);
            if (long_output || strcmp(PROCTOOLS_NAME, "pfind") == 0) printf(" %s", newest_text);
            found = 1;
        }
    }
    if (found && strcmp(PROCTOOLS_NAME, "pkill") != 0) putchar('\n');
    return found ? 0 : 1;
}
