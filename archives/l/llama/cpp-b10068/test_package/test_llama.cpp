#include "ggml.h"
#include "llama.h"

#include <cstdio>

int main() {
    const char *ver = ggml_version();
    if (!ver || !ver[0]) {
        std::fprintf(stderr, "ggml_version() returned empty\n");
        return 1;
    }
    std::printf("ggml version : %s\n", ver);

    const size_t max_devices = llama_max_devices();
    std::printf("max devices  : %zu\n", max_devices);
    if (max_devices == 0) {
        std::fprintf(stderr, "llama_max_devices() == 0\n");
        return 1;
    }
    return 0;
}
