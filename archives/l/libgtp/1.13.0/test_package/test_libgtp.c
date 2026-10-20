#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <osmocom/core/bits.h>
#include <osmocom/gtp/gtpie.h>

int main(void) {
    uint8_t buffer[64] = {0};
    unsigned int length = 0;
    const uint8_t value[] = {1, 2, 3, 4, 5, 6};

    if (gtpie_tlv(buffer, &length, sizeof(buffer), 23, sizeof(value), value) != 0)
        return 1;
    if (length != sizeof(value) + 3)
        return 2;
    if (buffer[0] != 23 || osmo_load16be(&buffer[1]) != sizeof(value))
        return 3;
    if (memcmp(&buffer[3], value, sizeof(value)) != 0)
        return 4;

    length = 0;
    if (gtpie_tv4(buffer, &length, sizeof(buffer), 42, 0xABCD0123U) != 0)
        return 5;
    if (length != 5 || osmo_load32be(&buffer[1]) != 0xABCD0123U)
        return 6;

    puts("LIBGTP_CONSUMER_OK");
    return 0;
}
