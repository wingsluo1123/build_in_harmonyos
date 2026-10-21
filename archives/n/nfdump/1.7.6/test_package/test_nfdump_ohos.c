/*
 * HarmonyOS consumer test for nfdump.
 *
 * The test drives the complete flow collection pipeline of the package the
 * way a real consumer would, without stubbing anything:
 *
 *   consumer (this program) --netflow v5/udp--> nfcapd --> flow file
 *   flow file --nfdump--> records read back and verified
 *
 * nfcapd and nfdump are executed from the package folder, so the test only
 * passes when the package is present and its tools really work on the
 * platform.
 *
 * No assertion is used on purpose: every step prints its own PASS/FAIL line
 * and the exit status is non zero as soon as one step failed.
 */
#define _GNU_SOURCE

#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define NETFLOW_V5_HEADER_LEN 24
#define NETFLOW_V5_RECORD_LEN 48

#define TEST_SRC_ADDR "192.0.2.1"
#define TEST_DST_ADDR "198.51.100.2"
#define TEST_SRC_PORT 12345
#define TEST_DST_PORT 80

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

// Run a shell command and return its exit status; stdout+stderr are collected
// into buffer when it is not NULL.
static int run_command(const char *command, char *buffer, size_t buffer_size) {
    FILE *pipe;
    int status;
    size_t used = 0;

    if (buffer != NULL && buffer_size > 0) buffer[0] = '\0';

    pipe = popen(command, "r");
    if (pipe == NULL) return -1;

    if (buffer != NULL) {
        while (used + 1 < buffer_size) {
            size_t got = fread(buffer + used, 1, buffer_size - 1 - used, pipe);
            used += got;
            if (got == 0) break;
        }
        buffer[used] = '\0';
    } else {
        char sink[512];
        while (fread(sink, 1, sizeof(sink), pipe) > 0) {
        }
    }

    status = pclose(pipe);
    if (status == -1) return -1;
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);

    return -1;

}  // End of run_command

static int file_exists(const char *path) {
    struct stat st;

    return stat(path, &st) == 0;

}  // End of file_exists

static long file_size(const char *path) {
    struct stat st;

    if (stat(path, &st) != 0) return -1;

    return (long)st.st_size;

}  // End of file_size

// Poll for a path to appear (present != 0) or to disappear (present == 0).
static int wait_for_path(const char *path, int present, int timeout_ms) {
    int waited = 0;

    while (waited < timeout_ms) {
        if (file_exists(path) == (present != 0)) return 1;
        usleep(100 * 1000);
        waited += 100;
    }

    return 0;

}  // End of wait_for_path

// Return the first entry of dir which starts with prefix, or zero when there
// is none.
static int find_entry_with_prefix(const char *dir, const char *prefix, char *result, size_t result_size) {
    DIR *handle;
    struct dirent *entry;
    int found = 0;

    handle = opendir(dir);
    if (handle == NULL) return 0;

    while ((entry = readdir(handle)) != NULL) {
        if (strncmp(entry->d_name, prefix, strlen(prefix)) != 0) continue;
        snprintf(result, result_size, "%s/%s", dir, entry->d_name);
        found = 1;
        break;
    }

    closedir(handle);

    return found;

}  // End of find_entry_with_prefix

static void put_u8(unsigned char *buffer, size_t offset, uint8_t value) {
    buffer[offset] = value;
}

static void put_u16(unsigned char *buffer, size_t offset, uint16_t value) {
    uint16_t be = htons(value);

    memcpy(buffer + offset, &be, sizeof(be));

}  // End of put_u16

static void put_u32(unsigned char *buffer, size_t offset, uint32_t value) {
    uint32_t be = htonl(value);

    memcpy(buffer + offset, &be, sizeof(be));

}  // End of put_u32

// Build a standard netflow v5 packet with a single flow record.
static size_t build_netflow_v5(unsigned char *packet, size_t size) {
    struct in_addr addr;
    uint32_t uptime = 3600 * 1000;
    time_t now = time(NULL);

    memset(packet, 0, size);

    // v5 header
    put_u16(packet, 0, 5);                      // version
    put_u16(packet, 2, 1);                      // flow record count
    put_u32(packet, 4, uptime);                 // system uptime in ms
    put_u32(packet, 8, (uint32_t)now);          // current unix seconds
    put_u32(packet, 12, 0);                     // current unix nanoseconds
    put_u32(packet, 16, 1);                     // flow sequence
    put_u8(packet, 20, 0);                      // engine type
    put_u8(packet, 21, 0);                      // engine id
    put_u16(packet, 22, 0);                     // sampling interval: not sampled

    // single v5 flow record
    unsigned char *record = packet + NETFLOW_V5_HEADER_LEN;

    inet_aton(TEST_SRC_ADDR, &addr);
    put_u32(record, 0, ntohl(addr.s_addr));     // source address
    inet_aton(TEST_DST_ADDR, &addr);
    put_u32(record, 4, ntohl(addr.s_addr));     // destination address
    inet_aton("203.0.113.1", &addr);
    put_u32(record, 8, ntohl(addr.s_addr));     // next hop
    put_u16(record, 12, 1);                     // input interface
    put_u16(record, 14, 2);                     // output interface
    put_u32(record, 16, 10);                    // packets
    put_u32(record, 20, 1000);                  // bytes
    put_u32(record, 24, uptime - 1000);         // first seen
    put_u32(record, 28, uptime);                // last seen
    put_u16(record, 32, TEST_SRC_PORT);         // source port
    put_u16(record, 34, TEST_DST_PORT);         // destination port
    put_u8(record, 36, 0);                      // padding
    put_u8(record, 37, 0x18);                   // tcp flags
    put_u8(record, 38, 6);                      // protocol: tcp
    put_u8(record, 39, 0);                      // type of service
    put_u16(record, 40, 64512);                 // source AS
    put_u16(record, 42, 64513);                 // destination AS
    put_u8(record, 44, 24);                     // source mask
    put_u8(record, 45, 24);                     // destination mask
    put_u16(record, 46, 0);                     // padding

    return NETFLOW_V5_HEADER_LEN + NETFLOW_V5_RECORD_LEN;

}  // End of build_netflow_v5

// Start nfcapd for the given port and directory; return the collector pid or
// -1. nfcapd daemonises itself, so the pid is read from its pid file.
static pid_t start_collector(const char *nfcapd, const char *datadir, int port, const char *pidfile) {
    pid_t child;
    int status = 0;
    char port_arg[16];
    char pid_text[32];
    FILE *handle;

    snprintf(port_arg, sizeof(port_arg), "%d", port);

    child = fork();
    if (child < 0) return -1;

    if (child == 0) {
        execl(nfcapd, nfcapd, "-p", port_arg, "-w", datadir, "-D", "-P", pidfile, "-I", "TestIdent", "-t", "3600", "-z", "lz4",
              (char *)NULL);
        _exit(127);
    }

    if (waitpid(child, &status, 0) < 0) return -1;

    // the collector writes its pid file once the daemon is up
    if (!wait_for_path(pidfile, 1, 10000)) return -1;

    handle = fopen(pidfile, "r");
    if (handle == NULL) return -1;
    if (fgets(pid_text, sizeof(pid_text), handle) == NULL) {
        fclose(handle);
        return -1;
    }
    fclose(handle);

    return (pid_t)strtol(pid_text, NULL, 10);

}  // End of start_collector

static int send_flow_records(int port, const unsigned char *packet, size_t packet_size) {
    struct sockaddr_in target;
    int sock;
    int sent = 0;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) return 0;

    memset(&target, 0, sizeof(target));
    target.sin_family = AF_INET;
    target.sin_port = htons((uint16_t)port);
    target.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    for (int i = 0; i < 3; i++) {
        ssize_t written = sendto(sock, packet, packet_size, 0, (struct sockaddr *)&target, sizeof(target));
        if (written == (ssize_t)packet_size) sent++;
        sleep(1);
    }

    close(sock);

    return sent;

}  // End of send_flow_records

int main(int argc, char **argv) {
    const char *package_folder;
    const char *work_root;
    char bindir[1024];
    char nfcapd[1024];
    char nfdump[1024];
    char datadir[1200];
    char pidfile[1200];
    char capture[1200];
    char command[4096];
    char output[64 * 1024];
    unsigned char packet[NETFLOW_V5_HEADER_LEN + NETFLOW_V5_RECORD_LEN];
    struct utsname uts;
    size_t packet_size;
    pid_t collector;
    int port;

    printf("=== nfdump HarmonyOS consumer test ===\n");

    if (argc < 3) {
        printf("usage: %s <package folder> <work folder>\n", argv[0]);
        return 2;
    }
    package_folder = argv[1];
    work_root = argv[2];

    snprintf(bindir, sizeof(bindir), "%s/bin", package_folder);
    snprintf(nfcapd, sizeof(nfcapd), "%s/nfcapd", bindir);
    snprintf(nfdump, sizeof(nfdump), "%s/nfdump", bindir);
    snprintf(datadir, sizeof(datadir), "%s/collected", work_root);
    snprintf(pidfile, sizeof(pidfile), "%s/nfcapd.pid", datadir);

    // ---- platform probe -------------------------------------------------
    printf("[1] platform\n");
    if (uname(&uts) == 0) {
        note("uname: %s %s %s", uts.sysname, uts.release, uts.machine);
        check(strstr(uts.sysname, "HarmonyOS") != NULL || strstr(uts.release, "HongMeng") != NULL,
              "platform is HarmonyOS (this consumer test is OHOS specific)");
    } else {
        check(0, "uname() reports the platform");
        note("uname: unavailable (%s)", strerror(errno));
    }

    // ---- packaged tools -------------------------------------------------
    printf("[2] packaged collector and analyser\n");
    check(file_exists(nfcapd), "bin/nfcapd from the package is present");
    check(file_exists(nfdump), "bin/nfdump from the package is present");
    if (g_failures > 0) {
        printf("\n=== %d check(s) failed ===\n", g_failures);
        return 1;
    }

    // ---- collection pipeline -------------------------------------------
    printf("[3] collection pipeline: consumer -> nfcapd -> flow file -> nfdump\n");
    mkdir(work_root, 0700);
    mkdir(datadir, 0700);

    port = 40000 + (int)(getpid() % 20000);
    packet_size = build_netflow_v5(packet, sizeof(packet));

    collector = start_collector(nfcapd, datadir, port, pidfile);
    if (!check(collector > 0, "nfcapd started and published its pid file")) {
        snprintf(command, sizeof(command), "cat \"%s\" 2>&1", pidfile);
        run_command(command, output, sizeof(output));
        printf("        %s\n", output);
        printf("\n=== %d check(s) failed ===\n", g_failures);
        return 1;
    }
    note("collector pid %ld listening on udp/%d", (long)collector, port);

    check(send_flow_records(port, packet, packet_size) == 3, "consumer exported 3 netflow v5 packets to the collector");

    sleep(1);
    if (kill(collector, SIGTERM) != 0) {
        check(0, "collector accepted SIGTERM");
    } else {
        check(wait_for_path(pidfile, 0, 15000), "collector shut down and removed its pid file");
    }

    if (!find_entry_with_prefix(datadir, "nfcapd.", capture, sizeof(capture))) {
        check(0, "collector wrote a flow file into the data directory");
        printf("\n=== %d check(s) failed ===\n", g_failures);
        return 1;
    }
    note("flow file %s (%ld bytes)", capture, file_size(capture));
    check(file_size(capture) > 0, "flow file is not empty");

    // ---- read the flows back -------------------------------------------
    printf("[4] read the collected flows back with nfdump\n");
    snprintf(command, sizeof(command), "\"%s\" -r \"%s\" -q -o raw 2>&1", nfdump, capture);
    check(run_command(command, output, sizeof(output)) == 0, "nfdump -r <flow file> -o raw succeeded");

    int flow_seen = strstr(output, TEST_SRC_ADDR) != NULL && strstr(output, TEST_DST_ADDR) != NULL &&
                    strstr(output, "12345") != NULL && strstr(output, "NETFLOW v5") != NULL;
    check(flow_seen, "the exported flow was collected and is reported by nfdump");
    if (flow_seen) {
        char *line = output;
        while (*line != '\0' && (*line == '\n' || *line == '\r')) line++;
        char *end_of_line = strchr(line, '\n');
        if (end_of_line != NULL) *end_of_line = '\0';
        note("nfdump -o raw: %s", line);
    } else {
        note("nfdump -o raw output was:");
        printf("%s\n", output);
    }

    snprintf(command, sizeof(command), "\"%s\" -r \"%s\" -s ip 2>&1", nfdump, capture);
    check(run_command(command, output, sizeof(output)) == 0, "nfdump -s ip aggregation over the collected flow file succeeded");

    printf("\n");
    if (g_failures > 0) {
        printf("=== %d check(s) failed ===\n", g_failures);
        return 1;
    }
    printf("=== OHOS stream collection consumer test PASSED ===\n");

    return 0;

}  // End of main
