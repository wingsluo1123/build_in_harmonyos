#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <smpp34.h>
#include <smpp34_structs.h>

int main(void) {
    bind_transmitter_t input;
    bind_transmitter_t output;
    uint8_t buffer[256] = {0};
    int encoded_length = 0;

    memset(&input, 0, sizeof(input));
    memset(&output, 0, sizeof(output));
    input.command_id = BIND_TRANSMITTER;
    input.command_status = ESME_ROK;
    input.sequence_number = 7;
    memcpy(input.system_id, "consumer", 8);
    memcpy(input.password, "secret", 6);
    memcpy(input.system_type, "smpp", 4);
    input.interface_version = 0x34;
    input.addr_ton = 2;
    input.addr_npi = 1;
    memcpy(input.address_range, "12345", 5);

    if (smpp34_pack(BIND_TRANSMITTER, buffer, sizeof(buffer), &encoded_length,
                    &input) != 0)
        return 1;
    if (encoded_length < 16)
        return 2;
    if (smpp34_unpack(BIND_TRANSMITTER, &output, buffer, encoded_length) != 0)
        return 3;
    if (output.command_id != BIND_TRANSMITTER ||
        output.sequence_number != input.sequence_number)
        return 4;
    if (memcmp(output.system_id, input.system_id, 8) != 0)
        return 5;

    puts("LIB_SMPP34_CONSUMER_OK");
    return 0;
}
