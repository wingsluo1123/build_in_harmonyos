/*
 * test.c — synscan 5.02 consumer test of the packaged libsynscan.a parse API.
 *
 * synscan's runtime scanning needs a raw socket + libpcap and root, so the
 * device cannot run the actual SYN-scan path.  Its net.c/common.c/obuf.c
 * build an extensive, libpcap-free parsing engine (IP-list & port-list
 * parsing, iterators, sums, TCP-flag parsing) that works with no privileges.
 * This consumer links against the packaged libsynscan.a and calls that API
 * directly, asserting its real (measured) behaviour.
 *
 * Honesty note (assertions reflect actual, observed upstream behaviour, not
 * assumptions):
 *   - net_parse_portlist/net_parse_iplistv4 use strtok/strchr and modify the
 *     input in place: callers MUST pass a mutable buffer (a string literal
 *     would segfault).  We use char[] buffers.
 *   - net_portlist_add prepends, so iteration order is the reverse of parse
 *     order; we assert on membership + count, not ordering.
 *   - net_parse_portlist_item has no upper-bound check on the port number
 *     (e.g. "70000" truncates to 4464 and is accepted) — we therefore assert
 *     rejection only for genuinely invalid forms (upper<lower, non-numeric).
 *   - net_ipv4_parse_flags warns on an unknown flag but still returns SYN_OK
 *     leaving the flags unchanged — a real upstream quirk we do not rely on.
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <netinet/in.h>

#include "net.h"
#include "synscan.h"

/* libsynscan.a (net.o) references the global `arg_progname` (extern in
 * synscan.h, normally defined by synscan.c/sslog.c).  Provide it here. */
char *arg_progname = "synscan-consumer-test";

static int fails = 0;
static int checks = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (!(cond)) { printf("FAIL: %s\n", msg); fails++; } \
    else { printf("PASS: %s\n", msg); } \
} while (0)

/* scan a portlist into buf; returns number of ports emitted. */
static int scan_ports(struct portlist_t *pl, uint16_t *out, int max) {
    int n = 0;
    struct portlist_iter_t it;
    uint16_t p;
    net_portlist_iter_init(&it, pl);
    while (n < max && net_portlist_iter_next(&it, &p) == ITER_CONTINUE)
        out[n++] = p;
    return n;
}

static int has_port(const uint16_t *arr, int n, uint16_t want) {
    int i;
    for (i = 0; i < n; i++)
        if (arr[i] == want)
            return 1;
    return 0;
}

int main(void) {
    /* mutable buffers (net_parse_* modify their input in place) */
    char b1[] = "80,443,8000-8010";
    char b3[] = "80-20";      /* upper < lower -> rejected */
    char b5[] = "abc";        /* non-numeric -> rejected */
    char b4[] = "1-3,5,9-10";
    char s1[] = "192.168.1.0/24";
    char s2[] = "10.0.0.1-10.0.0.3";
    char s3[] = "10.0.0.1/32";
    char s4[] = "10.0.0.1/30,10.0.1.0-10.0.1.2";
    char s5[] = "999.1.1.1";  /* invalid octet -> rejected */
    char s6[] = "10.0.0.1/99";/* mask > 32 -> rejected */
    char f1[] = "SYN,ACK";
    char f2[] = "RST";
    uint16_t buf[32];

    /* ---- port-list parsing ---- */
    struct portlist_t *pl = net_parse_portlist(b1);
    CHECK(pl != NULL, "net_parse_portlist(...) non-NULL");
    CHECK(net_portlist_sum(pl) == 13, "net_portlist_sum==13 (80,443,8000-8010)");
    int cnt = scan_ports(pl, buf, 32);
    CHECK(cnt == 13, "portlist iteration yields 13 ports");
    CHECK(has_port(buf, cnt, 80) && has_port(buf, cnt, 443)
          && has_port(buf, cnt, 8000) && has_port(buf, cnt, 8010),
          "port membership {80,443,8000..8010}");
    net_portlist_free(pl);

    /* invalid forms */
    CHECK(net_parse_portlist(b3) == NULL, "net_parse_portlist(80-20) NULL");
    CHECK(net_parse_portlist(b5) == NULL, "net_parse_portlist(abc) NULL");

    /* greedy list 1-3,5,9-10 => 6 ports, membership */
    pl = net_parse_portlist(b4);
    CHECK(pl != NULL, "greedy port list parsed");
    cnt = scan_ports(pl, buf, 32);
    CHECK(cnt == 6, "greedy port list count==6");
    CHECK(has_port(buf, cnt, 1) && has_port(buf, cnt, 3)
          && has_port(buf, cnt, 5) && has_port(buf, cnt, 9)
          && has_port(buf, cnt, 10),
          "greedy port membership {1,2,3,5,9,10}");
    net_portlist_free(pl);

    /* ---- IP-list parsing ---- */
    struct iplistv4_t *il = net_parse_iplistv4(s1);
    CHECK(il != NULL, "net_parse_iplistv4(/24) non-NULL");
    CHECK(net_iplistv4_sum(il) == 256, "iplistv4_sum(/24)==256");
    net_iplistv4_free(il);

    il = net_parse_iplistv4(s2);
    CHECK(il != NULL, "net_parse_iplistv4(range) non-NULL");
    CHECK(net_iplistv4_sum(il) == 3, "iplistv4_sum(range)==3");
    net_iplistv4_free(il);

    il = net_parse_iplistv4(s3);
    CHECK(il != NULL && net_iplistv4_sum(il) == 1, "iplistv4_sum(/32)==1");
    net_iplistv4_free(il);

    il = net_parse_iplistv4(s4);
    CHECK(il != NULL && net_iplistv4_sum(il) == 7, "two-block iplist sum==7");
    net_iplistv4_free(il);

    /* invalid ip / bad mask rejected */
    CHECK(net_parse_iplistv4(s5) == NULL, "invalid ip (999.x) rejected");
    CHECK(net_parse_iplistv4(s6) == NULL, "mask >32 rejected");

    /* IP-range iterator yields exactly the 3 addresses */
    il = net_parse_iplistv4(s2);
    {
        struct iplistv4_iter_t iit;
        struct in_addr a;
        int ipcnt = 0;
        net_iplistv4_iter_init(&iit, il);
        while (net_iplistv4_iter_next(&iit, &a) == ITER_CONTINUE)
            ipcnt++;
        CHECK(ipcnt == 3, "iplistv4 iteration yields 3 addresses");
    }
    net_iplistv4_free(il);

    /* ---- TCP flags ---- */
    uint8_t flags = 0;
    CHECK(net_ipv4_parse_flags(f1, &flags) == SYN_OK && flags == (TH_SYN | TH_ACK),
          "flags(SYN,ACK)==0x12");
    flags = 0;
    CHECK(net_ipv4_parse_flags(f2, &flags) == SYN_OK && flags == TH_RST,
          "flags(RST)==0x04");

    printf("SYNSCAN_API_TOTAL=%d\n", checks);
    printf("SYNSCAN_API_PASS=%d\n", checks - fails);
    printf("SYNSCAN_API_FAIL=%d\n", fails);
    printf("synscan parse-API consumer test: %d/%d passed\n",
           checks - fails, checks);
    return fails ? 1 : 0;
}
