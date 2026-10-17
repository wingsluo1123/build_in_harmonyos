/* Consumer test for the packaged libtrace library.
 *
 * It plays the role of an application that links the installed static libtrace
 * and uses the public API from the installed headers: a minimal PCAP file is
 * written on the fly, opened through trace_create()/trace_start() and read with
 * trace_read_packet().
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libtrace.h>

static int checks;
static int failures;

static void check(int condition, const char *name)
{
    checks++;
    if (condition) {
        printf("CHECK-OK: %s\n", name);
    } else {
        failures++;
        printf("CHECK-FAIL: %s\n", name);
    }
}

/* Write a one-packet, little-endian PCAP file (Ethernet, 4 payload bytes). */
static int write_pcap(const char *path)
{
    static const unsigned char global_header[24] = {
        0xd4, 0xc3, 0xb2, 0xa1,  /* magic 0xa1b2c3d4 stored little endian */
        0x02, 0x00, 0x04, 0x00,  /* version 2.4 */
        0x00, 0x00, 0x00, 0x00,  /* thiszone */
        0x00, 0x00, 0x00, 0x00,  /* sigfigs */
        0xff, 0xff, 0x00, 0x00,  /* snaplen 65535 */
        0x01, 0x00, 0x00, 0x00   /* linktype 1 (Ethernet) */
    };
    static const unsigned char packet_header[16] = {
        0x01, 0x00, 0x00, 0x00,  /* ts_sec */
        0x00, 0x00, 0x00, 0x00,  /* ts_usec */
        0x04, 0x00, 0x00, 0x00,  /* incl_len */
        0x04, 0x00, 0x00, 0x00   /* orig_len */
    };
    static const unsigned char payload[4] = {0xde, 0xad, 0xbe, 0xef};
    FILE *fh = fopen(path, "wb");

    if (!fh) {
        return 0;
    }
    fwrite(global_header, 1, sizeof(global_header), fh);
    fwrite(packet_header, 1, sizeof(packet_header), fh);
    fwrite(payload, 1, sizeof(payload), fh);
    fclose(fh);
    return 1;
}

int main(void)
{
    char path[512];
    libtrace_t *trace;
    libtrace_packet_t *packet;
    int length;

    snprintf(path, sizeof(path), "%s%clibtrace-consumer-test.pcap",
             getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp",
             '/');

    check(write_pcap(path) == 1, "consumer writes its own PCAP fixture");

    trace = trace_create(path);
    check(trace != NULL, "trace_create() returns a handle");
    check(!trace_is_err(trace), "trace_create() opens the PCAP file without error");

    check(trace_start(trace) == 0, "trace_start() returns 0");

    packet = trace_create_packet();
    check(packet != NULL, "trace_create_packet() returns a packet object");

    length = trace_read_packet(trace, packet);
    check(length >= 0, "trace_read_packet() reads the first packet");

    check(trace_get_capture_length(packet) == 4,
          "trace_get_capture_length() reports the captured payload length (4)");
    check(trace_get_link_type(packet) == TRACE_TYPE_ETH,
          "trace_get_link_type() reports Ethernet");

    length = trace_read_packet(trace, packet);
    check(length == 0, "trace_read_packet() returns 0 at end of file");

    trace_destroy_packet(packet);
    trace_destroy(trace);

    /* lifecycle is repeatable: open the same file a second time and really
     * check the result instead of asserting a constant */
    trace = trace_create(path);
    check(trace != NULL && !trace_is_err(trace),
          "a second trace_create() on the same file succeeds");
    check(trace_start(trace) == 0, "the second trace object starts successfully");
    trace_destroy(trace);

    /* error path: the handle is still returned but flagged as erred */
    trace = trace_create("/nonexistent/libtrace-consumer-missing.pcap");
    check(trace != NULL && trace_is_err(trace),
          "trace_create() flags a missing file through trace_is_err()");
    trace_destroy(trace);

    remove(path);

    printf("LIBTRACE_CONSUMER_CHECKS=%d FAILURES=%d\n", checks, failures);
    if (failures == 0) {
        printf("LIBTRACE_CONSUMER_OK\n");
    }
    return failures == 0 ? 0 : 1;
}
