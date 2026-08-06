#include <libsoup/soup.h>
#include <glib.h>

int main(void) {
    /* Test: create a SoupMessage and verify it's not NULL */
    SoupMessage *msg = soup_message_new("GET", "https://example.com");
    if (msg == NULL) {
        g_print("FAIL: soup_message_new returned NULL\n");
        return 1;
    }
    g_object_unref(msg);
    g_print("OK: libsoup 2.74.3 test passed\n");
    return 0;
}
