#include <czmq.h>
#include <stdio.h>
#include <string.h>

int main (void)
{
    int failures = 0;

    // 1) Version macros report 4.2.1
    printf ("CZMQ version: %d.%d.%d\n",
            CZMQ_VERSION_MAJOR, CZMQ_VERSION_MINOR, CZMQ_VERSION_PATCH);
    if (CZMQ_VERSION_MAJOR != 4
    ||  CZMQ_VERSION_MINOR != 2
    ||  CZMQ_VERSION_PATCH != 1
    ||  CZMQ_VERSION != CZMQ_MAKE_VERSION (4, 2, 1)) {
        fprintf (stderr, "FAIL: unexpected CZMQ version macros\n");
        failures++;
    }

    // 2) zsock PAIR over inproc: zstr send/recv roundtrip (no network needed)
    zsock_t *server = zsock_new (ZMQ_PAIR);
    zsock_t *client = zsock_new (ZMQ_PAIR);
    if (!server || !client) {
        fprintf (stderr, "FAIL: cannot create zsock PAIR sockets\n");
        zsock_destroy (&server);
        zsock_destroy (&client);
        return 1;
    }
    if (zsock_bind (server, "inproc://czmq-test") != 0) {
        fprintf (stderr, "FAIL: zsock_bind inproc://czmq-test\n");
        zsock_destroy (&server);
        zsock_destroy (&client);
        return 1;
    }
    zsock_connect (client, "inproc://czmq-test");
    zstr_send (client, "hello-czmq");
    char *reply = zstr_recv (server);
    if (!reply || !streq (reply, "hello-czmq")) {
        fprintf (stderr, "FAIL: zstr roundtrip mismatch\n");
        failures++;
    }
    zstr_free (&reply);

    // 3) zframe payload roundtrip
    zframe_t *frame = zframe_from ("frame-payload");
    if (!frame
    ||  zframe_size (frame) != strlen ("frame-payload")
    ||  !streq ((const char *) zframe_data (frame), "frame-payload")) {
        fprintf (stderr, "FAIL: zframe data/size mismatch\n");
        failures++;
    }
    zframe_destroy (&frame);

    // 4) zmsg assembly and inspection
    zmsg_t *msg = zmsg_new ();
    zmsg_addstr (msg, "part-1");
    zmsg_addstr (msg, "part-2");
    if (!msg || zmsg_size (msg) != 2) {
        fprintf (stderr, "FAIL: zmsg size != 2\n");
        failures++;
    }
    else {
        char *part = zmsg_popstr (msg);
        if (!part || !streq (part, "part-1")) {
            fprintf (stderr, "FAIL: zmsg first frame mismatch\n");
            failures++;
        }
        freen (part);
    }
    zmsg_destroy (&msg);

    zsock_destroy (&client);
    zsock_destroy (&server);

    if (failures == 0)
        printf ("All tests passed!\n");
    return failures ? 1 : 0;
}
