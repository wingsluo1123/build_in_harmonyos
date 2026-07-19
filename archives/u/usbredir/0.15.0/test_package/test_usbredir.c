#include <stdint.h>
#include <stdio.h>

#include <usbredirhost.h>
#include <usbredirparser.h>
#include <usbredirproto.h>

static void log_cb(void *priv, int level, const char *msg)
{
    (void)priv;
    (void)level;
    (void)msg;
}

static int read_cb(void *priv, uint8_t *data, int count)
{
    (void)priv;
    (void)data;
    (void)count;
    return 0;
}

static int write_cb(void *priv, uint8_t *data, int count)
{
    (void)priv;
    (void)data;
    return count;
}

int main(void)
{
    uint32_t caps[USB_REDIR_CAPS_SIZE] = {0};
    struct usbredirparser *parser = usbredirparser_create();
    if (parser == NULL) {
        return 1;
    }

    usbredirparser_caps_set_cap(caps, usb_redir_cap_bulk_streams);
    usbredirparser_init(parser, "usbredir-test", caps, USB_REDIR_CAPS_SIZE, 0);
    usbredirparser_destroy(parser);

    struct usbredirhost *host = usbredirhost_open(
        NULL, NULL, log_cb, read_cb, write_cb, NULL, "usbredir-test", 0, 0);
    if (host == NULL) {
        return 2;
    }
    usbredirhost_close(host);

    puts("usbredir parser and host smoke test passed");
    return 0;
}
