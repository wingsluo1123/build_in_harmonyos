#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <limits.h>
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
    if (ferror(file)) {
        fclose(file);
        return -1;
    }
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
        if (ferror(file)) {
            fclose(file);
            return -1;
        }
        fclose(file);
        buffer[used] = '\0';
        for (size_t i = 0; i < used; ++i) if (buffer[i] == '\0') buffer[i] = ' ';
        while (used && buffer[used - 1] == ' ') buffer[--used] = '\0';
        return used ? 0 : -1;
    }
    snprintf(path, sizeof(path), "/proc/%d/comm", (int)pid);
    return read_text(path, buffer, size);
}

static int process_start_time(pid_t pid, unsigned long long *start_time) {
    char path[64];
    char stat_line[4096];
    char *field;
    char *saveptr = NULL;
    char *end;
    int field_number;

    snprintf(path, sizeof(path), "/proc/%d/stat", (int)pid);
    if (read_text(path, stat_line, sizeof(stat_line)) != 0) return -1;

    /* The command name is parenthesized and may contain spaces. */
    field = strrchr(stat_line, ')');
    if (!field) return -1;
    field = strtok_r(field + 1, " ", &saveptr);
    for (field_number = 3; field && field_number < 22; ++field_number)
        field = strtok_r(NULL, " ", &saveptr);
    if (!field) return -1;

    errno = 0;
    *start_time = strtoull(field, &end, 10);
    if (errno == ERANGE || end == field || *end != '\0') return -1;
    return 0;
}

static void usage(void) {
    fprintf(stderr, "Usage: %s [-flnvxV] [-d delimiter] [-s signal] pattern\n", PROCTOOLS_NAME);
    exit(64);
}

static int parse_signal_number(const char *argument, int *signal_number) {
    char *end = NULL;
    long value;

    errno = 0;
    value = strtol(argument, &end, 10);
    if (errno == ERANGE || end == argument || *end != '\0' || value < 0 ||
        value >= NSIG || value > INT_MAX) {
        fprintf(stderr, "%s: invalid signal number: %s\n", PROCTOOLS_NAME,
                argument);
        return -1;
    }

    *signal_number = (int)value;
    return 0;
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
    unsigned long long newest_start_time = 0;
    char newest_text[4096] = {0};

    while ((option = getopt(argc, argv, "d:flnvs:xV")) != -1) {
        switch (option) {
        case 'd': delimiter = optarg; break;
        case 'f': full = 1; break;
        case 'l': long_output = 1; break;
        case 'n': newest = 1; break;
        case 'v': invert = 1; break;
        case 's':
            if (parse_signal_number(optarg, &signal_number) != 0) return 64;
            break;
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
    if (!proc) {
        if (!exact) regfree(&regex);
        return 2;
    }

    while ((entry = readdir(proc)) != NULL) {
        char *pid_end = NULL;
        long pid_value;
        pid_t pid;
        char text[4096];
        int matched;
        if (!numeric_name(entry->d_name)) continue;
        errno = 0;
        pid_value = strtol(entry->d_name, &pid_end, 10);
        if (errno == ERANGE || pid_end == entry->d_name || *pid_end != '\0' ||
            pid_value <= 0 || pid_value > INT_MAX) continue;
        pid = (pid_t)pid_value;
        if (pid == getpid() || process_text(pid, full, text, sizeof(text)) != 0) continue;
        matched = exact ? strcmp(text, pattern) == 0 : regexec(&regex, text, 0, NULL, 0) == 0;
        if (invert) matched = !matched;
        if (!matched) continue;
        if (newest) {
            unsigned long long start_time;
            if (process_start_time(pid, &start_time) != 0) continue;
            if (newest_pid < 0 || start_time > newest_start_time ||
                (start_time == newest_start_time && pid > newest_pid)) {
                newest_pid = pid;
                newest_start_time = start_time;
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
