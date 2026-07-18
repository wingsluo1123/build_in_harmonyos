#include <stdio.h>
#include <stdlib.h>
#include "bento4/Ap4.h"

int main(void) {
    // Verify bento4 library is usable by creating a minimal MP4 output stream
    AP4_ByteStream* output = NULL;
    AP4_Result result = AP4_FileByteStream::Create("test.mp4",
                                                    AP4_FileByteStream::STREAM_MODE_WRITE,
                                                    output);
    if (AP4_FAILED(result)) {
        printf("test bento4 1.6.0: FAILED (Create stream returned %d)\n", result);
        return 1;
    }
    output->Release();
    printf("test bento4 1.6.0: OK\n");
    return 0;
}
