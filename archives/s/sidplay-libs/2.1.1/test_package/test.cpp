// test_package consumer test — sidplay-libs 2.1.1
// Real API usage of libsidplay2 + libsidutils (R34: must not be a shell).
#include <sidplay/sidplay2.h>
#include <sidplay/sid2types.h>
#include <sidplay/utils/SidDatabase.h>
#include <cstdio>

int main() {
    // libsidplay2: construct the playback engine and query info
    sidplay2 engine;
    const sid2_info_t &info = engine.info();
    if (!engine) {
        std::printf("FAIL: sidplay2 engine not constructed\n");
        return 1;
    }
    std::printf("OK: sidplay2 engine info version=%s channels=%u\n",
                info.version, info.channels);

    // libsidutils: SidDatabase object (MD5/SID database helper)
    SidDatabase db;
    db.error();  // touch the API surface
    std::printf("OK: sidplay-libs consumer test passed\n");
    return 0;
}
