#include <lhasa.h>

int main(void)
{
    LHAInputStream *stream = lha_input_stream_from("definitely-missing.lzh");
    if (stream != 0) {
        lha_input_stream_free(stream);
        return 1;
    }
    return 0;
}
