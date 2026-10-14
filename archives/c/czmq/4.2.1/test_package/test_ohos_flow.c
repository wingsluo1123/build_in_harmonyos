/*  test_ohos_flow.c — czmq/4.2.1 HarmonyOS-specific end-to-end consumer test
 *  (rule12: complete consumer use case, not a pure-assertion test).
 *
 *  Runs a real functional flow against the packaged libczmq:
 *    Phase 1) zconfig persistence: build a config tree, save it to a real
 *             file under <work_dir>, reload it, verify both values survive.
 *    Phase 2) Real TCP loopback messaging: ZMQ_REP binds tcp://127.0.0.1:*
 *             (kernel picks an ephemeral port), ZMQ_REQ connects to the
 *             endpoint reported by zsock_endpoint(); zstr request/reply.
 *    Phase 3) A 3-frame zmsg roundtrip over the same TCP pair, with echo.
 *
 *  Note: the packaged zeromq dependency is built with ENABLE_CURVE=OFF, so
 *  the zcert/zmakecert certificate flow is outside this package's capability
 *  surface; this test deliberately uses stable, always-available classes.
 *
 *  usage: test_ohos_flow <work_dir>
 */
#include <czmq.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>

#define RCV_TIMEOUT_MSEC 10000

static int failures = 0;

static void
check (int ok, const char *what)
{
    if (ok)
        printf ("[ok] %s\n", what);
    else {
        fprintf (stderr, "FAIL: %s\n", what);
        failures++;
    }
}

int
main (int argc, char *argv [])
{
    if (argc < 2) {
        fprintf (stderr, "usage: test_ohos_flow <work_dir>\n");
        return 2;
    }
    const char *work_dir = argv [1];

    //  Make sure the work dir exists (test_ohos.sh also creates it)
    mkdir (work_dir, 0775);

    //  ---- Phase 1: zconfig file persistence roundtrip (real file I/O) ----
    char conf_path [512];
    snprintf (conf_path, sizeof (conf_path), "%s/flow.conf", work_dir);
    unlink (conf_path);

    zconfig_t *conf = zconfig_new ("cq", NULL);
    check (conf != NULL, "zconfig_new root node");
    zconfig_put (conf, "/worker/name", "harmonyos-consumer");
    zconfig_put (conf, "/worker/tcp-port", "31337");
    check (zconfig_save (conf, conf_path) == 0, "zconfig_save wrote flow.conf to disk");
    zconfig_destroy (&conf);

    zconfig_t *loaded = zconfig_load (conf_path);
    check (loaded != NULL, "zconfig_load re-read flow.conf from disk");
    if (loaded) {
        check (streq (zconfig_get (loaded, "/worker/name", ""), "harmonyos-consumer"),
               "config value /worker/name survives save/load roundtrip");
        check (atoi (zconfig_get (loaded, "/worker/tcp-port", "0")) == 31337,
               "config value /worker/tcp-port survives save/load roundtrip");
        zconfig_destroy (&loaded);
    }

    //  ---- Phase 2: real TCP loopback, ephemeral port, zstr request/reply ----
    zsock_t *rep = zsock_new (ZMQ_REP);
    check (rep != NULL, "zsock_new ZMQ_REP");
    zsock_t *req = zsock_new (ZMQ_REQ);
    check (req != NULL, "zsock_new ZMQ_REQ");
    if (rep)
        zsock_set_rcvtimeo (rep, RCV_TIMEOUT_MSEC);
    if (req)
        zsock_set_rcvtimeo (req, RCV_TIMEOUT_MSEC);

    int rc = rep? zsock_bind (rep, "tcp://127.0.0.1:*"): -1;
    check (rc > 0, "zsock_bind tcp://127.0.0.1:* picked a real ephemeral port");
    const char *endpoint = rep? zsock_endpoint (rep): NULL;
    check (endpoint != NULL
    &&      strncmp (endpoint, "tcp://127.0.0.1:", 16) == 0,
           "zsock_endpoint reports loopback TCP endpoint");
    check (endpoint != NULL
    &&      strrchr (endpoint, ':') != NULL
    &&      atoi (strrchr (endpoint, ':') + 1) > 0,
           "bound endpoint carries kernel-assigned port");
    printf ("      endpoint: %s\n", endpoint? endpoint: "(none)");

    if (!rep || !req || !endpoint) {
        fprintf (stderr, "FLOW-TEST FAILED: socket setup incomplete\n");
        zsock_destroy (&req);
        zsock_destroy (&rep);
        return 1;
    }

    rc = zsock_connect (req, "%s", endpoint);
    check (rc == 0, "zsock_connect REQ to bound REP endpoint");

    rc = zstr_send (req, "hello-from-harmonyos");
    check (rc == 0, "zstr_send request over TCP loopback");
    char *line = zstr_recv (rep);
    check (line != NULL && streq (line, "hello-from-harmonyos"),
           "REP received the exact request string over TCP");
    freen (line);
    rc = zstr_send (rep, "ack-from-harmonyos");
    check (rc == 0, "zstr_send reply over TCP loopback");
    line = zstr_recv (req);
    check (line != NULL && streq (line, "ack-from-harmonyos"),
           "REQ received the exact reply string over TCP");
    freen (line);

    //  ---- Phase 3: 3-frame zmsg roundtrip with echo over the same TCP pair ----
    zmsg_t *out = zmsg_new ();
    check (out != NULL, "zmsg_new");
    if (out) {
        zmsg_addstr (out, "frame-alpha");
        zmsg_addstr (out, "frame-beta");
        zmsg_addstr (out, "frame-gamma");
        check (zmsg_size (out) == 3, "zmsg assembled 3 frames");
        check (zmsg_send (&out, req) == 0, "zmsg_send 3-frame request over TCP");
    }
    zmsg_t *in = zmsg_recv (rep);
    check (in != NULL && zmsg_size (in) == 3, "REP received 3-frame zmsg over TCP");
    if (in) {
        char *f1 = zmsg_popstr (in);
        char *f2 = zmsg_popstr (in);
        char *f3 = zmsg_popstr (in);
        check (f1 && streq (f1, "frame-alpha")
        &&     f2 && streq (f2, "frame-beta")
        &&     f3 && streq (f3, "frame-gamma"),
               "3 frames arrived in order with exact content");
        freen (f1);
        freen (f2);
        freen (f3);
        zmsg_t *echo = zmsg_new ();
        if (echo) {
            zmsg_addstr (echo, "frame-alpha");
            zmsg_addstr (echo, "frame-beta");
            zmsg_addstr (echo, "frame-gamma");
            check (zmsg_send (&echo, rep) == 0, "REP echoed 3-frame reply over TCP");
        }
        else
            check (0, "zmsg_new echo");
        zmsg_destroy (&in);
    }
    in = zmsg_recv (req);
    check (in != NULL && zmsg_size (in) == 3, "REQ received 3-frame echo over TCP");
    if (in) {
        char *f1 = zmsg_popstr (in);
        char *f2 = zmsg_popstr (in);
        char *f3 = zmsg_popstr (in);
        check (f1 && streq (f1, "frame-alpha")
        &&     f2 && streq (f2, "frame-beta")
        &&     f3 && streq (f3, "frame-gamma"),
               "echoed 3 frames match the original content");
        freen (f1);
        freen (f2);
        freen (f3);
        zmsg_destroy (&in);
    }

    zsock_destroy (&req);
    zsock_destroy (&rep);

    if (failures) {
        fprintf (stderr, "FLOW-TEST FAILED: %d check(s) failed\n", failures);
        return 1;
    }
    printf ("FLOW-TEST PASSED: config persistence + TCP req/rep + zmsg roundtrip\n");
    return 0;
}
