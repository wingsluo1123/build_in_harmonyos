#include <stdbool.h>
#include <stdint.h>

#include <pb_decode.h>
#include <pb_encode.h>

int main(void)
{
    uint8_t buffer[16] = {0};
    pb_ostream_t output = pb_ostream_from_buffer(buffer, sizeof(buffer));

    if (!pb_encode_tag(&output, PB_WT_VARINT, 1)) {
        return 1;
    }
    if (!pb_encode_varint(&output, 150)) {
        return 2;
    }

    pb_istream_t input = pb_istream_from_buffer(buffer, output.bytes_written);
    pb_wire_type_t wire_type;
    uint32_t tag;
    bool eof = false;
    uint64_t value;

    if (!pb_decode_tag(&input, &wire_type, &tag, &eof)) {
        return 3;
    }
    if (eof || wire_type != PB_WT_VARINT || tag != 1) {
        return 4;
    }
    if (!pb_decode_varint(&input, &value) || value != 150) {
        return 5;
    }

    return 0;
}
