/*  test_ohos_flow.c — zyre/2.0.1 HarmonyOS-specific end-to-end consumer test
 *  (rule12: complete consumer use case, not a pure-assertion test).
 *
 *  Runs a real functional flow against the packaged libzyre, using only the
 *  stable public API (zyre / zyre_event):
 *    Phase 0) Both zyre nodes ("alpha" and "beta") are created and started
 *             serially on the main thread — all zyre/czmq socket creation
 *             happens before any node thread exists.
 *    Phase 1) The two nodes then run in two threads and discover each
 *             other over real UDP beacons on the local
 *             interface (ZRE discovery, default UDP port 5670).
 *    Phase 2) Both nodes join group "FLOW-GROUP"; each side waits for the
 *             other's ENTER and JOIN events.
 *    Phase 3) beta shouts "hello-from-beta" into the group; alpha receives
 *             the SHOUT with the exact payload and shouts back
 *             "ack-from-alpha"; beta receives the ack, then stops; alpha
 *             waits for beta's EXIT (proof the ack was consumed) before
 *             stopping too. Both nodes then stop and destroy gracefully.
 *    Phase 4) A flow report is written to <work_dir>/flow-report.txt with
 *             one line per observed step (disk evidence), ending with a
 *             "FLOW-RESULT: PASS" line on success.
 *
 *  All event waits are bounded (60 s receive timeout) so a broken
 *  environment fails fast instead of hanging CI, while tolerating the
 *  scheduler stalls seen on heavily loaded devices.
 *
 *  usage: test_ohos_flow <work_dir>
 */
#include <zyre.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RCV_TIMEOUT_MSEC 60000
#define FLOW_GROUP "FLOW-GROUP"

static int failures = 0;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static char g_report [8192];
static size_t g_report_len = 0;

static void
check (int ok, const char *what)
{
    pthread_mutex_lock (&g_lock);
    if (ok) {
        printf ("[ok] %s\n", what);
        g_report_len += (size_t) snprintf (
            g_report + g_report_len, sizeof (g_report) - g_report_len,
            "[ok] %s\n", what);
    }
    else {
        fprintf (stderr, "FAIL: %s\n", what);
        failures++;
        g_report_len += (size_t) snprintf (
            g_report + g_report_len, sizeof (g_report) - g_report_len,
            "FAIL: %s\n", what);
    }
    pthread_mutex_unlock (&g_lock);
}

struct node_ctx {
    const char *name;
    int send_first;              // 1 = beta side (sends first), 0 = alpha side
    int rc;                      // 0 = this thread's flow succeeded
    zyre_t *node;                // created by node_setup() on the main thread
};

//  Wait for a specific event type (and optional group/payload), skipping
//  any other events. Returns 0 on match, 1 on timeout or mismatch.
static int
wait_event (zyre_t *node, const char *want, const char *group,
            const char *payload_want)
{
    while (true) {
        zyre_event_t *ev = zyre_event_new (node);
        if (!ev) {
            fprintf (stderr, "FAIL: [%s] timeout waiting for %s event\n",
                     zyre_name (node), want);
            return 1;
        }
        const char *type = zyre_event_type (ev);
        bool hit = type && streq (type, want)
                   && (group == NULL || streq (zyre_event_group (ev), group));
        if (hit && payload_want) {
            zmsg_t *msg = zyre_event_msg (ev);
            char *text = msg? zmsg_popstr (msg): NULL;
            if (!text || !streq (text, payload_want)) {
                fprintf (stderr, "FAIL: [%s] %s payload mismatch "
                         "(expected '%s', got '%s')\n",
                         zyre_name (node), want, payload_want,
                         text? text: "(none)");
                freen (text);
                zyre_event_destroy (&ev);
                return 1;
            }
            freen (text);
        }
        zyre_event_destroy (&ev);
        if (hit)
            return 0;
        //  Non-matching event (echoes of our own JOIN, LEAVE, ...): keep waiting
    }
}

//  Create and start one node on the main thread. All zyre/czmq socket
//  creation happens serially here, before any node thread exists (see the
//  comment in main). Returns 0 on success.
static int
node_setup (struct node_ctx *ctx)
{
    char what [256];

    ctx->node = zyre_new (ctx->name);
    if (!ctx->node) {
        check (0, "zyre_new");
        return 1;
    }
    zyre_set_header (ctx->node, "X-FLOW", "%s", ctx->name);
    //  Bound every event wait so a broken environment fails fast
    zsock_set_rcvtimeo (zyre_socket (ctx->node), RCV_TIMEOUT_MSEC);

    if (zyre_start (ctx->node) != 0) {
        check (0, "zyre_start started beacon discovery");
        zyre_destroy (&ctx->node);
        return 1;
    }
    snprintf (what, sizeof (what), "node %s: zyre_start (UDP beacon, port 5670)",
              ctx->name);
    check (1, what);

    zyre_join (ctx->node, FLOW_GROUP);
    snprintf (what, sizeof (what), "node %s: joined " FLOW_GROUP, ctx->name);
    check (1, what);
    return 0;
}

static void *
node_thread (void *arg)
{
    struct node_ctx *ctx = (struct node_ctx *) arg;
    const char *peer = ctx->send_first? "alpha": "beta";
    zyre_t *node = ctx->node;

    char what [256];

    //  Phase 1: peer discovery over real UDP beacons
    if (wait_event (node, "ENTER", NULL, NULL) != 0) {
        snprintf (what, sizeof (what),
                  "node %s: wait ENTER from peer %s (UDP beacon discovery)",
                  ctx->name, peer);
        check (0, what);
        zyre_stop (node);
        zyre_destroy (&node);
        ctx->rc = 1;
        return NULL;
    }
    snprintf (what, sizeof (what),
              "node %s: ENTER received (peer %s discovered via UDP beacon)",
              ctx->name, peer);
    check (1, what);

    //  Phase 2: peer joined the common group
    if (wait_event (node, "JOIN", FLOW_GROUP, NULL) != 0) {
        snprintf (what, sizeof (what),
                  "node %s: wait JOIN from peer in " FLOW_GROUP, ctx->name);
        check (0, what);
        zyre_stop (node);
        zyre_destroy (&node);
        ctx->rc = 1;
        return NULL;
    }
    snprintf (what, sizeof (what), "node %s: JOIN received (peer in " FLOW_GROUP ")",
              ctx->name);
    check (1, what);

    //  Phase 3: group shout exchange
    if (ctx->send_first) {
        if (zyre_shouts (node, FLOW_GROUP, "hello-from-beta") != 0) {
            check (0, "zyre_shouts hello-from-beta");
            zyre_stop (node);
            zyre_destroy (&node);
            ctx->rc = 1;
            return NULL;
        }
        check (1, "node beta: SHOUT hello-from-beta sent to " FLOW_GROUP);
        if (wait_event (node, "SHOUT", FLOW_GROUP, "ack-from-alpha") != 0) {
            snprintf (what, sizeof (what),
                      "node %s: wait SHOUT ack-from-alpha from peer %s",
                      ctx->name, peer);
            check (0, what);
            zyre_stop (node);
            zyre_destroy (&node);
            ctx->rc = 1;
            return NULL;
        }
        check (1, "node beta: SHOUT ack-from-alpha received with exact payload");
    }
    else {
        if (wait_event (node, "SHOUT", FLOW_GROUP, "hello-from-beta") != 0) {
            snprintf (what, sizeof (what),
                      "node %s: wait SHOUT hello-from-beta from peer %s",
                      ctx->name, peer);
            check (0, what);
            zyre_stop (node);
            zyre_destroy (&node);
            ctx->rc = 1;
            return NULL;
        }
        check (1, "node alpha: SHOUT hello-from-beta received with exact payload");
        if (zyre_shouts (node, FLOW_GROUP, "ack-from-alpha") != 0) {
            check (0, "zyre_shouts ack-from-alpha");
            zyre_stop (node);
            zyre_destroy (&node);
            ctx->rc = 1;
            return NULL;
        }
        check (1, "node alpha: SHOUT ack-from-alpha sent to " FLOW_GROUP);
        //  Wait for beta's EXIT before stopping: beta sends EXIT only after
        //  its app thread has consumed the ack SHOUT, so this handshake
        //  guarantees the ack was delivered end-to-end. Stopping right
        //  after zyre_shouts can drop the still-unflushed group message
        //  when the node tears its peer down, leaving beta's bounded wait
        //  to expire on a message that was never sent on the wire.
        if (wait_event (node, "EXIT", NULL, NULL) != 0) {
            snprintf (what, sizeof (what),
                      "node %s: wait EXIT from peer %s (ack-consumed handshake)",
                      ctx->name, peer);
            check (0, what);
            zyre_stop (node);
            zyre_destroy (&node);
            ctx->rc = 1;
            return NULL;
        }
        check (1, "node alpha: EXIT received (beta stopped after consuming ack)");
    }

    //  Graceful stop (sends EXIT), settle, then destroy — upstream sequence
    zyre_stop (node);
    zclock_sleep (250);
    zyre_destroy (&node);
    snprintf (what, sizeof (what), "node %s: zyre_stop + zyre_destroy (graceful)",
              ctx->name);
    check (1, what);

    ctx->rc = 0;
    return NULL;
}

int
main (int argc, char *argv [])
{
    if (argc < 2) {
        fprintf (stderr, "usage: test_ohos_flow <work_dir>\n");
        return 2;
    }
    const char *work_dir = argv [1];

    struct node_ctx alpha = { "alpha", 0, 1, NULL };
    struct node_ctx beta = { "beta", 1, 1, NULL };

    //  Phase 0: both nodes are created and started here on the main thread,
    //  strictly serially, BEFORE any node thread exists. czmq 4.2.1's
    //  zsys_init() applies its environment/default settings
    //  (zsys_set_ipv6_mcast_address(), zsys_set_thread_name_prefix_str(),
    //  ...) only after it has marked itself initialized and released the
    //  init lock, and each of those setters asserts that no socket has been
    //  created yet (assert (s_open_sockets == 0) in czmq src/zsys.c). If
    //  the two nodes created their sockets concurrently on two threads, one
    //  thread's socket could open inside that window and abort the process
    //  (SIGABRT, exit 134; seen as PR-check #16226 failure on the buildbot
    //  device). Serial single-threaded setup makes that race impossible by
    //  construction and does not depend on any czmq version's internal
    //  ordering. Constraint: the node threads below must only run the event
    //  choreography on the already-started nodes; no thread may create its
    //  first zyre/czmq object before node_setup() has completed for both
    //  nodes.
    if (node_setup (&alpha) != 0 || node_setup (&beta) != 0) {
        fprintf (stderr, "FAIL: cannot set up both zyre nodes\n");
        if (alpha.node) {
            zyre_stop (alpha.node);
            zyre_destroy (&alpha.node);
        }
        return 1;
    }

    pthread_t ta, tb;
    if (pthread_create (&ta, NULL, node_thread, &alpha) != 0
    ||  pthread_create (&tb, NULL, node_thread, &beta) != 0) {
        fprintf (stderr, "FAIL: cannot start node threads\n");
        return 1;
    }
    pthread_join (ta, NULL);
    pthread_join (tb, NULL);
    //  Belt-and-braces: any node thread that bailed out early records rc != 0.
    //  Thread-level failures must count towards the global total too, so the
    //  process exit code and the FLOW-RESULT conclusion can never disagree
    //  (failures remains the single source of truth for both).
    if (alpha.rc != 0 || beta.rc != 0)
        failures++;

    //  Phase 4: flow report as disk evidence
    char report_path [512];
    snprintf (report_path, sizeof (report_path), "%s/flow-report.txt", work_dir);
    FILE *out = fopen (report_path, "w");
    if (out) {
        fputs (g_report, out);
        fputs (failures? "FLOW-RESULT: FAIL\n": "FLOW-RESULT: PASS\n", out);
        fclose (out);
        printf ("      flow report written to %s\n", report_path);
    }
    else
        fprintf (stderr, "FAIL: cannot write flow report %s\n", report_path);

    if (failures) {
        fprintf (stderr, "FLOW-TEST FAILED: %d check(s) failed\n", failures);
        return 1;
    }
    printf ("FLOW-TEST PASSED: dual-node UDP beacon discovery + JOIN + SHOUT group flow\n");
    return 0;
}
