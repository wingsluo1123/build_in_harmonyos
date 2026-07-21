#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libusb.h>
#include <usbredirhost.h>
#include <usbredirparser.h>
#include <usbredirproto.h>

struct callback_state {
    int log_calls;
    int read_calls;
    int write_calls;
    int bytes_written;
};

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "usbredir test failed: %s\n", message);
        exit(1);
    }
}

static void log_cb(void *priv, int level, const char *msg)
{
    (void)level;
    struct callback_state *state = (struct callback_state *)priv;
    require_true(state != NULL, "log callback state");
    require_true(msg != NULL, "log callback message");
    state->log_calls++;
}

static int read_cb(void *priv, uint8_t *data, int count)
{
    struct callback_state *state = (struct callback_state *)priv;
    require_true(state != NULL, "read callback state");
    require_true(data != NULL, "read callback buffer");
    require_true(count > 0, "read callback count");
    state->read_calls++;
    return 0;
}

static int write_cb(void *priv, uint8_t *data, int count)
{
    struct callback_state *state = (struct callback_state *)priv;
    require_true(state != NULL, "write callback state");
    require_true(data != NULL, "write callback buffer");
    require_true(count > 0, "write callback count");
    state->write_calls++;
    state->bytes_written += count;
    return count;
}

int main(void)
{
    uint32_t caps[USB_REDIR_CAPS_SIZE] = {0};
    struct callback_state parser_state;
    struct callback_state host_state;
    libusb_context *usb_ctx = NULL;

    memset(&parser_state, 0, sizeof(parser_state));
    memset(&host_state, 0, sizeof(host_state));

    struct usbredirparser *parser = usbredirparser_create();
    require_true(parser != NULL, "create parser");
    parser->priv = &parser_state;
    parser->log_func = log_cb;
    parser->read_func = read_cb;
    parser->write_func = write_cb;

    usbredirparser_caps_set_cap(caps, usb_redir_cap_bulk_streams);
    usbredirparser_init(parser, "usbredir-test", caps, USB_REDIR_CAPS_SIZE, 0);
    require_true(usbredirparser_have_cap(parser, usb_redir_cap_bulk_streams),
                 "bulk streams capability enabled");
    usbredirparser_send_device_disconnect(parser);
    require_true(usbredirparser_has_data_to_write(parser) > 0,
                 "parser queued disconnect packet");
    require_true(usbredirparser_do_write(parser) == 0,
                 "parser wrote queued packet");
    require_true(parser_state.write_calls > 0, "parser write callback invoked");
    require_true(parser_state.bytes_written > 0, "parser wrote bytes");
    usbredirparser_destroy(parser);

    require_true(libusb_init(&usb_ctx) == 0, "initialize libusb context");
    struct usbredirhost *host = usbredirhost_open(
        usb_ctx, NULL, log_cb, read_cb, write_cb, &host_state, "usbredir-test", 0, 0);
    require_true(host != NULL, "open host with libusb context");
    usbredirhost_close(host);
    libusb_exit(usb_ctx);

    puts("usbredir parser packet and host context test passed");
    return 0;
}
