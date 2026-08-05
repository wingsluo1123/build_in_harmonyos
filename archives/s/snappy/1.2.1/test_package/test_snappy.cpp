#include <snappy.h>
#include <snappy-stubs-public.h>

#include <cstdio>
#include <string>
#include <cstring>

int main() {
    const std::string input =
        "snappy 1.2.1 compression test - Hello OHOS!";
    std::string compressed;
    snappy::Compress(input.data(), input.size(), &compressed);

    std::string decompressed;
    if (!snappy::Uncompress(compressed.data(), compressed.size(),
                            &decompressed)) {
        std::fprintf(stderr, "Uncompress failed\n");
        return 1;
    }
    if (decompressed != input) {
        std::fprintf(stderr, "Round-trip mismatch\n");
        return 1;
    }
    std::printf("OK: compressed %zu -> %zu bytes, round-trip verified\n",
                input.size(), compressed.size());
    return 0;
}
