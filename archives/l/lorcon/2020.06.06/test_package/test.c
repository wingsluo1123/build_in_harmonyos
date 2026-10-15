#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <lorcon2/lorcon.h>
#include <lorcon2/lorcon_forge.h>
#include <lorcon2/lorcon_packasm.h>

int main(void) {
    int passed = 0;

    /* 1: library version is non-zero (Makefile VERSION 20180302). */
    {
        unsigned long ver = lorcon_get_version();
        if (ver == 0) {
            fprintf(stderr, "lorcon_get_version returned 0\n");
            return 1;
        }
        printf("CHECK-OK: version=%lu\n", ver);
        passed++;
    }

    /* 2: packet assembly list init/append/size/freeze/free. */
    {
        struct lcpa_metapack *pack = lcpa_init();
        uint8_t payload[4] = {0xde, 0xad, 0xbe, 0xef};
        uint8_t frozen[16];
        if (!pack) {
            fprintf(stderr, "lcpa_init returned NULL\n");
            return 2;
        }
        if (!lcpa_append_copy(pack, "test", sizeof(payload), payload)) {
            fprintf(stderr, "lcpa_append_copy failed\n");
            lcpa_free(pack);
            return 2;
        }
        if (lcpa_size(pack) != (int) sizeof(payload)) {
            fprintf(stderr, "lcpa_size mismatch: %d\n", lcpa_size(pack));
            lcpa_free(pack);
            return 2;
        }
        memset(frozen, 0, sizeof(frozen));
        lcpa_freeze(pack, frozen);
        if (memcmp(frozen, payload, sizeof(payload)) != 0) {
            fprintf(stderr, "lcpa_freeze content mismatch\n");
            lcpa_free(pack);
            return 2;
        }
        lcpa_free(pack);
        printf("CHECK-OK: packasm roundtrip\n");
        passed++;
    }

    /* 3: 802.11 beacon forge produces a non-empty frame. */
    {
        struct lcpa_metapack *pack = lcpa_init();
        uint8_t src[6] = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55};
        uint8_t bssid[6] = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55};
        int size;
        if (!pack) {
            fprintf(stderr, "lcpa_init returned NULL (beacon)\n");
            return 3;
        }
        lcpf_beacon(pack, src, bssid, 0, 0, 0, 0, 0, 100, 0x21);
        size = lcpa_size(pack);
        if (size <= 0) {
            fprintf(stderr, "lcpf_beacon produced empty frame\n");
            lcpa_free(pack);
            return 3;
        }
        lcpa_free(pack);
        printf("CHECK-OK: beacon size=%d\n", size);
        passed++;
    }

    /* 4: HT channel string parsing needs no hardware. */
    {
        lorcon_channel_t chan;
        memset(&chan, 0, sizeof(chan));
        if (lorcon_parse_ht_channel("6", &chan) != 0) {
            fprintf(stderr, "lorcon_parse_ht_channel failed\n");
            return 4;
        }
        if (chan.type != LORCON_CHANNEL_BASIC) {
            fprintf(stderr, "unexpected channel type %u\n", chan.type);
            return 4;
        }
        printf("CHECK-OK: ht channel parsed\n");
        passed++;
    }

    printf("lorcon API assertions: %d passed\n", passed);
    return 0;
}
