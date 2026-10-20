/*
 * vde 2.3.3 consumer test (test_package)
 *
 * Genuinely exercises the installed vde libraries:
 *   - libvdeplug : vdestream packet framing (open/send/recv/close) over a
 *                  real AF_UNIX socketpair, verifying the 2-byte big-endian
 *                  length header + payload round-trip and the frecv callback
 *                  delivery path.
 *   - libvdehist : vdehist_new/getstatus/setstatus/gettermfd/getmgmtfd/free
 *                  lifecycle on a history state object.
 *
 * Every check is counted internally and persisted to the result file passed
 * as argv[1] (deterministic key=value lines).  The test_package recipe reads
 * that file and emits the HMBS_TEST_PACKAGE_RESULT marker with the actual
 * command that was executed; the test binary itself does not print the marker
 * so the marker's `command` field can never disagree with the real argv.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <libvdehist.h>
#include <libvdeplug.h>

static int g_checks = 0;
static int g_passed = 0;

/* libvdehist.h declares `extern char *prompt;` — the variable is owned by the
 * application (upstream defines it in vdeterm.c), so provide it here. */
char *prompt;

static void check(int cond, const char *name)
{
    g_checks++;
    if (cond) {
        g_passed++;
        printf("PASS: %s\n", name);
    } else {
        printf("FAIL: %s\n", name);
    }
}

/* vdestream frecv callback: copy the delivered packet into our context. */
struct recv_ctx {
    unsigned char data[64];
    size_t len;
    int called;
};

static ssize_t on_packet(void *opaque, void *buf, size_t count)
{
    struct recv_ctx *ctx = (struct recv_ctx *)opaque;
    if (ctx->called == 0 && count <= sizeof(ctx->data)) {
        memcpy(ctx->data, buf, count);
        ctx->len = count;
        ctx->called = 1;
    }
    return (ssize_t)count;
}

static void on_error(void *opaque, int type, char *format, ...)
{
    (void)opaque;
    (void)type;
    (void)format;
}

static int write_result(const char *path)
{
    FILE *fp;

    if (path == NULL || path[0] == '\0')
        return -1;
    fp = fopen(path, "w");
    if (fp == NULL)
        return -1;
    fprintf(fp, "discovered=%d\n", g_checks);
    fprintf(fp, "passed=%d\n", g_passed);
    fprintf(fp, "failed=%d\n", g_checks - g_passed);
    fflush(fp);
    fclose(fp);
    return 0;
}

int main(int argc, char **argv)
{
    /* ---------- libvdeplug: vdestream framing ---------- */
    int sv[2] = {-1, -1};
    struct recv_ctx ctx;
    unsigned char wire[64];
    ssize_t n = 0;
    ssize_t got = 0;
    VDESTREAM *vs = NULL;

    memset(&ctx, 0, sizeof(ctx));

    check(socketpair(AF_UNIX, SOCK_STREAM, 0, sv) == 0,
          "socketpair(AF_UNIX, SOCK_STREAM)");
    if (sv[0] >= 0 && sv[1] >= 0) {
        vs = vdestream_open(&ctx, sv[0], on_packet, on_error);
        check(vs != NULL, "vdestream_open returns non-NULL handle");
        if (vs != NULL) {
            /* payload "hello" -> header 0x00 0x05 + 5 bytes */
            n = vdestream_send(vs, "hello", 5);
            check(n == 7, "vdestream_send writes 2-byte header + payload");

            /* AF_UNIX SOCK_STREAM may split the 7-byte frame; read until the
             * full frame (2-byte header + 5-byte payload) has arrived. */
            while (got < 7) {
                n = read(sv[1], wire + got, sizeof(wire) - (size_t)got);
                if (n <= 0)
                    break;
                got += n;
            }
            n = got;
            check(n == 7, "peer socket reads exactly 7 bytes");
            check(n >= 7 && wire[0] == 0x00 && wire[1] == 0x05,
                  "framing header is big-endian length 5");
            check(n >= 7 && memcmp(wire + 2, "hello", 5) == 0,
                  "framing payload round-trips intact");

            /* feed the wire bytes into a receiving vdestream and verify the
             * frecv callback is invoked with the reassembled packet. */
            vdestream_recv(vs, wire, 7);
            check(ctx.called == 1 && ctx.len == 5
                      && memcmp(ctx.data, "hello", 5) == 0,
                  "vdestream_recv delivers payload via frecv callback");

            vdestream_close(vs);
        }
        close(sv[0]);
        close(sv[1]);
    }

    /* ---------- libvdehist: state lifecycle ---------- */
    {
        struct vdehiststat *st = vdehist_new(0, -1);
        check(st != NULL, "vdehist_new returns non-NULL state");
        if (st != NULL) {
            check(vdehist_getstatus(st) == HIST_NOCMD,
                  "vdehist_getstatus returns HIST_NOCMD for no-mgmt state");
            check(vdehist_gettermfd(st) == 0,
                  "vdehist_gettermfd returns the terminal fd");
            check(vdehist_getmgmtfd(st) == -1,
                  "vdehist_getmgmtfd returns -1 when no mgmt socket");
            vdehist_setstatus(st, HIST_COMMAND);
            check(vdehist_getstatus(st) == HIST_COMMAND,
                  "vdehist_setstatus/getstatus round-trips HIST_COMMAND");
            vdehist_setstatus(st, HIST_NOCMD);
            check(vdehist_getstatus(st) == HIST_NOCMD,
                  "vdehist_setstatus/getstatus round-trips HIST_NOCMD");
            vdehist_free(st);
        }
    }

    /* ---------- persist counts for the recipe (single source of truth) ---- */
    if (write_result(argc > 1 ? argv[1] : NULL) != 0)
        fprintf(stderr, "warning: could not write result file\n");
    printf("RESULT: %d passed, %d failed, %d total\n",
           g_passed, g_checks - g_passed, g_checks);
    fflush(stdout);
    return g_checks == g_passed ? 0 : 1;
}
