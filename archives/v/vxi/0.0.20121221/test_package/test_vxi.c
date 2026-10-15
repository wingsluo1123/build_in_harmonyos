/* test_vxi.c — consumer test for vxi 0.0.20121221 (R34: real API calls).
 *
 * Links against installed libvxiclient.a/libvxiserver.a + libtirpc and:
 *   1. checks DEVICE_CORE / DEVICE_ASYNC / DEVICE_INTR program numbers
 *      from the rpcgen-generated headers match the VXI-11 spec constants;
 *   2. exercises the XDR codec for Create_LinkParms (xdr_Create_LinkParms)
 *      with a memory XDR stream: encode then decode, compare fields;
 *   3. exercises the XDR codec for Device_WriteParms round-trip;
 *   4. verifies the static archives export the expected client symbols
 *      (checked at link time: referencing them fails the link when absent).
 *
 * Each CHECK prints PASS/FAIL; main returns 0 only when all pass.
 * The conanfile runs this binary and emits HMBS_TEST_PACKAGE_RESULT
 * with discovered=4/passedCount=4 on exit 0.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <rpc/rpc.h>
#include <rpc/xdr.h>

#include "vxi.h"
#include "vxi_intr.h"

#define CHECK(n, cond, label) do { \
    if (cond) { printf("CHECK%d PASS: %s\n", (n), (label)); ++passed; } \
    else { printf("CHECK%d FAIL: %s\n", (n), (label)); } \
} while (0)

int main(void) {
    int passed = 0;

    /* 1. Program numbers from the VXI-11 specification. */
    CHECK(1, DEVICE_CORE == 0x0607AF && DEVICE_ASYNC == 0x0607B0
             && DEVICE_INTR == 0x0607B1,
          "DEVICE_CORE/ASYNC/INTR program numbers match spec");

    /* 2. XDR round-trip for Create_LinkParms. */
    {
        char buf[1024];
        XDR xdr_enc, xdr_dec;
        Create_LinkParms in, out;
        memset(&in, 0, sizeof(in));
        memset(&out, 0, sizeof(out));
        in.clientId = 1234;
        in.lockDevice = TRUE;
        in.lock_timeout = 5000;
        in.device = (char *)"inst0";

        xdrmem_create(&xdr_enc, buf, sizeof(buf), XDR_ENCODE);
        bool_t ok_enc = xdr_Create_LinkParms(&xdr_enc, &in);
        unsigned enc_size = ok_enc ? (unsigned)xdr_getpos(&xdr_enc) : 0;
        xdr_destroy(&xdr_enc);

        bool_t ok_dec = FALSE;
        if (ok_enc) {
            xdrmem_create(&xdr_dec, buf, enc_size, XDR_DECODE);
            memset(&out, 0, sizeof(out));
            ok_dec = xdr_Create_LinkParms(&xdr_dec, &out);
            xdr_destroy(&xdr_dec);
        }
        CHECK(2, ok_enc && ok_dec && out.clientId == 1234
                 && out.lock_timeout == 5000 && out.device
                 && strcmp(out.device, "inst0") == 0,
              "xdr_Create_LinkParms encode/decode round-trip");
        if (out.device) {
            xdr_free((xdrproc_t)xdr_Create_LinkParms, (char *)&out);
        }
    }

    /* 3. XDR round-trip for Device_WriteParms with payload. */
    {
        static const char payload[] = "*IDN?";
        char buf[1024];
        XDR xdr_enc, xdr_dec;
        Device_WriteParms in, out;
        memset(&in, 0, sizeof(in));
        memset(&out, 0, sizeof(out));
        in.lid = 7;
        in.io_timeout = 1000;
        in.lock_timeout = 2000;
        in.flags = 0;
        in.data.data_len = (unsigned)sizeof(payload) - 1;
        in.data.data_val = (char *)payload;

        xdrmem_create(&xdr_enc, buf, sizeof(buf), XDR_ENCODE);
        bool_t ok_enc = xdr_Device_WriteParms(&xdr_enc, &in);
        unsigned enc_size = ok_enc ? (unsigned)xdr_getpos(&xdr_enc) : 0;
        xdr_destroy(&xdr_enc);

        bool_t ok_dec = FALSE;
        if (ok_enc) {
            xdrmem_create(&xdr_dec, buf, enc_size, XDR_DECODE);
            memset(&out, 0, sizeof(out));
            ok_dec = xdr_Device_WriteParms(&xdr_dec, &out);
            xdr_destroy(&xdr_dec);
        }
        CHECK(3, ok_enc && ok_dec && out.lid == 7
                 && out.data.data_len == sizeof(payload) - 1
                 && memcmp(out.data.data_val, payload, sizeof(payload) - 1) == 0,
              "xdr_Device_WriteParms encode/decode round-trip");
        if (ok_dec) {
            xdr_free((xdrproc_t)xdr_Device_WriteParms, (char *)&out);
        }
    }

    /* 4. Link-time reference to client/server stub symbols. */
    {
        /* xdr entry points live in the vxi archives (not in libtirpc):
         * taking their addresses forces the linker to resolve them. */
        void *p1 = (void *)xdr_Create_LinkResp;
        void *p2 = (void *)xdr_Device_ReadResp;
        void *p3 = (void *)xdr_Device_SrqParms;
        CHECK(4, p1 != NULL && p2 != NULL && p3 != NULL,
              "client/server XDR symbols resolve from libvxiclient/libvxiserver");
    }

    printf("SUMMARY: %d/4 checks passed\n", passed);
    return passed == 4 ? 0 : 1;
}
