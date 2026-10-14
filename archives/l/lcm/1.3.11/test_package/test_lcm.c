/* test_package consumer — lcm 1.3.11.
 *
 * Links against the INSTALLED liblcm (+ its glib closure via CMakeDeps) and
 * drives the real C API through the in-memory "memq://" provider.  Each check
 * that passes prints exactly one "CHECK-OK: <name>" line; test_package/conanfile.py
 * counts those deterministic lines for the HMBS_TEST_PACKAGE_RESULT machine-evidence
 * marker (exit-code-0 alone is not proof).
 *
 * The checks deliberately mirror the upstream memq gtest suite (which the main
 * recipe already runs and reports as HMBS_UPSTREAM_TEST_RESULT) so a package
 * that links but does not actually marshal/subscribe cannot pass.
 *
 * Count of CHECK-OK checks = 6 (keep in sync with CONSUMER_CHECK_COUNT in
 * test_package/conanfile.py and MANIFEST.yml assertion_count).
 */
#include <lcm/lcm.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_failures = 0;

static void t_check(const char *name, int ok) {
    if (ok) {
        printf("CHECK-OK: %s\n", name);
    } else {
        printf("CHECK-FAIL: %s\n", name);
        g_failures++;
    }
}

/* collect received payload + flag for the timeout-with-message check */
static uint8_t g_recv_buf[4096];
static size_t  g_recv_len = 0;

static void recv_handler(const lcm_recv_buf_t *rbuf, const char *channel,
                         void *user_data) {
    (void)channel;
    (void)user_data;
    if (rbuf->data_size > sizeof(g_recv_buf)) {
        g_recv_len = 0;
        return;
    }
    g_recv_len = rbuf->data_size;
    memcpy(g_recv_buf, rbuf->data, rbuf->data_size);
}

int main(void) {
    /* 1) memq provider creation */
    lcm_t *lcm = lcm_create("memq://");
    t_check("lcm_create_memq", lcm != NULL);
    if (!lcm)
        return 1;

    /* 2) subscribe */
    lcm_subscription_t *sub = lcm_subscribe(lcm, "channel", recv_handler, NULL);
    t_check("lcm_subscribe", sub != NULL);

    /* 3) publish + handle round trip (10 iterations, random 1024-byte payload) */
    uint8_t sent[1024];
    int roundtrip_ok = sub != NULL;
    int it;
    for (it = 0; it < 10; ++it) {
        int i;
        for (i = 0; i < (int)sizeof(sent); ++i)
            sent[i] = (uint8_t)(rand() % 256);
        if (lcm_publish(lcm, "channel", sent, sizeof(sent)) != 0) {
            roundtrip_ok = 0;
            break;
        }
        g_recv_len = 0;
        if (lcm_handle(lcm) != 0 || g_recv_len != sizeof(sent) ||
            memcmp(g_recv_buf, sent, sizeof(sent)) != 0) {
            roundtrip_ok = 0;
            break;
        }
    }
    t_check("lcm_memq_roundtrip", roundtrip_ok);

    /* 4) handle_timeout with no pending message times out immediately */
    /*    (queue was drained by the round-trip loop above) */
    int timeout_empty_ok = (lcm_handle_timeout(lcm, 0) == 0);
    t_check("lcm_handle_timeout_empty", timeout_empty_ok);

    /* 5) handle_timeout with a pending message returns > 0 and handler runs */
    int handled = 0;
    g_recv_len = 0;
    lcm_publish(lcm, "channel", "ping", 4);
    int rc = lcm_handle_timeout(lcm, 10000);
    int timeout_msg_ok = (rc > 0 && g_recv_len == 4 && memcmp(g_recv_buf, "ping", 4) == 0);
    t_check("lcm_handle_timeout_handled", timeout_msg_ok);
    (void)handled;

    /* 6) destroy (no crash / no double-free) */
    lcm_destroy(lcm);
    lcm = NULL;
    t_check("lcm_destroy", 1);

    if (g_failures != 0) {
        printf("RESULT: %d check(s) failed\n", g_failures);
        return 1;
    }
    printf("RESULT: all checks passed\n");
    return 0;
}
