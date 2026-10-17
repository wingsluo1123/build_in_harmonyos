/*
 * test_package consumer test for libproxyprotocol 1.3.3.
 *
 * R34: the test must actually call the packaged library's API, not just
 * print a string. Here we create v1/v2 PROXY protocol headers with
 * pp_create_hdr()/pp2_create_healthcheck_hdr(), parse them back with
 * pp_parse_hdr(), and verify the parsed fields round-trip correctly.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "proxy_protocol.h"

int main(void)
{
    pp_info_t info;
    uint16_t hdr_len = 0;
    int32_t error = ERR_NULL;
    uint8_t *hdr;

    memset(&info, 0, sizeof(info));
    strcpy(info.src_addr, "192.168.10.100");
    strcpy(info.dst_addr, "192.168.11.90");
    info.src_port = 42332;
    info.dst_port = 8080;

    /* v1 header creation */
    hdr = pp_create_hdr(1, &info, &hdr_len, &error);
    if (hdr == NULL || error != ERR_NULL || hdr_len == 0) {
        printf("FAILED: pp_create_hdr(v1)\n");
        return EXIT_FAILURE;
    }
    printf("created v1 header (%u bytes): %.50s\n", hdr_len, (char *)hdr);
    free(hdr);

    /* v2 header creation */
    info.pp2_info.local = 0; /* PROXY */
    info.address_family = ADDR_FAMILY_INET;
    info.transport_protocol = TRANSPORT_PROTOCOL_STREAM;
    hdr = pp_create_hdr(2, &info, &hdr_len, &error);
    if (hdr == NULL || error != ERR_NULL || hdr_len == 0) {
        printf("FAILED: pp_create_hdr(v2)\n");
        return EXIT_FAILURE;
    }
    printf("created v2 header (%u bytes)\n", hdr_len);

    /* v2 parse-back: verify src/dst round-trip */
    {
        pp_info_t parsed;
        int32_t rc;
        memset(&parsed, 0, sizeof(parsed));
        rc = pp_parse_hdr(hdr, hdr_len, &parsed);
        if (rc <= 0) {
            printf("FAILED: pp_parse_hdr rc=%d\n", rc);
            free(hdr);
            return EXIT_FAILURE;
        }
        if (strcmp(parsed.src_addr, "192.168.10.100") != 0 ||
            strcmp(parsed.dst_addr, "192.168.11.90") != 0 ||
            parsed.src_port != 42332 || parsed.dst_port != 8080) {
            printf("FAILED: parsed fields mismatch (%s/%u -> %s/%u)\n",
                   parsed.src_addr, parsed.src_port, parsed.dst_addr, parsed.dst_port);
            pp_info_clear(&parsed);
            free(hdr);
            return EXIT_FAILURE;
        }
        pp_info_clear(&parsed);
    }
    free(hdr);

    /* v2 healthcheck header */
    hdr = pp2_create_healthcheck_hdr(&hdr_len, &error);
    if (hdr == NULL || error != ERR_NULL || hdr_len == 0) {
        printf("FAILED: pp2_create_healthcheck_hdr\n");
        return EXIT_FAILURE;
    }
    printf("created v2 healthcheck header (%u bytes)\n", hdr_len);
    free(hdr);

    /* error string lookup */
    if (pp_strerror(ERR_NULL) == NULL) {
        printf("FAILED: pp_strerror(ERR_NULL)\n");
        return EXIT_FAILURE;
    }

    printf("libproxyprotocol 1.3.3 consumer test: ALL PASSED\n");
    return EXIT_SUCCESS;
}
